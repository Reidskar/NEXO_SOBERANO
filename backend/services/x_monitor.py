"""Monitor X/Grok -> NEXO (cuarentena Drive + estado incremental)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from backend.services.x_publisher import fetch_mentions, search_x_recent
from services.connectors.google_connector import ensure_drive_folder_path, upload_bytes_to_drive


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _logs_dir() -> Path:
    path = _workspace_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return _logs_dir() / "x_monitor_state.json"


def _status_path() -> Path:
    return _logs_dir() / "x_monitor_status.json"


def _report_path() -> Path:
    return _logs_dir() / "x_monitor_last.json"


def _safe_json_read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_json_write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _upload_items_to_drive(items: List[Dict], username: str) -> Dict:
    now = datetime.now(timezone.utc)
    path_parts = [
        "NEXO_SOBERANO",
        "Cuarentena",
        "Aportes_X",
        str(now.year),
        f"{now.month:02d}",
    ]
    folder_id = ensure_drive_folder_path(path_parts, parent_id="root")

    uploaded: List[Dict] = []
    for item in items:
        source = str(item.get("source") or "x")
        tweet_id = str(item.get("id") or "")
        seed = f"{source}|{username}|{tweet_id}|{item.get('created_at') or ''}"
        aporte_id = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]

        payload = {
            "aporte_id": aporte_id,
            "source": source,
            "username": username,
            "tweet": item,
            "ingested_at": now.isoformat(),
            "status": "cuarentena",
        }
        filename = f"x_{source}_{tweet_id or aporte_id}.json"
        up = upload_bytes_to_drive(
            file_bytes=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            filename=filename,
            mime_type="application/json",
            parent_id=folder_id,
            app_properties={
                "nexo_type": "x_item",
                "source": source,
                "aporte_id": aporte_id,
                "tweet_id": tweet_id,
                "status": "cuarentena",
            },
        )
        file_id = up.get("id")
        uploaded.append(
            {
                "source": source,
                "tweet_id": tweet_id,
                "aporte_id": aporte_id,
                "file_id": file_id,
                "drive_link": f"https://drive.google.com/file/d/{file_id}/view" if file_id else None,
            }
        )

    return {"folder_id": folder_id, "uploaded": uploaded}


def monitor_x_once(limit: int = 20, username: Optional[str] = None) -> Dict:
    limit = max(1, min(int(limit), 100))
    started_at = datetime.now(timezone.utc).isoformat()
    state = _safe_json_read(_state_path())

    _safe_json_write(
        _status_path(),
        {
            "status": "running",
            "started_at": started_at,
            "limit": limit,
            "username": username,
        },
    )

    errors: List[str] = []
    mentions_data = {"mentions": [], "newest_id": state.get("mentions_since_id")}
    grok_data = {"tweets": [], "newest_id": state.get("grok_since_id")}

    try:
        mentions_data = fetch_mentions(limit=limit, since_id=state.get("mentions_since_id"), username=username)
    except Exception as exc:
        errors.append(f"mentions_error: {exc}")

    resolved_username = mentions_data.get("username") or username or os.getenv("X_BOT_USERNAME") or os.getenv("X_USERNAME") or "unknown"
    grok_query = f"from:grok to:{resolved_username} -is:retweet"

    try:
        grok_data = search_x_recent(query=grok_query, limit=limit, since_id=state.get("grok_since_id"))
    except Exception as exc:
        errors.append(f"grok_search_error: {exc}")

    ingest_items: List[Dict] = []
    for item in (mentions_data.get("mentions") or []):
        row = dict(item)
        row["source"] = "mention"
        ingest_items.append(row)

    for item in (grok_data.get("tweets") or []):
        row = dict(item)
        row["source"] = "grok_reply"
        ingest_items.append(row)

    drive_result = None
    if ingest_items:
        try:
            drive_result = _upload_items_to_drive(ingest_items, username=resolved_username)
        except Exception as exc:
            errors.append(f"drive_upload_error: {exc}")

    new_state = {
        "mentions_since_id": mentions_data.get("newest_id") or state.get("mentions_since_id"),
        "grok_since_id": grok_data.get("newest_id") or state.get("grok_since_id"),
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "username": resolved_username,
    }
    _safe_json_write(_state_path(), new_state)

    report = {
        "ok": len(errors) == 0,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "username": resolved_username,
        "limit": limit,
        "counts": {
            "mentions": len(mentions_data.get("mentions") or []),
            "grok_replies": len(grok_data.get("tweets") or []),
            "ingested": len(ingest_items),
        },
        "drive": drive_result,
        "errors": errors,
        "state": new_state,
    }

    _safe_json_write(_report_path(), report)
    _safe_json_write(
        _status_path(),
        {
            "status": "done" if report["ok"] else "error",
            "finished_at": report["finished_at"],
            "counts": report["counts"],
            "errors": errors,
        },
    )

    return report


def run_x_monitor_loop(interval_seconds: int = 900, limit: int = 20, username: Optional[str] = None) -> None:
    interval_seconds = max(60, int(interval_seconds))
    while True:
        try:
            monitor_x_once(limit=limit, username=username)
        except Exception as exc:
            _safe_json_write(
                _status_path(),
                {
                    "status": "error",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "errors": [str(exc)],
                },
            )
        time.sleep(interval_seconds)
