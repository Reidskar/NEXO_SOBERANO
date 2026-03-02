from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys
import os
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.unified_sync_service import run_unified_sync


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


LOCK_PATH = Path("logs") / "sync_drive.lock"
STATUS_PATH = Path("logs") / "sync_drive_status.json"
REPORT_PATH = Path("logs") / "sync_drive_last.json"


def _write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _acquire_lock() -> int:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(str(LOCK_PATH), flags)
    os.write(fd, str(os.getpid()).encode("utf-8"))
    return fd


def _release_lock(fd: int) -> None:
    try:
        os.close(fd)
    except Exception:
        pass
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass


def main() -> int:
    lock_fd = None
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        lock_fd = _acquire_lock()
    except FileExistsError:
        _write_status(
            {
                "status": "already_running",
                "timestamp": started_at,
                "message": "Ya existe una corrida de clasificación en ejecución.",
            }
        )
        log.info("already_running")
        return 2

    try:
        _write_status(
            {
                "status": "running",
                "pid": os.getpid(),
                "started_at": started_at,
                "report_path": str(REPORT_PATH),
            }
        )

        result = run_unified_sync(
            dry_run=False,
            photos_limit=0,
            drive_limit=500,
            onedrive_limit=0,
            onedrive_max_mb=50,
            youtube_per_channel=0,
            youtube_channels=[],
            drive_include_trashed=True,
            drive_full_scan=True,
            drive_auto_rename=True,
            retry_attempts=3,
            retry_backoff_seconds=1.2,
        )

        out = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ok": bool(result.get("ok", False)),
            "summary": {
                "google_drive_classified": result.get("google_drive", {}).get("classified", 0),
                "google_drive_skipped": result.get("google_drive", {}).get("skipped", 0),
                "google_drive_errors": result.get("google_drive", {}).get("errors", 0),
            },
            "result": result,
        }

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_status(
            {
                "status": "done",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "summary": out["summary"],
                "report_path": str(REPORT_PATH),
            }
        )
        log.info(json.dumps(out["summary"], ensure_ascii=False))
        log.info(f"Reporte: {REPORT_PATH}")
        return 0
    except Exception as exc:
        _write_status(
            {
                "status": "error",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        raise
    finally:
        if lock_fd is not None:
            _release_lock(lock_fd)


if __name__ == "__main__":
    raise SystemExit(main())
