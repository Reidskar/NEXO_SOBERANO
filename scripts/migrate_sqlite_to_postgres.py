import os
import sqlite3
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup local imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from NEXO_CORE.models.schema import (
    Base, Evidencia, VectorizadosLog, Consulta, CostoAPI, Alerta, CognitiveProfile
)
from NEXO_CORE.core.database import set_tenant_schema

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("migration")

ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_DIR = ROOT_DIR / "NEXO_SOBERANO" / "base_sqlite"
POSTGRES_URL = os.environ.get("DATABASE_URL", "postgresql://nexo_user:nexo_password@localhost:5432/nexo_db")

# Paths of SQLite legacy databases
DB_PATHS = {
    "boveda": SQLITE_DIR / "boveda.db",
    "preferences": SQLITE_DIR / "preferences.db",
    "notifications": SQLITE_DIR / "notifications.db",
    "calendar": SQLITE_DIR / "calendar.db",
    "conversations": SQLITE_DIR / "conversations.db",
    "cost_tracking": SQLITE_DIR / "cost_tracking.db",
    "auth": SQLITE_DIR / "auth.db"
}

def migrate_data(target_schema: str = "public"):
    """
    Migrates data from all relevant SQLite databases to the PostgreSQL schema.
    """
    logger.info(f"Connecting to PostgreSQL: {POSTGRES_URL}")
    pg_engine = create_engine(POSTGRES_URL)
    
    from sqlalchemy import text
    # Optional: ensure schema and tables are created
    from sqlalchemy.schema import CreateSchema
    with pg_engine.connect() as conn:
        conn.execute(CreateSchema(target_schema, if_not_exists=True))
        conn.commit()
    
    # The models are not automatically attached to this specific schema,
    # but we can set search_path or forcefully create them for the schema.
    # We'll rely on Alembic migrating the DB, but just in case:
    with pg_engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {target_schema}"))
        Base.metadata.create_all(conn)
        conn.commit()

    Session = sessionmaker(bind=pg_engine)
    session = Session()
    
    # Apply schema search path safely to session
    set_tenant_schema(session, target_schema)

    try:
        migrate_boveda(session)
        migrate_preferences(session)
        session.commit()
        logger.info(f"Migration to schema '{target_schema}' completed successfully!")
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        session.close()


def get_sqlite_conn(db_key: str):
    path = DB_PATHS[db_key]
    if not path.exists():
        logger.warning(f"Database {db_key} not found at {path}")
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

import uuid
from datetime import datetime

def migrate_boveda(pg_session):
    """
    Migrates from boveda.db: evidencia, vectorizados_log, consultas, costos_api, alertas
    """
    conn = get_sqlite_conn("boveda")
    if not conn: return
    
    # 1. evidencia
    try:
        rows = conn.execute("SELECT * FROM evidencia").fetchall()
        logger.info(f"Migrating {len(rows)} rows from evidencia...")
        for row in rows:
            # Map columns
            content_hash = row['hash_sha256']
            exists = pg_session.query(Evidencia).filter_by(content_hash=content_hash).first()
            if not exists:
                meta = {
                    "ruta_local": row['ruta_local'],
                    "link_nube": row['link_nube'],
                    "dominio": row['dominio'],
                    "nivel_confianza": row['nivel_confianza'],
                    "impacto": row['impacto']
                }
                obj = Evidencia(
                    content_hash=content_hash,
                    filename=row['nombre_archivo'],
                    file_type=row['categoria'],
                    content_text=row['resumen_ia'],
                    vectorizado=bool(row['vectorizado']),
                    metadata_={k: v for k, v in meta.items() if v is not None},
                    created_at=row['fecha_ingesta'] if isinstance(row['fecha_ingesta'], datetime) else None
                )
                pg_session.add(obj)
    except sqlite3.OperationalError:
        logger.warning("Table 'evidencia' does not exist in boveda.db")

    # 2. vectorizados_log
    try:
        rows = conn.execute("SELECT * FROM vectorizados_log").fetchall()
        logger.info(f"Migrating {len(rows)} rows from vectorizados_log...")
        for row in rows:
            # Note: Postgres model expects evidencia_id (UUID), SQLite has hash_sha256.
            # We skip this for now or find the evid_id
            evid = pg_session.query(Evidencia).filter_by(content_hash=row['hash_sha256']).first()
            log = VectorizadosLog(
                evidencia_id=evid.id if evid else None,
                filename=evid.filename if evid else None,
                created_at=row['fecha_vectorizacion'] if isinstance(row['fecha_vectorizacion'], datetime) else None
            )
            pg_session.add(log)
    except sqlite3.OperationalError:
        pass

    # 3. consultas
    try:
        rows = conn.execute("SELECT * FROM consultas").fetchall()
        logger.info(f"Migrating {len(rows)} rows from consultas...")
        for row in rows:
            obj = Consulta(
                pregunta=row['pregunta'],
                respuesta=row['respuesta'],
                duracion_ms=row['ms'],
                tokens_in=0, # Not in SQLite
                tokens_out=0,
                created_at=row['fecha'] if isinstance(row['fecha'], datetime) else None
            )
            pg_session.add(obj)
    except sqlite3.OperationalError:
        pass

    # 4. costos_api
    try:
        rows = conn.execute("SELECT * FROM costos_api").fetchall()
        logger.info(f"Migrating {len(rows)} rows from costos_api...")
        for row in rows:
            obj = CostoAPI(
                modelo=row['modelo'],
                tokens_in=row['tokens_in'],
                tokens_out=row['tokens_out'],
                operacion=row['operacion'],
                created_at=row['fecha'] if isinstance(row['fecha'], datetime) else None
            )
            pg_session.add(obj)
    except sqlite3.OperationalError:
        pass

    # 5. alertas
    try:
        rows = conn.execute("SELECT * FROM alertas").fetchall()
        logger.info(f"Migrating {len(rows)} rows from alertas...")
        for row in rows:
            obj = Alerta(
                tipo=row['tipo'],
                severidad=float(row['gravedad']) / 10 if isinstance(row['gravedad'], int) else 0.5,
                titulo=row['texto'][:512] if row['texto'] else "Sin título",
                descripcion=row['texto'],
                procesada=bool(row['enviado']),
                created_at=row['fecha'] if isinstance(row['fecha'], datetime) else None
            )
            pg_session.add(obj)
    except sqlite3.OperationalError:
        pass

    conn.close()


def migrate_preferences(pg_session):
    """
    Migrates cognitive_profile from preferences.db
    """
    conn = get_sqlite_conn("preferences")
    if not conn: return
    
    try:
        rows = conn.execute("SELECT * FROM cognitive_profile").fetchall()
        logger.info(f"Migrating {len(rows)} rows from cognitive_profile...")
        for row in rows:
            exists = pg_session.query(CognitiveProfile).filter_by(user_id=row['user_id']).first()
            if not exists:
                # Omit 'id' to let Postgres sequence handle it natively unless we want hardcoded IDs.
                # Since SQLite IDs overlap, we'll map them generically.
                profile_data = dict(row)
                if 'id' in profile_data:
                    del profile_data['id']
                pg_session.add(CognitiveProfile(**profile_data))
    except sqlite3.OperationalError:
        logger.warning("Table 'cognitive_profile' does not exist in preferences.db")
        
    conn.close()

if __name__ == "__main__":
    logger.info("--- NEXO SOBERANO: SQLite to PostgreSQL Multi-tenant Migration Script ---")
    logger.info("Executing this will migrate legacy SQLite DB components into a target PG schema.")
    
    # By default, migrating the local user to the "public" schema (or a specific tenant)
    # Allows parameterization later via Argparse or Env vars.
    TENANT_SCHEMA = os.environ.get("TENANT_SCHEMA", "public")
    
    migrate_data(TENANT_SCHEMA)
