#!/usr/bin/env python3
"""scripts/setup_obs.py — Configuración guiada de OBS WebSocket para NEXO SOBERANO"""

import asyncio
import os
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

def info(msg: str)   -> None: print(f"{CYAN}ℹ  {msg}{RESET}")
def ok(msg: str)     -> None: print(f"{GREEN}✔  {msg}{RESET}")
def warn(msg: str)   -> None: print(f"{YELLOW}⚠  {msg}{RESET}")
def error(msg: str)  -> None: print(f"{RED}✖  {msg}{RESET}")
def header(msg: str) -> None: print(f"\n{BOLD}{WHITE}{'─'*60}\n   {msg}\n{'─'*60}{RESET}")
def prompt(msg: str) -> str:  return input(f"{CYAN}▶  {msg}{RESET}").strip()


# ---------------------------------------------------------------------------
# Scene key definitions
# ---------------------------------------------------------------------------
NEXO_SCENE_KEYS = {
    "OBS_SCENE_IDLE":     ("idle",       "NEXO - Standby"),
    "OBS_SCENE_MONITOR":  ("monitoring", "NEXO - Monitor"),
    "OBS_SCENE_ALERT":    ("alert",      "NEXO - Alerta"),
    "OBS_SCENE_CRITICAL": ("critical",   "NEXO - Crítico"),
    "OBS_SCENE_GLOBE":    ("globe",      "NEXO - OmniGlobe"),
    "OBS_SCENE_ANALYSIS": ("analysis",   "NEXO - Análisis"),
}


# ---------------------------------------------------------------------------
# .env helpers
# ---------------------------------------------------------------------------
ENV_PATH = ROOT / ".env"


def read_env() -> dict[str, str]:
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

    for key, val in env.items():
        if key not in patched_keys:
            result.append(f"{key}={val}\n")

    ENV_PATH.write_text("".join(result), encoding="utf-8")


# ---------------------------------------------------------------------------
# OBS WebSocket connection (obsws-python)
# ---------------------------------------------------------------------------

def import_obsws():
    """Try to import obsws-python; return the module or None."""
    try:
        import obsws_python as obs
        return obs
    except ImportError:
        return None


def ensure_obsws_installed() -> bool:
    """Check obsws-python availability, prompt to install if missing."""
    obs = import_obsws()
    if obs is not None:
        return True

    warn("obsws-python no está instalado.")
    choice = prompt("¿Instalar ahora con pip? (s/N): ").lower()
    if choice in ("s", "si", "sí", "y", "yes"):
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "obsws-python"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ok("obsws-python instalado correctamente.")
            return True
        else:
            error("No se pudo instalar obsws-python:")
            print(result.stderr.strip())
            return False
    else:
        warn("Continuando sin probar conexión OBS.")
        return False


def connect_obs(host: str, port: int, password: str):
    """Connect to OBS WebSocket and return client or None."""
    obs = import_obsws()
    if obs is None:
        return None
    try:
        client = obs.ReqClient(host=host, port=port, password=password, timeout=5)
        return client
    except Exception as exc:
        error(f"No se pudo conectar a OBS: {exc}")
        return None


def get_scene_list(client) -> list[str]:
    """Return list of scene names from OBS."""
    try:
        resp = client.get_scene_list()
        # obsws-python returns scenes as list of dicts with 'sceneName'
        scenes = resp.scenes if hasattr(resp, "scenes") else []
        return [s.get("sceneName", s) if isinstance(s, dict) else str(s) for s in scenes]
    except Exception as exc:
        warn(f"No se pudo obtener la lista de escenas: {exc}")
        return []


def create_scene(client, scene_name: str) -> bool:
    """Create a new scene in OBS."""
    try:
        client.create_scene(scene_name)
        ok(f"Escena creada: '{scene_name}'")
        return True
    except Exception as exc:
        warn(f"No se pudo crear escena '{scene_name}': {exc}")
        return False


def switch_scene(client, scene_name: str) -> bool:
    """Switch OBS to the given scene."""
    try:
        client.set_current_program_scene(scene_name)
        ok(f"Escena activa: '{scene_name}'")
        return True
    except Exception as exc:
        warn(f"No se pudo cambiar a escena '{scene_name}': {exc}")
        return False


# ---------------------------------------------------------------------------
# Interactive setup helpers
# ---------------------------------------------------------------------------

def collect_obs_connection(current: dict[str, str]) -> tuple[str, int, str]:
    """Ask user for OBS host, port, password."""
    header("CONEXIÓN OBS WEBSOCKET")

    host = prompt(f"OBS_HOST (actual: {current.get('OBS_HOST', 'localhost')}): ") \
        or current.get("OBS_HOST", "localhost")

    port_str = prompt(f"OBS_PORT (actual: {current.get('OBS_PORT', '4455')}): ") \
        or current.get("OBS_PORT", "4455")
    try:
        port = int(port_str)
    except ValueError:
        warn(f"Puerto inválido '{port_str}', usando 4455.")
        port = 4455

    current_pass = current.get("OBS_PASSWORD", "")
    masked_pass = "***" if current_pass else "(vacío)"
    new_pass = prompt(f"OBS_PASSWORD (actual: {masked_pass}): ")
    password = new_pass if new_pass else current_pass

    return host, port, password


def assign_scene_names(
    client,
    current: dict[str, str],
    existing_scenes: list[str],
) -> dict[str, str]:
    """Let user assign OBS scene names to NEXO scene keys."""
    header("ASIGNACIÓN DE ESCENAS")

    if existing_scenes:
        info("Escenas existentes en OBS:")
        for i, s in enumerate(existing_scenes, 1):
            print(f"  {i:>2}. {s}")
    else:
        warn("No se encontraron escenas en OBS o no hay conexión.")

    scene_updates: dict[str, str] = {}
    scenes_to_create: list[str] = []

    for env_key, (label, default_name) in NEXO_SCENE_KEYS.items():
        current_val = current.get(env_key, default_name)
        info(f"\nEscena NEXO '{label}' → clave: {env_key}")
        info(f"  Sugerencia: '{default_name}'  |  Valor actual: '{current_val}'")
        user_input = prompt(f"  Nombre de escena OBS (Enter para usar '{current_val}'): ")
        chosen = user_input if user_input else current_val
        scene_updates[env_key] = chosen

        if client is not None and existing_scenes and chosen not in existing_scenes:
            create_choice = prompt(
                f"  '{chosen}' no existe en OBS. ¿Crear automáticamente? (s/N): "
            ).lower()
            if create_choice in ("s", "si", "sí", "y", "yes"):
                scenes_to_create.append(chosen)

    # Create missing scenes
    if client is not None and scenes_to_create:
        header("CREANDO ESCENAS FALTANTES")
        for scene_name in scenes_to_create:
            create_scene(client, scene_name)

    return scene_updates


def test_scene_switching(client, scene_name: str) -> None:
    """Quick test: switch to scene and back."""
    if client is None:
        warn("Sin conexión OBS — omitiendo prueba de cambio de escena.")
        return
    header("PRUEBA DE CAMBIO DE ESCENA")
    info(f"Cambiando a escena '{scene_name}' para probar…")
    if switch_scene(client, scene_name):
        ok("Cambio de escena exitoso.")
    else:
        warn("El cambio de escena falló. Verifica que la escena exista en OBS.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        _main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Cancelado por el usuario.{RESET}")
        sys.exit(0)


def _main() -> None:
    header("NEXO SOBERANO — Setup de OBS WebSocket")
    info(f"Directorio raíz: {ROOT}")

    # 1. Read current .env
    current_env = read_env()

    # 2. Check / install obsws-python
    obsws_available = ensure_obsws_installed()

    # 3. Collect connection params
    host, port, password = collect_obs_connection(current_env)

    # 4. Try to connect
    client = None
    if obsws_available:
        header("PROBANDO CONEXIÓN OBS")
        info(f"Conectando a ws://{host}:{port} …")
        client = connect_obs(host, port, password)
        if client:
            ok("Conexión OBS establecida.")
        else:
            warn("No se pudo conectar — continuando con configuración manual.")
            warn("Asegúrate de que OBS esté abierto con WebSocket Server activado.")
    else:
        warn("obsws-python no disponible — la configuración será solo manual.")

    # 5. List existing scenes
    existing_scenes: list[str] = []
    if client:
        existing_scenes = get_scene_list(client)
        if existing_scenes:
            info(f"Escenas detectadas: {len(existing_scenes)}")

    # 6. Assign scene names
    scene_updates = assign_scene_names(client, current_env, existing_scenes)

    # 7. Test scene switching with the idle scene
    idle_scene = scene_updates.get("OBS_SCENE_IDLE", "NEXO - Standby")
    test_scene_switching(client, idle_scene)

    # 8. Build final env updates
    obs_cfg: dict[str, str] = {
        "OBS_HOST":    host,
        "OBS_PORT":    str(port),
        "OBS_PASSWORD": password,
        "OBS_ENABLED": "true",
        **scene_updates,
    }

    # 9. Save to .env
    header("GUARDANDO CONFIGURACIÓN")
    merged = {**current_env, **obs_cfg}
    write_env(merged)
    ok(f".env actualizado en {ENV_PATH}")

    # 10. Print final config summary
    header("RESUMEN DE CONFIGURACIÓN OBS")
    col_w = 24
    print(f"  {'Variable':<{col_w}} {'Valor'}")
    print(f"  {'─'*col_w} {'─'*30}")
    for key in ["OBS_HOST", "OBS_PORT", "OBS_PASSWORD", "OBS_ENABLED"]:
        val = obs_cfg.get(key, "")
        display = "***" if key == "OBS_PASSWORD" and val else val
        print(f"  {key:<{col_w}} {display}")
    print()
    for env_key, (label, _) in NEXO_SCENE_KEYS.items():
        val = scene_updates.get(env_key, "(no configurado)")
        print(f"  {env_key:<{col_w}} {val}")

    print()
    if client:
        ok("OBS conectado y escenas configuradas.")
    else:
        warn("OBS no disponible durante el setup — verifica la conexión manualmente.")

    print(f"\n{BOLD}Para verificar la conexión OBS en el backend:{RESET}")
    print(f"  python scripts/nexo_manager.py diagnose")
    print()
    print(f"{BOLD}Para arrancar el backend con OBS habilitado:{RESET}")
    print(f"  .venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    print()
    ok("Setup de OBS completado.")


if __name__ == "__main__":
    main()
