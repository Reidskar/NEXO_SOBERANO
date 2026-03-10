from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from NEXO_CORE.core.state_manager import state_manager
from NEXO_CORE.services.obs_manager import obs_manager
from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/")
async def health_check():
    snapshot = state_manager.snapshot()
    uptime = (datetime.now(timezone.utc) - datetime.fromisoformat(snapshot["uptime_start"])).total_seconds()
    return {
        "status": "operational",
        "uptime_seconds": int(uptime),
        "state": snapshot,
        "ai_web": web_ai_supervisor.snapshot(),
    }


@router.get("/stream")
async def stream_health():
    snapshot = state_manager.snapshot()
    current_scene = await obs_manager.get_current_scene() if snapshot["obs_connected"] else None
    return {
        "active": snapshot["stream_active"],
        "obs_connected": snapshot["obs_connected"],
        "discord_connected": snapshot["discord_connected"],
        "current_scene": current_scene,
    }


@router.get("/ai")
async def ai_health():
    return web_ai_supervisor.snapshot()
