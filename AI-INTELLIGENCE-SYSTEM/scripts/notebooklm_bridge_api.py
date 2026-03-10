from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


APP_NAME = "notebooklm-bridge"
API_KEY = os.getenv("NEXO_BRIDGE_API_KEY", "NEXO_LOCAL_2026_OK")
MODE = os.getenv("NEXO_BRIDGE_MODE", "dry-run")
JOBS: Dict[str, Dict[str, Any]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_key(x_nexo_api_key: Optional[str]) -> None:
    if API_KEY and (x_nexo_api_key or "") != API_KEY:
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


app = FastAPI(title=f"{APP_NAME} API", version="0.1.0")


class NotebookAdapter:
    def __init__(self, mode: str):
        self.mode = mode

    def create_notebook(self, name: str, description: str, tags: List[str]) -> Dict[str, Any]:
        notebook_id = f"nb_{uuid.uuid4().hex[:10]}"
        return {
            "id": notebook_id,
            "name": name,
            "description": description,
            "tags": tags,
            "created_at": utc_now(),
        }

    def add_source(self, notebook_id: str, source_type: str, source_ref: str, title: Optional[str]) -> Dict[str, Any]:
        source_id = f"src_{uuid.uuid4().hex[:10]}"
        return {
            "id": source_id,
            "notebook_id": notebook_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "title": title,
            "ingested_at": utc_now(),
        }

    def generate_summary(self, notebook_id: str, objective: str, strict_evidence: bool) -> Dict[str, Any]:
        return {
            "status": "INSUFFICIENT_EVIDENCE" if strict_evidence else "DRAFT",
            "summary": "Modo dry-run: conecta notebooklm-py para obtener resumen real con citas.",
            "citations": [],
            "confidence": 0.0,
            "notebook_id": notebook_id,
            "objective": objective,
            "generated_at": utc_now(),
        }


adapter = NotebookAdapter(MODE)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": APP_NAME,
        "mode": MODE,
        "timestamp": utc_now(),
        "jobs_total": len(JOBS),
    }


@app.post("/notebooks/create")
def create_notebook(payload: NotebookCreateRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    require_key(x_nexo_api_key)
    notebook = adapter.create_notebook(payload.name, payload.description, payload.tags)
    return {
        "ok": True,
        "mode": MODE,
        "notebook": notebook,
    }


@app.post("/notebooks/source/add")
def add_source(payload: AddSourceRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    require_key(x_nexo_api_key)
    source = adapter.add_source(payload.notebook_id, payload.source_type, payload.source_ref, payload.title)
    return {
        "ok": True,
        "mode": MODE,
        "source": source,
        "note": "En modo dry-run no se invoca notebooklm-py real; solo valida contratos y flujo.",
    }


@app.post("/drive/sync-folder")
def sync_drive_folder(payload: DriveSyncRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    require_key(x_nexo_api_key)
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    JOBS[job_id] = {
        "job_id": job_id,
        "folder_id": payload.folder_id,
        "notebook_id": payload.notebook_id,
        "max_files": payload.max_files,
        "status": "queued",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "processed": 0,
    }
    return {
        "ok": True,
        "mode": MODE,
        "job": JOBS[job_id],
        "guardrails": {
            "idempotency": "by folder_id + notebook_id + day",
            "retry_policy": "3 retries, exponential backoff",
            "dead_letter": "logs/notebooklm_bridge_deadletter.jsonl",
        },
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str, x_nexo_api_key: Optional[str] = Header(default=None)):
    require_key(x_nexo_api_key)
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job": job}


@app.post("/summaries/generate")
def generate_summary(payload: SummaryRequest, x_nexo_api_key: Optional[str] = Header(default=None)):
    require_key(x_nexo_api_key)
    result = adapter.generate_summary(payload.notebook_id, payload.objective, payload.strict_evidence)
    response: Dict[str, Any] = {
        "ok": True,
        "mode": MODE,
        "notebook_id": payload.notebook_id,
        "objective": payload.objective,
        "strict_evidence": payload.strict_evidence,
        "result": result,
    }
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8011)
