# backend/routes/mobile_ai.py — AI endpoint optimizado para móvil
# Routing: LAN → torre Gemma 4 (27B GPU, $0) | off-LAN → dominio | offline → llama.cpp 1B
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import aiohttp
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/mobile", tags=["mobile-ai"])

# Shared conversation context per agent_id (in-memory, resets on restart)
_contexts: dict[str, list[dict]] = {}

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class MobileAIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    agent_id: str = "phone"
    system: Optional[str] = None
    model: str = "auto"           # auto | gemma4 | gemma3 | gemma2 | flash | claude
    max_tokens: int = 1024        # smaller default for phone bandwidth
    temperature: float = 0.2
    stream: bool = False
    remember: bool = True         # persist in shared context
    reset_context: bool = False   # clear history for this agent


class MobileAIResponse(BaseModel):
    text: str
    model_used: str
    source: str                   # ollama_torre | ollama_local_phone | gemini_cloud | claude_cloud
    tokens: int = 0
    cost_usd: float = 0.0
    agent_id: str
    context_size: int = 0
    timestamp: str


# ──────────────────────────────────────────────────────────────
# Context management
# ──────────────────────────────────────────────────────────────

def _get_context(agent_id: str) -> list[dict]:
    return _contexts.get(agent_id, [])


def _add_to_context(agent_id: str, role: str, content: str) -> None:
    ctx = _contexts.setdefault(agent_id, [])
    ctx.append({"role": role, "content": content})
    # Keep last 20 turns to avoid huge prompts on mobile
    if len(ctx) > 40:
        _contexts[agent_id] = ctx[-40:]


def _build_prompt_with_context(agent_id: str, prompt: str, system: Optional[str]) -> str:
    ctx = _get_context(agent_id)
    sys_prompt = system or (
        "Eres NEXO, el asistente de inteligencia soberana. "
        "Respuestas concisas y directas. Español salvo que pidan inglés."
    )
    parts = [f"SYSTEM: {sys_prompt}\n"]
    for turn in ctx[-10:]:  # last 10 turns in prompt
        prefix = "USER" if turn["role"] == "user" else "NEXO"
        parts.append(f"{prefix}: {turn['content']}")
    parts.append(f"USER: {prompt}")
    parts.append("NEXO:")
    return "\n".join(parts)


# ──────────────────────────────────────────────────────────────
# Ollama call (tower's local Gemma 4)
# ──────────────────────────────────────────────────────────────

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


async def _ask_ollama(
    prompt_with_ctx: str,
    model: str,
    temperature: float,
    max_tokens: int,
    stream: bool,
) -> tuple[str, str, int]:
    """Returns (text, model_used, tokens_used). Raises on failure."""
    # Auto-select model
    if model in ("auto", "gemma4"):
        candidates = ["gemma4:27b", "gemma4:12b", "gemma4:4b", "gemma4",
                      "gemma3:27b", "gemma3:12b", "gemma3", "gemma2:9b", "gemma2"]
    else:
        candidates = [model]

    payload = {
        "model": candidates[0],
        "prompt": prompt_with_ctx,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }

    async with aiohttp.ClientSession() as session:
        # Try each candidate model
        for candidate in candidates:
            payload["model"] = candidate
            try:
                async with session.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("response", "")
                        tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                        return text.strip(), candidate, tokens
            except Exception:
                continue

    raise RuntimeError("No Ollama model available")


# ──────────────────────────────────────────────────────────────
# Gemini fallback
# ──────────────────────────────────────────────────────────────

async def _ask_gemini(prompt: str, max_tokens: int, temperature: float) -> tuple[str, int]:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    import google.generativeai as genai  # type: ignore
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
    )
    text = resp.text or ""
    tokens = len(prompt.split()) + len(text.split())
    return text.strip(), tokens


# ──────────────────────────────────────────────────────────────
# POST /api/ai/mobile/query — main endpoint
# ──────────────────────────────────────────────────────────────

@router.post("/query", response_model=MobileAIResponse)
async def mobile_ai_query(payload: MobileAIRequest):
    if payload.reset_context:
        _contexts.pop(payload.agent_id, None)

    full_prompt = _build_prompt_with_context(
        payload.agent_id, payload.prompt, payload.system
    )

    text = ""
    model_used = "unknown"
    source = "error"
    tokens = 0
    cost = 0.0

    # 1. Try tower's Ollama (local Gemma 4 — $0)
    try:
        text, model_used, tokens = await _ask_ollama(
            full_prompt, payload.model, payload.temperature, payload.max_tokens, payload.stream
        )
        source = "ollama_torre"
    except Exception as e_ollama:
        logger.warning(f"[MOBILE-AI] Ollama failed: {e_ollama} — trying Gemini")
        # 2. Fallback: Gemini Flash (~$0.0001/1K)
        try:
            text, tokens = await _ask_gemini(full_prompt, payload.max_tokens, payload.temperature)
            model_used = "gemini-2.0-flash"
            source = "gemini_cloud"
            cost = round(tokens * 0.0000001, 6)
        except Exception as e_gemini:
            logger.error(f"[MOBILE-AI] Gemini fallback failed: {e_gemini}")
            raise HTTPException(status_code=503, detail="All AI backends unavailable")

    # Persist to shared context
    if payload.remember:
        _add_to_context(payload.agent_id, "user", payload.prompt)
        _add_to_context(payload.agent_id, "assistant", text)

    return MobileAIResponse(
        text=text,
        model_used=model_used,
        source=source,
        tokens=tokens,
        cost_usd=cost,
        agent_id=payload.agent_id,
        context_size=len(_get_context(payload.agent_id)),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ──────────────────────────────────────────────────────────────
# GET /api/ai/mobile/context/{agent_id} — view shared context
# ──────────────────────────────────────────────────────────────

@router.get("/context/{agent_id}")
async def get_context(agent_id: str):
    ctx = _get_context(agent_id)
    return {
        "agent_id": agent_id,
        "turns": len(ctx) // 2,
        "context": ctx,
    }


@router.delete("/context/{agent_id}")
async def clear_context(agent_id: str, x_api_key: str = Header(None)):
    expected = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="API Key inválida")
    _contexts.pop(agent_id, None)
    return {"cleared": True, "agent_id": agent_id}


# ──────────────────────────────────────────────────────────────
# GET /api/ai/mobile/models — what's available on torre
# ──────────────────────────────────────────────────────────────

@router.get("/models")
async def available_models():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_URL}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {"source": "ollama_torre", "models": models, "count": len(models)}
    except Exception:
        pass
    return {"source": "unavailable", "models": [], "count": 0}


# ──────────────────────────────────────────────────────────────
# GET /api/ai/mobile/status — quick status for phone UI
# ──────────────────────────────────────────────────────────────

@router.get("/status")
async def mobile_ai_status():
    ollama_ok = False
    models = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_URL}/api/tags",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    ollama_ok = True
    except Exception:
        pass

    gemini_ok = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    claude_ok = bool(os.getenv("ANTHROPIC_API_KEY"))

    return {
        "ollama_torre": {"available": ollama_ok, "models": models},
        "gemini_flash": {"available": gemini_ok},
        "claude": {"available": claude_ok},
        "recommended": "ollama_torre" if ollama_ok else ("gemini_flash" if gemini_ok else "none"),
        "active_contexts": list(_contexts.keys()),
    }
