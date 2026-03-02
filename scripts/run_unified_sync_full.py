from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.unified_sync_service import run_unified_sync
from scripts.ai_context_tracker import update_ai_context_state


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

LOGS = ROOT / "logs"
LOCK_PATH = LOGS / "sync_unified.lock"
STATUS_PATH = LOGS / "sync_unified_status.json"
REPORT_PATH = LOGS / "sync_unified_last.json"
ALERTS_PATH = LOGS / "sync_unified_alerts.jsonl"


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_channels() -> list[str]:
    raw = (os.getenv("NEXO_FULL_YOUTUBE_CHANNELS", "") or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_alert(payload: dict) -> None:
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _notify_webhook(payload: dict) -> None:
    webhook = (os.getenv("NEXO_ALERT_WEBHOOK", "") or "").strip()
    if not webhook:
        return
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urlrequest.Request(webhook, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urlrequest.urlopen(req, timeout=8):
            pass
    except Exception:
        pass


def _summary(result: dict) -> dict:
    gp = result.get("google_photos", {})
    gd = result.get("google_drive", {})
    od = result.get("onedrive", {})
    yt = result.get("youtube", {})
    return {
        "google_photos": {
            "imported": gp.get("imported", 0),
            "skipped": gp.get("skipped", 0),
            "errors": gp.get("errors", 0),
        },
        "google_drive": {
            "analyzed": gd.get("analyzed", 0),
            "classified": gd.get("classified", 0),
            "skipped": gd.get("skipped", 0),
            "errors": gd.get("errors", 0),
        },
        "onedrive": {
            "imported": od.get("imported", 0),
            "skipped": od.get("skipped", 0),
            "errors": od.get("errors", 0),
        },
        "youtube": {
            "processed": yt.get("processed", 0),
            "skipped": yt.get("skipped", 0),
            "errors": yt.get("errors", 0),
        },
    }


def _has_errors(summary: dict) -> bool:
    return any(int((section or {}).get("errors", 0) or 0) > 0 for section in summary.values())


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)

    try:
        lock_fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        os.close(lock_fd)
    except FileExistsError:
        _write_json(
            STATUS_PATH,
            {
                "status": "already_running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Ya existe una sincronización unificada en ejecución",
            },
        )
        log.info("already_running")
        return 2

    request_payload = {
        "dry_run": _env_bool("NEXO_FULL_DRY_RUN", False),
        "photos_limit": _env_int("NEXO_FULL_PHOTOS_LIMIT", 50),
        "drive_limit": _env_int("NEXO_FULL_DRIVE_LIMIT", 300),
        "onedrive_limit": _env_int("NEXO_FULL_ONEDRIVE_LIMIT", 100),
        "onedrive_max_mb": _env_int("NEXO_FULL_ONEDRIVE_MAX_MB", 50),
        "youtube_per_channel": _env_int("NEXO_FULL_YT_PER_CHANNEL", 10),
        "youtube_channels": _env_channels(),
        "drive_include_trashed": _env_bool("NEXO_FULL_DRIVE_INCLUDE_TRASHED", True),
        "drive_full_scan": _env_bool("NEXO_FULL_DRIVE_FULL_SCAN", True),
        "drive_auto_rename": _env_bool("NEXO_FULL_DRIVE_AUTO_RENAME", True),
        "retry_attempts": _env_int("NEXO_FULL_RETRY_ATTEMPTS", 3),
        "retry_backoff_seconds": _env_float("NEXO_FULL_RETRY_BACKOFF_SECONDS", 1.2),
    }
    full_run_attempts = max(1, _env_int("NEXO_FULL_RUN_ATTEMPTS", 2))

    try:
        last_exc = None
        result = None
        used_attempt = 0
        for run_attempt in range(1, full_run_attempts + 1):
            used_attempt = run_attempt
            _write_json(
                STATUS_PATH,
                {
                    "status": "running",
                    "pid": os.getpid(),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "run_attempt": run_attempt,
                    "max_run_attempts": full_run_attempts,
                    "request": request_payload,
                },
            )
            try:
                result = run_unified_sync(
                    dry_run=request_payload["dry_run"],
                    photos_limit=request_payload["photos_limit"],
                    drive_limit=request_payload["drive_limit"],
                    onedrive_limit=request_payload["onedrive_limit"],
                    onedrive_max_mb=request_payload["onedrive_max_mb"],
                    youtube_per_channel=request_payload["youtube_per_channel"],
                    youtube_channels=request_payload["youtube_channels"],
                    drive_include_trashed=request_payload["drive_include_trashed"],
                    drive_full_scan=request_payload["drive_full_scan"],
                    drive_auto_rename=request_payload["drive_auto_rename"],
                    retry_attempts=request_payload["retry_attempts"],
                    retry_backoff_seconds=request_payload["retry_backoff_seconds"],
                )
                break
            except Exception as exc:
                last_exc = exc
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "sync_unified_runner_retry",
                    "run_attempt": run_attempt,
                    "max_run_attempts": full_run_attempts,
                    "error": str(exc),
                }
                _append_alert(alert)
                _notify_webhook(alert)
                if run_attempt >= full_run_attempts:
                    raise

        if result is None and last_exc is not None:
            raise last_exc
        if result is None:
            raise RuntimeError("run_unified_sync no retornó resultado")

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ok": bool(result.get("ok", False)),
            "request": request_payload,
            "summary": _summary(result),
            "result": result,
        }
        _write_json(REPORT_PATH, payload)
        if payload["summary"] and _has_errors(payload["summary"]):
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "sync_unified_completed_with_errors",
                "summary": payload["summary"],
                "report_path": str(REPORT_PATH),
            }
            _append_alert(alert)
            _notify_webhook(alert)

        for item in (result.get("alerts") or []):
            _append_alert(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "sync_unified_internal_alert",
                    "payload": item,
                }
            )

        _write_json(
            STATUS_PATH,
            {
                "status": "done",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "run_attempt": used_attempt,
                "max_run_attempts": full_run_attempts,
                "summary": payload["summary"],
                "report_path": str(REPORT_PATH),
            },
        )
        try:
            update_ai_context_state()
        except Exception as ctx_exc:
            log.warning("No fue posible actualizar contexto IA automático: %s", ctx_exc)
        log.info(json.dumps(payload["summary"], ensure_ascii=False))
        log.info(f"Reporte: {REPORT_PATH}")
        return 0
    except Exception as exc:
        _write_json(
            STATUS_PATH,
            {
                "status": "error",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "sync_unified_runner_error",
            "error": str(exc),
        }
        _append_alert(alert)
        _notify_webhook(alert)
        try:
            update_ai_context_state()
        except Exception as ctx_exc:
            log.warning("No fue posible actualizar contexto IA automático tras error: %s", ctx_exc)
        raise
    finally:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
