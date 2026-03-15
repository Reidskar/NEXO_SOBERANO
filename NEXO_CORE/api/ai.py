from __future__ import annotations

from fastapi import APIRouter, Depends

from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor
from NEXO_CORE.middleware.rate_limit import enforce_rate_limit
from NEXO_CORE.models.ai import AIBotAskRequest, AIBotAskResponse
from NEXO_CORE.services.ai_qa_bot import ai_qa_bot
from backend.routes import agente as agente_routes

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/ask", response_model=AIBotAskResponse, dependencies=[Depends(enforce_rate_limit)])
async def ask_ai_bot(payload: AIBotAskRequest) -> AIBotAskResponse:
    result = await ai_qa_bot.ask(question=payload.question.strip(), category=payload.category)
    return AIBotAskResponse(**result)


@router.get("/status", dependencies=[Depends(enforce_rate_limit)])
async def ai_status():
    return {
        "bot": {
            "history_size": len(ai_qa_bot.history()),
        },
        "ai_growth": web_ai_supervisor.snapshot(),
    }


@router.get("/history", dependencies=[Depends(enforce_rate_limit)])
async def ai_history():
    return {"items": ai_qa_bot.history()}


@router.post("/evolution-cycle", dependencies=[Depends(enforce_rate_limit)])
async def ai_evolution_cycle(apply_code_fix: bool = True):
    return await agente_routes.intelligence_evolution_cycle(apply_code_fix=apply_code_fix)


@router.get("/evolution-status", dependencies=[Depends(enforce_rate_limit)])
async def ai_evolution_status():
    return await agente_routes.intelligence_evolution_status()


@router.post("/foda-critical", dependencies=[Depends(enforce_rate_limit)])
async def ai_foda_critical(payload: agente_routes.FodaCriticalRequest):
    return await agente_routes.intelligence_foda_critico(payload)


@router.get("/foda-status", dependencies=[Depends(enforce_rate_limit)])
async def ai_foda_status():
    return await agente_routes.intelligence_foda_status()
