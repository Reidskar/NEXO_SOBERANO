import time
from fastapi import APIRouter
from NEXO_CORE import config

router = APIRouter(tags=["Health"])
_start = time.time()

@router.get("/api/health")
async def health():
    return {"status": "online", "version": getattr(config, "APP_VERSION", "3.0.0"),
            "uptime_seconds": round(time.time() - _start, 1)}

@router.get("/api/status")
async def status():
    return {"status": "ok", "version": getattr(config, "APP_VERSION", "3.0.0"),
            "mode": "nexo_core_v3"}
