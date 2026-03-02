from __future__ import annotations

from fastapi import APIRouter

from backend.routes import agente, eventos

router = APIRouter()
router.include_router(agente.router)
router.include_router(eventos.router)
