import os
from supabase import create_client, Client
from NEXO_CORE import config

# Las claves deben estar en el .env env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_client = None

def get_supabase() -> Client:
    """Retorna un cliente singleton de Supabase."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL o SUPABASE_SERVICE_KEY no configurados en .env")
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client
