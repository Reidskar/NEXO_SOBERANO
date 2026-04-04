# ============================================================
# NEXO SOBERANO — Platform API Routes v1.0
# © 2026 elanarcocapital.com
# Endpoints: intel tiempo real, marketing, OBS, Drive, app
# ============================================================
from __future__ import annotations
import logging
import os
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger("NEXO.routes.platform")
router = APIRouter(prefix="/api/platform", tags=["platform"])
NEXO_API_KEY = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")

def _auth(key: Optional[str]):
    if key != NEXO_API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


# ── INTEL EN TIEMPO REAL ──────────────────────────────────────────────────────

@router.get("/intel/status")
async def intel_status():
    from NEXO_CORE.services.realtime_intel import realtime_intel
    return realtime_intel.get_status()

@router.post("/intel/fetch")
async def intel_fetch_now(background_tasks: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    from NEXO_CORE.services.realtime_intel import realtime_intel
    from backend.routes.globe_control import broadcast_command
    realtime_intel.set_broadcast(broadcast_command)
    background_tasks.add_task(realtime_intel.broadcast_intel)
    return {"queued": True, "message": "Fetching intel from all sources..."}

@router.get("/intel/live")
async def intel_live_data():
    """Devuelve los eventos de intel más recientes (no requiere auth — público)."""
    from NEXO_CORE.services.realtime_intel import realtime_intel
    data = await realtime_intel.fetch_all()
    return {"events": data["events"][:30], "aircraft": data["points"][:20], "headlines": data.get("headlines", [])}


# ── DRIVE / PHOTOS → GLOBE ────────────────────────────────────────────────────

@router.post("/drive/sync-globe")
async def drive_sync_to_globe(background_tasks: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    """Clasifica evidencia de Drive/Photos con Gemma 4 y la mapea al globo."""
    _auth(x_api_key)
    from backend.services.drive_intel_bridge import drive_intel_bridge
    from backend.routes.globe_control import broadcast_command

    async def _run():
        events = await drive_intel_bridge.procesar_drive_reciente()
        photos = await drive_intel_bridge.procesar_fotos_contexto()
        for ev in (events + photos):
            await broadcast_command(ev)
        return len(events) + len(photos)

    background_tasks.add_task(_run)
    return {"queued": True, "message": "Procesando Drive + Photos → OmniGlobe"}


# ── MARKETING ─────────────────────────────────────────────────────────────────

class PostRequest(BaseModel):
    evento: str
    lat: float = 0
    lng: float = 0
    fuente: str = ""
    publicar: bool = False

class HiloRequest(BaseModel):
    tema: str
    tweets: int = 5

@router.post("/marketing/post")
async def generar_post(body: PostRequest, x_api_key: Optional[str] = Header(None)):
    """Genera post de X para evento geopolítico con Gemma 4."""
    _auth(x_api_key)
    from backend.services.marketing_engine import marketing_engine
    post = await marketing_engine.generar_post_geopolitico(body.evento, body.lat, body.lng, body.fuente)
    if body.publicar:
        result = await marketing_engine.publicar_en_x(post["tweet"])
        post["publicacion"] = result
    return post

@router.post("/marketing/hilo")
async def generar_hilo(body: HiloRequest, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    from backend.services.marketing_engine import marketing_engine
    tweets = await marketing_engine.generar_hilo_tecnico(body.tema, body.tweets)
    return {"tema": body.tema, "tweets": tweets, "total": len(tweets)}

@router.get("/marketing/calendario")
async def calendario_editorial(dias: int = 7, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    from backend.services.marketing_engine import marketing_engine
    calendario = await marketing_engine.generar_calendario_editorial(dias)
    return {"dias": dias, "calendario": calendario}

@router.post("/marketing/narrativa-globo")
async def narrativa_globo(x_api_key: Optional[str] = Header(None)):
    """Genera narrativa geopolítica de los eventos activos del globo → overlay."""
    _auth(x_api_key)
    from backend.services.marketing_engine import marketing_engine
    from NEXO_CORE.services.realtime_intel import realtime_intel
    from backend.routes.globe_control import broadcast_command
    events = realtime_intel._last_events[:8]
    narrativa = await marketing_engine.generar_narrativa_globo(events)
    if narrativa:
        await broadcast_command({"type": "narrative", "text": narrativa, "duration": 12000})
    return {"narrativa": narrativa}


# ── OBS COORDINATOR ──────────────────────────────────────────────────────────

@router.get("/obs/status")
async def obs_status():
    from backend.services.obs_coordinator import obs_coordinator
    return obs_coordinator.get_status()

@router.post("/obs/connect")
async def obs_connect(x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    from backend.services.obs_coordinator import obs_coordinator
    ok = await obs_coordinator.connect()
    return {"connected": ok}

@router.post("/obs/scene/{scene_key}")
async def obs_scene(scene_key: str, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    from backend.services.obs_coordinator import obs_coordinator
    ok = await obs_coordinator.cambiar_escena(scene_key)
    return {"success": ok, "scene": scene_key}

@router.post("/obs/capture")
async def obs_capture(x_api_key: Optional[str] = Header(None)):
    """Captura screenshot del OmniGlobe en OBS."""
    _auth(x_api_key)
    from backend.services.obs_coordinator import obs_coordinator
    path = await obs_coordinator.captura_pantalla()
    return {"path": path, "success": path is not None}

@router.post("/obs/sync-intel")
async def obs_sync_intel(x_api_key: Optional[str] = Header(None)):
    """Sincroniza OBS con el estado actual del globo."""
    _auth(x_api_key)
    from backend.services.obs_coordinator import obs_coordinator
    from NEXO_CORE.services.realtime_intel import realtime_intel
    await obs_coordinator.sincronizar_con_intel(realtime_intel._last_events)
    return {"synced": True}


# ── APP / PWA INFO ────────────────────────────────────────────────────────────

@router.get("/app/info")
async def app_info():
    return {
        "name": "NEXO SOBERANO",
        "version": "1.3.0",
        "pwa": {"manifest": "/manifest.json", "sw": "/sw.js"},
        "platforms": ["web", "pwa", "discord"],
        "features": ["omniglobe_3d", "realtime_intel", "osint", "marketing", "obs"],
        "download": {"android": None, "ios": None, "pwa": "elanarcocapital.com"},
    }
