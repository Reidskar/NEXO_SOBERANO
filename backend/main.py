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
    
    yield
    
    # ── SHUTDOWN ──
    logger.info("🛑 NEXO Unificado shutdown")
    await obs_manager.shutdown()
    await discord_manager.shutdown()
    await discord_supervisor.shutdown()
    await web_ai_supervisor.shutdown()

app = FastAPI(
    title=core_config.APP_TITLE,
    description=core_config.APP_DESCRIPTION,
    version=core_config.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# ════════════════════════════════════════════════════════════════════
# MIDDLEWARES
# ════════════════════════════════════════════════════════════════════

app.add_middleware(CORSMiddleware, **build_cors_options())
app.add_middleware(TenantMiddleware)
app.add_middleware(PerformanceMiddleware)

if core_config.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=core_config.ALLOWED_HOSTS)

# Rate Limiters
read_limiter = InMemoryRateLimiter(max_requests=core_config.RATE_LIMIT_READ_PER_MIN, window_seconds=60)
write_limiter = InMemoryRateLimiter(max_requests=core_config.RATE_LIMIT_WRITE_PER_MIN, window_seconds=60)

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    client_ip = request.client.host if request.client else "unknown"

    if method == "OPTIONS":
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        return response

    protected = any(path.startswith(prefix) for prefix in core_config.PROTECTED_PATH_PREFIXES)
    if protected and core_config.NEXO_API_KEY:
        provided_key = (
            request.headers.get("X-NEXO-API-KEY", "")
            or request.headers.get("X-NEXO-KEY", "")
            or request.headers.get("X-API-Key", "")
        )
        if provided_key != core_config.NEXO_API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    if protected:
        limiter_key = f"{client_ip}:{path}"
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            write_limiter.check(limiter_key)
        else:
            read_limiter.check(limiter_key)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > core_config.REQUEST_MAX_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    if core_config.ENABLE_SECURITY_HEADERS:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 https: ws: wss:; "
            "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response

register_exception_handlers(app)

# ════════════════════════════════════════════════════════════════════
# ROUTER REGISTRATION
# ════════════════════════════════════════════════════════════════════

app.include_router(core_health_router)
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(stream_router)
app.include_router(legacy_router)
app.include_router(worldmonitor_router)
app.include_router(dashboard_router)
app.include_router(core_webhook_router)
app.include_router(agente_router.router)
app.include_router(eventos_router.router)
app.include_router(metrics_router.router)
app.include_router(media_router.router)
app.include_router(mobile_router.router)
app.include_router(files_router.router)
app.include_router(health_router.router)

# ════════════════════════════════════════════════════════════════════
# STATIC FILES
# ════════════════════════════════════════════════════════════════════

app.mount("/static", StaticFiles(directory="NEXO_CORE/static"), name="static")

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/panel/assets", StaticFiles(directory=frontend_dist / "assets"), name="panel-assets")
    logger.info(f"Panel admin React servido desde {frontend_dist}")

# ════════════════════════════════════════════════════════════════════
# AUTH & USER MOCK (from backend/main.py)
# ════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

ADMIN_USER = os.getenv("NEXO_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("NEXO_ADMIN_PASS", "Nexo@2026")

_users = {
    ADMIN_USER: {
        "username": ADMIN_USER,
        "email": "admin@nexo.local",
        "password": ADMIN_PASS,
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
}
_tokens = {}

# ════════════════════════════════════════════════════════════════════
# CUSTOM ENDPOINTS
# ════════════════════════════════════════════════════════════════════

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def _serve_existing_html(candidates: list[str]):
    root = Path(__file__).parent.parent
    for relative in candidates:
        target = root / relative
        if target.exists():
            return FileResponse(str(target))
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/")
async def root():
    return {
        "status": "NEXO_CORE activo",
        "mode": backend_config.NEXO_MODE,
        "version": core_config.APP_VERSION,
        "docs": "/api/docs",
        "warroom": "/warroom",
    }

@app.get("/health")
async def health():
    """Health check unificado solicitado."""
    return {"status": "ok", "mode": backend_config.NEXO_MODE}

@app.get("/war-room")
async def war_room(request: Request, api_key: str = Security(api_key_header)):
    actual_key = api_key or request.query_params.get("api_key")
    if actual_key != os.getenv("NEXO_API_KEY", "nexo_dev_key_2025"):
        return HTMLResponse(
            content="<html><body style='background:#0a0a0c;color:red;font-family:sans-serif;padding:50px;text-align:center;'>"
                    "<h2>Acceso Denegado (403)</h2><p>Falta o es incorrecta la API Key.</p>"
                    "</body></html>",
            status_code=403
        )
    return FileResponse("NEXO_CORE/static/war_room.html")

@app.get("/control-center")
async def control_center():
    return _serve_existing_html(["frontend_public/control_center.html"])

@app.get("/warroom")
async def warroom_default_page():
    return _serve_existing_html([
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
