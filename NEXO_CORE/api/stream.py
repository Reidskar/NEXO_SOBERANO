import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/stream", tags=["Stream"])

@router.get("/ping")
async def stream_ping():
    async def gen():
        for i in range(5):
            yield f"data: ping {i}\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")
