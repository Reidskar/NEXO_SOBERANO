"""
backend/routes/topics.py
=========================
API de Seguimiento Progresivo de Temas Estratégicos.

Endpoints:
  POST /api/topics                    — crear tema
  GET  /api/topics                    — listar temas
  GET  /api/topics/{id}               — detalle de tema
  PATCH /api/topics/{id}              — actualizar
  POST /api/topics/{id}/event         — agregar evento manual
  POST /api/topics/{id}/link-drive    — vincular archivo Drive
  GET  /api/topics/{id}/summary       — resumen IA progresivo
  GET  /api/topics/{id}/streams       — streams en vivo para el tema
  POST /api/topics/detect             — detectar temas en texto (voz/transcript)
  POST /api/topics/osint-sweep        — procesar sweep OSINT contra todos los temas
"""
from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)
router = APIRouter(tags=["topics"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")


def _auth(key: str = None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


def _tracker():
    from backend.services.topic_tracker import topic_tracker
    return topic_tracker


# ── Modelos ───────────────────────────────────────────────────────────────────

class CreateTopicRequest(BaseModel):
    name: str
    keywords: List[str]
    description: str = ""
    region: str = "general"
    priority: str = "media"  # alta | media | baja


class AddEventRequest(BaseModel):
    source: str
    text: str
    url: Optional[str] = None
    impact: Optional[str] = None


class LinkDriveRequest(BaseModel):
    file_id: str
    name: str
    mime_type: str = ""
    description: str = ""
    transcript: str = ""
    drive_url: Optional[str] = None


class DetectTopicsRequest(BaseModel):
    text: str


class OsintSweepRequest(BaseModel):
    sweep: dict  # resultado completo del OSINT Engine


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/api/topics")
def create_topic(body: CreateTopicRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    topic = _tracker().create_topic(
        name=body.name,
        keywords=body.keywords,
        description=body.description,
        region=body.region,
        priority=body.priority,
    )
    return topic


@router.get("/api/topics")
def list_topics(status: str = None, priority: str = None, x_api_key: str = Header(None)):
    _auth(x_api_key)
    return {"topics": _tracker().list_topics(status=status, priority=priority)}


@router.get("/api/topics/{topic_id}")
def get_topic(topic_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    topic = _tracker().get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    return topic


@router.patch("/api/topics/{topic_id}")
def update_topic(topic_id: str, body: dict, x_api_key: str = Header(None)):
    _auth(x_api_key)
    topic = _tracker().update_topic(topic_id, **body)
    if not topic:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    return topic


@router.post("/api/topics/{topic_id}/event")
def add_event(topic_id: str, body: AddEventRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    ok = _tracker().add_event(topic_id, {
        "source": body.source,
        "text": body.text,
        "url": body.url,
        "impact": body.impact,
    })
    if not ok:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    return {"ok": True}


@router.post("/api/topics/{topic_id}/link-drive")
def link_drive(topic_id: str, body: LinkDriveRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    ok = _tracker().link_drive_file(topic_id, {
        "file_id": body.file_id,
        "name": body.name,
        "mime_type": body.mime_type,
        "description": body.description,
        "transcript": body.transcript,
        "drive_url": body.drive_url,
    })
    if not ok:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    return {"ok": True}


@router.get("/api/topics/{topic_id}/summary")
def get_summary(topic_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    topic = _tracker().get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    summary = _tracker().generate_summary(topic_id)
    return {"topic": topic["name"], "summary": summary}


@router.get("/api/topics/{topic_id}/streams")
def get_streams(topic_id: str, x_api_key: str = Header(None)):
    _auth(x_api_key)
    topic = _tracker().get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    streams = _tracker().get_live_streams_for_topic(topic)
    return {"topic": topic["name"], "streams": streams}


@router.post("/api/topics/detect")
def detect_topics(body: DetectTopicsRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    topic_ids, regions = _tracker().detect_topics_in_text(body.text)
    streams = _tracker().get_streams_for_regions(regions)
    topics = [_tracker().get_topic(tid) for tid in topic_ids if _tracker().get_topic(tid)]
    return {
        "matched_topics": [{"id": t["id"], "name": t["name"], "priority": t["priority"]} for t in topics],
        "detected_regions": regions,
        "recommended_streams": streams,
    }


@router.post("/api/topics/osint-sweep")
def process_sweep(body: OsintSweepRequest, x_api_key: str = Header(None)):
    _auth(x_api_key)
    alerts = _tracker().process_osint_sweep(body.sweep)
    return {"alerts_generated": len(alerts), "alerts": alerts}


@router.post("/api/topics/drive-file")
def process_drive_file(body: LinkDriveRequest, x_api_key: str = Header(None)):
    """Auto-detecta a qué temas corresponde un archivo de Drive y los vincula."""
    _auth(x_api_key)
    linked = _tracker().process_new_drive_file({
        "file_id": body.file_id,
        "name": body.name,
        "mime_type": body.mime_type,
        "description": body.description,
        "transcript": body.transcript,
        "drive_url": body.drive_url,
    })
    return {"ok": True, "linked_to_topics": linked, "topics_count": len(linked)}
