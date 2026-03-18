import os
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.getcwd(), "system_config.json")
_config_lock = Lock()

DEFAULT_CONFIG = {
    "video": {
        "enabled": True,
        "min_impact_score": 8,
        "style": "neutral"
    },
    "ai": {
        "temperature": 0.2,
        "max_tokens": 1000
    },
    "pipeline": {
        "interval_seconds": 120
    }
}

def _init_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    else:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Falla crítica: Error parseando {CONFIG_PATH}: {e}")
            return DEFAULT_CONFIG

_current_config = _init_config()

def get_config() -> dict:
    """Devuelve la configuración cargada en memoria con thread-safety."""
    with _config_lock:
        return _current_config

def update_config(new_config: dict):
    """Actualiza la configuración en caliente (Hot Swap) y escribe al disco."""
    global _current_config
    with _config_lock:
        _current_config = new_config
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_current_config, f, indent=4)
        logger.info("⚙️ [SYSTEM_CONFIG] Configuración del sistema re-estructurada dinámica y persistida.")
