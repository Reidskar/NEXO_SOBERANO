from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".env.local", override=True)

COMPUTRABAJO_EMAIL = os.getenv("COMPUTRABAJO_EMAIL", "")
COMPUTRABAJO_PASSWORD = os.getenv("COMPUTRABAJO_PASSWORD", "")
COMPUTRABAJO_URL = os.getenv("COMPUTRABAJO_URL", "https://www.computrabajo.cl")
SEARCH_URL = os.getenv("SEARCH_URL", "https://www.computrabajo.cl/trabajo-de-desarrollador")

MIN_SALARY_CLP = int(os.getenv("MIN_SALARY_CLP", "900000"))
MAX_DISTANCE_KM = int(os.getenv("MAX_DISTANCE_KM", "30"))
KEYWORDS_REQUIRED = [x.strip() for x in os.getenv("KEYWORDS_REQUIRED", "python,backend,ia").split(",") if x.strip()]

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto")  # auto|anthropic|openai|heuristic
MIN_AI_SCORE = int(os.getenv("MIN_AI_SCORE", "7"))

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "nexo-alertas")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")

GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}
CYCLE_HOURS = float(os.getenv("CYCLE_HOURS", "4"))
MAX_CYCLE_RETRIES = int(os.getenv("MAX_CYCLE_RETRIES", "2"))
RETRY_BACKOFF_SECONDS = int(os.getenv("RETRY_BACKOFF_SECONDS", "20"))
MAX_APPLICATIONS_PER_CYCLE = int(os.getenv("MAX_APPLICATIONS_PER_CYCLE", "1"))
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in {"1", "true", "yes", "on"}

DEVICE_ID = os.getenv("DEVICE_ID", os.getenv("COMPUTERNAME", "device-unknown"))

STATE_DIR_RAW = os.getenv("STATE_DIR", "")
if STATE_DIR_RAW:
	_candidate = Path(STATE_DIR_RAW)
	STATE_DIR = _candidate if _candidate.is_absolute() else (BASE_DIR / _candidate)
else:
	STATE_DIR = DATA_DIR
STATE_DIR.mkdir(parents=True, exist_ok=True)

CV_PROFILE_FILE_RAW = os.getenv("CV_PROFILE_FILE", "cv_profile.json")
_cv_candidate = Path(CV_PROFILE_FILE_RAW)
CV_PROFILE_FILE = _cv_candidate if _cv_candidate.is_absolute() else (BASE_DIR / _cv_candidate)

LOCK_STALE_MINUTES = int(os.getenv("LOCK_STALE_MINUTES", "90"))
CYCLE_LOCK_FILE = STATE_DIR / "cycle.lock"
SEEN_JOBS_FILE = STATE_DIR / "seen_jobs.json"
CSV_LOG_FILE = STATE_DIR / "postulaciones_log.csv"
RUN_STATE_FILE = STATE_DIR / "run_state.json"
RUN_LOG_FILE = STATE_DIR / "agent_runtime.log"


def _load_cv_profile() -> dict:
	default_profile = {
		"full_name": "",
		"headline": "Perfil backend/IA",
		"summary": "Experiencia en backend, automatización e integración de IA.",
		"roles_preferred": ["backend", "python", "ia"],
		"skills_must": ["python", "backend"],
		"skills_bonus": ["fastapi", "sql", "ia", "api"],
		"seniority_preferred": ["semi senior", "senior"],
		"locations_preferred": ["remoto", "híbrido"],
		"industries_preferred": [],
		"exclude_keywords": ["práctica", "practica", "trainee", "becario"],
		"salary_min_clp": MIN_SALARY_CLP,
		"remote_preferred": True,
	}
	if not CV_PROFILE_FILE.exists():
		return default_profile
	try:
		import json

		loaded = json.loads(CV_PROFILE_FILE.read_text(encoding="utf-8"))
		if isinstance(loaded, dict):
			merged = default_profile.copy()
			merged.update(loaded)
			return merged
	except Exception:
		pass
	return default_profile


CV_PROFILE = _load_cv_profile()
