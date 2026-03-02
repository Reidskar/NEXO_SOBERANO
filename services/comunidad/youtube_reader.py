"""Integración YouTube para monitoreo y publicación.

Capacidades:
- Listar videos recientes de canales (YouTube Data API).
- Obtener transcripciones (youtube-transcript-api).
- Subir resúmenes/clips a YouTube (OAuth + API upload).
"""

from __future__ import annotations

import io
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)


YOUTUBE_READ_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
YOUTUBE_UPLOAD_SCOPES = [
	"https://www.googleapis.com/auth/youtube.upload",
	"https://www.googleapis.com/auth/youtube.readonly",
	"https://www.googleapis.com/auth/youtube.force-ssl",
]


def _resolve_auth_dir() -> Path:
	env_auth_dir = os.getenv("NEXO_AUTH_DIR")
	if env_auth_dir:
		return Path(env_auth_dir)

	current = Path(__file__).resolve()
	for parent in current.parents:
		candidate = parent / "backend" / "auth"
		if candidate.exists():
			return candidate
	return current.parent.parent.parent / "backend" / "auth"


AUTH_DIR = _resolve_auth_dir()
AUTH_DIR.mkdir(parents=True, exist_ok=True)
YOUTUBE_CLIENT_SECRETS_FILE = AUTH_DIR / "client_secrets_youtube.json"


def create_youtube_client_secrets_from_env() -> Path:
	"""Crea client_secrets para YouTube desde variables de entorno.

	Requiere:
	- YOUTUBE_CLIENT_ID
	- YOUTUBE_CLIENT_SECRET
	"""
	client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip() or os.getenv("GOOGLE_CLIENT_ID", "").strip()
	client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip() or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
	if not client_id or not client_secret:
		raise ValueError(
			"Faltan YOUTUBE_CLIENT_ID/YOUTUBE_CLIENT_SECRET o GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET en entorno/.env"
		)

	project_id = os.getenv("YOUTUBE_PROJECT_ID", "nexo-soberano")
	payload = {
		"installed": {
			"client_id": client_id,
			"project_id": project_id,
			"auth_uri": "https://accounts.google.com/o/oauth2/auth",
			"token_uri": "https://oauth2.googleapis.com/token",
			"auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
			"client_secret": client_secret,
			"redirect_uris": ["http://localhost"],
		}
	}
	YOUTUBE_CLIENT_SECRETS_FILE.write_text(
		json.dumps(payload, ensure_ascii=False, indent=2),
		encoding="utf-8",
	)
	return YOUTUBE_CLIENT_SECRETS_FILE


def _resolve_google_credentials_file() -> Path:
	if YOUTUBE_CLIENT_SECRETS_FILE.exists():
		return YOUTUBE_CLIENT_SECRETS_FILE

	if os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET"):
		try:
			return create_youtube_client_secrets_from_env()
		except Exception as exc:
			logger.warning("No fue posible crear client_secrets YouTube desde entorno: %s", exc)

	credentials_path = AUTH_DIR / "credenciales_google.json"
	if credentials_path.exists():
		return credentials_path

	root_fallback = AUTH_DIR.parent.parent / "credenciales_google.json"
	if root_fallback.exists():
		return root_fallback

	desktop = Path.home() / "Desktop" / "credenciales_google.json"
	if desktop.exists():
		return desktop

	downloads = Path.home() / "Downloads" / "credenciales_google.json"
	if downloads.exists():
		return downloads

	for f in (Path.home() / "Downloads").glob("client_secret_*.json"):
		return f

	raise FileNotFoundError(
		f"No se encontró credenciales de Google para YouTube en {credentials_path}"
	)


def _token_file(upload: bool) -> Path:
	return AUTH_DIR / ("token_youtube_upload.json" if upload else "token_youtube_read.json")


def get_youtube_credentials(upload: bool = False, allow_interactive: bool = False) -> Credentials:
	scopes = YOUTUBE_UPLOAD_SCOPES if upload else YOUTUBE_READ_SCOPES
	token_path = _token_file(upload)
	creds = None

	if token_path.exists():
		try:
			creds = Credentials.from_authorized_user_file(str(token_path), scopes)
		except Exception as exc:
			logger.warning("Token YouTube inválido en %s: %s", token_path, exc)
			creds = None

	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			try:
				creds.refresh(Request())
			except Exception as exc:
				logger.warning("Falló refresh token YouTube: %s", exc)
				creds = None

		if not creds or not creds.valid:
			if not allow_interactive:
				scope_label = "youtube.upload" if upload else "youtube.readonly"
				raise RuntimeError(
					f"Token de YouTube no disponible para scope {scope_label}. "
					"Autoriza previamente de forma interactiva y reintenta."
				)

			credentials_file = _resolve_google_credentials_file()
			flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scopes)
			creds = flow.run_local_server(port=0)

		with open(token_path, "w", encoding="utf-8") as token:
			token.write(creds.to_json())

	return creds


def get_youtube_service(upload: bool = False, allow_interactive: bool = False):
	creds = get_youtube_credentials(upload=upload, allow_interactive=allow_interactive)
	return build("youtube", "v3", credentials=creds)


def list_recent_channel_videos(
	channel_id: str,
	max_results: int = 20,
	published_after_iso: Optional[str] = None,
) -> List[Dict]:
	if not channel_id:
		return []

	max_results = max(1, min(int(max_results), 50))
	service = get_youtube_service(upload=False, allow_interactive=False)

	search_kwargs = {
		"part": "snippet",
		"channelId": channel_id,
		"maxResults": max_results,
		"order": "date",
		"type": "video",
	}
	if published_after_iso:
		search_kwargs["publishedAfter"] = published_after_iso

	response = service.search().list(**search_kwargs).execute()
	items = response.get("items", [])

	out: List[Dict] = []
	for it in items:
		snippet = it.get("snippet", {})
		vid = ((it.get("id") or {}).get("videoId"))
		if not vid:
			continue
		out.append(
			{
				"video_id": vid,
				"title": snippet.get("title", ""),
				"description": snippet.get("description", ""),
				"published_at": snippet.get("publishedAt", ""),
				"channel_id": snippet.get("channelId", channel_id),
				"channel_title": snippet.get("channelTitle", ""),
				"thumbnail": ((snippet.get("thumbnails") or {}).get("high") or {}).get("url", ""),
				"url": f"https://www.youtube.com/watch?v={vid}",
			}
		)
	return out


def get_video_transcript(video_id: str, languages: Optional[List[str]] = None) -> Dict:
	if not video_id:
		return {"ok": False, "error": "video_id vacío", "segments": []}

	languages = languages or ["es", "en"]

	try:
		from youtube_transcript_api import YouTubeTranscriptApi
	except Exception as exc:
		return {
			"ok": False,
			"error": f"Dependencia faltante youtube-transcript-api: {exc}",
			"segments": [],
		}

	try:
		transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
		full_text = " ".join(seg.get("text", "").strip() for seg in transcript if seg.get("text"))
		return {
			"ok": True,
			"video_id": video_id,
			"languages": languages,
			"segments": transcript,
			"text": full_text,
		}
	except Exception as exc:
		return {
			"ok": False,
			"video_id": video_id,
			"error": str(exc),
			"segments": [],
			"text": "",
		}


def upload_video_summary(
	*,
	title: str,
	description: str,
	file_bytes: bytes,
	filename: str = "resumen.mp4",
	tags: Optional[List[str]] = None,
	privacy_status: str = "unlisted",
	category_id: str = "25",
) -> Dict:
	"""Sube un video (clip/resumen) al canal autenticado."""
	service = get_youtube_service(upload=True, allow_interactive=False)
	tags = tags or ["nexo", "osint", "geopolitica"]
	privacy = privacy_status if privacy_status in {"private", "public", "unlisted"} else "unlisted"

	body = {
		"snippet": {
			"title": title[:100],
			"description": description[:5000],
			"tags": tags[:20],
			"categoryId": str(category_id),
		},
		"status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
	}

	media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype="video/mp4", resumable=True)
	created = service.videos().insert(part="snippet,status", body=body, media_body=media).execute()
	video_id = created.get("id")
	return {
		"ok": bool(video_id),
		"video_id": video_id,
		"url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
		"raw": created,
	}


def build_daily_summary_description(items: List[Dict], intro: Optional[str] = None) -> str:
	intro = intro or "Resumen diario generado automáticamente por NEXO SOBERANO."
	lines = [intro, "", "Fuentes analizadas:"]
	for idx, item in enumerate(items[:20], start=1):
		title = item.get("title", "(sin título)")
		url = item.get("url", "")
		lines.append(f"{idx}. {title} {url}".strip())
	lines.append("")
	lines.append(f"Generado: {datetime.now(timezone.utc).isoformat()}")
	return "\n".join(lines)


def save_transcript_to_json(video_id: str, transcript: Dict, target_dir: Path) -> Path:
	target_dir.mkdir(parents=True, exist_ok=True)
	out = target_dir / f"youtube_transcript_{video_id}.json"
	out.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
	return out


def authorize_youtube_interactive(upload: bool = False) -> Dict:
	"""Ejecuta OAuth interactivo para generar token YouTube persistente."""
	credentials_file = _resolve_google_credentials_file()
	creds = get_youtube_credentials(upload=upload, allow_interactive=True)
	return {
		"ok": bool(creds and creds.valid),
		"upload_scope": upload,
		"credentials_file": str(credentials_file),
		"token_file": str(_token_file(upload)),
	}
