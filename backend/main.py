from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict
import threading
import time
import subprocess

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# Configs
from backend.config import config as backend_app_config

# Core components & Services
from NEXO_CORE.core.errors import register_exception_handlers
from NEXO_CORE.core.logger import setup_logging
from NEXO_CORE.middleware.cors import build_cors_options
from NEXO_CORE.services.discord_manager import discord_manager
from NEXO_CORE.services.obs_manager import obs_manager
from NEXO_CORE.agents.discord_supervisor import discord_supervisor
from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor
from NEXO_CORE.core.state_manager import state_manager
from backend.middleware.tenant_middleware import TenantMiddleware
from backend.middleware.monitoring import PerformanceMiddleware
from backend.core import heartbeat as heartbeat_service

# Routers — NEXO_CORE
from NEXO_CORE.api.health import router as core_health_router
from NEXO_CORE.api.ai import router as ai_router
from NEXO_CORE.api.knowledge import router as knowledge_router
from NEXO_CORE.api.legacy import router as legacy_router
from NEXO_CORE.api.stream import router as stream_router
from NEXO_CORE.api.dashboard import router as dashboard_router
from NEXO_CORE.api.webhooks import router as core_webhook_router

# Routers — backend
from backend import health as health_module
from backend.services.worldmonitor_bridge import router as worldmonitor_router
from backend.routes.agente import router as agente_router
from backend.routes.eventos import router as eventos_router
from backend.routes.metrics import router as metrics_router
from backend.routes.media import router as media_router
from backend.routes.mobile import router as mobile_router
from backend.routes.files import router as files_router
from backend.routes.globe_control import router as globe_router, set_broadcast
from backend.routes.osint import router as osint_router
from backend.routes.nexo_platform import router as platform_router
from backend.routes.phone_setup import router as phone_setup_router
from backend.routes.nexo_integrations import router as integrations_router

# ════════════════════════════════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════════════════════════════════

setup_logging()
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# AUTH (in-memory, simple)
# ════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

_users: Dict[str, dict] = {
    os.getenv("NEXO_ADMIN_USER", "admin"): {
        "username": os.getenv("NEXO_ADMIN_USER", "admin"),
        "password": os.getenv("NEXO_ADMIN_PASS", "nexo_admin_2025"),
        "email": "admin@elanarcocapital.com",
        "role": "admin",
    }
}
_tokens: Dict[str, str] = {}

# ════════════════════════════════════════════════════════════════════
# KINDLE REFRESH
# ════════════════════════════════════════════════════════════════════

def kindle_refresh_loop():
    logger.info("Kindle Refresh Loop started")
    while True:
        try:
            subprocess.run(
                ["python", "kindle_dashboard/generar_dashboard.py"],
                cwd=os.getcwd(),
                capture_output=True,
                timeout=30,
            )
            logger.info("Kindle dashboard updated")
        except Exception as e:
            logger.error(f"Kindle dashboard update failed: {e}")
        time.sleep(300)  # 5 min

# ════════════════════════════════════════════════════════════════════
# LIFESPAN
# ════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    mode = backend_app_config.MODE
    logger.info(f"NEXO startup — modo: {mode}")

    if not backend_app_config.IS_PRODUCTION:
        # Solo en PC local — Railway no tiene OBS ni web supervisor
        obs_manager.start_background_reconnect()
        web_ai_supervisor.start()
        logger.info("OBS Manager + Web AI Supervisor activados")

    # Siempre activo (Railway + local)
    discord_supervisor.start()
    logger.info("Discord Supervisor activado")

    # Kindle dashboard auto-refresh
    t = threading.Thread(target=kindle_refresh_loop, daemon=True)
    t.start()

    # Heartbeat 24/7
    heartbeat_service.start(interval=60)

    yield

    # ── SHUTDOWN ──
    logger.info("🛑 NEXO Unificado shutdown")
    await obs_manager.shutdown()
    await discord_manager.shutdown()
    await discord_supervisor.shutdown()
    logger.info("NEXO shutdown completo")

# ════════════════════════════════════════════════════════════════════
# APP + MIDDLEWARE
# ════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="NEXO SOBERANO API",
    version="3.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, **build_cors_options())
app.add_middleware(TenantMiddleware)
app.add_middleware(PerformanceMiddleware)

register_exception_handlers(app)

# ════════════════════════════════════════════════════════════════════
# ROUTERS
# ════════════════════════════════════════════════════════════════════

app.include_router(core_health_router)
app.include_router(health_module.router)
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(legacy_router)
app.include_router(stream_router)
app.include_router(dashboard_router)
app.include_router(core_webhook_router)
app.include_router(worldmonitor_router)
app.include_router(agente_router)
app.include_router(eventos_router)
app.include_router(metrics_router)
app.include_router(media_router)
app.include_router(mobile_router)
app.include_router(files_router)

# ════════════════════════════════════════════════════════════════════
# WEBSOCKET MANAGER (Alertas en tiempo real)
# ════════════════════════════════════════════════════════════════════

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant: str):
        await websocket.accept()
        if tenant not in self.active_connections:
            self.active_connections[tenant] = []
        self.active_connections[tenant].append(websocket)
        logger.info(f"🔌 Cliente WS conectado a tenant: {tenant}")

    def disconnect(self, websocket: WebSocket, tenant: str):
        if tenant in self.active_connections:
            self.active_connections[tenant].remove(websocket)

    async def broadcast(self, tenant: str, message: dict):
        if tenant in self.active_connections:
            for connection in self.active_connections[tenant]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# Wire globe broadcast → WS manager (must be before globe_router include)
set_broadcast(lambda msg: manager.broadcast("globe", msg))

app.include_router(globe_router)
app.include_router(osint_router)
app.include_router(platform_router)
app.include_router(phone_setup_router)
app.include_router(integrations_router)

# ════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ════════════════════════════════════════════════════════════════════

@app.websocket("/ws/alerts/{tenant_slug}")
async def websocket_endpoint(websocket: WebSocket, tenant_slug: str):
    await manager.connect(websocket, tenant_slug)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_slug)

# ════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ════════════════════════════════════════════════════════════════════

@app.post("/auth/login")
async def auth_login(payload: LoginRequest):
    user = _users.get(payload.username)
    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = str(uuid.uuid4())
    _tokens[token] = payload.username
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": user["username"], "email": user["email"], "role": user["role"]},
    }

# ════════════════════════════════════════════════════════════════════
# WEBHOOK INGEST
# ════════════════════════════════════════════════════════════════════

class WebhookData(BaseModel):
    tenant_slug: str = "demo"
    type: str = "mobile_agent"
    title: str = ""
    body: str = ""
    severity: float = 0.5

@app.post("/api/webhooks/ingest")
async def api_webhook_ingest(data: WebhookData, x_api_key: str = Header(None)):
    if x_api_key != os.getenv("NEXO_API_KEY", "nexo_dev_key_2025"):
        raise HTTPException(status_code=401, detail="API Key inválida")

    payload = {
        "tipo": data.type,
        "titulo": data.title,
        "descripcion": data.body,
        "severidad": data.severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    state_manager.set_agent_checkin(payload)
    await manager.broadcast(data.tenant_slug, payload)
    return {"status": "success", "received": data.type, "broadcasted": True}

@app.get("/api/agente/status")
def get_agente_status():
    return state_manager.snapshot().get("last_agent_checkin")

# ════════════════════════════════════════════════════════════════════
# STATIC HTML PAGES — frontend_public/
# ════════════════════════════════════════════════════════════════════

def _serve_html(filename: str, fallback: str = "Not Found") -> HTMLResponse:
    path = Path("frontend_public") / filename
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse(content=f"<h1>{fallback}</h1>", status_code=404)


@app.get("/landing", response_class=HTMLResponse)
def landing_page():
    return _serve_html("landing_nexo.html", "Landing Page Not Found")


@app.get("/omniglobe", response_class=HTMLResponse)
def omniglobe_page():
    path = Path("frontend_public/omniglobe.html")
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>OmniGlobe — Building...</h1>", status_code=503)


@app.get("/flowmap", response_class=HTMLResponse)
def flowmap_page():
    path = Path("frontend_public/flowmap.html")
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>FlowMap — Building...</h1>", status_code=503)


@app.get("/control-center", response_class=HTMLResponse)
def control_center_page():
    return _serve_html("control_center.html", "Control Center Not Found")


# ════════════════════════════════════════════════════════════════════
# STATIC ASSETS — nexo_config.js, manifest.json, sw.js
# (explicit routes so they are always reachable at the root path)
# ════════════════════════════════════════════════════════════════════

@app.get("/nexo_config.js")
def nexo_config_js():
    return FileResponse("frontend_public/nexo_config.js", media_type="application/javascript")


@app.get("/manifest.json")
def manifest_json():
    return FileResponse("frontend_public/manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse("frontend_public/sw.js", media_type="application/javascript")


# ════════════════════════════════════════════════════════════════════
# STATIC FILE MOUNT — serves all remaining files in frontend_public/
# MUST be last so it doesn't shadow the routes above
# ════════════════════════════════════════════════════════════════════

_pub_dir = Path("frontend_public")
if _pub_dir.exists():
    app.mount("/public", StaticFiles(directory=str(_pub_dir)), name="public_static")

# React SPA (built frontend) — served at root
_dist_dir = Path("frontend/dist")
if _dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="spa")

# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
