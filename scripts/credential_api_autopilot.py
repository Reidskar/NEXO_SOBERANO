from __future__ import annotations

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
AUTH_DIR = ROOT / "backend" / "auth"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_env_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _parse_env(lines: List[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def _upsert_env(lines: List[str], key: str, value: str) -> List[str]:
    updated = False
    out: List[str] = []
    for line in lines:
        raw = line.strip()
        if raw and not raw.startswith("#") and raw.split("=", 1)[0].strip() == key and "=" in raw:
            out.append(f"{key}={value}")
            updated = True
        else:
            out.append(line)
    if not updated:
        out.append(f"{key}={value}")
    return out


def _bool(value: str | None) -> bool:
    return bool((value or "").strip())


def _mask(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "***"
    return f"{raw[:4]}...{raw[-4:]}"


def _auth_files_state() -> Dict[str, bool]:
    files = {
        "google_credentials": AUTH_DIR / "credenciales_google.json",
        "microsoft_credentials": AUTH_DIR / "credenciales_microsoft.json",
        "drive_client_secrets": AUTH_DIR / "drive_client_secrets.json",
        "token_google_full": AUTH_DIR / "token_google_full.json",
        "token_google_manage_full": AUTH_DIR / "token_google_manage_full.json",
        "token_youtube_upload": AUTH_DIR / "token_youtube_upload.json",
    }
    return {k: v.exists() for k, v in files.items()}


def _build_approvals(env: Dict[str, str], files: Dict[str, bool]) -> List[Dict[str, str]]:
    approvals: List[Dict[str, str]] = []

    if not files.get("google_credentials"):
        approvals.append(
            {
                "id": "google-creds-file",
                "title": "Agregar credenciales de Google",
                "action": "Coloca credenciales_google.json en backend/auth",
                "why": "Habilita OAuth para Drive/Photos/YouTube",
            }
        )

    if files.get("google_credentials") and not files.get("token_google_manage_full"):
        approvals.append(
            {
                "id": "google-oauth-full",
                "title": "Autorizar Google OAuth completo",
                "action": "Ejecutar POST /agente/photos/authorize con include_drive_write=true y aprobar en navegador",
                "why": "Genera token_google_manage_full.json para sync unificado",
            }
        )

    if not files.get("microsoft_credentials"):
        approvals.append(
            {
                "id": "microsoft-creds-file",
                "title": "Agregar credenciales de Microsoft",
                "action": "Coloca credenciales_microsoft.json en backend/auth",
                "why": "Habilita integración Graph/OneDrive",
            }
        )

    if not _bool(env.get("DISCORD_WEBHOOK_URL")):
        approvals.append(
            {
                "id": "discord-webhook",
                "title": "Configurar webhook de Discord",
                "action": "Crear webhook en canal privado y pegar DISCORD_WEBHOOK_URL en .env",
                "why": "Permite seguimiento continuo por Discord",
            }
        )

    return approvals


def run_autopilot(dry_run: bool = False) -> Dict:
    lines = _read_env_lines(ENV_PATH)
    env = _parse_env(lines)

    auto_fixes: List[Dict[str, str]] = []

    if not _bool(env.get("NEXO_API_KEY")):
        generated = secrets.token_urlsafe(32)
        lines = _upsert_env(lines, "NEXO_API_KEY", generated)
        env["NEXO_API_KEY"] = generated
        auto_fixes.append({"key": "NEXO_API_KEY", "action": "generated"})

    if not _bool(env.get("NEXO_BRIDGE_API_KEY")) and _bool(env.get("NEXO_API_KEY")):
        lines = _upsert_env(lines, "NEXO_BRIDGE_API_KEY", env["NEXO_API_KEY"])
        env["NEXO_BRIDGE_API_KEY"] = env["NEXO_API_KEY"]
        auto_fixes.append({"key": "NEXO_BRIDGE_API_KEY", "action": "synced_from_nexo_api_key"})

    if _bool(env.get("DISCORD_WEBHOOK_URL")) and not _bool(env.get("NEXO_ALERT_WEBHOOK")):
        lines = _upsert_env(lines, "NEXO_ALERT_WEBHOOK", env["DISCORD_WEBHOOK_URL"])
        env["NEXO_ALERT_WEBHOOK"] = env["DISCORD_WEBHOOK_URL"]
        auto_fixes.append({"key": "NEXO_ALERT_WEBHOOK", "action": "synced_from_discord_webhook"})

    if _bool(env.get("DISCORD_WEBHOOK_URL")):
        current = (env.get("DISCORD_ENABLED", "") or "").strip().lower()
        if current not in {"1", "true", "yes", "on"}:
            lines = _upsert_env(lines, "DISCORD_ENABLED", "true")
            env["DISCORD_ENABLED"] = "true"
            auto_fixes.append({"key": "DISCORD_ENABLED", "action": "enabled"})

    if not _bool(env.get("DISCORD_PERSONAL_FOLLOWUP_ENABLED")):
        lines = _upsert_env(lines, "DISCORD_PERSONAL_FOLLOWUP_ENABLED", "true")
        env["DISCORD_PERSONAL_FOLLOWUP_ENABLED"] = "true"
        auto_fixes.append({"key": "DISCORD_PERSONAL_FOLLOWUP_ENABLED", "action": "enabled"})

    if not _bool(env.get("NEXO_LLM_PROVIDER")):
        lines = _upsert_env(lines, "NEXO_LLM_PROVIDER", "auto")
        env["NEXO_LLM_PROVIDER"] = "auto"
        auto_fixes.append({"key": "NEXO_LLM_PROVIDER", "action": "set_auto"})

    if not dry_run:
        ENV_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    files = _auth_files_state()
    approvals = _build_approvals(env, files)

    configured = {
        "NEXO_API_KEY": _bool(env.get("NEXO_API_KEY")),
        "NEXO_BRIDGE_API_KEY": _bool(env.get("NEXO_BRIDGE_API_KEY")),
        "GEMINI_API_KEY": _bool(env.get("GEMINI_API_KEY")),
        "ANTHROPIC_API_KEY": _bool(env.get("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": _bool(env.get("OPENAI_API_KEY")),
        "XAI_API_KEY": _bool(env.get("XAI_API_KEY")),
        "DISCORD_WEBHOOK_URL": _bool(env.get("DISCORD_WEBHOOK_URL")),
        "NEXO_ALERT_WEBHOOK": _bool(env.get("NEXO_ALERT_WEBHOOK")),
        "DISCORD_ENABLED": (env.get("DISCORD_ENABLED", "") or "").strip().lower() in {"1", "true", "yes", "on"},
    }

    ai_ready_count = sum(
        1
        for key in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY"]
        if configured.get(key)
    )

    productivity_score = round(
        (ai_ready_count / 2) * 45
        + (20 if configured.get("DISCORD_WEBHOOK_URL") else 0)
        + (10 if configured.get("NEXO_ALERT_WEBHOOK") else 0)
        + (10 if files.get("token_google_manage_full") else 0)
        + (15 if files.get("microsoft_credentials") else 0),
        1,
    )

    return {
        "ok": True,
        "generated_at": _utc_now(),
        "dry_run": dry_run,
        "auto_fixes_applied": auto_fixes,
        "approvals_required": approvals,
        "status": {
            "configured": configured,
            "ai_ready_count": ai_ready_count,
            "auth_files": files,
            "productivity_score": productivity_score,
        },
        "masked_preview": {
            "NEXO_API_KEY": _mask(env.get("NEXO_API_KEY")),
            "NEXO_BRIDGE_API_KEY": _mask(env.get("NEXO_BRIDGE_API_KEY")),
            "DISCORD_WEBHOOK_URL": _mask(env.get("DISCORD_WEBHOOK_URL")),
            "NEXO_ALERT_WEBHOOK": _mask(env.get("NEXO_ALERT_WEBHOOK")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXO credential/api autopilot")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "logs" / "credential_api_autopilot_last.json"))
    args = parser.parse_args()

    result = run_autopilot(dry_run=args.dry_run)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "approvals_required": len(result["approvals_required"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
