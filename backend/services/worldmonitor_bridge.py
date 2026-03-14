from fastapi import APIRouter
router = APIRouter(prefix="/api/worldmonitor", tags=["WorldMonitor"])
@router.get("/status")
async def worldmonitor_status(): return {"status": "ok", "active": False}
