"""
NEXO SOBERANO — Globe Control API
Allows AI agents (NEXO, Discord bot, voice) to send real-time commands
to all connected OmniGlobe instances via WebSocket broadcast.
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/globe", tags=["globe"])

# ── In-memory command queue (last 50 commands, consumed by WS polling) ─────────
_command_history: List[Dict] = []
_MAX_HISTORY = 50

# ── Broadcast callback — injected by main.py after ConnectionManager is ready ──
_broadcast_fn = None

def set_broadcast(fn):
    """Called by main.py: set_broadcast(lambda msg: manager.broadcast('globe', msg))"""
    global _broadcast_fn
    _broadcast_fn = fn


async def broadcast_command(payload: Dict):
    """Public helper: send a command dict directly to all OmniGlobe clients."""
    _command_history.append(payload)
    if len(_command_history) > _MAX_HISTORY:
        _command_history.pop(0)
    if _broadcast_fn:
        try:
            await _broadcast_fn({"channel": "globe_command", "payload": payload})
        except Exception as e:
            logger.warning(f"Globe broadcast_command failed: {e}")


# ── Schemas ────────────────────────────────────────────────────────────────────

class GlobeCommand(BaseModel):
    type: str                       # fly_to | add_event | remove_event | update_infra |
                                    # add_arc | remove_arc | set_layer | narrative |
                                    # highlight | reset_view | add_point | remove_point |
                                    # damage_strike | animate_arc | clear_narrative
    # fly_to
    lat: Optional[float] = None
    lng: Optional[float] = None
    altitude: Optional[float] = None
    duration: Optional[int] = 1200  # ms

    # add_event / update event
    id: Optional[str] = None
    name: Optional[str] = None
    severity: Optional[str] = None  # CRITICAL | HIGH | MODERATE | MONITOR
    radius_deg: Optional[float] = None
    desc: Optional[str] = None

    # set_layer
    layer: Optional[str] = None     # vessels | aircraft | events | arcs | infrastructure
    visible: Optional[bool] = None

    # narrative overlay
    text: Optional[str] = None
    clear_after_ms: Optional[int] = 6000

    # highlight
    entity_id: Optional[str] = None

    # arc
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None
    color_start: Optional[str] = '#ef4444'
    color_end: Optional[str] = '#f97316'
    stroke: Optional[float] = 0.6

    # damage simulation
    status: Optional[str] = None    # active | damaged | destroyed | offline
    damage_pct: Optional[float] = None

    # point
    color: Optional[str] = None
    notes: Optional[str] = None
    cat: Optional[str] = None

    # extra payload
    meta: Optional[Dict[str, Any]] = None


class CommandBatch(BaseModel):
    commands: List[GlobeCommand]
    source: Optional[str] = "nexo_ai"  # nexo_ai | discord | voice | manual


# ── Helpers ────────────────────────────────────────────────────────────────────

def _verify_api_key(key: Optional[str]) -> bool:
    expected = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    return key == expected

SEVERITY_RGB = {
    "CRITICAL": (239, 68,  68),
    "HIGH":     (249, 115, 22),
    "MODERATE": (245, 158, 11),
    "MONITOR":  (0,   229, 255),
}

def _enrich_command(cmd: GlobeCommand) -> Dict:
    d = cmd.model_dump(exclude_none=True)
    d["_ts"] = datetime.now(timezone.utc).isoformat()
    # Auto-add RGB for events if severity given
    if cmd.type == "add_event" and cmd.severity:
        rgb = SEVERITY_RGB.get(cmd.severity, (100, 100, 100))
        d.setdefault("r", rgb[0])
        d.setdefault("g", rgb[1])
        d.setdefault("b", rgb[2])
        d.setdefault("radius_deg", {"CRITICAL": 0.14, "HIGH": 0.10, "MODERATE": 0.08, "MONITOR": 0.06}.get(cmd.severity, 0.08))
        d.setdefault("period", {"CRITICAL": 800, "HIGH": 1000, "MODERATE": 1300, "MONITOR": 1600}.get(cmd.severity, 1000))
    return d


async def _dispatch(payload: Dict):
    _command_history.append(payload)
    if len(_command_history) > _MAX_HISTORY:
        _command_history.pop(0)
    if _broadcast_fn:
        try:
            await _broadcast_fn({"channel": "globe_command", "payload": payload})
        except Exception as e:
            logger.warning(f"Globe broadcast failed: {e}")


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/command")
async def globe_command(cmd: GlobeCommand, x_api_key: str = Header(None, alias="x-api-key")):
    """
    Send a single command to all connected OmniGlobe instances.
    Called by AI agents, Discord bot, voice pipeline, or manual API.
    """
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    payload = _enrich_command(cmd)
    await _dispatch(payload)
    logger.info(f"Globe command dispatched: {cmd.type} | {cmd.id or cmd.layer or cmd.text or ''}")
    return {"ok": True, "dispatched": payload}


@router.post("/commands")
async def globe_commands_batch(batch: CommandBatch, x_api_key: str = Header(None, alias="x-api-key")):
    """Send multiple commands in sequence (scenario playback)."""
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    results = []
    for cmd in batch.commands:
        payload = _enrich_command(cmd)
        await _dispatch(payload)
        results.append(payload)
    return {"ok": True, "count": len(results), "source": batch.source}


@router.get("/history")
async def globe_history(x_api_key: str = Header(None, alias="x-api-key")):
    """Return last N globe commands (for globe polling fallback)."""
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"commands": list(_command_history)}


@router.get("/poll")
async def globe_poll(since: Optional[str] = None):
    """
    Public polling endpoint — globe clients poll this every 3s.
    Returns commands newer than `since` timestamp.
    No auth required (commands are display-only, no sensitive data).
    """
    if not since:
        return {"commands": list(_command_history[-10:])}
    cmds = [c for c in _command_history if c.get("_ts", "") > since]
    return {"commands": cmds}


# ── Scenario Presets ───────────────────────────────────────────────────────────

SCENARIOS = {
    "hormuz_crisis": [
        {"type": "narrative", "text": "⚠ ESTRECHO DE HORMUZ CERRADO — Analizando impacto en cadena de suministro global...", "clear_after_ms": 8000},
        {"type": "fly_to", "lat": 26.58, "lng": 56.50, "altitude": 1.0, "duration": 2000},
        {"type": "add_event", "id": "hormuz_block", "name": "BLOQUEO TOTAL HORMUZ", "lat": 26.58, "lng": 56.50, "severity": "CRITICAL", "desc": "Cierre completo del estrecho. 21% del suministro global de petróleo afectado."},
        {"type": "add_arc", "id": "sc_hormuz_rot", "name": "Ruta petróleo bloqueada", "start_lat": 26.58, "start_lng": 56.50, "end_lat": 51.9, "end_lng": 4.5, "color_start": "#ef4444", "color_end": "#7f1d1d", "stroke": 1.0},
        {"type": "update_infra", "id": "ir_bandarabbas", "status": "offline", "damage_pct": 100},
    ],
    "ukraine_grid_strike": [
        {"type": "narrative", "text": "⚡ ATAQUE A INFRAESTRUCTURA ENERGÉTICA UCRANIANA — Evaluando pérdidas...", "clear_after_ms": 7000},
        {"type": "fly_to", "lat": 49.0, "lng": 32.0, "altitude": 1.2, "duration": 2000},
        {"type": "update_infra", "id": "ua_zaporizhzhia", "status": "destroyed", "damage_pct": 100},
        {"type": "update_infra", "id": "ua_trypilska",   "status": "destroyed", "damage_pct": 100},
        {"type": "update_infra", "id": "ua_burshtyn",    "status": "damaged",   "damage_pct": 70},
        {"type": "add_event", "id": "ua_grid_down", "name": "RED ELÉCTRICA UA — COLAPSO PARCIAL", "lat": 50.45, "lng": 30.52, "severity": "CRITICAL", "desc": "Apagones masivos en Kiev y región central. 8M personas sin electricidad."},
    ],
    "taiwan_strait": [
        {"type": "narrative", "text": "🚨 EJERCICIOS PLA — ESTRECHO DE TAIWÁN EN ALERTA MÁXIMA", "clear_after_ms": 7000},
        {"type": "fly_to", "lat": 24.5, "lng": 120.5, "altitude": 1.1, "duration": 2500},
        {"type": "set_layer", "layer": "vessels", "visible": True},
        {"type": "add_event", "id": "tw_encirclement", "name": "MANIOBRAS PLA ENCIRCLEMENT", "lat": 24.5, "lng": 120.0, "severity": "CRITICAL", "desc": "12 fragatas PLAN + 2 portaaviones en posición de bloqueo. F-22 USAF scramble desde Okinawa."},
        {"type": "add_arc", "id": "sc_usaf_tw", "name": "USAF reinforcements", "start_lat": 26.3, "start_lng": 127.8, "end_lat": 24.5, "end_lng": 120.5, "color_start": "#60a5fa", "color_end": "#1d4ed8", "stroke": 0.8},
    ],
}


@router.post("/scenario/{name}")
async def play_scenario(name: str, x_api_key: str = Header(None, alias="x-api-key")):
    """Execute a pre-built scenario sequence."""
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    scenario = SCENARIOS.get(name)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found. Available: {list(SCENARIOS.keys())}")
    results = []
    for step in scenario:
        cmd = GlobeCommand(**step)
        payload = _enrich_command(cmd)
        await _dispatch(payload)
        results.append(payload)
    return {"ok": True, "scenario": name, "steps": len(results)}


@router.get("/scenarios")
async def list_scenarios():
    """List available scenario presets."""
    return {"scenarios": list(SCENARIOS.keys())}


# ── OSINT MCP Integration ──────────────────────────────────────────────────────

@router.get("/osint/tools")
async def list_osint_tools():
    """Return all OSINT MCP servers that can feed data into the OmniGlobe."""
    try:
        from backend.config.osint_mcp_registry import OSINT_MCP_SERVERS, CATEGORIES, get_globe_servers
        return {
            "total": len(OSINT_MCP_SERVERS),
            "categories": CATEGORIES,
            "globe_capable": [s["id"] for s in get_globe_servers()],
            "servers": OSINT_MCP_SERVERS,
        }
    except ImportError:
        return {"error": "OSINT registry not found", "servers": []}
