import os
import sys
import asyncio
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup local imports
sys_path = Path(__file__).resolve().parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from backend.services.vector_service import upsert_document
from NEXO_CORE.core.database import get_db_context, set_tenant_schema

async def index_evidencia(tenant_slug="demo"):
    print(f"Iniciando indexación en Qdrant para tenant: {tenant_slug}")
    
    with get_db_context() as db:
        set_tenant_schema(db, tenant_slug)
        
        # Consultar evidencia del tenant
        try:
            sql = text("SELECT id, content, metadata FROM evidencia")
            rows = db.execute(sql).fetchall()
        except Exception as e:
            print(f"Error consultando evidencia: {e}")
            return

        total = len(rows)
        print(f"Encontrados {total} documentos para indexar.")
        
        for i, row in enumerate(rows):
            try:
                # El metadata en Postgres suele ser un dict o JSON
                metadata = row.metadata if isinstance(row.metadata, dict) else {}
                upsert_document(
                    tenant_slug=tenant_slug,
                    doc_id=str(row.id),
                    text=row.content,
                    metadata=metadata
                )
                if (i + 1) % 10 == 0:
                    print(f"Indexados {i+1}/{total}...")
            except Exception as e:
                print(f"Error indexando doc {row.id}: {e}")

    print("Indexación completada.")

if __name__ == "__main__":
    asyncio.run(index_evidencia("demo"))
