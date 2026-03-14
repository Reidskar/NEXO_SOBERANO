from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/ai", tags=["AI"])

class QueryRequest(BaseModel):
    query: str
    provider: str = "auto"

@router.post("/consultar")
async def consultar_ia(req: QueryRequest):
    try:
        from backend.services.multi_ai_service import MultiAIService
        svc = MultiAIService()
        respuesta, proveedor = svc.chat([{"role": "user", "content": req.query}])
        return {"answer": respuesta, "provider": proveedor}
    except Exception as e:
        return {"answer": f"Error: {e}", "provider": "none"}
