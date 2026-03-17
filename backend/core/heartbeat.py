"""
Heartbeat service — actualiza el estado de salud cada 60 segundos.
Escribe en memoria y opcionalmente en Qdrant/Redis para monitoreo externo.
"""
from __future__ import annotations

import os
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

_state: Dict[str, Any] = {
    "alive": False,
    "started_at": None,
    "last_beat": None,
    "beat_count": 0,
    "services": {},
}
_lock = threading.Lock()


def _check_qdrant() -> str:
    try:
        from qdrant_client import QdrantClient
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        c = QdrantClient(url=url, timeout=3)
        c.get_collections()
        return "ok"
    except Exception as e:
        return f"error: {e}"


def _check_backend() -> str:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as r:
            return "ok" if r.status < 400 else f"http_{r.status}"
    except Exception as e:
        return f"error: {e}"


def _beat() -> None:
    now = datetime.now(timezone.utc).isoformat()
    services = {
        "qdrant": _check_qdrant(),
        "backend": _check_backend(),
    }
    with _lock:
        _state["alive"] = True
        _state["last_beat"] = now
        _state["beat_count"] += 1
        _state["services"] = services
    logger.debug("Heartbeat #%d — %s | services: %s", _state["beat_count"], now, services)


def _loop(interval: int = 60) -> None:
    while True:
        try:
            _beat()
        except Exception as e:
            logger.error("Heartbeat error: %s", e)
        time.sleep(interval)


def start(interval: int = 60) -> threading.Thread:
    """Arranca el heartbeat en background. Llamar desde lifespan."""
    with _lock:
        _state["started_at"] = datetime.now(timezone.utc).isoformat()
        _state["alive"] = True

    t = threading.Thread(target=_loop, args=(interval,), daemon=True, name="heartbeat")
    t.start()
    logger.info("Heartbeat iniciado (intervalo=%ds)", interval)
    return t


def get_status() -> Dict[str, Any]:
    with _lock:
        return dict(_state)
