"""
backend/routes/device.py
Endpoints REST para control remoto de dispositivo.
La IA NEXO y el agente móvil usan estas rutas.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import os

from backend.services.device_control import device_control

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/device", tags=["device"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")


def _auth(key: str = None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


# ── Modelos ──────────────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    action: str
    params: Optional[dict] = {}


class CommandPush(BaseModel):
    command: dict


# ── Rutas ────────────────────────────────────────────────────────────────────

@router.get("/status")
def device_status(x_api_key: str = Header(None)):
    """Estado del dispositivo y conexión ADB."""
    _auth(x_api_key)
    return device_control.status()


@router.post("/connect")
def device_connect(x_api_key: str = Header(None)):
    """Fuerza reconexión ADB (Tailscale primero, luego USB)."""
    _auth(x_api_key)
    return device_control.connect()


@router.post("/action")
def device_action(body: ActionRequest, x_api_key: str = Header(None)):
    """
    Ejecuta una acción en el dispositivo.

    Acciones disponibles:
    - screenshot               → retorna image_base64
    - tap        {x, y}
    - swipe      {x1, y1, x2, y2, duration_ms?}
    - key        {keycode}      → ej: 3=HOME, 4=BACK, 224=WAKE
    - type       {text}
    - wake / lock / home / back
    - launch_app {package}      → ej: com.whatsapp
    - launch_url {url}
    - shell      {command}
    - installed_apps
    - scrcpy_start / scrcpy_stop
    """
    _auth(x_api_key)
    return device_control.execute_ai_command(body.action, body.params)


@router.post("/screenshot")
def device_screenshot(x_api_key: str = Header(None)):
    """Captura de pantalla (imagen base64 PNG)."""
    _auth(x_api_key)
    data = device_control.screenshot()
    if not data:
        raise HTTPException(status_code=503, detail="No se pudo capturar pantalla")
    return {"ok": True, "image_base64": data, "format": "png"}


@router.post("/scrcpy/start")
def scrcpy_start(x_api_key: str = Header(None)):
    """Lanza scrcpy apuntando al dispositivo activo (wireless o USB)."""
    _auth(x_api_key)
    return device_control.start_scrcpy()


@router.post("/scrcpy/stop")
def scrcpy_stop(x_api_key: str = Header(None)):
    """Cierra scrcpy."""
    _auth(x_api_key)
    return {"ok": device_control.stop_scrcpy()}


# ── Cola de comandos push (IA → Celular) ──────────────────────────────────────

@router.post("/queue/push")
def queue_push(body: CommandPush, x_api_key: str = Header(None)):
    """La IA empuja un comando a la cola del agente móvil."""
    _auth(x_api_key)
    cmd_id = device_control.push_command(body.command)
    return {"ok": True, "command_id": cmd_id}


@router.get("/queue/pop")
def queue_pop(x_api_key: str = Header(None)):
    """El agente móvil consume la cola de comandos pendientes."""
    _auth(x_api_key)
    return {"commands": device_control.pop_commands()}


# ── Shortcuts para la IA ──────────────────────────────────────────────────────

@router.post("/open")
def open_url(url: str, x_api_key: str = Header(None)):
    """Abre una URL en el celular (cualquier navegador/app)."""
    _auth(x_api_key)
    return {"ok": device_control.launch_url(url)}


@router.post("/shell")
def run_shell(command: str, x_api_key: str = Header(None)):
    """Ejecuta un comando shell en el dispositivo."""
    _auth(x_api_key)
    ok, out = device_control.shell(command)
    return {"ok": ok, "output": out}
