import os
import sys
from pathlib import Path

# Setup local imports
sys_path = Path(__file__).resolve().parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from NEXO_CORE.core.database import get_db_context, create_tenant_schema_and_tables
from NEXO_CORE.models.schema import Tenant

def create_demo():
    print("--- Registro de Tenant Demo ---")
    with get_db_context() as db:
        # 1. Registrar en public
        existing = db.query(Tenant).filter_by(slug='demo').first()
        if not existing:
            t = Tenant(slug='demo', name='Demo', plan='pro')
            db.add(t)
            db.commit()
            print("INFO: Tenant 'demo' creado en public.tenants")
        else:
            print("INFO: Tenant 'demo' ya registrado")

        # 2. Inicializar esquema tenant_demo
        try:
            schema = create_tenant_schema_and_tables(db, 'demo')
            print(f"INFO: Esquema '{schema}' inicializado con éxito")
        except Exception as e:
            print(f"ERROR: No se pudo inicializar esquema: {e}")

if __name__ == "__main__":
    create_demo()
