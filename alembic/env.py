from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

import os
import sys

# ── Añadir raíz del proyecto al path ──────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Imports de NEXO ───────────────────────────────────────────
from NEXO_CORE.models.schema import Base
from NEXO_CORE.core.database import DATABASE_URL

# ── Config Alembic ─────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sobreescribir la URL con la variable de entorno real
# (ignora el placeholder "driver://user:pass@localhost/dbname" del alembic.ini)
# Se escapan los '%' como '%%' para evitar errores de interpolación de ConfigParser con passwords cacheados
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata

# Schema objetivo: "public" por defecto.
# Para migrar un tenant específico, pasar la variable de entorno:
#   ALEMBIC_TARGET_SCHEMA=tenant_demo alembic upgrade head
TARGET_SCHEMA = os.getenv("ALEMBIC_TARGET_SCHEMA", "public")


# ── Modo OFFLINE ───────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Genera SQL sin conectarse a la DB.
    Útil para auditar qué se va a ejecutar:
        alembic upgrade head --sql > migration_preview.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=TARGET_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Modo ONLINE ────────────────────────────────────────────────

def run_migrations_online() -> None:
    """
    Conecta a PostgreSQL y aplica las migraciones.

    Si ALEMBIC_TARGET_SCHEMA != "public", el schema del tenant se crea
    automáticamente y se establece como search_path de la sesión antes
    de correr las migraciones, para que todas las tablas se creen allí.

    La tabla alembic_version se guarda también en el schema correcto,
    por lo que cada tenant tiene su propio historial de versiones.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Para un schema de tenant: crearlo si no existe y hacer SET search_path
        if TARGET_SCHEMA != "public":
            connection.execute(
                text(f'CREATE SCHEMA IF NOT EXISTS "{TARGET_SCHEMA}"')
            )
            connection.execute(
                text(f'SET search_path TO "{TARGET_SCHEMA}", public')
            )
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Versiones en el schema correcto (no mezclar entre tenants)
            version_table="alembic_version",
            version_table_schema=TARGET_SCHEMA,
            include_schemas=True,
            # Filtro para autogenerate: solo incluir objetos del schema objetivo
            include_object=_include_object,
            # Detectar cambios de tipo y defaults del servidor
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def _include_object(object, name, type_, reflected, compare_to):
    """
    Le dice a Alembic --autogenerate qué objetos comparar.

    En schema "public"   → solo tablas globales (tenants, users, sessions).
    En schema "tenant_*" → solo tablas de tenant.

    Sin este filtro, --autogenerate detectaría las tablas de TODOS los schemas
    y generaría migraciones duplicadas o incorrectas.
    """
    if type_ == "table":
        obj_schema = getattr(object, "schema", None) or "public"
        if TARGET_SCHEMA == "public":
            # Solo tablas sin schema explícito (las del schema public)
            return obj_schema == "public"
        else:
            return obj_schema in (TARGET_SCHEMA, "public")
    return True


# ── Punto de entrada ───────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
