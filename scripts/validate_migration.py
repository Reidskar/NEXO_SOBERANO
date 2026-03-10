import os
import sys
import sqlite3
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup local imports
sys_path = Path(__file__).resolve().parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from NEXO_CORE.models.schema import Tenant

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("validate_migration")

ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT_DIR / "NEXO_SOBERANO" / "base_sqlite" / "boveda.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

def count_sqlite(table_name):
    if not SQLITE_PATH.exists():
        return 0
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        return count
    except:
        return 0
    finally:
        conn.close()

def validate(tenant_slug="demo"):
    if not DATABASE_URL:
        logger.error("DATABASE_URL no configurada")
        return

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    schema = f"tenant_{tenant_slug}"
    tables = {
        "evidencia": "evidencia",
        "consultas": "consultas",
        "alertas": "alertas",
        "costos_api": "costos_api"
    }

    print(f"\n--- Validando Migración: {tenant_slug} ---")
    print(f"{'Tabla':<15} | {'SQLite':<10} | {'Postgres':<10} | {'Estado'}")
    print("-" * 50)

    for pg_table, sqlite_table in tables.items():
        # Count PG
        try:
            sql = text(f"SELECT COUNT(*) FROM {schema}.{pg_table}")
            pg_count = session.execute(sql).scalar()
        except Exception as e:
            pg_count = f"Error"
        
        # Count SQLite
        sq_count = count_sqlite(sqlite_table)
        if pg_table == "costos_api":
            # Sum legacy tables in SQLite for comparison
            sq_count += count_sqlite("costos_ia")
            sq_count += count_sqlite("costos_servicios")

        status = "✅ OK" if str(pg_count) == str(sq_count) else "❌ DIFF"
        print(f"{pg_table:<15} | {sq_count:<10} | {pg_count:<10} | {status}")

    session.close()

if __name__ == "__main__":
    validate("demo")
