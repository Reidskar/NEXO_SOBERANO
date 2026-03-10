from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
OUT_PATH = ROOT / "logs" / "web_user_multi_ai_simulation.json"
BASE_URL = "http://127.0.0.1:8000"


def get_env_value(name: str, default: str = "") -> str:
    if not ENV_PATH.exists():
        return default
    for line in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip() or default
    return default


def request_json(path: str, method: str = "GET", payload: dict | None = None, api_key: str = "") -> dict:
    headers = {
        "X-NEXO-API-KEY": api_key,
        "X-NEXO-KEY": api_key,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = Request(BASE_URL + path, method=method, headers=headers, data=data)
    try:
        with urlopen(req, timeout=300) as resp:
            return {
                "ok": True,
                "status": getattr(resp, "status", 200),
                "data": json.loads(resp.read().decode("utf-8", errors="ignore") or "{}"),
            }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return {
            "ok": False,
            "status": exc.code,
            "error": body or str(exc),
        }
    except URLError as exc:
        return {
            "ok": False,
            "status": None,
            "error": str(exc),
        }


def summarize_foda(result: dict) -> dict:
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error"), "status": result.get("status")}

    payload = result.get("data", {})
    consensus = payload.get("consensus", {})
    reviews = payload.get("reviews", [])

    return {
        "ok": True,
        "decider": consensus.get("decider"),
        "consensus_ok": bool(consensus.get("ok")),
        "model": consensus.get("model"),
        "reviewers_ok": [r.get("provider") for r in reviews if r.get("ok")],
        "reviewers_all": [r.get("provider") for r in reviews],
        "settings": payload.get("settings", {}),
    }


def main() -> int:
    api_key = get_env_value("NEXO_API_KEY", "CAMBIA_ESTA_CLAVE_NEXO")
    providers = {
        "anthropic": bool(get_env_value("ANTHROPIC_API_KEY")),
        "openai": bool(get_env_value("OPENAI_API_KEY")),
        "gemini": bool(get_env_value("GEMINI_API_KEY")),
        "grok": bool(get_env_value("XAI_API_KEY")),
    }

    report: dict = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "providers_env": providers,
        "functions": {},
        "multi_ai": {},
    }

    report["functions"]["health"] = request_json("/api/health", api_key=api_key)
    report["functions"]["control_center_status"] = request_json("/agente/control-center/status", api_key=api_key)
    report["functions"]["analytics"] = request_json("/agente/control-center/analytics", api_key=api_key)
    report["functions"]["warroom_ai_control"] = request_json("/agente/warroom/ai-control?include_autonomous_cycle=true", api_key=api_key)

    claude_run = request_json(
        "/api/ai/foda-critical",
        method="POST",
        api_key=api_key,
        payload={
            "objetivo": "Simulación usuario web en modo ahorro con decisor Claude",
            "incluir_evolucion": True,
            "incluir_alertas": True,
            "decisor_final": "claude",
            "modo_ahorro": True,
        },
    )

    gemini_run = request_json(
        "/api/ai/foda-critical",
        method="POST",
        api_key=api_key,
        payload={
            "objetivo": "Simulación usuario web con decisor Gemini",
            "incluir_evolucion": True,
            "incluir_alertas": True,
            "decisor_final": "gemini",
            "modo_ahorro": True,
        },
    )

    multi_run = request_json(
        "/api/ai/foda-critical",
        method="POST",
        api_key=api_key,
        payload={
            "objetivo": "Simulación comparativa multi IA de funciones web usuario",
            "incluir_evolucion": True,
            "incluir_alertas": True,
            "decisor_final": "claude",
            "modo_ahorro": False,
        },
    )

    report["multi_ai"]["claude_low_cost"] = summarize_foda(claude_run)
    report["multi_ai"]["gemini_low_cost"] = summarize_foda(gemini_run)
    report["multi_ai"]["multi_review_claude_decider"] = summarize_foda(multi_run)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "report": str(OUT_PATH),
        "functions_ok": {
            k: bool(v.get("ok")) for k, v in report["functions"].items()
        },
        "multi_ai": report["multi_ai"],
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
