#!/usr/bin/env python3
# ============================================================
# NEXO SOBERANO — OSINT Supervisor v1.0
# © 2026 elanarcocapital.com
#
# Supervisa y auto-restaura:
#   - Ollama (Gemma 4)
#   - TheBigBrother
#   - AI Router health
#
# Uso: python scripts/supervisor_osint.py [--once] [--interval 60]
# ============================================================
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SUPERVISOR] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nexo.supervisor")

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_URL",        "http://localhost:11434")
OLLAMA_HOST   = os.getenv("OLLAMA_TORRE_HOST", "")
BB_URL        = os.getenv("BIGBROTHER_URL",    "http://localhost:8888")
NEXO_URL      = os.getenv("NEXO_URL",          "http://localhost:8000")
NEXO_API_KEY  = os.getenv("NEXO_API_KEY",      "nexo_dev_key_2025")

OLLAMA_RESTART_CMD  = os.getenv("OLLAMA_RESTART_CMD",  "systemctl restart ollama")
BB_RESTART_CMD      = os.getenv("BB_RESTART_CMD",      "")     # ej: "docker restart bigbrother"

STATE_FILE = Path("logs/supervisor_osint_state.json")

# ── HELPERS ───────────────────────────────────────────────────────────────────

async def _get(url: str, timeout: int = 5) -> tuple[bool, dict]:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                if r.status == 200:
                    return True, await r.json()
                return False, {"status": r.status}
    except Exception as e:
        return False, {"error": str(e)}


def _restart(cmd: str, service: str):
    if not cmd:
        logger.warning(f"No restart command configured for {service}")
        return False
    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"✓ Restarted {service}")
            return True
        logger.error(f"Failed to restart {service}: {result.stderr.decode()[:200]}")
    except Exception as e:
        logger.error(f"Restart {service} exception: {e}")
    return False


# ── CHECKS ────────────────────────────────────────────────────────────────────

async def check_ollama() -> dict:
    base = OLLAMA_HOST or OLLAMA_URL
    ok, data = await _get(f"{base}/api/tags")
    models = [m["name"] for m in data.get("models", [])] if ok else []
    gemma_models = [m for m in models if "gemma" in m.lower()]
    return {
        "service": "ollama",
        "ok": ok and len(models) > 0,
        "models_total": len(models),
        "gemma_models": gemma_models,
        "gemma_available": len(gemma_models) > 0,
        "url": base,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def check_bigbrother() -> dict:
    ok, data = await _get(f"{BB_URL}/health")
    return {
        "service": "bigbrother",
        "ok": ok,
        "data": data,
        "url": BB_URL,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def check_nexo_backend() -> dict:
    ok, data = await _get(f"{NEXO_URL}/health")
    return {
        "service": "nexo_backend",
        "ok": ok,
        "data": data,
        "url": NEXO_URL,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def check_ai_routing() -> dict:
    """Verifica que el router de IA funciona correctamente."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{NEXO_URL}/api/ai/routing-stats",
                headers={"x-api-key": NEXO_API_KEY},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    return {
                        "service": "ai_router",
                        "ok": True,
                        "local_available": data.get("local_available", False),
                        "local_model": data.get("local_model", "N/A"),
                        "tareas_locales": data.get("tareas_locales", 0),
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }
    except Exception as e:
        pass
    return {
        "service": "ai_router",
        "ok": False,
        "error": "endpoint not reachable",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


# ── REPORT ────────────────────────────────────────────────────────────────────

def _save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _print_report(results: dict):
    print("\n" + "━" * 60)
    print(f"  NEXO SUPERVISOR OSINT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("━" * 60)
    for svc, r in results.items():
        status = "✓ OK   " if r.get("ok") else "✗ FAIL "
        extra = ""
        if svc == "ollama":
            extra = f"gemma={r.get('gemma_models', ['none'])[0] if r.get('gemma_models') else 'none'}"
        elif svc == "ai_router":
            extra = f"local={r.get('local_available', '?')} | model={r.get('local_model', '?')}"
        elif svc == "bigbrother":
            extra = f"url={r.get('url', '')}"
        print(f"  {status} {svc:<20} {extra}")
    print("━" * 60 + "\n")


# ── MAIN LOOP ────────────────────────────────────────────────────────────────

async def run_once(auto_restart: bool = True) -> dict:
    ollama, bigbrother, nexo, ai = await asyncio.gather(
        check_ollama(),
        check_bigbrother(),
        check_nexo_backend(),
        check_ai_routing(),
    )

    results = {
        "ollama": ollama,
        "bigbrother": bigbrother,
        "nexo_backend": nexo,
        "ai_router": ai,
    }

    _print_report(results)
    _save_state(results)

    # Auto-restart si configurado
    if auto_restart:
        if not ollama["ok"]:
            logger.warning("Ollama down → intentando reiniciar")
            _restart(OLLAMA_RESTART_CMD, "ollama")

        if not bigbrother["ok"] and BB_RESTART_CMD:
            logger.warning("BigBrother down → intentando reiniciar")
            _restart(BB_RESTART_CMD, "bigbrother")

    return results


async def run_loop(interval: int, auto_restart: bool):
    logger.info(f"Supervisor OSINT iniciado — intervalo={interval}s")
    while True:
        try:
            await run_once(auto_restart)
        except Exception as e:
            logger.error(f"Supervisor loop error: {e}")
        await asyncio.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="NEXO OSINT Supervisor")
    parser.add_argument("--once",     action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60,  help="Check interval seconds")
    parser.add_argument("--no-restart", action="store_true", help="Don't auto-restart services")
    args = parser.parse_args()

    auto_restart = not args.no_restart

    if args.once:
        results = asyncio.run(run_once(auto_restart))
        all_ok = all(r.get("ok") for r in results.values())
        sys.exit(0 if all_ok else 1)
    else:
        asyncio.run(run_loop(args.interval, auto_restart))


if __name__ == "__main__":
    main()
