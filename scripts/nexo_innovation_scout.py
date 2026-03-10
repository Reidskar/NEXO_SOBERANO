from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def _bool(value: str | None) -> bool:
    return bool((value or "").strip())


def _safe_run(cmd: List[str], timeout: int = 20) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": (completed.stdout or "")[:10000],
            "stderr": (completed.stderr or "")[:4000],
        }
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def _package_updates(python_exe: str) -> Dict[str, Any]:
    cmd = [python_exe, "-m", "pip", "list", "--outdated", "--format=json"]
    result = _safe_run(cmd, timeout=25)
    if not result["ok"]:
        return {"ok": False, "count": 0, "items": [], "error": result.get("stderr", "")}
    try:
        items = json.loads(result.get("stdout", "") or "[]")
        trimmed = [
            {
                "name": item.get("name"),
                "current": item.get("version"),
                "latest": item.get("latest_version"),
            }
            for item in (items or [])[:20]
        ]
        return {"ok": True, "count": len(items or []), "items": trimmed}
    except Exception as exc:
        return {"ok": False, "count": 0, "items": [], "error": str(exc)}


def _module_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _integrations_check() -> Dict[str, Any]:
    wanted = {
        "apify_client": "apify-client",
        "pandas": "pandas",
        "plotly": "plotly",
        "python_docx": "python-docx",
        "sentence_transformers": "sentence-transformers",
        "youtube_transcript_api": "youtube-transcript-api",
    }
    present: Dict[str, bool] = {}
    for module_name, _pkg in wanted.items():
        present[module_name] = _module_installed(module_name)

    missing = [wanted[m] for m, ok in present.items() if not ok]
    return {
        "present": present,
        "missing_packages": missing,
    }


def _credentials_check(env: Dict[str, str]) -> Dict[str, Any]:
    keys = {
        "GEMINI_API_KEY": _bool(env.get("GEMINI_API_KEY")),
        "ANTHROPIC_API_KEY": _bool(env.get("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": _bool(env.get("OPENAI_API_KEY")),
        "XAI_API_KEY": _bool(env.get("XAI_API_KEY")),
        "DISCORD_WEBHOOK_URL": _bool(env.get("DISCORD_WEBHOOK_URL")),
        "NEXO_ALERT_WEBHOOK": _bool(env.get("NEXO_ALERT_WEBHOOK")),
    }
    ai_ready = sum(1 for k in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"] if keys[k])
    missing = [k for k, ok in keys.items() if not ok]
    return {"keys": keys, "ai_ready": ai_ready, "missing": missing}


def build_recommendations(updates: Dict[str, Any], integrations: Dict[str, Any], creds: Dict[str, Any]) -> List[Dict[str, str]]:
    recs: List[Dict[str, str]] = []

    if updates.get("ok") and int(updates.get("count", 0)) > 0:
        recs.append(
            {
                "priority": "P2",
                "title": "Actualizar dependencias con rezago",
                "action": "Ejecutar task de upgrade en ventana controlada y volver a correr tests",
                "impact": "Mejora seguridad/estabilidad del stack",
            }
        )

    missing_packages = integrations.get("missing_packages", []) or []
    if missing_packages:
        recs.append(
            {
                "priority": "P2",
                "title": "Instalar integraciones opcionales faltantes",
                "action": f"Instalar: {', '.join(missing_packages[:6])}",
                "impact": "Amplía automatización de análisis y reporting",
            }
        )

    if creds.get("ai_ready", 0) < 3:
        recs.append(
            {
                "priority": "P1",
                "title": "Subir resiliencia multi-IA",
                "action": "Configurar OPENAI_API_KEY y XAI_API_KEY para fallback completo",
                "impact": "Reduce caídas y mejora continuidad cognitiva",
            }
        )

    missing = creds.get("missing", []) or []
    if "NEXO_ALERT_WEBHOOK" in missing:
        recs.append(
            {
                "priority": "P1",
                "title": "Cerrar loop de alertas",
                "action": "Configurar NEXO_ALERT_WEBHOOK para notificaciones de incidentes",
                "impact": "Acelera respuesta operativa",
            }
        )

    if not recs:
        recs.append(
            {
                "priority": "P3",
                "title": "Stack estable",
                "action": "Mantener escaneo continuo y revisión semanal",
                "impact": "Sostiene productividad extrema",
            }
        )

    return recs[:8]


def run_scan() -> Dict[str, Any]:
    env = _load_env_file(ENV_PATH)
    python_exe = sys.executable

    updates = _package_updates(python_exe)
    integrations = _integrations_check()
    creds = _credentials_check(env)
    recommendations = build_recommendations(updates, integrations, creds)

    score = 100.0
    score -= min(25.0, float(int(updates.get("count", 0)) * 0.8)) if updates.get("ok") else 8.0
    score -= min(20.0, float(len(integrations.get("missing_packages", []) or []) * 2.5))
    score -= max(0.0, float(4 - int(creds.get("ai_ready", 0))) * 6.0)
    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "ok": True,
        "generated_at": _now(),
        "innovation_score": score,
        "updates": updates,
        "integrations": integrations,
        "credentials": creds,
        "recommendations": recommendations,
    }


def main() -> int:
    out = ROOT / "logs" / "innovation_scout_last.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = run_scan()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "innovation_score": payload.get("innovation_score")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
