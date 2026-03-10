"""
backend/config_multitenant.py
==============================
Configuración central para NEXO SOBERANO multi-tenant.
Reemplaza el config.py original.

FILOSOFÍA DE COSTOS:
- Embedding: siempre local (sentence-transformers, costo = $0)
- Modelo default: gemini-1.5-flash (el más barato que funciona bien)
- GPT-4 / GPT-4o: DESACTIVADOS por defecto, activar por plan
- Caché semántico: activado siempre (ahorra 40-60% de tokens)
- Caché Redis: TTL agresivo para datos que no cambian rápido
"""

import os
from pathlib import Path
from functools import lru_cache

# ── Base ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Base de datos ──────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://nexo:nexo_dev_password@localhost:5432/nexo_soberano"
)

# ── Redis ──────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── Qdrant (vector store) ──────────────────────────────────────
QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = "nexo_docs"  # Una colección, namespace por tenant_id

# ── IA — FILOSOFÍA: LO MÁS BARATO PRIMERO ─────────────────────
# Gemini Flash: $0.075 / 1M tokens input → el default
# Gemini Pro:   $1.25  / 1M tokens → solo para razonamiento
# GPT-4o-mini:  $0.15  / 1M tokens → alternativa si Gemini falla
# GPT-4:        $10    / 1M tokens → NUNCA automático
MODELO_DEFAULT        = "gemini-1.5-flash"
MODELO_COMPLEJO       = "gemini-1.5-pro"
MODELO_FALLBACK       = "gpt-4o-mini"
MODELO_TWITTER        = "grok-beta"

# Desactivar GPT-4 de la rotación automática
OPENAI_GPT4_ENABLED   = os.getenv("OPENAI_GPT4_ENABLED", "false").lower() == "true"

# API Keys (cada tenant puede tener las suyas via DB, estas son las del sistema)
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
GROK_API_KEY      = os.getenv("GROK_API_KEY", "")

# ── Embedding LOCAL (costo = $0) ──────────────────────────────
# all-MiniLM-L6-v2: 90MB, rápido en CPU, buena calidad para RAG
EMBED_MODEL_LOCAL = "all-MiniLM-L6-v2"
EMBED_DIMENSION   = 384
USE_LOCAL_EMBED   = True  # Cambiar a False para usar Gemini embedding (cuesta tokens)

# ── RAG ────────────────────────────────────────────────────────
CHUNK_SIZE          = 400   # caracteres por chunk
CHUNK_OVERLAP       = 50    # overlap entre chunks
TOP_K               = 5     # resultados del vector search
RELEVANCE_THRESHOLD = 0.65  # similitud mínima para incluir en contexto

# ── Caché ──────────────────────────────────────────────────────
CACHE_TTL_PREFERENCES  = 3600      # 1 hora (perfiles cambian poco)
CACHE_TTL_RAG_RESULT   = 300       # 5 min (resultados RAG)
CACHE_TTL_BUDGET       = 30        # 30 seg (presupuesto)
CACHE_TTL_SEMANTIC     = 3600 * 4  # 4 horas (respuestas cacheadas semánticamente)

# ── Límites por plan ───────────────────────────────────────────
PLAN_CONFIGS = {
    "starter": {
        "max_users": 3,
        "max_tokens_dia": 50_000,
        "max_storage_mb": 200,
        "modelos_permitidos": ["gemini-1.5-flash"],
        "features": ["chat", "rag", "notifications"],
    },
    "pro": {
        "max_users": 15,
        "max_tokens_dia": 200_000,
        "max_storage_mb": 2000,
        "modelos_permitidos": ["gemini-1.5-flash", "gemini-1.5-pro", "gpt-4o-mini"],
        "features": ["chat", "rag", "notifications", "calendar", "cloud_sync"],
    },
    "enterprise": {
        "max_users": 999,
        "max_tokens_dia": 900_000,
        "max_storage_mb": 50000,
        "modelos_permitidos": ["gemini-1.5-flash", "gemini-1.5-pro", "gpt-4o-mini", "gpt-4o", "grok-beta"],
        "features": ["chat", "rag", "notifications", "calendar", "cloud_sync", "obs", "discord", "analytics"],
    },
}

# ── Seguridad ──────────────────────────────────────────────────
SECRET_KEY         = os.getenv("SECRET_KEY", "CAMBIAR_EN_PRODUCCION_con_openssl_rand_hex_32")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRE_MINUTES = 60 * 8  # 8 horas

# ── Celery / Workers ───────────────────────────────────────────
CELERY_BROKER_URL  = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# ── Email ──────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ── Directorios ────────────────────────────────────────────────
LOG_DIR      = BASE_DIR / "logs"
DOCS_DIR     = BASE_DIR / "documentos"
REPORTS_DIR  = BASE_DIR / "reportes_cifrados"

for d in [LOG_DIR, DOCS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUPS   = 5

# ── Sentry (opcional) ──────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# ── Validación de arranque ─────────────────────────────────────
def validar_config():
    """Verifica que la configuración mínima esté presente al arrancar."""
    errores = []

    if not DATABASE_URL or "CAMBIAR" in DATABASE_URL:
        errores.append("DATABASE_URL no configurada")

    if not GEMINI_API_KEY and not OPENAI_API_KEY:
        errores.append("Se necesita al menos GEMINI_API_KEY u OPENAI_API_KEY")

    if SECRET_KEY == "CAMBIAR_EN_PRODUCCION_con_openssl_rand_hex_32":
        errores.append("SECRET_KEY usa valor por defecto inseguro")

    if errores:
        log.info("\n⚠️  ADVERTENCIAS DE CONFIGURACIÓN:")
        for e in errores:
            log.info(f"   - {e}")
        print()

    return len(errores) == 0
