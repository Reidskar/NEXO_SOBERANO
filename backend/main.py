# This file has been removed to avoid conflicts with main.py in the root directory.
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

from fastapi import FastAPI, HTTPException, Header, Request, WebSocket, WebSocketDisconnect, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
import threading
import time
import subprocess

# Configs
from backend import config as backend_config
from NEXO_CORE import config as core_config

# Core components & Services
from NEXO_CORE.core.errors import register_exception_handlers
from NEXO_CORE.core.logger import setup_logging
from NEXO_CORE.middleware.cors import build_cors_options
from NEXO_CORE.middleware.rate_limit import InMemoryRateLimiter
from NEXO_CORE.services.discord_manager import discord_manager
from NEXO_CORE.services.obs_manager import obs_manager
from NEXO_CORE.agents.discord_supervisor import discord_supervisor
from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor
from NEXO_CORE.agents.livestream_supervisor import livestream_supervisor
from NEXO_CORE.core.websocket_manager import manager
from NEXO_CORE.core.state_manager import state_manager
from backend.middleware.tenant_middleware import TenantMiddleware

# ── Phase 2: Imports & Core Modules ──────────────────────────────────────────
import uvicorn
from contextlib import asynccontextmanager

# Routers
from NEXO_CORE.api.health import router as core_health_router
from NEXO_CORE.api.ai import router as ai_router
from NEXO_CORE.api.knowledge import router as knowledge_router
from NEXO_CORE.api.legacy import router as legacy_router
from NEXO_CORE.api.stream import router as stream_router
from NEXO_CORE.api.dashboard import router as dashboard_router
from NEXO_CORE.api.webhooks import router as core_webhook_router

# Force-patching attributes to avoid AttributeError in some environments
import NEXO_CORE.core.database
NEXO_CORE.core.database.core_webhook_router = core_webhook_router
NEXO_CORE.core.database.core_health_router = core_health_router

from backend.services.worldmonitor_bridge import router as worldmonitor_router
from backend.routes.agente import router as agente_router
from backend.routes.eventos import router as eventos_router
from backend.routes.metrics import router as metrics_router
from backend.routes.media import router as media_router
from backend.routes.mobile import router as mobile_router
from backend.routes.files import router as files_router
from backend.routes.sesiones import router as sesiones_router
from backend.routes.device import router as device_router
from backend.routes.devices import router as devices_router
from backend.routes.auth_google import router as auth_google_router
from backend.routes.shopify import router as shopify_router
from backend.routes.osint import router as osint_router
from backend.middleware.monitoring import PerformanceMiddleware
from backend.core import heartbeat as heartbeat_service

# ════════════════════════════════════════════════════════════════════
# SETUP & LOGGING
# ════════════════════════════════════════════════════════════════════

from contextlib import asynccontextmanager
from backend import health as health_router
from backend.config import config as backend_app_config

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    # Ampliar el thread pool de anyio (default=40) para que StaticFiles y
    # los sync route handlers no se bloqueen mutuamente bajo carga.
    import anyio.to_thread
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 200
    logger.info(f"anyio thread pool ampliado a {limiter.total_tokens} tokens")

    mode = backend_app_config.MODE
    logger.info(f"NEXO startup — modo: {mode}")
    
    if not backend_app_config.IS_PRODUCTION:
        # Solo en PC local — Railway no tiene OBS ni web supervisor
        obs_manager.start_background_reconnect()
        web_ai_supervisor.start()
        livestream_supervisor.start()
        logger.info("OBS Manager + Web AI + Livestream Supervisors activados")
    
    # Siempre activo (Railway + local)
    discord_supervisor.start()
    logger.info("Discord Supervisor activado")

    # Scheduler de automatizaciones diarias (Gemma)
    try:
        from NEXO_CORE.services.nexo_scheduler import nexo_scheduler, setup_tareas_default
        setup_tareas_default()
        nexo_scheduler.iniciar()
        logger.info("Nexo Scheduler activado (diario, RRSS, OSINT, reflexion)")
    except Exception as e:
        logger.warning(f"[Scheduler] No se pudo iniciar: {e}")

    # OSINT Autonomous Scraper (Phase 12)
    try:
        from NEXO_CORE.workers.osint_scraper import osint_scraper
        if not backend_app_config.IS_PRODUCTION:
            osint_scraper.start()
            logger.info("OSINT Autonomous Scraper activado")
    except Exception as e:
        logger.warning(f"[OSINT Scraper] No se pudo iniciar: {e}")

    # Iniciar loop del Kindle
    t = threading.Thread(target=kindle_refresh_loop, daemon=True)
    t.start()

    # Heartbeat 24/7
    heartbeat_service.start(interval=60)

    # Control remoto de dispositivo (Tailscale/USB)
    try:
        from backend.services.device_control import device_control
        result = device_control.connect()
        if result["ok"]:
            logger.info(f"[DEVICE] Conectado al arranque: {result['device']} via {result['via']}")
        else:
            logger.warning(f"[DEVICE] Sin dispositivo en arranque (se reintentará): {result.get('error')}")
    except Exception as e:
        logger.warning(f"[DEVICE] Error inicializando control de dispositivo: {e}")

    yield
    
    # ── SHUTDOWN ──
    logger.info("🛑 NEXO Unificado shutdown")
    await obs_manager.shutdown()
    await discord_manager.shutdown()
    await discord_supervisor.shutdown()
    await livestream_supervisor.shutdown()

app = FastAPI(title="NEXO Unified Backend", lifespan=lifespan)

# CORS PRO-MODE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# StaticFiles SIEMPRE al final (pero lo definimos aquí para que esté disponible)
if os.path.isdir("frontend/dist"):
    app.mount("/dist", StaticFiles(directory="frontend/dist", html=True), name="frontend_dist")

# Auth
class LoginRequest(BaseModel):
    username: str
    password: str

# In-memory auth store — single admin user from env
_users: dict = {
    os.getenv("NEXO_ADMIN_USER", "admin"): {
        "username": os.getenv("NEXO_ADMIN_USER", "admin"),
        "password": os.getenv("NEXO_ADMIN_PASS", "nexo2026"),
        "email": os.getenv("ADMIN_EMAIL", "admin@elanarcocapital.com"),
        "role": "admin",
    }
}
_tokens: dict = {}

@app.post("/auth/login")
async def auth_login(payload: LoginRequest):
    user = _users.get(payload.username)
    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = str(uuid.uuid4())
    _tokens[token] = payload.username
    return {"access_token": token, "token_type": "bearer", "user": {"username": user["username"], "email": user["email"], "role": user["role"]}}

# ════════════════════════════════════════════════════════════════════
# WEBSOCKET MANAGER (Alertas en tiempo real)
# ════════════════════════════════════════════════════════════════════

# Shared WebSocket manager imported from NEXO_CORE.core.websocket_manager

@app.websocket("/ws/alerts/{tenant_slug}")
async def websocket_endpoint(websocket: WebSocket, tenant_slug: str):
    await manager.connect(websocket, tenant_slug)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_slug)

# ── Mount Routers (NEXO_CORE + Backend) ───────────────────────────────────
app.include_router(core_webhook_router)  # Handles /api/webhooks/ingest
app.include_router(core_health_router)
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(legacy_router)
app.include_router(stream_router)
app.include_router(dashboard_router)
app.include_router(worldmonitor_router)
# Intel Hub — Gemma local, diario, scheduler
from NEXO_CORE.api.intel import router as intel_router
app.include_router(intel_router)
app.include_router(agente_router)
app.include_router(eventos_router)
app.include_router(metrics_router)
app.include_router(media_router)
app.include_router(mobile_router)
app.include_router(files_router)
app.include_router(sesiones_router)
app.include_router(device_router)
app.include_router(devices_router)
app.include_router(auth_google_router)
app.include_router(shopify_router)
app.include_router(osint_router)
# Motor cognitivo — voz, texto, intents
from backend.routes.cognitive import router as cognitive_router
app.include_router(cognitive_router)
# Voice STT/TTS — transcripción con faster-whisper
try:
    from NEXO_CORE.api.voice import router as voice_router
    app.include_router(voice_router)
except Exception as _ve:
    import logging; logging.getLogger(__name__).warning(f"[NEXO] Voice router no cargado: {_ve}")
# Video Studio — generación de Reels/YouTube con ffmpeg + TTS
try:
    from backend.routes.video_studio import router as video_studio_router
    app.include_router(video_studio_router, prefix="/api")
except Exception as _ve:
    import logging; logging.getLogger(__name__).warning(f"[NEXO] Video studio no cargado: {_ve}")
# Chat Comercial — endpoint para chatbots de clientes (Make.com, WhatsApp, web)
try:
    from backend.routes.chat_comercial import router as chat_comercial_router
    app.include_router(chat_comercial_router)
except Exception as _ve:
    import logging; logging.getLogger(__name__).warning(f"[NEXO] Chat comercial no cargado: {_ve}")

# ── Gemini 3.1 Live — WebSocket de audio en tiempo real ───────────────────
try:
    from backend.services.gemini_live_service import register_gemini_live_ws
    register_gemini_live_ws(app)
    logger.info("Gemini Live WebSocket registrado en /ws/gemini-live")
except Exception as e:
    logger.warning("Gemini Live WebSocket no disponible: %s", e)

@app.get("/", include_in_schema=False)
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dist/", status_code=302)

@app.get("/api/agente/status")
async def get_agente_status():
    return state_manager.snapshot().get("last_agent_checkin")

# Kindle dashboard auto-refresh (cada 5 min)
def kindle_refresh_loop():
    logger.info("Kindle Refresh Loop started")
    while True:
        # Ejecutar inmediatamente y luego esperar
        try:
            subprocess.run(
                ["python", "kindle_dashboard/generar_dashboard.py"],
                cwd=os.getcwd(),
                capture_output=True, timeout=30
            )
            logger.info("Kindle dashboard updated")
        except Exception as e:
            logger.error(f"Kindle dashboard update failed: {e}")
        time.sleep(300)  # 5 minutos

# Startup/shutdown events removed in favor of lifespan

# ── IPs permitidas para páginas internas (torre + Tailscale) ─────────────────
_INTERNAL_PREFIXES = (
    "127.", "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.",
    "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "100.",   # Tailscale range
)

def _es_interno(request: Request) -> bool:
    ip = request.headers.get("cf-connecting-ip") or \
         request.headers.get("x-real-ip") or \
         request.headers.get("x-forwarded-for", "").split(",")[0].strip() or \
         (request.client.host if request.client else "")
    return any(ip.startswith(p) for p in _INTERNAL_PREFIXES)


@app.get("/audio/latest")
async def audio_latest():
    from fastapi.responses import FileResponse as FR
    from backend.services.tts_service import get_audio_path, audio_disponible
    if not audio_disponible():
        from fastapi.responses import Response
        return Response(status_code=204)
    return FR(str(get_audio_path()), media_type="audio/mpeg", headers={"Cache-Control": "no-cache"})


@app.get("/nexo-avatar")
async def nexo_avatar():
    p = Path("frontend_public/nexo_avatar.html")
    if p.exists():
        return FileResponse(str(p), media_type="text/html")
    return HTMLResponse("<h1>nexo_avatar.html no encontrado</h1>", status_code=404)

@app.get("/nexo-intro")
async def nexo_intro():
    p = Path("frontend_public/nexo_intro.html")
    if p.exists():
        return FileResponse(str(p), media_type="text/html")
    return HTMLResponse("<body style='background:#000;color:#fff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'><h1>NEXO SOBERANO</h1></body>", media_type="text/html")

@app.get("/nexo-pausa")
async def nexo_pausa():
    p = Path("frontend_public/nexo_pausa.html")
    if p.exists():
        return FileResponse(str(p), media_type="text/html")
    return HTMLResponse("<body style='background:#050510;color:#336;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'><h2>— PAUSA —</h2></body>", media_type="text/html")


@app.get("/intel")
async def intel_hub_page(request: Request):
    if not _es_interno(request):
        return HTMLResponse("<h1>403 — Acceso restringido</h1>", status_code=403)
    p = Path("frontend_public/nexo_intel.html")
    if p.exists():
        return FileResponse(str(p))
    return HTMLResponse("<h1>nexo_intel.html no encontrado</h1>", status_code=404)


@app.get("/grafo")
async def grafo_actores_page(request: Request):
    if not _es_interno(request):
        return HTMLResponse("<h1>403 — Acceso restringido</h1>", status_code=403)
    p = Path("frontend_public/nexo_grafo.html")
    if p.exists():
        return FileResponse(str(p))
    return HTMLResponse("<h1>nexo_grafo.html no encontrado</h1>", status_code=404)


@app.get("/control")
async def control_center_page(request: Request):
    if not _es_interno(request):
        return HTMLResponse("<h1>403 — Acceso restringido</h1>", status_code=403)
    p = Path("frontend_public/control_center.html")
    if p.exists():
        return FileResponse(str(p))
    return HTMLResponse("<h1>control_center.html no encontrado</h1>", status_code=404)


@app.get("/admin")
async def admin_dashboard_page(request: Request):
    if not _es_interno(request):
        return HTMLResponse("<h1>403 — Acceso restringido</h1>", status_code=403)
    p = Path("frontend_public/admin_dashboard_v2.html")
    if p.exists():
        return FileResponse(str(p))
    return HTMLResponse("<h1>admin_dashboard_v2.html no encontrado</h1>", status_code=404)


@app.get("/phone/setup.sh")
async def phone_setup_script():
    """Script de setup del agente móvil — instalar en Termux con: curl http://IP:8000/phone/setup.sh | bash"""
    from fastapi.responses import PlainTextResponse
    p = Path("discord_bot/mobile_agent/nexo_phone_setup.sh")
    if p.exists():
        return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="text/plain")
    return PlainTextResponse("# Script no encontrado", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
