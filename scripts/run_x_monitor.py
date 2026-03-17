"""
scripts/run_x_monitor.py
=========================
Ejecuta un ciclo de monitoreo web/X (Twitter) para NEXO SOBERANO.
Llamado por WebAISupervisor con: --once --limit N

Salida JSON en stdout.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nexo.x_monitor")


def _check_x_api() -> dict[str, Any]:
    """Verifica conectividad con la API de X/Twitter."""
    bearer = os.getenv("TWITTER_BEARER_TOKEN", "") or os.getenv("X_BEARER_TOKEN", "")
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY", "") or os.getenv("X_CONSUMER_KEY", "")

    if not bearer and not consumer_key:
        return {
            "available": False,
            "reason": "TWITTER_BEARER_TOKEN / X_BEARER_TOKEN no configuradas",
        }

    try:
        from backend.services.x_monitor import XMonitor
        monitor = XMonitor()
        status = monitor.get_status() if hasattr(monitor, "get_status") else {"ok": True}
        return {"available": True, "status": status}
    except ImportError:
        return {"available": False, "reason": "x_monitor module not found"}
    except Exception as e:
        return {"available": False, "reason": str(e)[:200]}


def _get_latest_monitor_data() -> dict[str, Any]:
    """Lee datos del último ciclo de monitoreo guardado."""
    try:
        log_path = ROOT / "logs" / "x_monitor_last.json"
        if log_path.exists():
            age = time.time() - log_path.stat().st_mtime
            data = json.loads(log_path.read_text(encoding="utf-8"))
            data["cache_age_seconds"] = int(age)
            return data
    except Exception:
        pass
    return {}


def _try_run_real_monitor(limit: int) -> dict[str, Any] | None:
    """Intenta ejecutar el monitor real de X si está disponible."""
    try:
        from backend.services.x_monitor import XMonitor
        monitor = XMonitor()
        if hasattr(monitor, "run_once"):
            result = monitor.run_once(limit=limit)
            return result
        if hasattr(monitor, "monitor"):
            result = monitor.monitor(limit=limit)
            return result
    except Exception as e:
        logger.debug("Real X monitor failed: %s", e)
    return None


def run_once(limit: int = 20) -> dict[str, Any]:
    """Ejecuta un ciclo único de monitoreo."""
    started = time.time()
    x_api = _check_x_api()
    cached = _get_latest_monitor_data()

    result: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ok": True,
        "limit": limit,
        "x_api": x_api,
        "duration_ms": 0,
        "items_checked": 0,
        "source": "cache",
    }

    if x_api.get("available"):
        real = _try_run_real_monitor(limit)
        if real:
            result.update(real)
            result["source"] = "live"
            result["items_checked"] = int(real.get("items_checked", real.get("count", 0)))

            # Guardar para próximas llamadas
            log_path = ROOT / "logs" / "x_monitor_last.json"
            log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        elif cached:
            result.update(cached)
            result["source"] = "cache"
    elif cached:
        result.update(cached)
        result["source"] = "cache"
        result["ok"] = True  # cache disponible = no es error crítico

    result["duration_ms"] = int((time.time() - started) * 1000)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXO X Monitor")
    parser.add_argument("--once", action="store_true", help="Ejecutar ciclo único")
    parser.add_argument("--limit", type=int, default=20, help="Máximo de items a procesar")
    args = parser.parse_args()

    result = run_once(limit=args.limit)
    log.info(json.dumps(result, ensure_ascii=False))
