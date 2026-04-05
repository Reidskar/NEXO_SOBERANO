"""
backend/routes/nexo_integrations.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hub unificado de integraciones: Discord + OBS + Estado global.

Endpoints:
  GET  /api/integrations/status            — estado de todas las integraciones
  POST /api/integrations/discord/send      — enviar mensaje/embed via webhook
  POST /api/integrations/discord/alert     — alerta con embed formateado
  POST /api/integrations/obs/scene         — cambiar escena OBS
  POST /api/integrations/obs/recording     — start/stop grabación
  POST /api/integrations/obs/screenshot    — captura de pantalla
  GET  /api/integrations/obs/scenes        — listar escenas disponibles
  POST /api/integrations/globe-event       — evento globo → Discord + OBS
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger("NEXO.integrations")
router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# ─── API Key guard ────────────────────────────────────────────────────────────

def _check_key(key: Optional[str]):
    expected = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    if key != expected:
        raise HTTPException(status_code=401, detail="API Key inválida")

# ─── Models ───────────────────────────────────────────────────────────────────

class DiscordSendRequest(BaseModel):
    content:    Optional[str] = None
    title:      Optional[str] = None
    description:Optional[str] = None
    color:      Optional[int] = 0x00e5ff   # cyan NEXO
    fields:     Optional[list] = None      # [{"name": "...", "value": "..."}]
    footer:     Optional[str] = None

class OBSSceneRequest(BaseModel):
    scene:    str           # idle | monitoring | alert | critical | globe | analysis | <nombre exacto>
    duration: Optional[int] = None  # ms — si se especifica, vuelve a la escena anterior

class OBSRecordingRequest(BaseModel):
    action: str = "toggle"  # start | stop | toggle

class GlobeEventRequest(BaseModel):
    event_id:   str
    name:       str
    lat:        float
    lng:        float
    severity:   str = "MODERATE"   # CRITICAL | HIGH | MODERATE | MONITOR
    description:str = ""
    source:     str = "nexo"
    notify_discord: bool = True
    switch_obs:     bool = True

# ─── Discord helpers ──────────────────────────────────────────────────────────

SEVERITY_COLORS = {
    "CRITICAL": 0xef4444,
    "HIGH":     0xf97316,
    "MODERATE": 0xf59e0b,
    "MONITOR":  0x00e5ff,
    "OK":       0x10b981,
    "INFO":     0x3b82f6,
}

SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MODERATE": "🟡",
    "MONITOR":  "🔵",
    "OK":       "🟢",
    "INFO":     "⚪",
}

async def _discord_send(content: str | None = None, embeds: list | None = None) -> bool:
    try:
        import aiohttp
        url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not url:
            logger.warning("DISCORD_WEBHOOK_URL no configurada")
            return False
        payload: dict = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as r:
                ok = r.status in (200, 204)
                if not ok:
                    logger.warning(f"Discord webhook error: {r.status}")
                return ok
    except Exception as e:
        logger.error(f"Discord send error: {e}")
        return False

def _build_embed(req: DiscordSendRequest) -> dict:
    embed: dict = {"color": req.color or 0x00e5ff}
    if req.title:
        embed["title"] = req.title
    if req.description:
        embed["description"] = req.description
    if req.fields:
        embed["fields"] = [
            {"name": f.get("name",""), "value": f.get("value",""), "inline": f.get("inline", False)}
            for f in req.fields
        ]
    embed["footer"] = {"text": req.footer or f"NEXO SOBERANO · {datetime.now(timezone.utc).strftime('%H:%M UTC')}"}
    return embed

# ─── OBS helpers ──────────────────────────────────────────────────────────────

def _get_obs():
    """Retorna cliente OBS o None si no está disponible."""
    try:
        import obsws_python as obs
        host = os.getenv("OBS_HOST", "localhost")
        port = int(os.getenv("OBS_PORT", "4455"))
        pwd  = os.getenv("OBS_PASSWORD", "")
        if not pwd:
            return None
        return obs.ReqClient(host=host, port=port, password=pwd, timeout=5)
    except Exception as e:
        logger.debug(f"OBS no disponible: {e}")
        return None

SCENE_MAP = {
    "idle":       os.getenv("OBS_SCENE_IDLE",     "NEXO - Standby"),
    "monitoring": os.getenv("OBS_SCENE_MONITOR",  "NEXO - Monitor"),
    "alert":      os.getenv("OBS_SCENE_ALERT",    "NEXO - Alerta"),
    "critical":   os.getenv("OBS_SCENE_CRITICAL", "NEXO - Crítico"),
    "globe":      os.getenv("OBS_SCENE_GLOBE",    "NEXO - OmniGlobe"),
    "analysis":   os.getenv("OBS_SCENE_ANALYSIS", "NEXO - Análisis"),
}

SEVERITY_TO_OBS = {
    "CRITICAL": "critical",
    "HIGH":     "alert",
    "MODERATE": "monitoring",
    "MONITOR":  "globe",
}

def _obs_switch_scene(scene_key: str) -> bool:
    scene_name = SCENE_MAP.get(scene_key, scene_key)
    client = _get_obs()
    if not client:
        logger.info(f"[OBS SIM] Escena → {scene_name}")
        return True
    try:
        client.set_current_program_scene(scene_name)
        logger.info(f"OBS escena → {scene_name}")
        return True
    except Exception as e:
        logger.warning(f"OBS scene switch error: {e}")
        return False

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def integrations_status():
    """Estado en tiempo real de todas las integraciones."""
    discord_ok = bool(os.getenv("DISCORD_WEBHOOK_URL") and os.getenv("DISCORD_ENABLED", "false") == "true")
    obs_ok     = bool(os.getenv("OBS_PASSWORD") and os.getenv("OBS_ENABLED", "false") == "true")

    obs_scenes = []
    if obs_ok:
        client = _get_obs()
        if client:
            try:
                resp = client.get_scene_list()
                obs_scenes = [s["sceneName"] for s in resp.scenes]
            except Exception:
                obs_ok = False

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "discord": {
            "enabled":  discord_ok,
            "webhook":  bool(os.getenv("DISCORD_WEBHOOK_URL")),
            "token":    bool(os.getenv("DISCORD_TOKEN")),
            "guild_id": os.getenv("DISCORD_GUILD_ID", ""),
        },
        "obs": {
            "enabled":       obs_ok,
            "host":          os.getenv("OBS_HOST", "localhost"),
            "port":          os.getenv("OBS_PORT", "4455"),
            "password_set":  bool(os.getenv("OBS_PASSWORD")),
            "scene_map":     SCENE_MAP,
            "scenes_found":  obs_scenes,
        },
    }


@router.post("/discord/send")
async def discord_send(req: DiscordSendRequest, x_api_key: str = Header(None)):
    _check_key(x_api_key)
    embeds = [_build_embed(req)] if (req.title or req.description) else None
    ok = await _discord_send(content=req.content, embeds=embeds)
    if not ok:
        raise HTTPException(status_code=503, detail="Discord webhook no disponible")
    return {"sent": True}


@router.post("/discord/alert")
async def discord_alert(req: GlobeEventRequest, x_api_key: str = Header(None)):
    """Alerta formateada al Discord con datos del evento geopolítico."""
    emoji = SEVERITY_EMOJI.get(req.severity, "⚪")
    color = SEVERITY_COLORS.get(req.severity, 0x00e5ff)
    embed = {
        "title":       f"{emoji} {req.severity} — {req.name}",
        "description": req.description or f"Evento detectado en {req.lat:.2f}°, {req.lng:.2f}°",
        "color":       color,
        "fields": [
            {"name": "Coordenadas", "value": f"`{req.lat:.4f}°, {req.lng:.4f}°`", "inline": True},
            {"name": "Fuente",      "value": req.source.upper(), "inline": True},
            {"name": "ID",          "value": f"`{req.event_id}`", "inline": True},
        ],
        "footer": {"text": f"NEXO SOBERANO · OmniGlobe · {datetime.now(timezone.utc).strftime('%H:%M UTC')}"},
    }
    ok = await _discord_send(embeds=[embed])
    return {"sent": ok, "event_id": req.event_id}


@router.post("/obs/scene")
async def obs_scene(req: OBSSceneRequest, x_api_key: str = Header(None)):
    _check_key(x_api_key)
    ok = _obs_switch_scene(req.scene)
    return {"switched": ok, "scene": req.scene, "resolved": SCENE_MAP.get(req.scene, req.scene)}


@router.get("/obs/scenes")
async def obs_scenes(x_api_key: str = Header(None)):
    client = _get_obs()
    if not client:
        return {"scenes": list(SCENE_MAP.values()), "source": "config", "connected": False}
    try:
        resp = client.get_scene_list()
        return {
            "scenes":  [s["sceneName"] for s in resp.scenes],
            "current": resp.current_program_scene_name,
            "source":  "obs_live",
            "connected": True,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/obs/recording")
async def obs_recording(req: OBSRecordingRequest, x_api_key: str = Header(None)):
    _check_key(x_api_key)
    client = _get_obs()
    if not client:
        return {"action": req.action, "simulated": True}
    try:
        if req.action == "start":
            client.start_record()
        elif req.action == "stop":
            client.stop_record()
        else:
            client.toggle_record()
        return {"action": req.action, "ok": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/obs/screenshot")
async def obs_screenshot(x_api_key: str = Header(None)):
    _check_key(x_api_key)
    client = _get_obs()
    if not client:
        return {"screenshot": None, "simulated": True}
    try:
        resp = client.get_source_screenshot(
            source_name=os.getenv("OBS_SOURCE_GLOBE", "OmniGlobe Browser"),
            image_format="png",
            image_width=1920,
            image_height=1080,
        )
        return {"screenshot": resp.image_data[:100] + "...", "format": "png", "ok": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/globe-event")
async def globe_event_bridge(req: GlobeEventRequest, x_api_key: str = Header(None)):
    """
    Punto de entrada único para eventos del OmniGlobe.
    → Notifica Discord con embed formateado
    → Cambia escena OBS según severidad
    → Devuelve estado de ambas acciones
    """
    _check_key(x_api_key)
    results: dict = {"event_id": req.event_id, "discord": False, "obs": False}

    if req.notify_discord:
        emoji = SEVERITY_EMOJI.get(req.severity, "⚪")
        color = SEVERITY_COLORS.get(req.severity, 0x00e5ff)
        embed = {
            "title":       f"{emoji} {req.severity} — {req.name}",
            "description": req.description or f"Lat {req.lat:.4f}° Lng {req.lng:.4f}°",
            "color":       color,
            "fields": [
                {"name": "Coords",  "value": f"`{req.lat:.4f}°, {req.lng:.4f}°`", "inline": True},
                {"name": "Fuente",  "value": req.source.upper(), "inline": True},
            ],
            "footer": {"text": f"NEXO OmniGlobe · {datetime.now(timezone.utc).strftime('%H:%M UTC')}"},
        }
        results["discord"] = await _discord_send(embeds=[embed])

    if req.switch_obs:
        obs_key = SEVERITY_TO_OBS.get(req.severity, "monitoring")
        results["obs"] = _obs_switch_scene(obs_key)
        results["obs_scene"] = SCENE_MAP.get(obs_key)

    return results
