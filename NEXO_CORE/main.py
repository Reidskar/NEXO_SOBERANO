from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from NEXO_CORE import config
from NEXO_CORE.api.health import router as health_router
from NEXO_CORE.api.legacy import router as legacy_router
from NEXO_CORE.api.stream import router as stream_router
from NEXO_CORE.core.errors import register_exception_handlers
from NEXO_CORE.core.logger import setup_logging
from NEXO_CORE.middleware.cors import build_cors_options
from NEXO_CORE.middleware.rate_limit import InMemoryRateLimiter
from NEXO_CORE.services.discord_manager import discord_manager
from NEXO_CORE.services.obs_manager import obs_manager

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(CORSMiddleware, **build_cors_options())

if config.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)

read_limiter = InMemoryRateLimiter(max_requests=config.RATE_LIMIT_READ_PER_MIN, window_seconds=60)
write_limiter = InMemoryRateLimiter(max_requests=config.RATE_LIMIT_WRITE_PER_MIN, window_seconds=60)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    client_ip = request.client.host if request.client else "unknown"

    protected = any(path.startswith(prefix) for prefix in config.PROTECTED_PATH_PREFIXES)
    if protected and config.NEXO_API_KEY:
        if request.headers.get("X-NEXO-KEY", "") != config.NEXO_API_KEY:
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
            if int(content_length) > config.REQUEST_MAX_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    if config.ENABLE_SECURITY_HEADERS:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        response.headers.setdefault("Cache-Control", "no-store")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response


register_exception_handlers(app)

app.include_router(health_router)
app.include_router(stream_router)
app.include_router(legacy_router)


def _serve_existing_html(candidates: list[str]):
    root = Path(__file__).resolve().parent.parent
    for relative in candidates:
        target = root / relative
        if target.exists():
            return FileResponse(str(target))
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/")
async def root():
    return {
        "status": "NEXO_CORE activo",
        "version": config.APP_VERSION,
        "docs": "/api/docs",
        "control_center": "/control-center",
    }


@app.get("/control-center")
async def control_center():
    return _serve_existing_html(["frontend_public/control_center.html"])


@app.get("/warroom")
async def warroom_default_page():
    return _serve_existing_html([
        "warroom_v2.html",
        "frontend_public/warroom_v2.html",
    ])


@app.get("/warroom_v2.html")
async def warroom_v2_page():
    return _serve_existing_html([
        "warroom_v2.html",
        "frontend_public/warroom_v2.html",
    ])


@app.get("/admin_dashboard.html")
async def admin_dashboard_page():
    return _serve_existing_html([
        "admin_dashboard.html",
        "frontend_public/admin_dashboard_v2.html",
    ])


@app.on_event("startup")
async def startup_event():
    logger.info("NEXO_CORE startup")
    obs_manager.start_background_reconnect()
    discord_manager.start_background_reconnect()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("NEXO_CORE shutdown")
    await obs_manager.shutdown()
    await discord_manager.shutdown()
