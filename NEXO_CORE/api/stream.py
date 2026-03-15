from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from NEXO_CORE import config
from NEXO_CORE.core.state_manager import state_manager
from NEXO_CORE.middleware.rate_limit import enforce_rate_limit
from NEXO_CORE.models.stream import StreamControlRequest, StreamStatusResponse
from NEXO_CORE.services.discord_manager import discord_manager
from NEXO_CORE.services.obs_manager import obs_manager

router = APIRouter(prefix="/api/stream", tags=["stream"])


def _load_multidevice_profiles() -> Optional[Dict[str, Any]]:
    profile_path = Path(__file__).resolve().parents[2] / "obs_control" / "multidevice_stream_profiles.json"
    if not profile_path.exists():
        return None
    try:
        return json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pick_stream_profile(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    fallback = {
        "mode": "fallback",
        "profile_key": None,
        "reason": "multidevice_profile_missing",
        "recommended_upload_mbps": None,
    }
    if not data:
        return fallback

    profiles: Dict[str, Any] = data.get("profiles") or {}
    if not profiles:
        return fallback

    forced_profile = (config.STREAM_PROFILE or "auto").strip().lower()
    if forced_profile and forced_profile != "auto" and forced_profile in profiles:
        selected = profiles[forced_profile]
        return {
            "mode": "forced",
            "profile_key": forced_profile,
            "profile": selected,
            "recommended_upload_mbps": selected.get("recommended_upload_mbps"),
            "reason": "explicit_stream_profile",
        }

    device = (config.STREAM_DEVICE or "pc").strip().lower()
    upload = float(config.STREAM_UPLOAD_MBPS)

    candidates: list[tuple[str, Dict[str, Any], float]] = []
    for key, profile in profiles.items():
        req = float(profile.get("recommended_upload_mbps", 0) or 0)
        gap = upload - req
        candidates.append((key, profile, gap))

    if device.startswith("mobile") or device.startswith("phone"):
        preferred_keys = ["mobile_optimized_720p", "tablet_balanced_1080p30", "pc_stable_1080p"]
    elif device.startswith("tablet"):
        preferred_keys = ["tablet_balanced_1080p30", "mobile_optimized_720p", "pc_stable_1080p"]
    else:
        preferred_keys = ["pc_stable_1080p", "tablet_balanced_1080p30", "mobile_optimized_720p"]

    for key in preferred_keys:
        profile = profiles.get(key)
        if not profile:
            continue
        req = float(profile.get("recommended_upload_mbps", 0) or 0)
        if upload >= req and req > 0:
            return {
                "mode": "auto",
                "profile_key": key,
                "profile": profile,
                "recommended_upload_mbps": req,
                "reason": f"device={device};upload={upload}",
            }

    # Fallback: mejor perfil por brecha mínima (menos exigente)
    best_key, best_profile, _ = sorted(candidates, key=lambda item: item[2], reverse=True)[0]
    return {
        "mode": "auto",
        "profile_key": best_key,
        "profile": best_profile,
        "recommended_upload_mbps": float(best_profile.get("recommended_upload_mbps", 0) or 0),
        "reason": f"fallback_by_bandwidth;device={device};upload={upload}",
    }


async def _bool_with_timeout(coro, timeout_seconds: float, default: bool = False) -> bool:
    try:
        return bool(await asyncio.wait_for(coro, timeout=timeout_seconds))
    except Exception:
        return default


@router.get("/status", response_model=StreamStatusResponse, dependencies=[Depends(enforce_rate_limit)])
async def get_stream_status() -> StreamStatusResponse:
    await _bool_with_timeout(obs_manager.ensure_connected(), timeout_seconds=2.5, default=False)
    await _bool_with_timeout(discord_manager.health_check(), timeout_seconds=2.5, default=False)
    stream_active = await obs_manager.get_stream_active()
    current_scene = await obs_manager.get_current_scene()
    snapshot = state_manager.snapshot()
    return StreamStatusResponse(
        active=bool(snapshot["stream_active"] if stream_active is None else stream_active),
        obs_connected=snapshot["obs_connected"],
        discord_connected=snapshot["discord_connected"],
        current_scene=current_scene or snapshot["current_scene"],
    )


@router.post("/status", dependencies=[Depends(enforce_rate_limit)])
async def set_stream_status(payload: StreamControlRequest):
    obs_ok, obs_error = await obs_manager.set_stream_active(payload.active)
    current_scene = await obs_manager.get_current_scene()
    discord_ok = await discord_manager.notify_stream_state(payload.active, current_scene)

    if not obs_ok:
        state_manager.set_stream_active(payload.active)

    return {
        "ok": bool(obs_ok),
        "stream_active": payload.active,
        "obs_applied": bool(obs_ok),
        "obs_error": obs_error,
        "discord_notified": bool(discord_ok),
        "current_scene": current_scene,
    }


@router.post("/sync", dependencies=[Depends(enforce_rate_limit)])
async def sync_stream_connectors():
    obs_connected = await _bool_with_timeout(obs_manager.ensure_connected(), timeout_seconds=2.5, default=False)
    discord_connected = await _bool_with_timeout(discord_manager.health_check(), timeout_seconds=2.5, default=False)
    stream_active = await obs_manager.get_stream_active()
    current_scene = await obs_manager.get_current_scene()

    snapshot = state_manager.snapshot()
    return {
        "ok": bool(obs_connected or discord_connected),
        "stream_active": bool(snapshot["stream_active"] if stream_active is None else stream_active),
        "obs_connected": bool(snapshot["obs_connected"]),
        "discord_connected": bool(snapshot["discord_connected"]),
        "current_scene": current_scene or snapshot["current_scene"],
        "last_error": snapshot["last_error"],
    }


@router.get("/preflight", dependencies=[Depends(enforce_rate_limit)])
async def stream_preflight():
    obs_connected = await _bool_with_timeout(obs_manager.ensure_connected(), timeout_seconds=2.5, default=False)
    discord_connected = await _bool_with_timeout(discord_manager.health_check(), timeout_seconds=2.5, default=False)
    snapshot = state_manager.snapshot()
    profile_data = _load_multidevice_profiles()
    selected_profile = _pick_stream_profile(profile_data)

    blockers: list[str] = []
    warnings: list[str] = []

    if not config.OBS_ENABLED:
        blockers.append("OBS_ENABLED=false")
    elif not obs_connected:
        blockers.append("OBS WebSocket no conectado (revisa Tools > WebSocket Server Settings en OBS)")

    if not config.DISCORD_ENABLED:
        blockers.append("DISCORD_ENABLED=false")
    elif not config.DISCORD_WEBHOOK_URL:
        blockers.append("DISCORD_WEBHOOK_URL vacío")
    elif not discord_connected:
        warnings.append("Webhook Discord no responde 200/204")

    rec_upload = selected_profile.get("recommended_upload_mbps")
    if rec_upload and float(config.STREAM_UPLOAD_MBPS) < float(rec_upload):
        warnings.append(
            f"Upload actual ({config.STREAM_UPLOAD_MBPS} Mbps) bajo para perfil recomendado ({rec_upload} Mbps)"
        )

    if selected_profile.get("profile_key") is None:
        warnings.append("Perfil multi-dispositivo no disponible; usa configuración manual de OBS")

    return {
        "ok": len(blockers) == 0,
        "obs_connected": bool(snapshot["obs_connected"]),
        "discord_connected": bool(snapshot["discord_connected"]),
        "blockers": blockers,
        "warnings": warnings,
        "last_error": snapshot["last_error"],
        "recommended_profile": selected_profile,
        "stream_env": {
            "device": config.STREAM_DEVICE,
            "upload_mbps": config.STREAM_UPLOAD_MBPS,
            "profile_mode": config.STREAM_PROFILE,
        },
    }


@router.get("/multidevice-profile", dependencies=[Depends(enforce_rate_limit)])
async def stream_multidevice_profile():
    profile_path = Path(__file__).resolve().parents[2] / "obs_control" / "multidevice_stream_profiles.json"
    data = _load_multidevice_profiles()
    if not data:
        return {
            "ok": False,
            "message": "Perfil multi-dispositivo no encontrado",
            "profile_path": str(profile_path),
        }

    try:
        selected_profile = _pick_stream_profile(data)
        return {
            "ok": True,
            "profiles": data,
            "recommended_profile": selected_profile,
            "active_transport": {
                "obs_host": config.OBS_HOST,
                "obs_port": config.OBS_PORT,
                "obs_enabled": config.OBS_ENABLED,
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Error leyendo perfil multi-dispositivo: {exc}",
        }
