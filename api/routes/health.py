from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
def health_check():
    """Endpoint para verificar estado del backend."""
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "message": "✅ Nexo Soberano está operacional"
    }

@router.get("/status")
def status():
    """Status detallado del sistema."""
    return {
        "api": "online",
        "rag_engine": "ready",
        "vectordb": "ready",
        "connectors": {
            "google": "configured",
            "microsoft": "configured",
            "discord": "pending"
        },
        "timestamp": datetime.now().isoformat()
    }
