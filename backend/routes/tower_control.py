# backend/routes/tower_control.py — Remote tower management (tunnel + backend + OBS + stream)
from __future__ import annotations

import asyncio
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tower", tags=["tower-control"])

# ──────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────

def _require_api_key(key: Optional[str]) -> None:
    expected = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    if key != expected:
        raise HTTPException(status_code=401, detail="API Key inválida")


# ──────────────────────────────────────────────────────────────
# Constants — Cloudflare Tunnel
# ──────────────────────────────────────────────────────────────

CLOUDFLARED_PATH = os.getenv(
    "CLOUDFLARED_PATH",
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
)
TUNNEL_ID = os.getenv("CLOUDFLARE_TUNNEL_ID", "2205f004-b6de-4ede-a3c2-365a24afe0c2")

# Backend startup
PYTHON_PATH = os.getenv("TOWER_PYTHON", sys.executable)
BACKEND_MODULE = "backend.main:app"
BACKEND_PORT = int(os.getenv("PORT", 8000))

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _is_windows() -> bool:
    return platform.system() == "Windows"


def _process_running(name: str) -> bool:
    """Check if a process by name is running (Windows + Linux)."""
    try:
        if _is_windows():
            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {name}"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return name.lower() in out.lower()
        else:
            out = subprocess.check_output(
                ["pgrep", "-f", name], stderr=subprocess.DEVNULL, text=True
            )
            return bool(out.strip())
    except Exception:
        return False


def _tunnel_alive() -> bool:
    return _process_running("cloudflared.exe") or _process_running("cloudflared")


def _backend_alive() -> bool:
    """Probe our own health endpoint on localhost."""
    try:
        import urllib.request
        with urllib.request.urlopen(
            f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=3
        ) as r:
            return r.status < 500
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# GET /api/tower/status — comprehensive tower status
# ──────────────────────────────────────────────────────────────

@router.get("/status")
async def tower_status():
    """
    Returns real-time tower health.
    Safe to call without API key (read-only, local network only).
    """
    tunnel_up = _tunnel_alive()
    backend_up = _backend_alive()

    obs_status = "unknown"
    try:
        from NEXO_CORE.core.state_manager import state_manager as sm
        obs_status = "connected" if sm.snapshot().get("obs_connected") else "disconnected"
    except Exception:
        obs_status = "not_configured"

    return {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform.system(),
        "backend": {
            "alive": backend_up,
            "port": BACKEND_PORT,
            "module": BACKEND_MODULE,
        },
        "tunnel": {
            "alive": tunnel_up,
            "tunnel_id": TUNNEL_ID,
            "cloudflared": CLOUDFLARED_PATH,
        },
        "obs": obs_status,
        "domain": "elanarcocapital.com",
        "diagnosis": _make_diagnosis(backend_up, tunnel_up),
    }


def _make_diagnosis(backend: bool, tunnel: bool) -> str:
    if backend and tunnel:
        return "All systems operational"
    if backend and not tunnel:
        return "Backend alive but tunnel is DOWN — domain unreachable. Restart tunnel."
    if not backend and tunnel:
        return "Tunnel running but backend is DOWN — API unreachable."
    return "Both backend and tunnel are DOWN — full restart needed."


# ──────────────────────────────────────────────────────────────
# POST /api/tower/restart-tunnel
# ──────────────────────────────────────────────────────────────

class RestartResult(BaseModel):
    ok: bool
    message: str
    pid: Optional[int] = None


@router.post("/restart-tunnel", response_model=RestartResult)
async def restart_tunnel(x_api_key: str = Header(None)):
    _require_api_key(x_api_key)

    if not _is_windows():
        # Linux / Railway — cloudflared runs differently
        try:
            proc = subprocess.Popen(
                ["cloudflared", "tunnel", "run", TUNNEL_ID],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return RestartResult(ok=True, message="Tunnel restarted (Linux)", pid=proc.pid)
        except FileNotFoundError:
            raise HTTPException(status_code=503, detail="cloudflared not found in PATH")

    # Windows path
    if not Path(CLOUDFLARED_PATH).exists():
        raise HTTPException(
            status_code=503,
            detail=f"cloudflared.exe not found at: {CLOUDFLARED_PATH}",
        )

    try:
        # Kill any existing cloudflared
        subprocess.run(
            ["taskkill", "/F", "/IM", "cloudflared.exe"],
            capture_output=True,
        )
        await asyncio.sleep(1)

        proc = subprocess.Popen(
            [CLOUDFLARED_PATH, "tunnel", "run", TUNNEL_ID],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        await asyncio.sleep(2)

        if _tunnel_alive():
            logger.info(f"[TOWER] Cloudflare tunnel restarted, PID={proc.pid}")
            return RestartResult(ok=True, message="Tunnel restarted successfully", pid=proc.pid)
        else:
            return RestartResult(ok=False, message="Tunnel process launched but may not be running yet")

    except Exception as exc:
        logger.error(f"[TOWER] Failed to restart tunnel: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ──────────────────────────────────────────────────────────────
# POST /api/tower/restart-backend
# ──────────────────────────────────────────────────────────────

@router.post("/restart-backend")
async def restart_backend(x_api_key: str = Header(None)):
    """
    Launches a new uvicorn process. Works only on Windows when called from a
    long-running supervisor — otherwise the process dies with the response.
    Prefer using the Windows Task Scheduler / AUTOSTART_TORRE.bat to keep it alive.
    """
    _require_api_key(x_api_key)

    project_root = str(Path(__file__).resolve().parents[2])

    if _is_windows():
        bat = Path(project_root) / "INICIAR_TODO.bat"
        if bat.exists():
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat)],
                cwd=project_root,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            return {"ok": True, "message": "INICIAR_TODO.bat launched"}
        else:
            return {"ok": False, "message": "INICIAR_TODO.bat not found; start manually"}
    else:
        # Linux: restart via systemd or supervisor (not implemented here)
        return {"ok": False, "message": "Backend restart not supported on this platform via API"}


# ──────────────────────────────────────────────────────────────
# POST /api/tower/stream/start  |  /stop  |  GET /status
# ──────────────────────────────────────────────────────────────

class StreamAction(BaseModel):
    action: str = "start"        # start | stop | toggle
    record: bool = False          # also start recording


@router.post("/stream")
async def control_stream(payload: StreamAction, x_api_key: str = Header(None)):
    _require_api_key(x_api_key)
    try:
        from NEXO_CORE.services.obs_manager import obs_manager
        from NEXO_CORE.core.state_manager import state_manager

        connected = await obs_manager.ensure_connected()
        if not connected:
            raise HTTPException(status_code=503, detail="OBS not connected — open OBS on the torre and enable WebSocket (Tools > WebSocket Server Settings)")

        if payload.action in ("start", "toggle"):
            ok, err = await obs_manager.set_stream_active(True)
            if not ok:
                raise HTTPException(status_code=500, detail=err or "Failed to start stream")
            if payload.record:
                try:
                    await asyncio.to_thread(obs_manager._client.start_record)
                except Exception:
                    pass  # recording failure non-fatal
            return {"ok": True, "action": "stream_started", "streaming": True}

        elif payload.action == "stop":
            ok, err = await obs_manager.set_stream_active(False)
            if not ok:
                raise HTTPException(status_code=500, detail=err or "Failed to stop stream")
            return {"ok": True, "action": "stream_stopped", "streaming": False}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}. Use: start | stop | toggle")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stream/status")
async def stream_status():
    """OBS streaming/recording status — no auth needed (read-only)."""
    try:
        from NEXO_CORE.services.obs_manager import obs_manager
        from NEXO_CORE.core.state_manager import state_manager

        snap = state_manager.snapshot()
        obs_connected = snap.get("obs_connected", False)

        if not obs_connected or obs_manager._client is None:
            # Try a quick reconnect
            await obs_manager.connect()
            obs_connected = state_manager.snapshot().get("obs_connected", False)

        if not obs_connected:
            return {
                "obs_connected": False,
                "streaming": None,
                "recording": None,
                "hint": "OBS not connected. Make sure OBS is open and WebSocket is enabled on port 4455.",
            }

        streaming = await obs_manager.get_stream_active()

        # Try to get record status
        recording = None
        try:
            rec = await asyncio.to_thread(obs_manager._client.get_record_status)
            recording = getattr(rec, "output_active", None)
        except Exception:
            pass

        # Get current scene
        scene = await obs_manager.get_current_scene()

        return {
            "obs_connected": True,
            "streaming": streaming,
            "recording": recording,
            "current_scene": scene,
        }
    except Exception as exc:
        return {"obs_connected": False, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# GET /api/tower/logs — tail last N lines of uvicorn log
# ──────────────────────────────────────────────────────────────

@router.get("/logs")
async def tail_logs(n: int = 50, x_api_key: str = Header(None)):
    _require_api_key(x_api_key)

    log_candidates = [
        Path("logs/nexo.log"),
        Path("logs/backend.log"),
        Path("uvicorn.log"),
    ]
    for lp in log_candidates:
        if lp.exists():
            lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
            return {"file": str(lp), "lines": lines[-n:]}

    return {"file": None, "lines": [], "note": "No log file found"}


# ──────────────────────────────────────────────────────────────
# GET /api/tower/ping — fast liveness check (no auth)
# ──────────────────────────────────────────────────────────────

@router.get("/ping")
async def ping():
    return {"pong": True, "ts": datetime.now(timezone.utc).isoformat()}


# ──────────────────────────────────────────────────────────────
# POST /api/tower/discord/register — register slash commands
# ──────────────────────────────────────────────────────────────

@router.post("/discord/register")
async def discord_register_commands(x_api_key: str = Header(None)):
    """Registers all NEXO slash commands with Discord API from the tower."""
    _require_api_key(x_api_key)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "register_discord_commands",
            Path(__file__).resolve().parents[2] / "scripts" / "register_discord_commands.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.register_commands()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
