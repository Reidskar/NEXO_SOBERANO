#!/usr/bin/env python3
"""
NEXO SOBERANO — Notebook Agent v1.0
Corre en el Dell Latitude (Windows/Linux). Se conecta al backend central,
reporta métricas y ejecuta comandos remotos enviados por la IA o el bot.

Instalación (Windows):
    pip install requests psutil pillow

Inicio:
    python nexo_notebook_agent.py

Inicio en background (Windows):
    pythonw nexo_notebook_agent.py
"""
import os
import sys
import time
import json
import logging
import platform
import subprocess
from datetime import datetime, timezone

import requests
import psutil

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("nexo_notebook.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("NEXO_NOTEBOOK")

# ── Configuración ──────────────────────────────────────────────────────────────
BACKENDS = [
    os.getenv("NEXO_BACKEND_LAN",       "http://192.168.100.22:8080"),
    os.getenv("NEXO_BACKEND_TAILSCALE", "http://100.104.152.43:8080"),
    os.getenv("NEXO_BACKEND_RAILWAY",   ""),
]

def get_backend_activo() -> str:
    for url in BACKENDS:
        if not url:
            continue
        try:
            r = requests.get(f"{url}/health", timeout=3)
            if r.status_code == 200:
                logger.info(f"Backend activo: {url}")
                return url
        except Exception:
            continue
    logger.warning("Ningún backend alcanzable, usando primero por defecto")
    return BACKENDS[0]

BACKEND_URL   = get_backend_activo()
AGENT_ID      = os.getenv("NEXO_AGENT_ID", "dell-latitude-1")
POLL_INTERVAL = int(os.getenv("NEXO_POLL", "15"))
API_KEY       = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")

# ── Métricas del dispositivo ───────────────────────────────────────────────────
def get_device_metrics() -> dict:
    metrics = {
        "agent_id":  AGENT_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tipo":      "notebook",
        "os":        platform.system(),
        "hostname":  platform.node(),
    }
    try:
        metrics["cpu_pct"]     = psutil.cpu_percent(interval=1)
        mem                    = psutil.virtual_memory()
        metrics["ram_total_mb"] = round(mem.total / 1e6, 1)
        metrics["ram_usado_mb"] = round(mem.used  / 1e6, 1)
        metrics["ram_pct"]     = mem.percent
    except Exception as e:
        metrics["psutil_error"] = str(e)

    try:
        bat = psutil.sensors_battery()
        if bat:
            metrics["bateria_pct"]    = round(bat.percent, 1)
            metrics["bateria_estado"] = "charging" if bat.power_plugged else "discharging"
            metrics["cargando"]       = bat.power_plugged
    except Exception:
        metrics["bateria_pct"] = -1

    try:
        disk = psutil.disk_usage("/")
        metrics["disco_libre_gb"] = round(disk.free / 1e9, 1)
        metrics["disco_total_gb"] = round(disk.total / 1e9, 1)
    except Exception:
        pass

    return metrics


# ── Ejecutar comandos remotos ──────────────────────────────────────────────────
def ejecutar_comando(cmd: dict):
    accion = cmd.get("accion", "")
    params = cmd.get("params", {})
    logger.info(f"[CMD] Ejecutando: {accion} | params={params}")

    try:
        # ── Ping ──────────────────────────────────────────────────────────────
        if accion == "ping":
            _reportar_resultado(cmd["id"], "pong", {
                "agente": AGENT_ID,
                "ts": datetime.now(timezone.utc).isoformat(),
                "os": platform.system(),
            })

        # ── Screenshot ────────────────────────────────────────────────────────
        elif accion == "screenshot":
            try:
                from PIL import ImageGrab
                import base64, io
                img  = ImageGrab.grab()
                buf  = io.BytesIO()
                img.save(buf, format="PNG")
                b64  = base64.b64encode(buf.getvalue()).decode()
                path = f"nexo_screenshot_{int(time.time())}.png"
                img.save(path)
                _reportar_resultado(cmd["id"], "screenshot", {"path": path, "image_base64": b64})
                logger.info(f"[CMD] Screenshot guardado: {path}")
            except ImportError:
                logger.warning("[CMD] Pillow no instalado — pip install pillow")
                _reportar_resultado(cmd["id"], "error", {"msg": "pillow no instalado"})

        # ── Lock pantalla ─────────────────────────────────────────────────────
        elif accion == "lock_pantalla":
            if IS_WINDOWS:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            elif IS_LINUX:
                subprocess.run(["loginctl", "lock-session"], timeout=5)
            logger.info("[CMD] Pantalla bloqueada")

        # ── Abrir app ─────────────────────────────────────────────────────────
        elif accion == "abrir_app":
            app = params.get("app", "")
            if not app:
                logger.warning("[CMD] abrir_app requiere params.app")
                return
            if IS_WINDOWS:
                subprocess.Popen(["start", app], shell=True)
            else:
                subprocess.Popen([app])
            logger.info(f"[CMD] App lanzada: {app}")

        # ── Notificación Windows ──────────────────────────────────────────────
        elif accion == "notificacion_win":
            msg = params.get("mensaje", "NEXO")
            titulo = params.get("titulo", "Nexo Soberano")
            if IS_WINDOWS:
                # Win10/11 toast via PowerShell (sin deps extra)
                ps_cmd = (
                    f"[Windows.UI.Notifications.ToastNotificationManager, "
                    f"Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null; "
                    f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                    f"[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                    f"$template.SelectSingleNode('//text[@id=1]').InnerText = '{titulo}'; "
                    f"$template.SelectSingleNode('//text[@id=2]').InnerText = '{msg}'; "
                    f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                    f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('NEXO').Show($toast)"
                )
                subprocess.run(["powershell", "-Command", ps_cmd], timeout=10, capture_output=True)
            else:
                # Linux — libnotify
                subprocess.run(["notify-send", titulo, msg], timeout=5)
            logger.info(f"[CMD] Notificación enviada: {titulo} — {msg}")

        # ── Volumen ───────────────────────────────────────────────────────────
        elif accion == "volumen_notebook":
            nivel = int(params.get("nivel", 50))  # 0-100
            if IS_WINDOWS:
                # PowerShell para volumen
                subprocess.run(
                    ["powershell", "-Command",
                     f"(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                    timeout=5
                )
            elif IS_LINUX:
                subprocess.run(["amixer", "-q", "sset", "Master", f"{nivel}%"], timeout=5)
            logger.info(f"[CMD] Volumen ajustado a {nivel}%")

        # ── Ejecutar comando shell (RESTRINGIDO) ──────────────────────────────
        elif accion == "ejecutar_cmd":
            # Solo comandos pre-aprobados para seguridad
            cmd_str = params.get("cmd", "")
            ALLOWED_CMDS_PREFIX = ("ipconfig", "hostname", "echo", "dir", "ls", "pwd",
                                   "python --version", "pip list")
            if not any(cmd_str.startswith(p) for p in ALLOWED_CMDS_PREFIX):
                logger.warning(f"[CMD] ejecutar_cmd rechazado (no en lista blanca): {cmd_str}")
                _reportar_resultado(cmd["id"], "error", {"msg": "comando no permitido"})
                return
            result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=30)
            _reportar_resultado(cmd["id"], "cmd_result", {
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            })

        else:
            logger.warning(f"[CMD] Acción desconocida: {accion}")

    except Exception as e:
        logger.error(f"[CMD] Error ejecutando '{accion}': {e}")


def _reportar_resultado(cmd_id: str, tipo: str, data: dict):
    try:
        requests.post(
            f"{BACKEND_URL}/api/mobile/resultado",
            json={"cmd_id": cmd_id, "tipo": tipo, "data": data, "agent_id": AGENT_ID},
            headers={"x-api-key": API_KEY},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"[CMD] No se pudo reportar resultado de {cmd_id}: {e}")


# ── Heartbeat ──────────────────────────────────────────────────────────────────
def reportar_y_recibir_comandos(metrics: dict) -> list:
    try:
        headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
        resp = requests.post(
            f"{BACKEND_URL}/api/mobile/heartbeat",
            json=metrics,
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            cpu  = metrics.get("cpu_pct", "?")
            ram  = metrics.get("ram_pct", "?")
            bat  = metrics.get("bateria_pct", "?")
            cmds = data.get("comandos", [])
            logger.info(f"Heartbeat OK — CPU:{cpu}% RAM:{ram}% BAT:{bat}% | cmds={len(cmds)}")
            return cmds
        else:
            logger.warning(f"Heartbeat rechazado: {resp.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        logger.error(f"Sin conexión a {BACKEND_URL}")
        global BACKEND_URL
        BACKEND_URL = get_backend_activo()
        return []
    except Exception as e:
        logger.error(f"Error en heartbeat: {e}")
        return []


# ── Loop principal ─────────────────────────────────────────────────────────────
def loop_principal():
    logger.info(f"[NEXO NOTEBOOK v1.0] Iniciado — Backend: {BACKEND_URL}")
    logger.info(f"Agent ID: {AGENT_ID} | OS: {platform.system()} | Poll: {POLL_INTERVAL}s")

    errores = 0
    while True:
        try:
            metrics   = get_device_metrics()
            comandos  = reportar_y_recibir_comandos(metrics)
            for cmd in comandos:
                ejecutar_comando(cmd)
            errores = 0
        except Exception as e:
            errores += 1
            logger.error(f"Error en loop: {e}")
            if errores >= 10:
                logger.critical("10 errores consecutivos — esperando 60s")
                time.sleep(60)
                errores = 0
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    loop_principal()
