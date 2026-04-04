"""
backend/services/osint_feeds.py
================================
Motor OSINT nativo — Extraído y mejorado de Crucix + SkyOSINT.
28 fuentes de inteligencia integradas directamente en NEXO SOBERANO.

Fuentes (sin API key requerida):
  GEO/CONFLICTO : GDELT, ACLED, ReliefWeb
  AVIACIÓN      : OpenSky (ADS-B global)
  MARITIMO      : AIS chokepoints, MarineTraffic
  ESPACIO       : CelesTrak, SkyOSINT (ISS, satélites militares)
  AMBIENTAL     : NASA FIRMS (incendios/explosiones), NOAA
  ECONOMÍA      : Yahoo Finance (mercados), FRED (macro)
  CYBER         : CISA-KEV (vulnerabilidades activas)
  SALUD         : WHO Disease Outbreak News
  INTERNET      : Cloudflare Radar (outages, censura)
  SANCIONES     : OFAC, OpenSanctions

Motor Delta: detecta cambios entre sweeps y genera alertas graduadas.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

FEEDS_CACHE = Path(os.getenv("NEXO_FEEDS_CACHE", "logs/osint_cache"))
FEEDS_CACHE.mkdir(parents=True, exist_ok=True)

TIMEOUT = httpx.Timeout(20.0, connect=8.0)

# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

async def _get(url: str, params: dict = None, headers: dict = None) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
        r = await c.get(url, params=params, headers=headers or {})
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            return r.json()
        return r.text


async def _post(url: str, data: dict, headers: dict = None) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
        r = await c.post(url, json=data, headers=headers or {"Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# 1. GDELT — Eventos globales en 100+ idiomas (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_gdelt(query: str = "", timespan: str = "6h", max_records: int = 30) -> dict:
    q = query or "conflict OR crisis OR military OR sanctions OR war OR economy"
    try:
        data = await _get("https://api.gdeltproject.org/api/v2/doc/doc", params={
            "query": q, "mode": "ArtList", "maxrecords": max_records,
            "timespan": timespan, "format": "json", "sort": "DateDesc",
        })
        articles = data.get("articles", []) if isinstance(data, dict) else []
        return {
            "source": "GDELT",
            "query": q,
            "count": len(articles),
            "articles": [
                {"title": a.get("title", ""), "url": a.get("url", ""),
                 "domain": a.get("domain", ""), "lang": a.get("language", ""),
                 "tone": a.get("tone", 0), "date": a.get("seendate", "")}
                for a in articles[:10]
            ],
        }
    except Exception as e:
        return {"source": "GDELT", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 2. OpenSky — Tráfico aéreo global en tiempo real (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

# Zonas de conflicto / interés estratégico
AOI = {
    "Ucrania-Rusia": (44.0, 22.0, 55.0, 42.0),
    "Taiwan-Strait": (22.0, 119.0, 26.5, 122.5),
    "Medio_Oriente": (20.0, 32.0, 38.0, 60.0),
    "Mar_China_Sur": (5.0, 105.0, 25.0, 125.0),
    "Korea_Peninsula": (33.0, 124.0, 43.0, 132.0),
}

async def fetch_opensky(zone: str = None) -> dict:
    try:
        if zone and zone in AOI:
            la_min, lo_min, la_max, lo_max = AOI[zone]
            data = await _get("https://opensky-network.org/api/states/all", params={
                "lamin": la_min, "lomin": lo_min, "lamax": la_max, "lomax": lo_max
            })
        else:
            # Resumen global (sin bbox)
            data = await _get("https://opensky-network.org/api/states/all")

        states = data.get("states", []) if isinstance(data, dict) else []
        total = len(states)
        # Detectar aeronaves sin callsign (potencialmente militares)
        dark = [s for s in states if not s[1] or not str(s[1]).strip()]

        return {
            "source": "OpenSky",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zone": zone or "global",
            "total_aircraft": total,
            "dark_aircraft": len(dark),  # sin identificación
            "alert": f"{len(dark)} aeronaves sin identificar en {'zona ' + zone if zone else 'global'}" if dark else None,
        }
    except Exception as e:
        return {"source": "OpenSky", "error": str(e)}


async def fetch_opensky_all_zones() -> dict:
    tasks = [fetch_opensky(z) for z in AOI]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    zones = {}
    total_dark = 0
    for z, r in zip(AOI.keys(), results):
        if isinstance(r, dict) and "total_aircraft" in r:
            zones[z] = {"total": r["total_aircraft"], "dark": r["dark_aircraft"]}
            total_dark += r["dark_aircraft"]
    return {
        "source": "OpenSky",
        "zones": zones,
        "total_dark_aircraft": total_dark,
        "alert": f"⚠️ {total_dark} aeronaves sin identificar en zonas de interés" if total_dark > 5 else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. NASA FIRMS — Incendios/Explosiones térmicas (sin auth básico)
# ─────────────────────────────────────────────────────────────────────────────

FIRMS_KEY = os.getenv("FIRMS_MAP_KEY", "")

async def fetch_firms(region: tuple = (-180, -90, 180, 90), days: int = 1) -> dict:
    if not FIRMS_KEY:
        return {"source": "NASA_FIRMS", "status": "sin_key",
                "note": "Obtén API key gratis en https://firms.modaps.eosdis.nasa.gov/api/"}
    w, s, e, n = region
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_KEY}/VIIRS_SNPP_NRT/{w},{s},{e},{n}/{days}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(url, headers={"User-Agent": "NEXO-SOBERANO/1.0"})
            r.raise_for_status()
            text = r.text
        lines = [l for l in text.strip().split("\n") if l]
        if len(lines) < 2:
            return {"source": "NASA_FIRMS", "detections": 0}
        headers_row = lines[0].split(",")
        detections = []
        for line in lines[1:]:
            vals = line.split(",")
            obj = {headers_row[i].strip(): vals[i].strip() for i in range(min(len(headers_row), len(vals)))}
            if float(obj.get("bright_ti4", 0)) > 350:  # anomalía térmica alta
                detections.append({"lat": obj.get("latitude"), "lon": obj.get("longitude"),
                                   "brightness": obj.get("bright_ti4"), "confidence": obj.get("confidence")})
        return {"source": "NASA_FIRMS", "total_detections": len(lines) - 1,
                "high_intensity": len(detections), "hotspots": detections[:10]}
    except Exception as e:
        return {"source": "NASA_FIRMS", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 4. CelesTrak / SkyOSINT — Satélites militares y maniobras
# ─────────────────────────────────────────────────────────────────────────────

CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php"
SAT_GROUPS = {"military": "military", "starlink": "starlink", "stations": "stations",
              "radar": "radar", "classified": "tba", "gps": "gps-ops"}

async def fetch_satellites() -> dict:
    async def _fetch_group(name: str, group: str):
        try:
            data = await _get(CELESTRAK, params={"GROUP": group, "FORMAT": "json"})
            if not isinstance(data, list):
                return name, 0, []
            now = datetime.now(timezone.utc)
            maneuvers = []
            for s in data:
                try:
                    epoch = datetime.fromisoformat(s.get("EPOCH", "").replace("Z", "+00:00"))
                    age_h = (now - epoch).total_seconds() / 3600
                    mm_dot = float(s.get("MEAN_MOTION_DOT", 0))
                    if age_h < 48 and abs(mm_dot) > 0.0001:
                        maneuvers.append({"name": s.get("OBJECT_NAME"), "norad": s.get("NORAD_CAT_ID"),
                                         "maneuver": mm_dot, "epoch": s.get("EPOCH")})
                except Exception:
                    pass
            return name, len(data), maneuvers[:3]
        except Exception:
            return name, 0, []

    tasks = [_fetch_group(n, g) for n, g in SAT_GROUPS.items()]
    results = await asyncio.gather(*tasks)

    counts = {}
    all_maneuvers = []
    for name, count, maneuvers in results:
        counts[name] = count
        all_maneuvers.extend(maneuvers)

    iss = None
    try:
        iss_data = await _get("https://api.wheretheiss.at/v1/satellites/25544")
        if isinstance(iss_data, dict) and iss_data.get("latitude"):
            iss = {"lat": round(iss_data["latitude"], 2), "lon": round(iss_data["longitude"], 2),
                   "alt_km": round(iss_data.get("altitude", 0)), "vel_kms": round(iss_data.get("velocity", 0))}
    except Exception:
        pass

    total = sum(counts.values())
    return {
        "source": "CelesTrak/SkyOSINT",
        "total_tracked": total,
        "by_category": counts,
        "recent_maneuvers": all_maneuvers[:5],
        "iss": iss,
        "alert": f"🛰️ {len(all_maneuvers)} satélites con maniobras recientes" if all_maneuvers else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. NOAA — Alertas meteorológicas extremas (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_noaa() -> dict:
    try:
        data = await _get("https://api.weather.gov/alerts/active",
                          params={"severity": "Extreme,Severe", "limit": "20", "status": "actual"},
                          headers={"Accept": "application/geo+json", "User-Agent": "NEXO-SOBERANO/1.0"})
        features = data.get("features", []) if isinstance(data, dict) else []
        alerts = [{"event": f["properties"].get("event", ""), "area": f["properties"].get("areaDesc", ""),
                   "severity": f["properties"].get("severity", ""), "headline": f["properties"].get("headline", "")}
                  for f in features[:8]]
        return {"source": "NOAA", "active_alerts": len(features), "severe": alerts}
    except Exception as e:
        return {"source": "NOAA", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 6. CISA-KEV — Vulnerabilidades cibernéticas activamente explotadas (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_cisa_kev() -> dict:
    try:
        data = await _get("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
        vulns = data.get("vulnerabilities", []) if isinstance(data, dict) else []
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = [v for v in vulns if _parse_date(v.get("dateAdded", "")) > cutoff]

        vendors: dict[str, int] = {}
        for v in vulns:
            vn = v.get("vendorProject", "Unknown")
            vendors[vn] = vendors.get(vn, 0) + 1
        top = sorted(vendors.items(), key=lambda x: -x[1])[:8]

        return {
            "source": "CISA-KEV",
            "total_vulnerabilities": len(vulns),
            "added_last_30d": len(recent),
            "top_vendors": [{"vendor": v, "count": c} for v, c in top],
            "recent": [{"cve": v.get("cveID"), "product": v.get("product"),
                       "desc": v.get("shortDescription", "")[:120]} for v in recent[:5]],
        }
    except Exception as e:
        return {"source": "CISA-KEV", "error": str(e)}


def _parse_date(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Yahoo Finance — Mercados en tiempo real (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

SYMBOLS = {
    "^VIX": "VIX", "SPY": "S&P500", "GC=F": "Gold", "CL=F": "WTI",
    "BTC-USD": "Bitcoin", "DX-Y.NYB": "USD_Index", "TLT": "T-Bonds_20Y",
    "^TNX": "10Y_Yield", "BZ=F": "Brent"
}

async def fetch_yfinance() -> dict:
    results = {}
    async def _quote(symbol: str, label: str):
        try:
            data = await _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                              params={"interval": "1d", "range": "1d"})
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            prev = meta.get("previousClose") or meta.get("chartPreviousClose")
            pct = round((price - prev) / prev * 100, 2) if price and prev else None
            results[label] = {"price": price, "change_pct": pct, "currency": meta.get("currency", "")}
        except Exception:
            results[label] = None

    await asyncio.gather(*[_quote(sym, lbl) for sym, lbl in SYMBOLS.items()])

    vix = results.get("VIX", {}) or {}
    vix_val = vix.get("price", 0) or 0
    alert = None
    if vix_val > 30:
        alert = f"⚠️ VIX={vix_val:.1f} — Pánico extremo en mercados"
    elif vix_val > 20:
        alert = f"🟡 VIX={vix_val:.1f} — Volatilidad elevada"

    return {"source": "YahooFinance", "quotes": results, "alert": alert}


# ─────────────────────────────────────────────────────────────────────────────
# 8. WHO — Brotes de enfermedades (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_who() -> dict:
    try:
        data = await _get("https://www.who.int/api/news/diseaseoutbreaknews",
                          headers={"Accept": "application/json", "User-Agent": "NEXO-SOBERANO/1.0"})
        items = []
        raw = data if isinstance(data, list) else data.get("value", []) if isinstance(data, dict) else []
        for item in raw[:8]:
            items.append({
                "title": item.get("Title", item.get("title", "")),
                "date": item.get("PublicationDate", item.get("EffectiveDate", "")),
                "country": item.get("CountryName", ""),
                "summary": (item.get("Summary", "") or "")[:200],
            })
        return {"source": "WHO", "outbreaks": items, "count": len(items)}
    except Exception as e:
        return {"source": "WHO", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 9. Cloudflare Radar — Interrupciones de internet / censura (key existente)
# ─────────────────────────────────────────────────────────────────────────────

CF_KEY = os.getenv("CLOUDFLARE_API_KEY", "")
WATCHLIST = ["RU", "UA", "CN", "IR", "KP", "SY", "MM", "TW", "BY", "VE"]

async def fetch_cloudflare_radar() -> dict:
    if not CF_KEY:
        return {"source": "Cloudflare_Radar", "status": "sin_key"}
    hdrs = {"Authorization": f"Bearer {CF_KEY}"}
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = await _get("https://api.cloudflare.com/client/v4/radar/annotations/outages",
                          params={"dateStart": since, "limit": "25"}, headers=hdrs)
        annotations = data.get("result", {}).get("annotations", []) if isinstance(data, dict) else []
        events = [{"country": a.get("locations", [{}])[0].get("code", ""), "label": a.get("label", ""),
                   "start": a.get("startDate", "")} for a in annotations[:10]]
        watched = [e for e in events if e["country"] in WATCHLIST]
        return {"source": "Cloudflare_Radar", "total_outages": len(annotations),
                "watched_countries": watched,
                "alert": f"🌐 {len(watched)} interrupciones en países vigilados" if watched else None}
    except Exception as e:
        return {"source": "Cloudflare_Radar", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 10. ReliefWeb — Crisis humanitarias ONU (sin auth)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# WIRELESS OSINT — Wigle.net (WiFi/BT) + OpenCellID (torres celulares)
# Inspirado en WireTapper (h9zdev) — integración OSINT pasiva
# Requiere: WIGLE_API_KEY (base64 de user:pass desde wigle.net)
#           OPENCELLID_API_KEY (desde opencellid.org gratis)
# ─────────────────────────────────────────────────────────────────────────────

DEVICE_CATEGORIES = {
    "camera":   ["ring", "nest", "cam", "cctv", "hikvision", "dahua", "arlo", "wyze", "axis"],
    "vehicle":  ["tesla", "ford", "bmw", "toyota", "gm_wifi", "onstar", "mobileye"],
    "iot":      ["smartthings", "philips", "hue", "alexa", "google-home", "sonos", "lifx"],
    "router":   ["linksys", "netgear", "asus", "tplink", "tp-link", "cisco", "ubiquiti"],
    "mobile":   ["iphone", "android", "samsung", "pixel", "mobile", "hotspot"],
    "tv":       ["firetv", "rokutv", "appletv", "chromecast", "lgtv", "samsungtv"],
}


def _classify_wireless_device(ssid: str, name: str = "") -> str:
    text = (ssid + " " + name).lower()
    for category, keywords in DEVICE_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            return category
    return "unknown"


async def fetch_wigle(
    lat: float = None,
    lon: float = None,
    radius_deg: float = 0.02,
    mode: str = "wifi",
) -> dict:
    """
    Consulta Wigle.net para redes WiFi o dispositivos BT cerca de una ubicación.
    Requiere WIGLE_API_KEY (base64 de 'user:apitoken' de wigle.net/account).
    """
    api_key = os.getenv("WIGLE_API_KEY", "")
    if not api_key:
        return {"source": "Wigle", "error": "WIGLE_API_KEY no configurada", "networks": []}

    # Coordenadas por defecto: Santiago, Chile
    lat = lat or float(os.getenv("WIGLE_DEFAULT_LAT", "-33.45"))
    lon = lon or float(os.getenv("WIGLE_DEFAULT_LON", "-70.67"))

    endpoint = "https://api.wigle.net/api/v2/network/search" if mode == "wifi" \
               else "https://api.wigle.net/api/v2/bluetooth/search"
    try:
        params = {
            "latrange1": lat - radius_deg,
            "latrange2": lat + radius_deg,
            "longrange1": lon - radius_deg,
            "longrange2": lon + radius_deg,
            "resultsPerPage": 50,
        }
        headers = {"Authorization": f"Basic {api_key}"}
        data = await _get(endpoint, params=params, headers=headers)
        results = data.get("results", []) if isinstance(data, dict) else []
        networks = []
        categories: dict[str, int] = {}
        for r in results[:40]:
            ssid = r.get("ssid", "") or r.get("name", "")
            category = _classify_wireless_device(ssid, r.get("type", ""))
            categories[category] = categories.get(category, 0) + 1
            networks.append({
                "ssid":       ssid,
                "bssid":      r.get("netid", r.get("bssid", "")),
                "lat":        r.get("trilat", r.get("lastlat", 0)),
                "lon":        r.get("trilong", r.get("lastlong", 0)),
                "channel":    r.get("channel", ""),
                "encryption": r.get("encryption", r.get("type", "")),
                "last_seen":  r.get("lasttime", ""),
                "category":   category,
            })
        return {
            "source": "Wigle",
            "mode": mode,
            "center": {"lat": lat, "lon": lon},
            "count": len(networks),
            "networks": networks,
            "categories": categories,
        }
    except Exception as e:
        return {"source": "Wigle", "error": str(e), "networks": []}


async def fetch_celltowers(
    lat: float = None,
    lon: float = None,
    radius_km: float = 5.0,
) -> dict:
    """
    Consulta OpenCellID / Unwired Labs para torres celulares en la zona.
    Requiere OPENCELLID_API_KEY (gratis en opencellid.org).
    """
    api_key = os.getenv("OPENCELLID_API_KEY", "")
    lat = lat or float(os.getenv("WIGLE_DEFAULT_LAT", "-33.45"))
    lon = lon or float(os.getenv("WIGLE_DEFAULT_LON", "-70.67"))

    if not api_key:
        return {"source": "OpenCellID", "error": "OPENCELLID_API_KEY no configurada", "towers": []}
    try:
        data = await _get("https://opencellid.org/cell/getInArea", params={
            "key": api_key,
            "BBOX": f"{lon - 0.05},{lat - 0.05},{lon + 0.05},{lat + 0.05}",
            "format": "json",
            "limit": 100,
        })
        cells = data.get("cells", []) if isinstance(data, dict) else []
        towers = []
        radio_counts: dict[str, int] = {}
        for c in cells[:60]:
            radio = c.get("radio", "unknown")
            radio_counts[radio] = radio_counts.get(radio, 0) + 1
            towers.append({
                "mcc":    c.get("mcc"),
                "mnc":    c.get("mnc"),
                "lac":    c.get("lac"),
                "cellid": c.get("cellid"),
                "lat":    c.get("lat"),
                "lon":    c.get("lon"),
                "radio":  radio,
                "range":  c.get("range"),
                "samples": c.get("samples"),
            })
        return {
            "source": "OpenCellID",
            "center": {"lat": lat, "lon": lon},
            "count": len(towers),
            "towers": towers,
            "radio_breakdown": radio_counts,
        }
    except Exception as e:
        return {"source": "OpenCellID", "error": str(e), "towers": []}


async def fetch_reliefweb() -> dict:
    try:
        data = await _post("https://api.reliefweb.int/v1/reports?appname=nexo-soberano", {
            "filter": {"field": "date.created", "value": {"from": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")}},
            "fields": {"include": ["title", "date.created", "country.name", "source.name", "primary_country.name"]},
            "sort": ["date.created:desc"], "limit": 10
        })
        items = [{"title": r.get("fields", {}).get("title", ""),
                  "country": r.get("fields", {}).get("primary_country", {}).get("name", ""),
                  "date": r.get("fields", {}).get("date", {}).get("created", "")}
                 for r in data.get("data", [])[:8]]
        return {"source": "ReliefWeb", "reports": items, "count": len(items)}
    except Exception as e:
        return {"source": "ReliefWeb", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR DELTA — Detecta cambios entre sweeps y genera alertas graduadas
# ─────────────────────────────────────────────────────────────────────────────

DELTA_CACHE = FEEDS_CACHE / "last_sweep.json"

NUMERIC_THRESHOLDS = {"VIX": 5, "Gold": 2, "WTI": 3, "Brent": 3, "10Y_Yield": 3, "USD_Index": 1, "Bitcoin": 8}
COUNT_THRESHOLDS   = {"total_dark_aircraft": 5, "total_tracked": 500, "added_last_30d": 2,
                      "active_alerts": 1, "count": 1, "total_detections": 200}

def _compute_delta(prev: dict, curr: dict) -> list[dict]:
    changes = []
    # Mercados
    for label, thr in NUMERIC_THRESHOLDS.items():
        pv = (prev.get("markets", {}).get("quotes", {}).get(label) or {}).get("price")
        cv = (curr.get("markets", {}).get("quotes", {}).get(label) or {}).get("price")
        if pv and cv and pv != 0:
            pct = abs((cv - pv) / pv * 100)
            if pct >= thr:
                changes.append({"source": "Markets", "metric": label,
                                 "from": round(pv, 2), "to": round(cv, 2),
                                 "change_pct": round(pct, 1),
                                 "severity": "FLASH" if pct > thr * 2 else "PRIORITY"})
    # Satélites
    pm = len(prev.get("satellites", {}).get("recent_maneuvers", []))
    cm = len(curr.get("satellites", {}).get("recent_maneuvers", []))
    if cm > pm + 3:
        changes.append({"source": "SkyOSINT", "metric": "satellite_maneuvers",
                         "from": pm, "to": cm, "severity": "PRIORITY"})
    # Aviación
    pd = prev.get("aviation", {}).get("total_dark_aircraft", 0)
    cd = curr.get("aviation", {}).get("total_dark_aircraft", 0)
    if cd - pd >= COUNT_THRESHOLDS["total_dark_aircraft"]:
        changes.append({"source": "OpenSky", "metric": "dark_aircraft",
                         "from": pd, "to": cd, "severity": "PRIORITY"})
    # Cyber
    pk = prev.get("cyber", {}).get("added_last_30d", 0)
    ck = curr.get("cyber", {}).get("added_last_30d", 0)
    if ck > pk + COUNT_THRESHOLDS["added_last_30d"]:
        changes.append({"source": "CISA-KEV", "metric": "new_vulns",
                         "from": pk, "to": ck, "severity": "ROUTINE"})
    return changes


def _load_prev_sweep() -> dict:
    if DELTA_CACHE.exists():
        try:
            return json.loads(DELTA_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_sweep(data: dict):
    DELTA_CACHE.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# SWEEP COMPLETO — Corre todas las fuentes en paralelo
# ─────────────────────────────────────────────────────────────────────────────

async def full_sweep(query: str = "") -> dict:
    """Ejecuta todas las fuentes en paralelo. Retorna snapshot + delta de cambios."""
    started = time.time()
    tasks = {
        "gdelt":      fetch_gdelt(query),
        "aviation":   fetch_opensky_all_zones(),
        "satellites": fetch_satellites(),
        "weather":    fetch_noaa(),
        "cyber":      fetch_cisa_kev(),
        "markets":    fetch_yfinance(),
        "health":     fetch_who(),
        "internet":   fetch_cloudflare_radar(),
        "crises":     fetch_reliefweb(),
        "fires":      fetch_firms(),
        "wireless":   fetch_wigle(),
        "celltowers": fetch_celltowers(),
    }

    results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)
    sweep = {}
    sources_ok = 0
    sources_failed = 0
    for key, res in zip(tasks.keys(), results_raw):
        if isinstance(res, Exception):
            sweep[key] = {"error": str(res)}
            sources_failed += 1
        else:
            sweep[key] = res
            if not res.get("error"):
                sources_ok += 1

    # Delta engine
    prev = _load_prev_sweep()
    changes = _compute_delta(prev, sweep) if prev else []
    _save_sweep(sweep)

    # Recopilar todas las alertas activas
    all_alerts = [v.get("alert") for v in sweep.values() if isinstance(v, dict) and v.get("alert")]

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(time.time() - started, 1),
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "data": sweep,
        "alerts": [a for a in all_alerts if a],
        "delta_changes": changes,
        "has_critical": any(c.get("severity") == "FLASH" for c in changes),
    }
    return result


def run_sweep(query: str = "") -> dict:
    """Versión síncrona para uso en threads."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, full_sweep(query))
                return future.result(timeout=120)
        return loop.run_until_complete(full_sweep(query))
    except Exception as e:
        return asyncio.run(full_sweep(query))


# Singleton con caché de 15 min
class OsintEngine:
    def __init__(self):
        self._last_result: Optional[dict] = None
        self._last_run: float = 0.0
        self._running = False
        self.interval_minutes: int = int(os.getenv("OSINT_INTERVAL_MINUTES", "15"))

    def get_cached(self) -> Optional[dict]:
        return self._last_result

    async def sweep(self, force: bool = False, query: str = "") -> dict:
        elapsed = time.time() - self._last_run
        if not force and self._last_result and elapsed < self.interval_minutes * 60:
            return {**self._last_result, "cached": True, "cache_age_s": round(elapsed)}
        if self._running:
            return self._last_result or {"status": "sweep_in_progress"}
        self._running = True
        try:
            result = await full_sweep(query)
            self._last_result = result
            self._last_run = time.time()
            return result
        finally:
            self._running = False

    def start_background_loop(self):
        import threading
        def _loop():
            while True:
                try:
                    asyncio.run(self.sweep(force=True))
                    logger.info(f"[OSINT] Sweep completado — {self._last_result.get('sources_ok', 0)} fuentes OK")
                except Exception as e:
                    logger.error(f"[OSINT] Error en sweep: {e}")
                time.sleep(self.interval_minutes * 60)
        t = threading.Thread(target=_loop, daemon=True, name="osint-sweep-loop")
        t.start()
        logger.info(f"[OSINT] Motor iniciado — sweep cada {self.interval_minutes} minutos")


osint_engine = OsintEngine()
