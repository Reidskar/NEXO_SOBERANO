from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib import request
import os

BASE_URL = "http://127.0.0.1:8000"
LOCK_PATH = Path("logs") / "sync_drive_api.lock"
STATUS_PATH = Path("logs") / "sync_drive_status.json"


def main() -> int:
    Path("logs").mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        os.close(fd)
    except FileExistsError:
        STATUS_PATH.write_text(
            json.dumps(
                {
                    "status": "already_running",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Ya existe una clasificación API en ejecución",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        log.info("already_running")
        return 2

    try:
        batch_limit = int(os.getenv("NEXO_DRIVE_BATCH_LIMIT", "20"))
        max_rounds = int(os.getenv("NEXO_DRIVE_BATCH_ROUNDS", "30"))
        timeout = int(os.getenv("NEXO_DRIVE_BATCH_TIMEOUT", "180"))
        include_trashed = (os.getenv("NEXO_DRIVE_INCLUDE_TRASHED", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
        full_scan = (os.getenv("NEXO_DRIVE_FULL_SCAN", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
        auto_rename = (os.getenv("NEXO_DRIVE_AUTO_RENAME", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
        retry_attempts = int(os.getenv("NEXO_DRIVE_RETRY_ATTEMPTS", "3"))
        retry_backoff_seconds = float(os.getenv("NEXO_DRIVE_RETRY_BACKOFF_SECONDS", "1.2"))

        totals = {"analyzed": 0, "classified": 0, "skipped": 0, "errors": 0}
        rounds = []

        for round_idx in range(1, max_rounds + 1):
            payload = {
                "dry_run": False,
                "photos_limit": 0,
                "drive_limit": batch_limit,
                "onedrive_limit": 0,
                "onedrive_max_mb": 50,
                "youtube_per_channel": 0,
                "youtube_channels": [],
                "drive_include_trashed": include_trashed,
                "drive_full_scan": full_scan,
                "drive_auto_rename": auto_rename,
                "retry_attempts": retry_attempts,
                "retry_backoff_seconds": retry_backoff_seconds,
            }

            STATUS_PATH.write_text(
                json.dumps(
                    {
                        "status": "running",
                        "round": round_idx,
                        "max_rounds": max_rounds,
                        "batch_limit": batch_limit,
                        "totals": totals,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            body = json.dumps(payload).encode("utf-8")
            req = request.Request(
                f"{BASE_URL}/agente/sync/unificado",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            with request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            result = data.get("result", {})
            drive = result.get("google_drive", {})
            analyzed = int(drive.get("analyzed", 0) or 0)
            classified = int(drive.get("classified", 0) or 0)
            skipped = int(drive.get("skipped", 0) or 0)
            errors = int(drive.get("errors", 0) or 0)

            totals["analyzed"] += analyzed
            totals["classified"] += classified
            totals["skipped"] += skipped
            totals["errors"] += errors

            rounds.append(
                {
                    "round": round_idx,
                    "ok": bool(data.get("ok")),
                    "analyzed": analyzed,
                    "classified": classified,
                    "skipped": skipped,
                    "errors": errors,
                }
            )

            if classified == 0:
                break

        out = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": {
                "batch_limit": batch_limit,
                "max_rounds": max_rounds,
                "timeout": timeout,
            },
            "totals": totals,
            "rounds": rounds,
        }
        out_path = Path("logs") / "sync_drive_last.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        STATUS_PATH.write_text(
            json.dumps(
                {
                    "status": "done",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "totals": totals,
                    "report_path": str(out_path),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        log.info(json.dumps({"ok": True, "totals": totals}, ensure_ascii=False))
        log.info(f"Reporte: {out_path}")
        return 0
    finally:
        LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
