from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db, Document, Event, SessionLocal, SponsoredSlot
from services.document_processor import document_processor
from datetime import datetime
import logging
from api.webhooks.supabase import router as webhook_supabase_router
from api.webhooks.discord import router as webhook_discord_router
from services.analytics_service import analytics_service, TrackEventPayload, EmailSubscribePayload
from services.connection_supervisor import connection_supervisor
from services.ops_agent import ops_agent

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

# ---- ENDPOINTS MONETIZACIÓN (Sponsored Slots) ----

@router.post("/sponsored/upload")
async def register_sponsored_slot(payload: dict):
    """Sube un clip pidiendo patrocinio en videos de NEXO (Máx 30s)"""
    async with SessionLocal() as db:
        duration = payload.get("duration_seconds", 0)
        if duration > 30:
            raise HTTPException(status_code=400, detail="Error: El vector publicitario excede los 30s de atención autorizada.")
            
        new_slot = SponsoredSlot(
            email=payload.get("email", "anonymous@nexo.com"),
            media_url=payload.get("media_url"),
            duration_seconds=duration,
            priority=payload.get("priority", 0)
        )
        db.add(new_slot)
        await db.commit()
        return {"status": "pending_validation", "slot_id": new_slot.id}

@router.post("/sponsored/approve/{slot_id}")
async def approve_sponsored_slot(slot_id: str):
    """Uso Interno: Validador de Calidad / Copyright"""
    async with SessionLocal() as db:
        stmt = select(SponsoredSlot).where(SponsoredSlot.id == slot_id)
        res = await db.execute(stmt)
        slot = res.scalars().first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot Inexistente")
            
        slot.status = "approved"
        await db.commit()
        return {"status": "approved", "slot_id": slot_id}

@router.get("/sponsored/active")
async def get_active_sponsors():
    async with SessionLocal() as db:
        stmt = select(SponsoredSlot).where(SponsoredSlot.status == "approved").order_by(SponsoredSlot.priority.desc())
        res = await db.execute(stmt)
        return [{"id": s.id, "media_url": s.media_url, "duration": s.duration_seconds} for s in res.scalars().all()]

@router.get("/system/status")
async def get_system_health_status():
    """Retorna la latencia y la salud de la estructura distribuida"""
    return {"status": "ok", "nodes": connection_supervisor.system_status}

@router.get("/system/ops")
async def get_ops_state():
    """Ventral del Agente Autónomo (Estado, Decisiones, Riesgo)"""
    return ops_agent.state

@router.get("/system/expansion")
async def get_expansion_metrics():
    """Retorna historial y red de plataformas penetradas por NEXO"""
    from services.expansion_agent import expansion_agent
    return {
        "status": "active" if expansion_agent.active else "paused",
        "platforms_reached": list(expansion_agent.platforms_used),
        "history_lines": len(expansion_agent.history),
        "last_posts": expansion_agent.history[-10:]
    }

# ---- ENDPOINTS PÚBLICOS DE DATOS Y FRONTEND (Dashboard MVP) ----

@router.get("/documents")
async def get_documents():
    async with SessionLocal() as db:
        stmt = select(Document).order_by(Document.created_at.desc())
        docs = await db.execute(stmt)
        return [
            {
                "id": d.id, 
                "title": d.title or "Sin título", 
                "summary": d.summary or "Sin resumen", 
                "status": d.status, 
                "impact_level": d.impact_level or 0, 
                "video_url": getattr(d, 'video_url', None),
                "slug": getattr(d, 'slug', f"report-{d.id}"),
                "seo_title": getattr(d, 'seo_title', d.title),
                "meta_description": getattr(d, 'meta_description', d.summary),
                "published": getattr(d, 'published', False)
            } for d in docs.scalars().all()
        ]

@router.get("/documents/{slug}")
async def get_document_by_slug(slug: str):
    async with SessionLocal() as db:
        # Resolvemos soporte legacy vs nuevo slug
        if slug.isdigit():
            stmt = select(Document).where(Document.id == int(slug))
        else:
            stmt = select(Document).where(Document.slug == slug)
            
        res = await db.execute(stmt)
        d = res.scalars().first()
        if not d:
            raise HTTPException(status_code=404, detail="Documento clasificado o purgado.")
            
        return {
            "id": d.id, 
            "title": d.title or "Sin título", 
            "summary": d.summary or "Sin resumen", 
            "status": d.status, 
            "impact_level": d.impact_level or 0, 
            "video_url": getattr(d, 'video_url', None),
            "slug": getattr(d, 'slug', f"report-{d.id}"),
            "seo_title": getattr(d, 'seo_title', d.title),
            "meta_description": getattr(d, 'meta_description', d.summary),
            "keywords": getattr(d, 'keywords', ""),
            "published": getattr(d, 'published', False),
            "content": f"{d.title}\n\n{d.summary}" # Mock para el análisis completo (paywall target)
        }

@router.get("/sitemap.xml", response_class=Response)
async def generate_sitemap():
    """Generador dinámico O(1) de Indexación para Vercel Edge"""
    async with SessionLocal() as db:
        # Traemos solo publicados para asegurar funnel sano
        stmt = select(Document).where(Document.published == True)
        res = await db.execute(stmt)
        docs = res.scalars().all()
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Static Core Routes
        xml_content += f"  <url>\n    <loc>https://elanarcocapital.com/</loc>\n    <changefreq>hourly</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
        
        # Dynamic Slugs
        for d in docs:
            safe_slug = getattr(d, 'slug', f"report-{d.id}")
            loc = f"https://elanarcocapital.com/d/{safe_slug}"
            raw_date = getattr(d, 'published_at', datetime.utcnow())
            lastmod = raw_date.strftime('%Y-%m-%d') if raw_date else datetime.utcnow().strftime('%Y-%m-%d')
            
            xml_content += f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>daily</changefreq>\n  </url>\n"
            
        xml_content += '</urlset>'
        return Response(content=xml_content, media_type="application/xml")

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
