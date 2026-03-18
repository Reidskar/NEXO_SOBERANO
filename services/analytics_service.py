import uuid
import json
import logging
import re
from datetime import datetime
from pydantic import BaseModel, EmailStr
from core.database import SessionLocal, AnalyticsEvent, Subscriber
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class TrackEventPayload(BaseModel):
    event_type: str
    document_id: int | None = None
    metadata_data: dict | None = None

class EmailSubscribePayload(BaseModel):
    email: EmailStr
    source: str = "web"

class AnalyticsService:
    async def track(self, payload: TrackEventPayload):
        async with SessionLocal() as db:
            try:
                event = AnalyticsEvent(
                    event_id=str(uuid.uuid4()),
                    document_id=payload.document_id,
                    event_type=payload.event_type,
                    metadata_json=json.dumps(payload.metadata_data or {}),
                    timestamp=datetime.utcnow()
                )
                db.add(event)
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"Falla crítica en Analytics Tracking: {e}")
                return False

    async def subscribe(self, payload: EmailSubscribePayload):
        async with SessionLocal() as db:
            try:
                stmt = select(Subscriber).where(Subscriber.email == payload.email)
                existing = await db.execute(stmt)
                if existing.scalars().first():
                    return {"status": "duplicate"}

                new_sub = Subscriber(
                    email=payload.email,
                    source=payload.source,
                    created_at=datetime.utcnow()
                )
                db.add(new_sub)
                await db.commit()
                logger.info(f"✨ [GROWTH] Nuevo suscriptor capturado: {payload.email}")
                return {"status": "success"}
                
            except Exception as e:
                logger.error(f"Error procesando captura de email: {e}")
                return {"status": "error"}

analytics_service = AnalyticsService()
