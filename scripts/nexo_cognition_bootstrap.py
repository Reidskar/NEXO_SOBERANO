from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"

if load_dotenv:
    load_dotenv(ROOT / ".env")


@dataclass
class Capability:
    name: str
    objective: str
    status: str
    score: int
    blockers: List[str]
    next_actions: List[str]


def _has_env(name: str) -> bool:
    return bool((os.getenv(name, "") or "").strip())


def _exists(path: Path) -> bool:
    return path.exists()


def evaluate() -> Dict:
    capabilities: List[Capability] = []

    # 1) Core IA providers
    providers = {
        "gemini": _has_env("GEMINI_API_KEY"),
        "anthropic": _has_env("ANTHROPIC_API_KEY"),
        "openai": _has_env("OPENAI_API_KEY"),
        "grok": _has_env("XAI_API_KEY"),
    }
    ready_count = sum(1 for v in providers.values() if v)
    blockers = []
    if ready_count < 2:
        blockers.append("Mínimo 2 providers IA para resiliencia")
    if not providers["openai"]:
        blockers.append("Falta OPENAI_API_KEY")
    if not providers["grok"]:
        blockers.append("Falta XAI_API_KEY")
    capabilities.append(
        Capability(
            name="multi_ai_resilience",
            objective="Alta disponibilidad cognitiva y fallback entre modelos",
            status="ok" if ready_count >= 2 else "degraded",
            score=min(100, ready_count * 25),
            blockers=blockers,
            next_actions=[
                "Configurar OPENAI_API_KEY",
                "Configurar XAI_API_KEY",
                "Mantener Gemini/Claude como base de análisis",
            ],
        )
    )

    # 2) NotebookLM bridge readiness
    notebooklm_ready = _exists(ROOT / "AI-INTELLIGENCE-SYSTEM" / "scripts" / "notebooklm_bridge_api.py")
    capabilities.append(
        Capability(
            name="notebooklm_research_engine",
            objective="Procesar corpus masivo (2TB) con RAG asistido",
            status="ok" if notebooklm_ready else "missing",
            score=85 if notebooklm_ready else 20,
            blockers=[] if notebooklm_ready else ["No se detecta bridge NotebookLM"],
            next_actions=[
                "Definir taxonomía de fuentes (geopolítica/economía/RRSS)",
                "Cargar perfiles de personalidad por libreta",
                "Programar resumen diario automático",
            ],
        )
    )

    # 3) Social + discord + alerting
    discord = _has_env("DISCORD_WEBHOOK_URL")
    alerts = _has_env("NEXO_ALERT_WEBHOOK")
    social_blockers = []
    if not discord:
        social_blockers.append("Falta DISCORD_WEBHOOK_URL")
    if not alerts:
        social_blockers.append("Falta NEXO_ALERT_WEBHOOK")
    capabilities.append(
        Capability(
            name="rrss_mediation_and_alerts",
            objective="Mediación de RRSS y alertas operativas",
            status="ok" if (discord and alerts) else "degraded",
            score=100 if (discord and alerts) else 60,
            blockers=social_blockers,
            next_actions=[
                "Validar webhook de Discord en runtime",
                "Unificar alertas de sync y war room",
                "Añadir umbrales de ruido para evitar spam",
            ],
        )
    )

    # 4) Video + youtube pipeline
    youtube_pipeline = _exists(ROOT / "backend" / "services" / "drive_youtube_service.py")
    capabilities.append(
        Capability(
            name="youtube_operational_pipeline",
            objective="Armado de videos, guiones y publicación asistida",
            status="ok" if youtube_pipeline else "missing",
            score=80 if youtube_pipeline else 30,
            blockers=[] if youtube_pipeline else ["No existe servicio de pipeline YouTube"],
            next_actions=[
                "Conectar salida de NotebookLM a guion",
                "Añadir plantilla de storytelling y CTA",
                "Medir retención estimada por segmento",
            ],
        )
    )

    # 5) Web/visual agent
    obs_enabled = (os.getenv("OBS_ENABLED", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
    capabilities.append(
        Capability(
            name="web_visual_agent",
            objective="Operación web + visual con telemetría",
            status="degraded" if obs_enabled else "ok",
            score=65 if obs_enabled else 75,
            blockers=["OBS habilitado pero puede degradar si no está levantado"] if obs_enabled else [],
            next_actions=[
                "Si no usas OBS continuo, poner OBS_ENABLED=false",
                "Mantener AI visual guard con SLO de frescura",
                "Registrar errores visuales en tablero diario",
            ],
        )
    )

    # 6) Secure coding evolution
    secure_code = _exists(ROOT / "nexo_autosupervisor.py") and _exists(ROOT / "scripts" / "run_multi_ai_project_review.py")
    capabilities.append(
        Capability(
            name="secure_code_evolution",
            objective="Evolución de código segura y orientada a objetivos",
            status="ok" if secure_code else "degraded",
            score=88 if secure_code else 55,
            blockers=[] if secure_code else ["Faltan componentes de revisión automática"],
            next_actions=[
                "Ejecutar scan/fix diario con reporte",
                "Bloquear deploy con issues críticos",
                "Alinear roadmap técnico con KPI de negocio",
            ],
        )
    )

    # 7) Geopolitical cognition depth
    cognition_assets = [
        ROOT / "AI-INTELLIGENCE-SYSTEM" / "knowledge" / "NEXO_METACOGNITION_PROTOCOL.md",
        ROOT / "AI-INTELLIGENCE-SYSTEM" / "prompts" / "PERSONAL_AGENT_MASTER_PROMPT.md",
    ]
    cogn_ready = all(p.exists() for p in cognition_assets)
    capabilities.append(
        Capability(
            name="metacognition_core",
            objective="Razonamiento causal, escenarios y autocrítica",
            status="ok" if cogn_ready else "missing",
            score=90 if cogn_ready else 40,
            blockers=[] if cogn_ready else ["Faltan protocolos metacognitivos"],
            next_actions=[
                "Correr brief diario por dominios (geo/econ/social)",
                "Medir precisión de hipótesis semanal",
                "Refinar prompts por fallos observados",
            ],
        )
    )

    avg_score = round(sum(c.score for c in capabilities) / len(capabilities), 1)
    critical_blockers = [b for c in capabilities for b in c.blockers if "Falta" in b or "Mínimo" in b]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "global_score": avg_score,
        "critical_blockers": critical_blockers,
        "capabilities": [asdict(c) for c in capabilities],
    }


def write_report(payload: Dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "nexo_cognition_readiness.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> None:
    payload = evaluate()
    out = write_report(payload)
    print(f"[OK] Readiness generado: {out}")
    print(f"[OK] Global score: {payload['global_score']}")
    if payload["critical_blockers"]:
        print("[BLOCKERS]")
        for b in payload["critical_blockers"]:
            print(f" - {b}")


if __name__ == "__main__":
    main()
