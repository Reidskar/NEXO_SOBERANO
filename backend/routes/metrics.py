from fastapi import APIRouter
import psutil
import time
import os
from datetime import datetime

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

START_TIME = time.time()

@router.get("/")
async def get_metrics():
    uptime = time.time() - START_TIME
    
    # Métricas de sistema
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    
    # Intentar obtener costos (fallback si no hay DB)
    try:
        from backend.services.unified_cost_tracker import get_cost_tracker
        tracker = get_cost_tracker()
        cost_today = tracker.get_cost_report(period="today").get("total_cost_usd", 0)
    except Exception:
        cost_today = 0.0

    return {
        "uptime_seconds": uptime,
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_used_mb": round(memory.used / (1024*1024), 2),
        },
        "costs": {
            "today_usd": cost_today
        },
        "version": "3.3.0"
    }
