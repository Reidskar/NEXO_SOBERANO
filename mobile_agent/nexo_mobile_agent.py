#!/usr/bin/env python3
"""
NEXO SOBERANO — Mobile Agent v0.6
Corre en Termux (Xiaomi). Se conecta al backend central, reporta métricas
y ejecuta comandos remotos enviados desde el bot de Discord o la torre.
"""
import os
import time
import json
import logging
import threading
import subprocess
from datetime import datetime, timezone

import requests
import psutil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/sdcard/nexo_mobile.log")
    ]
)
logger = logging.getLogger("NEXO_MOBILE")

# ── Configuración ──────────────────────────────────────────────────────────────
BACKENDS = [
    os.getenv("NEXO_BACKEND_LAN",       "http://192.168.100.22:8080"),
    os.getenv("NEXO_BACKEND_TAILSCALE", "http://100.112.238.97:8080"),  # Torre Tailscale
    os.getenv("NEXO_BACKEND_RAILWAY",   ""),
]

def get_backend_activo() -> str:
    for url in BACKENDS:
        if not url:
            continue
        try:
            r = requests.get(f"{url}/health", timeout=3)
            if r.status_code == 200:
                logger.info(f"[NEXO MOBILE] Backend activo: {url}")
                return url
        except Exception:
            continue
    logger.warning("[NEXO MOBILE] Ningún backend alcanzable, usando primero por defecto")
    return BACKENDS[0]

BACKEND_URL   = get_backend_activo()
AGENT_ID      = os.getenv("NEXO_AGENT_ID", "xiaomi-14t-pro-1")
POLL_INTERVAL = int(os.getenv("NEXO_POLL", "15"))  # segundos entre heartbeats
API_KEY       = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")

# ── Métricas del dispositivo ───────────────────────────────────────────────────
def get_device_metrics() -> dict:
    metrics = {
        "agent_id": AGENT_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tipo": "mobile",
    }
    try:
        metrics["cpu_pct"] = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        metrics["ram_total_mb"] = round(mem.total / 1e6, 1)
        metrics["ram_usado_mb"] = round(mem.used / 1e6, 1)
        metrics["ram_pct"] = mem.percent
    except Exception as e:
        metrics["psutil_error"] = str(e)

    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            bat = json.loads(r.stdout)
            metrics["bateria_pct"]    = bat.get("percentage", -1)
            metrics["bateria_estado"] = bat.get("status", "unknown")
            metrics["cargando"]       = bat.get("plugged", False)
    except Exception:
        metrics["bateria_pct"] = -1

    try:
        r = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            wifi = json.loads(r.stdout)
            metrics["wifi_ssid"] = wifi.get("ssid", "unknown")
            metrics["wifi_rssi"] = wifi.get("rssi", 0)
    except Exception:
        metrics["wifi_ssid"] = "unknown"

    return metrics

# ── Ejecutar comandos remotos ──────────────────────────────────────────────────
def ejecutar_comando(cmd: dict):
    accion = cmd.get("accion", "")
    params = cmd.get("params", {})
    logger.info(f"[CMD] Ejecutando: {accion} | params={params}")

    try:
        if accion == "silenciar":
            subprocess.run(["termux-volume", "media", "0"], timeout=5)
            subprocess.run(["termux-volume", "ring", "0"], timeout=5)
            subprocess.run(["termux-volume", "notification", "0"], timeout=5)
            subprocess.run(["termux-toast", "NEXO: Volumen silenciado"], timeout=5)
            logger.info("[CMD] Dispositivo silenciado")

        elif accion == "volumen_max":
            subprocess.run(["termux-volume", "media", "15"], timeout=5)
            subprocess.run(["termux-toast", "NEXO: Volumen al máximo"], timeout=5)

        elif accion == "pantalla_off":
            subprocess.run(["termux-screen-off"], timeout=5)
            logger.info("[CMD] Pantalla apagada")

        elif accion == "vibrar":
            ms = str(params.get("ms", 500))
            subprocess.run(["termux-vibrate", "-d", ms], timeout=5)

        elif accion == "ubicacion":
            r = subprocess.run(["termux-location", "-p", "network"], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                loc = json.loads(r.stdout)
                _reportar_resultado(cmd["id"], "ubicacion", loc)

        elif accion == "foto_frontal":
            path = f"/sdcard/nexo_foto_{int(time.time())}.jpg"
            subprocess.run(["termux-camera-photo", "-c", "1", path], timeout=15)
            logger.info(f"[CMD] Foto guardada en {path}")
            _reportar_resultado(cmd["id"], "foto", {"path": path})

        elif accion == "toast":
            msg = params.get("mensaje", "NEXO")
            subprocess.run(["termux-toast", msg], timeout=5)

        elif accion == "reiniciar_tailscale":
            subprocess.run(["pkill", "-f", "tailscale"], timeout=5)
            time.sleep(2)
            subprocess.Popen(["tailscale", "up"])
            logger.info("[CMD] Tailscale reiniciando...")

        elif accion == "ping":
            _reportar_resultado(cmd["id"], "pong", {"agente": AGENT_ID, "ts": datetime.now(timezone.utc).isoformat()})

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
            timeout=10
        )
    except Exception as e:
        logger.warning(f"[CMD] No se pudo reportar resultado de {cmd_id}: {e}")

# ── Heartbeat con recepción de comandos ───────────────────────────────────────
def reportar_y_recibir_comandos(metrics: dict) -> list:
    global BACKEND_URL
    try:
        headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
        resp = requests.post(
            f"{BACKEND_URL}/api/mobile/heartbeat",
            json=metrics,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            bat  = metrics.get("bateria_pct", "?")
            cpu  = metrics.get("cpu_pct", "?")
            ram  = metrics.get("ram_pct", "?")
            cmds = data.get("comandos", [])
            logger.info(f"Heartbeat OK — CPU:{cpu}% RAM:{ram}% BAT:{bat}% | comandos_pendientes={len(cmds)}")
            return cmds
        else:
            logger.warning(f"Heartbeat rechazado: {resp.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        logger.error(f"Sin conexión a {BACKEND_URL}")
        # Intentar reconectar con otro backend
        BACKEND_URL = get_backend_activo()
        return []
    except Exception as e:
        logger.error(f"Error en heartbeat: {e}")
        return []

# ── Loop principal ─────────────────────────────────────────────────────────────
def loop_principal():
    logger.info(f"[NEXO MOBILE v0.6] Iniciado — Backend: {BACKEND_URL}")
    logger.info(f"Agent ID: {AGENT_ID} | Poll: {POLL_INTERVAL}s")

    errores = 0
    while True:
        try:
            metrics = get_device_metrics()
            comandos = reportar_y_recibir_comandos(metrics)

            for cmd in comandos:
                ejecutar_comando(cmd)

            errores = 0
        except Exception as e:
            errores += 1
            logger.error(f"Error en loop principal: {e}")
            if errores >= 10:
                logger.critical("10 errores consecutivos — esperando 60s")
                time.sleep(60)
                errores = 0

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    import sys
    if "--interactivo" in sys.argv:
        t = threading.Thread(target=loop_principal, daemon=True)
        t.start()
        logger.info("\n=== NEXO MOBILE — Modo Interactivo ===")
        logger.info(f"Backend: {BACKEND_URL}")
        while True:
            try:
                query = input("nexo> ").strip()
                if not query:
                    continue
                if query.lower() == "salir":
                    break
                resp = requests.post(f"{BACKEND_URL}/api/agente/", json={"query": query}, timeout=30)
                print("NEXO:", resp.json().get("respuesta", "?"))
            except KeyboardInterrupt:
                break
    else:
        loop_principal()
