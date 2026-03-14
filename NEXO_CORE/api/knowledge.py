from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])

class KnowledgeQuery(BaseModel):
    query: str
    categoria: str | None = None

@router.post("/consultar")
async def consultar_rag(req: KnowledgeQuery):
    try:
        from backend.services.rag_service import RAGService
        rag = RAGService()
        resultado = rag.consultar(pregunta=req.query, categoria=req.categoria)
        return resultado
    except Exception as e:
        return {"respuesta": f"RAG no disponible: {e}", "fuentes": []}

@router.get("/status")
async def knowledge_status():
    return {"status": "ok", "backend": "rag_service"}
