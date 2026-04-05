#!/usr/bin/env python3
"""scripts/setup_discord.py — Configuración guiada de Discord para NEXO SOBERANO"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# ANSI color helpers (no external deps)
# ---------------------------------------------------------------------------
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
WHITE  = "\033[97m"

def info(msg: str)    -> None: print(f"{CYAN}ℹ  {msg}{RESET}")
def ok(msg: str)      -> None: print(f"{GREEN}✔  {msg}{RESET}")
def warn(msg: str)    -> None: print(f"{YELLOW}⚠  {msg}{RESET}")
def error(msg: str)   -> None: print(f"{RED}✖  {msg}{RESET}")
def header(msg: str)  -> None: print(f"\n{BOLD}{WHITE}{'─'*60}\n   {msg}\n{'─'*60}{RESET}")
def prompt(msg: str)  -> str:  return input(f"{CYAN}▶  {msg}{RESET}").strip()


# ---------------------------------------------------------------------------
# .env helpers
# ---------------------------------------------------------------------------
ENV_PATH = ROOT / ".env"


def read_env() -> dict[str, str]:
    """Parse .env file into a dict, preserving order."""
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, val = stripped.partition("=")
            env[key.strip()] = val.strip()
    return env


def write_env(env: dict[str, str]) -> None:
    """Rewrite .env preserving comments and unknown lines, patching known keys."""
    if not ENV_PATH.exists():
        lines = [f"{k}={v}\n" for k, v in env.items()]
        ENV_PATH.write_text("".join(lines), encoding="utf-8")
        return

    original = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    patched_keys: set[str] = set()
    result: list[str] = []

    for line in original:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in env:
                result.append(f"{key}={env[key]}\n")
                patched_keys.add(key)
                continue
        result.append(line)

    # Append keys that were not yet present
    for key, val in env.items():
        if key not in patched_keys:
            result.append(f"{key}={val}\n")

    ENV_PATH.write_text("".join(result), encoding="utf-8")


# ---------------------------------------------------------------------------
# aiohttp-based tests
# ---------------------------------------------------------------------------

async def test_webhook(webhook_url: str) -> bool:
    """POST a test message to the Discord webhook."""
    try:
        import aiohttp
    except ImportError:
        warn("aiohttp no está instalado. Saltando prueba de webhook.")
        warn("  Instalar con: pip install aiohttp")
        return False

    payload = {
        "content": None,
        "embeds": [
            {
                "title": "NEXO SOBERANO — Test de Conexión",
                "description": "Webhook configurado correctamente ✔",
                "color": 0x00D4FF,
                "footer": {"text": "setup_discord.py"},
            }
        ],
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 204):
                    ok(f"Webhook respondió con HTTP {resp.status}")
                    return True
                body = await resp.text()
                error(f"Webhook devolvió HTTP {resp.status}: {body[:200]}")
                return False
    except Exception as exc:
        error(f"Error al conectar con webhook: {exc}")
        return False


async def test_bot_token(token: str) -> bool:
    """Validate bot token via Discord REST API."""
    try:
        import aiohttp
    except ImportError:
        warn("aiohttp no está instalado. Saltando prueba de token de bot.")
        return False

    url = "https://discord.com/api/v10/users/@me"
    headers = {"Authorization": f"Bot {token}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ok(f"Bot token válido — usuario: {data.get('username')}#{data.get('discriminator', '0')}")
                    return True
                body = await resp.text()
                error(f"Token inválido — HTTP {resp.status}: {body[:200]}")
                return False
    except Exception as exc:
        error(f"Error al validar token de bot: {exc}")
        return False


# ---------------------------------------------------------------------------
# PM2 ecosystem.config.cjs patcher
# ---------------------------------------------------------------------------

def patch_ecosystem_config() -> None:
    """Update cwd in discord_bot/ecosystem.config.cjs to actual ROOT path."""
    config_path = ROOT / "discord_bot" / "ecosystem.config.cjs"
    if not config_path.exists():
        warn("No se encontró discord_bot/ecosystem.config.cjs — omitiendo.")
        return

    content = config_path.read_text(encoding="utf-8")
    bot_dir = str(ROOT / "discord_bot").replace("\\", "/")

    # Replace the cwd value — handles both single and double quotes
    import re
    new_content = re.sub(
        r"(cwd\s*:\s*)['\"][^'\"]*['\"]",
        f"cwd: '{bot_dir}'",
        content,
    )

    if new_content == content:
        info("ecosystem.config.cjs ya tiene la ruta correcta o no contiene cwd.")
    else:
        config_path.write_text(new_content, encoding="utf-8")
        ok(f"ecosystem.config.cjs actualizado — cwd: {bot_dir}")


# ---------------------------------------------------------------------------
# Slash commands registration
# ---------------------------------------------------------------------------

def register_slash_commands() -> None:
    """Run node discord_bot/register_commands.js if it exists."""
    register_js = ROOT / "discord_bot" / "register_commands.js"
    if not register_js.exists():
        warn("No se encontró discord_bot/register_commands.js — omitiendo registro.")
        return

    info("Registrando slash commands con Node.js…")
    try:
        result = subprocess.run(
            ["node", str(register_js)],
            cwd=str(ROOT / "discord_bot"),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            ok("Slash commands registrados correctamente.")
            if result.stdout.strip():
                print(result.stdout.strip())
        else:
            error("El registro de slash commands falló:")
            print(result.stderr.strip() or result.stdout.strip())
    except FileNotFoundError:
        warn("Node.js no está disponible en PATH — instálalo para registrar comandos.")
    except subprocess.TimeoutExpired:
        error("Tiempo de espera agotado al registrar slash commands.")
    except Exception as exc:
        error(f"Error inesperado: {exc}")


# ---------------------------------------------------------------------------
# Interactive setup
# ---------------------------------------------------------------------------

def collect_discord_config(current: dict[str, str]) -> dict[str, str]:
    """Interactively collect Discord configuration from the user."""
    header("CONFIGURACIÓN DE DISCORD")

    updates: dict[str, str] = {}

    # DISCORD_TOKEN (bot token)
    current_token = current.get("DISCORD_BOT_TOKEN", "")
    masked = f"***{current_token[-6:]}" if len(current_token) > 6 else "(no configurado)"
    info(f"Token actual del bot: {masked}")
    new_token = prompt("Nuevo DISCORD_BOT_TOKEN (Enter para mantener actual): ")
    if new_token:
        updates["DISCORD_BOT_TOKEN"] = new_token
    elif current_token:
        updates["DISCORD_BOT_TOKEN"] = current_token

    # DISCORD_WEBHOOK_URL
    current_wh = current.get("DISCORD_WEBHOOK_URL", "")
    masked_wh = current_wh[:40] + "…" if len(current_wh) > 40 else current_wh or "(no configurado)"
    info(f"Webhook actual: {masked_wh}")
    new_wh = prompt("Nuevo DISCORD_WEBHOOK_URL (Enter para mantener actual): ")
    if new_wh:
        updates["DISCORD_WEBHOOK_URL"] = new_wh
    elif current_wh:
        updates["DISCORD_WEBHOOK_URL"] = current_wh

    # DISCORD_GUILD_ID
    current_guild = current.get("DISCORD_GUILD_ID", "")
    info(f"Guild ID actual: {current_guild or '(no configurado)'}")
    new_guild = prompt("Nuevo DISCORD_GUILD_ID (Enter para mantener actual): ")
    if new_guild:
        updates["DISCORD_GUILD_ID"] = new_guild
    elif current_guild:
        updates["DISCORD_GUILD_ID"] = current_guild

    # Always enable
    updates["DISCORD_ENABLED"] = "true"

    return updates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def async_main() -> None:
    header("NEXO SOBERANO — Setup de Discord")
    info(f"Directorio raíz: {ROOT}")

    # 1. Read current .env
    current_env = read_env()

    # 2. Collect config interactively
    discord_cfg = collect_discord_config(current_env)

    # 3. Test webhook
    webhook_url = discord_cfg.get("DISCORD_WEBHOOK_URL", "")
    webhook_ok = False
    if webhook_url and webhook_url.startswith("https://discord.com/api/webhooks/"):
        header("PRUEBA DE WEBHOOK")
        webhook_ok = await test_webhook(webhook_url)
    else:
        warn("Webhook URL no proporcionada o inválida — omitiendo prueba.")

    # 4. Test bot token
    bot_token = discord_cfg.get("DISCORD_BOT_TOKEN", "")
    token_ok = False
    if bot_token and bot_token != "your-discord-token":
        header("PRUEBA DE TOKEN DE BOT")
        token_ok = await test_bot_token(bot_token)
    else:
        warn("Token de bot no proporcionado o es el valor de ejemplo — omitiendo prueba.")

    # 5. Save to .env
    header("GUARDANDO CONFIGURACIÓN")
    merged = {**current_env, **discord_cfg}
    write_env(merged)
    ok(f".env actualizado en {ENV_PATH}")

    # 6. Patch PM2 ecosystem config
    header("VERIFICANDO ECOSYSTEM.CONFIG.CJS")
    patch_ecosystem_config()

    # 7. Register slash commands
    header("REGISTRO DE SLASH COMMANDS")
    register_slash_commands()

    # 8. Print summary and next steps
    header("RESUMEN Y PRÓXIMOS PASOS")
    print(f"  {'DISCORD_BOT_TOKEN':<25} {'✔ configurado' if bot_token else '✖ falta'}")
    print(f"  {'DISCORD_WEBHOOK_URL':<25} {'✔ ' + ('testeado' if webhook_ok else 'configurado') if webhook_url else '✖ falta'}")
    print(f"  {'DISCORD_GUILD_ID':<25} {'✔ configurado' if discord_cfg.get('DISCORD_GUILD_ID') else '✖ falta'}")
    print(f"  {'DISCORD_ENABLED':<25} {'✔ true'}")
    print()

    if not webhook_ok or not token_ok:
        warn("Algunas pruebas fallaron — verifica tus credenciales en Discord Developer Portal.")

    print(f"{BOLD}Para arrancar el bot con PM2 (desde cmd.exe, NO PowerShell):{RESET}")
    print(f"  cd {ROOT / 'discord_bot'}")
    print(f"  pm2 start ecosystem.config.cjs")
    print(f"  pm2 save")
    print()
    print(f"{BOLD}Para ver logs del bot:{RESET}")
    print(f"  pm2 logs nexo-discord-bot")
    print()
    ok("Setup de Discord completado.")


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Cancelado por el usuario.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
