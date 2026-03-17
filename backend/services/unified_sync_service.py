"""Sincronización unificada entre Google Photos, Google Drive y OneDrive.

Objetivo:
- Clasificar automáticamente archivos en carpetas de Drive.
- Migrar Google Photos a Drive.
- Importar recientes de OneDrive hacia Drive.
"""

from __future__ import annotations

import logging
import os
import re
import time
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import Counter

from services.connectors.google_connector import GoogleConnector
from services.connectors.microsoft_connector import MicrosoftConnector
from services.connectors.local_onedrive_connector import (
    list_recent_local_onedrive_files,
    read_local_onedrive_bytes,
    resolve_onedrive_local_root,
)
from services.comunidad.youtube_reader import (
    list_recent_channel_videos,
    get_video_transcript,
    save_transcript_to_json,
)
from backend import config

from backend.services.intelligence.media_processor import media_processor
import asyncio

logger = logging.getLogger(__name__)


ROOT_DRIVE_FOLDER = (os.getenv("NEXO_DRIVE_ROOT_FOLDER", "NEXO_SOBERANO_CLASIFICADO") or "NEXO_SOBERANO_CLASIFICADO").strip()
LIMBO_FOLDER_NAME = "00_ANALISIS_24H"
MANUAL_REVIEW_FOLDER_NAME = "01_REVISION_MANUAL"

SOURCE_FOLDERS = {
    "google_photos": (os.getenv("NEXO_DRIVE_FOLDER_GOOGLE_PHOTOS", "GooglePhotos") or "GooglePhotos").strip(),
    "google_drive": (os.getenv("NEXO_DRIVE_FOLDER_GOOGLE_DRIVE", "GoogleDrive") or "GoogleDrive").strip(),
    "onedrive": (os.getenv("NEXO_DRIVE_FOLDER_ONEDRIVE", "OneDrive") or "OneDrive").strip(),
}
GEOPOLITICA_FOLDER = (os.getenv("NEXO_DRIVE_FOLDER_GEOPOLITICA", "GEOPOLITICA") or "GEOPOLITICA").strip()
GEOPOLITICA_BUCKETS = {
    "israel": (os.getenv("NEXO_DRIVE_FOLDER_ISRAEL", "ISRAEL") or "ISRAEL").strip(),
    "argentina": (os.getenv("NEXO_DRIVE_FOLDER_ARGENTINA", "ARGENTINA") or "ARGENTINA").strip(),
    "otros_conflictos": (os.getenv("NEXO_DRIVE_FOLDER_OTROS_CONFLICTOS", "OTROS_CONFLICTOS") or "OTROS_CONFLICTOS").strip(),
}

KEYWORDS_ISRAEL = {
    "israel", "gaza", "hamas", "idf", "jerusalem", "jerusalen", "telaviv", "tel aviv", "hezbollah", "netanyahu",
}
KEYWORDS_ARGENTINA = {
    "argentina", "milei", "buenos aires", "rosada", "patagonia", "malvinas", "peron", "peronismo",
}

DEFAULT_CONFLICT_TAXONOMY = {
    "ISRAEL": {"israel", "gaza", "hamas", "idf", "jerusalem", "jerusalen", "telaviv", "tel aviv", "hezbollah", "netanyahu"},
    "ARGENTINA": {"argentina", "milei", "buenos aires", "rosada", "patagonia", "malvinas", "peron", "peronismo"},
    "UCRANIA_RUSIA": {"ucrania", "ukraine", "rusia", "russia", "donbass", "crimea", "moscu", "moscow", "kiev", "kyiv", "zelensky", "putin"},
    "IRAN": {"iran", "teheran", "tehran", "persa", "khamenei", "irgc"},
    "CHINA_TAIWAN": {"china", "taiwan", "beijing", "pekin", "xi jinping", "taipei", "mar del sur de china"},
    "SIRIA": {"siria", "syria", "alepo", "damasco", "damascus", "assad"},
    "VENEZUELA": {"venezuela", "maduro", "caracas", "guaido", "pdvsa"},
    "EEUU": {"eeuu", "usa", "u.s.", "estados unidos", "washington", "trump", "biden", "pentagono", "pentagon"},
    "EUROPA": {"otan", "nato", "ue", "european union", "bruselas", "brussels", "francia", "alemania", "reino unido", "uk"},
    "LATAM": {"latam", "america latina", "colombia", "chile", "peru", "ecuador", "mexico", "brasil", "bolivia", "paraguay", "uruguay"},
}


def _normalize_bucket_label(value: str) -> str:
    label = re.sub(r"[^0-9A-Za-zÁÉÍÓÚáéíóúÑñÜü _\-]", " ", (value or "").strip())
    label = re.sub(r"\s+", " ", label).strip()
    if not label:
        return GEOPOLITICA_BUCKETS["otros_conflictos"]
    return label.upper().replace(" ", "_")


def _tokenize_text(value: str) -> set[str]:
    normalized = (value or "").lower()
    chunks = re.split(r"[^a-z0-9áéíóúñü]+", normalized)
    return {chunk for chunk in chunks if len(chunk) >= 3}


@dataclass
class SyncLimits:
    photos: int = 20
    drive: int = 50
    onedrive: int = 20
    onedrive_max_mb: int = 20
    youtube_per_channel: int = 10
    drive_include_trashed: bool = False
    drive_full_scan: bool = False
    drive_auto_rename: bool = False
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.2


def _safe_name(name: str, fallback: str) -> str:
    value = (name or "").strip()
    if not value:
        return fallback
    return value.replace("/", "-").replace("\\", "-")


def _normalize_name(name: str, fallback: str) -> str:
    value = _safe_name(name, fallback)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[^0-9A-Za-záéíóúÁÉÍÓÚñÑüÜ ._\-()]", "_", value)
    if len(value) > 180:
        ext = Path(value).suffix
        stem = value[: 180 - len(ext)].rstrip(" ._")
        value = f"{stem}{ext}"
    return value or fallback


def _is_retryable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    retryable_tokens = [
        "timeout",
        "timed out",
        "temporar",
        "rate limit",
        "too many requests",
        "connection reset",
        "connection aborted",
        "503",
        "502",
        "500",
        "429",
    ]
    return any(token in text for token in retryable_tokens)


def _extension_from_name(name: str) -> str:
    return Path(name or "").suffix.lower()


def _classify_category(name: str, mime_type: str) -> str:
    mime = (mime_type or "").lower()
    ext = _extension_from_name(name)

    if mime.startswith("image/") or ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}:
        return "IMAGENES"
    if mime.startswith("video/") or ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return "VIDEOS"
    if mime.startswith("audio/") or ext in {".mp3", ".wav", ".ogg", ".m4a"}:
        return "AUDIOS"
    if (
        mime.startswith("text/")
        or mime in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }
        or ext in {".pdf", ".txt", ".md", ".doc", ".docx", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"}
    ):
        return "DOCUMENTOS"
    if mime in {"application/zip", "application/x-7z-compressed", "application/x-rar-compressed"} or ext in {
        ".zip",
        ".7z",
        ".rar",
        ".tar",
        ".gz",
    }:
        return "COMPRIMIDOS"

    return "OTROS"


    return GEOPOLITICA_BUCKETS["otros_conflictos"]


async def _apply_intelligent_analysis(file_path: str, name: str, mime_type: str) -> Optional[Dict]:
    """Llama al MediaProcessor para obtener análisis profundo y ruta inteligente."""
    try:
        result = await media_processor.analyze_and_route(file_path, name, mime_type)
        if result.get("ok"):
            return result["data"]
    except Exception as e:
        logger.error(f"Error en análisis inteligente post-sync: {e}")
    return None


def _extract_text_preview(payload: bytes, name: str, mime_type: str, limit: int = 10000) -> str:
    if not payload:
        return ""
    mime = (mime_type or "").lower()
    ext = _extension_from_name(name)
    textual_ext = {".txt", ".md", ".csv", ".json", ".xml", ".log", ".html", ".htm"}
    if mime.startswith("text/") or ext in textual_ext:
        try:
            return payload[:limit].decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return ""


class UnifiedSyncService:
    def __init__(self):
        self.gc = GoogleConnector()
        self._alerts: List[Dict] = []
        self._folder_cache: Dict[str, List[Dict]] = {}
        self._bucket_taxonomy_cache: Dict[str, Dict[str, set[str]]] = {}

    def _track_alert(self, level: str, source: str, message: str, extra: Optional[Dict] = None):
        event = {
            "level": level,
            "source": source,
            "message": message,
        }
        if extra:
            event.update(extra)
        self._alerts.append(event)

    def _with_retries(self, op_name: str, fn, *args, attempts: int = 3, backoff_seconds: float = 1.2, **kwargs):
        attempts = max(1, int(attempts))
        backoff = max(0.1, float(backoff_seconds))
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                retryable = _is_retryable_error(exc)
                if attempt < attempts and retryable:
                    sleep_for = round(backoff * attempt, 2)
                    logger.warning("%s fallo (%s/%s), reintentando en %ss: %s", op_name, attempt, attempts, sleep_for, exc)
                    self._track_alert(
                        "warning",
                        op_name,
                        "reintento_automatico",
                        {"attempt": attempt, "max_attempts": attempts, "sleep_seconds": sleep_for, "error": str(exc)},
                    )
                    time.sleep(sleep_for)
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"{op_name} failed without captured exception")

    def _get_bucket_taxonomy_for_source(self, source_key: str) -> Dict[str, set[str]]:
        cached = self._bucket_taxonomy_cache.get(source_key)
        if cached is not None:
            return cached

        taxonomy: Dict[str, set[str]] = {
            _normalize_bucket_label(label): set(words)
            for label, words in DEFAULT_CONFLICT_TAXONOMY.items()
        }
        taxonomy[_normalize_bucket_label(GEOPOLITICA_BUCKETS["israel"])] = set(KEYWORDS_ISRAEL)
        taxonomy[_normalize_bucket_label(GEOPOLITICA_BUCKETS["argentina"])] = set(KEYWORDS_ARGENTINA)
        taxonomy.setdefault(_normalize_bucket_label(GEOPOLITICA_BUCKETS["otros_conflictos"]), set())

        source_folder = SOURCE_FOLDERS.get(source_key, source_key)
        try:
            # We want to look at the GLOBAL Geopolitica folder: ROOT_DRIVE_FOLDER/GEOPOLITICA
            geo_folder_id = self.gc.ensure_folder_path([ROOT_DRIVE_FOLDER, GEOPOLITICA_FOLDER])
            folder_items = self.gc.list_files_in_folder(geo_folder_id, 200) or []
            for item in folder_items:
                if (item.get("mimeType") or "") != "application/vnd.google-apps.folder":
                    continue
                bucket_name = _normalize_bucket_label(str(item.get("name") or ""))
                if not bucket_name:
                    continue
                taxonomy.setdefault(bucket_name, set())
                taxonomy[bucket_name].update(_tokenize_text(bucket_name.replace("_", " ")))
        except Exception as exc:
            self._track_alert("warning", "taxonomy", "folder_learning_failed", {"source_key": source_key, "error": str(exc)})

        self._bucket_taxonomy_cache[source_key] = taxonomy
        return taxonomy

    def _infer_conflict_bucket(self, source_key: str, item_name: str, extra_text: str = "") -> Dict:
        taxonomy = self._get_bucket_taxonomy_for_source(source_key)
        text = f"{item_name or ''}\n{extra_text or ''}".lower()
        tokens = _tokenize_text(text)
        best_bucket = _normalize_bucket_label(GEOPOLITICA_BUCKETS["otros_conflictos"])
        best_score = 0
        matched_terms: List[str] = []

        for bucket, keywords in taxonomy.items():
            if not keywords:
                continue
            hits = [kw for kw in keywords if kw in text or kw in tokens]
            score = len(hits)
            if score > best_score:
                best_score = score
                best_bucket = bucket
                matched_terms = sorted(set(hits))[:10]

        return {
            "bucket": best_bucket,
            "score": best_score,
            "matched_terms": matched_terms,
            "taxonomy_size": len(taxonomy),
        }

    def _build_target_parts(self, source_key: str, category: str, item_name: str = "", extra_text: str = "", conflict_bucket: Optional[str] = None) -> List[str]:
        source_folder = SOURCE_FOLDERS[source_key]
        target_parts = [ROOT_DRIVE_FOLDER, source_folder]
        if source_key in {"google_photos", "onedrive"}:
            selected_bucket = conflict_bucket
            if not selected_bucket:
                selected_bucket = self._infer_conflict_bucket(source_key, item_name, extra_text).get("bucket")
            target_parts.extend([GEOPOLITICA_FOLDER, _normalize_bucket_label(str(selected_bucket or ""))])
        target_parts.append(category)
        return target_parts

    def _ensure_target_folder(
        self,
        source_key: str,
        category: str,
        item_name: str = "",
        extra_text: str = "",
        conflict_bucket: Optional[str] = None,
    ) -> str:
        return self.gc.ensure_folder_path(
            self._build_target_parts(
                source_key,
                category,
                item_name,
                extra_text=extra_text,
                conflict_bucket=conflict_bucket,
            )
        )

    def _already_synced(self, source: str, source_id: str):
        return self.gc.find_file_by_app_properties({"nexo_source": source, "nexo_source_id": source_id})

    def _find_duplicate_by_hash(self, sha1_hex: str):
        if not sha1_hex:
            return None
        return self.gc.find_file_by_app_properties({"nexo_content_sha1": sha1_hex})

    def _list_folder_cached(self, folder_id: str) -> List[Dict]:
        if folder_id in self._folder_cache:
            return self._folder_cache[folder_id]
        try:
            files = self.gc.list_files_in_folder(folder_id, 500) or []
        except Exception:
            files = []
        self._folder_cache[folder_id] = files
        return files

    def _build_learning_snapshot(self, result: Dict) -> Dict:
        by_category = Counter()
        by_bucket = Counter()
        by_status = Counter()
        by_country_or_conflict = Counter()
        for source in ("google_photos", "google_drive", "onedrive", "youtube"):
            for item in (result.get(source, {}).get("items") or []):
                status = str(item.get("status") or "unknown")
                by_status[status] += 1
                category = item.get("category")
                if category:
                    by_category[str(category)] += 1
                bucket = item.get("conflict_bucket")
                if bucket:
                    by_bucket[str(bucket)] += 1
                    by_country_or_conflict[str(bucket)] += 1
        return {
            "categories": dict(sorted(by_category.items(), key=lambda x: (-x[1], x[0]))),
            "conflict_buckets": dict(sorted(by_bucket.items(), key=lambda x: (-x[1], x[0]))),
            "country_or_conflict": dict(sorted(by_country_or_conflict.items(), key=lambda x: (-x[1], x[0]))),
            "statuses": dict(sorted(by_status.items(), key=lambda x: (-x[1], x[0]))),
        }

    def sync(self, limits: Optional[SyncLimits] = None, dry_run: bool = False, youtube_channels: Optional[List[str]] = None) -> Dict:
        limits = limits or SyncLimits()
        result = {
            "ok": True,
            "dry_run": dry_run,
            "alerts": [],
            "google_photos": {"imported": 0, "skipped": 0, "errors": 0, "items": []},
            "google_drive": {"analyzed": 0, "classified": 0, "skipped": 0, "errors": 0, "items": []},
            "onedrive": {"imported": 0, "skipped": 0, "errors": 0, "items": []},
            "youtube": {"processed": 0, "skipped": 0, "errors": 0, "items": []},
        }

        self._sync_google_photos(result, limits, dry_run)
        self._classify_google_drive(result, limits, dry_run)
        self._sync_onedrive(result, limits, dry_run)
        self._sync_youtube(result, limits, dry_run, youtube_channels=youtube_channels or [])
        result["learning"] = self._build_learning_snapshot(result)
        result["alerts"] = list(self._alerts)

        # Notificación Discord si lote > 5 archivos
        if not dry_run:
            self._notify_discord_batch(result)

        return result

    def _notify_discord_batch(self, result: Dict) -> None:
        """Envía reporte a Discord si el lote procesó ≥5 archivos."""
        try:
            total = (
                result.get("google_photos", {}).get("imported", 0)
                + result.get("google_drive", {}).get("classified", 0)
                + result.get("onedrive", {}).get("imported", 0)
                + result.get("youtube", {}).get("processed", 0)
            )
            if total < 5:
                return

            # Contar por categoría semántica
            from backend.services.semantic_classifier import CATEGORIES
            categorias: Dict[str, int] = {k: 0 for k in CATEGORIES}
            for source in ("google_drive", "google_photos", "onedrive"):
                for item in result.get(source, {}).get("items", []):
                    cat = item.get("categoria") or item.get("category") or "Archivo_Personal"
                    if cat in categorias:
                        categorias[cat] += 1

            cat_lines = "\n".join(
                f"  • **{k.replace('_', ' ')}**: {v}" for k, v in categorias.items() if v > 0
            )
            msg = (
                f"🗂️ **Refinería procesó {total} archivos**\n"
                f"{cat_lines or '  • Sin clasificación semántica'}\n\n"
                f"📦 OneDrive: {result.get('onedrive',{}).get('imported',0)} | "
                f"Drive: {result.get('google_drive',{}).get('classified',0)} | "
                f"Photos: {result.get('google_photos',{}).get('imported',0)}"
            )

            import asyncio
            from NEXO_CORE.services.discord_manager import discord_manager
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(discord_manager.send_message(msg))
            else:
                loop.run_until_complete(discord_manager.send_message(msg))
        except Exception as exc:
            logger.warning("Discord batch notify falló: %s", exc)

    def _sync_youtube(self, result: Dict, limits: SyncLimits, dry_run: bool, youtube_channels: List[str]):
        if not youtube_channels or limits.youtube_per_channel <= 0:
            result["youtube"]["items"].append({"status": "skipped", "reason": "sin_canales_o_limite"})
            return

        for channel_id in youtube_channels:
            try:
                videos = list_recent_channel_videos(channel_id=channel_id, max_results=limits.youtube_per_channel)
            except Exception as exc:
                logger.error("Error listando canal YouTube %s: %s", channel_id, exc)
                result["youtube"]["errors"] += 1
                result["youtube"]["items"].append({"channel_id": channel_id, "status": "error", "error": str(exc)})
                continue

            for vid in videos:
                video_id = str(vid.get("video_id") or "")
                if not video_id:
                    result["youtube"]["skipped"] += 1
                    continue

                transcript_path = config.DOCS_DIR / f"youtube_transcript_{video_id}.json"
                if transcript_path.exists():
                    result["youtube"]["skipped"] += 1
                    result["youtube"]["items"].append({
                        "channel_id": channel_id,
                        "video_id": video_id,
                        "status": "already_indexed",
                    })
                    continue

                if dry_run:
                    result["youtube"]["processed"] += 1
                    result["youtube"]["items"].append({
                        "channel_id": channel_id,
                        "video_id": video_id,
                        "status": "dry_run_process",
                        "title": vid.get("title", ""),
                    })
                    continue

                transcript = get_video_transcript(video_id, languages=["es", "en"])
                if not transcript.get("ok"):
                    result["youtube"]["errors"] += 1
                    result["youtube"]["items"].append({
                        "channel_id": channel_id,
                        "video_id": video_id,
                        "status": "error_transcript",
                        "error": transcript.get("error", "transcript_error"),
                    })
                    continue

                saved = save_transcript_to_json(video_id, transcript, config.DOCS_DIR)
                result["youtube"]["processed"] += 1
                result["youtube"]["items"].append({
                    "channel_id": channel_id,
                    "video_id": video_id,
                    "status": "indexed",
                    "title": vid.get("title", ""),
                    "saved_file": str(saved),
                })

    def _sync_google_photos(self, result: Dict, limits: SyncLimits, dry_run: bool):
        if limits.photos <= 0:
            result["google_photos"]["items"].append({"status": "skipped", "reason": "photos_limit=0"})
            return

        try:
            photos = self._with_retries(
                "google_photos.list",
                self.gc.list_photos,
                page_size=limits.photos,
                attempts=limits.retry_attempts,
                backoff_seconds=limits.retry_backoff_seconds,
            )
        except Exception as exc:
            logger.error("No fue posible listar Google Photos: %s", exc)
            result["google_photos"]["errors"] += 1
            result["google_photos"]["items"].append({"error": str(exc)})
            self._track_alert("error", "google_photos", "list_failed", {"error": str(exc)})
            return

        for photo in photos:
            source_id = str(photo.get("id") or "")
            name = _safe_name(photo.get("filename", ""), f"photo_{source_id or 'sin_id'}.jpg")
            mime_type = photo.get("mimeType") or "image/jpeg"
            renamed_from = None
            normalized_name = _normalize_name(name, f"photo_{source_id or 'sin_id'}.jpg")
            if normalized_name != name:
                renamed_from = name
                name = normalized_name
            category = _classify_category(name, mime_type)
            semantic_context = str(photo.get("description") or "")
            conflict_inference = self._infer_conflict_bucket("google_photos", name, semantic_context)
            conflict_bucket = conflict_inference["bucket"]
            target_path = self._build_target_parts("google_photos", category, name, extra_text=semantic_context, conflict_bucket=conflict_bucket)

            if not source_id:
                result["google_photos"]["skipped"] += 1
                result["google_photos"]["items"].append({"name": name, "status": "skipped", "reason": "sin_id"})
                continue

            if self._already_synced("google_photos", source_id):
                result["google_photos"]["skipped"] += 1
                result["google_photos"]["items"].append({"id": source_id, "name": name, "status": "already_synced"})
                continue

            try:
                # 1. Analisis Inteligente Pre-ingesta
                intelligent_data = None
                # Guardar temporalmente para que Gemini pueda leerlo
                temp_path = Path(f"temp_ingest_{name}")
                temp_path.write_bytes(payload)
                try:
                    intelligent_data = asyncio.run(_apply_intelligent_analysis(str(temp_path), name, mime_type))
                finally:
                    if temp_path.exists(): temp_path.unlink()

                # 2. Lógica de Ruteo de Agente Soberano
                is_duplicate = self._find_duplicate_by_hash(content_sha1)
                
                if not intelligent_data or is_duplicate or intelligent_data.get("resolucion", "Dudoso").upper() != "CERTEZA":
                    # Flujo DUDOSO o DUPLICADO -> 01_REVISION_MANUAL
                    folder_id = self.gc.ensure_folder_path([ROOT_DRIVE_FOLDER, MANUAL_REVIEW_FOLDER_NAME])
                    if intelligent_data:
                        name = intelligent_data.get("nombre_inteligente", name)
                    target_path = [ROOT_DRIVE_FOLDER, MANUAL_REVIEW_FOLDER_NAME]
                    if is_duplicate:
                        name = f"DUP_{name}"
                else:
                    # Flujo CERTEZA -> 00_ANALISIS_24H y luego copiar a Geopolítica
                    name = intelligent_data.get("nombre_inteligente", name)
                    category = intelligent_data.get("etiqueta", category)
                    
                    # Upload_bytes inicial a Limbo
                    folder_id = self.gc.ensure_folder_path([ROOT_DRIVE_FOLDER, LIMBO_FOLDER_NAME])
                    target_path = [ROOT_DRIVE_FOLDER, LIMBO_FOLDER_NAME]

                # 4. Upload con Propiedades Inteligentes
                uploaded = self._with_retries(
                    "google_photos.upload",
                    self.gc.upload_bytes,
                    payload,
                    filename=name,
                    mime_type=mime_type,
                    parent_id=folder_id,
                    app_properties={
                        "nexo_source": "google_photos",
                        "nexo_source_id": source_id,
                        "nexo_category": category,
                        "nexo_intelligent_name": name if intelligent_data else "no",
                        "nexo_content_sha1": content_sha1,
                        "nexo_daily_magazine": "true" if intelligent_data else "false"
                    },
                    attempts=limits.retry_attempts,
                    backoff_seconds=limits.retry_backoff_seconds,
                )
                
                # Si fue CERTEZA, copiar también a carpeta definitiva
                if intelligent_data and not is_duplicate and intelligent_data.get("resolucion", "Dudoso").upper() == "CERTEZA":
                    final_folder_id = self.gc.ensure_folder_path([
                        ROOT_DRIVE_FOLDER, 
                        GEOPOLITICA_FOLDER,
                        *intelligent_data.get("categoria_jerarquica", [])
                    ])
                    # Mover una copia
                    try:
                        # Asumiendo que gc.copy_file existe, sino lo forzamos con upload de nuevo
                        if hasattr(self.gc, "copy_file"):
                           self.gc.copy_file(uploaded["id"], final_folder_id, new_name=name)
                        else:
                           self.gc.upload_bytes(payload, filename=name, mime_type=mime_type, parent_id=final_folder_id)
                    except Exception as copy_exc:
                        logger.error(f"Falla copiando archivo a definitiva: {copy_exc}")

                result["google_photos"]["imported"] += 1
                result["google_photos"]["items"].append({
                    "id": source_id,
                    "name": name,
                    "status": "imported_limbo" if intelligent_data else "imported",
                    "target_path": target_path
                })


            except Exception as exc:
                logger.error("Error importando foto %s: %s", name, exc)
                result["google_photos"]["errors"] += 1
                result["google_photos"]["items"].append({"id": source_id, "name": name, "status": "error", "error": str(exc)})

    def _classify_google_drive(self, result: Dict, limits: SyncLimits, dry_run: bool):
        if limits.drive <= 0:
            result["google_drive"]["items"].append({"status": "skipped", "reason": "drive_limit=0"})
            return

        try:
            files = self._with_retries(
                "google_drive.list_unclassified",
                self.gc.list_unclassified_drive_files_detailed,
                page_size=limits.drive,
                include_trashed=limits.drive_include_trashed,
                full_scan=limits.drive_full_scan,
                attempts=limits.retry_attempts,
                backoff_seconds=limits.retry_backoff_seconds,
            )
        except Exception as exc:
            logger.error("No fue posible listar Drive detallado: %s", exc)
            result["google_drive"]["errors"] += 1
            result["google_drive"]["items"].append({"error": str(exc)})
            self._track_alert("error", "google_drive", "list_failed", {"error": str(exc)})
            return

        for file_info in files:
            result["google_drive"]["analyzed"] += 1
            file_id = file_info.get("id")
            name = _safe_name(file_info.get("name", ""), "archivo_sin_nombre")
            mime_type = (file_info.get("mimeType") or "").lower()

            if not file_id:
                result["google_drive"]["skipped"] += 1
                result["google_drive"]["items"].append({"name": name, "status": "skipped", "reason": "sin_id"})
                continue
            if mime_type == "application/vnd.google-apps.folder":
                result["google_drive"]["skipped"] += 1
                continue

            if bool(file_info.get("trashed")):
                if dry_run:
                    result["google_drive"]["skipped"] += 1
                    result["google_drive"]["items"].append(
                        {"id": file_id, "name": name, "status": "dry_run_restore_from_trash"}
                    )
                    continue
                try:
                    self._with_retries(
                        "google_drive.restore_from_trash",
                        self.gc.trash_file,
                        file_id,
                        False,
                        attempts=limits.retry_attempts,
                        backoff_seconds=limits.retry_backoff_seconds,
                    )
                    self._track_alert("info", "google_drive", "restored_from_trash", {"id": file_id, "name": name})
                except Exception as exc:
                    result["google_drive"]["errors"] += 1
                    result["google_drive"]["items"].append({"id": file_id, "name": name, "status": "error_restore", "error": str(exc)})
                    self._track_alert("error", "google_drive", "restore_from_trash_failed", {"id": file_id, "error": str(exc)})
                    continue

            renamed_from = None
            if limits.drive_auto_rename:
                normalized_name = _normalize_name(name, "archivo_sin_nombre")
                if normalized_name != name:
                    if dry_run:
                        renamed_from = name
                        name = normalized_name
                    else:
                        try:
                            self._with_retries(
                                "google_drive.rename",
                                self.gc.rename_file,
                                file_id,
                                normalized_name,
                                attempts=limits.retry_attempts,
                                backoff_seconds=limits.retry_backoff_seconds,
                            )
                            renamed_from = name
                            name = normalized_name
                        except Exception as exc:
                            result["google_drive"]["errors"] += 1
                            result["google_drive"]["items"].append({"id": file_id, "name": name, "status": "error_rename", "error": str(exc)})
                            self._track_alert("error", "google_drive", "rename_failed", {"id": file_id, "name": name, "error": str(exc)})
                            continue

            app_props = file_info.get("appProperties") or {}
            if app_props.get("nexo_source") in {"google_photos", "onedrive"}:
                result["google_drive"]["skipped"] += 1
                continue

            category = _classify_category(name, mime_type)
            try:
                target_folder = self._ensure_target_folder("google_drive", category)
                current_size = int(file_info.get("size") or 0)
                same_folder_files = self._list_folder_cached(target_folder)
                duplicate_in_folder = next(
                    (
                        other for other in same_folder_files
                        if str(other.get("id") or "") != str(file_id)
                        and str(other.get("name") or "") == name
                        and int(other.get("size") or 0) == current_size
                    ),
                    None,
                )
                if duplicate_in_folder:
                    if dry_run:
                        result["google_drive"]["skipped"] += 1
                        result["google_drive"]["items"].append(
                            {
                                "id": file_id,
                                "name": name,
                                "status": "dry_run_deduplicated",
                                "duplicate_of": duplicate_in_folder.get("id"),
                                "category": category,
                            }
                        )
                        continue
                    self._with_retries(
                        "google_drive.deduplicate_trash",
                        self.gc.trash_file,
                        file_id,
                        True,
                        attempts=limits.retry_attempts,
                        backoff_seconds=limits.retry_backoff_seconds,
                    )
                    result["google_drive"]["skipped"] += 1
                    result["google_drive"]["items"].append(
                        {
                            "id": file_id,
                            "name": name,
                            "status": "deduplicated",
                            "duplicate_of": duplicate_in_folder.get("id"),
                            "category": category,
                        }
                    )
                    continue
                parents = file_info.get("parents") or []
                if target_folder in parents:
                    result["google_drive"]["skipped"] += 1
                    item = {"id": file_id, "name": name, "status": "already_classified", "category": category}
                    if renamed_from:
                        item["renamed_from"] = renamed_from
                    result["google_drive"]["items"].append(item)
                    continue

                if dry_run:
                    result["google_drive"]["classified"] += 1
                    item = {"id": file_id, "name": name, "status": "dry_run_classify", "category": category}
                    if renamed_from:
                        item["renamed_from"] = renamed_from
                    result["google_drive"]["items"].append(item)
                    continue

                self._with_retries(
                    "google_drive.move_to_folder",
                    self.gc.move_file_to_folder,
                    file_id,
                    target_folder,
                    app_properties={
                        "nexo_source": "google_drive",
                        "nexo_source_id": str(file_id),
                        "nexo_category": category,
                    },
                    attempts=limits.retry_attempts,
                    backoff_seconds=limits.retry_backoff_seconds,
                )
                result["google_drive"]["classified"] += 1
                item = {"id": file_id, "name": name, "status": "classified", "category": category}
                if renamed_from:
                    item["renamed_from"] = renamed_from
                result["google_drive"]["items"].append(item)
            except Exception as exc:
                logger.error("Error clasificando archivo Drive %s: %s", name, exc)
                result["google_drive"]["errors"] += 1
                result["google_drive"]["items"].append({"id": file_id, "name": name, "status": "error", "error": str(exc)})
                self._track_alert("error", "google_drive", "classify_failed", {"id": file_id, "name": name, "error": str(exc)})

    def _sync_onedrive(self, result: Dict, limits: SyncLimits, dry_run: bool):
        if limits.onedrive <= 0:
            result["onedrive"]["items"].append({"status": "skipped", "reason": "onedrive_limit=0"})
            return

        onedrive_mode = (os.getenv("NEXO_ONEDRIVE_SOURCE", "auto") or "auto").strip().lower()
        using_local_fallback = False

        try:
            files = None
            mc = None

            if onedrive_mode in {"graph", "auto"}:
                try:
                    mc = MicrosoftConnector()
                    if getattr(mc, "headers", None):
                        files = self._with_retries(
                            "onedrive.list_recent",
                            mc.list_recent_files,
                            top=limits.onedrive,
                            attempts=limits.retry_attempts,
                            backoff_seconds=limits.retry_backoff_seconds,
                        )
                except Exception as graph_exc:
                    self._track_alert(
                        "warning",
                        "onedrive",
                        "graph_unavailable",
                        {"error": str(graph_exc)},
                    )
                    mc = None

            if files is None and onedrive_mode in {"local", "filesystem", "auto"}:
                files = list_recent_local_onedrive_files(top=limits.onedrive)
                if files:
                    using_local_fallback = True
                    self._track_alert(
                        "warning",
                        "onedrive",
                        "using_local_fallback",
                        {"root": str(resolve_onedrive_local_root() or "")},
                    )

            if files is None:
                raise RuntimeError("OneDrive no disponible en modo graph ni fallback local")
        except Exception as exc:
            logger.error("No fue posible leer OneDrive: %s", exc)
            result["onedrive"]["errors"] += 1
            result["onedrive"]["items"].append({"error": str(exc)})
            self._track_alert("error", "onedrive", "list_failed", {"error": str(exc)})
            return

        for item in files:
            item_id = str(item.get("id") or "")
            name = _safe_name(item.get("name", ""), f"onedrive_{item_id or 'sin_id'}")
            file_meta = item.get("file") or {}
            mime_type = file_meta.get("mimeType") or item.get("mimeType") or "application/octet-stream"
            size_bytes = int(item.get("size") or 0)

            if not item_id:
                result["onedrive"]["skipped"] += 1
                result["onedrive"]["items"].append({"name": name, "status": "skipped", "reason": "sin_id"})
                continue
            if self._already_synced("onedrive", item_id):
                result["onedrive"]["skipped"] += 1
                result["onedrive"]["items"].append({"id": item_id, "name": name, "status": "already_synced"})
                continue

            max_size = limits.onedrive_max_mb * 1024 * 1024
            if size_bytes and size_bytes > max_size:
                result["onedrive"]["skipped"] += 1
                result["onedrive"]["items"].append({
                    "id": item_id,
                    "name": name,
                    "status": "skipped_too_large",
                    "size_bytes": size_bytes,
                })
                continue

            category = _classify_category(name, mime_type)
            renamed_from = None
            normalized_name = _normalize_name(name, f"onedrive_{item_id or 'sin_id'}")
            if normalized_name != name:
                renamed_from = name
                name = normalized_name
            try:
                if dry_run:
                    conflict_inference = self._infer_conflict_bucket("onedrive", name, str(item.get("relative_path") or ""))
                    conflict_bucket = conflict_inference["bucket"]
                    target_path = self._build_target_parts("onedrive", category, name, extra_text=str(item.get("relative_path") or ""), conflict_bucket=conflict_bucket)
                    result["onedrive"]["imported"] += 1
                    dry_item = {
                        "id": item_id,
                        "name": name,
                        "status": "dry_run_import",
                        "category": category,
                        "conflict_bucket": conflict_bucket,
                        "conflict_score": conflict_inference["score"],
                        "conflict_terms": conflict_inference["matched_terms"],
                        "target_path": target_path,
                        "source": "local_onedrive" if using_local_fallback else "graph",
                    }
                    if renamed_from:
                        dry_item["renamed_from"] = renamed_from
                    result["onedrive"]["items"].append(dry_item)
                    continue

                if using_local_fallback:
                    local_path = Path(str(item.get("local_path") or ""))
                    if not local_path.exists() or not local_path.is_file():
                        raise RuntimeError(f"Archivo local no encontrado: {local_path}")
                    payload = read_local_onedrive_bytes(local_path)
                else:
                    if mc is None:
                        raise RuntimeError("Conector OneDrive Graph no inicializado")
                    payload = self._with_retries(
                        "onedrive.download",
                        mc.download_file_content,
                        item_id,
                        attempts=limits.retry_attempts,
                        backoff_seconds=limits.retry_backoff_seconds,
                    )
                if not payload:
                    result["onedrive"]["errors"] += 1
                    result["onedrive"]["items"].append({"id": item_id, "name": name, "status": "error", "error": "sin_contenido"})
                    continue

                semantic_text = str(item.get("relative_path") or "")
                semantic_text = f"{semantic_text}\n{_extract_text_preview(payload, name, mime_type)}"
                conflict_inference = self._infer_conflict_bucket("onedrive", name, semantic_text)
                conflict_bucket = conflict_inference["bucket"]
                target_path = self._build_target_parts("onedrive", category, name, extra_text=semantic_text, conflict_bucket=conflict_bucket)
                folder_id = self._ensure_target_folder(
                    "onedrive",
                    category,
                    name,
                    extra_text=semantic_text,
                    conflict_bucket=conflict_bucket,
                )

                content_sha1 = hashlib.sha1(payload).hexdigest()
                duplicate = self._find_duplicate_by_hash(content_sha1)
                if duplicate:
                    result["onedrive"]["skipped"] += 1
                    dup_item = {
                        "id": item_id,
                        "name": name,
                        "status": "duplicate_skipped",
                        "duplicate_of": duplicate.get("id"),
                        "category": category,
                        "conflict_bucket": conflict_bucket,
                        "conflict_score": conflict_inference["score"],
                        "conflict_terms": conflict_inference["matched_terms"],
                        "target_path": target_path,
                        "source": "local_onedrive" if using_local_fallback else "graph",
                    }
                    if renamed_from:
                        dup_item["renamed_from"] = renamed_from
                    result["onedrive"]["items"].append(dup_item)
                    continue

                uploaded = self._with_retries(
                    "onedrive.upload_to_drive",
                    self.gc.upload_bytes,
                    payload,
                    filename=name,
                    mime_type=mime_type,
                    parent_id=folder_id,
                    app_properties={
                        "nexo_source": "onedrive",
                        "nexo_source_id": item_id,
                        "nexo_category": category,
                        "nexo_conflict_bucket": conflict_bucket,
                        "nexo_conflict_score": str(conflict_inference["score"]),
                        "nexo_content_sha1": content_sha1,
                    },
                    attempts=limits.retry_attempts,
                    backoff_seconds=limits.retry_backoff_seconds,
                )
                result["onedrive"]["imported"] += 1
                out_item = {
                    "id": item_id,
                    "name": name,
                    "status": "imported",
                    "category": category,
                    "conflict_bucket": conflict_bucket,
                    "conflict_score": conflict_inference["score"],
                    "conflict_terms": conflict_inference["matched_terms"],
                    "target_path": target_path,
                    "drive_file_id": uploaded.get("id"),
                    "source": "local_onedrive" if using_local_fallback else "graph",
                }
                if renamed_from:
                    out_item["renamed_from"] = renamed_from
                result["onedrive"]["items"].append(out_item)
            except Exception as exc:
                logger.error("Error importando OneDrive %s: %s", name, exc)
                result["onedrive"]["errors"] += 1
                result["onedrive"]["items"].append({"id": item_id, "name": name, "status": "error", "error": str(exc)})
                self._track_alert("error", "onedrive", "import_failed", {"id": item_id, "name": name, "error": str(exc)})


def run_unified_sync(*, dry_run: bool = False, photos_limit: int = 20, drive_limit: int = 50, onedrive_limit: int = 20, onedrive_max_mb: int = 20, youtube_per_channel: int = 10, youtube_channels: Optional[List[str]] = None, drive_include_trashed: bool = False, drive_full_scan: bool = False, drive_auto_rename: bool = False, retry_attempts: int = 3, retry_backoff_seconds: float = 1.2) -> Dict:
    service = UnifiedSyncService()
    limits = SyncLimits(
        photos=max(0, int(photos_limit)),
        drive=max(0, int(drive_limit)),
        onedrive=max(0, int(onedrive_limit)),
        onedrive_max_mb=max(1, int(onedrive_max_mb)),
        youtube_per_channel=max(0, int(youtube_per_channel)),
        drive_include_trashed=bool(drive_include_trashed),
        drive_full_scan=bool(drive_full_scan),
        drive_auto_rename=bool(drive_auto_rename),
        retry_attempts=max(1, int(retry_attempts)),
        retry_backoff_seconds=max(0.1, float(retry_backoff_seconds)),
    )
    return service.sync(limits=limits, dry_run=dry_run, youtube_channels=youtube_channels or [])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run_unified_sync()
    summary = {
        "google_photos_imported": result.get("google_photos", {}).get("imported", 0),
        "google_photos_skipped": result.get("google_photos", {}).get("skipped", 0),
        "google_photos_errors": result.get("google_photos", {}).get("errors", 0),
        "google_drive_classified": result.get("google_drive", {}).get("classified", 0),
        "google_drive_skipped": result.get("google_drive", {}).get("skipped", 0),
        "google_drive_errors": result.get("google_drive", {}).get("errors", 0),
        "onedrive_imported": result.get("onedrive", {}).get("imported", 0),
        "onedrive_skipped": result.get("onedrive", {}).get("skipped", 0),
        "onedrive_errors": result.get("onedrive", {}).get("errors", 0),
        "youtube_processed": result.get("youtube", {}).get("processed", 0),
        "youtube_skipped": result.get("youtube", {}).get("skipped", 0),
        "youtube_errors": result.get("youtube", {}).get("errors", 0),
    }
    log.info(json.dumps(summary, ensure_ascii=False))
