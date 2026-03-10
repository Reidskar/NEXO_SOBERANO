#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


def run(cmd: List[str], timeout: int = 40) -> Dict[str, Any]:
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


def detect_adb() -> str:
    in_path = shutil.which("adb")
    if in_path:
        return in_path

    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        local / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        local / "Microsoft" / "WinGet" / "Packages",
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


def parse_android_packages(stdout: str) -> List[str]:
    packages = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            packages.append(line.replace("package:", "", 1).strip())
    return sorted(set(packages))


def parse_winget_list(stdout: str) -> List[str]:
    rows = [line.rstrip() for line in stdout.splitlines() if line.strip()]
    apps: List[str] = []
    for row in rows:
        if row.startswith("Nombre") or row.startswith("---") or row.startswith("-"):
            continue
        if "ARP\\" in row or "\\" in row:
            name = row.split("  ")[0].strip()
            if name:
                apps.append(name)
        else:
            parts = [p for p in row.split("  ") if p.strip()]
            if parts:
                apps.append(parts[0].strip())
    return sorted(set(apps))


def risk_tags(packages: List[str]) -> Dict[str, List[str]]:
    keys = {
        "remote_control": ["anydesk", "airdroid", "teamviewer", "remote"],
        "vpn": ["vpn", "wireguard", "tailscale", "proton"],
        "finance_crypto": ["bank", "wallet", "crypto", "binance", "coin", "xtb"],
        "social_heavy": ["instagram", "telegram", "facebook", "tiktok", "instapro"],
    }
    out: Dict[str, List[str]] = {}
    for category, words in keys.items():
        found = [p for p in packages if any(w in p.lower() for w in words)]
        if found:
            out[category] = found
    return out


def main() -> int:
    adb = detect_adb()
    android_packages: List[str] = []
    serial = ""

    if adb:
        devices = run([adb, "devices"])
        if devices["ok"]:
            for line in devices["stdout"].splitlines()[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    serial = parts[0]
                    break
        if serial:
            pkg_out = run([adb, "shell", "pm", "list", "packages", "-3"], timeout=60)
            if pkg_out["ok"]:
                android_packages = parse_android_packages(pkg_out["stdout"])

    winget = run(["winget", "list", "--source", "winget"], timeout=80)
    pc_apps = parse_winget_list(winget["stdout"]) if winget["ok"] else []

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phone": {
            "connected": bool(serial),
            "serial": serial,
            "apps_count": len(android_packages),
            "apps": android_packages,
            "risk_tags": risk_tags(android_packages),
        },
        "pc": {
            "apps_count": len(pc_apps),
            "apps_sample": pc_apps[:250],
        },
    }

    reports_dir = Path("reports/security")
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = reports_dir / f"app_inventory_{ts}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    docs_dir = Path("documentos")
    docs_dir.mkdir(parents=True, exist_ok=True)
    md_path = docs_dir / "APP_INVENTORY_CONTEXT.md"
    md_lines = [
        "# Contexto de Apps (PC + Teléfono)",
        "",
        f"Generado: {report['timestamp']}",
        "",
        "## Teléfono Android",
        f"- Conectado: {report['phone']['connected']}",
        f"- Serial: {report['phone']['serial'] or 'N/A'}",
        f"- Apps detectadas (3rd party): {report['phone']['apps_count']}",
        "",
        "### Tags de riesgo/operación",
    ]
    for category, items in report["phone"]["risk_tags"].items():
        md_lines.append(f"- {category}: {len(items)}")
    md_lines += [
        "",
        "### Top apps Android (primeras 80)",
    ]
    for app in report["phone"]["apps"][:80]:
        md_lines.append(f"- {app}")

    md_lines += [
        "",
        "## PC (winget)",
        f"- Apps detectadas: {report['pc']['apps_count']}",
        "",
        "### Apps PC (muestra)",
    ]
    for app in report["pc"]["apps_sample"][:80]:
        md_lines.append(f"- {app}")

    md_lines += [
        "",
        "## Uso para IA",
        "- Este archivo puede ser indexado por el pipeline RAG para adaptar respuestas y sugerencias a tu stack real de apps.",
        f"- Fuente JSON completa: {json_path.as_posix()}",
    ]

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    log.info(f"✅ Inventario generado: {json_path}")
    log.info(f"✅ Contexto IA actualizado: {md_path}")
    print(json.dumps({
        "phone_connected": bool(serial),
        "phone_apps": len(android_packages),
        "pc_apps": len(pc_apps),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
