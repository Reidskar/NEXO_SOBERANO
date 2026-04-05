# backend/routes/mobile.py — agente móvil con cola de comandos bidireccional
from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone
from typing import Optional
import logging, os, uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# ─── Estado en memoria ────────────────────────────────────────────────────────
mobile_agents: dict = {}
command_queues: dict[str, list] = {}   # agent_id → [{"id":..,"type":..,"payload":..}]

def _api_key_ok(key: Optional[str]) -> bool:
    expected = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    return key == expected

def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# ─── Heartbeat (phone → torre) ────────────────────────────────────────────────

@router.post("/heartbeat")
async def heartbeat(data: dict, x_api_key: str = Header(None)):
    agent_id = data.get("agent_id", "unknown")
    now = datetime.now(timezone.utc).isoformat()
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
                                      "bateria_pct","bateria_estado","wifi_ssid"]},
        }).execute()
    except Exception as e:
        logger.warning(f"[MOBILE] Supabase write falló: {e}")

    # Devolver comandos pendientes en la respuesta del heartbeat
    pending = command_queues.pop(agent_id, [])
    return {"ok": True, "agent_id": agent_id, "commands": pending}

# ─── Consulta de comandos (phone → torre, polling) ────────────────────────────

@router.get("/commands/{agent_id}")
async def get_commands(agent_id: str, x_api_key: str = Header(None)):
    """Phone hace polling cada 10s — devuelve comandos pendientes y los limpia."""
    cmds = command_queues.pop(agent_id, [])
    return {"agent_id": agent_id, "commands": cmds}

# ─── Enviar comando (torre → phone) ──────────────────────────────────────────

@router.post("/command/{agent_id}")
async def send_command(agent_id: str, cmd: dict, x_api_key: str = Header(None)):
    """
    Encola un comando para el agente móvil.
    Tipos: notify | location | screenshot | exec | ping | volume | torch | vibrate
    """
    if not _api_key_ok(x_api_key):
        raise HTTPException(status_code=401, detail="API Key inválida")
    if agent_id not in mobile_agents and agent_id != "*":
        # Permitir envío aunque el agente no haya hecho heartbeat aún
        logger.warning(f"[MOBILE] Comando para agente desconocido: {agent_id}")

    cmd["id"] = str(uuid.uuid4())[:8]
    cmd["ts"]  = datetime.now(timezone.utc).isoformat()

    if agent_id == "*":
        # Broadcast a todos los agentes registrados
        for aid in list(mobile_agents.keys()):
            command_queues.setdefault(aid, []).append(cmd)
        return {"queued": True, "broadcast": True, "agents": list(mobile_agents.keys())}

    command_queues.setdefault(agent_id, []).append(cmd)
    return {"queued": True, "agent_id": agent_id, "cmd_id": cmd["id"]}

# ─── Estado de agentes ────────────────────────────────────────────────────────

@router.get("/agents")
async def agentes():
    if mobile_agents:
        return {"agentes": mobile_agents, "fuente": "memoria"}
    try:
        sb = _get_supabase()
        result = sb.table("mobile_agents").select("*").order("ultimo_contacto", desc=True).execute()
        agents = {row["agent_id"]: row for row in result.data}
        return {"agentes": agents, "fuente": "supabase"}
    except Exception as e:
        return {"agentes": {}, "fuente": "error", "error": str(e)}

@router.get("/status/{agent_id}")
async def agent_status(agent_id: str):
    agent = mobile_agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")
    return {
        "agent": agent,
        "pending_commands": len(command_queues.get(agent_id, [])),
    }
