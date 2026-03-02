from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os
import sys

router = APIRouter()

# Asegurar imports desde raíz
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

class ChatRequest(BaseModel):
    """Request model para chat."""
    message: str
    context: str = ""

class ChatResponse(BaseModel):
    """Response model para chat."""
    response: str
    sources: List[str] = []
    confidence: float = 0.0

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Endpoint de chat conectado al motor RAG."""
    try:
        # Aquí se conectaría al motor RAG real
        # Por ahora: respuesta demo
        response_text = f"Procesando: {request.message}"
        
        return ChatResponse(
            response=response_text,
            sources=["demo"],
            confidence=0.95
        )
    except Exception as e:
        return ChatResponse(
            response=f"Error procesando solicitud: {str(e)}",
            sources=[],
            confidence=0.0
        )

@router.get("/chat/history")
async def chat_history():
    """Obtener historial de chat."""
    return {
        "history": [],
        "total": 0
    }
