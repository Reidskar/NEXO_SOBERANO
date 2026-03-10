#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path


def latest(pattern: str) -> str | None:
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def main() -> int:
    inventory_path = latest("reports/security/app_inventory_*.json")
    phone_advisor_path = latest("reports/security/phone_advisor_*.json")

    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8")) if inventory_path else {}
    advisor = json.loads(Path(phone_advisor_path).read_text(encoding="utf-8")) if phone_advisor_path else {}

    phone = inventory.get("phone", {})
    risk_tags = phone.get("risk_tags", {})
    top_cpu = advisor.get("top_cpu_processes", [])
    temp = advisor.get("battery_temp_c")

    lines = [
        "# Optimización de Procesos y Apps (IA-Aware)",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Resumen",
        f"- Apps Android detectadas: {phone.get('apps_count', 0)}",
        f"- Temperatura batería (último advisor): {temp}",
        f"- Categorías de riesgo detectadas: {', '.join(risk_tags.keys()) if risk_tags else 'ninguna'}",
        "",
        "## Causas probables de sobrecarga",
    ]

    if top_cpu:
        lines.append("- Procesos con mayor carga observada:")
        for row in top_cpu[:5]:
            lines.append(f"  - {row}")
    else:
        lines.append("- No hay muestra de CPU en el advisor actual.")

    lines += [
        "",
        "## Reglas de optimización recomendadas",
        "- Mantener solo una app de control remoto activa con permisos altos (evitar solapamiento AnyDesk/AirDroid).",
        "- Aplicar perfil de background estricto a apps sociales pesadas cuando no transmites.",
        "- Programar escaneo térmico cada 15 min durante sesiones de streaming.",
        "- Usar DNS filtrado (AdGuard) + VPN malla (Tailscale) para reducir superficie de red.",
        "- Ingerir este documento en el contexto RAG para recomendaciones adaptadas a apps reales.",
        "",
        "## Integración con IA (NEXO)",
        "- Fuente inventario: reports/security/app_inventory_*.json",
        "- Fuente advisor: reports/security/phone_advisor_*.json",
        "- Este documento: documentos/OPTIMIZACION_FLUJO_APPS.md",
    ]

    out = Path("documentos/OPTIMIZACION_FLUJO_APPS.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"✅ Reporte generado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
