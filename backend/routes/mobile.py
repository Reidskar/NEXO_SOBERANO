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
agent_tools: dict[str, list] = {}      # agent_id → [lista de herramientas Termux detectadas]

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

# ─── Inventario de herramientas Termux ───────────────────────────────────────

# Lista completa de herramientas Termux:API que el agente puede detectar
TERMUX_TOOLS_CATALOG = {
    # Sensores y hardware
    "termux-battery-status":     {"cat": "hardware",  "desc": "Estado de batería (%, estado, cargando)"},
    "termux-sensor":             {"cat": "hardware",  "desc": "Sensores del dispositivo (acelerómetro, giroscopio, etc.)"},
    "termux-torch":              {"cat": "hardware",  "desc": "Control de linterna/flash"},
    "termux-vibrate":            {"cat": "hardware",  "desc": "Control de vibración"},
    "termux-volume":             {"cat": "hardware",  "desc": "Control de volumen por stream"},
    # Red y conectividad
    "termux-wifi-connectioninfo":{"cat": "network",   "desc": "Info de WiFi (SSID, RSSI, IP)"},
    "termux-wifi-scaninfo":      {"cat": "network",   "desc": "Escaneo de redes WiFi cercanas"},
    "termux-wifi-enable":        {"cat": "network",   "desc": "Habilitar/deshabilitar WiFi"},
    "termux-telephony-deviceinfo":{"cat":"network",   "desc": "Info de red celular (operadora, señal)"},
    "termux-telephony-call":     {"cat": "network",   "desc": "Realizar llamadas (requiere permiso)"},
    # Localización
    "termux-location":           {"cat": "location",  "desc": "GPS: lat, lng, altitud, precisión"},
    # Cámara y multimedia
    "termux-camera-info":        {"cat": "media",     "desc": "Info de cámaras disponibles"},
    "termux-camera-photo":       {"cat": "media",     "desc": "Tomar foto con cámara"},
    "termux-microphone-record":  {"cat": "media",     "desc": "Grabar audio del micrófono"},
    "termux-media-player":       {"cat": "media",     "desc": "Reproducir/pausar audio"},
    "termux-media-scan":         {"cat": "media",     "desc": "Escanear archivos de medios"},
    # UI y notificaciones
    "termux-notification":       {"cat": "ui",        "desc": "Mostrar notificaciones en barra"},
    "termux-notification-remove":{"cat": "ui",        "desc": "Eliminar notificaciones"},
    "termux-notification-list":  {"cat": "ui",        "desc": "Listar notificaciones activas"},
    "termux-dialog":             {"cat": "ui",        "desc": "Mostrar diálogos interactivos"},
    "termux-toast":              {"cat": "ui",        "desc": "Toast rápido en pantalla"},
    "termux-open-url":           {"cat": "ui",        "desc": "Abrir URL en browser"},
    "termux-share":              {"cat": "ui",        "desc": "Compartir contenido via Android"},
    # Sistema
    "termux-clipboard-get":      {"cat": "system",    "desc": "Leer portapapeles"},
    "termux-clipboard-set":      {"cat": "system",    "desc": "Escribir al portapapeles"},
    "termux-screenshot":         {"cat": "system",    "desc": "Captura de pantalla"},
    "termux-wake-lock":          {"cat": "system",    "desc": "Mantener CPU activa (no dormir)"},
    "termux-wake-unlock":        {"cat": "system",    "desc": "Liberar wake lock"},
    "termux-alarm":              {"cat": "system",    "desc": "Programar alarma"},
    "termux-job-scheduler":      {"cat": "system",    "desc": "Programar tareas periódicas"},
    # Mensajería
    "termux-sms-send":           {"cat": "messaging", "desc": "Enviar SMS (requiere permiso)"},
    "termux-sms-list":           {"cat": "messaging", "desc": "Listar SMS recibidos"},
    "termux-call-log":           {"cat": "messaging", "desc": "Historial de llamadas"},
    "termux-contact-list":       {"cat": "messaging", "desc": "Lista de contactos"},
    # Extras
    "termux-fingerprint":        {"cat": "security",  "desc": "Autenticación por huella"},
    "termux-tts-engines":        {"cat": "tts",       "desc": "Text-to-Speech disponible"},
    "termux-tts-speak":          {"cat": "tts",       "desc": "Hablar texto en voz alta"},
}


@router.post("/tools/{agent_id}")
async def register_tools(agent_id: str, data: dict, x_api_key: str = Header(None)):
    """
    Recibe el inventario de herramientas Termux disponibles en el dispositivo.
    El agente envía: {"tools": ["termux-battery-status", ...]}
    """
    tools = data.get("tools", [])
    agent_tools[agent_id] = tools

    # Enriquecer con metadatos del catálogo
    enriched = []
    for t in tools:
        info = TERMUX_TOOLS_CATALOG.get(t, {"cat": "unknown", "desc": t})
        enriched.append({"cmd": t, **info})

    # Actualizar metadatos del agente
    if agent_id in mobile_agents:
        mobile_agents[agent_id]["termux_tools"] = enriched
        mobile_agents[agent_id]["tools_count"]  = len(tools)

    # Generar comandos disponibles según herramientas detectadas
    available_commands = []
    tool_set = set(tools)
    if "termux-notification" in tool_set:
        available_commands.append("notify")
    if "termux-location" in tool_set:
        available_commands.append("location")
    if "termux-screenshot" in tool_set:
        available_commands.append("screenshot")
    if "termux-camera-photo" in tool_set:
        available_commands.append("camera")
    if "termux-vibrate" in tool_set:
        available_commands.append("vibrate")
    if "termux-torch" in tool_set:
        available_commands.append("torch")
    if "termux-volume" in tool_set:
        available_commands.append("volume")
    if "termux-sms-send" in tool_set:
        available_commands.append("sms")
    if "termux-tts-speak" in tool_set:
        available_commands.append("tts_speak")

    logger.info(f"[MOBILE] {agent_id}: {len(tools)} herramientas Termux registradas")

    return {
        "registered": len(tools),
        "enriched":   enriched,
        "available_commands": available_commands,
        "catalog_coverage": f"{len([t for t in tools if t in TERMUX_TOOLS_CATALOG])}/{len(TERMUX_TOOLS_CATALOG)} del catálogo",
    }


@router.get("/tools/{agent_id}")
async def get_tools(agent_id: str):
    """Retorna las herramientas Termux registradas para un agente."""
    tools = agent_tools.get(agent_id, [])
    enriched = [{"cmd": t, **TERMUX_TOOLS_CATALOG.get(t, {"cat": "unknown", "desc": t})} for t in tools]
    return {
        "agent_id": agent_id,
        "tools":    enriched,
        "count":    len(tools),
        "by_category": {
            cat: [t for t in enriched if t["cat"] == cat]
            for cat in set(t["cat"] for t in enriched)
        },
    }


@router.get("/tools-catalog")
async def tools_catalog():
    """Catálogo completo de herramientas Termux soportadas por NEXO."""
    by_cat: dict = {}
    for cmd, info in TERMUX_TOOLS_CATALOG.items():
        cat = info["cat"]
        by_cat.setdefault(cat, []).append({"cmd": cmd, "desc": info["desc"]})
    return {"total": len(TERMUX_TOOLS_CATALOG), "by_category": by_cat}


# ─── Comandos rápidos de control remoto (torre → phone) ──────────────────────
# La torre es el dispositivo de confianza — acceso total a todos los dispositivos

QUICK_COMMANDS = {
    "silence": [
        {"type": "volume", "payload": {"stream": "music",        "volume": 0}},
        {"type": "volume", "payload": {"stream": "notification", "volume": 0}},
        {"type": "volume", "payload": {"stream": "ring",         "volume": 0}},
        {"type": "volume", "payload": {"stream": "alarm",        "volume": 0}},
        {"type": "notify", "payload": {"title": "NEXO", "content": "🔇 Silenciado remotamente"}},
    ],
    "unsilence": [
        {"type": "volume", "payload": {"stream": "music",        "volume": 7}},
        {"type": "volume", "payload": {"stream": "notification", "volume": 5}},
        {"type": "volume", "payload": {"stream": "ring",         "volume": 7}},
        {"type": "volume", "payload": {"stream": "alarm",        "volume": 7}},
        {"type": "notify", "payload": {"title": "NEXO", "content": "🔊 Volumen restaurado"}},
    ],
    "find": [
        {"type": "volume",  "payload": {"stream": "ring", "volume": 15}},
        {"type": "vibrate", "payload": {"duration_ms": 1000}},
        {"type": "torch",   "payload": {"on": True}},
        {"type": "notify",  "payload": {"title": "📍 NEXO — Localizando dispositivo",
                                        "content": "Tu torre está buscando este teléfono"}},
        {"type": "tts",     "payload": {"text": "NEXO soberano: localizando dispositivo"}},
    ],
    "locate": [
        {"type": "location", "payload": {}},
        {"type": "notify",   "payload": {"title": "NEXO GPS", "content": "Enviando ubicación a la torre..."}},
    ],
    "camera": [
        {"type": "camera_photo", "payload": {"camera_id": 0}},
        {"type": "notify",       "payload": {"title": "NEXO", "content": "Foto tomada y enviada"}},
    ],
    "screenshot": [
        {"type": "screenshot", "payload": {}},
    ],
    "lock_screen": [
        {"type": "exec",   "payload": {"command": "input keyevent 26 || am start -n com.android.settings/.Settings 2>/dev/null || true"}},
        {"type": "notify", "payload": {"title": "NEXO", "content": "Pantalla bloqueada"}},
    ],
    "torch_on":  [{"type": "torch",   "payload": {"on": True}}],
    "torch_off": [{"type": "torch",   "payload": {"on": False}}],
    "ping":      [{"type": "ping",    "payload": {}}],
    "wakeup": [
        {"type": "vibrate", "payload": {"duration_ms": 500}},
        {"type": "notify",  "payload": {"title": "◎ NEXO", "content": "Wake-up desde torre"}},
        {"type": "tts",     "payload": {"text": "Atención. Mensaje de NEXO soberano."}},
    ],
}


@router.post("/quick/{agent_id}/{action}")
async def quick_command(agent_id: str, action: str,
                        message: str = "",
                        x_api_key: str = Header(None)):
    """
    Comandos rápidos predefinidos desde la torre.
    Actions: silence | unsilence | find | locate | camera | screenshot |
             lock_screen | torch_on | torch_off | ping | wakeup

    La torre es el dispositivo de confianza — acceso total.
    """
    if not _api_key_ok(x_api_key):
        raise HTTPException(status_code=401, detail="API Key inválida")

    cmds = QUICK_COMMANDS.get(action)
    if cmds is None:
        raise HTTPException(
            status_code=400,
            detail=f"Acción desconocida: '{action}'. Disponibles: {list(QUICK_COMMANDS)}",
        )

    now = datetime.now(timezone.utc).isoformat()
    queued = []
    targets = list(mobile_agents.keys()) if agent_id == "*" else [agent_id]

    for target in targets:
        for cmd in cmds:
            c = {**cmd, "id": str(uuid.uuid4())[:8], "ts": now,
                 "source": "tower_trusted"}
            if message and c.get("type") == "notify":
                c["payload"] = {**c["payload"], "content": message or c["payload"].get("content", "")}
            command_queues.setdefault(target, []).append(c)
        queued.append(target)

    logger.info(f"[MOBILE] Quick '{action}' enviado a: {queued}")
    return {
        "ok": True,
        "action": action,
        "queued_commands": len(cmds),
        "targets": queued,
        "note": "Torre de confianza — acceso total",
    }


@router.get("/devices")
async def list_devices():
    """Lista todos los dispositivos registrados con su estado."""
    devices = []
    for aid, info in mobile_agents.items():
        last = info.get("ultimo_contacto", "")
        pending = len(command_queues.get(aid, []))
        tools = agent_tools.get(aid, [])
        devices.append({
            "agent_id":        aid,
            "ultimo_contacto": last,
            "bateria":         info.get("bateria_pct", "?"),
            "wifi":            info.get("wifi_ssid", "?"),
            "cpu":             info.get("cpu_pct", "?"),
            "pending_cmds":    pending,
            "tools_count":     len(tools),
            "online":          True,
        })
    return {
        "devices":      devices,
        "total":        len(devices),
        "trusted_hub":  "torre — dispositivo de confianza principal",
    }
