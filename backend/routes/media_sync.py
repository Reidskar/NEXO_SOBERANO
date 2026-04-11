"""
NEXO — Media Sync API Routes
============================
Exposes endpoints to trigger and monitor the Google Photos / OneDrive → Drive
classification pipeline.

Routes:
  GET  /api/media/sync/status         → auth status + folder config
  POST /api/media/sync/run            → trigger sync (source, limit, dry_run)
  GET  /api/media/sync/classify       → classify a single filename/description
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from backend.services.media_sync import media_sync_service

logger = logging.getLogger("NEXO.routes.media_sync")
router = APIRouter(prefix="/api/media/sync", tags=["media-sync"])

_API_KEY = None  # loaded lazily from env


def _check_key(x_api_key: Optional[str]) -> None:
    import os
    expected = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="API key inválida")


# ── Models ───────────────────────────────────────────────────────────────────

class SyncRequest(BaseModel):
    source: str = Field("google_photos", description="google_photos | onedrive")
    limit: int = Field(30, ge=1, le=200, description="Máximo de items a procesar")
    dry_run: bool = Field(False, description="Si true, clasifica pero NO copia a Drive")


class ClassifyRequest(BaseModel):
    filename: str = Field(..., description="Nombre del archivo")
    description: str = Field("", description="Descripción opcional")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def sync_status():
    """Retorna el estado de autenticación de Google Photos y Drive."""
    try:
        status = await media_sync_service.get_status()
        return {"ok": True, **status}
    except Exception as e:
        logger.error("[media_sync] status error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def sync_run(
    req: SyncRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Lanza el pipeline de clasificación y sincronización de medios."""
    _check_key(x_api_key)
    try:
        report = await media_sync_service.run_sync(
            source=req.source,
            limit=req.limit,
            dry_run=req.dry_run,
        )
        return {"ok": True, "report": report}
    except Exception as e:
        logger.error("[media_sync] run error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify")
async def classify_single(req: ClassifyRequest):
    """Clasifica un único archivo por nombre/descripción (sin mover nada)."""
    try:
        item = {"filename": req.filename, "description": req.description, "id": "manual"}
        category = await media_sync_service._classify_item(item)
        return {"filename": req.filename, "category": category}
    except Exception as e:
        logger.error("[media_sync] classify error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
