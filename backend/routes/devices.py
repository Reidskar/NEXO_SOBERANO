"""
backend/routes/devices.py
Control unificado de los 3 dispositivos del sistema NEXO:
  - Torre (servidor central)
  - Xiaomi (celu — Termux agent)
  - Dell Latitude (notebook — notebook agent)

Endpoints:
  GET  /api/devices/status           — estado online de los 3 dispositivos
  POST /api/devices/ai-comando       — lenguaje natural → IA decide device + acción
  POST /api/devices/comando/{device} — enviar comando directo a un dispositivo
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.routes.mobile import mobile_agents, _command_queues, ALLOWED_COMMANDS
from collections import deque

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/devices", tags=["devices"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")

# Mapeo canónico de alias a agent_id
DEVICE_ALIASES = {
    "celu":    "xiaomi-14t-pro-1",
    "xiaomi":  "xiaomi-14t-pro-1",
    "celular": "xiaomi-14t-pro-1",
    "movil":   "xiaomi-14t-pro-1",
    "note":    "dell-latitude-1",
    "notebook": "dell-latitude-1",
    "dell":    "dell-latitude-1",
    "laptop":  "dell-latitude-1",
    "torre":   "torre",
    "pc":      "torre",
    "server":  "torre",
}

# Comandos por tipo de dispositivo para el AI router
DEVICE_COMMANDS = {
    "xiaomi-14t-pro-1": ["silenciar", "volumen_max", "pantalla_off", "vibrar",
                          "ubicacion", "foto_frontal", "toast", "reiniciar_tailscale", "ping"],
    "dell-latitude-1":  ["screenshot", "lock_pantalla", "abrir_app",
                          "notificacion_win", "ejecutar_cmd", "volumen_notebook", "ping"],
    "torre":            ["ping", "ejecutar_cmd"],
}

# ── Modelos ───────────────────────────────────────────────────────────────────

class AIComandoRequest(BaseModel):
    query: str
    device: Optional[str] = None  # "celu", "note", "torre", "auto" (default)


class ComandoDirectoRequest(BaseModel):
    accion: str
    params: Optional[dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_online(agent_id: str, threshold_secs: int = 60) -> bool:
    if agent_id == "torre":
        return True  # La torre siempre está online (es el servidor)
    agente = mobile_agents.get(agent_id)
    if not agente:
        return False
    ultimo = agente.get("ultimo_contacto", "")
    if not ultimo:
        return False
    try:
        diff = (datetime.now(timezone.utc) - datetime.fromisoformat(ultimo)).total_seconds()
        return diff < threshold_secs
    except Exception:
        return False


def _encolar(agent_id: str, accion: str, params: dict) -> dict:
    if agent_id not in _command_queues:
        _command_queues[agent_id] = deque()
    cmd = {
        "id": f"cmd_{int(datetime.now().timestamp() * 1000)}",
        "accion": accion,
        "params": params,
        "encolado_en": datetime.now(timezone.utc).isoformat(),
    }
    _command_queues[agent_id].append(cmd)
    return cmd


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def devices_status():
    """
    Estado unificado de los 3 dispositivos.
    """
    devices = {}

    # Torre (servidor)
    devices["torre"] = {
        "agent_id": "torre",
        "tipo": "servidor",
        "nombre": "PC Torre",
        "online": True,
        "ip_local": "192.168.100.22",
        "rol": "servidor_central",
        "ultimo_contacto": datetime.now(timezone.utc).isoformat(),
    }

    # Xiaomi
    xiaomi_data = mobile_agents.get("xiaomi-14t-pro-1", {})
    devices["xiaomi"] = {
        "agent_id": "xiaomi-14t-pro-1",
        "tipo": "mobile",
        "nombre": "Xiaomi 14T Pro",
        "online": _is_online("xiaomi-14t-pro-1"),
        "bateria_pct": xiaomi_data.get("bateria_pct", -1),
        "bateria_estado": xiaomi_data.get("bateria_estado", "unknown"),
        "cpu_pct": xiaomi_data.get("cpu_pct", -1),
        "ram_pct": xiaomi_data.get("ram_pct", -1),
        "wifi_ssid": xiaomi_data.get("wifi_ssid", "unknown"),
        "ultimo_contacto": xiaomi_data.get("ultimo_contacto", None),
        "comandos_pendientes": len(_command_queues.get("xiaomi-14t-pro-1", deque())),
    }

    # Dell Notebook
    dell_data = mobile_agents.get("dell-latitude-1", {})
    devices["dell"] = {
        "agent_id": "dell-latitude-1",
        "tipo": "notebook",
        "nombre": "Dell Latitude",
        "online": _is_online("dell-latitude-1"),
        "bateria_pct": dell_data.get("bateria_pct", -1),
        "bateria_estado": dell_data.get("bateria_estado", "unknown"),
        "cpu_pct": dell_data.get("cpu_pct", -1),
        "ram_pct": dell_data.get("ram_pct", -1),
        "disco_libre_gb": dell_data.get("disco_libre_gb", -1),
        "ultimo_contacto": dell_data.get("ultimo_contacto", None),
        "comandos_pendientes": len(_command_queues.get("dell-latitude-1", deque())),
    }

    online_count = sum(1 for d in devices.values() if d["online"])
    return {
        "ok": True,
        "devices": devices,
        "resumen": {
            "total": 3,
            "online": online_count,
            "offline": 3 - online_count,
        },
    }


@router.post("/ai-comando")
async def ai_comando(req: AIComandoRequest):
    """
    Acepta lenguaje natural. La IA decide qué dispositivo y qué acción ejecutar.
    Ejemplos:
      "silencia el celu"       → xiaomi / silenciar
      "toma screenshot del note" → dell / screenshot
      "vibra el teléfono"      → xiaomi / vibrar
      "bloquea el notebook"    → dell / lock_pantalla
    """
    query   = req.query.lower()
    device  = req.device

    # Resolver alias de dispositivo si el usuario lo especificó
    if device and device in DEVICE_ALIASES:
        agent_id = DEVICE_ALIASES[device]
    else:
        agent_id = None

    # Intentar routing por IA (Gemini/Claude vía NEXO_CORE)
    ai_decision = None
    try:
        from NEXO_CORE.services.multi_ai_service import multi_ai_service

        estado_dispositivos = {
            "xiaomi_online": _is_online("xiaomi-14t-pro-1"),
            "dell_online": _is_online("dell-latitude-1"),
        }
        system_prompt = (
            "Eres el router de comandos de dispositivos de Nexo Soberano. "
            "Dado un comando en lenguaje natural, responde SOLO con JSON en este formato:\n"
            '{"device": "xiaomi-14t-pro-1" | "dell-latitude-1" | "torre", '
            '"accion": "<accion>", "params": {}, "razon": "<breve explicacion>"}\n\n'
            f"Dispositivos disponibles: {estado_dispositivos}\n"
            f"Comandos Xiaomi: {DEVICE_COMMANDS['xiaomi-14t-pro-1']}\n"
            f"Comandos Dell: {DEVICE_COMMANDS['dell-latitude-1']}\n"
        )

        import json
        response_text = await multi_ai_service.generate(
            prompt=f"Comando: {req.query}",
            system=system_prompt,
            max_tokens=200,
        )
        # Extraer JSON de la respuesta
        start = response_text.find("{")
        end   = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            ai_decision = json.loads(response_text[start:end])
            if not agent_id:
                agent_id = ai_decision.get("device")
    except Exception as e:
        logger.warning(f"[AI ROUTER] IA no disponible, usando heurísticas: {e}")

    # Fallback heurístico si la IA falla
    if not ai_decision:
        ai_decision = _heuristic_route(query)
        if not agent_id:
            agent_id = ai_decision.get("device")

    accion = ai_decision.get("accion", "ping")
    params = ai_decision.get("params", {})
    razon  = ai_decision.get("razon", "heurística")

    if not agent_id:
        raise HTTPException(400, "No se pudo determinar el dispositivo destino")

    if accion not in ALLOWED_COMMANDS:
        raise HTTPException(400, f"Acción no permitida: {accion}")

    cmd = _encolar(agent_id, accion, params)
    online = _is_online(agent_id)

    return {
        "ok": True,
        "query": req.query,
        "device": agent_id,
        "accion": accion,
        "params": params,
        "razon": razon,
        "cmd_id": cmd["id"],
        "device_online": online,
        "mensaje": (
            f"Comando '{accion}' encolado para {agent_id} — "
            f"{'se ejecutará en segundos' if online else 'se ejecutará cuando el dispositivo se conecte'}"
        ),
    }


@router.post("/comando/{device}")
async def comando_directo(device: str, body: ComandoDirectoRequest):
    """
    Envía un comando directo a un dispositivo por alias.
    device: "celu" | "xiaomi" | "note" | "dell" | "torre"
    """
    agent_id = DEVICE_ALIASES.get(device.lower())
    if not agent_id:
        raise HTTPException(400, f"Dispositivo desconocido: {device}. Válidos: {list(DEVICE_ALIASES.keys())}")

    if body.accion not in ALLOWED_COMMANDS:
        raise HTTPException(400, f"Acción no permitida: {body.accion}")

    cmd = _encolar(agent_id, body.accion, body.params or {})
    return {
        "ok": True,
        "device": agent_id,
        "accion": body.accion,
        "cmd_id": cmd["id"],
        "device_online": _is_online(agent_id),
    }


# ── Heurísticas de routing ────────────────────────────────────────────────────

def _heuristic_route(query: str) -> dict:
    """Routing de emergencia si la IA no está disponible."""
    q = query.lower()

    # Palabras clave de dispositivo
    if any(w in q for w in ["celu", "cel", "xiaomi", "móvil", "movil", "teléfono", "telefono", "phone"]):
        device = "xiaomi-14t-pro-1"
    elif any(w in q for w in ["note", "notebook", "dell", "laptop", "portatil", "portátil"]):
        device = "dell-latitude-1"
    else:
        device = "xiaomi-14t-pro-1"  # default al celu

    # Acción
    if any(w in q for w in ["silenci", "mute", "callado", "silencio"]):
        return {"device": device, "accion": "silenciar", "params": {}, "razon": "heurística: silenciar"}
    if any(w in q for w in ["pantalla", "apagar pantalla", "screen off"]):
        return {"device": device, "accion": "pantalla_off", "params": {}, "razon": "heurística: pantalla"}
    if any(w in q for w in ["screenshot", "captura", "foto pantalla", "screen"]):
        return {"device": "dell-latitude-1", "accion": "screenshot", "params": {}, "razon": "heurística: screenshot → notebook"}
    if any(w in q for w in ["vibra", "vibrar", "vibración"]):
        return {"device": "xiaomi-14t-pro-1", "accion": "vibrar", "params": {"ms": 500}, "razon": "heurística: vibrar → celu"}
    if any(w in q for w in ["bloquea", "lock", "bloquear"]):
        return {"device": device, "accion": "lock_pantalla", "params": {}, "razon": "heurística: lock"}
    if any(w in q for w in ["ubicacion", "ubicación", "donde", "localiza"]):
        return {"device": "xiaomi-14t-pro-1", "accion": "ubicacion", "params": {}, "razon": "heurística: ubicación → celu"}
    if any(w in q for w in ["foto", "camara", "cámara", "selfie"]):
        return {"device": "xiaomi-14t-pro-1", "accion": "foto_frontal", "params": {}, "razon": "heurística: foto → celu"}

    # Fallback: ping
    return {"device": device, "accion": "ping", "params": {}, "razon": "heurística: sin match → ping"}
