"""
backend/routes/cognitive.py
============================
Endpoint del Motor Cognitivo — punto de entrada para la conversación de voz.

POST /api/cognitive/process   — turno de conversación completo
GET  /api/cognitive/session   — estado de la sesión activa
POST /api/cognitive/youtube   — registrar stream YouTube activo
DELETE /api/cognitive/youtube — limpiar contexto YouTube
GET  /api/cognitive/sessions  — listar sesiones activas
"""
from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cognitive"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")


def _auth(key=None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


def _engine():
    from backend.services.cognitive_engine import cognitive_engine
    return cognitive_engine


class ProcessRequest(BaseModel):
    text: str
    channel_id: str
    user_id: str = ""


class YouTubeContextRequest(BaseModel):
    channel_id: str
    title: str = ""
    video_id: str = ""
    url: str = ""
    description: str = ""


@router.post("/api/cognitive/process")
async def process_turn(body: ProcessRequest, x_api_key: str = Header(None)):
    """Procesa un turno de voz: clasifica intent, ejecuta herramientas, sintetiza respuesta."""
    _auth(x_api_key)
    result = await _engine().process(
        text=body.text,
        channel_id=body.channel_id,
        user_id=body.user_id,
    )
    return result


@router.post("/api/cognitive/voz")
async def process_voz(body: ProcessRequest, x_api_key: str = Header(None)):
    """
    Path rápido para voz en tiempo real — va directo a Ollama sin tools ni self-eval.
    Objetivo: respuesta < 8s.
    """
    _auth(x_api_key)
    import asyncio
    try:
        from NEXO_CORE.services.ollama_service import ollama_service
        prompt = f"""Eres NEXO, un analista de inteligencia conciso que responde por audio.
Una oración directa, sin listas, sin formato. Tono natural, como en conversación.

Mensaje: "{body.text}"

Responde en UNA oración oral, máximo 25 palabras."""

        resp = await asyncio.wait_for(
            ollama_service.consultar(prompt, modelo="fast", temperature=0.2),
            timeout=12.0
        )
        text = resp.text.strip() if resp.success else ""
        # Limpiar thinking tags
        if "<think>" in text:
            text = text.split("</think>")[-1].strip()
        if not text:
            text = "Procesando tu consulta."
        return {
            "response": text[:300],
            "intent": "CONVERSACION",
            "tools_used": [],
            "urgent": False,
            "model": "ollama_fast",
        }
    except asyncio.TimeoutError:
        return {"response": "Dame un segundo, estoy procesando.", "intent": "CONVERSACION", "tools_used": [], "urgent": False}
    except Exception as e:
        logger.error(f"[VOZ FAST] Error: {e}")
        return {"response": "Error procesando respuesta.", "intent": "CONVERSACION", "tools_used": [], "urgent": False}


@router.get("/api/cognitive/session")
def get_session(channel_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    engine = _engine()
    session = engine.get_session(channel_id)
    return {
        "session_id": session.session_id,
        "channel_id": channel_id,
        "turns": len(session.turns),
        "active_topics": session.active_topics,
        "youtube_active": bool(session.youtube_context),
        "youtube_context": session.youtube_context,
        "last_active": session.last_active,
    }


@router.post("/api/cognitive/youtube")
def set_youtube(body: YouTubeContextRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    _engine().set_youtube_context(body.channel_id, {
        "title": body.title,
        "video_id": body.video_id,
        "url": body.url,
        "description": body.description,
    })
    return {"ok": True, "message": f"Stream '{body.title}' registrado para canal {body.channel_id}"}


@router.delete("/api/cognitive/youtube")
def clear_youtube(channel_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    _engine().clear_youtube_context(channel_id)
    return {"ok": True}


@router.get("/api/cognitive/sessions")
def list_sessions(x_api_key: str = Header(None)):
    _auth(x_api_key)
    engine = _engine()
    sessions = []
    for cid, s in engine._sessions.items():
        sessions.append({
            "channel_id": cid,
            "session_id": s.session_id,
            "turns": len(s.turns),
            "active_topics": s.active_topics,
            "youtube_active": bool(s.youtube_context),
        })
    return {"sessions": sessions}


@router.get("/api/cognitive/metacog")
def get_metacognition(x_api_key: str = Header(None)):
    """Retorna las estadísticas de metacognición del motor."""
    _auth(x_api_key)
    engine = _engine()
    return {
        "snapshot": engine.metacog.snapshot(),
        "intents_with_low_score": [
            i for i in engine.metacog._stats
            if engine.metacog.avg_score(i) < 0.45 and engine.metacog._stats[i]["hits"] >= 3
        ],
    }
