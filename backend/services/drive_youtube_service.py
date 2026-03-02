"""Pipeline Drive -> YouTube para resumen diario.

Flujo:
1) Busca archivo de resumen reciente en Drive.
2) Descarga contenido de texto.
3) Genera clip vertical simple con moviepy.
4) Sube video a YouTube.
"""

from __future__ import annotations

import os
import tempfile
import logging
import importlib
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from services.connectors.google_connector import list_recent_files_detailed, download_drive_file
from services.comunidad.youtube_reader import upload_video_summary

logger = logging.getLogger(__name__)

API_DELAY_SECONDS = float(os.getenv("NEXO_API_DELAY_SECONDS", "0"))
VIDEO_BITRATE = os.getenv("NEXO_VIDEO_BITRATE", "1000k")
VIDEO_WITH_TEXT = os.getenv("NEXO_VIDEO_WITH_TEXT", "false").strip().lower() in {"1", "true", "yes", "on"}
X_AUTO_PUBLISH = os.getenv("NEXO_X_AUTO_PUBLISH", "false").strip().lower() in {"1", "true", "yes", "on"}
X_GROK_VALIDATE = os.getenv("NEXO_X_GROK_VALIDATE", "false").strip().lower() in {"1", "true", "yes", "on"}


def _discover_ffmpeg() -> Optional[str]:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

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
            return str(match)

    return None

SUPPORTED_TEXT_MIME = {
    "text/plain",
    "text/markdown",
    "application/json",
}
SUPPORTED_TEXT_EXT = {".txt", ".md", ".json"}


def list_recent_files_in_root(max_results: int = 20) -> List[Dict]:
    """Lista recientes de Drive para inspección rápida desde API."""
    max_results = max(1, min(int(max_results), 200))
    files = list_recent_files_detailed(max_results=max_results)
    if API_DELAY_SECONDS > 0:
        time.sleep(API_DELAY_SECONDS)
    return files


def _is_summary_candidate(file_info: Dict) -> bool:
    name = (file_info.get("name") or "").lower()
    mime_type = (file_info.get("mimeType") or "").lower()
    ext = Path(name).suffix.lower()
    has_keyword = any(k in name for k in ["resumen", "summary", "daily_resume", "daily-summary"])
    is_supported = mime_type in SUPPORTED_TEXT_MIME or ext in SUPPORTED_TEXT_EXT
    return has_keyword and is_supported


def find_latest_summary_file(max_results: int = 50) -> Optional[Dict]:
    files = list_recent_files_detailed(max_results=max_results)
    for file_info in files:
        if _is_summary_candidate(file_info):
            return file_info
    return None


def download_summary_text(file_id: str, file_name: str) -> str:
    suffix = Path(file_name or "resumen.txt").suffix or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name

    try:
        download_drive_file(file_id, tmp_path)
        if API_DELAY_SECONDS > 0:
            time.sleep(API_DELAY_SECONDS)
        content = Path(tmp_path).read_text(encoding="utf-8", errors="ignore")
        return content
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def create_simple_summary_video(text: str, output_path: str) -> str:
    """Genera un video vertical muy simple con texto usando moviepy."""
    logger.info("Generando video temporal en %s", output_path)
    ffmpeg_path = _discover_ffmpeg()
    if ffmpeg_path:
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", ffmpeg_path)

    try:
        moviepy_mod = importlib.import_module("moviepy")
    except Exception as exc:
        raise RuntimeError(
            f"moviepy no disponible o no funcional: {exc}. Instala moviepy y ffmpeg para habilitar esta función."
        )

    if not ffmpeg_path and not os.getenv("IMAGEIO_FFMPEG_EXE"):
        raise RuntimeError(
            "ffmpeg no está disponible (PATH/IMAGEIO_FFMPEG_EXE). "
            "Instala ffmpeg o define IMAGEIO_FFMPEG_EXE con ruta absoluta."
        )

    ColorClip = getattr(moviepy_mod, "ColorClip", None)
    TextClip = getattr(moviepy_mod, "TextClip", None)
    CompositeVideoClip = getattr(moviepy_mod, "CompositeVideoClip", None)

    if ColorClip is None:
        raise RuntimeError("moviepy instalado pero sin ColorClip disponible")

    def _with_duration(clip, duration):
        if hasattr(clip, "with_duration"):
            return clip.with_duration(duration)
        return clip.set_duration(duration)

    def _with_position(clip, position):
        if hasattr(clip, "with_position"):
            return clip.with_position(position)
        return clip.set_position(position)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        lines = ["Resumen diario sin contenido."]

    bg = _with_duration(ColorClip(size=(1080, 1920), color=(18, 18, 24)), 10)
    final = bg

    if VIDEO_WITH_TEXT and TextClip is not None and CompositeVideoClip is not None:
        try:
            headline = " | ".join(lines[:2])[:180]
            try:
                txt = TextClip(
                    text=headline,
                    font_size=56,
                    color="white",
                    method="caption",
                    size=(980, 1500),
                    text_align="center",
                )
            except TypeError:
                txt = TextClip(
                    headline,
                    fontsize=56,
                    color="white",
                    method="caption",
                    size=(980, 1500),
                    align="center",
                )
            txt = _with_position(_with_duration(txt, 10), "center")
            final = _with_duration(CompositeVideoClip([bg, txt]), 10)
        except Exception as exc:
            logger.warning("No fue posible renderizar texto en el video; se usa fallback sin texto: %s", exc)
    elif not VIDEO_WITH_TEXT:
        logger.info("Render de texto desactivado (NEXO_VIDEO_WITH_TEXT=false)")

    logger.info("Escribiendo video con codec libx264 y bitrate %s", VIDEO_BITRATE)
    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        bitrate=VIDEO_BITRATE,
        audio=False,
        logger=None,
    )
    return output_path


def daily_resume_pipeline(dry_run: bool = True, max_scan: int = 50, privacy_status: str = "unlisted") -> Dict:
    logger.info("Iniciando pipeline diario Drive -> YouTube")

    logger.info("Buscando resumen reciente en Drive (max_scan=%s)", max_scan)
    summary_file = find_latest_summary_file(max_results=max_scan)
    if not summary_file:
        return {"ok": False, "status": "no_summary_found", "message": "No se encontró archivo de resumen reciente en Drive."}

    file_id = summary_file.get("id")
    file_name = summary_file.get("name") or "resumen.txt"
    if not file_id:
        return {"ok": False, "status": "invalid_summary_file", "message": "Archivo resumen sin id."}

    logger.info("Descargando resumen: %s (%s)", file_name, file_id)
    text_content = download_summary_text(file_id, file_name)
    text_content = (text_content or "").strip()
    if not text_content:
        return {
            "ok": False,
            "status": "empty_summary",
            "message": "El archivo resumen está vacío.",
            "summary_file": summary_file,
        }

    preview = text_content[:500]
    if dry_run:
        return {
            "ok": True,
            "status": "dry_run",
            "summary_file": summary_file,
            "preview": preview,
            "chars": len(text_content),
        }

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
        video_path = tmp_video.name

    try:
        logger.info("Creando video desde resumen (%s chars)", len(text_content))
        create_simple_summary_video(text_content, video_path)
        title = f"Resumen SIG Diario - {datetime.now().strftime('%Y-%m-%d')}"
        description = (
            "Resumen automático generado por NEXO SOBERANO.\n\n"
            + preview
            + ("..." if len(text_content) > 500 else "")
        )
        logger.info("Subiendo video a YouTube con privacy_status=%s", privacy_status)
        upload_result = upload_video_summary(
            title=title,
            description=description,
            file_bytes=Path(video_path).read_bytes(),
            filename=f"resumen_{datetime.now().strftime('%Y%m%d')}.mp4",
            tags=["nexo_soberano", "sig", "resumen_diario", "geopolitica"],
            privacy_status=privacy_status,
            category_id="25",
        )
        safe_upload = {
            "ok": bool(upload_result.get("ok")),
            "video_id": upload_result.get("video_id"),
            "url": upload_result.get("url"),
        }
        if "error" in upload_result:
            safe_upload["error"] = str(upload_result.get("error"))
        if API_DELAY_SECONDS > 0:
            time.sleep(API_DELAY_SECONDS)

        x_result = None
        if safe_upload.get("ok") and X_AUTO_PUBLISH:
            try:
                from backend.services.x_publisher import post_to_x, ask_grok_via_x

                grok_probe = None
                if X_GROK_VALIDATE:
                    try:
                        grok_probe = ask_grok_via_x(
                            question="Valida consistencia factual de este resumen SIG.",
                            context=preview,
                        )
                    except Exception as grok_exc:
                        grok_probe = {"ok": False, "error": str(grok_exc)}

                tweet_text = (
                    f"Resumen SIG Diario {datetime.now().strftime('%Y-%m-%d')}\n"
                    f"{safe_upload.get('url') or ''}\n"
                    "#NexoSoberano #Geopolitica"
                ).strip()
                posted = post_to_x(tweet_text)
                x_result = {"post": posted, "grok_probe": grok_probe}
            except Exception as exc:
                x_result = {"ok": False, "error": str(exc)}

        logger.info("Respuesta de subida YouTube: ok=%s", bool(safe_upload.get("ok")))
        return {
            "ok": bool(safe_upload.get("ok")),
            "status": "uploaded" if safe_upload.get("ok") else "upload_failed",
            "summary_file": summary_file,
            "youtube": safe_upload,
            "x": x_result,
        }
    finally:
        try:
            os.remove(video_path)
        except Exception:
            pass
