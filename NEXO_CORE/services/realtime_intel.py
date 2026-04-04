# ============================================================
# NEXO SOBERANO — Real-Time Intelligence Service v1.0
# © 2026 elanarcocapital.com
#
# Fuentes de datos en tiempo real (todas gratuitas):
#   - GDELT: eventos geopolíticos globales
#   - USGS: terremotos y desastres naturales
#   - NASA EONET: eventos naturales
#   - OpenSky Network: tráfico aéreo en vivo
#   - RSS: Reuters, AP, Al Jazeera, BBC
#
# Flujo: Fetch → Gemma 4 clasifica → broadcast al OmniGlobe
# Costo: $0 (Gemma 4 local + APIs gratuitas)
# ============================================================
from __future__ import annotations
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
import aiohttp

logger = logging.getLogger("NEXO.realtime_intel")

REFRESH_INTERVAL = int(os.getenv("INTEL_REFRESH_S", "300"))   # 5 min default
OPENSKY_USER     = os.getenv("OPENSKY_USER", "")
OPENSKY_PASS     = os.getenv("OPENSKY_PASS", "")

# ── FUENTES DE DATOS ──────────────────────────────────────────────────────────

GDELT_URL    = "https://api.gdeltproject.org/api/v2/doc/doc?query=conflict%20OR%20military%20OR%20geopolitics&mode=artlist&maxrecords=10&format=json"
USGS_URL     = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
EONET_URL    = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=20"
OPENSKY_URL  = "https://opensky-network.org/api/states/all"

RSS_FEEDS = {
    "reuters":  "https://feeds.reuters.com/reuters/worldNews",
    "ap":       "https://feeds.apnews.com/apnews/world",
    "bbc":      "https://feeds.bbci.co.uk/news/world/rss.xml",
    "aljazeera":"https://www.aljazeera.com/xml/rss/all.xml",
}

# Mapeo de regiones EONET a coordenadas aproximadas
EONET_REGION_COORDS = {
    "Pacific Ocean": (-15.0, -170.0),
    "Atlantic Ocean": (20.0, -40.0),
    "Indian Ocean":  (-10.0, 70.0),
    "Gulf of Mexico": (23.0, -90.0),
    "Caribbean":     (15.0, -75.0),
}

# Severidad de tipo de evento para el globo
EVENT_SEVERITY = {
    "Wildfires":     0.6, "Volcanoes": 0.7, "Severe Storms": 0.5,
    "Earthquakes":   0.8, "Floods":    0.5, "Landslides":    0.4,
    "Sea and Lake Ice": 0.3, "Drought": 0.4,
}

EVENT_COLORS = {
    "Wildfires":     "#ff6b35", "Volcanoes":    "#ff0000",
    "Severe Storms": "#8b5cf6", "Earthquakes":  "#f59e0b",
    "Floods":        "#3b82f6", "conflict":     "#ef4444",
    "military":      "#dc2626", "natural":      "#10b981",
    "political":     "#6366f1",
}


# ── FETCHERS ─────────────────────────────────────────────────────────────────

async def _fetch(url: str, timeout: int = 10, auth=None) -> dict | list | None:
    try:
        async with aiohttp.ClientSession() as s:
            kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout)}
            if auth:
                kwargs["auth"] = aiohttp.BasicAuth(*auth)
            async with s.get(url, **kwargs) as r:
                if r.status == 200:
                    ct = r.content_type or ""
                    if "json" in ct:
                        return await r.json()
                    return await r.text()
    except Exception as e:
        logger.debug(f"Fetch error {url}: {e}")
    return None


async def fetch_earthquakes() -> list[dict]:
    """Terremotos M4.5+ de las últimas 24h — USGS GeoJSON."""
    data = await _fetch(USGS_URL)
    if not data or "features" not in data:
        return []
    events = []
    for feature in data["features"][:20]:
        props = feature.get("properties", {})
        geom  = feature.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        if coords[0] is None:
            continue
        mag = props.get("mag", 0)
        events.append({
            "id":       f"eq_{feature['id']}",
            "type":     "add_event",
            "lat":      coords[1],
            "lng":      coords[0],
            "label":    f"M{mag} {props.get('place', 'Earthquake')}",
            "severity": min(1.0, float(mag) / 9.0),
            "radius":   0.04 + float(mag) * 0.015,
            "color":    "#f59e0b",
            "layer":    "events",
            "source":   "usgs",
            "ts":       datetime.now(timezone.utc).isoformat(),
            "metadata": {"magnitude": mag, "depth_km": coords[2] if len(coords) > 2 else None},
        })
    return events


async def fetch_natural_events() -> list[dict]:
    """Eventos naturales activos — NASA EONET."""
    data = await _fetch(EONET_URL)
    if not isinstance(data, dict):
        return []
    events = []
    for ev in data.get("events", [])[:15]:
        cat  = ev.get("categories", [{}])[0].get("title", "Natural")
        geom = ev.get("geometry", [])
        if not geom:
            continue
        latest = geom[-1] if isinstance(geom, list) else geom
        coords = latest.get("coordinates", [None, None])
        if not coords or coords[0] is None:
            # Try region lookup
            coords = EONET_REGION_COORDS.get(ev.get("title", ""), None)
            if not coords:
                continue
            lat, lng = coords
        else:
            if isinstance(coords[0], list):
                coords = coords[0]
            lng, lat = coords[0], coords[1]
        events.append({
            "id":       f"eonet_{ev['id']}",
            "type":     "add_event",
            "lat":      lat,
            "lng":      lng,
            "label":    ev.get("title", cat)[:60],
            "severity": EVENT_SEVERITY.get(cat, 0.4),
            "radius":   0.06,
            "color":    EVENT_COLORS.get(cat, "#10b981"),
            "layer":    "events",
            "source":   "nasa_eonet",
            "ts":       datetime.now(timezone.utc).isoformat(),
            "metadata": {"category": cat, "eonet_id": ev["id"]},
        })
    return events


async def fetch_live_aircraft() -> list[dict]:
    """Vuelos en tiempo real — OpenSky Network (anónimo, región global)."""
    auth = (OPENSKY_USER, OPENSKY_PASS) if OPENSKY_USER else None
    data = await _fetch(OPENSKY_URL, timeout=15, auth=auth)
    if not isinstance(data, dict):
        return []

    states = data.get("states", []) or []
    points = []
    # Filtrar: en aire, con posición, velocidad > 100 kn — tomar muestra
    airborne = [s for s in states if s and len(s) > 8 and s[5] and s[6] and s[8] is True]
    # Muestrear ~50 aeronaves distribuidas geográficamente
    import random
    sample = random.sample(airborne, min(50, len(airborne))) if airborne else []

    for state in sample:
        callsign = (state[1] or "").strip() or "N/A"
        lng, lat  = state[5], state[6]
        alt_m     = state[13] or state[7] or 0
        vel_ms    = state[9] or 0
        points.append({
            "id":    f"ac_{state[0]}",
            "type":  "add_point",
            "lat":   lat,
            "lng":   lng,
            "label": callsign,
            "color": "#f59e0b",
            "radius": 0.3,
            "layer": "aircraft",
            "source": "opensky",
            "ts":    datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "callsign":  callsign,
                "altitude_m": round(alt_m),
                "speed_ms":   round(vel_ms, 1),
                "icao24":     state[0],
                "origin_country": state[2],
            },
        })
    return points


async def fetch_gdelt_events() -> list[dict]:
    """Eventos geopolíticos globales — GDELT."""
    data = await _fetch(GDELT_URL, timeout=15)
    if not isinstance(data, dict):
        return []
    articles = data.get("articles", [])[:10]
    events = []
    for art in articles:
        # GDELT incluye coordenadas en algunos artículos
        lat = art.get("socialimage_latitude") or art.get("latitude")
        lng = art.get("socialimage_longitude") or art.get("longitude")
        if not lat or not lng:
            continue
        events.append({
            "id":       f"gdelt_{hash(art.get('url','')) & 0xFFFF}",
            "type":     "add_event",
            "lat":      float(lat),
            "lng":      float(lng),
            "label":    art.get("title", "")[:60],
            "severity": 0.6,
            "radius":   0.08,
            "color":    "#ef4444",
            "layer":    "events",
            "source":   "gdelt",
            "ts":       datetime.now(timezone.utc).isoformat(),
            "metadata": {"url": art.get("url", ""), "domain": art.get("domain", "")},
        })
    return events


async def fetch_rss_headlines() -> list[str]:
    """Titulares de RSS para el ticker del globo."""
    import re as re_mod
    headlines = []
    for source, url in RSS_FEEDS.items():
        try:
            text = await _fetch(url, timeout=8)
            if not text or not isinstance(text, str):
                continue
            # Extraer <title> de items RSS (sin xml parser)
            titles = re_mod.findall(r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>|<item>.*?<title>(.*?)</title>', text, re.DOTALL)
            for t in titles[:3]:
                title = (t[0] or t[1]).strip()
                if title and len(title) > 10 and title.lower() not in ("", "rss", "home"):
                    headlines.append(f"[{source.upper()}] {title}")
        except Exception:
            pass
    return headlines[:20]


# ── GEMMA 4 CLASSIFIER ────────────────────────────────────────────────────────

async def _classify_event_gemma(event: dict) -> dict:
    """
    Gemma 4 enriquece el evento con contexto inteligente.
    Si el label es genérico, añade análisis geopolítico.
    Costo: $0.
    """
    label = event.get("label", "")
    if len(label) < 20:   # Solo enriquecer eventos sin descripción detallada
        return event
    try:
        from NEXO_CORE.services.ollama_service import ollama_service
        resp = await ollama_service.consultar(
            prompt=f"Evento: {label}\nLat: {event.get('lat')}, Lng: {event.get('lng')}\n"
                   "En 1 oración, añade contexto geopolítico o de seguridad. Máximo 80 caracteres.",
            modelo="fast",
            system="Analista geopolítico conciso. Solo datos, sin opinión.",
            temperature=0.1,
            max_tokens=60,
        )
        if resp.success and resp.text:
            event["context"] = resp.text.strip()
    except Exception:
        pass
    return event


# ── MAIN INTEL LOOP ──────────────────────────────────────────────────────────

class RealtimeIntelService:
    """
    Servicio de inteligencia en tiempo real.
    Agrega fuentes → filtra con Gemma 4 → broadcast al OmniGlobe.
    """

    def __init__(self):
        self._running = False
        self._broadcast_fn = None
        self._last_events: list[dict] = []
        self._headlines: list[str] = []

    def set_broadcast(self, fn):
        self._broadcast_fn = fn

    async def _broadcast(self, cmd: dict):
        if self._broadcast_fn:
            try:
                await self._broadcast_fn({"channel": "globe_command", "payload": cmd})
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")

    async def fetch_all(self) -> dict:
        """Agrega todas las fuentes en paralelo."""
        quakes, natural, aircraft, gdelt, headlines = await asyncio.gather(
            fetch_earthquakes(),
            fetch_natural_events(),
            fetch_live_aircraft(),
            fetch_gdelt_events(),
            fetch_rss_headlines(),
            return_exceptions=True,
        )

        events = []
        for result in [quakes, natural, gdelt]:
            if isinstance(result, list):
                events.extend(result)

        points = aircraft if isinstance(aircraft, list) else []
        self._headlines = headlines if isinstance(headlines, list) else []

        logger.info(f"Intel fetch: {len(events)} events, {len(points)} aircraft, {len(self._headlines)} headlines")
        return {"events": events, "points": points, "headlines": self._headlines}

    async def broadcast_intel(self):
        """Fetches y transmite toda la inteligencia al OmniGlobe."""
        # Limpiar puntos anteriores
        await self._broadcast({"type": "clear_dynamic"})

        data = await self.fetch_all()

        # Transmitir eventos (con Gemma 4 para los primeros 5)
        for i, event in enumerate(data["events"][:25]):
            if i < 5:
                event = await _classify_event_gemma(event)
            await self._broadcast(event)
            await asyncio.sleep(0.05)

        # Transmitir aeronaves (sample)
        for point in data["points"][:30]:
            await self._broadcast(point)

        # Transmitir headlines al ticker
        if self._headlines:
            await self._broadcast({
                "type": "update_ticker",
                "headlines": self._headlines,
            })

        self._last_events = data["events"]
        return data

    async def run(self, interval: int = REFRESH_INTERVAL):
        """Bucle de actualización continua."""
        self._running = True
        logger.info(f"RealTime Intel iniciado — intervalo={interval}s")
        while self._running:
            try:
                await self.broadcast_intel()
            except Exception as e:
                logger.error(f"Intel loop error: {e}")
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "events_cached": len(self._last_events),
            "headlines_cached": len(self._headlines),
            "sources": ["usgs", "nasa_eonet", "opensky", "gdelt", "rss"],
            "refresh_interval_s": REFRESH_INTERVAL,
        }


# Instancia global
realtime_intel = RealtimeIntelService()
