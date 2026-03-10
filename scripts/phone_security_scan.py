#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


@dataclass
class CheckResult:
    ok: bool
    output: str
    error: str = ""


def run_cmd(cmd: list[str], timeout: int = 20) -> CheckResult:
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
        ok = proc.returncode == 0
        return CheckResult(ok=ok, output=(proc.stdout or "").strip(), error=(proc.stderr or "").strip())
    except Exception as exc:
        return CheckResult(ok=False, output="", error=str(exc))


def detect_adb_executable() -> str:
    adb_in_path = shutil.which("adb")
    if adb_in_path:
        return adb_in_path

    candidates = [
        Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
    ]

    for candidate in candidates[:2]:
        if candidate.exists():
            return str(candidate)

    winget_root = candidates[2]
    if winget_root.exists():
        matches = list(winget_root.glob("Google.PlatformTools*/*/adb.exe"))
        if matches:
            return str(matches[0])

    return ""


ADB_CMD = detect_adb_executable()


def adb_shell(command: str, timeout: int = 20) -> CheckResult:
    return run_cmd([ADB_CMD, "shell", command], timeout=timeout)


def parse_adb_device(serial: str | None) -> str:
    if serial:
        return serial

    devices = run_cmd([ADB_CMD, "devices"])
    if not devices.ok:
        return ""

    lines = [line.strip() for line in devices.output.splitlines() if line.strip()]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return ""


def collect_scan(mode: str) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    checks["adb_version"] = asdict(run_cmd(["adb", "version"]))
    checks["devices"] = asdict(run_cmd(["adb", "devices"]))

    checks["android_version"] = asdict(adb_shell("getprop ro.build.version.release"))
    checks["security_patch"] = asdict(adb_shell("getprop ro.build.version.security_patch"))
    checks["device_model"] = asdict(adb_shell("getprop ro.product.model"))
    checks["kernel"] = asdict(adb_shell("uname -a"))

    checks["battery"] = asdict(adb_shell("dumpsys battery"))
    checks["top_processes"] = asdict(adb_shell("top -n 1 -b | head -n 20"))
    checks["meminfo"] = asdict(adb_shell("dumpsys meminfo"))

    checks["unknown_sources"] = asdict(adb_shell("settings get secure install_non_market_apps"))
    checks["accessibility_enabled"] = asdict(adb_shell("settings get secure accessibility_enabled"))
    checks["enabled_accessibility_services"] = asdict(adb_shell("settings get secure enabled_accessibility_services"))
    checks["developer_options"] = asdict(adb_shell("settings get global development_settings_enabled"))

    checks["third_party_packages"] = asdict(adb_shell("pm list packages -3"))

    if mode == "full":
        checks["network_stats"] = asdict(adb_shell("dumpsys netstats"))
        checks["active_connections"] = asdict(adb_shell("cat /proc/net/tcp"))

    findings = []
    patch = checks["security_patch"]["output"].strip()
    if patch and patch not in {"", "null", "unknown"}:
        findings.append(f"Parche de seguridad detectado: {patch}")
    else:
        findings.append("No se pudo leer parche de seguridad")

    if checks["developer_options"]["output"].strip() == "1":
        findings.append("Developer options ACTIVADAS (revisar si es intencional)")

    if checks["accessibility_enabled"]["output"].strip() == "1":
        findings.append("Accesibilidad activada (verificar servicios autorizados)")

    top_sample = checks["top_processes"]["output"]
    if top_sample:
        findings.append("Top procesos capturado (revisar consumo anormal CPU)")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "findings": findings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Escaneo de seguridad Android (ADB)")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--output", default="reports/security")
    parser.add_argument("--serial", default="", help="Serial de dispositivo ADB (opcional)")
    args = parser.parse_args()

    if not ADB_CMD:
        log.info("❌ ADB no está instalado o no está en PATH.")
        log.info("Instala Android Platform Tools y vuelve a ejecutar.")
        return 1

    serial = parse_adb_device(args.serial or None)
    if not serial:
        log.info("❌ No hay dispositivo Android conectado/autorizado por ADB.")
        log.info("Conecta el teléfono por USB, habilita depuración USB y autoriza la huella RSA.")
        return 2

    if args.serial:
        run_cmd([ADB_CMD, "-s", args.serial, "get-state"])

    log.info(f"🔎 Escaneando dispositivo: {serial}")
    report = collect_scan(args.mode)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"phone_scan_{ts}.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"✅ Reporte generado: {out_file}")
    log.info("⚠️ Revisa findings y comparte el JSON si quieres análisis forense guiado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
