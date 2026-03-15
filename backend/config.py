import os
from pathlib import Path
from dataclasses import dataclass

ROOT_DIR = Path(__file__).parent.parent
PROJECT_DIR = ROOT_DIR
NEXO_DIR = PROJECT_DIR / "NEXO_SOBERANO"
DB_PATH = NEXO_DIR / "base_sqlite" / "boveda.db"
CHROMA_DIR = NEXO_DIR / "memoria_vectorial"
DOCS_DIR = PROJECT_DIR / "documentos"
BITACORA = NEXO_DIR / "bitacora" / "evolucion.md"
ENV_FILE = PROJECT_DIR / ".env"

NEXO_MODE = os.getenv("NEXO_MODE", "local").lower()
IS_PRODUCTION = NEXO_MODE == "railway"
PORT = int(os.getenv("PORT", 8000))

DATABASE_URL = os.getenv("DATABASE_URL", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODELO_FLASH = os.getenv("GEMINI_MODEL_FLASH", "gemini-2.5-flash-lite")
MODELO_PRO = os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-pro")

OWNER_DISPLAY_NAME = os.getenv("NEXO_OWNER_NAME", "Soberano")

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

EMBED_LOCAL = "all-MiniLM-L6-v2"
EMBED_GEMINI = "models/embedding-001"
TOP_K = 5

@dataclass
class Config:
    # Entorno
    MODE: str = NEXO_MODE
    IS_PRODUCTION: bool = IS_PRODUCTION
    PORT: int = PORT

    # Base de datos
    DATABASE_URL: str = DATABASE_URL
    SUPABASE_URL: str = SUPABASE_URL
    SUPABASE_KEY: str = SUPABASE_KEY

    # IA
    GEMINI_API_KEY: str = GEMINI_API_KEY
    ANTHROPIC_API_KEY: str = ANTHROPIC_API_KEY

    # Redis
    UPSTASH_REDIS_URL: str = UPSTASH_REDIS_URL

    # Discord
    DISCORD_TOKEN: str = DISCORD_TOKEN

    def validate(self):
        """Valida que las variables críticas estén presentes."""
        required = {
            "DATABASE_URL": self.DATABASE_URL,
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_KEY": self.SUPABASE_KEY,
            "GEMINI_API_KEY": self.GEMINI_API_KEY,
        }
        faltantes = [k for k, v in required.items() if not v]
        if faltantes:
            # En local solo loggeamos, en prod podría ser crítico
            print(f"[WARN] Variables faltantes: {faltantes}")
        return True

config = Config()

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
BITACORA.parent.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    config.validate()
