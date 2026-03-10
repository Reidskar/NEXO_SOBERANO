from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib import error, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def http_json(
    base_url: str,
    path: str,
    api_key: str,
    method: str = "GET",
    payload: Dict[str, Any] | None = None,
    timeout_seconds: int = 180,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {
        "Accept": "application/json",
        "X-NEXO-API-KEY": api_key,
        "X-NEXO-KEY": api_key,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = request.Request(url=url, method=method.upper(), headers=headers, data=data)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw.strip() else {}
            return {
                "ok": True,
                "status": int(resp.status),
                "data": body,
            }
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        body: Any = raw
        try:
            if raw.strip():
                body = json.loads(raw)
        except Exception:
            body = raw
        return {
            "ok": False,
            "status": int(exc.code),
            "error": body,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error": str(exc),
        }


def summarize_flags(report: Dict[str, Any]) -> Dict[str, str]:
    checks = report.get("checks", {})

    def flag(ok: bool, degraded: bool = False) -> str:
        if not ok:
            return "red"
        return "yellow" if degraded else "green"

    health_ok = bool((checks.get("health", {}) or {}).get("ok"))
    analytics_data = ((checks.get("analytics", {}) or {}).get("data") or {}).get("data", {})
    workspace = analytics_data.get("workspace", {}) if isinstance(analytics_data, dict) else {}
    workspace_degraded = bool(workspace.get("drive_error") or workspace.get("photos_error"))

    warroom_data = ((checks.get("warroom_ai_control", {}) or {}).get("data") or {}).get("data", {})
    stream = warroom_data.get("stream", {}) if isinstance(warroom_data, dict) else {}
    stream_ok = bool(stream.get("obs_connected")) and bool(stream.get("discord_connected"))

    multi = report.get("multi_ai", {})
    claude_ok = bool((multi.get("claude_low_cost", {}) or {}).get("ok"))
    gemini_ok = bool((multi.get("gemini_low_cost", {}) or {}).get("ok"))
    multi_ok = bool((multi.get("multi_review_claude_decider", {}) or {}).get("ok"))

    analytics_ok = bool((checks.get("analytics", {}) or {}).get("ok"))

    return {
        "backend_health": flag(health_ok),
        "workspace_data": flag(analytics_ok, workspace_degraded),
        "stream_ops": flag(stream_ok, degraded=not stream_ok),
        "multi_ai": flag(claude_ok and gemini_ok and multi_ok, degraded=(claude_ok or gemini_ok or multi_ok)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NEXO multi-AI project review and export share package")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="NEXO_LOCAL_2026_OK")
    parser.add_argument("--output", default="logs/multi_ai_project_review.json")
    parser.add_argument("--timeout", type=int, default=90, help="HTTP timeout seconds for checks")
    parser.add_argument("--foda-timeout", type=int, default=120, help="HTTP timeout seconds for FODA runs")
    parser.add_argument("--skip-foda", action="store_true", help="Skip expensive FODA multi-provider calls")
    args = parser.parse_args()

    objective = (
        "Auditar integralmente NEXO_SOBERANO: arquitectura, backend, frontend, seguridad, "
        "operación, deuda técnica y ruta de refuerzo."
    )

    report: Dict[str, Any] = {
        "ok": True,
        "generated_at": utc_now(),
        "base_url": args.base_url,
        "checks": {},
        "multi_ai": {},
        "share_package": {},
    }

    log.info("[1/6] health + analytics + warroom checks...", flush=True)
    report["checks"]["health"] = http_json(args.base_url, "/api/health/", args.api_key, "GET", timeout_seconds=args.timeout)
    report["checks"]["analytics"] = http_json(
        args.base_url,
        "/agente/control-center/analytics",
        args.api_key,
        "GET",
        timeout_seconds=args.timeout,
    )
    report["checks"]["warroom_ai_control"] = http_json(
        args.base_url,
        "/agente/warroom/ai-control?include_autonomous_cycle=true",
        args.api_key,
        "GET",
        timeout_seconds=args.timeout,
    )
    report["checks"]["foda_status_before"] = http_json(
        args.base_url,
        "/api/ai/foda-status",
        args.api_key,
        "GET",
        timeout_seconds=args.timeout,
    )

    base_payload = {
        "objetivo": objective,
        "incluir_evolucion": True,
        "incluir_alertas": True,
    }
    if not args.skip_foda:
        log.info("[2/6] running FODA claude low-cost...", flush=True)
        report["multi_ai"]["claude_low_cost"] = http_json(
            args.base_url,
            "/api/ai/foda-critical",
            args.api_key,
            "POST",
            {**base_payload, "decisor_final": "claude", "modo_ahorro": True},
            timeout_seconds=args.foda_timeout,
        )
        log.info("[3/6] running FODA gemini low-cost...", flush=True)
        report["multi_ai"]["gemini_low_cost"] = http_json(
            args.base_url,
            "/api/ai/foda-critical",
            args.api_key,
            "POST",
            {**base_payload, "decisor_final": "gemini", "modo_ahorro": True},
            timeout_seconds=args.foda_timeout,
        )
        log.info("[4/6] running FODA multi-review...", flush=True)
        report["multi_ai"]["multi_review_claude_decider"] = http_json(
            args.base_url,
            "/api/ai/foda-critical",
            args.api_key,
            "POST",
            {**base_payload, "decisor_final": "claude", "modo_ahorro": False},
            timeout_seconds=args.foda_timeout,
        )
    else:
        report["multi_ai"]["skipped"] = {"ok": True, "reason": "--skip-foda"}
    log.info("[5/6] refreshing FODA status...", flush=True)
    report["checks"]["foda_status_after"] = http_json(
        args.base_url,
        "/api/ai/foda-status",
        args.api_key,
        "GET",
        timeout_seconds=args.timeout,
    )

    log.info("[6/6] building share package...", flush=True)
    report["share_package"] = http_json(
        args.base_url,
        "/agente/control-center/extractor-prompt",
        args.api_key,
        "GET",
        timeout_seconds=args.timeout,
    )
    report["semaforo"] = summarize_flags(report)

    sem = report.get("semaforo", {})
    recs: list[str] = []
    if sem.get("workspace_data") != "green":
        recs.append("Reautorizar Google Drive/Photos y validar analytics.workspace.ok=true")
    if sem.get("stream_ops") != "green":
        recs.append("Levantar OBS WebSocket y reconectar Discord para stream_ops verde")
    if sem.get("multi_ai") == "red":
        recs.append("Validar proveedores IA (claude/gemini) y ejecutar foda-critical nuevamente")
    if not recs:
        recs.append("Sistema en estado estable; mantener monitoreo periódico")
    report["recommended_next_actions"] = recs

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(json.dumps({"ok": True, "output": str(output_path), "semaforo": report.get("semaforo", {}), "actions": recs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
