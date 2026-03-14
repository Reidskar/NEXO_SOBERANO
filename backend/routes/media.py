from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import logging
from NEXO_CORE.services.media_ingestion_service import media_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/media", tags=["media"])

class IngestRequest(BaseModel):
    file_path: str
    metadata: Optional[dict] = None

class IngestResponse(BaseModel):
    task_id: str
    status: str

@router.post("/ingestar", response_model=IngestResponse)
async def ingestar_media(request: IngestRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
    async def process():
        try:
            texto = media_service.transcribir(request.file_path, task_id=task_id)
            # Aquí se integraría con el RAG en el futuro
            logger.info(f"Transcripción completada para {task_id}: {texto[:100]}...")
        except Exception as e:
            logger.error(f"Fallo en background task {task_id}: {e}")

    background_tasks.add_task(process)
    return IngestResponse(task_id=task_id, status="iniciado")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    status = media_service.get_status(task_id)
    return {"task_id": task_id, "status": status}

@router.get("/status")
async def global_status():
    return {"service": "media_ingestion", "online": True}
