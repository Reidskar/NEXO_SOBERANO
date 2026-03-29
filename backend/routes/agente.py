"""
Rutas del Agente RAG — Contrato unificado
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from collections import Counter, defaultdict, deque
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
from datetime import datetime, timezone, timedelta
from pathlib import Path

from backend.services.rag_service import get_rag_service
from backend.services.cost_manager import get_cost_manager
from backend.services.unified_cost_tracker import get_cost_tracker

from NEXO_CORE.services.ai_router import ai_router, AIRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agente", tags=["agente"])


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

# Historial de conversación por usuario Discord (en memoria)
conversation_history: dict = defaultdict(lambda: deque(maxlen=10))

# ════════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC — CONTRATO UNIFICADO
# ════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """Request unificado del agente"""
    query: Optional[str] = Field(default=None, description="Pregunta del usuario")
    pregunta: Optional[str] = Field(default=None, description="Alia para query")
    user_id: Optional[str] = Field(default=None, description="ID del usuario Discord")
    canal: Optional[str] = Field(default=None, description="Canal de origen")
    mode: str = Field(default="normal", description="Modo: normal|high|fast")
    categoria: Optional[str] = Field(default=None, description="Filtro por categoría")

class QueryResponse(BaseModel):
    """Response unificado del agente"""
    answer: Optional[str] = Field(default=None, description="Respuesta de la IA")
    respuesta: Optional[str] = Field(default=None, description="Alias para answer")
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

# ════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════

@router.post("/", response_model=QueryResponse)
async def procesar_query(request: QueryRequest):
    """
    Endpoint principal del agente NEXO (Soporta historial).
    Recibe query del bot Discord y devuelve respuesta de IA real.
    """
    q = request.query or request.pregunta
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query vacía")

    try:
        from NEXO_CORE.services.multi_ai_service import consultar_ia

        # Construir contexto con historial si hay user_id
        if request.user_id:
            history = conversation_history[request.user_id]
            contexto = "\n".join([f"{h['role']}: {h['text']}" for h in history])
            query_con_contexto = f"{contexto}\nUsuario: {q}" if contexto else q
            history.append({"role": "Usuario", "text": q})
        else:
            query_con_contexto = q

        respuesta = consultar_ia(query_con_contexto)

        if request.user_id:
            conversation_history[request.user_id].append(
                {"role": "NEXO", "text": respuesta[:200]}
            )

        return QueryResponse(answer=respuesta, respuesta=respuesta)

    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Servicio IA no disponible: {str(e)}")
    except Exception as e:
        logger.error(f"[AGENTE] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

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
        consulta_texto = request.query or request.pregunta or ""
        resultado = await ai_router.consultar(AIRequest(
            prompt=consulta_texto,
            tipo="rag"
        ))
        respuesta = resultado.texto

        # Mapear a respuesta unificada
        return QueryResponse(
            answer=respuesta,
            sources=[resultado.fuente],
            tokens_used=resultado.tokens,
            chunks_used=0,
            execution_time_ms=0,
            total_docs=0,
            presupuesto={},
            error=not resultado.success,
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


@router.get("/drive/recent-old")
def drive_recent_old():
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
        logger.error(f"Error en /drive/recent-old: {e}")
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


@router.get("/costs/report")
async def costs_report(period: str = "today"):
    """
    🤑 Reporte unificado de costos operacionales
    
    Incluye:
    - APIs de IA (Gemini, Claude, OpenAI, Grok)
    - Servicios externos (Drive, Microsoft, X, Discord)
    - Breakdown por operación
    - Warnings de costos anormales
    
    Args:
        period: "today", "week", "month", "all"
    
    Returns:
        Reporte detallado con costos en USD
    """
    try:
        tracker = get_cost_tracker()
        report = tracker.get_cost_report(period=period)
        return report
    except Exception as e:
        logger.error(f"Error generando reporte de costos: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/costs/daily-summary")
async def costs_daily_summary(days: int = 7):
    """
    📊 Resumen diario de costos de los últimos N días
    
    Args:
        days: número de días a incluir (default: 7)
    
    Returns:
        Lista de costos diarios
    """
    try:
        tracker = get_cost_tracker()
        summary = tracker.get_daily_summary(days=days)
        return {"days": days, "summary": summary}
    except Exception as e:
        logger.error(f"Error generando resumen diario: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/costs/budget")
async def costs_budget():
    """
    💰 Estado actual del presupuesto diario (Gemini free tier)
    
    Returns:
        Estado de tokens Gemini y límite free tier
    """
    try:
        tracker = get_cost_tracker()
        status = tracker.get_budget_status()
        return status
    except Exception as e:
        logger.error(f"Error obteniendo estado de presupuesto: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/tokens/status")
async def tokens_status():
    """Estado de configuración de tokens/API keys (sin exponer secretos)."""
    try:
        values = {
            "NEXO_API_KEY": (os.getenv("NEXO_API_KEY", "") or "").strip(),
            "GEMINI_API_KEY": (os.getenv("GEMINI_API_KEY", "") or "").strip(),
            "OPENAI_API_KEY": (os.getenv("OPENAI_API_KEY", "") or "").strip(),
            "ANTHROPIC_API_KEY": (os.getenv("ANTHROPIC_API_KEY", "") or "").strip(),
            "XAI_API_KEY": (os.getenv("XAI_API_KEY", "") or "").strip(),
            "DISCORD_WEBHOOK_URL": (os.getenv("DISCORD_WEBHOOK_URL", "") or "").strip(),
            "NEXO_ALERT_WEBHOOK": (os.getenv("NEXO_ALERT_WEBHOOK", "") or "").strip(),
        }

        configured = {k: bool(v) for k, v in values.items()}
        ai_providers = {
            "gemini": configured["GEMINI_API_KEY"],
            "openai": configured["OPENAI_API_KEY"],
            "anthropic": configured["ANTHROPIC_API_KEY"],
            "grok": configured["XAI_API_KEY"],
        }
        ai_ready_count = sum(1 for ok in ai_providers.values() if ok)

        status = {
            "auth": {
                "nexo_api_key": configured["NEXO_API_KEY"],
                "protected_endpoints_ready": configured["NEXO_API_KEY"],
            },
            "ai": {
                "providers": ai_providers,
                "ready_count": ai_ready_count,
                "at_least_one_ready": ai_ready_count > 0,
                "all_ready": all(ai_providers.values()),
            },
            "discord": {
                "discord_webhook_url": configured["DISCORD_WEBHOOK_URL"],
                "alert_webhook": configured["NEXO_ALERT_WEBHOOK"],
                "fully_ready": configured["DISCORD_WEBHOOK_URL"] and configured["NEXO_ALERT_WEBHOOK"],
            },
        }

        missing_required = []
        if not status["auth"]["protected_endpoints_ready"]:
            missing_required.append("NEXO_API_KEY")
        if not status["ai"]["at_least_one_ready"]:
            missing_required.append("GEMINI_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|XAI_API_KEY")
        if not configured["DISCORD_WEBHOOK_URL"]:
            missing_required.append("DISCORD_WEBHOOK_URL")

        return {
            "ok": True,
            "complete": len(missing_required) == 0,
            "missing_required": missing_required,
            "configured": configured,
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estado de tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/autopilot/credentials")
async def credential_autopilot(request: CredentialAutopilotRequest):
    """Autopiloto de credenciales/APIs: aplica fixes seguros y devuelve solo autorizaciones humanas pendientes."""
    root = _workspace_root()
    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    output = logs_dir / "credential_api_autopilot_last.json"

    cmd = [
        sys.executable,
        str(root / "scripts" / "credential_api_autopilot.py"),
        "--output",
        str(output),
    ]
    if not request.auto_apply:
        cmd.append("--dry-run")

    result = _run_local_command(cmd, cwd=root, timeout_seconds=120)
    payload = _safe_json_read(output)

    if not result.get("ok") and not payload:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "No se pudo ejecutar autopilot de credenciales",
                "stderr": _mask_sensitive_text(str(result.get("stderr", ""))),
                "stdout": _mask_sensitive_text(str(result.get("stdout", ""))),
            },
        )

    return {
        "ok": True,
        "auto_apply": request.auto_apply,
        "execution": {
            "ok": bool(result.get("ok")),
            "returncode": result.get("returncode"),
            "started_at": result.get("started_at"),
            "finished_at": result.get("finished_at"),
        },
        "report": _sanitize_warroom_payload(payload),
        "report_path": str(output),
    }


@router.get("/autopilot/credentials/status")
async def credential_autopilot_status():
    """Último estado del autopiloto de credenciales/APIs."""
    output = _logs_dir() / "credential_api_autopilot_last.json"
    data = _safe_json_read(output)
    if not data:
        return {
            "ok": False,
            "message": "Aún no existe reporte. Ejecuta POST /agente/autopilot/credentials",
            "report_path": str(output),
        }
    return {
        "ok": True,
        "report": _sanitize_warroom_payload(data),
        "report_path": str(output),
    }


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


_DRIVE_AI_STOPWORDS = {
    "este", "esta", "estos", "estas", "para", "como", "pero", "porque", "sobre", "entre", "desde",
    "hasta", "donde", "cuando", "quien", "cual", "cuanto", "tambien", "solo", "mismo", "misma", "muy",
    "poco", "mucho", "cada", "todo", "toda", "todos", "todas", "algun", "alguna", "algunos", "algunas",
    "nexo", "soberano", "drive", "google", "document", "docs", "file", "files", "data", "datos",
}


def _parse_drive_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_textual_drive_item(item: Dict) -> bool:
    name = str(item.get("name") or "").lower()
    mime = str(item.get("mimeType") or "").lower()
    if mime.startswith("text/"):
        return True
    return any(name.endswith(ext) for ext in (".txt", ".md", ".json", ".csv", ".log", ".xml", ".html", ".htm"))


def _extract_keywords_counter(text: str) -> Counter:
    counter: Counter = Counter()
    for token in re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]{4,}", (text or "").lower()):
        if token in _DRIVE_AI_STOPWORDS:
            continue
        counter[token] += 1
    return counter


def _build_autonomous_briefing(analytics: Dict) -> Dict:
    charts = analytics.get("charts", {}) or {}
    workspace = analytics.get("workspace", {}) or {}
    m365 = analytics.get("microsoft365", {}) or {}
    ai = analytics.get("ai", {}) or {}

    activity = ((charts.get("drive_activity_7d") or {}).get("values") or [])
    labels = ((charts.get("drive_activity_7d") or {}).get("labels") or [])
    topics_labels = ((charts.get("drive_ai_topics") or {}).get("labels") or [])
    topics_values = ((charts.get("drive_ai_topics") or {}).get("values") or [])

    topic_pairs = []
    for idx, label in enumerate(topics_labels[:10]):
        try:
            topic_pairs.append({"term": str(label), "count": int(topics_values[idx] or 0)})
        except Exception:
            topic_pairs.append({"term": str(label), "count": 0})

    trend = "estable"
    if len(activity) >= 4:
        recent = sum(int(x or 0) for x in activity[-3:])
        previous = sum(int(x or 0) for x in activity[-6:-3]) if len(activity) >= 6 else sum(int(x or 0) for x in activity[:-3])
        if recent > previous:
            trend = "ascendente"
        elif recent < previous:
            trend = "descendente"

    insights = [
        f"Actividad Drive 7D en tendencia {trend} ({sum(int(x or 0) for x in activity)} eventos totales).",
        f"Volumen cloud actual: Drive={int(workspace.get('drive_recent', 0) or 0)}, Photos={int(workspace.get('photos_recent', 0) or 0)}, OneDrive={int(m365.get('onedrive_recent', 0) or 0)}.",
        f"IA operativa: docs={int(ai.get('total_documentos', 0) or 0)} | tokens_hoy={int(ai.get('tokens_hoy', 0) or 0)}.",
    ]

    if topic_pairs:
        top = ", ".join([f"{p['term']}({p['count']})" for p in topic_pairs[:5]])
        insights.append(f"Tópicos emergentes detectados por lectura de Drive: {top}.")
    else:
        insights.append("Sin tópicos textuales recientes en Drive; se recomienda subir fuentes .txt/.md/.json/.csv para ampliar inteligencia autónoma.")

    fallback_briefing = " ".join(insights)
    ai_briefing = None
    ai_error = None

    try:
        prompt = (
            "Genera un briefing ejecutivo autónomo (máx 8 líneas) para operaciones de inteligencia. "
            "Usa solo los indicadores siguientes y produce: 1) hallazgo clave, 2) riesgo, 3) oportunidad, 4) siguiente acción concreta. "
            f"Indicadores: {json.dumps({'activity_labels': labels, 'activity_values': activity, 'topics': topic_pairs[:8], 'workspace': workspace, 'm365': m365, 'ai': {'total_documentos': ai.get('total_documentos'), 'tokens_hoy': ai.get('tokens_hoy')}}, ensure_ascii=False)}"
        )
        ai_result = get_rag_service().consultar(prompt, categoria="INTEL")
        ai_briefing = (ai_result or {}).get("respuesta")
    except Exception as exc:
        ai_error = str(exc)

    briefing_text = ai_briefing or fallback_briefing
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "rag" if ai_briefing else "rule_based",
        "briefing": briefing_text,
        "insights": insights,
        "trend": trend,
        "top_topics": topic_pairs[:10],
        "ai_error": ai_error,
    }


def _build_drive_ai_indicators(drive_items: List[Dict]) -> Dict:
    now_utc = datetime.now(timezone.utc)
    labels_dt = [(now_utc - timedelta(days=offset)).date() for offset in range(6, -1, -1)]
    labels = [day.strftime("%d/%m") for day in labels_dt]
    activity = {day: 0 for day in labels_dt}

    for item in drive_items:
        parsed = _parse_drive_dt(str(item.get("modifiedTime") or ""))
        if not parsed:
            continue
        d = parsed.astimezone(timezone.utc).date()
        if d in activity:
            activity[d] += 1

    output = {
        "text_files_read": 0,
        "text_chars": 0,
        "top_keywords": [],
        "activity_7d": {
            "labels": labels,
            "values": [activity[d] for d in labels_dt],
        },
        "errors": [],
    }

    textual_candidates = [item for item in drive_items if _is_textual_drive_item(item)]
    if not textual_candidates:
        return output

    keyword_counter: Counter = Counter()
    max_files = 8

    try:
        import tempfile
        from services.connectors.google_connector import download_drive_file

        for item in textual_candidates[:max_files]:
            file_id = str(item.get("id") or "").strip()
            if not file_id:
                continue

            suffix = Path(str(item.get("name") or "tmp.txt")).suffix or ".txt"
            tmp_path: Optional[Path] = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp_path = Path(tmp.name)

                download_drive_file(file_id, str(tmp_path))
                raw = tmp_path.read_bytes()
                decoded = raw.decode("utf-8", errors="ignore")
                if not decoded.strip():
                    continue

                output["text_files_read"] += 1
                output["text_chars"] += len(decoded)
                keyword_counter.update(_extract_keywords_counter(decoded))
            except Exception as exc:
                output["errors"].append(f"{item.get('name') or file_id}: {exc}")
            finally:
                if tmp_path and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
    except Exception as exc:
        output["errors"].append(f"No se pudo leer contenido textual de Drive: {exc}")

    output["top_keywords"] = [
        {"term": term, "count": int(count)}
        for term, count in keyword_counter.most_common(10)
    ]
    return output


def _run_local_command(cmd: List[str], cwd: Path, timeout_seconds: int = 1200) -> Dict:
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=max(30, int(timeout_seconds or 1200)),
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": int(result.returncode),
            "stdout": _mask_sensitive_text((result.stdout or "")[:5000]),
            "stderr": _mask_sensitive_text((result.stderr or "")[:5000]),
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "command": cmd,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": _mask_sensitive_text(str((exc.stdout or "")[:3000])),
            "stderr": _mask_sensitive_text(str((exc.stderr or "")[:3000])),
            "error": f"timeout>{timeout_seconds}s",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "command": cmd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": str(exc),
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "command": cmd,
        }


def _latest_supervisor_scan_summary() -> Dict:
    reports_dir = _workspace_root() / "reports" / "supervisor"
    if not reports_dir.exists():
        return {}
    candidates = sorted(
        reports_dir.glob("scan_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {}
    latest = candidates[0]
    payload = _safe_json_read(latest)
    report = (payload or {}).get("report", {}) or {}
    return {
        "path": str(latest),
        "timestamp": report.get("timestamp"),
        "files_scanned": int(report.get("files_scanned", 0) or 0),
        "quality_score": float(report.get("quality_score", 0.0) or 0.0),
        "total_issues": int(report.get("total_issues", 0) or 0),
        "critical": int(report.get("critical", 0) or 0),
        "high": int(report.get("high", 0) or 0),
        "medium": int(report.get("medium", 0) or 0),
        "low": int(report.get("low", 0) or 0),
        "auto_fixed": int(report.get("auto_fixed", 0) or 0),
    }


def _build_evolution_hints(analytics: Dict, scan_summary: Dict, cycle_payload: Dict) -> List[str]:
    hints: List[str] = []
    workspace = analytics.get("workspace", {}) or {}
    ai = analytics.get("ai", {}) or {}

    critical = int(scan_summary.get("critical", 0) or 0)
    high = int(scan_summary.get("high", 0) or 0)
    docs = int(ai.get("total_documentos", 0) or 0)

    if critical > 0:
        hints.append(f"Prioridad máxima: resolver {critical} issues críticos antes de desplegar UI o nuevas automatizaciones.")
    elif high > 40:
        hints.append(f"Calidad técnica: bajar issues altos ({high}) por tandas para acelerar evolución estable del sistema.")
    else:
        hints.append("Calidad técnica estable: puedes iterar mejoras visuales y de producto con bajo riesgo inmediato.")

    if workspace.get("photos_error"):
        hints.append("Integración Google Photos con error: corrige OAuth scopes/consent para mejorar inteligencia multimodal.")
    if workspace.get("drive_error"):
        hints.append("Drive con error: restaurar sync para mantener la IA aprendiendo de documentos recientes.")

    if docs < 20:
        hints.append("Programación/IA: ampliar corpus RAG (>20 docs) para respuestas más estratégicas y menos genéricas.")
    else:
        hints.append("Programación/IA: habilitar ciclos más frecuentes con objetivos semanales de deuda técnica y UX.")

    fix_ok = bool(((cycle_payload.get("actions") or {}).get("scan_fix") or {}).get("ok"))
    if fix_ok:
        hints.append("Auto-fix aplicado: revisa diff y promueve mejoras estables al flujo principal.")

    if not hints:
        hints.append("Sistema operativo sin hallazgos relevantes: mantener evolución incremental y monitoreo continuo.")
    return hints[:8]


def _provider_flags() -> Dict[str, bool]:
    return {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "grok": bool(os.getenv("XAI_API_KEY")),
    }


def _swot_review_prompt(provider_name: str, objetivo: str, context_payload: Dict) -> str:
    return (
        "Eres un revisor técnico crítico senior. Tu trabajo es cuestionar supuestos y detectar riesgos reales.\n"
        f"Proveedor revisor: {provider_name}.\n"
        "Responde en español, sin marketing, con enfoque profesional y técnico.\n"
        "Formato obligatorio:\n"
        "1) Fortalezas\n"
        "2) Debilidades\n"
        "3) Oportunidades\n"
        "4) Amenazas\n"
        "5) Riesgos críticos (top 5, con impacto y probabilidad)\n"
        "6) Recomendaciones priorizadas (top 5, con quick wins y mejoras estructurales)\n"
        "7) Veredicto (1 párrafo duro y accionable)\n\n"
        f"OBJETIVO:\n{objetivo}\n\n"
        f"CONTEXTO TÉCNICO (JSON):\n{json.dumps(context_payload, ensure_ascii=False)}"
    )


def _swot_consensus_prompt_by_grok(objetivo: str, provider_reviews: List[Dict], context_payload: Dict) -> str:
    return (
        "Eres Grok actuando como árbitro final de consenso entre múltiples IAs.\n"
        "Debes decidir el consenso final (no resumir de forma neutral).\n"
        "Toma postura, prioriza y justifica técnicamente.\n"
        "Responde en español con formato obligatorio:\n"
        "A) CONSENSO FINAL (decisión ejecutiva)\n"
        "B) TOP 7 ACCIONES PRIORIZADAS (impacto, esfuerzo, riesgo)\n"
        "C) QUÉ ARREGLAR YA (24-48h)\n"
        "D) QUÉ OPTIMIZAR (7 días)\n"
        "E) QUÉ PROTEGER/HARDENING (seguridad y resiliencia)\n"
        "F) RIESGO DE NO HACERLO\n"
        "G) KPI de validación de éxito\n\n"
        f"OBJETIVO:\n{objetivo}\n\n"
        f"REVISIONES MULTI-IA:\n{json.dumps(provider_reviews, ensure_ascii=False)}\n\n"
        f"CONTEXTO TÉCNICO:\n{json.dumps(context_payload, ensure_ascii=False)}"
    )


def _swot_consensus_prompt(decider_label: str, objetivo: str, provider_reviews: List[Dict], context_payload: Dict) -> str:
    return (
        f"Eres {decider_label} actuando como árbitro final de consenso entre múltiples IAs.\n"
        "Debes decidir el consenso final (no resumir de forma neutral).\n"
        "Toma postura, prioriza y justifica técnicamente.\n"
        "Responde en español con formato obligatorio:\n"
        "A) CONSENSO FINAL (decisión ejecutiva)\n"
        "B) TOP 7 ACCIONES PRIORIZADAS (impacto, esfuerzo, riesgo)\n"
        "C) QUÉ ARREGLAR YA (24-48h)\n"
        "D) QUÉ OPTIMIZAR (7 días)\n"
        "E) QUÉ PROTEGER/HARDENING (seguridad y resiliencia)\n"
        "F) RIESGO DE NO HACERLO\n"
        "G) KPI de validación de éxito\n\n"
        f"OBJETIVO:\n{objetivo}\n\n"
        f"REVISIONES MULTI-IA:\n{json.dumps(provider_reviews, ensure_ascii=False)}\n\n"
        f"CONTEXTO TÉCNICO:\n{json.dumps(context_payload, ensure_ascii=False)}"
    )


def _call_provider_review(provider: str, prompt: str) -> Dict:
    rag = get_rag_service()
    started = datetime.now(timezone.utc)
    try:
        if provider == "anthropic":
            content, model = rag._gen_anthropic(prompt)
        elif provider == "openai":
            content, model = rag._gen_openai_or_copilot(prompt)
        elif provider == "gemini":
            content, model = rag._gen_gemini(prompt)
        elif provider == "grok":
            content, model = rag._gen_grok(prompt)
        else:
            raise RuntimeError(f"Proveedor no soportado: {provider}")

        return {
            "provider": provider,
            "ok": True,
            "model": model,
            "content": (content or "").strip(),
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }
    except Exception as exc:
        return {
            "provider": provider,
            "ok": False,
            "error": str(exc),
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }


def _build_foda_corrective_actions(
    objective: str,
    context_payload: Dict,
    provider_reviews: List[Dict],
    consensus_payload: Dict,
    settings: Dict,
) -> Dict:
    workspace = ((context_payload.get("analytics") or {}).get("workspace") or {})
    ai_block = ((context_payload.get("analytics") or {}).get("ai") or {})
    alerts = context_payload.get("alerts") or []
    evolution_data = context_payload.get("evolution") or {}
    scan_summary = evolution_data.get("scan_summary") or {}

    high_issues = int(scan_summary.get("high", 0) or 0)
    medium_issues = int(scan_summary.get("medium", 0) or 0)
    critical_issues = int(scan_summary.get("critical", 0) or 0)

    actions: List[Dict] = []

    if workspace.get("drive_error"):
        actions.append(
            {
                "id": "drive-auth-recovery",
                "priority": "P1",
                "owner": "ProductOps",
                "title": "Recuperar autorización de Google Drive",
                "action": "Ejecutar autorización interactiva de Drive y validar lecturas recientes en analytics.",
                "api_or_command": "POST /agente/drive/authorize",
                "success_criteria": "analytics.workspace.drive_error vacío y drive_recent > 0",
                "eta_hours": 2,
            }
        )

    if workspace.get("photos_error"):
        actions.append(
            {
                "id": "photos-scope-fix",
                "priority": "P1",
                "owner": "ProductOps",
                "title": "Corregir scopes de Google Photos",
                "action": "Reautorizar Photos con include_drive_write y validar permisos OAuth/API habilitada.",
                "api_or_command": "POST /agente/photos/authorize {\"include_drive_write\": true}",
                "success_criteria": "analytics.workspace.photos_error vacío y photos_recent > 0",
                "eta_hours": 2,
            }
        )

    has_obs_alert = any("obs" in str((a or {}).get("message", "")).lower() for a in alerts)
    has_discord_alert = any("discord" in str((a or {}).get("message", "")).lower() for a in alerts)
    if has_obs_alert:
        actions.append(
            {
                "id": "obs-connectivity-fix",
                "priority": "P1",
                "owner": "SRE",
                "title": "Restablecer conectividad OBS",
                "action": "Levantar OBS WebSocket y verificar conexión desde War Room.",
                "api_or_command": "GET /warroom/ai-control",
                "success_criteria": "stream.obs_connected = true",
                "eta_hours": 1,
            }
        )

    if has_discord_alert:
        actions.append(
            {
                "id": "discord-restore",
                "priority": "P1",
                "owner": "SRE",
                "title": "Recuperar enlace con Discord",
                "action": "Revalidar webhook/bot token y confirmar estado conectado en control de warroom.",
                "api_or_command": "GET /warroom/ai-control",
                "success_criteria": "stream.discord_connected = true",
                "eta_hours": 1,
            }
        )

    if critical_issues > 0 or high_issues > 40:
        actions.append(
            {
                "id": "code-quality-burst",
                "priority": "P1" if critical_issues > 0 else "P2",
                "owner": "Backend",
                "title": "Reducir deuda técnica alta antes de nuevas features",
                "action": "Ejecutar escaneo y reparación en tandas, con validación por tests al final de cada tanda.",
                "api_or_command": ".\\.venv\\Scripts\\python.exe nexo_autosupervisor.py --scan --fix",
                "success_criteria": f"critical=0 y high < {max(25, high_issues - 15)}",
                "eta_hours": 8,
            }
        )
    elif medium_issues > 60:
        actions.append(
            {
                "id": "medium-debt-trim",
                "priority": "P3",
                "owner": "Backend",
                "title": "Reducir issues medios en lote controlado",
                "action": "Ejecutar escaneo periódico y consolidar fixes seguros.",
                "api_or_command": ".\\.venv\\Scripts\\python.exe nexo_autosupervisor.py --scan",
                "success_criteria": "medium disminuye al menos 20%",
                "eta_hours": 12,
            }
        )

    ai_budget = (ai_block.get("presupuesto") or {}) if isinstance(ai_block, dict) else {}
    can_operate = ai_budget.get("puede_operar")
    if can_operate is False:
        actions.append(
            {
                "id": "budget-protection",
                "priority": "P1",
                "owner": "AI-Ops",
                "title": "Restaurar presupuesto operativo IA",
                "action": "Forzar modo ahorro en FODA y limitar revisores a 1-2 proveedores activos.",
                "api_or_command": "POST /api/ai/foda-critical {\"decisor_final\":\"claude\",\"modo_ahorro\":true}",
                "success_criteria": "presupuesto.puede_operar = true",
                "eta_hours": 1,
            }
        )

    if not actions:
        actions.append(
            {
                "id": "stability-guardrail",
                "priority": "P2",
                "owner": "SRE",
                "title": "Mantener estabilidad operativa",
                "action": "Ejecutar verificación de salud/analytics/foda-status y sostener modo ahorro por defecto.",
                "api_or_command": "GET /health, GET /analytics, GET /api/ai/foda-status",
                "success_criteria": "todos los checks en ok=true por 24h",
                "eta_hours": 24,
            }
        )

    reviewers_ok = [r.get("provider") for r in provider_reviews if r.get("ok")]
    return {
        "required": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "objective": objective,
        "settings": {
            "decisor_final": settings.get("decisor_final"),
            "modo_ahorro": bool(settings.get("modo_ahorro", True)),
        },
        "consensus_ok": bool(consensus_payload.get("ok")),
        "reviewers_ok": reviewers_ok,
        "count": len(actions),
        "items": actions,
    }


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
    drive_items: List[Dict] = []
    photo_items: List[Dict] = []

    try:
        from services.connectors.google_connector import list_recent_files_detailed, list_recent_photos

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

    drive_ai_indicators = _build_drive_ai_indicators(drive_items)
    analytics["ai"]["drive_indicators"] = drive_ai_indicators

    sync_drive = _safe_json_read(_logs_dir() / "sync_drive_last.json").get("totals", {})
    sync_unified = _safe_json_read(_logs_dir() / "sync_unified_last.json").get("summary", {})
    top_keywords = drive_ai_indicators.get("top_keywords", [])
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
        "drive_ai_topics": {
            "labels": [entry.get("term", "-") for entry in top_keywords],
            "values": [int(entry.get("count", 0) or 0) for entry in top_keywords],
        },
        "drive_activity_7d": drive_ai_indicators.get("activity_7d", {"labels": [], "values": []}),
    }
    return analytics


@router.post("/intelligence/autonomous-cycle")
async def intelligence_autonomous_cycle():
    analytics = await control_center_analytics()
    briefing = _build_autonomous_briefing(analytics)

    payload = {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analytics": analytics,
        "briefing": briefing,
    }

    output_path = _logs_dir() / "autonomous_intelligence_last.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return payload


@router.get("/intelligence/autonomous-status")
async def intelligence_autonomous_status():
    output_path = _logs_dir() / "autonomous_intelligence_last.json"
    if not output_path.exists():
        return {
            "ok": True,
            "has_data": False,
            "message": "Aún no hay ciclo autónomo generado. Ejecuta /agente/intelligence/autonomous-cycle",
            "data": {},
        }
    return {
        "ok": True,
        "has_data": True,
        "data": _safe_json_read(output_path),
        "path": str(output_path),
    }


@router.post("/intelligence/evolution-cycle")
async def intelligence_evolution_cycle(apply_code_fix: bool = True):
    started_at = datetime.now(timezone.utc)
    root = _workspace_root()
    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    analytics = await control_center_analytics()
    autonomous = await intelligence_autonomous_cycle()

    autosupervisor_script = root / "nexo_autosupervisor.py"
    scan_action = {
        "ok": False,
        "error": f"No existe {autosupervisor_script}",
        "command": [sys.executable, str(autosupervisor_script), "--scan"],
    }
    fix_action: Dict = {
        "ok": False,
        "skipped": True,
        "reason": "apply_code_fix=false",
        "command": [sys.executable, str(autosupervisor_script), "--scan", "--fix"],
    }

    if autosupervisor_script.exists():
        scan_action = _run_local_command(
            [sys.executable, str(autosupervisor_script), "--scan"],
            cwd=root,
            timeout_seconds=1200,
        )
        if apply_code_fix:
            fix_action = _run_local_command(
                [sys.executable, str(autosupervisor_script), "--scan", "--fix"],
                cwd=root,
                timeout_seconds=1500,
            )

    scan_summary = _latest_supervisor_scan_summary()
    cycle_payload = {
        "ok": bool(scan_action.get("ok")) and (bool(fix_action.get("ok")) if apply_code_fix else True),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": int((datetime.now(timezone.utc) - started_at).total_seconds()),
        "mode": {
            "apply_code_fix": bool(apply_code_fix),
        },
        "actions": {
            "autonomous_intelligence": {
                "ok": bool((autonomous or {}).get("ok")),
                "path": str(logs_dir / "autonomous_intelligence_last.json"),
            },
            "scan": scan_action,
            "scan_fix": fix_action,
        },
        "analytics_snapshot": {
            "workspace": analytics.get("workspace", {}),
            "microsoft365": analytics.get("microsoft365", {}),
            "ai": analytics.get("ai", {}),
        },
        "scan_summary": scan_summary,
    }

    hints = _build_evolution_hints(analytics, scan_summary, cycle_payload)
    cycle_payload["hints"] = hints

    last_path = logs_dir / "ai_evolution_last.json"
    history_path = logs_dir / "ai_evolution_history.jsonl"
    last_path.write_text(json.dumps(cycle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as hf:
        hf.write(json.dumps(cycle_payload, ensure_ascii=False) + "\n")

    return cycle_payload


@router.get("/intelligence/evolution-status")
async def intelligence_evolution_status():
    last_path = _logs_dir() / "ai_evolution_last.json"
    if not last_path.exists():
        return {
            "ok": True,
            "has_data": False,
            "message": "Aún no hay ciclo de evolución generado. Ejecuta /agente/intelligence/evolution-cycle",
            "data": {},
        }
    return {
        "ok": True,
        "has_data": True,
        "data": _safe_json_read(last_path),
        "path": str(last_path),
    }


@router.post("/intelligence/foda-critico")
async def intelligence_foda_critico(request: FodaCriticalRequest):
    started = datetime.now(timezone.utc)
    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    analytics = await control_center_analytics()
    evolution = await intelligence_evolution_status() if request.incluir_evolucion else {"ok": True, "has_data": False, "data": {}}
    alerts = await agente_alerts(limit=12) if request.incluir_alertas else {"ok": True, "items": []}

    context_payload = {
        "analytics": {
            "workspace": analytics.get("workspace", {}),
            "microsoft365": analytics.get("microsoft365", {}),
            "ai": analytics.get("ai", {}),
            "charts": analytics.get("charts", {}),
        },
        "evolution": (evolution or {}).get("data", {}),
        "alerts": (alerts or {}).get("items", []),
        "extra": request.contexto_extra,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    flags = _provider_flags()
    provider_from_decider = {
        "claude": "anthropic",
        "grok": "grok",
        "gemini": "gemini",
        "openai": "openai",
    }
    final_decider = (request.decisor_final or "claude").strip().lower()
    final_provider = provider_from_decider.get(final_decider, "anthropic")

    review_order = ["anthropic", "openai", "gemini", "grok"]
    if request.modo_ahorro:
        review_order = [final_provider]

    provider_reviews: List[Dict] = []
    for provider in review_order:
        if not flags.get(provider):
            provider_reviews.append({
                "provider": provider,
                "ok": False,
                "error": "API key no configurada",
                "skipped": True,
            })
            continue
        prompt = _swot_review_prompt(provider, request.objetivo, context_payload)
        provider_reviews.append(_call_provider_review(provider, prompt))

    consensus_result_payload: Dict = {
        "decider": final_decider,
        "ok": False,
        "content": "",
        "error": f"{final_decider} no disponible",
    }

    if flags.get(final_provider):
        consensus_prompt = _swot_consensus_prompt(final_decider.capitalize(), request.objetivo, provider_reviews, context_payload)
        consensus_result = _call_provider_review(final_provider, consensus_prompt)
        consensus_result_payload = {
            "decider": final_decider,
            "ok": bool(consensus_result.get("ok")),
            "model": consensus_result.get("model"),
            "content": consensus_result.get("content", ""),
            "error": consensus_result.get("error"),
            "duration_ms": consensus_result.get("duration_ms"),
        }
    else:
        first_ok = next((r for r in provider_reviews if r.get("ok")), None)
        if first_ok:
            consensus_result_payload = {
                "decider": "fallback_non_decider",
                "ok": True,
                "model": first_ok.get("model"),
                "content": (
                    f"[Consenso provisional: {final_decider} no disponible; se usa fallback temporal.]\n\n"
                    + str(first_ok.get("content") or "")
                ),
                "error": f"{final_decider} no disponible/configurado",
            }

    payload = {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": int((datetime.now(timezone.utc) - started).total_seconds()),
        "objective": request.objetivo,
        "settings": {
            "decisor_final": final_decider,
            "modo_ahorro": bool(request.modo_ahorro),
        },
        "providers": flags,
        "reviews": provider_reviews,
        "consensus": consensus_result_payload,
        "accion_correctiva": _build_foda_corrective_actions(
            objective=request.objetivo,
            context_payload=context_payload,
            provider_reviews=provider_reviews,
            consensus_payload=consensus_result_payload,
            settings={
                "decisor_final": final_decider,
                "modo_ahorro": bool(request.modo_ahorro),
            },
        ),
        "context_snapshot": {
            "workspace": context_payload["analytics"].get("workspace", {}),
            "microsoft365": context_payload["analytics"].get("microsoft365", {}),
            "ai": context_payload["analytics"].get("ai", {}),
            "alerts_count": len(context_payload.get("alerts") or []),
            "has_evolution": bool((evolution or {}).get("has_data")),
        },
    }

    last_path = logs_dir / "ai_foda_critico_last.json"
    history_path = logs_dir / "ai_foda_critico_history.jsonl"
    last_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as hf:
        hf.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return payload


@router.get("/intelligence/foda-status")
async def intelligence_foda_status():
    last_path = _logs_dir() / "ai_foda_critico_last.json"
    if not last_path.exists():
        return {
            "ok": True,
            "has_data": False,
            "message": "Aún no hay informe FODA crítico. Ejecuta /agente/intelligence/foda-critico",
            "data": {},
        }
    data = _safe_json_read(last_path)
    if isinstance(data, dict) and not data.get("accion_correctiva"):
        context_payload = {
            "analytics": {
                "workspace": (data.get("context_snapshot") or {}).get("workspace", {}),
                "microsoft365": (data.get("context_snapshot") or {}).get("microsoft365", {}),
                "ai": (data.get("context_snapshot") or {}).get("ai", {}),
            },
            "alerts": [],
            "evolution": {},
        }
        data["accion_correctiva"] = _build_foda_corrective_actions(
            objective=str(data.get("objective") or "FODA crítico NEXO"),
            context_payload=context_payload,
            provider_reviews=(data.get("reviews") or []),
            consensus_payload=(data.get("consensus") or {}),
            settings=(data.get("settings") or {}),
        )

    return {
        "ok": True,
        "has_data": True,
        "data": data,
        "path": str(last_path),
    }


@router.get("/alerts")
async def agente_alerts(limit: int = 10):
    limit = max(1, min(int(limit or 10), 50))
    now_iso = datetime.now(timezone.utc).isoformat()
    alerts: List[Dict] = []

    sync_totals = (_safe_json_read(_logs_dir() / "sync_drive_last.json") or {}).get("totals", {}) or {}
    sync_errors = int(sync_totals.get("errors", 0) or 0)
    if sync_errors > 0:
        alerts.append({
            "type": "sync",
            "level": "high" if sync_errors >= 3 else "medium",
            "message": f"Errores en sincronización Drive: {sync_errors}",
            "time": now_iso,
        })

    autonomous = _safe_json_read(_logs_dir() / "autonomous_intelligence_last.json") or {}
    briefing = (((autonomous.get("briefing") or {}).get("briefing") or "") if isinstance(autonomous, dict) else "").strip()
    if briefing:
        alerts.append({
            "type": "intelligence",
            "level": "medium",
            "message": briefing[:180] + ("..." if len(briefing) > 180 else ""),
            "time": str((autonomous.get("timestamp") or now_iso)),
        })

    analytics = await control_center_analytics()
    workspace = analytics.get("workspace", {}) or {}
    if workspace.get("drive_error"):
        alerts.append({
            "type": "drive",
            "level": "high",
            "message": f"Drive error: {workspace.get('drive_error')}",
            "time": now_iso,
        })
    if workspace.get("photos_error"):
        alerts.append({
            "type": "photos",
            "level": "medium",
            "message": f"Photos error: {workspace.get('photos_error')}",
            "time": now_iso,
        })

    if not alerts:
        alerts.append({
            "type": "system",
            "level": "low",
            "message": "Sin alertas críticas activas. Sistema estable.",
            "time": now_iso,
        })

    return {
        "ok": True,
        "count": len(alerts),
        "items": alerts[:limit],
    }


@router.get("/warroom/ai-control")
async def warroom_ai_control(include_autonomous_cycle: bool = False):
    privacy_mode = _is_truthy_env("NEXO_WARROOM_PRIVACY_MODE", "true")
    now_iso = datetime.now(timezone.utc).isoformat()
    analytics = await control_center_analytics()
    alerts_payload = await agente_alerts(limit=8)

    stream_snapshot = {
        "ok": False,
        "obs_connected": False,
        "discord_connected": False,
        "stream_active": False,
        "blockers": ["Stream state unavailable"],
    }

    try:
        from NEXO_CORE import config as core_config
        from NEXO_CORE.core.state_manager import state_manager

        s = state_manager.snapshot()
        blockers: List[str] = []
        if not core_config.OBS_ENABLED:
            blockers.append("OBS_ENABLED=false")
        elif not s.get("obs_connected"):
            blockers.append("OBS desconectado")

        if not core_config.DISCORD_ENABLED:
            blockers.append("DISCORD_ENABLED=false")
        elif not core_config.DISCORD_WEBHOOK_URL:
            blockers.append("DISCORD_WEBHOOK_URL vacío")
        elif not s.get("discord_connected"):
            blockers.append("Discord desconectado")

        stream_snapshot = {
            "ok": len(blockers) == 0,
            "obs_connected": bool(s.get("obs_connected")),
            "discord_connected": bool(s.get("discord_connected")),
            "stream_active": bool(s.get("stream_active")),
            "current_scene": s.get("current_scene"),
            "blockers": blockers,
            "last_error": s.get("last_error"),
        }
    except Exception as exc:
        stream_snapshot["blockers"] = [f"No se pudo leer estado stream: {exc}"]

    autonomous_status = await intelligence_autonomous_status()
    evolution_status = await intelligence_evolution_status()
    if include_autonomous_cycle and not autonomous_status.get("has_data"):
        try:
            _ = await intelligence_autonomous_cycle()
            autonomous_status = await intelligence_autonomous_status()
        except Exception:
            pass

    workspace = analytics.get("workspace", {}) or {}
    m365 = analytics.get("microsoft365", {}) or {}
    ai = analytics.get("ai", {}) or {}
    charts = analytics.get("charts", {}) or {}

    drive_sync_values = (charts.get("drive_sync") or {}).get("values") or [0, 0, 0, 0]
    analyzed = int(drive_sync_values[0] or 0) if len(drive_sync_values) > 0 else 0
    classified = int(drive_sync_values[1] or 0) if len(drive_sync_values) > 1 else 0
    sync_errors = int(drive_sync_values[3] or 0) if len(drive_sync_values) > 3 else 0

    guides: List[str] = []
    guides.append("Prioriza ejecutar SYNC si hay documentos pendientes y errores en cero.")
    if sync_errors > 0:
        guides.append(f"Detectados {sync_errors} errores de sync: revisa credenciales Drive/Photos y reintenta con backoff.")
    if not stream_snapshot.get("ok"):
        guides.append("Stream no listo: corrige blockers de OBS/Discord antes de operar transmisión.")
    if not workspace.get("ok"):
        guides.append("Workspace sin señal: valida tokens de Google y permisos de Drive/Photos.")
    if not m365.get("ok"):
        guides.append("OneDrive sin datos recientes: verificar Graph token o fallback local_onedrive.")
    if int(ai.get("total_documentos", 0) or 0) == 0:
        guides.append("Sin corpus RAG: ingesta documentos críticos para mejorar respuestas de IA.")

    if len(guides) < 4:
        guides.append("Sistema estable: mantén polling inteligente y ejecuta revisión de integridad cada 15 minutos.")

    code_improvements = [
        {
            "priority": "high",
            "title": "Escaneo automático de código",
            "command": ".\\.venv\\Scripts\\python.exe nexo_autosupervisor.py --scan",
            "reason": "Detecta regressions y deuda técnica antes de producción.",
        },
        {
            "priority": "high",
            "title": "Auto-reparación guiada",
            "command": ".\\.venv\\Scripts\\python.exe nexo_autosupervisor.py --scan --fix",
            "reason": "Corrige issues repetitivos de estilo/estructura en lote.",
        },
        {
            "priority": "medium",
            "title": "Sincronización unificada completa",
            "command": ".\\.venv\\Scripts\\python.exe scripts\\run_unified_sync_full.py",
            "reason": "Refresca datos reales para evitar métricas vacías en War Room.",
        },
    ]

    summary = {
        "drive_recent": int(workspace.get("drive_recent", 0) or 0),
        "photos_recent": int(workspace.get("photos_recent", 0) or 0),
        "onedrive_recent": int(m365.get("onedrive_recent", 0) or 0),
        "rag_docs": int(ai.get("total_documentos", 0) or 0),
        "sync_analyzed": analyzed,
        "sync_classified": classified,
        "sync_errors": sync_errors,
        "alerts": int((alerts_payload or {}).get("count", 0) or 0),
    }

    stream_out = stream_snapshot
    analytics_out = analytics
    alerts_out = alerts_payload
    if privacy_mode:
        stream_out = _sanitize_warroom_payload(stream_snapshot)
        analytics_out = _sanitize_warroom_payload(analytics)
        alerts_out = _sanitize_warroom_payload(alerts_payload)

    return {
        "ok": True,
        "timestamp": now_iso,
        "privacy": {"enabled": privacy_mode},
        "data": {
            "summary": summary,
            "stream": stream_out,
            "alerts": alerts_out,
            "analytics": analytics_out,
            "autonomous": autonomous_status,
            "evolution": evolution_status,
        },
        "guides": guides,
        "code_improvements": code_improvements,
    }


@router.post("/warroom/apply-code-improvements")
async def warroom_apply_code_improvements():
    root = _workspace_root()
    script_path = root / "nexo_autosupervisor.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"No existe script: {script_path}")

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    run_log = logs_dir / "warroom_ai_code_improve.log"
    status_path = logs_dir / "warroom_ai_code_improve_status.json"

    cmd = [sys.executable, str(script_path), "--scan", "--fix"]

    try:
        with run_log.open("a", encoding="utf-8") as lf:
            lf.write(f"\n[{datetime.now(timezone.utc).isoformat()}] START {' '.join(cmd)}\n")
            proc = subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=lf,
                stderr=lf,
                shell=False,
            )
        status_payload = {
            "ok": True,
            "running": True,
            "pid": proc.pid,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "command": cmd,
            "log": str(run_log),
        }
        status_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return status_payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo iniciar mejora automática: {exc}")


@router.get("/warroom/code-improvements-status")
async def warroom_code_improvements_status():
    status_path = _logs_dir() / "warroom_ai_code_improve_status.json"
    payload = _safe_json_read(status_path)
    if not payload:
        return {"ok": True, "running": False, "message": "Sin ejecuciones registradas"}
    return {"ok": True, **payload}


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


# ─────────────────────────────────────────────────────────────────────────────
# COMPARAR IAs — respuestas paralelas Claude / GPT-4o / Gemini
# ─────────────────────────────────────────────────────────────────────────────

class CompararRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    modelo: str = Field(..., description="'gpt-4o' | 'gemini-1.5-pro'")


@router.post("/comparar")
async def comparar_modelos(request: CompararRequest):
    """
    Llama a GPT-4o o Gemini 1.5 Pro con el mismo prompt.
    Usado por el panel de comparacion de SesionIA.
    """
    modelo = request.modelo.lower().strip()
    query = request.query

    # ── GPT-4o (OpenAI) ───────────────────────────────────────────────────────
    if "gpt" in modelo:
        OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
        if not OPENAI_KEY:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY no configurada")
        try:
            import openai as _openai
            client = _openai.AsyncOpenAI(api_key=OPENAI_KEY)
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": query}],
                max_tokens=1500,
                temperature=0.7,
            )
            respuesta = resp.choices[0].message.content or ""
            return {"ok": True, "modelo": "gpt-4o", "respuesta": respuesta}
        except Exception as e:
            logger.error(f"Error GPT-4o: {e}")
            raise HTTPException(status_code=502, detail=f"Error GPT-4o: {e}")

    # ── Gemini 1.5 Pro (Google) ───────────────────────────────────────────────
    if "gemini" in modelo:
        GEMINI_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_AI_API_KEY", ""))
        if not GEMINI_KEY:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY no configurada")
        try:
            import httpx as _httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_KEY}"
            payload = {
                "contents": [{"parts": [{"text": query}]}],
                "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7},
            }
            async with _httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, json=payload)
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Gemini API error {r.status_code}: {r.text[:200]}")
            data = r.json()
            respuesta = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
            )
            return {"ok": True, "modelo": "gemini-1.5-pro", "respuesta": respuesta}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error Gemini: {e}")
            raise HTTPException(status_code=502, detail=f"Error Gemini: {e}")

    raise HTTPException(status_code=400, detail=f"Modelo '{modelo}' no soportado. Usa 'gpt-4o' o 'gemini-1.5-pro'")
