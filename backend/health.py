from fastapi import APIRouter
from datetime import datetime, timezone
import os, time

router = APIRouter(tags=["health"])
START_TIME = time.time()

@router.get("/health")
async def health():
    """Endpoint de healthcheck para Railway y monitores externos."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_s": int(time.time() - START_TIME),
        "mode": os.getenv("NEXO_MODE", "local"),
        "version": "0.8.0"
    }

@router.get("/")
async def root():
    return {"nexo": "soberano", "status": "online", "version": "0.8.0"}
