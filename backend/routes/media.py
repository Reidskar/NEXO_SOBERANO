from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import logging
from NEXO_CORE.services.media_ingestion_service import media_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/media", tags=["media"])


# --- YouTube OSINT ---
class YoutubeIngestRequest(BaseModel):
    url: str
    topic: Optional[str] = "general"

class YoutubeIngestResponse(BaseModel):
    status: str
    chunks: int
    video_id: Optional[str]
    duplicate: bool

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


@router.post("/ingest-youtube", response_model=YoutubeIngestResponse)
async def ingest_youtube(request: YoutubeIngestRequest):
    """Ingiere un video de YouTube y lo indexa en Qdrant (colección youtube_osint)."""
    try:
        from backend.services.osint_video_extractor import ingest_youtube_video
        result = ingest_youtube_video(url_or_id=request.url, topic=request.topic)
    except Exception as e:
        logger.error(f"Error en ingest-youtube: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Error desconocido"))

    return YoutubeIngestResponse(
        status=result["status"],
        chunks=result["indexed"],
        video_id=result["video_id"],
        duplicate=result["duplicate"],
    )
