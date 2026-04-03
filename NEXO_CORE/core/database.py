"""
NEXO_CORE/core/database.py
===========================
Motor de base de datos PostgreSQL con:
  - SQLAlchemy sync (compatible con FastAPI sync/async y Celery)
# Debug placeholders to trap rogue imports (REMOVE LATER)
core_webhook_router = None
core_health_router = None

# Inyección de dependencias para FastAPI (get_db)
  - Aislamiento por tenant via SET search_path
  - Helper para crear schemas nuevos al registrar tenants

Uso en un endpoint FastAPI:
    @router.post("/consulta")
    def consultar(
        request: Request,
        db: Session = Depends(get_db),
    ):
        tenant_slug = request.state.tenant_slug  # inyectado por TenantMiddleware
        set_tenant_schema(db, tenant_slug)
        ...
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool

# Import config to ensure .env is parsed and loaded into os.environ
from NEXO_CORE import config

# ── URL de conexión ────────────────────────────────────────────
# Docker inyecta esto como variable de entorno desde docker-compose.yml
# Desarrollo local sin Docker: exportar DATABASE_URL en tu shell o .env
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://nexo_user:nexo_password@localhost:5432/nexo_db"
)

# ── Motor SQLAlchemy ───────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # Detecta conexiones muertas antes de usar
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# ── Session Factory ────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Base declarativa compartida (importada en schema.py) ───────
class Base(DeclarativeBase):
    pass


# ── Aislamiento por tenant ─────────────────────────────────────

def set_tenant_schema(db: Session, tenant_slug: str) -> None:
    """
    Cambia el search_path de la sesión al schema del tenant.
    DEBE llamarse al inicio de cada operación que toque datos de un tenant.

    Efecto:
        SET search_path TO "tenant_mi_empresa", public

    A partir de ahí, cualquier query sin schema explícito busca primero
    en el schema del tenant, luego en public como fallback.
    """
    schema = slug_to_schema(tenant_slug)
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    db.execute(text(f'SET search_path TO "{schema}", public'))
    db.commit()


def reset_to_public(db: Session) -> None:
    """Vuelve al schema público (para operaciones de sistema / admin)."""
    db.execute(text("SET search_path TO public"))
    db.commit()


def create_tenant_schema_and_tables(db: Session, tenant_slug: str) -> str:
    """
    Crea el schema de un tenant nuevo y todas sus tablas.
    Llamar al registrar una empresa nueva en el sistema.

    Returns:
        Nombre del schema creado (ej: "tenant_mi_empresa")
    """
    schema = slug_to_schema(tenant_slug)
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    db.commit()

    set_tenant_schema(db, tenant_slug)
    Base.metadata.create_all(bind=engine)
    reset_to_public(db)

    return schema


def slug_to_schema(tenant_slug: str) -> str:
    """
    Convierte slug de tenant a nombre de schema Postgres válido.

    "mi-empresa"  → "tenant_mi_empresa"
    "Demo Corp"   → "tenant_demo_corp"
    "demo"        → "tenant_demo"
    """
    slug = tenant_slug.lower().strip()
    slug = slug.replace("-", "_").replace(" ", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    return f"tenant_{slug}"


# ── Dependency injection FastAPI ───────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI. Una sesión por request, cerrada al finalizar.

        @router.get("/evidencia")
        def listar(db: Session = Depends(get_db), req: Request = ...):
            set_tenant_schema(db, req.state.tenant_slug)
            return db.execute(text("SELECT * FROM evidencia")).fetchall()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager para uso fuera de FastAPI: scripts, Celery tasks.

        with get_db_context() as db:
            set_tenant_schema(db, "demo")
            db.execute(text("INSERT INTO evidencia ..."))
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Verificación de conexión ───────────────────────────────────

def verify_connection() -> bool:
    """
    Verifica que Postgres esté accesible. Llamar desde startup de main.py.
    Nunca loguea la password (solo muestra host:puerto/db).
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        host_info = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
        logger.info("✅ PostgreSQL conectado: %s", host_info)
        return True
    except Exception as e:
        logger.warning("❌ Error conectando a PostgreSQL: %s", e)
        return False
