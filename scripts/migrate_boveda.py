import os
import sqlite3
import logging
import uuid
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup local imports
sys_path = Path(__file__).resolve().parent.parent
import sys
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from NEXO_CORE.models.schema import (
    Base, Evidencia, VectorizadosLog, Consulta, CostoAPI, Alerta, CognitiveProfile, Tenant
)
from NEXO_CORE.core.database import set_tenant_schema

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("migration_boveda")

ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT_DIR / "NEXO_SOBERANO" / "base_sqlite" / "boveda.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_sqlite_conn():
    if not SQLITE_PATH.exists():
        logger.error(f"SQLite DB not found at {SQLITE_PATH}")
        return None
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_boveda(tenant_slug="demo"):
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in environment")
        return

    logger.info(f"Starting migration for tenant: {tenant_slug}")
    pg_engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=pg_engine)
    session = Session()

    # ensure tenant exists
    tenant = session.query(Tenant).filter_by(slug=tenant_slug).first()
    if not tenant:
        logger.error(f"Tenant '{tenant_slug}' not found. Run create_demo_tenant.py first.")
        session.close()
        return

    # Set schema
    target_schema = f"tenant_{tenant_slug}"
    session.execute(text(f"SET search_path TO {target_schema}, public"))

    sqlite_conn = get_sqlite_conn()
    if not sqlite_conn:
        session.close()
        return

    try:
        # 1. Evidencia
        rows = sqlite_conn.execute("SELECT * FROM evidencia").fetchall()
        logger.info(f"Migrating {len(rows)} rows to evidencia...")
        for row in rows:
            r = dict(row)
            content_hash = r['hash_sha256']
            exists = session.query(Evidencia).filter_by(content_hash=content_hash).first()
            if not exists:
                meta = {
                    "ruta_local": r.get('ruta_local'),
                    "link_nube": r.get('link_nube'),
                    "dominio": r.get('dominio'),
                    "nivel_confianza": r.get('nivel_confianza'),
                    "impacto": r.get('impacto')
                }
                obj = Evidencia(
                    content_hash=content_hash,
                    filename=r.get('nombre_archivo'),
                    file_type=r.get('categoria'),
                    content_text=r.get('resumen_ia'),
                    vectorizado=bool(r.get('vectorizado')),
                    metadata_={k: v for k, v in meta.items() if v is not None},
                    created_at=datetime.fromisoformat(r['fecha_ingesta']) if r.get('fecha_ingesta') else None
                )
                session.add(obj)
        session.commit()

        # 2. Consultas
        rows = sqlite_conn.execute("SELECT * FROM consultas").fetchall()
        logger.info(f"Migrating {len(rows)} rows to consultas...")
        for row in rows:
            r = dict(row)
            obj = Consulta(
                pregunta=r['pregunta'],
                respuesta=r['respuesta'],
                duracion_ms=r.get('ms', 0),
                created_at=datetime.fromisoformat(r['fecha']) if r.get('fecha') else None
            )
            session.add(obj)
        session.commit()

        # 3. Costos API (includes legacy tables)
        tables_costos = ['costos_api', 'costos_ia', 'costos_servicios']
        for t_name in tables_costos:
            try:
                rows = sqlite_conn.execute(f"SELECT * FROM {t_name}").fetchall()
                logger.info(f"Migrating {len(rows)} rows from {t_name} to costos_api...")
                for row in rows:
                    r = dict(row)
                    obj = CostoAPI(
                        modelo=r.get('modelo', 'unknown'),
                        tokens_in=r.get('tokens_in', 0),
                        tokens_out=r.get('tokens_out', 0),
                        operacion=r.get('operacion', t_name),
                        created_at=datetime.fromisoformat(r['fecha']) if r.get('fecha') else None
                    )
                    session.add(obj)
                session.commit()
            except sqlite3.OperationalError:
                logger.warning(f"Table {t_name} not found in SQLite")

        # 4. Alertas
        rows = sqlite_conn.execute("SELECT * FROM alertas").fetchall()
        logger.info(f"Migrating {len(rows)} rows to alertas...")
        for row in rows:
            r = dict(row)
            obj = Alerta(
                tipo=r.get('tipo', 'general'),
                severidad=float(r.get('gravedad', 5)) / 10,
                titulo=r.get('texto', 'Sin título')[:512],
                descripcion=r.get('texto'),
                procesada=bool(r.get('enviado')),
                created_at=datetime.fromisoformat(r['fecha']) if r.get('fecha') else None
            )
            session.add(obj)
        session.commit()

        logger.info("Migration of boveda.db completed successfully!")

    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        sqlite_conn.close()
        session.close()

if __name__ == "__main__":
    migrate_boveda("demo")
