from fastapi import APIRouter, Header, HTTPException, Request, Depends
from typing import Optional
from core.config import settings
from core.queue_manager import system_queue
from workers.pipeline import pipeline_orchestrator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db, Document
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/supabase")
async def handle_supabase_webhook(
    request: Request,
    x_supabase_secret: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Supabase DB Triggers Hook
    Despierta al Pipeline instantáneamente de forma segura
    """
    event_id = str(uuid.uuid4())
    logger.info(f"🌐 [IN] Webhook Event ID {event_id} recibido.")

    expected_secret = getattr(settings, "SUPABASE_WEBHOOK_SECRET", "super_secure_nexo_token")
    
    if x_supabase_secret != expected_secret:
        logger.warning(f"Intento de acceso denegado a Webhook Supabase. (Event ID: {event_id})")
        raise HTTPException(status_code=401, detail="Invalid Supabase Signature")

    payload = await request.json()
    action = payload.get("type", "UNKNOWN")
    record = payload.get("record", {})
    table = payload.get("table", "UNKNOWN")
    
    if table == "documents" and action == "INSERT":
        doc_source = record.get("source", "unknown")
        doc_title = record.get("title", "Desconocido")
        doc_hash = record.get("hash", "")
        
        # Anti-Duplicación
        if doc_hash:
            stmt = select(Document).where(Document.hash == doc_hash)
            existing = await db.execute(stmt)
            if existing.scalars().first():
                logger.info(f"Event ID {event_id}: Documento {doc_hash} duplicado ignorado.")
                return {"status": "duplicate", "event_id": event_id}

        logger.info(f"Impulso Neuronal Iniciando sobre un documento {doc_source}: {doc_title}")
        
        # Encolamos la tarea desacoplada
        await system_queue.enqueue(pipeline_orchestrator.run_cycle, event_id=event_id)
        
    return {"status": "queued", "event_id": event_id}
