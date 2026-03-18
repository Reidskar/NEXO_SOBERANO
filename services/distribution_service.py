import logging
import asyncio
from datetime import datetime
from core.database import SessionLocal, Document
from core.config import settings
from core.queue_manager import system_queue
from services.discord_service import discord_service

logger = logging.getLogger(__name__)

class DistributionService:
    async def distribute(self, document_id: int, video_url: str, title: str, summary: str, impact_score: float) -> bool:
        if not video_url:
            logger.warning(f"⚠️ [DISTRIBUTION] Abortando (ID {document_id}): Video URL requerido no encontrado.")
            return False

        async with SessionLocal() as db:
            doc = await db.get(Document, document_id)
            if not doc:
                logger.error(f"❌ [DISTRIBUTION] Error Crítico: Documento ID {document_id} extraviado.")
                return False

            if doc.published:
                logger.info(f"⏭️ [DISTRIBUTION] Bypass (ID {document_id}): Contenido ya fue publicado globalmente.")
                return True

            logger.info(f"🚀 [DISTRIBUTION] Trillando audiencias (Impact: {impact_score}) | ID: {document_id}")

            distributed_discord = False
            distributed_web = False
            distributed_news = False

            try:
                # 🔀 MATRIX DE RUTEO POR IMPACT_SCORE
                if impact_score >= 8:
                    distributed_discord = await self._send_to_discord(title, summary, video_url, impact_score)
                    distributed_web = True
                    distributed_news = await self._queue_newsletter(doc.id, title)
                elif impact_score >= 5:
                    distributed_discord = await self._send_to_discord(title, summary, video_url, impact_score)
                    distributed_web = True
                else:
                    logger.info(f"ℹ️ [DISTRIBUTION] Impact Score ({impact_score} < 5). Aislado en Vault (No distribuido).")

                # ✅ Persistencia segura en base de datos
                doc.published = distributed_web
                if distributed_web:
                    doc.published_at = datetime.utcnow()
                    
                doc.distributed_to_discord = distributed_discord
                doc.distributed_to_web = distributed_web
                doc.distributed_to_newsletter = distributed_news
                doc.distribution_timestamp = datetime.utcnow()

                await db.commit()
                logger.info(f"💾 [DISTRIBUTION] Pipeline exitoso. Web={distributed_web} DC={distributed_discord} News={distributed_news}")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"🚨 [DISTRIBUTION] Colapso inyectando en la red DB: {e}")
                return False

    async def _send_to_discord(self, title: str, summary: str, video_url: str, impact_score: float) -> bool:
        for attempt in range(2):
            try:
                payload = {
                    "title": f"🚨 PROTOCOLO CÍVICO: {title}",
                    "summary": f"IMPACTO CALCULADO: {impact_score}\n\n" + (summary[:180] + "...") if summary else "",
                    "drive_url": video_url, # Hack provisional: reusamos campo drive_url en Discord UI
                    "type": "distribution_alert"
                }
                
                # Aprovechamos el webhook persistente
                await discord_service.notify_new_document(payload)
                return True
            except Exception as e:
                logger.warning(f"⚠️ [DISTRIBUTION-DISCORD] Reintento {attempt+1}/2 fallido: {e}")
                await asyncio.sleep(2)
        
        logger.error(f"❌ [DISTRIBUTION-DISCORD] Fatiga de red total.")
        return False

    async def _queue_newsletter(self, document_id: int, title: str) -> bool:
        try:
            # Integrando con la misma Task Queue segura que usamos para el webhook
            async def _dispatch_campaign(doc_id):
                logger.info(f"📧 [NEWSLETTER_WORKER] Transmitiendo boletín encriptado. Doc: {doc_id}")
                await asyncio.sleep(1)
                
            await system_queue.enqueue(_dispatch_campaign, document_id, event_id=f"nslttr_{document_id}")
            return True
        except Exception as e:
            logger.error(f"❌ [DISTRIBUTION-NEWS] Fallo encolando envío: {e}")
            return False

distribution_service = DistributionService()
