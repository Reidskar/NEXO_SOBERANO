# ============================================================
# NEXO SOBERANO — OSINT Routes v1.0
# © 2026 elanarcocapital.com
# Endpoints: /api/osint/*  →  BigBrother + Gemma 4
# ============================================================
from __future__ import annotations
import logging
import os
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("NEXO.routes.osint")

router = APIRouter(prefix="/api/osint", tags=["osint"])

NEXO_API_KEY = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")


def _require_key(x_api_key: Optional[str]):
    if x_api_key != NEXO_API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


# ── REQUEST MODELS ───────────────────────────────────────────────────────────

class UsernameRequest(BaseModel):
    username: str

class EmailRequest(BaseModel):
    email: str

class ScanRequest(BaseModel):
    target: str
    ports: str = "top100"

class AircraftRequest(BaseModel):
    callsign: str = ""
    icao: str = ""

class DarkwebRequest(BaseModel):
    keyword: str

class ProfileRequest(BaseModel):
    target: str
    target_type: str = "username"   # username | email | ip | phone


# ── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.get("/status")
async def osint_status():
    """Estado de BigBrother + Gemma 4 (público)."""
    from backend.services.big_brother_bridge import big_brother_bridge
    return await big_brother_bridge.status()


@router.post("/username")
async def search_username(
    body: UsernameRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Rastreo de usuario en múltiples plataformas (OSINT + Gemma 4)."""
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    result = await big_brother_bridge.investigate_username(body.username)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "BigBrother error"))
    return result


@router.post("/breach")
async def lookup_breach(
    body: EmailRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Busca brechas de datos para un email."""
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    result = await big_brother_bridge.investigate_breach(body.email)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return result


@router.post("/scan")
async def scan_network(
    body: ScanRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Escaneo de red/host con análisis automático."""
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    result = await big_brother_bridge.scan_target(body.target, body.ports)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return result


@router.post("/aircraft")
async def track_aircraft(
    body: AircraftRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Rastrea aeronave en tiempo real → genera punto en globo."""
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    result = await big_brother_bridge.track_aircraft_live(body.callsign, body.icao)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return result


@router.post("/darkweb")
async def darkweb_monitor(
    body: DarkwebRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Monitorea dark web para una keyword."""
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    result = await big_brother_bridge.monitor_darkweb(body.keyword)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return result


@router.post("/profile")
async def full_profile(
    body: ProfileRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Perfil OSINT completo de un objetivo.
    Orquesta múltiples herramientas + análisis Gemma 4.
    Resultado puede incluir globe_event para visualización inmediata.
    """
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    result = await big_brother_bridge.full_profile(body.target, body.target_type)
    return result


@router.post("/globe/inject")
async def inject_osint_to_globe(
    body: ProfileRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Perfil OSINT completo → publica resultado en el OmniGlobe automáticamente.
    Requiere globe_event con lat/lng en el resultado.
    """
    _require_key(x_api_key)
    from backend.services.big_brother_bridge import big_brother_bridge
    from backend.routes.globe_control import broadcast_command

    result = await big_brother_bridge.full_profile(body.target, body.target_type)

    # Extraer primer globe_event disponible
    injected = False
    for module_key, module_data in result.get("modules", {}).items():
        event = module_data.get("globe_event") if isinstance(module_data, dict) else None
        if event and event.get("lat"):
            await broadcast_command({
                "type": "add_event",
                "id": f"osint_{body.target.replace('@', '_').replace('.', '_')}",
                **event,
            })
            injected = True
            break

    return {**result, "globe_injected": injected}
