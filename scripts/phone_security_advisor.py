#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


RISKY_KEYWORDS = {
    "remote_access": ["anydesk", "airdroid", "teamviewer", "quicksupport", "remote"],
    "modified_social": ["instapro", "mod", "plus", "pro2"],
    "instrumentation": ["frida", "xposed", "magisk", "supersu"],
}


def latest_report(path_glob: str) -> str:
    matches = sorted(glob.glob(path_glob))
    if not matches:
        raise FileNotFoundError("No hay reportes de escaneo del teléfono.")
    return matches[-1]


def extract_battery_temp_c(battery_text: str) -> float | None:
    match = re.search(r"temperature:\s*([0-9]+)", battery_text)
    if not match:
        return None
    return int(match.group(1)) / 10.0


def detect_risky_packages(packages: List[str]) -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = {k: [] for k in RISKY_KEYWORDS}
    for package in packages:
        pkg_l = package.lower()
        for category, keys in RISKY_KEYWORDS.items():
            if any(keyword in pkg_l for keyword in keys):
                found[category].append(package)
    return {k: v for k, v in found.items() if v}


def top_cpu_processes(cpu_text: str, limit: int = 8) -> List[str]:
    lines = [line.strip() for line in cpu_text.splitlines() if line.strip()]
    result = []
    for line in lines:
        if re.match(r"^[0-9]+%", line) or re.search(r"\s[0-9]+\.?[0-9]*\s+[0-9]+\.?[0-9]*\s+.+", line):
            result.append(line)
        if len(result) >= limit:
            break
    return result


def build_recommendations(checks: Dict[str, Any], risky: Dict[str, List[str]], temp_c: float | None) -> List[str]:
    recs: List[str] = []

    if checks.get("unknown_sources", {}).get("output", "").strip() == "1":
        recs.append("Desactivar instalación de orígenes desconocidos y revisar sideload recientes.")

    if checks.get("developer_options", {}).get("output", "").strip() == "1":
        recs.append("Desactivar Opciones de desarrollador cuando no estés depurando para reducir superficie de ataque.")

    if checks.get("accessibility_enabled", {}).get("output", "").strip() == "1":
        recs.append("Auditar servicios de Accesibilidad; dejar solo los estrictamente necesarios.")

    if "remote_access" in risky:
        recs.append("Reducir apps de acceso remoto (AnyDesk/AirDroid/RemoteSupport) o limitar permisos en segundo plano.")

    if "modified_social" in risky:
        recs.append("Eliminar apps modificadas (ej. InstaPro) por riesgo de exfiltración y consumo elevado.")

    if temp_c is not None and temp_c >= 38.5:
        recs.append("Temperatura de batería alta para reposo (>38.5°C): limitar apps con CPU alta, refresco alto y brillo automático agresivo.")

    recs.append("Activar 2FA en cuentas críticas y revisar sesiones activas en Google/Meta/Telegram.")
    recs.append("Ejecutar escaneo full semanal y comparar dif de paquetes/servicios habilitados.")

    return recs


def main() -> int:
    parser = argparse.ArgumentParser(description="Asesor de seguridad/temperatura para reporte de teléfono")
    parser.add_argument("--report", default="", help="Ruta de reporte JSON. Si se omite, usa el más reciente.")
    parser.add_argument("--output", default="reports/security", help="Directorio de salida")
    args = parser.parse_args()

    report_path = args.report or latest_report("reports/security/phone_scan_*.json")
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    checks = data.get("checks", {})

    packages_text = checks.get("third_party_packages", {}).get("output", "")
    packages = [line.strip() for line in packages_text.splitlines() if line.strip()]

    cpu_text = checks.get("cpuinfo", {}).get("output", "")
    if not cpu_text:
        cpu_text = checks.get("top_processes", {}).get("output", "")
    battery_text = checks.get("battery", {}).get("output", "")
    temp_c = extract_battery_temp_c(battery_text)
    risky = detect_risky_packages(packages)

    advisor = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_report": report_path,
        "device_model": checks.get("device_model", {}).get("output", "").strip(),
        "android_version": checks.get("android_version", {}).get("output", "").strip(),
        "security_patch": checks.get("security_patch", {}).get("output", "").strip(),
        "developer_options": checks.get("developer_options", {}).get("output", "").strip(),
        "unknown_sources": checks.get("unknown_sources", {}).get("output", "").strip(),
        "accessibility_enabled": checks.get("accessibility_enabled", {}).get("output", "").strip(),
        "battery_temp_c": temp_c,
        "risky_packages": risky,
        "top_cpu_processes": top_cpu_processes(cpu_text),
        "recommendations": build_recommendations(checks, risky, temp_c),
    }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"phone_advisor_{ts}.json"
    out_file.write_text(json.dumps(advisor, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"✅ Advisor generado: {out_file}")
    print(json.dumps({
        "battery_temp_c": advisor["battery_temp_c"],
        "risky_categories": list(advisor["risky_packages"].keys()),
        "top_cpu_processes": advisor["top_cpu_processes"][:3],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
