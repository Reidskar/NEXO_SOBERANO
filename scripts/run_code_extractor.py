from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extractor_codigo import extract_project_context, save_result_json

LOGS = ROOT / "logs"
LOCK_PATH = LOGS / "extractor.lock"
STATUS_PATH = LOGS / "extractor_status.json"
REPORT_PATH = LOGS / "extractor_report.json"
OUTPUT_PATH = LOGS / "ai_context" / "contexto_nexo_soberano.txt"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
                "message": "Ya hay un extractor en ejecución",
            },
        )
        log.info("already_running")
        return 2

    try:
        _write_json(
            STATUS_PATH,
            {
                "status": "running",
                "pid": os.getpid(),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "output_file": str(OUTPUT_PATH),
            },
        )

        result = extract_project_context(
            root_dir=str(ROOT),
            output_file=str(OUTPUT_PATH),
        )
        save_result_json(result, str(REPORT_PATH))

        _write_json(
            STATUS_PATH,
            {
                "status": "done",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "output_file": result.output_file,
                "files_scanned": result.files_scanned,
                "files_included": result.files_included,
                "bytes_written": result.bytes_written,
                "report_path": str(REPORT_PATH),
            },
        )
        log.info(json.dumps({"ok": True, "output_file": result.output_file, "files_scanned": result.files_scanned}, ensure_ascii=False))
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
        raise
    finally:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
