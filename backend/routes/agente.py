"""
Rutas del Agente RAG — Contrato unificado
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging
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
from datetime import datetime, timezone
from pathlib import Path

from backend.services.rag_service import get_rag_service
from backend.services.cost_manager import get_cost_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agente", tags=["agente"])

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


class MobilePackageEmailRequest(BaseModel):
    recipient: Optional[str] = Field(default=None, max_length=254)
    subject: Optional[str] = Field(default="NEXO SOBERANO - App móvil y enlaces de descarga", max_length=200)

# ════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════

@router.post("/consultar", response_model=QueryResponse)
async def consultar(request: QueryRequest) -> QueryResponse:
    """
    Endpoint principal del agente RAG.
    
    Consulta la bóveda de documentos y genera respuesta con IA.
    """
    try:
        # Validar presupuesto
        cost_mgr = get_cost_manager()
        if not cost_mgr.puede_operar():
            raise HTTPException(
                status_code=429,
                detail="Presupuesto diario de tokens Gemini excedido"
            )

        # Ejecutar consulta RAG
        rag = get_rag_service()
        resultado = rag.consultar(request.query, request.categoria)

        # Mapear a respuesta unificada
        tokens_aproximado = (len(request.query) + len(resultado.get("respuesta", ""))) // 4

        return QueryResponse(
            answer=resultado.get("respuesta", ""),
            sources=resultado.get("fuentes"),
            tokens_used=tokens_aproximado,
            chunks_used=resultado.get("chunks_usados"),
            execution_time_ms=resultado.get("ms"),
            total_docs=resultado.get("total_docs"),
            presupuesto=resultado.get("presupuesto"),
            error=resultado.get("error", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /agente/consultar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/consultar-rag")
async def consultar_rag(request: ConsultarRagRequest):
    """Endpoint de compatibilidad para clientes externos (Discord/Web) con formato Tutor de Evidencia."""
    try:
        cost_mgr = get_cost_manager()
        if not cost_mgr.puede_operar():
            raise HTTPException(status_code=429, detail="Presupuesto diario de tokens Gemini excedido")

        prompt = (
            "Responde como Tutor de Evidencia de forma objetiva y verificable. "
            "Estructura obligatoria: Antecedentes, Situación actual, Evidencia directa (solo links y hechos). "
            "Si faltan datos, dilo explícitamente. "
            f"Pregunta del usuario: {request.pregunta}"
        )

        rag = get_rag_service()
        resultado = rag.consultar(prompt, request.categoria)

        return {
            "ok": not bool(resultado.get("error", False)),
            "respuesta": resultado.get("respuesta", "No encontré evidencia suficiente."),
            "fuentes": resultado.get("fuentes") or [],
            "chunks_usados": resultado.get("chunks_usados", 0),
            "total_docs": resultado.get("total_docs", 0),
            "error": bool(resultado.get("error", False)),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /agente/consultar-rag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno consultar-rag: {str(e)}")


def _detect_direct_harm(content: str, file_urls: List[str]) -> Optional[str]:
    lowered = (content or "").lower()

    spam_patterns = [r"(.)\1{9,}", r"(https?://\S+\s*){6,}"]
    for pattern in spam_patterns:
        if re.search(pattern, lowered):
            return "spam"

    doxxing_patterns = [
        r"\b\d{8,}\b",  # secuencias numéricas largas
        r"[\w\.-]+@[\w\.-]+\.\w+",  # emails
        r"\b(?:direcci[oó]n|domicilio|rut|dni|pasaporte)\b",
    ]
    for pattern in doxxing_patterns:
        if re.search(pattern, lowered):
            return "doxxing"

    malware_terms = [".exe", ".bat", ".scr", "payload", "stealer", "keylogger", "ransomware"]
    if any(term in lowered for term in malware_terms):
        return "malware"

    for url in file_urls:
        u = (url or "").lower()
        if any(ext in u for ext in [".exe", ".bat", ".scr", ".dll", ".js"]):
            return "malware"

    return None


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


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check del agente RAG"""
    try:
        rag = get_rag_service()
        estado = rag.estado()
        
        return HealthResponse(
            status="ok" if estado.get("rag_loaded") else "degraded",
            rag_loaded=estado.get("rag_loaded", False),
            total_documentos=estado.get("total_documentos", 0),
            presupuesto=estado.get("presupuesto", {}),
        )
    except Exception as e:
        logger.error(f"Error en /agente/health: {e}")
        raise HTTPException(status_code=500, detail="Error en health check")


@router.get("/presupuesto")
async def presupuesto():
    """Estado actual del presupuesto Gemini"""
    try:
        cost_mgr = get_cost_manager()
        return cost_mgr.estado()
    except Exception as e:
        logger.error(f"Error obteniendo presupuesto: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo presupuesto")


@router.get("/drive/recent")
def drive_recent():
    """Lista los archivos más recientes de Google Drive usando el conector seguro."""
    try:
        # Import local para evitar circular imports
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import list_recent_files
        
        files = list_recent_files(max_results=10)
        return {"files": files}
    except Exception as e:
        logger.error(f"Error en /drive/recent: {e}")
        return {"error": str(e), "files": []}


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


@router.get("/historial-costos")
async def historial_costos():
    """Historial de costos últimos 7 días"""
    try:
        cost_mgr = get_cost_manager()
        return {"historial": cost_mgr.historial_7_dias()}
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo historial")


@router.post("/sync/unificado", response_model=SyncResponse)
async def sync_unificado(request: SyncRequest) -> SyncResponse:
    """Sincroniza y clasifica automáticamente Google Photos, Drive y OneDrive en Drive."""
    try:
        import asyncio
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from backend.services.unified_sync_service import run_unified_sync

        timeout_seconds = int(os.getenv("NEXO_SYNC_UNIFICADO_TIMEOUT", "900"))
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_unified_sync,
                dry_run=request.dry_run,
                photos_limit=request.photos_limit,
                drive_limit=request.drive_limit,
                onedrive_limit=request.onedrive_limit,
                onedrive_max_mb=request.onedrive_max_mb,
                youtube_per_channel=request.youtube_per_channel,
                youtube_channels=request.youtube_channels,
                drive_include_trashed=request.drive_include_trashed,
                drive_full_scan=request.drive_full_scan,
                drive_auto_rename=request.drive_auto_rename,
                retry_attempts=request.retry_attempts,
                retry_backoff_seconds=request.retry_backoff_seconds,
            ),
            timeout=timeout_seconds,
        )
        return SyncResponse(ok=bool(result.get("ok", False)), dry_run=request.dry_run, result=result)
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Timeout en sincronización unificada. Reduce límites o aumenta NEXO_SYNC_UNIFICADO_TIMEOUT.",
        )
    except Exception as e:
        logger.error(f"Error en /sync/unificado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en sincronización unificada: {str(e)}")


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


@router.post("/youtube/upload-summary")
async def youtube_upload_summary(request: YouTubeUploadRequest):
    """Sube un clip/resumen diario al canal autenticado en YouTube."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.comunidad.youtube_reader import upload_video_summary

        file_bytes = base64.b64decode(request.file_b64)
        result = upload_video_summary(
            title=request.title,
            description=request.description,
            file_bytes=file_bytes,
            filename=request.filename,
            tags=request.tags,
            privacy_status=request.privacy_status,
            category_id=request.category_id,
        )
        return {"ok": bool(result.get("ok")), "result": result}
    except Exception as e:
        logger.error(f"Error en /youtube/upload-summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error subiendo resumen a YouTube: {str(e)}")


@router.post("/youtube/upload-summary-file")
async def youtube_upload_summary_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    tags: Optional[str] = Form(None),
    privacy_status: str = Form("unlisted"),
    category_id: str = Form("25"),
):
    """Sube un resumen a YouTube vía multipart/form-data (sin base64)."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.comunidad.youtube_reader import upload_video_summary

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        tags_list = [t.strip() for t in tags.split(",")] if tags else None
        result = upload_video_summary(
            title=title,
            description=description,
            file_bytes=file_bytes,
            filename=file.filename or "resumen.mp4",
            tags=tags_list,
            privacy_status=privacy_status,
            category_id=category_id,
        )
        return {"ok": bool(result.get("ok")), "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /youtube/upload-summary-file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo a YouTube: {str(e)}")


@router.post("/youtube/authorize")
async def youtube_authorize(request: YouTubeAuthRequest):
    """Inicia OAuth interactivo para generar tokens persistentes de YouTube."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.comunidad.youtube_reader import authorize_youtube_interactive

        result = authorize_youtube_interactive(upload=request.upload_scope)
        return {"ok": bool(result.get("ok")), "result": result}
    except Exception as e:
        logger.error(f"Error en /youtube/authorize: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error autorizando YouTube: {str(e)}")


@router.post("/youtube/create-client-secrets")
async def youtube_create_client_secrets():
    """Crea client_secrets de YouTube desde YOUTUBE_CLIENT_ID/YOUTUBE_CLIENT_SECRET."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.comunidad.youtube_reader import create_youtube_client_secrets_from_env

        path = create_youtube_client_secrets_from_env()
        return {"ok": True, "client_secrets_file": str(path)}
    except Exception as e:
        logger.error(f"Error en /youtube/create-client-secrets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creando client_secrets: {str(e)}")


@router.post("/drive/create-client-secrets")
async def drive_create_client_secrets():
    """Crea client_secrets de Drive desde DRIVE_CLIENT_ID/DRIVE_CLIENT_SECRET."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import create_drive_client_secrets_from_env

        path = create_drive_client_secrets_from_env()
        return {"ok": True, "client_secrets_file": str(path)}
    except Exception as e:
        logger.error(f"Error en /drive/create-client-secrets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creando client_secrets Drive: {str(e)}")


@router.post("/drive/authorize")
async def drive_authorize(request: DriveAuthRequest):
    """Inicia OAuth interactivo para generar token persistente de Drive."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import authorize_drive_interactive

        result = authorize_drive_interactive(require_write=request.write_scope)
        return {"ok": bool(result.get("ok")), "result": result}
    except Exception as e:
        logger.error(f"Error en /drive/authorize: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error autorizando Drive: {str(e)}")


@router.post("/photos/authorize")
async def photos_authorize(request: PhotosAuthRequest):
    """Inicia OAuth interactivo para generar token persistente de Google Photos."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import authorize_photos_interactive

        result = authorize_photos_interactive(include_drive_write=request.include_drive_write)
        return {"ok": bool(result.get("ok")), "result": result}
    except Exception as e:
        logger.error(f"Error en /photos/authorize: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error autorizando Google Photos: {str(e)}")


@router.post("/drive/list")
async def drive_list(request: DriveListRequest):
    """Lista archivos de una carpeta específica de Drive."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import list_files_in_folder

        files = list_files_in_folder(request.folder_id, max_results=request.max_results)
        return {"ok": True, "count": len(files), "files": files}
    except Exception as e:
        logger.error(f"Error en /drive/list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listando Drive: {str(e)}")


@router.post("/drive/ensure-folder")
async def drive_ensure_folder(request: DriveEnsureFolderRequest):
    """Crea (si no existe) una ruta de carpetas en Drive y retorna el folder_id final."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import ensure_drive_folder_path

        folder_id = ensure_drive_folder_path(request.path_parts, parent_id=request.parent_id)
        return {"ok": True, "folder_id": folder_id, "path_parts": request.path_parts}
    except Exception as e:
        logger.error(f"Error en /drive/ensure-folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creando/buscando carpeta Drive: {str(e)}")


@router.post("/drive/upload")
async def drive_upload(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    name: Optional[str] = Form(None),
):
    """Sube un archivo local a una carpeta de Drive."""
    try:
        import sys
        from pathlib import Path
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import upload_local_file_to_drive

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        suffix = Path(file.filename or "upload.bin").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        uploaded = upload_local_file_to_drive(tmp_path, parent_id=folder_id, name=name or file.filename)
        return {"ok": True, "file": uploaded}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /drive/upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error subiendo a Drive: {str(e)}")


@router.post("/drive/upload-b64")
async def drive_upload_b64(request: DriveUploadBase64Request):
    """Sube archivo a Drive enviando contenido base64 (útil para PowerShell/automatización)."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import upload_bytes_to_drive

        file_bytes = base64.b64decode(request.file_b64)
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        uploaded = upload_bytes_to_drive(
            file_bytes=file_bytes,
            filename=request.filename,
            mime_type="application/octet-stream",
            parent_id=request.folder_id,
        )
        return {"ok": True, "file": uploaded}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /drive/upload-b64: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error subiendo base64 a Drive: {str(e)}")


@router.post("/drive/move")
async def drive_move(request: DriveMoveRequest):
    """Mueve un archivo de Drive a otra carpeta."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import move_drive_file_to_folder

        moved = move_drive_file_to_folder(request.file_id, request.target_folder_id)
        return {"ok": True, "file": moved}
    except Exception as e:
        logger.error(f"Error en /drive/move: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error moviendo archivo en Drive: {str(e)}")


@router.post("/drive/rename")
async def drive_rename(request: DriveRenameRequest):
    """Renombra archivo en Drive."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import rename_drive_file

        renamed = rename_drive_file(request.file_id, request.new_name)
        return {"ok": True, "file": renamed}
    except Exception as e:
        logger.error(f"Error en /drive/rename: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error renombrando archivo en Drive: {str(e)}")


@router.post("/drive/trash")
async def drive_trash(request: DriveTrashRequest):
    """Envía archivo a papelera o lo restaura."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import trash_drive_file

        trashed = trash_drive_file(request.file_id, trashed=request.trashed)
        return {"ok": True, "file": trashed}
    except Exception as e:
        logger.error(f"Error en /drive/trash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error enviando a papelera en Drive: {str(e)}")


@router.post("/drive/delete")
async def drive_delete(request: DriveDeleteRequest):
    """Elimina permanentemente archivo en Drive."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from services.connectors.google_connector import delete_drive_file

        result = delete_drive_file(request.file_id)
        return {"ok": True, "result": result}
    except Exception as e:
        logger.error(f"Error en /drive/delete: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo en Drive: {str(e)}")


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


@router.post("/youtube/daily-resume")
async def youtube_daily_resume(request: YouTubeDailyResumeRequest):
    """Pipeline diario: Drive resumen -> video -> YouTube."""
    try:
        import asyncio
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from backend.services.drive_youtube_service import daily_resume_pipeline

        timeout_seconds = int(os.getenv("NEXO_DAILY_RESUME_TIMEOUT", "600"))
        result = await asyncio.wait_for(
            asyncio.to_thread(
                daily_resume_pipeline,
                request.dry_run,
                request.max_scan,
                request.privacy_status,
            ),
            timeout=timeout_seconds,
        )
        return {"ok": bool(result.get("ok")), "result": result}
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Timeout ejecutando resumen diario Drive->YouTube. Reintenta o aumenta NEXO_DAILY_RESUME_TIMEOUT.",
        )
    except Exception as e:
        logger.error(f"Error en /youtube/daily-resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error ejecutando resumen diario: {str(e)}")


def _ingest_x_mentions_to_drive(mentions: List[Dict], username: str) -> Dict:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from services.connectors.google_connector import ensure_drive_folder_path, upload_bytes_to_drive

    now = datetime.now(timezone.utc)
    path_parts = [
        "NEXO_SOBERANO",
        "Cuarentena",
        "Aportes_X",
        str(now.year),
        f"{now.month:02d}",
    ]
    folder_id = ensure_drive_folder_path(path_parts, parent_id="root")

    uploaded_items: List[Dict] = []
    for item in mentions:
        tweet_id = str(item.get("id") or "")
        seed = f"x|{username}|{tweet_id}|{item.get('created_at') or ''}"
        aporte_id = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]

        payload = {
            "aporte_id": aporte_id,
            "source": "x_mentions",
            "username": username,
            "tweet": item,
            "ingested_at": now.isoformat(),
            "status": "cuarentena",
        }
        filename = f"x_aporte_{tweet_id or aporte_id}.json"
        uploaded = upload_bytes_to_drive(
            file_bytes=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            filename=filename,
            mime_type="application/json",
            parent_id=folder_id,
            app_properties={
                "nexo_type": "x_mention",
                "aporte_id": aporte_id,
                "tweet_id": tweet_id,
                "status": "cuarentena",
            },
        )

        uploaded_items.append(
            {
                "aporte_id": aporte_id,
                "tweet_id": tweet_id,
                "file_id": uploaded.get("id"),
                "drive_link": f"https://drive.google.com/file/d/{uploaded.get('id')}/view" if uploaded.get("id") else None,
            }
        )

    return {"folder_id": folder_id, "uploaded": uploaded_items}


@router.post("/x/post")
async def x_post(request: XPostRequest):
    """Publica en X (Twitter) usando credenciales del entorno."""
    try:
        from backend.services.x_publisher import post_to_x

        result = post_to_x(request.text, request.media_path)
        return {"ok": bool(result.get("ok")), "result": result}
    except Exception as e:
        logger.error(f"Error en /x/post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error publicando en X: {str(e)}")


@router.post("/x/search")
async def x_search(request: XSearchRequest):
    """Búsqueda reciente en X por query (threads, menciones públicas, señales)."""
    try:
        from backend.services.x_publisher import search_x_recent

        result = search_x_recent(query=request.query, limit=request.limit)
        return result
    except Exception as e:
        logger.error(f"Error en /x/search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error buscando en X: {str(e)}")


@router.post("/x/mentions")
async def x_mentions(request: XMentionsRequest):
    """Lee menciones recientes al usuario configurado en X."""
    try:
        from backend.services.x_publisher import fetch_mentions

        result = fetch_mentions(limit=request.limit, since_id=request.since_id, username=request.username)
        return result
    except Exception as e:
        logger.error(f"Error en /x/mentions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error leyendo menciones X: {str(e)}")


@router.post("/x/ingest-mentions")
async def x_ingest_mentions(request: XMentionsRequest):
    """Obtiene menciones de X y las sube a cuarentena Drive para análisis posterior."""
    try:
        from backend.services.x_publisher import fetch_mentions

        mentions_result = fetch_mentions(limit=request.limit, since_id=request.since_id, username=request.username)
        mentions = mentions_result.get("mentions") or []
        username = mentions_result.get("username") or (request.username or "unknown")

        ingestion = _ingest_x_mentions_to_drive(mentions, username=username)
        return {
            "ok": True,
            "count": len(mentions),
            "username": username,
            "mentions": mentions,
            "drive": ingestion,
            "next_since_id": mentions_result.get("newest_id"),
        }
    except Exception as e:
        logger.error(f"Error en /x/ingest-mentions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error ingiriendo menciones X: {str(e)}")


@router.post("/grok/consult")
async def grok_consult(request: GrokConsultRequest):
    """Consulta Grok vía xAI API cuando hay acceso; fallback descriptivo si no está configurado."""
    try:
        from backend.services.x_publisher import ask_grok

        result = ask_grok(question=request.question, model=request.model)
        return result
    except Exception as e:
        logger.error(f"Error en /grok/consult: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error consultando Grok: {str(e)}")


@router.post("/x/monitor-once")
async def x_monitor_once(request: XMonitorRunRequest):
    """Ejecuta una ronda de monitoreo X/Grok e ingesta a Drive cuarentena."""
    try:
        from backend.services.x_monitor import monitor_x_once

        result = monitor_x_once(limit=request.limit, username=request.username)
        return result
    except Exception as e:
        logger.error(f"Error en /x/monitor-once: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en monitor X/Grok: {str(e)}")


@router.get("/x/monitor-status")
async def x_monitor_status():
    """Estado y último reporte del monitor X/Grok."""
    logs_dir = _logs_dir()
    status_path = logs_dir / "x_monitor_status.json"
    report_path = logs_dir / "x_monitor_last.json"
    state_path = logs_dir / "x_monitor_state.json"

    return {
        "ok": True,
        "status": _safe_json_read(status_path),
        "report": _safe_json_read(report_path),
        "state": _safe_json_read(state_path),
        "status_file": str(status_path),
        "report_file": str(report_path),
        "state_file": str(state_path),
    }


@router.get("/google-stitch/status")
async def google_stitch_status():
    """Estado de configuración y prueba de Google Stitch (webhook)."""
    try:
        from backend.services.google_stitch_service import get_stitch_config

        cfg = get_stitch_config()
        return {
            "ok": True,
            "configured": cfg.get("configured", False),
            "source": cfg.get("source"),
            "webhook_url": cfg.get("webhook_url_masked"),
            "api_key": cfg.get("api_key_masked"),
        }
    except Exception as e:
        logger.error(f"Error en /google-stitch/status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error consultando Google Stitch: {str(e)}")


@router.post("/google-stitch/connect")
async def google_stitch_connect(request: GoogleStitchConnectRequest):
    """Guarda configuración de Google Stitch en logs/google_stitch_config.json."""
    try:
        from backend.services.google_stitch_service import save_stitch_config

        cfg = save_stitch_config(request.webhook_url, request.api_key)
        return {
            "ok": True,
            "configured": cfg.get("configured", False),
            "source": cfg.get("source"),
            "webhook_url": cfg.get("webhook_url_masked"),
            "api_key": cfg.get("api_key_masked"),
        }
    except Exception as e:
        logger.error(f"Error en /google-stitch/connect: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error configurando Google Stitch: {str(e)}")


@router.post("/google-stitch/test")
async def google_stitch_test():
    """Envía ping de prueba a Google Stitch."""
    try:
        from backend.services.google_stitch_service import test_stitch_connection

        result = test_stitch_connection()
        return result
    except Exception as e:
        logger.error(f"Error en /google-stitch/test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error probando Google Stitch: {str(e)}")


@router.post("/google-stitch/push")
async def google_stitch_push(request: GoogleStitchEventRequest):
    """Empuja evento operacional hacia Google Stitch."""
    try:
        from backend.services.google_stitch_service import push_event_to_stitch

        event = {
            "event_type": request.event_type,
            "source": "nexo_soberano",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": request.payload,
        }
        return push_event_to_stitch(event)
    except Exception as e:
        logger.error(f"Error en /google-stitch/push: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error enviando evento a Google Stitch: {str(e)}")


@router.post("/grok/share-code")
async def grok_share_code(request: GrokShareCodeRequest):
    """Comparte contexto técnico del código con Grok vía X (hilo) o retorna prompt listo para uso manual."""
    try:
        paths = _extractor_paths()
        root = _workspace_root()
        script_path = root / "scripts" / "run_code_extractor.py"

        if not paths["output"].exists() and script_path.exists():
            subprocess.run([sys.executable, str(script_path)], cwd=str(root), check=False)

        if not paths["output"].exists():
            raise HTTPException(status_code=404, detail="No existe contexto extraído para compartir")

        context_text = paths["output"].read_text(encoding="utf-8", errors="ignore")
        context_text = (context_text or "").strip()
        if not context_text:
            raise HTTPException(status_code=400, detail="Contexto extraído vacío")

        report = _safe_json_read(paths["report"])
        files_scanned = report.get("files_scanned", "n/d")
        bytes_written = report.get("bytes_written", "n/d")

        header = (
            "@grok Debate técnico NEXO SOBERANO:\n"
            f"{request.question[:170]}\n"
            f"Contexto: files={files_scanned}, bytes={bytes_written}\n"
            "Responde con mejoras concretas por prioridad."
        )

        chunks: List[str] = []
        max_chunk = 220
        raw_body = context_text[: request.max_tweets * max_chunk]
        for idx in range(0, len(raw_body), max_chunk):
            piece = raw_body[idx: idx + max_chunk].strip()
            if piece:
                chunks.append(piece)
        chunks = chunks[: max(0, request.max_tweets - 1)]

        prompt_manual = (
            f"{request.question}\n\n"
            f"Contexto extraído ({paths['output']}):\n"
            f"{context_text[:3000]}"
        )

        posted_thread = []
        post_error = None
        try:
            from backend.services.x_publisher import post_to_x

            first = post_to_x(header)
            posted_thread.append(first)
            prev_id = first.get("tweet_id")

            for piece in chunks:
                if not prev_id:
                    break
                reply = post_to_x(piece, in_reply_to=prev_id)
                posted_thread.append(reply)
                prev_id = reply.get("tweet_id")
        except Exception as exc:
            post_error = str(exc)

        output_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "question": request.question,
            "output_file": str(paths["output"]),
            "files_scanned": files_scanned,
            "bytes_written": bytes_written,
            "thread_posts": posted_thread,
            "post_error": post_error,
            "prompt_manual": prompt_manual,
        }

        grok_prompt_path = _logs_dir() / "grok_share_prompt.txt"
        grok_prompt_path.write_text(prompt_manual, encoding="utf-8")

        return {
            "ok": True,
            "posted": len(posted_thread) > 0,
            "thread_count": len(posted_thread),
            "thread": posted_thread,
            "post_error": post_error,
            "prompt_file": str(grok_prompt_path),
            "prompt_manual": prompt_manual[:2000],
            "meta": output_payload,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /grok/share-code: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error compartiendo código con Grok: {str(e)}")


def _detect_lan_ip() -> Optional[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        return None
    return None


def _resolve_public_base_url(request: Request) -> str:
    env_base = os.getenv("NEXO_PUBLIC_BASE_URL", "").strip()
    if env_base:
        return env_base.rstrip("/")

    req_base = str(request.base_url).rstrip("/")
    if "127.0.0.1" in req_base or "localhost" in req_base:
        lan_ip = _detect_lan_ip()
        if lan_ip:
            return f"http://{lan_ip}:8000"
    return req_base


def _build_mobile_package(base_url: str) -> Dict:
    base = (base_url or "").rstrip("/")
    links = {
        "app_user": f"{base}/app-user",
        "app_admin": f"{base}/app-admin",
        "control_center": f"{base}/control-center",
        "warroom": f"{base}/warroom",
        "warroom_v3": f"{base}/warroom_v3.html",
        "admin_dashboard": f"{base}/admin_dashboard.html",
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "links": links,
        "install_steps": [
            "Abrir enlace en Chrome/Safari desde el teléfono",
            "Seleccionar 'Agregar a pantalla de inicio'",
            "Permitir notificaciones si se solicitan",
        ],
        "grok": {
            "share_code_endpoint": f"{base}/agente/grok/share-code",
            "prompt_file": str(_logs_dir() / "grok_share_prompt.txt"),
        },
        "qr": {
            "app_user": f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={links.get('app_user')}",
            "app_admin": f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={links.get('app_admin')}",
            "download": f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={base}/app-download",
        }
    }
    return payload


def _write_mobile_package_files(package: Dict) -> Dict:
    logs = _logs_dir()
    json_path = logs / "mobile_app_package.json"
    txt_path = logs / "mobile_app_links.txt"

    json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")

    links = package.get("links", {})
    txt_body = (
        "NEXO SOBERANO - Enlaces de instalación móvil\n\n"
        f"Usuario: {links.get('app_user')}\n"
        f"Admin: {links.get('app_admin')}\n"
        f"Control Center: {links.get('control_center')}\n"
        f"War Room: {links.get('warroom')}\n"
        f"Dashboard: {links.get('admin_dashboard')}\n\n"
        "Para instalar en teléfono: abrir enlace en navegador y usar 'Agregar a pantalla de inicio'.\n"
    )
    txt_path.write_text(txt_body, encoding="utf-8")

    return {"json": json_path, "txt": txt_path}


@router.get("/mobile-package")
async def mobile_package(request: Request):
    """Genera paquete de enlaces móviles (usuario/admin) y devuelve rutas de descarga."""
    base = _resolve_public_base_url(request)
    package = _build_mobile_package(base)
    files = _write_mobile_package_files(package)

    return {
        "ok": True,
        "package": package,
        "download_json": "/agente/mobile-package/download?kind=json",
        "download_txt": "/agente/mobile-package/download?kind=txt",
        "files": {"json": str(files["json"]), "txt": str(files["txt"])},
    }


@router.get("/mobile-package/download")
async def mobile_package_download(kind: str = "txt"):
    """Descarga archivo del paquete móvil (txt/json)."""
    kind = (kind or "txt").lower().strip()
    logs = _logs_dir()
    file_map = {
        "txt": logs / "mobile_app_links.txt",
        "json": logs / "mobile_app_package.json",
    }
    target = file_map.get(kind)
    if not target:
        raise HTTPException(status_code=400, detail="kind inválido. Usa txt o json")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Paquete no generado aún. Llama /agente/mobile-package primero")
    media = "text/plain" if kind == "txt" else "application/json"
    return FileResponse(str(target), filename=target.name, media_type=media)


@router.post("/mobile-package/send-email")
async def mobile_package_send_email(payload: MobilePackageEmailRequest, request: Request):
    """Envía por correo el enlace/paquete de instalación móvil usando SMTP configurado."""
    base = _resolve_public_base_url(request)
    package = _build_mobile_package(base)
    files = _write_mobile_package_files(package)

    smtp_host = (os.getenv("SMTP_HOST", "") or "").strip()
    smtp_port = int((os.getenv("SMTP_PORT", "587") or "587").strip())
    smtp_user = (os.getenv("SMTP_USER", "") or "").strip()
    smtp_password = (os.getenv("SMTP_PASSWORD", "") or "").strip()
    smtp_from = (os.getenv("SMTP_FROM", "") or smtp_user or "").strip()
    recipient = (payload.recipient or os.getenv("ADMIN_EMAIL", "") or smtp_user).strip()

    if not recipient:
        return {
            "ok": False,
            "status": "missing_recipient",
            "detail": "Falta recipient y no hay ADMIN_EMAIL/SMTP_USER configurado",
            "download_txt": f"{base}/agente/mobile-package/download?kind=txt",
        }

    if not smtp_host or not smtp_user or not smtp_password or not smtp_from:
        return {
            "ok": False,
            "status": "smtp_not_configured",
            "detail": "Faltan SMTP_HOST/SMTP_USER/SMTP_PASSWORD (y/o SMTP_FROM)",
            "recipient": recipient,
            "download_txt": f"{base}/agente/mobile-package/download?kind=txt",
        }

    msg = EmailMessage()
    msg["Subject"] = payload.subject or "NEXO SOBERANO - App móvil"
    msg["From"] = smtp_from
    msg["To"] = recipient
    links = package.get("links", {})
    body = (
        "Hola,\n\n"
        "Aquí tienes los enlaces de instalación móvil de NEXO SOBERANO:\n\n"
        f"- App Usuario: {links.get('app_user')}\n"
        f"- App Admin: {links.get('app_admin')}\n"
        f"- Control Center: {links.get('control_center')}\n\n"
        "También puedes descargar el paquete de enlaces aquí:\n"
        f"{base}/agente/mobile-package/download?kind=txt\n\n"
        "Para debatir el código con Grok:\n"
        f"- Endpoint automático: {base}/agente/grok/share-code\n"
        f"- Prompt local: {str(_logs_dir() / 'grok_share_prompt.txt')}\n\n"
        "Saludos,\nNEXO SOBERANO"
    )
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return {
            "ok": True,
            "status": "sent",
            "recipient": recipient,
            "download_txt": f"{base}/agente/mobile-package/download?kind=txt",
            "files": {"json": str(files["json"]), "txt": str(files["txt"])}
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "send_failed",
            "detail": str(exc),
            "recipient": recipient,
            "download_txt": f"{base}/agente/mobile-package/download?kind=txt",
        }


@router.get("/go-live/preflight")
async def go_live_preflight():
    """Chequeo rápido de prerequisitos para go-live Drive->YouTube."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from services.connectors.google_connector import AUTH_DIR as DRIVE_AUTH_DIR

        required_env_any = {
            "google_client": ["GOOGLE_CLIENT_ID", "DRIVE_CLIENT_ID", "YOUTUBE_CLIENT_ID"],
            "google_secret": ["GOOGLE_CLIENT_SECRET", "DRIVE_CLIENT_SECRET", "YOUTUBE_CLIENT_SECRET"],
        }

        env_status = {}
        for key, options in required_env_any.items():
            env_status[key] = any(bool(os.getenv(opt, "").strip()) for opt in options)

        files_to_check = {
            "drive_client_secrets": DRIVE_AUTH_DIR / "drive_client_secrets.json",
            "youtube_client_secrets": DRIVE_AUTH_DIR / "client_secrets_youtube.json",
            "google_credentials_json": DRIVE_AUTH_DIR / "credenciales_google.json",
            "drive_token_write": DRIVE_AUTH_DIR / "token_google_manage.json",
            "youtube_token_upload": DRIVE_AUTH_DIR / "token_youtube_upload.json",
        }
        file_status = {name: path.exists() for name, path in files_to_check.items()}

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            candidates = []
            local_app_data = os.getenv("LOCALAPPDATA", "")
            if local_app_data:
                candidates.append(Path(local_app_data) / "Microsoft" / "WinGet" / "Packages")
            user_profile = os.getenv("USERPROFILE", "")
            if user_profile:
                candidates.append(Path(user_profile) / "scoop" / "apps")

            for base in candidates:
                if not base.exists():
                    continue
                try:
                    match = next(base.rglob("ffmpeg.exe"), None)
                except Exception:
                    match = None
                if match:
                    ffmpeg_path = str(match)
                    break
        summary_candidates = []
        summary_scan_error = None
        try:
            from backend.services.drive_youtube_service import find_latest_summary_file
            candidate = find_latest_summary_file(max_results=30)
            if candidate:
                summary_candidates.append({
                    "id": candidate.get("id"),
                    "name": candidate.get("name"),
                    "mimeType": candidate.get("mimeType"),
                })
        except Exception as exc:
            summary_scan_error = str(exc)

        has_client_credentials = (
            (env_status["google_client"] and env_status["google_secret"])
            or file_status["drive_client_secrets"]
            or file_status["youtube_client_secrets"]
            or file_status["google_credentials_json"]
        )

        ready = (
            has_client_credentials
            and (file_status["drive_token_write"] or file_status["google_credentials_json"])
            and (file_status["youtube_token_upload"] or file_status["google_credentials_json"])
        )

        return {
            "ok": True,
            "ready": bool(ready),
            "env": env_status,
            "files": file_status,
            "ffmpeg": {"found": bool(ffmpeg_path), "path": ffmpeg_path},
            "summary_candidates": summary_candidates,
            "summary_scan_error": summary_scan_error,
            "auth_dir": str(DRIVE_AUTH_DIR),
        }
    except Exception as e:
        logger.error(f"Error en /go-live/preflight: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error ejecutando preflight: {str(e)}")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _logs_dir() -> Path:
    return _workspace_root() / "logs"


def _safe_json_read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extractor_paths() -> Dict[str, Path]:
    logs = _logs_dir()
    return {
        "lock": logs / "extractor.lock",
        "status": logs / "extractor_status.json",
        "report": logs / "extractor_report.json",
        "output": logs / "ai_context" / "contexto_nexo_soberano.txt",
    }


def _parse_youtube_channels_from_env() -> List[str]:
    channels: List[str] = []
    many = (os.getenv("YOUTUBE_CHANNELS", "") or "").strip()
    one = (os.getenv("YOUTUBE_CHANNEL_ID", "") or "").strip()

    if many:
        channels.extend([x.strip() for x in many.split(",") if x.strip()])
    elif one:
        channels.append(one)

    unique: List[str] = []
    seen = set()
    for ch in channels:
        if ch not in seen:
            unique.append(ch)
            seen.add(ch)
    return unique


def _sync_summary(result: Dict) -> Dict:
    gp = result.get("google_photos", {})
    gd = result.get("google_drive", {})
    od = result.get("onedrive", {})
    yt = result.get("youtube", {})
    return {
        "google_photos": {
            "imported": gp.get("imported", 0),
            "skipped": gp.get("skipped", 0),
            "errors": gp.get("errors", 0),
        },
        "google_drive": {
            "analyzed": gd.get("analyzed", 0),
            "classified": gd.get("classified", 0),
            "skipped": gd.get("skipped", 0),
            "errors": gd.get("errors", 0),
        },
        "onedrive": {
            "imported": od.get("imported", 0),
            "skipped": od.get("skipped", 0),
            "errors": od.get("errors", 0),
        },
        "youtube": {
            "processed": yt.get("processed", 0),
            "skipped": yt.get("skipped", 0),
            "errors": yt.get("errors", 0),
        },
    }


@router.get("/control-center/status")
async def control_center_status():
    """Estado consolidado para panel de control operacional."""
    logs_dir = _logs_dir()
    status_path = logs_dir / "sync_drive_status.json"
    report_path = logs_dir / "sync_drive_last.json"
    unified_status_path = logs_dir / "sync_unified_status.json"
    unified_report_path = logs_dir / "sync_unified_last.json"
    lock_paths = {
        "sync_drive": logs_dir / "sync_drive.lock",
        "sync_drive_api": logs_dir / "sync_drive_api.lock",
        "sync_unified": logs_dir / "sync_unified.lock",
    }

    preflight = await go_live_preflight()
    sync_status = _safe_json_read(status_path)
    sync_report = _safe_json_read(report_path)
    unified_sync_status = _safe_json_read(unified_status_path)
    unified_sync_report = _safe_json_read(unified_report_path)
    extractor = _extractor_paths()

    ai_health = None
    ai_budget = None
    try:
        rag = get_rag_service()
        ai_health = rag.estado()
    except Exception as exc:
        ai_health = {"error": str(exc)}

    try:
        ai_budget = get_cost_manager().estado()
    except Exception as exc:
        ai_budget = {"error": str(exc)}

    return {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health": {
            "status": "ok",
            "service": "nexo-soberano-backend",
        },
        "ai": {
            "health": ai_health,
            "budget": ai_budget,
        },
        "web": {
            "control_center": "/control-center",
            "api_docs": "/api/docs",
            "admin_dashboard": "/admin_dashboard.html",
            "warroom": "/warroom_v2.html",
        },
        "preflight": preflight,
        "locks": {name: path.exists() for name, path in lock_paths.items()},
        "sync": {
            "status": sync_status,
            "last_report": sync_report,
            "status_file": str(status_path),
            "report_file": str(report_path),
        },
        "sync_unified": {
            "status": unified_sync_status,
            "last_report": unified_sync_report,
            "status_file": str(unified_status_path),
            "report_file": str(unified_report_path),
        },
        "extractor": {
            "lock": extractor["lock"].exists(),
            "status": _safe_json_read(extractor["status"]),
            "report": _safe_json_read(extractor["report"]),
            "output_file": str(extractor["output"]),
        },
    }


@router.get("/control-center/reports")
async def control_center_reports():
    """Lista reportes JSON de logs para inspección rápida."""
    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    for path in sorted(logs_dir.glob("*.json")):
        stat = path.stat()
        reports.append(
            {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            }
        )

    return {"ok": True, "count": len(reports), "reports": reports}


@router.get("/control-center/report/{report_name}")
async def control_center_report(report_name: str):
    """Devuelve contenido de un reporte JSON específico en logs/."""
    if not report_name.endswith(".json") or "/" in report_name or "\\" in report_name:
        raise HTTPException(status_code=400, detail="Nombre de reporte inválido")

    report_path = _logs_dir() / report_name
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    payload = _safe_json_read(report_path)
    return {"ok": True, "report": report_name, "data": payload}


@router.get("/control-center/errors")
async def control_center_errors(limit: int = 50):
    """Resume errores recientes detectados en archivos de estado/reporte."""
    limit = max(1, min(int(limit), 500))
    items: List[dict] = []

    status_data = _safe_json_read(_logs_dir() / "sync_drive_status.json")
    if status_data.get("status") == "error":
        items.append(
            {
                "source": "sync_drive_status.json",
                "type": "runtime",
                "error": status_data.get("error", "unknown_error"),
                "timestamp": status_data.get("finished_at") or status_data.get("timestamp"),
            }
        )

    report_data = _safe_json_read(_logs_dir() / "sync_drive_last.json")
    rounds = report_data.get("rounds") or []
    for round_item in rounds:
        if int(round_item.get("errors", 0) or 0) > 0:
            items.append(
                {
                    "source": "sync_drive_last.json",
                    "type": "sync_round",
                    "round": round_item.get("round"),
                    "errors": round_item.get("errors"),
                    "ok": round_item.get("ok"),
                    "timestamp": report_data.get("timestamp"),
                }
            )

    return {"ok": True, "count": len(items[:limit]), "errors": items[:limit]}


@router.post("/control-center/run-drive-classification")
async def control_center_run_drive_classification():
    """Lanza clasificación de Drive en segundo plano (runner por API)."""
    logs_dir = _logs_dir()
    lock_path = logs_dir / "sync_drive_api.lock"
    if lock_path.exists():
        try:
            status_payload = _safe_json_read(logs_dir / "sync_drive_status.json")
            pid = int(status_payload.get("pid") or 0)
            if pid > 0:
                os.kill(pid, 0)
        except Exception:
            lock_path.unlink(missing_ok=True)
        if lock_path.exists():
            return {
                "ok": True,
                "already_running": True,
                "message": "Ya hay una clasificación en ejecución",
                "lock_file": str(lock_path),
            }

    if lock_path.exists():
        return {
            "ok": True,
            "already_running": True,
            "message": "Ya hay una clasificación en ejecución",
            "lock_file": str(lock_path),
        }

    root = _workspace_root()
    script_path = root / "scripts" / "run_drive_classification_api.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"No existe script: {script_path}")

    runner_log = logs_dir / "sync_drive_runner.log"
    runner_log.parent.mkdir(parents=True, exist_ok=True)
    with runner_log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n[{datetime.now(timezone.utc).isoformat()}] launching {script_path}\n")
    log_handle = runner_log.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(root),
        stdout=log_handle,
        stderr=log_handle,
    )

    return {
        "ok": True,
        "already_running": False,
        "pid": proc.pid,
        "script": str(script_path),
        "runner_log": str(runner_log),
        "report_path": str(logs_dir / "sync_drive_last.json"),
        "status_path": str(logs_dir / "sync_drive_status.json"),
    }


@router.get("/control-center/sync-unified-status")
async def control_center_sync_unified_status():
    logs_dir = _logs_dir()
    lock = (logs_dir / "sync_unified.lock").exists()
    status = _safe_json_read(logs_dir / "sync_unified_status.json")
    if lock and not status.get("status"):
        status = {"status": "running", "message": "lock activo sin estado detallado"}
    return {
        "ok": True,
        "status": status,
        "report": _safe_json_read(logs_dir / "sync_unified_last.json"),
        "lock": lock,
    }


@router.post("/control-center/run-unified-sync")
async def control_center_run_unified_sync(request: UnifiedSyncRunRequest):
    """Lanza sincronización completa (Workspace + Microsoft 365 + YouTube) en segundo plano."""
    logs_dir = _logs_dir()
    lock_path = logs_dir / "sync_unified.lock"
    if lock_path.exists():
        try:
            status_payload = _safe_json_read(logs_dir / "sync_unified_status.json")
            pid = int(status_payload.get("pid") or 0)
            if pid > 0:
                os.kill(pid, 0)
        except Exception:
            lock_path.unlink(missing_ok=True)
        if lock_path.exists():
            return {
                "ok": True,
                "already_running": True,
                "message": "Ya hay una sincronización unificada en ejecución",
                "lock_file": str(lock_path),
            }

    if lock_path.exists():
        return {
            "ok": True,
            "already_running": True,
            "message": "Ya hay una sincronización unificada en ejecución",
            "lock_file": str(lock_path),
        }

    root = _workspace_root()
    script_path = root / "scripts" / "run_unified_sync_full.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"No existe script: {script_path}")

    channels = request.youtube_channels if request.youtube_channels is not None else _parse_youtube_channels_from_env()

    _safe_json_path = logs_dir / "sync_unified_status.json"
    _safe_json_path.write_text(
        json.dumps(
            {
                "status": "queued",
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "request": {
                    "dry_run": request.dry_run,
                    "photos_limit": request.photos_limit,
                    "drive_limit": request.drive_limit,
                    "onedrive_limit": request.onedrive_limit,
                    "onedrive_max_mb": request.onedrive_max_mb,
                    "youtube_per_channel": request.youtube_per_channel,
                    "youtube_channels": channels,
                    "drive_include_trashed": request.drive_include_trashed,
                    "drive_full_scan": request.drive_full_scan,
                    "drive_auto_rename": request.drive_auto_rename,
                    "retry_attempts": request.retry_attempts,
                    "retry_backoff_seconds": request.retry_backoff_seconds,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "NEXO_FULL_DRY_RUN": "true" if request.dry_run else "false",
            "NEXO_FULL_PHOTOS_LIMIT": str(request.photos_limit),
            "NEXO_FULL_DRIVE_LIMIT": str(request.drive_limit),
            "NEXO_FULL_ONEDRIVE_LIMIT": str(request.onedrive_limit),
            "NEXO_FULL_ONEDRIVE_MAX_MB": str(request.onedrive_max_mb),
            "NEXO_FULL_YT_PER_CHANNEL": str(request.youtube_per_channel),
            "NEXO_FULL_YOUTUBE_CHANNELS": ",".join(channels or []),
            "NEXO_FULL_DRIVE_INCLUDE_TRASHED": "true" if request.drive_include_trashed else "false",
            "NEXO_FULL_DRIVE_FULL_SCAN": "true" if request.drive_full_scan else "false",
            "NEXO_FULL_DRIVE_AUTO_RENAME": "true" if request.drive_auto_rename else "false",
            "NEXO_FULL_RETRY_ATTEMPTS": str(request.retry_attempts),
            "NEXO_FULL_RETRY_BACKOFF_SECONDS": str(request.retry_backoff_seconds),
        }
    )

    runner_log = logs_dir / "sync_unified_runner.log"
    runner_log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with runner_log.open("a", encoding="utf-8") as fh:
            fh.write(f"\n[{datetime.now(timezone.utc).isoformat()}] launching {script_path}\n")
        log_handle = runner_log.open("a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(root),
            env=env,
            stdout=log_handle,
            stderr=log_handle,
        )
    except Exception as exc:
        _safe_json_path.write_text(
            json.dumps(
                {
                    "status": "error",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error": f"No se pudo lanzar runner: {exc}",
                    "script": str(script_path),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        raise

    return {
        "ok": True,
        "already_running": False,
        "pid": proc.pid,
        "script": str(script_path),
        "channels": channels,
        "runner_log": str(runner_log),
        "status_path": str(logs_dir / "sync_unified_status.json"),
        "report_path": str(logs_dir / "sync_unified_last.json"),
    }


@router.get("/control-center/analytics")
async def control_center_analytics():
    """Métricas visuales y analíticas de IA + Workspace + Microsoft 365."""
    analytics = {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workspace": {"ok": False},
        "microsoft365": {"ok": False},
        "ai": {"ok": False},
        "charts": {},
    }

    try:
        from services.connectors.google_connector import list_recent_files_detailed, list_recent_photos

        drive_items = []
        photo_items = []
        drive_error = None
        photos_error = None

        try:
            drive_items = list_recent_files_detailed(max_results=20)
        except Exception as exc:
            drive_error = str(exc)

        try:
            photo_items = list_recent_photos(max_results=20)
        except Exception as exc:
            photos_error = str(exc)

        mime_buckets = {
            "images": 0,
            "videos": 0,
            "documents": 0,
            "others": 0,
        }
        for item in drive_items:
            mime = str(item.get("mimeType") or "").lower()
            if mime.startswith("image/"):
                mime_buckets["images"] += 1
            elif mime.startswith("video/"):
                mime_buckets["videos"] += 1
            elif mime.startswith("text/") or "pdf" in mime or "document" in mime or "sheet" in mime or "presentation" in mime:
                mime_buckets["documents"] += 1
            else:
                mime_buckets["others"] += 1

        analytics["workspace"] = {
            "ok": bool(drive_items or photo_items),
            "drive_recent": len(drive_items),
            "photos_recent": len(photo_items),
            "mime_buckets": mime_buckets,
            "drive_error": drive_error,
            "photos_error": photos_error,
        }
    except Exception as exc:
        analytics["workspace"] = {"ok": False, "error": str(exc)}

    try:
        from services.connectors.microsoft_connector import MicrosoftConnector
        from services.connectors.local_onedrive_connector import list_recent_local_onedrive_files, resolve_onedrive_local_root

        mc = MicrosoftConnector()
        files = mc.list_recent_files(top=20)
        source = "graph"
        if not files:
            files = list_recent_local_onedrive_files(top=20)
            if files:
                source = "local_onedrive"
        total_size = 0
        for item in files:
            try:
                total_size += int(item.get("size") or 0)
            except Exception:
                pass

        analytics["microsoft365"] = {
            "ok": bool(files),
            "onedrive_recent": len(files),
            "onedrive_total_size_mb": round(total_size / (1024 * 1024), 2),
            "source": source,
            "local_root": str(resolve_onedrive_local_root() or ""),
        }
    except Exception as exc:
        analytics["microsoft365"] = {"ok": False, "error": str(exc)}

    try:
        rag_state = get_rag_service().estado()
        budget = get_cost_manager().estado()
        analytics["ai"] = {
            "ok": True,
            "rag_loaded": bool(rag_state.get("rag_loaded")),
            "total_documentos": rag_state.get("total_documentos", 0),
            "presupuesto_restante_usd": budget.get("presupuesto_restante_usd"),
            "tokens_hoy": budget.get("tokens_hoy"),
        }
    except Exception as exc:
        analytics["ai"] = {"ok": False, "error": str(exc)}

    sync_drive = _safe_json_read(_logs_dir() / "sync_drive_last.json").get("totals", {})
    sync_unified = _safe_json_read(_logs_dir() / "sync_unified_last.json").get("summary", {})
    analytics["charts"] = {
        "drive_sync": {
            "labels": ["analyzed", "classified", "skipped", "errors"],
            "values": [
                int(sync_drive.get("analyzed", 0) or 0),
                int(sync_drive.get("classified", 0) or 0),
                int(sync_drive.get("skipped", 0) or 0),
                int(sync_drive.get("errors", 0) or 0),
            ],
        },
        "workspace_vs_m365": {
            "labels": ["Drive recientes", "Photos recientes", "OneDrive recientes"],
            "values": [
                int((analytics.get("workspace") or {}).get("drive_recent", 0) or 0),
                int((analytics.get("workspace") or {}).get("photos_recent", 0) or 0),
                int((analytics.get("microsoft365") or {}).get("onedrive_recent", 0) or 0),
            ],
        },
        "unified_sync": {
            "labels": ["Drive clasificados", "Photos importadas", "OneDrive importados", "YouTube procesados"],
            "values": [
                int(((sync_unified.get("google_drive") or {}).get("classified", 0) or 0)),
                int(((sync_unified.get("google_photos") or {}).get("imported", 0) or 0)),
                int(((sync_unified.get("onedrive") or {}).get("imported", 0) or 0)),
                int(((sync_unified.get("youtube") or {}).get("processed", 0) or 0)),
            ],
        },
    }
    return analytics


@router.get("/control-center/extractor-status")
async def control_center_extractor_status():
    paths = _extractor_paths()
    return {
        "ok": True,
        "lock": paths["lock"].exists(),
        "status": _safe_json_read(paths["status"]),
        "report": _safe_json_read(paths["report"]),
        "output_file": str(paths["output"]),
    }


@router.post("/control-center/run-code-extractor")
async def control_center_run_code_extractor():
    paths = _extractor_paths()
    if paths["lock"].exists():
        return {
            "ok": True,
            "already_running": True,
            "message": "Ya hay una extracción de código en ejecución",
            "lock_file": str(paths["lock"]),
        }

    root = _workspace_root()
    script_path = root / "scripts" / "run_code_extractor.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"No existe script: {script_path}")

    paths["status"].parent.mkdir(parents=True, exist_ok=True)
    paths["status"].write_text(
        json.dumps(
            {
                "status": "queued",
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "output_file": str(paths["output"]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return {
        "ok": True,
        "already_running": False,
        "pid": proc.pid,
        "script": str(script_path),
        "status_path": str(paths["status"]),
        "report_path": str(paths["report"]),
        "output_file": str(paths["output"]),
    }


@router.get("/control-center/extractor-download")
async def control_center_extractor_download():
    paths = _extractor_paths()
    output = paths["output"]
    if not output.exists():
        raise HTTPException(status_code=404, detail="No existe contexto extraído aún")
    return FileResponse(str(output), filename=output.name, media_type="text/plain")


@router.get("/control-center/extractor-prompt")
async def control_center_extractor_prompt():
    paths = _extractor_paths()
    report = _safe_json_read(paths["report"])
    output_file = str(paths["output"])
    files_scanned = report.get("files_scanned", "n/d")
    bytes_written = report.get("bytes_written", "n/d")

    prompt = (
        "Actúa como arquitecto de software senior. Analiza el contexto del proyecto NEXO SOBERANO "
        "y entrega: 1) diagnóstico de arquitectura, 2) riesgos técnicos, 3) quick wins de alto impacto, "
        "4) plan de implementación por fases con esfuerzo estimado. "
        f"Contexto extraído: {output_file}. "
        f"Archivos escaneados: {files_scanned}. Bytes: {bytes_written}. "
        "Sé específico y prioriza cambios que mejoren confiabilidad operacional, observabilidad y UX del panel de control."
    )
    return {"ok": True, "prompt": prompt, "output_file": output_file, "report": report}
