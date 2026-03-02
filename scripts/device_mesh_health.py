#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def run(cmd: list[str], timeout: int = 15) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": proc.returncode == 0, "stdout": (proc.stdout or "").strip(), "stderr": (proc.stderr or "").strip()}
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc)}


def http_get(url: str, timeout: int = 10) -> dict:
    req = Request(url, headers={"User-Agent": "NEXO-Mesh-Health/1.0"})
    try:
        with urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": r.status, "body": body[:2000]}
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except URLError as exc:
        return {"ok": False, "status": 0, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status": 0, "error": str(exc)}


def main() -> int:
    adb_path = r"C:\Users\Admn\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe"

    adb_devices = run([adb_path, "devices"])
    battery = run([adb_path, "shell", "dumpsys", "battery"])
    thermal = run([adb_path, "shell", "dumpsys", "thermalservice"])

    backend_root = http_get("http://localhost:8000/")
    backend_health = http_get("http://localhost:8000/api/health/")
    stream_health = http_get("http://localhost:8000/api/stream/status")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "adb_devices": adb_devices,
            "battery": battery,
            "thermal": {"ok": thermal.get("ok", False), "snippet": thermal.get("stdout", "")[:1200]},
            "backend_root": backend_root,
            "backend_health": backend_health,
            "stream_health": stream_health,
        },
    }

    out_dir = Path("reports/security")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"mesh_health_{ts}.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Mesh health: {out_file}")
    print(json.dumps({
        "adb_ok": adb_devices.get("ok"),
        "backend_ok": backend_root.get("ok"),
        "api_health_ok": backend_health.get("ok"),
        "stream_ok": stream_health.get("ok"),
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
