"""
backend/routes/content.py
===========================
API de Grabación, Vault y Guía de Investigación IA.

Endpoints:
  POST /api/content/record/start       — inicia grabación (phone/obs/screen/file)
  POST /api/content/record/stop        — detiene y procesa
  GET  /api/content/sessions           — lista sesiones de captura
  GET  /api/content/sessions/{id}      — estado de una sesión

  POST /api/research/sessions          — crea sesión de investigación
  GET  /api/research/sessions          — lista investigaciones
  GET  /api/research/sessions/{id}     — estado de investigación
  POST /api/research/sessions/{id}/ask — pregunta libre a la IA
  GET  /api/research/sessions/{id}/suggest — ¿qué grabar a continuación?
  GET  /api/research/sessions/{id}/insights — síntesis de hallazgos
  POST /api/research/sessions/{id}/report  — genera reporte final
"""
from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from backend.services.content_pipeline import content_pipeline
from backend.services.research_guide import research_guide

logger = logging.getLogger(__name__)
router = APIRouter(tags=["content"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")


def _auth(key: str = None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


# ── Modelos ────────────────────────────────────────────────────────────────────

class StartRecordRequest(BaseModel):
    source: str = "phone"          # phone | obs | screen | file
    tag: str = "GEN"               # MIL | ECO | GEO | POL | PSY | GEN
    research_id: Optional[str] = None
    title: str = ""
    file_path: Optional[str] = None   # solo para source="file"


class StopRecordRequest(BaseModel):
    session_id: str


class CreateResearchRequest(BaseModel):
    topic: str
    scope: str = "general"
    depth: str = "profundo"
    language: str = "es"


class AskRequest(BaseModel):
    question: str


# ── GRABACIÓN / VAULT ──────────────────────────────────────────────────────────

@router.post("/api/content/record/start")
def start_record(body: StartRecordRequest, x_api_key: str = Header(None)):
    """Inicia grabación desde la fuente indicada."""
    _auth(x_api_key)
    return content_pipeline.start_capture(
        source=body.source,
        tag=body.tag,
        research_id=body.research_id,
        file_path=body.file_path,
        title=body.title,
    )


@router.post("/api/content/record/stop")
def stop_record(body: StopRecordRequest, x_api_key: str = Header(None)):
    """Detiene la grabación y lanza el pipeline de procesamiento."""
    _auth(x_api_key)
    return content_pipeline.stop_capture(body.session_id)


@router.post("/api/content/ingest")
async def ingest_file(
    background_tasks: BackgroundTasks,
    tag: str = "GEN",
    title: str = "",
    research_id: Optional[str] = None,
    file: UploadFile = File(...),
    x_api_key: str = Header(None),
):
    """Sube un archivo para ingesta y clasificación IA directa."""
    _auth(x_api_key)
    import tempfile, shutil
    from pathlib import Path
    suffix = Path(file.filename).suffix if file.filename else ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    result = content_pipeline.start_capture(
        source="file",
        tag=tag,
        title=title or file.filename or "",
        research_id=research_id,
        file_path=tmp_path,
    )
    return result


@router.post("/api/content/ingest-crucix")
async def ingest_crucix_briefing(payload: dict, x_api_key: str = Header(None)):
    """
    Endpoint exclusivo para Crucix: recibe un briefing de inteligencia
    con 27+ fuentes y lo clasifica + almacena en el vault de NEXO.
    """
    _auth(x_api_key)
    import json, threading
    from datetime import datetime, timezone
    from backend.services.research_guide import research_guide
    from backend.services.content_pipeline import content_pipeline, VAULT_DIR
    from pathlib import Path

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    briefing_dir = VAULT_DIR / "crucix"
    briefing_dir.mkdir(parents=True, exist_ok=True)

    # Guardar briefing completo como JSON
    briefing_path = briefing_dir / f"crucix_briefing_{ts}.json"
    briefing_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )

    # Extraer texto para clasificación
    sources_text = []
    for key, val in payload.items():
        if isinstance(val, dict):
            text = val.get("summary") or val.get("alerts") or val.get("headline") or ""
            if text:
                sources_text.append(f"[{key.upper()}] {text}")
        elif isinstance(val, str) and len(val) > 10:
            sources_text.append(f"[{key.upper()}] {val}")

    combined = "\n".join(sources_text[:30])

    # Clasificar con Gemini
    classification = content_pipeline._classify(briefing_path, combined, "GEN")

    # Guardar resumen clasificado
    summary = {
        "source": "crucix",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "briefing_path": str(briefing_path),
        "classification": classification,
        "sources_active": list(payload.keys()),
        "satellite_data": payload.get("SkyOSINT") or payload.get("Space"),
    }
    (briefing_dir / f"crucix_summary_{ts}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )

    # Si hay investigaciones activas, inyectar el briefing en todas
    active = research_guide.list_sessions(status="active")
    for session in active[:3]:
        research_guide.add_capture(session["id"], {
            "session_capture_id": f"crucix_{ts}",
            "source": "crucix_briefing",
            "transcript": combined[:2000],
            "classification": classification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return {
        "ok": True,
        "briefing_saved": str(briefing_path),
        "classification": classification.get("etiqueta", "GEN"),
        "impact": classification.get("impacto", ""),
        "injected_into_sessions": len(active),
    }


@router.get("/api/content/sessions")
def list_capture_sessions(limit: int = 20, x_api_key: str = Header(None)):
    _auth(x_api_key)
    return {"sessions": content_pipeline.list_sessions(limit=limit)}


@router.get("/api/content/sessions/{session_id}")
def get_capture_session(session_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    session = content_pipeline.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return session


# ── INVESTIGACIÓN ──────────────────────────────────────────────────────────────

@router.post("/api/research/sessions")
def create_research(body: CreateResearchRequest, x_api_key: str = Header(None)):
    """Crea una nueva sesión de investigación guiada por IA."""
    _auth(x_api_key)
    return research_guide.create_session(
        topic=body.topic,
        scope=body.scope,
        depth=body.depth,
        language=body.language,
    )


@router.get("/api/research/sessions")
def list_research(status: str = None, x_api_key: str = Header(None)):
    _auth(x_api_key)
    return {"sessions": research_guide.list_sessions(status=status)}


@router.get("/api/research/sessions/{session_id}")
def get_research(session_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    session = research_guide.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return session


@router.post("/api/research/sessions/{session_id}/ask")
def ask_research(session_id: str, body: AskRequest, x_api_key: str = Header(None)):
    """Pregunta libre a la IA sobre la investigación en curso."""
    _auth(x_api_key)
    return research_guide.ask(session_id, body.question)


@router.get("/api/research/sessions/{session_id}/suggest")
def suggest_next(session_id: str, x_api_key: str = Header(None)):
    """¿Qué grabar o investigar a continuación?"""
    _auth(x_api_key)
    return research_guide.suggest_next(session_id)


@router.get("/api/research/sessions/{session_id}/insights")
def get_insights(session_id: str, x_api_key: str = Header(None)):
    """Síntesis IA de todo lo recopilado hasta ahora."""
    _auth(x_api_key)
    return research_guide.get_insights(session_id)


@router.post("/api/research/sessions/{session_id}/report")
def generate_report(session_id: str, x_api_key: str = Header(None)):
    """Genera el reporte final de investigación en Markdown."""
    _auth(x_api_key)
    return research_guide.generate_report(session_id)
