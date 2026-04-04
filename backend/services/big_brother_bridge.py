# ============================================================
# NEXO SOBERANO — TheBigBrother Bridge v1.0
# © 2026 elanarcocapital.com
# Conecta TheBigBrother OSINT → Gemma 4 análisis → OmniGlobe
# ============================================================
from __future__ import annotations
import logging
import os
from typing import Optional
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger("NEXO.big_brother_bridge")

BB_URL     = os.getenv("BIGBROTHER_URL",     "http://localhost:8888")
BB_API_KEY = os.getenv("BIGBROTHER_API_KEY", "")
BB_TIMEOUT = int(os.getenv("BIGBROTHER_TIMEOUT_S", "30"))


# ── MODELS ──────────────────────────────────────────────────────────────────

class BBUsernameResult(BaseModel):
    username: str
    platforms_found: list[str] = []
    total: int = 0
    raw: dict = {}

class BBBreachResult(BaseModel):
    email: str
    breaches_found: int = 0
    passwords: list[str] = []
    services: list[str] = []
    raw: dict = {}

class BBNetworkResult(BaseModel):
    target: str
    open_ports: list[int] = []
    services: dict = {}
    vulnerabilities: list[str] = []
    raw: dict = {}

class BBPhoneResult(BaseModel):
    phone: str
    country: str = ""
    carrier: str = ""
    location: str = ""
    raw: dict = {}

class BBGlobeEvent(BaseModel):
    """Evento formatado para enviar al OmniGlobe via globe_control."""
    lat: float
    lng: float
    label: str
    severity: float = Field(ge=0.0, le=1.0, default=0.5)
    radius: float = 0.08       # grados (~8km ciudad)
    source: str = "bigbrother"
    metadata: dict = {}


# ── CLIENTE HTTP ─────────────────────────────────────────────────────────────

class BigBrotherClient:
    """Cliente async para la API REST de TheBigBrother."""

    def __init__(self):
        self.base = BB_URL.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if BB_API_KEY:
            self.headers["X-API-Key"] = BB_API_KEY

    async def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{self.base}{path}", params=params or {},
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=BB_TIMEOUT),
                ) as r:
                    if r.status == 200:
                        return await r.json()
                    text = await r.text()
                    logger.error(f"BigBrother GET {path} → {r.status}: {text[:200]}")
                    return {"error": text[:200], "status": r.status}
        except Exception as e:
            logger.error(f"BigBrother request error {path}: {e}")
            return {"error": str(e)}

    async def _post(self, path: str, body: dict) -> dict:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{self.base}{path}", json=body,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=BB_TIMEOUT),
                ) as r:
                    if r.status in (200, 201):
                        return await r.json()
                    text = await r.text()
                    logger.error(f"BigBrother POST {path} → {r.status}: {text[:200]}")
                    return {"error": text[:200], "status": r.status}
        except Exception as e:
            logger.error(f"BigBrother request error {path}: {e}")
            return {"error": str(e)}

    async def health(self) -> bool:
        r = await self._get("/health")
        return "error" not in r

    async def search_username(self, username: str) -> dict:
        return await self._get("/api/username", {"q": username})

    async def lookup_breach(self, email: str) -> dict:
        return await self._get("/api/breach", {"email": email})

    async def scan_network(self, target: str, ports: str = "top100") -> dict:
        return await self._post("/api/network/scan", {"target": target, "ports": ports})

    async def lookup_phone(self, phone: str) -> dict:
        return await self._get("/api/phone", {"number": phone})

    async def track_aircraft(self, callsign: str = "", icao: str = "") -> dict:
        return await self._get("/api/aircraft", {"callsign": callsign, "icao": icao})

    async def shodan_host(self, ip: str) -> dict:
        return await self._get("/api/shodan/host", {"ip": ip})

    async def darkweb_monitor(self, keyword: str) -> dict:
        return await self._get("/api/darkweb", {"q": keyword})

    async def geo_locate(self, ip: str) -> dict:
        return await self._get("/api/geo", {"ip": ip})


# ── BRIDGE (OSINT → Gemma 4 → Globe) ─────────────────────────────────────────

class BigBrotherBridge:
    """
    Orquestador que:
    1. Llama a TheBigBrother OSINT
    2. Analiza resultados con Gemma 4 ($0)
    3. Traduce hallazgos a comandos OmniGlobe

    Costo: $0 (todo procesado localmente).
    """

    def __init__(self):
        self.client = BigBrotherClient()
        self._ai = None

    @property
    def ai(self):
        if self._ai is None:
            from NEXO_CORE.services.ollama_service import ollama_service
            self._ai = ollama_service
        return self._ai

    # ── HEALTH ───────────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        return await self.client.health()

    # ── OSINT + ANÁLISIS ─────────────────────────────────────────────────────

    async def investigate_username(self, username: str) -> dict:
        """Rastrea username en OSINT → analiza con Gemma 4."""
        raw = await self.client.search_username(username)
        if "error" in raw:
            return {"success": False, "error": raw["error"]}

        analysis = await self.ai.analizar_osint(
            str(raw),
            objetivo=f"Rastreo de identidad para usuario: {username}"
        )
        return {
            "success": True,
            "username": username,
            "osint_raw": raw,
            "analysis": analysis.text if analysis.success else "Análisis no disponible",
            "cost_usd": 0.0,
        }

    async def investigate_breach(self, email: str) -> dict:
        """Revisa brechas de datos para un email."""
        raw = await self.client.lookup_breach(email)
        if "error" in raw:
            return {"success": False, "error": raw["error"]}

        analysis = await self.ai.analizar_osint(
            str(raw),
            objetivo=f"Análisis de brechas de datos para: {email}"
        )
        return {
            "success": True,
            "email": email,
            "osint_raw": raw,
            "analysis": analysis.text if analysis.success else "Análisis no disponible",
            "cost_usd": 0.0,
        }

    async def scan_target(self, target: str, ports: str = "top100") -> dict:
        """Escanea red/host → analiza vulnerabilidades con Gemma 4."""
        raw = await self.client.scan_network(target, ports)
        if "error" in raw:
            return {"success": False, "error": raw["error"]}

        analysis = await self.ai.analizar_osint(
            str(raw),
            objetivo=f"Escaneo de red para objetivo: {target}"
        )

        # Intentar geolocalizar para el globo
        globe_event = None
        if "." in target:   # parece IP
            geo = await self.client.geo_locate(target)
            if geo.get("lat") and geo.get("lon"):
                sev = 0.6 if raw.get("open_ports") else 0.3
                globe_event = BBGlobeEvent(
                    lat=geo["lat"], lng=geo["lon"],
                    label=f"Scan: {target}",
                    severity=sev,
                    radius=0.04,
                    source="bigbrother_scan",
                    metadata={"open_ports": raw.get("open_ports", [])},
                ).model_dump()

        return {
            "success": True,
            "target": target,
            "osint_raw": raw,
            "analysis": analysis.text if analysis.success else "Análisis no disponible",
            "globe_event": globe_event,
            "cost_usd": 0.0,
        }

    async def track_aircraft_live(self, callsign: str = "", icao: str = "") -> dict:
        """Rastrea aeronave y genera punto en el globo."""
        raw = await self.client.track_aircraft(callsign, icao)
        if "error" in raw:
            return {"success": False, "error": raw["error"]}

        globe_point = None
        lat = raw.get("latitude") or raw.get("lat")
        lon = raw.get("longitude") or raw.get("lon")
        if lat and lon:
            globe_point = {
                "lat": lat, "lng": lon,
                "label": callsign or icao,
                "color": "#f59e0b",
                "radius": 0.4,
                "layer": "aircraft",
                "metadata": raw,
            }

        analysis = await self.ai.analizar_osint(
            str(raw),
            objetivo=f"Seguimiento aeronave {callsign or icao}"
        )

        return {
            "success": True,
            "callsign": callsign,
            "icao": icao,
            "osint_raw": raw,
            "analysis": analysis.text if analysis.success else "Análisis no disponible",
            "globe_point": globe_point,
            "cost_usd": 0.0,
        }

    async def monitor_darkweb(self, keyword: str) -> dict:
        """Monitorea dark web para keyword → análisis Gemma 4."""
        raw = await self.client.darkweb_monitor(keyword)
        if "error" in raw:
            return {"success": False, "error": raw["error"]}

        analysis = await self.ai.analizar_osint(
            str(raw),
            objetivo=f"Monitoreo dark web: {keyword}"
        )
        return {
            "success": True,
            "keyword": keyword,
            "osint_raw": raw,
            "analysis": analysis.text if analysis.success else "Análisis no disponible",
            "cost_usd": 0.0,
        }

    async def full_profile(self, target: str, target_type: str = "username") -> dict:
        """
        Perfil completo OSINT de un objetivo.
        target_type: 'username' | 'email' | 'ip' | 'phone'
        """
        results = {}

        if target_type == "username":
            results["username"] = await self.investigate_username(target)
        elif target_type == "email":
            results["breach"] = await self.investigate_breach(target)
        elif target_type == "ip":
            results["network"] = await self.scan_target(target)
            geo = await self.client.geo_locate(target)
            results["geo"] = geo
            shodan = await self.client.shodan_host(target)
            results["shodan"] = shodan
        elif target_type == "phone":
            raw = await self.client.lookup_phone(target)
            analysis = await self.ai.analizar_osint(
                str(raw), objetivo=f"Análisis teléfono: {target}"
            )
            results["phone"] = {
                "osint_raw": raw,
                "analysis": analysis.text if analysis.success else "",
            }

        # Análisis consolidado con Gemma 4
        combined = str(results)
        final_analysis = await self.ai.analizar_osint(
            combined,
            objetivo=f"Perfil completo OSINT para {target_type}: {target}"
        )

        return {
            "success": True,
            "target": target,
            "target_type": target_type,
            "modules": results,
            "final_analysis": final_analysis.text if final_analysis.success else "",
            "cost_usd": 0.0,
            "model_used": "gemma4_local",
        }

    async def status(self) -> dict:
        bb_ok = await self.is_available()
        ai_ok = await self.ai.is_available()
        return {
            "bigbrother": {"available": bb_ok, "url": BB_URL},
            "ai_local": {"available": ai_ok, "cost_per_query": "$0.00"},
            "status": "ready" if (bb_ok and ai_ok) else ("ai_only" if ai_ok else "offline"),
        }


# Instancia global
big_brother_bridge = BigBrotherBridge()
