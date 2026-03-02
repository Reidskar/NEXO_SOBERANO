"""
FastAPI — Punto de entrada unificado del backend
Puerto: 8000
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import logging
import os
import uuid
from datetime import datetime, timezone

from backend import config
from backend.routes import agente
from backend.routes import eventos

# ════════════════════════════════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# APP
# ════════════════════════════════════════════════════════════════════

app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


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
# CORS — CORRECTO (sin allow_origins=["*"])
# ════════════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# ════════════════════════════════════════════════════════════════════
# RUTAS
# ════════════════════════════════════════════════════════════════════

# Raíz
@app.get("/")
def root():
    """Información básica del API"""
    return {
        "nombre": config.APP_TITLE,
        "version": config.APP_VERSION,
        "descripcion": config.APP_DESCRIPTION,
        "endpoints": {
            "docs": "/api/docs",
            "openapi": "/api/openapi.json",
            "agente": "/agente...",
            "infraestructura": "/eventos/infraestructura?query=...",
        }
    }


@app.get("/control-center")
def control_center():
    """Panel web de monitoreo operacional."""
    page = Path(__file__).parent.parent / "frontend_public" / "control_center.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail=f"No existe panel: {page}")
    return FileResponse(str(page))


def _serve_existing_html(candidates: list[str]):
    root = Path(__file__).parent.parent
    for relative in candidates:
        target = root / relative
        if target.exists():
            return FileResponse(str(target))
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/warroom_v2.html")
def warroom_page():
    return _serve_existing_html([
        "warroom_v2.html",
        "frontend_public/warroom_v2.html",
    ])


@app.get("/warroom_v3.html")
def warroom_v3_page():
    return _serve_existing_html([
        "NEXO_SOBERANO_v3.html",
        "warroom_v3.html",
        "frontend_public/warroom_v3.html",
    ])


@app.get("/warroom")
def warroom_default_page():
    return _serve_existing_html([
        "NEXO_SOBERANO_v3.html",
        "warroom_v3.html",
        "warroom_v2.html",
        "frontend_public/warroom_v2.html",
    ])


@app.get("/admin_dashboard.html")
def admin_dashboard_page():
    return _serve_existing_html([
        "admin_dashboard.html",
        "frontend_public/admin_dashboard_v2.html",
    ])


@app.get("/app-user")
def app_user_page():
    return _serve_existing_html([
        "frontend_public/app_user_mobile.html",
    ])


@app.get("/app-admin")
def app_admin_page():
    return _serve_existing_html([
        "frontend_public/app_admin_mobile.html",
    ])


@app.get("/app-download")
def app_download_page():
    return _serve_existing_html([
        "frontend_public/app_download.html",
    ])

# Health check general
@app.get("/health")
def health():
    """Health check global"""
    return {
        "status": "ok",
        "service": "nexo-soberano-backend",
        "version": config.APP_VERSION,
    }


@app.post("/auth/login")
def auth_login(payload: LoginRequest):
    user = _users.get(payload.username)
    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = str(uuid.uuid4())
    _tokens[token] = payload.username
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/auth/register")
def auth_register(payload: RegisterRequest):
    if payload.username in _users:
        raise HTTPException(status_code=409, detail="Usuario ya existe")

    _users[payload.username] = {
        "username": payload.username,
        "email": payload.email,
        "password": payload.password,
        "role": "user",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"ok": True, "user": {"username": payload.username, "email": payload.email}}


@app.get("/admin/users")
def admin_users(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = authorization.split(" ", 1)[1].strip()
    username = _tokens.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="Token inválido")

    users_payload = []
    for user in _users.values():
        users_payload.append(
            {
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "is_active": user["is_active"],
                "created_at": user["created_at"],
            }
        )

    return {"ok": True, "users": users_payload}

# Rutas del agente
app.include_router(agente.router)
# Rutas de eventos/infraestructura
app.include_router(eventos.router)

# ════════════════════════════════════════════════════════════════════
# MANEJO DE ERRORES GLOBAL
# ════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Captura excepciones globales"""
    logger.error(f"Excepción no capturada: {exc}", exc_info=True)
    return {
        "error": "Internal Server Error",
        "detail": str(exc),
        "status": 500
    }

# ════════════════════════════════════════════════════════════════════
# SERVIR FRONTEND (si existe)
# ════════════════════════════════════════════════════════════════════

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/static", StaticFiles(directory=frontend_dist), name="static")
    logger.info(f"Frontend servido desde {frontend_dist}")
else:
    logger.warning(f"Frontend no encontrado en {frontend_dist} (normal en desarrollo)")

# ════════════════════════════════════════════════════════════════════
# STARTUP/SHUTDOWN
# ════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Iniciación del servidor"""
    logger.info("🚀 Backend iniciado")
    logger.info(f"CORS permitido en: {config.CORS_ORIGINS}")
    logger.info(f"Presupuesto diario: {config.MAX_TOKENS_DIA:,} tokens")

@app.on_event("shutdown")
async def shutdown_event():
    """Cierre del servidor"""
    logger.info("🛑 Backend detenido")

# ════════════════════════════════════════════════════════════════════
# EJECUCIÓN LOCAL
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Iniciando en http://{config.HOST}:{config.PORT}")
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )
