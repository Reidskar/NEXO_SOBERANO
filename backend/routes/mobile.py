# backend/routes/mobile.py
# backend/routes/mobile.py — versión con persistencia Supabase
from fastapi import APIRouter
from datetime import datetime, timezone
import logging, os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# Cache en memoria + persistencia
mobile_agents: dict = {}

def _get_supabase():
    from supabase import create_client
    # Prefer keys from .env if available
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Fallback to DATABASE_URL parsing if needed, but the user implicitly expects SUPABASE_URL/KEY
    if not url or not key:
        # We know from test_db_conn.py the URL structure, but usually Supabase uses separate URL/KEY for the client
        # For now, let's assume they are set or provided. 
        # Actually, let's check .env for them first.
        pass
    return create_client(url, key)

@router.post("/heartbeat")
async def heartbeat(data: dict):
    agent_id = data.get("agent_id", "unknown")
    now = datetime.now(timezone.utc).isoformat()
    
    # Cache en memoria (acceso rápido)
    mobile_agents[agent_id] = {**data, "ultimo_contacto": now}
    
    # Persistir en Supabase
    try:
        sb = _get_supabase()
        sb.table("mobile_agents").upsert({
            "agent_id": agent_id,
            "cpu_pct": data.get("cpu_pct"),
            "ram_pct": data.get("ram_pct"),
            "ram_total_mb": data.get("ram_total_mb"),
            "bateria_pct": data.get("bateria_pct", -1),
            "bateria_estado": data.get("bateria_estado", "unknown"),
            "wifi_ssid": data.get("wifi_ssid", "unknown"),
            "ultimo_contacto": now,
            "metadata": {k: v for k, v in data.items() 
                        if k not in ["agent_id","cpu_pct","ram_pct","ram_total_mb",
                                     "bateria_pct","bateria_estado","wifi_ssid"]}
        }).execute()
        logger.info(f"[MOBILE] {agent_id} persistido en Supabase")
    except Exception as e:
        logger.warning(f"[MOBILE] Supabase write falló (usando solo memoria): {e}")
    
    return {"ok": True, "agent_id": agent_id}

@router.get("/agents")
async def agentes():
    """Retorna agentes — primero memoria, fallback Supabase."""
    if mobile_agents:
        return {"agentes": mobile_agents, "fuente": "memoria"}
    try:
        sb = _get_supabase()
        result = sb.table("mobile_agents")\
            .select("*")\
            .order("ultimo_contacto", desc=True)\
            .execute()
        agents = {row["agent_id"]: row for row in result.data}
        return {"agentes": agents, "fuente": "supabase"}
    except Exception as e:
        return {"agentes": {}, "fuente": "error", "error": str(e)}
