import hmac
import hashlib
import json
import os
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from NEXO_CORE.core.database import get_db, set_tenant_schema
from typing import Dict, Any

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = os.getenv("NEXO_WEBHOOK_SECRET", "super-secret-key")

def verify_signature(payload: bytes, signature: str):
    """Valida la firma HMAC-SHA256 del webhook."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/ingest")
async def webhook_ingest(request: Request, db: Session = Depends(get_db)):
    """Recibe y enruta alertas externas de WorldMonitor o n8n."""
    signature = request.headers.get("X-NEXO-Signature")
    body = await request.body()
    
    if signature and not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        data = json.loads(body)
        tenant_slug = data.get("tenant_slug", "demo")
        
        set_tenant_schema(db, tenant_slug)
        
        import uuid
        
        # Insertar alerta
        sql = text("""
            INSERT INTO alertas (id, tipo, severidad, titulo, descripcion, fuente, created_at)
            VALUES (:id, :tipo, :sev, :titulo, :desc, :src, NOW())
        """)
        db.execute(sql, {
            "id": str(uuid.uuid4()),
            "tipo": data.get("type", "external"),
            "sev": float(data.get("severity") or 0.5),
            "titulo": data.get("title", "Alerta Webhook"),
            "desc": data.get("body", str(data)),
            "src": "webhook_ingest"
        })
        db.commit()
        
        return {"status": "success", "tenant": tenant_slug}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
