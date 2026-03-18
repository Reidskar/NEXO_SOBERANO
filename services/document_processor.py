import json
import logging
import hashlib
import asyncio
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import Document, Event, SessionLocal
from core.config import settings
from core.system_config import get_config
from services.discord_service import discord_service
from services.video_generator import video_generator
try:
    from openai import AsyncAzureOpenAI
except ImportError:
    AsyncAzureOpenAI = None

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.client = None
        if AsyncAzureOpenAI and settings.AZURE_OPENAI_KEY:
            self.client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_KEY,
                api_version="2023-12-01-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )

    def _generate_hash(self, content_str: str) -> str:
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()

    async def create_pending_task(self, metadata: dict, priority: int) -> bool:
        """Crea un documento en la base de datos con status 'pending' para que el local worker lo reclame."""
        # En este paso no tenemos el contenido aun, generamos un pseudo-hash temporal con el ID para evitar dupes de drive_id
        doc_hash = self._generate_hash(metadata.get('id', metadata.get('name', '')))
        
        async with SessionLocal() as session:
            stmt = select(Document).where(Document.hash == doc_hash)
            existing = await session.execute(stmt)
            if existing.scalar_one_or_none():
                return False

            try:
                new_doc = Document(
                    title=metadata.get('name', 'Desconocido'),
                    country="Pendiente",
                    category="Pendiente",
                    drive_url=metadata.get('web_view_link', ''),
                    summary="En cola local...",
                    impact_level=0,
                    source_type="drive",
                    hash=doc_hash,
                    status="pending",
                    priority=priority
                )
                session.add(new_doc)
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error encolando documento a DB: {e}")
                return False

    async def analyze_and_save(self, doc: Document, extracted_text: str, session: AsyncSession) -> Tuple[bool, Dict[str, Any]]:
        """Es llamado por el webhook (/tasks/complete) cuando el Local Worker termina de hacer OCR."""
        
        ai_data = await self.analyze_with_ai(extracted_text)
        
        try:
            doc.title = ai_data.get('title', doc.title)
            doc.country = ai_data['country']
            doc.category = ai_data['category']
            doc.summary = ai_data['summary']
            doc.impact_level = ai_data['impact_score']
            doc.status = "processed"
            
            new_event = Event(
                country=ai_data['country'],
                type=ai_data.get('type', 'generic'),
                description=ai_data['summary'],
                document_id=doc.id,
                economic_impact_score=ai_data['impact_score'] * 0.8,
                military_impact_score=ai_data['impact_score'] * 0.2,
                confidence_score=ai_data['confidence_score']
            )
            session.add(new_event)
            await session.commit()
            
            # Lanzamos discord
            ai_data['drive_url'] = doc.drive_url
            asyncio.create_task(discord_service.notify_new_document(ai_data))
            
            # 🔥 Lanzamos MOTOR DE VIDEO evaluando Configuración Dinámica
            config = get_config()
            video_enabled = config.get("video", {}).get("enabled", True)
            min_impact = config.get("video", {}).get("min_impact_score", 8)
            
            if video_enabled and new_event.economic_impact_score and new_event.economic_impact_score >= min_impact:
                asyncio.create_task(video_generator.generate(doc, new_event))
            
            return True, ai_data
            
        except Exception as e:
            doc.status = "failed"
            doc.last_error = str(e)
            doc.retry_count += 1
            await session.commit()
            logger.error(f"Error procesando Cloud IA para documento {doc.id}: {e}")
            return False, {}

    async def analyze_with_ai(self, text: str) -> Dict[str, Any]:
        if not self.client:
            logger.warning("Cliente de Azure OpenAI no disponible. Usando fallback Mock.")
            return self._mock_analysis()
            
        max_chars = 10000 
        safe_text = text[:max_chars]
        
        prompt = (
            "You are a geopolitical intelligence analyst. Extract structured data from the following document. "
            "Return ONLY a strictly valid JSON dictionary with no markdown formatting.\n"
            "Format:\n"
            "{\n"
            "  \"title\": \"doc title\",\n"
            "  \"country\": \"country name\",\n"
            "  \"category\": \"military, economic, or political\",\n"
            "  \"summary\": \"max 300 words\",\n"
            "  \"impact_score\": 5,\n"
            "  \"confidence_score\": 0.90\n"
            "}\n\n"
            f"Document:\n{safe_text}"
        )
        
        config = get_config()
        temp = config.get("ai", {}).get("temperature", 0.2)
        max_tokens = config.get("ai", {}).get("max_tokens", 800)

        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.AZURE_OPENAI_DEPLOYMENT,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )
                
                content_str = response.choices[0].message.content
                data = json.loads(content_str)
                
                return {
                    "title": data.get("title", "Desconocido"),
                    "country": data.get("country", "Global"),
                    "category": data.get("category", "political"),
                    "summary": data.get("summary", ""),
                    "impact_score": int(data.get("impact_score", 5)),
                    "confidence_score": float(data.get("confidence_score", 0.5)),
                    "type": "situational_report"
                }

            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando JSON (intento {attempt+1}): {e}")
            except Exception as e:
                logger.error(f"Falla de API de Azure OpenAI: {e}")
                
        return self._mock_analysis()

    def _mock_analysis(self) -> Dict[str, Any]:
         return {
            "title": "Mock Analysis", "country": "N/A", "category": "political",
            "summary": "Mock local fallido", "impact_score": 1,
            "confidence_score": 0.1, "type": "error"
        }

document_processor = DocumentProcessor()
