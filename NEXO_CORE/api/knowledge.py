from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from NEXO_CORE.middleware.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_BRIDGE_API_KEY = os.getenv("NEXO_BRIDGE_API_KEY", os.getenv("NEXO_API_KEY", ""))
_BRIDGE_MODE = os.getenv("NEXO_BRIDGE_MODE", "dry-run")
_JOBS: Dict[str, Dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_bridge_key(x_nexo_api_key: Optional[str]) -> None:
    if _BRIDGE_API_KEY and (x_nexo_api_key or "") != _BRIDGE_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


class NotebookCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    tags: List[str] = Field(default_factory=list)


class AddSourceRequest(BaseModel):
    notebook_id: str = Field(..., min_length=3, max_length=200)
    source_type: str = Field(default="drive_file", pattern="^(drive_file|url|text)$")
    source_ref: str = Field(..., min_length=3, max_length=2048)
    title: Optional[str] = Field(default=None, max_length=255)


class DriveSyncRequest(BaseModel):
    folder_id: str = Field(..., min_length=3, max_length=256)
    notebook_id: str = Field(..., min_length=3, max_length=200)
    max_files: int = Field(default=50, ge=1, le=500)


class SummaryRequest(BaseModel):
    notebook_id: str = Field(..., min_length=3, max_length=200)
    objective: str = Field(..., min_length=10, max_length=3000)
    strict_evidence: bool = Field(default=True)


@router.get("/health", dependencies=[Depends(enforce_rate_limit)])
async def knowledge_health():
    return {
        "ok": True,
        "service": "notebooklm-bridge-embedded",
        "mode": _BRIDGE_MODE,
        "jobs_total": len(_JOBS),
        "timestamp": _utc_now(),
    }


@router.post("/notebooks/create", dependencies=[Depends(enforce_rate_limit)])
async def notebooks_create(payload: NotebookCreateRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    _require_bridge_key(x_nexo_api_key)
    notebook = {
        "id": f"nb_{uuid.uuid4().hex[:10]}",
        "name": payload.name,
        "description": payload.description,
        "tags": payload.tags,
        "created_at": _utc_now(),
    }
    return {"ok": True, "mode": _BRIDGE_MODE, "notebook": notebook}


@router.post("/notebooks/source/add", dependencies=[Depends(enforce_rate_limit)])
async def notebooks_source_add(payload: AddSourceRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    _require_bridge_key(x_nexo_api_key)
    source = {
        "id": f"src_{uuid.uuid4().hex[:10]}",
        "notebook_id": payload.notebook_id,
        "source_type": payload.source_type,
        "source_ref": payload.source_ref,
        "title": payload.title,
        "ingested_at": _utc_now(),
    }
    return {
        "ok": True,
        "mode": _BRIDGE_MODE,
        "source": source,
        "note": "dry-run activo: implementar adaptador notebooklm-py en siguiente iteración",
    }


@router.post("/drive/sync-folder", dependencies=[Depends(enforce_rate_limit)])
async def drive_sync_folder(payload: DriveSyncRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    _require_bridge_key(x_nexo_api_key)
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    job = {
        "job_id": job_id,
        "folder_id": payload.folder_id,
        "notebook_id": payload.notebook_id,
        "max_files": payload.max_files,
        "status": "queued",
        "processed": 0,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    _JOBS[job_id] = job
    return {
        "ok": True,
        "mode": _BRIDGE_MODE,
        "job": job,
        "guardrails": {
            "idempotency": "folder_id+notebook_id+day",
            "retry_policy": "3 retries exponential",
            "dead_letter": "logs/notebooklm_bridge_deadletter.jsonl",
        },
    }


@router.get("/jobs/{job_id}", dependencies=[Depends(enforce_rate_limit)])
async def jobs_status(job_id: str, x_nexo_api_key: Optional[str] = Header(default=None)):
    _require_bridge_key(x_nexo_api_key)
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job": _JOBS[job_id]}


@router.post("/summaries/generate", dependencies=[Depends(enforce_rate_limit)])
async def summaries_generate(payload: SummaryRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    _require_bridge_key(x_nexo_api_key)
    result = {
        "status": "INSUFFICIENT_EVIDENCE" if payload.strict_evidence else "DRAFT",
        "summary": "Modo dry-run: conectar notebooklm-py/Playwright para resumen real con citas.",
        "citations": [],
        "confidence": 0.0,
        "generated_at": _utc_now(),
    }
    return {
        "ok": True,
        "mode": _BRIDGE_MODE,
        "notebook_id": payload.notebook_id,
        "objective": payload.objective,
        "strict_evidence": payload.strict_evidence,
        "result": result,
    }
