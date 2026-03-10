from __future__ import annotations

from pydantic import BaseModel, Field


class AIBotAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000, description="Pregunta del usuario")
    category: str | None = Field(default=None, max_length=120, description="Filtro opcional de categoría")


class AIBotAskResponse(BaseModel):
    ok: bool
    answer: str
    sources: list[str] = []
    used_rag: bool = False
    used_provider: str | None = None
    chunks_used: int = 0
    total_docs: int = 0
    ai_growth: dict
    execution_time_ms: int = 0
