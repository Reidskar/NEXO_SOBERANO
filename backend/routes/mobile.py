# backend/routes/mobile.py
# backend/routes/mobile.py — versión con persistencia Supabase + comandos remotos
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from collections import deque
import logging, os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# Cache en memoria + persistencia
mobile_agents: dict = {}

# Cola de comandos pendientes por agente: agent_id → deque de comandos
_command_queues: dict[str, deque] = {}

ALLOWED_COMMANDS = {
    # ── Xiaomi / Termux ─────────────────────────────────────────────
    "silenciar",        # termux-volume media 0
    "volumen_max",      # termux-volume media 15
    "pantalla_off",     # termux-screen-off
    "vibrar",           # termux-vibrate
    "ubicacion",        # termux-location
    "foto_frontal",     # termux-camera-photo -c 1
    "toast",            # termux-toast <mensaje>
    "reiniciar_tailscale",  # pkill tailscale && tailscale up
    "ping",             # responde con pong para verificar conectividad
    # ── Dell Notebook (Windows/Linux) ───────────────────────────────
    "screenshot",       # captura de pantalla → base64
    "lock_pantalla",    # bloquear sesión
    "abrir_app",        # abrir aplicación por nombre/path
    "notificacion_win", # notificación toast de Windows
    "ejecutar_cmd",     # ejecutar comando shell (restringido)
    "volumen_notebook", # controlar volumen del notebook
}

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

    # Devolver comandos pendientes en la respuesta del heartbeat
    pendientes = []
    if agent_id in _command_queues:
        while _command_queues[agent_id]:
            pendientes.append(_command_queues[agent_id].popleft())

    return {"ok": True, "agent_id": agent_id, "comandos": pendientes}


@router.post("/comando/{agent_id}")
async def enviar_comando(agent_id: str, body: dict):
    """
    Encola un comando para un agente mobile.
    El agente lo recibe en el próximo heartbeat.
    body: { "accion": "silenciar" | "pantalla_off" | "ubicacion" | ..., "params": {} }
    """
    accion = body.get("accion", "")
    if accion not in ALLOWED_COMMANDS:
        raise HTTPException(400, detail=f"Acción no permitida: {accion}. Válidas: {sorted(ALLOWED_COMMANDS)}")

    if agent_id not in _command_queues:
        _command_queues[agent_id] = deque()

    cmd = {
        "id": f"cmd_{int(datetime.now().timestamp()*1000)}",
        "accion": accion,
        "params": body.get("params", {}),
        "encolado_en": datetime.now(timezone.utc).isoformat(),
    }
    _command_queues[agent_id].append(cmd)
    logger.info(f"[MOBILE CMD] Comando '{accion}' encolado para {agent_id}")

    # Verificar si el agente está online (último heartbeat < 60s)
    agente = mobile_agents.get(agent_id)
    if agente:
        from datetime import datetime as dt
        ultimo = agente.get("ultimo_contacto", "")
        if ultimo:
            try:
                diff = (dt.now(timezone.utc) - dt.fromisoformat(ultimo)).total_seconds()
                online = diff < 60
            except Exception:
                online = False
        else:
            online = False
    else:
        online = False

    return {
        "ok": True,
        "cmd_id": cmd["id"],
        "agente_online": online,
        "mensaje": f"Comando '{accion}' encolado — se ejecutará en el próximo heartbeat (~15s)" if not online
                   else f"Comando '{accion}' encolado — agente online, se ejecutará en segundos",
    }


@router.get("/comando/{agent_id}/poll")
async def poll_comandos(agent_id: str):
    """
    Endpoint de polling directo para el agente mobile (alternativa al heartbeat).
    Devuelve y vacía la cola de comandos pendientes.
    """
    pendientes = []
    if agent_id in _command_queues:
        while _command_queues[agent_id]:
            pendientes.append(_command_queues[agent_id].popleft())
    return {"comandos": pendientes, "agent_id": agent_id}

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


@router.post("/resultado")
async def recibir_resultado(data: dict):
    """
    Recibe el resultado de un comando ejecutado por el agente.
    Ej: foto_frontal devuelve path, ubicacion devuelve coords.
    """
    agent_id  = data.get("agent_id", "unknown")
    cmd_id    = data.get("cmd_id", "?")
    tipo      = data.get("tipo", "?")
    resultado = data.get("data", {})
    logger.info(f"[MOBILE RESULT] {agent_id} | cmd={cmd_id} | tipo={tipo} | data={resultado}")

    # Persistir en Supabase si disponible
    try:
        sb = _get_supabase()
        sb.table("mobile_results").insert({
            "agent_id": agent_id,
            "cmd_id": cmd_id,
            "tipo": tipo,
            "resultado": resultado,
            "recibido_en": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # Sin Supabase, solo log

    return {"ok": True, "cmd_id": cmd_id}
