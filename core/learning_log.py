import os
import json
import uuid
import logging
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

LOG_PATH = os.path.join(os.getcwd(), "learning_log.json")
_log_lock = Lock()

def _load_logs():
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def log_change(action: str, old_config: dict, new_config: dict, reason: str) -> str:
    """Registra una mutación en el sistema y crea una nueva 'Época' de aprendizaje."""
    logs = _load_logs()
    change_id = str(uuid.uuid4())
    entry = {
        "id": change_id,
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "old_config": old_config,
        "new_config": new_config,
        "reason": reason,
        "metrics": []
    }
    with _log_lock:
        logs.append(entry)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs[-100:], f, indent=4) # max 100 epochs
    logger.info(f"📓 [LEARNING LOG] Nueva época registrada: {change_id}")
    return change_id

def attach_result_metrics(metric_data: dict):
    """Agrega telemetría a la época de configuración actual para evaluación futura."""
    logs = _load_logs()
    if not logs:
        log_change("system_init", {}, {}, "baseline")
        logs = _load_logs()
        
    latest = logs[-1]
    with _log_lock:
        latest["metrics"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "data": metric_data
        })
        with open(LOG_PATH, "w", encoding="utf-8") as f:
             json.dump(logs, f, indent=4)

def get_recent_changes():
    return _load_logs()
