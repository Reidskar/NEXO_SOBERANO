from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db, Document, Event
from services.document_processor import document_processor
from datetime import datetime
import logging
from api.webhooks.supabase import router as webhook_supabase_router
from api.webhooks.discord import router as webhook_discord_router
from services.analytics_service import analytics_service, TrackEventPayload, EmailSubscribePayload

logger = logging.getLogger(__name__)
router = APIRouter()

class TaskCompletePayload(BaseModel):
    document_id: int
    extracted_text: str
    error: Optional[str] = None

class NLPControlPayload(BaseModel):
    command: str

@router.get("/config")
async def get_system_config():
    from core.system_config import get_config
    return get_config()

@router.post("/ai/control")
async def control_system_via_ai(payload: NLPControlPayload):
    from services.ai_controller import nlp_command_controller
    result = await nlp_command_controller.execute_command(payload.command)
    if result.get("action") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@router.get("/tasks/pending")
async def get_pending_tasks(db: AsyncSession = Depends(get_db)):
    """API para Local Worker: Devuelve tareas pesadas pendientes (PDF/OCR) priorizadas."""
    stmt = select(Document).where(Document.status == "pending").order_by(Document.priority.asc(), Document.created_at.asc()).limit(5)
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [{"id": d.id, "title": d.title, "drive_url": d.drive_url, "priority": d.priority} for d in docs]

@router.post("/tasks/complete")
async def complete_task(payload: TaskCompletePayload, db: AsyncSession = Depends(get_db)):
    """API para Local Worker: Recibe texto extraído y lanza la inferencia final en Cloud."""
    doc = await db.get(Document, payload.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if payload.error:
        doc.status = "failed"
        doc.last_error = payload.error
        doc.retry_count += 1
        await db.commit()
        return {"status": "error_logged"}
        
    # Azure AI Analysis con el texto devuelto desde la PC local
    try:
        success, ai_data = await document_processor.analyze_and_save(doc, payload.extracted_text, db)
        
        if success:
            return {"status": "completed"}
        else:
            raise HTTPException(status_code=500, detail="AI processing in cloud failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# REGISTRO DE WEBHOOKS AUTÓNOMOS
# ================================
router.include_router(webhook_supabase_router, prefix="/webhooks", tags=["Webhooks"])
router.include_router(webhook_discord_router, prefix="/webhooks", tags=["Webhooks"])

@router.post("/analytics/track")
async def track_frontend_event(payload: TrackEventPayload):
    """API para recolectar eventos de interacción UX (Time on page, scrolls, clicks)"""
    success = await analytics_service.track(payload)
    if not success:
        raise HTTPException(status_code=500, detail="Analytics Tracking Error")
    return {"status": "ok"}

@router.post("/email/subscribe")
async def subscribe_user_email(payload: EmailSubscribePayload):
    """API Core de Growth - Captura silenciosa de Leads y Newsletters"""
    res = await analytics_service.subscribe(payload)
    if res["status"] == "error":
        raise HTTPException(status_code=500, detail="Internal Error")
    return res

# ---- ENDPOINTS PÚBLICOS DE DATOS Y FRONTEND (Dashboard MVP) ----

@router.get("/documents")
async def get_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()).limit(50))
    return result.scalars().all()

@router.get("/events")
async def get_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).order_by(Event.created_at.desc()).limit(50))
    return result.scalars().all()

@router.get("/countries/{name}")
async def get_country_stats(name: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Event).where(Event.country.ilike(f"%{name}%"))
    result = await db.execute(stmt)
    events = result.scalars().all()
    return {"country": name, "total_events": len(events), "events": events}

@router.get("/timeline/{country}")
async def get_country_timeline(country: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Event).where(Event.country.ilike(f"%{country}%")).order_by(Event.created_at.desc())
    result = await db.execute(stmt)
    events = result.scalars().all()
    return {"timeline": events}
