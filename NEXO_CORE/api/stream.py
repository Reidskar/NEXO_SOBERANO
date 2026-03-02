from __future__ import annotations

from fastapi import APIRouter, Depends

from NEXO_CORE.core.state_manager import state_manager
from NEXO_CORE.middleware.rate_limit import enforce_rate_limit
from NEXO_CORE.models.stream import StreamControlRequest, StreamStatusResponse

router = APIRouter(prefix="/api/stream", tags=["stream"])


@router.get("/status", response_model=StreamStatusResponse, dependencies=[Depends(enforce_rate_limit)])
async def get_stream_status() -> StreamStatusResponse:
    snapshot = state_manager.snapshot()
    return StreamStatusResponse(
        active=snapshot["stream_active"],
        obs_connected=snapshot["obs_connected"],
        discord_connected=snapshot["discord_connected"],
        current_scene=snapshot["current_scene"],
    )


@router.post("/status", dependencies=[Depends(enforce_rate_limit)])
async def set_stream_status(payload: StreamControlRequest):
    state_manager.set_stream_active(payload.active)
    return {"ok": True, "stream_active": payload.active}
