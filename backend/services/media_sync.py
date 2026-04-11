"""
NEXO — Media Classification & Sync Service
==========================================
Google Photos / OneDrive → Google Drive with AI classification.

Pipeline:
  1. List recent items from Google Photos (via Photos API) or local OneDrive folder
  2. Classify each item with Gemma 4 (local) → Gemini fallback
  3. Move/copy to the correct Drive folder based on classification
  4. Return a structured report

Usage:
  from backend.services.media_sync import media_sync_service
  result = await media_sync_service.run_sync(source="google_photos", limit=50)
"""
from __future__ import annotations

import asyncio
import logging
import os
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("NEXO.media_sync")

# ── Drive folder structure ───────────────────────────────────────────────────
ROOT_FOLDER = os.getenv("NEXO_DRIVE_ROOT_FOLDER", "NEXO_SOBERANO_CLASIFICADO")
FOLDER_MAP = {
    "geopolitica":   os.getenv("NEXO_DRIVE_FOLDER_GEOPOLITICA",   "GEOPOLITICA"),
    "personal":      os.getenv("NEXO_DRIVE_FOLDER_PERSONAL",       "PERSONAL"),
    "trabajo":       os.getenv("NEXO_DRIVE_FOLDER_TRABAJO",        "TRABAJO"),
    "viajes":        os.getenv("NEXO_DRIVE_FOLDER_VIAJES",         "VIAJES"),
    "documentos":    os.getenv("NEXO_DRIVE_FOLDER_DOCUMENTOS",     "DOCUMENTOS"),
    "capturas":      os.getenv("NEXO_DRIVE_FOLDER_CAPTURAS",       "CAPTURAS_PANTALLA"),
    "sin_clasificar": "00_SIN_CLASIFICAR",
}

# ── AI routing ───────────────────────────────────────────────────────────────
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000").rstrip("/")
OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434")
GEMINI_KEY  = os.getenv("GEMINI_API_KEY", "")

# ── Classification keywords ──────────────────────────────────────────────────
GEO_KEYWORDS = {
    "israel", "gaza", "hamas", "ucrania", "ukraine", "rusia", "russia",
    "conflicto", "guerra", "military", "militar", "ejercito", "nato", "otan",
    "iran", "siria", "china", "taiwan", "corea", "north korea", "siria", "venezuela",
    "manifestacion", "protesta", "protest", "golpe",
}
WORK_KEYWORDS = {"trabajo", "reunion", "meeting", "oficina", "proyecto", "documento", "informe", "reporte"}
TRAVEL_KEYWORDS = {"viaje", "travel", "vacaciones", "playa", "hotel", "aeropuerto", "avion", "tren", "ciudad"}
SCREENSHOT_KEYWORDS = {"screenshot", "captura", "pantalla", "screen"}


class MediaSyncService:
    """Classifies and organises media from Google Photos and OneDrive."""

    def __init__(self) -> None:
        self._drive_folder_cache: dict[str, str] = {}  # name → id

    # ── Public API ───────────────────────────────────────────────────────────

    async def run_sync(
        self,
        source: str = "google_photos",
        limit: int = 30,
        dry_run: bool = False,
    ) -> dict:
        """Run a sync cycle. Returns a report dict."""
        started = time.time()
        report: dict = {
            "source": source,
            "dry_run": dry_run,
            "processed": 0,
            "classified": {},
            "errors": [],
            "duration_s": 0,
        }

        try:
            if source == "google_photos":
                items = await self._list_google_photos(limit)
            elif source == "onedrive":
                items = await self._list_onedrive_local(limit)
            else:
                raise ValueError(f"Unknown source: {source}")

            logger.info("[media_sync] Got %d items from %s", len(items), source)

            for item in items:
                try:
                    category = await self._classify_item(item)
                    report["classified"].setdefault(category, []).append(item.get("filename", item.get("id", "?")))
                    report["processed"] += 1

                    if not dry_run and source == "google_photos":
                        await self._copy_to_drive(item, category)

                except Exception as e:
                    logger.warning("[media_sync] Item error: %s", e)
                    report["errors"].append(str(e))

        except Exception as e:
            logger.error("[media_sync] Sync failed: %s", e)
            report["errors"].append(str(e))

        report["duration_s"] = round(time.time() - started, 2)
        return report

    async def get_status(self) -> dict:
        """Return service health status."""
        photos_ok = await self._check_google_photos_auth()
        drive_ok  = await self._check_drive_auth()
        return {
            "google_photos": "ok" if photos_ok else "no_auth",
            "google_drive":  "ok" if drive_ok  else "no_auth",
            "onedrive_local": "ok" if self._onedrive_local_root() else "not_configured",
            "root_folder": ROOT_FOLDER,
            "folder_map": FOLDER_MAP,
        }

    # ── Google Photos ────────────────────────────────────────────────────────

    async def _list_google_photos(self, limit: int) -> list[dict]:
        """List recent Google Photos items using the Photos Library API."""
        token = await self._get_google_photos_token()
        if not token:
            logger.warning("[media_sync] Google Photos token unavailable — check OAuth setup")
            return []

        items: list[dict] = []
        page_token: Optional[str] = None

        async with httpx.AsyncClient(timeout=30) as client:
            while len(items) < limit:
                params: dict = {"pageSize": min(50, limit - len(items))}
                if page_token:
                    params["pageToken"] = page_token

                resp = await client.get(
                    "https://photoslibrary.googleapis.com/v1/mediaItems",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if resp.status_code == 401:
                    logger.warning("[media_sync] Google Photos token expired")
                    break
                if resp.status_code != 200:
                    logger.warning("[media_sync] Photos API error %d: %s", resp.status_code, resp.text[:200])
                    break

                data = resp.json()
                batch = data.get("mediaItems", [])
                for m in batch:
                    items.append({
                        "id":          m.get("id", ""),
                        "filename":    m.get("filename", ""),
                        "mimeType":    m.get("mimeType", ""),
                        "description": m.get("description", ""),
                        "baseUrl":     m.get("baseUrl", ""),
                        "productUrl":  m.get("productUrl", ""),
                        "creationTime": m.get("mediaMetadata", {}).get("creationTime", ""),
                    })

                page_token = data.get("nextPageToken")
                if not page_token or not batch:
                    break

        logger.info("[media_sync] Listed %d Google Photos items", len(items))
        return items

    async def _get_google_photos_token(self) -> Optional[str]:
        """Get a valid Google Photos OAuth2 access token from stored credentials."""
        try:
            from services.connectors.google_connector import GoogleConnector
            gc = GoogleConnector()
            creds = gc.get_photos_credentials()
            if creds and creds.token:
                return creds.token
        except Exception as e:
            logger.debug("[media_sync] GoogleConnector unavailable: %s", e)

        # Fallback: check auth/photos_token.json
        token_path = Path(__file__).parents[2] / "backend" / "auth" / "photos_token.json"
        if token_path.exists():
            try:
                data = json.loads(token_path.read_text())
                return data.get("access_token") or data.get("token")
            except Exception:
                pass

        return None

    async def _check_google_photos_auth(self) -> bool:
        token = await self._get_google_photos_token()
        return bool(token)

    # ── OneDrive (local folder) ──────────────────────────────────────────────

    def _onedrive_local_root(self) -> Optional[Path]:
        """Resolve the local OneDrive sync folder path."""
        custom = os.getenv("NEXO_ONEDRIVE_LOCAL_DIR", "").strip()
        if custom:
            p = Path(custom)
            if p.exists():
                return p

        # Common Windows paths (may be mounted via WSL)
        for candidate in [
            Path("/mnt/c/Users/Admn/OneDrive"),
            Path("/mnt/c/Users/estef/OneDrive"),
            Path(os.path.expanduser("~/OneDrive")),
        ]:
            if candidate.exists():
                return candidate
        return None

    async def _list_onedrive_local(self, limit: int) -> list[dict]:
        """List recent files from local OneDrive sync folder."""
        root = self._onedrive_local_root()
        if not root:
            logger.warning("[media_sync] OneDrive local folder not found")
            return []

        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".mp4", ".mov", ".avi"}
        files: list[tuple[float, Path]] = []

        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                try:
                    files.append((p.stat().st_mtime, p))
                except OSError:
                    pass

        files.sort(reverse=True)
        items = []
        for _, path in files[:limit]:
            items.append({
                "id":       str(path),
                "filename": path.name,
                "mimeType": self._guess_mime(path),
                "description": path.parent.name,
                "local_path": str(path),
            })

        logger.info("[media_sync] Listed %d OneDrive local items", len(items))
        return items

    def _guess_mime(self, path: Path) -> str:
        import mimetypes
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"

    # ── AI Classification ────────────────────────────────────────────────────

    async def _classify_item(self, item: dict) -> str:
        """Classify a media item into a folder category using AI + heuristics."""
        filename   = (item.get("filename", "") or "").lower()
        description = (item.get("description", "") or "").lower()
        combined   = f"{filename} {description}"

        # Fast keyword heuristics (no API call needed)
        if any(k in combined for k in SCREENSHOT_KEYWORDS):
            return "capturas"
        if any(k in combined for k in GEO_KEYWORDS):
            return "geopolitica"
        if any(k in combined for k in WORK_KEYWORDS):
            return "trabajo"
        if any(k in combined for k in TRAVEL_KEYWORDS):
            return "viajes"

        # Photos with generic names like IMG_XXXX → try AI classification
        if item.get("description") or len(filename) > 20:
            try:
                category = await self._ai_classify(combined)
                if category and category in FOLDER_MAP:
                    return category
            except Exception as e:
                logger.debug("[media_sync] AI classify failed: %s", e)

        return "personal"

    async def _ai_classify(self, text: str) -> str:
        """Ask Gemma 4 (local) to classify the media. Returns folder key."""
        prompt = (
            "Clasifica el siguiente archivo multimedia en UNA de estas categorías: "
            "geopolitica, personal, trabajo, viajes, documentos, capturas, sin_clasificar.\n"
            f"Nombre/descripción: {text[:200]}\n"
            "Responde SOLO con la categoría, sin explicaciones."
        )

        # Try Ollama/Gemma 4 first
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": os.getenv("OLLAMA_MODEL_GENERAL", "gemma3:4b"), "prompt": prompt, "stream": False},
                )
                if resp.status_code == 200:
                    answer = resp.json().get("response", "").strip().lower().split()[0]
                    if answer in FOLDER_MAP:
                        return answer
        except Exception:
            pass

        # Fallback: Gemini Flash
        if GEMINI_KEY:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                    )
                    if resp.status_code == 200:
                        answer = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().lower().split()[0]
                        if answer in FOLDER_MAP:
                            return answer
            except Exception:
                pass

        return "sin_clasificar"

    # ── Drive upload ─────────────────────────────────────────────────────────

    async def _copy_to_drive(self, item: dict, category: str) -> None:
        """Copy/move a Photos item to the appropriate Drive folder."""
        try:
            from services.connectors.google_connector import GoogleConnector
            gc = GoogleConnector()
            drive = gc.get_drive_service()
            if not drive:
                return

            folder_name = FOLDER_MAP.get(category, FOLDER_MAP["sin_clasificar"])
            folder_id = await self._ensure_drive_folder(drive, folder_name)

            # Download photo bytes from baseUrl
            base_url = item.get("baseUrl", "")
            if not base_url:
                return

            async with httpx.AsyncClient(timeout=60) as client:
                photo_resp = await client.get(f"{base_url}=d")  # =d for download
                if photo_resp.status_code != 200:
                    return
                content = photo_resp.content

            # Upload to Drive
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._drive_upload, drive, item, content, folder_id)
            logger.info("[media_sync] Uploaded %s → %s", item["filename"], folder_name)

        except Exception as e:
            logger.warning("[media_sync] Drive copy failed for %s: %s", item.get("filename"), e)

    def _drive_upload(self, drive, item: dict, content: bytes, folder_id: str) -> None:
        from googleapiclient.http import MediaIoBaseUpload
        import io
        file_meta = {
            "name": item["filename"],
            "parents": [folder_id],
        }
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=item.get("mimeType", "image/jpeg"))
        drive.files().create(body=file_meta, media_body=media, fields="id").execute()

    async def _ensure_drive_folder(self, drive, folder_name: str) -> str:
        """Get or create a Drive folder under ROOT_FOLDER. Returns folder id."""
        cache_key = folder_name
        if cache_key in self._drive_folder_cache:
            return self._drive_folder_cache[cache_key]

        loop = asyncio.get_event_loop()
        folder_id = await loop.run_in_executor(None, self._find_or_create_drive_folder, drive, folder_name)
        self._drive_folder_cache[cache_key] = folder_id
        return folder_id

    def _find_or_create_drive_folder(self, drive, folder_name: str) -> str:
        # Search for existing
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        res = drive.files().list(q=query, fields="files(id, name)").execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]

        # Create it
        meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
        f = drive.files().create(body=meta, fields="id").execute()
        return f["id"]

    async def _check_drive_auth(self) -> bool:
        try:
            from services.connectors.google_connector import GoogleConnector
            gc = GoogleConnector()
            return gc.get_drive_service() is not None
        except Exception:
            return False


# Singleton
media_sync_service = MediaSyncService()
