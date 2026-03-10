from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib import error, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def http_json(base_url: str, path: str, api_key: str, timeout: int = 30) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-NEXO-API-KEY"] = api_key
        headers["X-NEXO-KEY"] = api_key

    req = request.Request(url=url, method="GET", headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw.strip() else {}
            return {"ok": True, "status": int(resp.status), "data": body}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            payload = json.loads(raw) if raw.strip() else raw
        except Exception:
            payload = raw
        return {"ok": False, "status": int(exc.code), "error": payload}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def env_snapshot() -> Dict[str, Any]:
    keys = [
        "NEXO_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "XAI_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "OBS_PASSWORD",
        "DISCORD_WEBHOOK_URL",
    ]
    return {k: bool((os.getenv(k) or "").strip()) for k in keys}


def build_actions(health: Dict[str, Any], analytics: Dict[str, Any], warroom: Dict[str, Any], env: Dict[str, Any]) -> list[Dict[str, Any]]:
    actions: list[Dict[str, Any]] = []

    if not health.get("ok"):
        actions.append({
            "priority": "P1",
            "title": "Restaurar backend",
            "owner": "SRE",
            "command": ".\\.venv\\Scripts\\python.exe run_backend.py",
            "success": "GET /api/health/ => 200",
        })

    workspace = ((analytics.get("data") or {}).get("workspace") or {}) if analytics.get("ok") else {}
    if workspace.get("drive_error"):
        actions.append({
            "priority": "P1",
            "title": "Reautorizar Google Drive",
            "owner": "ProductOps",
            "command": "POST /agente/drive/authorize {\"write_scope\": true}",
            "success": "workspace.drive_error vacío y drive_recent > 0",
        })
    if workspace.get("photos_error"):
        actions.append({
            "priority": "P1",
            "title": "Reautorizar Google Photos",
            "owner": "ProductOps",
            "command": "POST /agente/photos/authorize {\"include_drive_write\": true}",
            "success": "workspace.photos_error vacío y photos_recent > 0",
        })

    stream = ((warroom.get("data") or {}).get("data") or {}).get("stream", {}) if warroom.get("ok") else {}
    if stream.get("obs_connected") is False:
        actions.append({
            "priority": "P2",
            "title": "Conectar OBS WebSocket",
            "owner": "SRE",
            "command": "Iniciar OBS + verificar puerto 4455 y password",
            "success": "stream.obs_connected=true",
        })
    if stream.get("discord_connected") is False:
        actions.append({
            "priority": "P2",
            "title": "Conectar Discord",
            "owner": "SRE",
            "command": "Validar DISCORD_WEBHOOK_URL/token y reiniciar servicio",
            "success": "stream.discord_connected=true",
        })

    if not env.get("ANTHROPIC_API_KEY", False):
        actions.append({
            "priority": "P2",
            "title": "Configurar Claude API key",
            "owner": "AI-Ops",
            "command": "Definir ANTHROPIC_API_KEY en .env",
            "success": "FODA low-cost con decidor_final=claude",
        })
    if not env.get("GEMINI_API_KEY", False):
        actions.append({
            "priority": "P3",
            "title": "Configurar Gemini fallback",
            "owner": "AI-Ops",
            "command": "Definir GEMINI_API_KEY en .env",
            "success": "Fallback multi-ai disponible",
        })

    if not actions:
        actions.append({
            "priority": "P3",
            "title": "Sistema estable",
            "owner": "Ops",
            "command": "Ejecutar revisión semanal",
            "success": "Semáforo en verde sostenido",
        })

    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXO operational optimizer")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="NEXO_LOCAL_2026_OK")
    parser.add_argument("--output", default="logs/nexo_operational_optimizer_report.json")
    args = parser.parse_args()

    env = env_snapshot()
    health = http_json(args.base_url, "/api/health/", args.api_key)
    analytics = http_json(args.base_url, "/agente/control-center/analytics", args.api_key)
    warroom = http_json(args.base_url, "/agente/warroom/ai-control?include_autonomous_cycle=true", args.api_key)

    report = {
        "ok": True,
        "generated_at": utc_now(),
        "base_url": args.base_url,
        "env": env,
        "checks": {
            "health": health,
            "analytics": analytics,
            "warroom": warroom,
        },
        "actions": build_actions(health, analytics, warroom, env),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(json.dumps({"ok": True, "output": str(out), "actions": len(report["actions"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
