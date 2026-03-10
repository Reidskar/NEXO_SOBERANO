"""
Configuración centralizada del backend Nexo Soberano
"""

import os
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
# RUTAS
# ════════════════════════════════════════════════════════════════════

ROOT_DIR = Path(__file__).parent.parent
PROJECT_DIR = ROOT_DIR
NEXO_DIR = PROJECT_DIR / "NEXO_SOBERANO"
DB_PATH = NEXO_DIR / "base_sqlite" / "boveda.db"
CHROMA_DIR = NEXO_DIR / "memoria_vectorial"
DOCS_DIR = PROJECT_DIR / "documentos"
BITACORA = NEXO_DIR / "bitacora" / "evolucion.md"
ENV_FILE = PROJECT_DIR / ".env"

# ════════════════════════════════════════════════════════════════════
# AMBIENTE
# ════════════════════════════════════════════════════════════════════

def load_env():
    """Carga variables de .env"""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

# ════════════════════════════════════════════════════════════════════
# FASTAPI
# ════════════════════════════════════════════════════════════════════

APP_TITLE = "Nexo Soberano API"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Plataforma de inteligencia híbrida RAG - Backend unificado"

HOST = os.getenv("NEXO_HOST", os.getenv("HOST", "0.0.0.0"))
PORT = int(os.getenv("NEXO_PORT", os.getenv("PORT", 8000)))
NEXO_MODE = os.getenv("NEXO_MODE", "local").lower()  # 'local' o 'cloud'
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "")
RAILWAY_URL = os.getenv("RAILWAY_URL", "")

# CORS — lee orígenes extra desde .env (separados por coma)
_extra_origins = [
    o.strip() for o in os.getenv("NEXO_CORS_ORIGINS", "").split(",") if o.strip()
]
CORS_ORIGINS = list(dict.fromkeys([
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
] + _extra_origins))

# ════════════════════════════════════════════════════════════════════
# GEMINI / LLM
# ════════════════════════════════════════════════════════════════════

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODELO_FLASH = os.getenv("GEMINI_MODEL_FLASH", "gemini-2.5-flash-lite")
MODELO_PRO = os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-pro")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_API_URL = os.getenv("XAI_API_URL", "https://api.x.ai/v1/chat/completions")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-beta")
LLM_PROVIDER = os.getenv("NEXO_LLM_PROVIDER", "auto").strip().lower()

# ════════════════════════════════════════════════════════════════════
# EMBEDDINGS
# ════════════════════════════════════════════════════════════════════

EMBED_LOCAL = "all-MiniLM-L6-v2"
EMBED_GEMINI = "models/embedding-001"

# ════════════════════════════════════════════════════════════════════
# RAG
# ════════════════════════════════════════════════════════════════════

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
TOP_K = 5
MAX_MB = 50  # Tamaño máximo de archivo

# Presupuesto GEMINI
MAX_TOKENS_DIA = 900_000
RELEVANCE_THRESHOLD = 0.65  # Distancia cosina máxima

# Fuentes que merecen análisis Pro (más caro) vs Flash
FUENTES_ALTO = [
    "OTAN", "NATO", "Rusia", "Russia", "China", "Iran", "Ucrania",
    "Ukraine", "Gaza", "Economia_Austriaca", "Latam", "MiddleEast",
]

# ════════════════════════════════════════════════════════════════════
# FORMATOS SOPORTADOS
# ════════════════════════════════════════════════════════════════════

EXTENSION_SOPORTADAS = {'.pdf', '.txt', '.md', '.docx', '.csv', '.jpg', '.jpeg', '.png'}

# ════════════════════════════════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════════════════════════════════

LOG_LEVEL = os.getenv("NEXO_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO"))
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ════════════════════════════════════════════════════════════════════
# INICIALIZAR DIRECTORIOS
# ════════════════════════════════════════════════════════════════════

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
BITACORA.parent.mkdir(parents=True, exist_ok=True)
