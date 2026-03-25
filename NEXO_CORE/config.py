from __future__ import annotations

import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env file
env_file = ROOT_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv(ROOT_DIR.parent / ".env")

def load_env() -> None:
    """Legacy function for backward compatibility"""
    pass

load_env()

APP_TITLE = "El Anarcocapital API"
APP_VERSION = "3.0.0"
APP_DESCRIPTION = "Backend consolidado para El Anarcocapital"
MAX_TOKENS_DIA = int(os.getenv("NEXO_MAX_TOKENS_DIA", "900000"))

HOST = os.getenv("NEXO_HOST", "0.0.0.0")
PORT = int(os.getenv("NEXO_PORT", "8000"))
LOG_LEVEL = os.getenv("NEXO_LOG_LEVEL", "INFO").upper()
LOG_FILE_NAME = os.getenv("NEXO_LOG_FILE", "nexo_core.log")

OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")
OBS_RECONNECT_SECONDS = float(os.getenv("OBS_RECONNECT_SECONDS", "5"))
OBS_ENABLED = os.getenv("OBS_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
OBS_DEGRADED_LOG_SECONDS = float(os.getenv("OBS_DEGRADED_LOG_SECONDS", "60"))
STREAM_DEVICE = os.getenv("NEXO_STREAM_DEVICE", "pc")
STREAM_UPLOAD_MBPS = float(os.getenv("NEXO_STREAM_UPLOAD_MBPS", "10"))
STREAM_PROFILE = os.getenv("NEXO_STREAM_PROFILE", "auto")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_RECONNECT_SECONDS = float(os.getenv("DISCORD_RECONNECT_SECONDS", "15"))
DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
DISCORD_PERSONAL_FOLLOWUP_ENABLED = os.getenv("DISCORD_PERSONAL_FOLLOWUP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
DISCORD_PERSONAL_FOLLOWUP_SECONDS = float(os.getenv("DISCORD_PERSONAL_FOLLOWUP_SECONDS", "1800"))
DISCORD_OWNER_NAME = os.getenv("DISCORD_OWNER_NAME", "Camilo")
DISCORD_PERSONAL_OBJECTIVES = os.getenv(
    "DISCORD_PERSONAL_OBJECTIVES",
    "Geopolítica, economía, RRSS, evolución de código, ejecución de metas",
)

AI_WEB_INTELLIGENCE_ENABLED = os.getenv("AI_WEB_INTELLIGENCE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
AI_SUPERVISOR_POLL_SECONDS = float(os.getenv("AI_SUPERVISOR_POLL_SECONDS", "10"))
AI_CONTEXT_UPDATE_SECONDS = float(os.getenv("AI_CONTEXT_UPDATE_SECONDS", "180"))
AI_WEB_MONITOR_ENABLED = os.getenv("AI_WEB_MONITOR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
AI_WEB_MONITOR_SECONDS = float(os.getenv("AI_WEB_MONITOR_SECONDS", "300"))
AI_WEB_MONITOR_LIMIT = int(os.getenv("AI_WEB_MONITOR_LIMIT", "20"))
AI_WEB_MONITOR_TIMEOUT = float(os.getenv("AI_WEB_MONITOR_TIMEOUT", "60"))
AI_VISUAL_GUARD_ENABLED = os.getenv("AI_VISUAL_GUARD_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
AI_VISUAL_GUARD_SECONDS = float(os.getenv("AI_VISUAL_GUARD_SECONDS", "30"))
AI_VISUAL_HTTP_TIMEOUT = float(os.getenv("AI_VISUAL_HTTP_TIMEOUT", "10"))
AI_DATA_FRESHNESS_MAX_AGE_SECONDS = float(os.getenv("AI_DATA_FRESHNESS_MAX_AGE_SECONDS", "600"))
AI_INNOVATION_SCOUT_ENABLED = os.getenv("AI_INNOVATION_SCOUT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
AI_INNOVATION_SCOUT_SECONDS = float(os.getenv("AI_INNOVATION_SCOUT_SECONDS", "3600"))

_cors_raw = os.getenv(
    "NEXO_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,http://localhost:8000",
)
CORS_ORIGINS: List[str] = [item.strip() for item in _cors_raw.split(",") if item.strip()]

_allowed_hosts_raw = os.getenv("NEXO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS: List[str] = [item.strip() for item in _allowed_hosts_raw.split(",") if item.strip()]

REQUEST_MAX_BYTES = int(os.getenv("NEXO_REQUEST_MAX_BYTES", "1048576"))
ENABLE_SECURITY_HEADERS = os.getenv("NEXO_ENABLE_SECURITY_HEADERS", "true").lower() in {"1", "true", "yes", "on"}

NEXO_API_KEY = os.getenv("NEXO_API_KEY", "")
_protected_paths_raw = os.getenv("NEXO_PROTECTED_PATH_PREFIXES", "/agente,/api/stream,/api/ai")
PROTECTED_PATH_PREFIXES: List[str] = [item.strip() for item in _protected_paths_raw.split(",") if item.strip()]

RATE_LIMIT_READ_PER_MIN = int(os.getenv("NEXO_RATE_LIMIT_READ_PER_MIN", "240"))
RATE_LIMIT_WRITE_PER_MIN = int(os.getenv("NEXO_RATE_LIMIT_WRITE_PER_MIN", "60"))
