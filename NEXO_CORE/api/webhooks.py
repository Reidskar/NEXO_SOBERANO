import hmac
import hashlib
import json
import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from typing import Any

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = os.getenv("NEXO_WEBHOOK_SECRET", "super-secret-key")
NEXO_API_KEY   = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")


def _verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/ingest")
async def webhook_ingest(request: Request):
    """
    Unified webhook ingestion.
    Accepts: mobile_agent pings, WorldMonitor events, and Phase-12 TACTICAL_SIMULATION events.
    Auth: x-api-key header OR X-NEXO-Signature HMAC.
    """
    # ── Auth ────────────────────────────────────────────────────────────────
    api_key   = request.headers.get("x-api-key", "")
    signature = request.headers.get("X-NEXO-Signature", "")
    body      = await request.body()

    if api_key != NEXO_API_KEY:
        if signature and not _verify_signature(body, signature):
            raise HTTPException(status_code=401, detail="API Key o firma invalida")
        elif not signature and not api_key:
            raise HTTPException(status_code=401, detail="Se requiere x-api-key")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Body must be valid JSON")

    tenant_slug = data.get("tenant_slug", "demo")
    event_type  = data.get("type", "external")

    # ── Build broadcast payload ──────────────────────────────────────────────
    payload: dict[str, Any] = {
        "tipo":        event_type,
        "titulo":      data.get("title", "Alerta Webhook"),
        "descripcion": data.get("body", str(data)),
        "severidad":   float(data.get("severity") or 0.5),
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }

    # ── Pass-through OSINT simulation fields ──────────────────────────────
    if event_type == "TACTICAL_SIMULATION" and data.get("lat") is not None:
        payload.update({
            "lat":        data.get("lat"),
            "lng":        data.get("lng"),
            "event_type": data.get("event_type"),
            "country":    data.get("country"),
            "target":     data.get("target"),
            "media_urls": data.get("media_urls", []),
            "source":     data.get("source"),
        })
        logger.info(
            f"[Webhook] TACTICAL_SIMULATION lat={data.get('lat')}, "
            f"lng={data.get('lng')}, target={data.get('target')}"
        )

    # ── Broadcast via WebSocket ─────────────────────────────────────────────
    try:
        from NEXO_CORE.core.websocket_manager import manager
        await manager.broadcast(tenant_slug, payload)
        logger.info(f"[Webhook] Broadcasted {event_type} to tenant={tenant_slug}")
    except Exception as ws_err:
        logger.warning(f"[Webhook] WebSocket broadcast failed: {ws_err}")

    # ── Persist to DB (best-effort, non-blocking) ───────────────────────────
    try:
        from NEXO_CORE.core.database import get_db, set_tenant_schema
        from sqlalchemy import text
        import uuid
        db = next(get_db())
        set_tenant_schema(db, tenant_slug)
        db.execute(text("""
            INSERT INTO alertas (id, tipo, severidad, titulo, descripcion, fuente, created_at)
            VALUES (:id, :tipo, :sev, :titulo, :desc, :src, NOW())
        """), {
            "id":     str(uuid.uuid4()),
            "tipo":   event_type,
            "sev":    float(data.get("severity") or 0.5),
            "titulo": data.get("title", "Alerta Webhook"),
            "desc":   data.get("body", ""),
            "src":    "webhook_ingest"
        })
        db.commit()
        db.close()
    except Exception as db_err:
        logger.debug(f"[Webhook] DB persist skipped (non-blocking): {db_err}")

    return {"status": "success", "received": event_type, "broadcasted": True}
