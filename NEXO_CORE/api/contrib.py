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

router = APIRouter(prefix="/api/contrib", tags=["contrib"])


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
# RUTAS EXTRAÍDAS: contrib
# ════════════════════════════════════════════════════════════════════

@router.post("/drive/upload-aporte")
async def drive_upload_aporte(request: UploadAporteRequest):
    """Recibe aportes comunitarios y los guarda en carpeta de cuarentena en Drive."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import ensure_drive_folder_path, upload_bytes_to_drive

        timestamp = datetime.now(timezone.utc).isoformat()
        aporte_seed = f"{request.usuario}|{request.contenido}|{timestamp}"
        aporte_id = hashlib.sha1(aporte_seed.encode("utf-8")).hexdigest()[:16]

        urls = [item.url for item in request.files]
        blocked_reason = _detect_direct_harm(request.contenido, urls)
        if blocked_reason:
            return {
                "ok": False,
                "status": "rechazado",
                "motivo": blocked_reason,
                "aporte_id": aporte_id,
            }

        now = datetime.now(timezone.utc)
        path_parts = [
            "NEXO_SOBERANO",
            "Cuarentena",
            "Aportes_Comunidad",
            str(now.year),
            f"{now.month:02d}",
        ]
        folder_id = ensure_drive_folder_path(path_parts, parent_id="root")

        payload = {
            "aporte_id": aporte_id,
            "usuario": request.usuario,
            "contenido": request.contenido,
            "files": [item.model_dump() for item in request.files],
            "timestamp": timestamp,
            "source": "discord",
            "status": "cuarentena",
        }
        filename = f"aporte_{aporte_id}.json"
        uploaded = upload_bytes_to_drive(
            file_bytes=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            filename=filename,
            mime_type="application/json",
            parent_id=folder_id,
            app_properties={
                "nexo_type": "community_aporte",
                "aporte_id": aporte_id,
                "usuario": request.usuario,
                "status": "cuarentena",
            },
        )

        file_id = uploaded.get("id")
        return {
            "ok": True,
            "status": "recibido",
            "aporte_id": aporte_id,
            "folder_id": folder_id,
            "file_id": file_id,
            "drive_link": f"https://drive.google.com/file/d/{file_id}/view" if file_id else None,
        }
    except Exception as e:
        logger.error(f"Error en /agente/drive/upload-aporte: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error subiendo aporte a Drive: {str(e)}")

