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
from NEXO_CORE.core.state_manager import state_manager
from backend.middleware.tenant_middleware import TenantMiddleware

# Routers
from NEXO_CORE.api.health import router as core_health_router
from NEXO_CORE.api.ai import router as ai_router
from NEXO_CORE.api.knowledge import router as knowledge_router
from NEXO_CORE.api.legacy import router as legacy_router
from NEXO_CORE.api.stream import router as stream_router
from NEXO_CORE.api.dashboard import router as dashboard_router
from NEXO_CORE.api.webhooks import router as core_webhook_router
from backend.services.worldmonitor_bridge import router as worldmonitor_router
from backend.routes import agente as agente_router
from backend.routes import eventos as eventos_router
from backend.routes import metrics as metrics_router
from backend.routes import media as media_router
from backend.routes import mobile as mobile_router
from backend.routes import files as files_router
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

    # Iniciar loop del Kindle
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
    logger.info(f"Panel admin React servido desde {frontend_dist}")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    import os
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    import os
    from backend.database import test_connection
    from backend.routes.agente import router as agente_router

    app = FastAPI(title="NEXO SOBERANO API", version="2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://elanarcocapital.com", "https://elanarcocapital.vercel.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agente_router)

    @app.on_event("startup")
    async def startup():
        await test_connection()

    @app.get("/health")
    async def health():
        db_ok = await test_connection()
        return {"status": "ok", "db": "connected" if db_ok else "fail"}

    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
        "NEXO_SOBERANO_v3.html",
        "warroom_v3.html",
        "warroom_v2.html",
        "frontend_public/warroom_v2.html",
    ])

@app.get("/landing", response_class=HTMLResponse)
def landing_page():
    path = Path("frontend_public/landing_nexo.html")
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Landing Page Not Found</h1>", status_code=404)

# Auth
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
                except:
                    pass

manager = ConnectionManager()

@app.websocket("/ws/alerts/{tenant_slug}")
async def websocket_endpoint(websocket: WebSocket, tenant_slug: str):
    await manager.connect(websocket, tenant_slug)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_slug)

# ════════════════════════════════════════════════════════════════════
# WEBHOOK INGEST (Nuevos Agentes)
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
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    state_manager.set_agent_checkin(payload)
    
    await manager.broadcast(data.tenant_slug, payload)
    return {"status": "success", "received": data.type, "broadcasted": True}

@app.get("/api/agente/status")
def get_agente_status():
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
