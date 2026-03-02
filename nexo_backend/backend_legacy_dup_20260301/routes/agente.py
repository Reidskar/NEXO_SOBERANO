from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.rag_service import RAGService
from backend.services.cost_manager import CostManager
import time

router = APIRouter(prefix="/agente", tags=["Agente"])

rag = RAGService()
cost = CostManager()

class ConsultaRequest(BaseModel):
    query: str
    mode: str = "normal"
    categoria: str | None = None


@router.post("/consultar")
def consultar(request: ConsultaRequest):

    inicio = time.time()

    resultado = rag.consultar(
        pregunta=request.query,
        categoria=request.categoria,
        mode=request.mode
    )

    execution_time = int((time.time() - inicio) * 1000)

    tokens_reales = resultado.get("tokens_reales", 0)

    cost.registrar(tokens_reales, modelo=resultado.get("modelo_usado", "flash"))

    return {
        "answer": resultado.get("respuesta"),
        "sources": resultado.get("fuentes", []),
        "tokens_used": tokens_reales,
        "chunks_used": len(resultado.get("fuentes", [])),
        "execution_time_ms": execution_time,
        "presupuesto": cost.obtener_presupuesto()
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "presupuesto": cost.obtener_presupuesto()
    }


@router.get("/presupuesto")
def presupuesto():
    return cost.obtener_presupuesto()


@router.get("/historial-costos")
def historial():
    return cost.historial_7_dias()
