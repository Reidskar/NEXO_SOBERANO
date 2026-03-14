import os
import time
import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
_START = time.time()

@router.get("/system")
async def system_metrics():
    mem = psutil.virtual_memory()
    return {
        "uptime_seconds": round(time.time() - _START, 1),
        "mode": os.getenv("NEXO_MODE", "local"),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory": {
            "total_mb": round(mem.total / 1024**2),
            "used_mb":  round(mem.used  / 1024**2),
            "percent":  mem.percent,
        },
        "version": "2.0.0",
        "status": "operational",
    }

@router.get("/health/deep")
async def deep_health():
    checks = {}
    # Redis
    try:
        from backend.worker.celery_app import celery_app
        celery_app.control.ping(timeout=1)
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = "offline"
        
    # Supabase
    try:
        from backend.services.supabase_client import supabase
        supabase.table("tenants").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = "offline"
        
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
