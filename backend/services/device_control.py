"""
backend/services/device_control.py
Control remoto de dispositivos vía ADB para la IA NEXO.
Prioridad de conexión: Tailscale > WiFi local > USB
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configuración ────────────────────────────────────────────────────────────

ADB_PATH = os.getenv(
    "ADB_PATH",
    r"C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\adb.exe"
)
SCRCPY_PATH = os.getenv(
    "SCRCPY_PATH",
    r"C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v3.3.4\scrcpy.exe"
)

# Endpoints de conexión, en orden de prioridad
DEVICE_ENDPOINTS = [
    ("tailscale", "100.83.26.14:5555"),
    ("tailscale_alt", "100.112.23.72:5555"),
    ("wifi_local", "192.168.100.X:5555"),   # se auto-detecta
]


# ── Servicio ──────────────────────────────────────────────────────────────────

class DeviceControlService:
    """
    Gestiona la conexión ADB y expone comandos de alto nivel.
    La IA NEXO llama a este servicio para controlar el celular.
    """

    def __init__(self):
        self._device: Optional[str] = None   # serial activo (IP:port o USB)
        self._connected = False
        self._scrcpy_proc: Optional[subprocess.Popen] = None
        self._last_check = 0.0
        self._command_queue: list[dict] = []  # cola de comandos push desde la IA

    # ── Conexión ──────────────────────────────────────────────────────────────

    def _adb(self, *args, device: str = None) -> tuple[bool, str]:
        """Ejecuta un comando adb y retorna (éxito, output)."""
        target = device or self._device
        cmd = [ADB_PATH]
        if target:
            cmd += ["-s", target]
        cmd += list(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            out = (result.stdout + result.stderr).strip()
            return result.returncode == 0, out
        except Exception as e:
            return False, str(e)

    def connect(self) -> dict:
        """Intenta conectar en orden: Tailscale → USB."""
        # 1. Tailscale IPs
        for label, endpoint in [
            ("tailscale", "100.83.26.14:5555"),
            ("tailscale_alt", "100.112.23.72:5555"),
        ]:
            ok, out = self._adb("connect", endpoint, device="")
            if ok and "connected" in out.lower():
                self._device = endpoint
                self._connected = True
                logger.info(f"[DEVICE] Conectado via {label}: {endpoint}")
                return {"ok": True, "via": label, "device": endpoint}

        # 2. USB (cualquier dispositivo ya listado)
        ok, out = self._adb("devices", device="")
        lines = [l for l in out.splitlines() if "\tdevice" in l]
        if lines:
            serial = lines[0].split("\t")[0]
            self._device = serial
            self._connected = True
            logger.info(f"[DEVICE] Conectado via USB: {serial}")
            return {"ok": True, "via": "usb", "device": serial}

        self._connected = False
        return {"ok": False, "error": "Sin dispositivo disponible"}

    def ensure_connected(self) -> bool:
        """Reconecta si es necesario (max cada 30s)."""
        if self._connected and time.time() - self._last_check < 30:
            return True
        self._last_check = time.time()
        ok, out = self._adb("get-state")
        if ok and "device" in out:
            self._connected = True
            return True
        result = self.connect()
        return result["ok"]

    def status(self) -> dict:
        connected = self.ensure_connected()
        info = {}
        if connected:
            _, battery = self._adb("shell", "dumpsys battery | grep level")
            _, model = self._adb("shell", "getprop ro.product.model")
            _, screen = self._adb("shell", "dumpsys power | grep 'mWakefulness='")
            info = {
                "model": model.strip(),
                "battery": battery.strip(),
                "screen": screen.strip(),
            }
        return {
            "connected": connected,
            "device": self._device,
            "scrcpy_running": self._scrcpy_proc is not None and self._scrcpy_proc.poll() is None,
            **info,
        }

    # ── Pantalla ──────────────────────────────────────────────────────────────

    def screenshot(self) -> Optional[str]:
        """Toma captura de pantalla y retorna base64."""
        if not self.ensure_connected():
            return None
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        ok, _ = self._adb("exec-out", "screencap -p", device=self._device)
        # Método alternativo con pull
        self._adb("shell", "screencap -p /sdcard/nexo_screenshot.png")
        ok, _ = self._adb("pull", "/sdcard/nexo_screenshot.png", tmp)
        if ok and Path(tmp).exists():
            data = base64.b64encode(Path(tmp).read_bytes()).decode()
            Path(tmp).unlink(missing_ok=True)
            self._adb("shell", "rm /sdcard/nexo_screenshot.png")
            return data
        return None

    def tap(self, x: int, y: int) -> bool:
        ok, _ = self._adb("shell", f"input tap {x} {y}")
        return ok

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        ok, _ = self._adb("shell", f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        return ok

    def key_event(self, keycode: int | str) -> bool:
        ok, _ = self._adb("shell", f"input keyevent {keycode}")
        return ok

    def type_text(self, text: str) -> bool:
        safe = text.replace(" ", "%s").replace("'", "\\'")
        ok, _ = self._adb("shell", f"input text '{safe}'")
        return ok

    def wake_screen(self) -> bool:
        return self.key_event(224)  # KEYCODE_WAKEUP

    def lock_screen(self) -> bool:
        return self.key_event(223)  # KEYCODE_SLEEP

    def home(self) -> bool:
        return self.key_event(3)  # KEYCODE_HOME

    def back(self) -> bool:
        return self.key_event(4)  # KEYCODE_BACK

    # ── Apps ──────────────────────────────────────────────────────────────────

    def launch_app(self, package: str) -> bool:
        ok, _ = self._adb("shell", f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
        return ok

    def launch_url(self, url: str) -> bool:
        ok, _ = self._adb("shell", f"am start -a android.intent.action.VIEW -d '{url}'")
        return ok

    def installed_apps(self) -> list[str]:
        ok, out = self._adb("shell", "pm list packages -3")
        if not ok:
            return []
        return [l.replace("package:", "").strip() for l in out.splitlines() if l.startswith("package:")]

    # ── Shell ────────────────────────────────────────────────────────────────

    def shell(self, command: str) -> tuple[bool, str]:
        return self._adb("shell", command)

    def get_clipboard(self) -> str:
        ok, out = self._adb("shell", "am broadcast -a clipper.get")
        return out if ok else ""

    def set_clipboard(self, text: str) -> bool:
        ok, _ = self._adb("shell", f"am broadcast -a clipper.set -e text '{text}'")
        return ok

    # ── scrcpy ────────────────────────────────────────────────────────────────

    def start_scrcpy(self, wireless: bool = True) -> dict:
        """Lanza scrcpy apuntando al dispositivo activo."""
        if self._scrcpy_proc and self._scrcpy_proc.poll() is None:
            return {"ok": True, "msg": "scrcpy ya está corriendo"}

        cmd = [SCRCPY_PATH, "--window-title", "NEXO Control", "--stay-awake"]
        if wireless and self._device and ":" in self._device:
            cmd += ["--serial", self._device]

        try:
            self._scrcpy_proc = subprocess.Popen(cmd)
            return {"ok": True, "msg": "scrcpy iniciado", "device": self._device}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop_scrcpy(self) -> bool:
        if self._scrcpy_proc:
            self._scrcpy_proc.terminate()
            self._scrcpy_proc = None
            return True
        return False

    # ── Cola de comandos (push desde IA) ─────────────────────────────────────

    def push_command(self, command: dict) -> str:
        """La IA empuja un comando a la cola."""
        import uuid
        command["id"] = str(uuid.uuid4())[:8]
        command["ts"] = time.time()
        self._command_queue.append(command)
        logger.info(f"[DEVICE] Comando encolado: {command}")
        return command["id"]

    def pop_commands(self) -> list[dict]:
        """El agente móvil consume la cola."""
        cmds = list(self._command_queue)
        self._command_queue.clear()
        return cmds

    # ── Ejecución de comando IA de alto nivel ─────────────────────────────────

    def execute_ai_command(self, action: str, params: dict = None) -> dict:
        """
        Punto de entrada único para que la IA ejecute acciones en el dispositivo.

        Acciones disponibles:
          screenshot, tap, swipe, key, type, wake, lock, home, back,
          launch_app, launch_url, shell, installed_apps, status, scrcpy_start, scrcpy_stop
        """
        if not self.ensure_connected():
            return {"ok": False, "error": "Dispositivo no conectado"}

        p = params or {}

        if action == "screenshot":
            data = self.screenshot()
            return {"ok": bool(data), "image_base64": data}

        elif action == "tap":
            return {"ok": self.tap(p["x"], p["y"])}

        elif action == "swipe":
            return {"ok": self.swipe(p["x1"], p["y1"], p["x2"], p["y2"], p.get("duration_ms", 300))}

        elif action == "key":
            return {"ok": self.key_event(p["keycode"])}

        elif action == "type":
            return {"ok": self.type_text(p["text"])}

        elif action == "wake":
            return {"ok": self.wake_screen()}

        elif action == "lock":
            return {"ok": self.lock_screen()}

        elif action == "home":
            return {"ok": self.home()}

        elif action == "back":
            return {"ok": self.back()}

        elif action == "launch_app":
            return {"ok": self.launch_app(p["package"])}

        elif action == "launch_url":
            return {"ok": self.launch_url(p["url"])}

        elif action == "shell":
            ok, out = self.shell(p["command"])
            return {"ok": ok, "output": out}

        elif action == "installed_apps":
            return {"ok": True, "apps": self.installed_apps()}

        elif action == "status":
            return {"ok": True, **self.status()}

        elif action == "scrcpy_start":
            return self.start_scrcpy()

        elif action == "scrcpy_stop":
            return {"ok": self.stop_scrcpy()}

        else:
            return {"ok": False, "error": f"Acción desconocida: {action}"}


# Singleton global
device_control = DeviceControlService()

# Auto-conectar al importar
try:
    result = device_control.connect()
    if result["ok"]:
        logger.info(f"[DEVICE] Auto-conexión exitosa: {result}")
    else:
        logger.warning(f"[DEVICE] Auto-conexión falló: {result}")
except Exception as e:
    logger.warning(f"[DEVICE] Error en auto-conexión: {e}")
