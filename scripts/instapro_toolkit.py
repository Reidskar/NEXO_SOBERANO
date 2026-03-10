#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PACKAGE = "com.instapro2.android"


def detect_adb() -> str:
    in_path = shutil.which("adb")
    if in_path:
        return in_path

    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        local / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    winget_root = local / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        matches = list(winget_root.glob("Google.PlatformTools*/*/adb.exe"))
        if matches:
            return str(matches[0])

    return ""


def run(cmd: List[str], timeout: int = 25) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except Exception as exc:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(exc)}


def adb_shell(adb: str, command: str, timeout: int = 25) -> Dict[str, Any]:
    return run([adb, "shell", command], timeout=timeout)


def ensure_device(adb: str) -> str:
    devices = run([adb, "devices"])
    if not devices["ok"]:
        return ""
    for line in devices["stdout"].splitlines()[1:]:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return ""


def battery_temp_c(battery_dump: str) -> float | None:
    m = re.search(r"temperature:\s*(\d+)", battery_dump)
    if not m:
        return None
    return int(m.group(1)) / 10.0


def collect_status(adb: str) -> Dict[str, Any]:
    package_info = adb_shell(adb, f"dumpsys package {PACKAGE}", timeout=35)
    proc = adb_shell(adb, f"pidof {PACKAGE}")
    top = adb_shell(adb, "top -n 1 -b | head -n 25")
    thermal = adb_shell(adb, "dumpsys thermalservice", timeout=35)
    battery = adb_shell(adb, "dumpsys battery")
    appops_bg = adb_shell(adb, f"cmd appops get {PACKAGE} RUN_IN_BACKGROUND")
    appops_any_bg = adb_shell(adb, f"cmd appops get {PACKAGE} RUN_ANY_IN_BACKGROUND")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "package": PACKAGE,
        "pid": proc.get("stdout", ""),
        "battery_temp_c": battery_temp_c(battery.get("stdout", "")),
        "bg_policy": {
            "RUN_IN_BACKGROUND": appops_bg.get("stdout", ""),
            "RUN_ANY_IN_BACKGROUND": appops_any_bg.get("stdout", ""),
        },
        "snapshots": {
            "top": top,
            "thermal": {
                "ok": thermal.get("ok", False),
                "stdout": thermal.get("stdout", "")[:2000],
                "stderr": thermal.get("stderr", ""),
            },
            "battery": {
                "ok": battery.get("ok", False),
                "stdout": battery.get("stdout", "")[:2000],
                "stderr": battery.get("stderr", ""),
            },
            "package_info": {
                "ok": package_info.get("ok", False),
                "stdout": package_info.get("stdout", "")[:3000],
                "stderr": package_info.get("stderr", ""),
            },
        },
    }


def apply_safe_profile(adb: str) -> Dict[str, Any]:
    actions = {
        "run_in_background": adb_shell(adb, f"cmd appops set {PACKAGE} RUN_IN_BACKGROUND ignore"),
        "run_any_in_background": adb_shell(adb, f"cmd appops set {PACKAGE} RUN_ANY_IN_BACKGROUND ignore"),
        "force_stop": adb_shell(adb, f"am force-stop {PACKAGE}"),
    }
    return actions


def apply_normal_profile(adb: str) -> Dict[str, Any]:
    actions = {
        "run_in_background": adb_shell(adb, f"cmd appops set {PACKAGE} RUN_IN_BACKGROUND allow"),
        "run_any_in_background": adb_shell(adb, f"cmd appops set {PACKAGE} RUN_ANY_IN_BACKGROUND allow"),
    }
    return actions


def monitor(adb: str, seconds: int, interval: int) -> Dict[str, Any]:
    samples: List[Dict[str, Any]] = []
    loops = max(1, seconds // max(1, interval))

    for _ in range(loops):
        top = adb_shell(adb, f"top -n 1 -b | grep {PACKAGE}")
        battery = adb_shell(adb, "dumpsys battery")
        thermal = adb_shell(adb, "dumpsys thermalservice")
        samples.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "top": top.get("stdout", ""),
                "battery_temp_c": battery_temp_c(battery.get("stdout", "")),
                "thermal_status_line": next(
                    (line for line in thermal.get("stdout", "").splitlines() if "Thermal Status:" in line),
                    "",
                ),
            }
        )
        time.sleep(interval)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "package": PACKAGE,
        "seconds": seconds,
        "interval": interval,
        "samples": samples,
    }


def save_report(prefix: str, payload: Dict[str, Any]) -> Path:
    out_dir = Path("reports/security")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"{prefix}_{ts}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Toolkit externo para InstaPro (sin modificar APK)")
    parser.add_argument("command", choices=["status", "safe-profile", "normal-profile", "monitor", "restart"])
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--interval", type=int, default=15)
    args = parser.parse_args()

    adb = detect_adb()
    if not adb:
        log.info("❌ ADB no detectado.")
        return 1

    serial = ensure_device(adb)
    if not serial:
        log.info("❌ No hay dispositivo ADB autorizado.")
        return 2

    if args.command == "status":
        report = collect_status(adb)
        out = save_report("instapro_status", report)
        log.info(f"✅ Status guardado: {out}")
        log.info(json.dumps({"pid": report.get("pid"), "battery_temp_c": report.get("battery_temp_c")}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "safe-profile":
        result = apply_safe_profile(adb)
        out = save_report("instapro_safe_profile", {"timestamp": datetime.now(timezone.utc).isoformat(), "actions": result})
        log.info(f"✅ Perfil seguro aplicado: {out}")
        return 0

    if args.command == "normal-profile":
        result = apply_normal_profile(adb)
        out = save_report("instapro_normal_profile", {"timestamp": datetime.now(timezone.utc).isoformat(), "actions": result})
        log.info(f"✅ Perfil normal aplicado: {out}")
        return 0

    if args.command == "restart":
        stop = adb_shell(adb, f"am force-stop {PACKAGE}")
        start = adb_shell(adb, f"monkey -p {PACKAGE} -c android.intent.category.LAUNCHER 1")
        out = save_report("instapro_restart", {"timestamp": datetime.now(timezone.utc).isoformat(), "stop": stop, "start": start})
        log.info(f"✅ Reinicio ejecutado: {out}")
        return 0

    if args.command == "monitor":
        result = monitor(adb, seconds=args.seconds, interval=args.interval)
        out = save_report("instapro_monitor", result)
        log.info(f"✅ Monitor guardado: {out}")
        if result["samples"]:
            log.info(json.dumps(result["samples"][-1], ensure_ascii=False, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
