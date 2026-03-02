"""Conector práctico para Google Stitch (modo webhook/API configurable)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = LOGS_DIR / "google_stitch_config.json"


def _safe_read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _masked(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def get_stitch_config() -> Dict:
    file_cfg = _safe_read(CONFIG_PATH)
    webhook_url = (os.getenv("GOOGLE_STITCH_WEBHOOK_URL", "") or file_cfg.get("webhook_url") or "").strip()
    api_key = (os.getenv("GOOGLE_STITCH_API_KEY", "") or file_cfg.get("api_key") or "").strip()

    return {
        "configured": bool(webhook_url),
        "webhook_url": webhook_url,
        "api_key": api_key,
        "webhook_url_masked": _masked(webhook_url),
        "api_key_masked": _masked(api_key),
        "source": "env" if os.getenv("GOOGLE_STITCH_WEBHOOK_URL") else ("file" if file_cfg else "none"),
    }


def save_stitch_config(webhook_url: str, api_key: Optional[str] = None) -> Dict:
    payload = {
        "webhook_url": (webhook_url or "").strip(),
        "api_key": (api_key or "").strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _safe_write(CONFIG_PATH, payload)
    return get_stitch_config()


def test_stitch_connection() -> Dict:
    cfg = get_stitch_config()
    if not cfg["configured"]:
        return {"ok": False, "status": "not_configured", "detail": "Falta GOOGLE_STITCH_WEBHOOK_URL"}

    event = {
        "event_type": "nexo_health_ping",
        "source": "nexo_soberano",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"status": "ok"},
    }
    return push_event_to_stitch(event)


def push_event_to_stitch(event: Dict) -> Dict:
    cfg = get_stitch_config()
    if not cfg["configured"]:
        return {"ok": False, "status": "not_configured", "detail": "Falta GOOGLE_STITCH_WEBHOOK_URL"}

    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    try:
        response = requests.post(
            cfg["webhook_url"],
            headers=headers,
            json=event,
            timeout=20,
        )
        return {
            "ok": response.ok,
            "status": "sent" if response.ok else "http_error",
            "http_status": response.status_code,
            "detail": response.text[:300] if not response.ok else "ok",
            "event_type": event.get("event_type"),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "request_error",
            "detail": str(exc),
            "event_type": event.get("event_type"),
        }
