from __future__ import annotations

from pydantic import BaseModel, Field


class StreamStatusResponse(BaseModel):
    active: bool
    obs_connected: bool
    discord_connected: bool
    current_scene: str | None = None


class StreamControlRequest(BaseModel):
    active: bool = Field(..., description="Estado de stream")
