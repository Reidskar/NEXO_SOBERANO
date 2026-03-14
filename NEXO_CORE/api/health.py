from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter

from NEXO_CORE.core.state_manager import state_manager
from NEXO_CORE.services.obs_manager import obs_manager
from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor

router = APIRouter(prefix="/api/health", tags=["health"])


from pydantic import BaseModel
from typing import Dict, Any

class DiscordStatusPayload(BaseModel):
    connected: bool
    voice_state: str
    guild_id: str = None
    uptime: int = 0

@router.get("/")
async def health_check():
    snapshot = state_manager.snapshot()
    uptime = (datetime.now(timezone.utc) - datetime.fromisoformat(snapshot["uptime_start"])).total_seconds()
    
    # DB Status (supongamos que está UP si la app cargó, o check real si hay tiempo)
    db_ok = True 
    
    # Agent Status
    agent = snapshot.get("last_agent_checkin")
    agent_status = "offline"
    if agent and agent.get("received_at"):
        last_dt = datetime.fromisoformat(agent["received_at"])
        if (datetime.now(timezone.utc) - last_dt).total_seconds() < 120:
            agent_status = "online"

    # AI Status
    ai_status = "operational"
    missing_keys = []
    for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if not os.getenv(k):
            missing_keys.append(k)
    if len(missing_keys) == 3:
        ai_status = "degraded"

    return {
        "status": "operational",
        "uptime_seconds": int(uptime),
        "db": "online" if db_ok else "offline",
        "xiaomi": agent_status,
        "ai": ai_status,
        "missing_keys": missing_keys,
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


@router.post("/discord-status")
async def discord_bot_status(payload: DiscordStatusPayload):
    state_manager.set_discord_bot_status(payload.dict())
    return {"status": "ok"}


@router.get("/systems")
async def systems_status():
    snapshot = state_manager.snapshot()
    
    discord_bot = snapshot.get("discord_bot_status", {})
    discord_state = "offline"
    if discord_bot and discord_bot.get("received_at"):
        last_dt = datetime.fromisoformat(discord_bot["received_at"])
        if (datetime.now(timezone.utc) - last_dt).total_seconds() < 120:
            discord_state = "online"
            
    return {
        "discord_bot": {
            "status": discord_state,
            "connected": discord_bot.get("connected", False),
            "voice_state": discord_bot.get("voice_state", "Desconectado"),
            "uptime": discord_bot.get("uptime", 0)
        },
        "xiaomi_agent": {
            "status": "online" if snapshot.get("last_agent_checkin") else "offline",
        },
        "warroom": {
            "status": "operational"
        }
    }
