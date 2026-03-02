from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable


def load_seen(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_seen(path: Path, data: Dict[str, str]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_seen(path: Path, job_id: str, device_id: str) -> None:
    data = load_seen(path)
    data[job_id] = device_id
    save_seen(path, data)


def is_seen(path: Path, job_id: str) -> bool:
    return job_id in load_seen(path)


def append_csv(path: Path, row: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    fields = [
        "timestamp",
        "device_id",
        "job_id",
        "title",
        "company",
        "location",
        "score",
        "status",
        "detail_url",
        "apply_url",
        "reason",
    ]
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def append_google_sheet(
    enabled: bool,
    spreadsheet_id: str,
    service_account_json: str,
    rows: Iterable[Dict],
) -> None:
    if not enabled:
        return
    if not spreadsheet_id or not service_account_json:
        return
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(service_account_json, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.sheet1
        for row in rows:
            ws.append_row([
                row.get("timestamp", datetime.now(timezone.utc).isoformat()),
                row.get("device_id", ""),
                row.get("job_id", ""),
                row.get("title", ""),
                row.get("company", ""),
                row.get("location", ""),
                row.get("score", ""),
                row.get("status", ""),
                row.get("detail_url", ""),
                row.get("apply_url", ""),
                row.get("reason", ""),
            ])
    except Exception:
        return


def acquire_cycle_lock(lock_file: Path, device_id: str, stale_minutes: int = 90) -> bool:
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    if lock_file.exists():
        try:
            age_seconds = now.timestamp() - lock_file.stat().st_mtime
            if age_seconds > max(60, stale_minutes * 60):
                lock_file.unlink(missing_ok=True)
        except Exception:
            pass

    payload = {
        "device_id": device_id,
        "pid": os.getpid(),
        "locked_at": now.isoformat(),
    }

    try:
        with lock_file.open("x", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=2))
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def release_cycle_lock(lock_file: Path, device_id: str) -> None:
    if not lock_file.exists():
        return
    try:
        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
        owner = str(lock_data.get("device_id", ""))
        if owner and owner != device_id:
            return
    except Exception:
        pass

    try:
        lock_file.unlink(missing_ok=True)
    except Exception:
        return
