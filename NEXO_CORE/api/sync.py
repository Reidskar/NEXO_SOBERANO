"""
Rutas del Agente RAG — Contrato unificado
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Header as ParamHeader
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from collections import Counter
import logging
import asyncio
import base64
import os
import shutil
import json
import hashlib
import re
import subprocess
import sys
import smtplib
import socket
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
from pathlib import Path

from backend.services.rag_service import get_rag_service
from backend.services.cost_manager import get_cost_manager
from backend.services.unified_cost_tracker import get_cost_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _is_truthy_env(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default)
    return str(value or "").strip().lower() not in {"0", "false", "no", "off"}


def _mask_sensitive_text(value: str) -> str:
    text = str(value)
    replacements = [
        (r"[\w.+\-]+@[\w\-]+\.[\w.\-]+", "<redacted_email>"),
        (r"https://discord\.com/api/webhooks/[^\s\"']+", "https://discord.com/api/webhooks/<redacted>"),
        (r"\bAIza[0-9A-Za-z_\-]{20,}\b", "AIza<redacted>"),
        (r"\bGOCSPX-[0-9A-Za-z_\-]+\b", "GOCSPX-<redacted>"),
        (r"\bsk-[0-9A-Za-z_\-]{16,}\b", "sk-<redacted>"),
        (r"\bya29\.[0-9A-Za-z\-_.]+\b", "ya29.<redacted>"),
        (r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+", r"\1<redacted>"),
        (r"([A-Za-z]:\\Users\\)[^\\\s]+", r"\1<redacted_user>"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


def _sanitize_warroom_payload(obj):
    if isinstance(obj, dict):
        sanitized: Dict = {}
        for key, value in obj.items():
            key_l = str(key).lower()
            if key_l in {
                "password",
                "token",
                "refresh_token",
                "client_secret",
                "api_key",
                "secret",
                "webhook",
                "webhook_url",
                "local_root",
                "auth_dir",
            }:
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = _sanitize_warroom_payload(value)
        return sanitized
    if isinstance(obj, list):
        return [_sanitize_warroom_payload(item) for item in obj]
    if isinstance(obj, str):
        return _mask_sensitive_text(obj)
    return obj

# ════════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC — CONTRATO UNIFICADO
# ════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """Request unificado del agente"""
    query: str = Field(..., description="Pregunta del usuario", min_length=1, max_length=2000)
    mode: str = Field(default="normal", description="Modo: normal|high|fast")
    categoria: Optional[str] = Field(default=None, description="Filtro por categoría")

class QueryResponse(BaseModel):
    """Response unificado del agente"""
    answer: str = Field(..., description="Respuesta de la IA")
    sources: Optional[List[str]] = Field(default=None, description="Fuentes utilizadas")
    tokens_used: Optional[int] = Field(default=None, description="Tokens consumidos (aproximado)")
    chunks_used: Optional[int] = Field(default=None, description="Chunks de documentos usados")
    execution_time_ms: Optional[int] = Field(default=None, description="Tiempo de ejecución ms")
    total_docs: Optional[int] = Field(default=None, description="Total de docs en bóveda")
    presupuesto: Optional[dict] = Field(default=None, description="Estado del presupuesto")
    error: Optional[bool] = Field(default=False, description="¿Hubo error?")


class ConsultarRagRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000)
    usuario_id: Optional[str] = Field(default=None, max_length=128)
    categoria: Optional[str] = Field(default=None, max_length=64)


class AporteFileItem(BaseModel):
    url: str = Field(..., min_length=5, max_length=4096)
    name: Optional[str] = Field(default=None, max_length=255)


class UploadAporteRequest(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=6000)
    usuario: str = Field(..., min_length=1, max_length=120)
    files: List[AporteFileItem] = Field(default_factory=list)

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    rag_loaded: bool
    total_documentos: int
    presupuesto: dict


class SyncRequest(BaseModel):
    """Parámetros de sincronización unificada."""
    dry_run: bool = Field(default=True, description="Si true, no escribe cambios en la nube")
    photos_limit: int = Field(default=20, ge=0, le=100, description="Máximo de elementos desde Google Photos")
    drive_limit: int = Field(default=50, ge=0, le=500, description="Máximo de archivos recientes a clasificar en Drive")
    onedrive_limit: int = Field(default=20, ge=0, le=200, description="Máximo de archivos recientes desde OneDrive")
    onedrive_max_mb: int = Field(default=20, ge=1, le=1024, description="Tamaño máximo por archivo de OneDrive a importar")
    youtube_per_channel: int = Field(default=10, ge=0, le=50, description="Máximo de videos por canal YouTube")
    youtube_channels: Optional[List[str]] = Field(default=None, description="IDs de canales de YouTube a monitorear")
    drive_include_trashed: bool = Field(default=True, description="Si true, revisa también papelera de Drive")
    drive_full_scan: bool = Field(default=True, description="Si true, pagina todas las carpetas/archivos de Drive")
    drive_auto_rename: bool = Field(default=True, description="Si true, normaliza nombres antes de clasificar")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Reintentos automáticos por operación")
    retry_backoff_seconds: float = Field(default=1.2, ge=0.1, le=10, description="Backoff base entre reintentos")


class SyncResponse(BaseModel):
    ok: bool
    dry_run: bool
    result: dict


class YouTubeRecentRequest(BaseModel):
    channel_id: str = Field(..., min_length=5, max_length=64)
    max_results: int = Field(default=20, ge=1, le=50)
    published_after_iso: Optional[str] = Field(default=None)


class YouTubeTranscriptRequest(BaseModel):
    video_id: str = Field(..., min_length=5, max_length=64)
    languages: Optional[List[str]] = Field(default=None)
    save_to_documentos: bool = Field(default=True)


class YouTubeUploadRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(default="", max_length=5000)
    file_b64: str = Field(..., description="Contenido MP4 en base64")
    filename: str = Field(default="resumen.mp4", max_length=128)
    tags: Optional[List[str]] = Field(default=None)
    privacy_status: str = Field(default="unlisted")
    category_id: str = Field(default="25")


class YouTubeAuthRequest(BaseModel):
    upload_scope: bool = Field(default=False, description="false=readonly, true=youtube.upload")


class DriveAuthRequest(BaseModel):
    write_scope: bool = Field(default=True, description="true usa https://www.googleapis.com/auth/drive")


class PhotosAuthRequest(BaseModel):
    include_drive_write: bool = Field(
        default=False,
        description="true genera token combinado Drive(write)+Photos para sync unificado",
    )


class CredentialAutopilotRequest(BaseModel):
    auto_apply: bool = Field(default=True, description="Si true, aplica auto-fixes seguros en .env")


class DriveListRequest(BaseModel):
    folder_id: str = Field(..., min_length=3, max_length=256)
    max_results: int = Field(default=50, ge=1, le=1000)


class DriveMoveRequest(BaseModel):
    file_id: str = Field(..., min_length=3, max_length=256)
    target_folder_id: str = Field(..., min_length=3, max_length=256)


class DriveRenameRequest(BaseModel):
    file_id: str = Field(..., min_length=3, max_length=256)
    new_name: str = Field(..., min_length=1, max_length=255)


class DriveTrashRequest(BaseModel):
    file_id: str = Field(..., min_length=3, max_length=256)
    trashed: bool = Field(default=True)


class DriveDeleteRequest(BaseModel):
    file_id: str = Field(..., min_length=3, max_length=256)


class DriveEnsureFolderRequest(BaseModel):
    path_parts: List[str] = Field(..., min_length=1, description="Ruta de carpetas en Drive")
    parent_id: str = Field(default="root", min_length=1, max_length=256)


class DriveUploadBase64Request(BaseModel):
    folder_id: str = Field(..., min_length=3, max_length=256)
    filename: str = Field(..., min_length=1, max_length=255)
    file_b64: str = Field(..., description="Contenido del archivo en base64")


class YouTubeDailyResumeRequest(BaseModel):
    dry_run: bool = Field(default=True)
    max_scan: int = Field(default=50, ge=1, le=300)
    privacy_status: str = Field(default="unlisted")


class UnifiedSyncRunRequest(BaseModel):
    dry_run: bool = Field(default=False)
    photos_limit: int = Field(default=50, ge=0, le=100)
    drive_limit: int = Field(default=300, ge=0, le=500)
    onedrive_limit: int = Field(default=100, ge=0, le=200)
    onedrive_max_mb: int = Field(default=50, ge=1, le=1024)
    youtube_per_channel: int = Field(default=10, ge=0, le=50)
    youtube_channels: Optional[List[str]] = Field(default=None)
    drive_include_trashed: bool = Field(default=True)
    drive_full_scan: bool = Field(default=True)
    drive_auto_rename: bool = Field(default=True)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_backoff_seconds: float = Field(default=1.2, ge=0.1, le=10)


class XPostRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=280)
    media_path: Optional[str] = Field(default=None, max_length=1024)


class XSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    limit: int = Field(default=10, ge=1, le=50)


class XMentionsRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    since_id: Optional[str] = Field(default=None, max_length=64)
    username: Optional[str] = Field(default=None, max_length=64)


class GrokConsultRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default="grok-beta", min_length=3, max_length=64)


class XMonitorRunRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    username: Optional[str] = Field(default=None, max_length=64)


class GoogleStitchConnectRequest(BaseModel):
    webhook_url: str = Field(..., min_length=8, max_length=2048)
    api_key: Optional[str] = Field(default=None, max_length=512)


class GoogleStitchEventRequest(BaseModel):
    event_type: str = Field(..., min_length=2, max_length=128)
    payload: Dict = Field(default_factory=dict)


class GrokShareCodeRequest(BaseModel):
    question: str = Field(
        default="Analiza esta arquitectura y debate mejoras de integración, observabilidad y confiabilidad.",
        min_length=10,
        max_length=4000,
    )
    max_tweets: int = Field(default=5, ge=1, le=12)


class FodaCriticalRequest(BaseModel):
    objetivo: str = Field(
        default="Evaluar críticamente el estado actual del sistema NEXO y priorizar mejoras de arquitectura, seguridad, UX y operación.",
        min_length=10,
        max_length=2000,
    )
    contexto_extra: Optional[str] = Field(default=None, max_length=4000)
    incluir_evolucion: bool = Field(default=True)
    incluir_alertas: bool = Field(default=True)
    decisor_final: str = Field(default="claude", pattern="^(claude|grok|gemini|openai)$")
    modo_ahorro: bool = Field(default=True, description="Si true, usa solo el decisor final para reducir costo")


class MobilePackageEmailRequest(BaseModel):
    recipient: Optional[str] = Field(default=None, max_length=254)
    subject: Optional[str] = Field(default="NEXO SOBERANO - App móvil y enlaces de descarga", max_length=200)

class CommandRequest(BaseModel):
    command: str


# ════════════════════════════════════════════════════════════════════
# RUTAS EXTRAÍDAS: sync
# ════════════════════════════════════════════════════════════════════

@router.post("/sync/unificado", response_model=SyncResponse)
async def sync_unificado(request: SyncRequest) -> SyncResponse:
    """Sincroniza y clasifica automáticamente Google Photos, Drive y OneDrive en Drive."""
    try:
        from NEXO_CORE.worker.tasks import sync_drive_onedrive_task
        
        # Enviar la tarea a la cola de Celery para evitar bloqueo de hilos
        task = sync_drive_onedrive_task.delay(request.dict())
        
        return SyncResponse(
            ok=True, 
            dry_run=request.dry_run, 
            result={
                "task_id": task.id,
                "status": "processing",
                "message": "Sincronización enviada al worker de Celery en segundo plano."
            }
        )
    except Exception as e:
        logger.error(f"Error en /sync/unificado (Celery dispatch): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error encolando sincronización unificada: {str(e)}")

@router.get("/drive/recent")
async def drive_recent(max_results: int = 10):
    """Lista recientes de Drive para pipeline de resumen diario."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from backend.services.drive_youtube_service import list_recent_files_in_root

        files = list_recent_files_in_root(max_results=max_results)
        return {"ok": True, "count": len(files), "files": files}
    except Exception as e:
        logger.error(f"Error en /drive/recent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listando recientes de Drive: {str(e)}")

@router.get("/photos/recent")
def photos_recent():
    """Lista los elementos recientes de Google Photos."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import list_recent_photos

        photos = list_recent_photos(max_results=20)
        return {"photos": photos}
    except Exception as e:
        logger.error(f"Error en /photos/recent: {e}")
        return {"error": str(e), "photos": []}

@router.get("/onedrive/recent")
def onedrive_recent():
    """Lista elementos recientes de OneDrive."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.microsoft_connector import MicrosoftConnector
        from services.connectors.local_onedrive_connector import list_recent_local_onedrive_files, resolve_onedrive_local_root

        mc = MicrosoftConnector()
        files = mc.list_recent_files(top=20)
        source = "graph"
        if not files:
            files = list_recent_local_onedrive_files(top=20)
            if files:
                source = "local_onedrive"

        return {
            "files": files,
            "source": source,
            "local_root": str(resolve_onedrive_local_root() or ""),
        }
    except Exception as e:
        logger.error(f"Error en /onedrive/recent: {e}")
        return {"error": str(e), "files": []}

@router.post("/youtube/recent")
async def youtube_recent(request: YouTubeRecentRequest):
    """Lista videos recientes de un canal de YouTube para monitoreo paralelo."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.comunidad.youtube_reader import list_recent_channel_videos

        videos = list_recent_channel_videos(
            channel_id=request.channel_id,
            max_results=request.max_results,
            published_after_iso=request.published_after_iso,
        )
        return {"ok": True, "count": len(videos), "videos": videos}
    except Exception as e:
        logger.error(f"Error en /youtube/recent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error consultando YouTube: {str(e)}")

@router.post("/youtube/transcript")
async def youtube_transcript(request: YouTubeTranscriptRequest):
    """Obtiene transcripción de video y opcionalmente la guarda para RAG."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from services.comunidad.youtube_reader import get_video_transcript, save_transcript_to_json
        from backend import config

        transcript = get_video_transcript(request.video_id, languages=request.languages)
        saved_file = None
        if request.save_to_documentos and transcript.get("ok"):
            saved_path = save_transcript_to_json(request.video_id, transcript, config.DOCS_DIR)
            saved_file = str(saved_path)

        return {"ok": bool(transcript.get("ok")), "transcript": transcript, "saved_file": saved_file}
    except Exception as e:
        logger.error(f"Error en /youtube/transcript: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo transcripción: {str(e)}")

