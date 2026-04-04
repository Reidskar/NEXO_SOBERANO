"""
backend/routes/osint.py
========================
API REST para el OSINT Engine nativo de NEXO.

Endpoints:
  GET  /api/osint/sweep          — sweep completo (usa caché 15 min)
  POST /api/osint/sweep/force    — fuerza nuevo sweep ignorando caché
  GET  /api/osint/status         — estado del engine + última ejecución
  GET  /api/osint/source/{name}  — datos de una fuente específica
  GET  /api/osint/satellites     — datos de satélites (SkyOSINT nativo)
  GET  /api/osint/flights        — vuelos en zonas estratégicas (OpenSky)
  GET  /api/osint/threats        — amenazas activas (CISA KEV + FIRMS + GDELT)
  GET  /api/osint/markets        — datos de mercados (YFinance)
  GET  /api/osint/delta          — cambios detectados vs sweep anterior
"""
from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["osint"])

API_KEY = os.getenv("NEXO_API_KEY", "NEXO_LOCAL_2026_OK")


def _auth(key: str = None):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")


def _get_engine():
    from backend.services.osint_feeds import osint_engine
    return osint_engine


# ── SWEEP PRINCIPAL ────────────────────────────────────────────────────────────

@router.get("/api/osint/sweep")
async def get_sweep(
    query: str = Query(default="geopolitics conflict economy", description="Consulta GDELT"),
    x_api_key: str = Header(None),
):
    """Devuelve el último sweep OSINT (caché 15 min). Si no hay caché, ejecuta uno nuevo."""
    _auth(x_api_key)
    engine = _get_engine()
    result = await engine.sweep(force=False, query=query)
    return result


@router.post("/api/osint/sweep/force")
async def force_sweep(
    query: str = Query(default="geopolitics conflict economy"),
    x_api_key: str = Header(None),
):
    """Fuerza un nuevo sweep completo de las 10 fuentes OSINT en paralelo."""
    _auth(x_api_key)
    engine = _get_engine()
    result = await engine.sweep(force=True, query=query)
    return result


# ── STATUS ─────────────────────────────────────────────────────────────────────

@router.get("/api/osint/status")
async def osint_status(x_api_key: str = Header(None)):
    """Estado del engine: última ejecución, fuentes activas, errores."""
    _auth(x_api_key)
    engine = _get_engine()

    last = engine._last_result or {}
    meta = last.get("meta", {})

    return {
        "engine": "osint_feeds.py",
        "sources": 10,
        "cache_ttl_minutes": 15,
        "last_sweep": meta.get("swept_at"),
        "last_duration_seconds": meta.get("duration_seconds"),
        "sources_ok": meta.get("sources_ok", 0),
        "sources_failed": meta.get("sources_failed", 0),
        "errors": last.get("errors", []),
        "background_loop": "active" if engine._running else "idle",
    }


# ── FUENTE INDIVIDUAL ──────────────────────────────────────────────────────────

@router.get("/api/osint/source/{source_name}")
async def get_source(
    source_name: str,
    x_api_key: str = Header(None),
):
    """Datos de una fuente específica del último sweep."""
    _auth(x_api_key)
    engine = _get_engine()

    if not engine._last_result:
        raise HTTPException(status_code=503, detail="No hay datos OSINT aún. Ejecuta /api/osint/sweep/force")

    sources = engine._last_result.get("sources", {})
    key = source_name.lower()

    # Buscar por nombre exacto o parcial
    match = sources.get(key) or sources.get(source_name)
    if not match:
        for k, v in sources.items():
            if key in k.lower():
                match = v
                break

    if not match:
        available = list(sources.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Fuente '{source_name}' no encontrada. Disponibles: {available}"
        )

    return {"source": source_name, "data": match}


# ── VISTAS ESPECIALIZADAS ──────────────────────────────────────────────────────

@router.get("/api/osint/satellites")
async def get_satellites(x_api_key: str = Header(None)):
    """Datos de satélites: ISS, militares, maniobras detectadas."""
    _auth(x_api_key)

    try:
        from backend.services.osint_feeds import fetch_satellites
        data = await fetch_satellites()
        return {"ok": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/osint/flights")
async def get_flights(x_api_key: str = Header(None)):
    """Vuelos en tiempo real sobre zonas estratégicas (OpenSky)."""
    _auth(x_api_key)

    try:
        from backend.services.osint_feeds import fetch_opensky_all_zones
        data = await fetch_opensky_all_zones()
        return {"ok": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/osint/threats")
async def get_threats(x_api_key: str = Header(None)):
    """Vista consolidada de amenazas: CISA KEV, FIRMS, GDELT conflictos."""
    _auth(x_api_key)

    try:
        import asyncio
        from backend.services.osint_feeds import fetch_cisa_kev, fetch_firms, fetch_gdelt

        cisa, firms, gdelt = await asyncio.gather(
            fetch_cisa_kev(),
            fetch_firms(),
            fetch_gdelt("conflict war attack military"),
            return_exceptions=True,
        )

        return {
            "ok": True,
            "cyber": cisa if not isinstance(cisa, Exception) else {"error": str(cisa)},
            "thermal_anomalies": firms if not isinstance(firms, Exception) else {"error": str(firms)},
            "conflict_events": gdelt if not isinstance(gdelt, Exception) else {"error": str(gdelt)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/osint/markets")
async def get_markets(x_api_key: str = Header(None)):
    """Mercados en tiempo real: VIX, S&P500, Oro, WTI, Bitcoin."""
    _auth(x_api_key)

    try:
        from backend.services.osint_feeds import fetch_yfinance
        data = await fetch_yfinance()
        return {"ok": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/osint/delta")
async def get_delta(x_api_key: str = Header(None)):
    """Cambios significativos detectados entre el último sweep y el anterior."""
    _auth(x_api_key)
    engine = _get_engine()

    if not engine._last_result:
        raise HTTPException(status_code=503, detail="No hay datos OSINT aún.")

    delta = engine._last_result.get("delta", {})
    if not delta:
        return {"ok": True, "message": "Sin delta aún (se necesitan al menos 2 sweeps)", "delta": {}}

    significant = {k: v for k, v in delta.items() if v.get("significant")}
    return {
        "ok": True,
        "significant_changes": len(significant),
        "delta": significant or delta,
    }


@router.get("/api/osint/humanitarian")
async def get_humanitarian(x_api_key: str = Header(None)):
    """Crisis humanitarias activas (ReliefWeb/ONU) + alertas WHO."""
    _auth(x_api_key)

    try:
        import asyncio
        from backend.services.osint_feeds import fetch_reliefweb, fetch_who

        relief, who = await asyncio.gather(
            fetch_reliefweb(),
            fetch_who(),
            return_exceptions=True,
        )

        return {
            "ok": True,
            "reliefweb": relief if not isinstance(relief, Exception) else {"error": str(relief)},
            "who": who if not isinstance(who, Exception) else {"error": str(who)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/osint/wireless")
async def get_wireless(
    lat: float = Query(None, description="Latitud central"),
    lon: float = Query(None, description="Longitud central"),
    mode: str = Query("wifi", description="wifi|bluetooth"),
    x_api_key: str = Header(None),
):
    """Redes WiFi/BT cercanas (Wigle.net) + torres celulares (OpenCellID)."""
    _auth(x_api_key)
    try:
        import asyncio
        from backend.services.osint_feeds import fetch_wigle, fetch_celltowers
        wifi, towers = await asyncio.gather(
            fetch_wigle(lat=lat, lon=lon, mode=mode),
            fetch_celltowers(lat=lat, lon=lon),
            return_exceptions=True,
        )
        return {
            "ok": True,
            "wireless": wifi if not isinstance(wifi, Exception) else {"error": str(wifi)},
            "celltowers": towers if not isinstance(towers, Exception) else {"error": str(towers)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
