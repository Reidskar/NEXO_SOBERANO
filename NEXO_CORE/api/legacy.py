from fastapi import APIRouter
router = APIRouter()
try:
    from backend.routes.agente import router as _agente_router
    router.include_router(_agente_router)
except ImportError:
    pass  # modo degradado sin legacy
