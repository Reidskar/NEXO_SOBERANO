import os
import sys
from pathlib import Path

# Setup local imports
sys_path = Path(__file__).resolve().parent.parent
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from NEXO_CORE.core.database import get_db_context
from sqlalchemy import text

def setup_rls():
    print("--- Configurando RLS en Supabase ---")
    with get_db_context() as db:
        # Habilitar RLS en tablas globales
        db.execute(text("ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;"))
        db.execute(text("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;"))
        db.execute(text("ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;"))
        
        # Políticas básicas (simplificadas para el demo)
        # Nota: En producción esto usaría JWT claims. Aquí permitimos acceso si el rol es 'authenticated'
        # o basado en el tenant_id.
        
        sql_policies = """
        -- Policy para tenants: usuarios ven su propio tenant
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_policy') THEN
                CREATE POLICY tenant_isolation_policy ON public.tenants
                FOR ALL TO authenticated USING (slug = current_setting('request.jwt.claims', true)::jsonb->>'tenant_slug');
            END IF;
        END $$;
        """
        # db.execute(text(sql_policies)) # Comentado porque requiere configuración de JWT en Supabase
        
        db.commit()
        print("INFO: RLS habilitado en tablas public.tenants, public.users, public.sessions")

if __name__ == "__main__":
    setup_rls()
