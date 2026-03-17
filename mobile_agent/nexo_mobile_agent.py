#!/usr/bin/env python3
"""
NEXO SOBERANO — Mobile Agent v0.4
Corre en Termux (Xiaomi). Se conecta al backend central y reporta métricas del dispositivo.
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
# En Termux, editar estas variables o poner en ~/.nexo_env
# Soporte multi-backend: local primero, Railway como fallback
BACKENDS = [
    os.getenv("NEXO_BACKEND", "http://192.168.100.22:8000"),      # Local (LAN)
    os.getenv("NEXO_BACKEND_TAILSCALE", "http://100.104.152.43:8000"), # Tailscale (IP detectada)
    os.getenv("NEXO_BACKEND_RAILWAY", ""),                          # Railway (producción)
]

def get_backend_activo() -> str:
    """Retorna el primer backend disponible."""
    for url in BACKENDS:
        if not url:
            continue
        try:
            r = requests.get(f"{url}/health", timeout=3)
            if r.status_code == 200:
                return url
        except:
            continue
    return BACKENDS[0]  # fallback al primero aunque falle

BACKEND_URL = get_backend_activo()
AGENT_ID    = os.getenv("NEXO_AGENT_ID", "xiaomi-mobile-01")
POLL_INTERVAL = int(os.getenv("NEXO_POLL", "30"))  # segundos entre reportes
API_KEY     = os.getenv("NEXO_API_KEY", "")  # para cuando implementes auth

# ── Métricas del dispositivo ───────────────────────────────────────────────────
def get_device_metrics() -> dict:
    """Recopila métricas del dispositivo Android via Termux."""
    metrics = {
        "agent_id": AGENT_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tipo": "mobile",
    }

    # CPU y RAM via psutil
    try:
        metrics["cpu_pct"] = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        metrics["ram_total_mb"] = round(mem.total / 1e6, 1)
        metrics["ram_usado_mb"] = round(mem.used / 1e6, 1)
        metrics["ram_pct"] = mem.percent
    except Exception as e:
        metrics["psutil_error"] = str(e)

    # Batería via Termux API (requiere termux-api instalado)
    try:
        r = subprocess.run(
            ["termux-battery-status"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            bat = json.loads(r.stdout)
            metrics["bateria_pct"] = bat.get("percentage", -1)
            metrics["bateria_estado"] = bat.get("status", "unknown")
            metrics["cargando"] = bat.get("plugged", False)
    except Exception:
        metrics["bateria_pct"] = -1  # termux-api no instalado

    # Conectividad
    try:
        r = subprocess.run(
            ["termux-wifi-connectioninfo"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            wifi = json.loads(r.stdout)
            metrics["wifi_ssid"] = wifi.get("ssid", "unknown")
            metrics["wifi_rssi"] = wifi.get("rssi", 0)
    except Exception:
        metrics["wifi_ssid"] = "unknown"

    return metrics

# ── Comunicación con backend ───────────────────────────────────────────────────
def reportar_metrics(metrics: dict) -> bool:
    """Envía métricas al endpoint del backend central."""
    try:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["X-API-Key"] = API_KEY

        resp = requests.post(
            f"{BACKEND_URL}/api/mobile/heartbeat",
            json=metrics,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            logger.info(f"Heartbeat OK — CPU:{metrics.get('cpu_pct')}% RAM:{metrics.get('ram_pct')}% BAT:{metrics.get('bateria_pct')}%")
            return True
        else:
            logger.warning(f"Heartbeat rechazado: {resp.status_code} — {resp.text[:100]}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"No se pudo conectar a {BACKEND_URL} — ¿Backend activo? ¿Misma red WiFi?")
        return False
    except Exception as e:
        logger.error(f"Error en heartbeat: {e}")
        return False

def consultar_agente(query: str) -> str:
    """Consulta al agente NEXO desde el móvil."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/agente/",
            json={"query": query},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get("respuesta", "Sin respuesta")
        return f"Error HTTP {resp.status_code}"
    except Exception as e:
        return f"Error de conexión: {e}"

# ── Loop principal ─────────────────────────────────────────────────────────────
def loop_heartbeat():
    """Loop de reporte de métricas cada POLL_INTERVAL segundos."""
    logger.info(f"[NEXO MOBILE] Agente iniciado — Backend: {BACKEND_URL}")
    logger.info(f"[NEXO MOBILE] Agent ID: {AGENT_ID} | Poll: {POLL_INTERVAL}s")

    errores_consecutivos = 0
    while True:
        try:
            metrics = get_device_metrics()
            ok = reportar_metrics(metrics)
            if ok:
                errores_consecutivos = 0
            else:
                errores_consecutivos += 1
                if errores_consecutivos >= 5:
                    logger.critical("5 errores consecutivos — verificar conexión y backend")
                    errores_consecutivos = 0
        except Exception as e:
            logger.error(f"Error en loop: {e}")

        time.sleep(POLL_INTERVAL)

def modo_interactivo():
    """Permite hacer queries al agente desde la terminal Termux."""
    log.info("\n=== NEXO MOBILE — Modo Interactivo ===")
    log.info(f"Backend: {BACKEND_URL}")
    log.info("Escribe 'salir' para terminar, 'metrics' para ver métricas locales\n")

    while True:
        try:
            query = input("nexo> ").strip()
            if not query:
                continue
            if query.lower() == "salir":
                break
            if query.lower() == "metrics":
                m = get_device_metrics()
                log.info(json.dumps(m, indent=2, ensure_ascii=False))
                continue
            log.info("Consultando...")
            respuesta = consultar_agente(query)
            log.info(f"NEXO: {respuesta}\n")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    import sys
    if "--interactivo" in sys.argv:
        # Modo terminal interactiva
        # Heartbeat en background
        t = threading.Thread(target=loop_heartbeat, daemon=True)
        t.start()
        modo_interactivo()
    else:
        # Solo heartbeat (modo servicio)
        loop_heartbeat()
