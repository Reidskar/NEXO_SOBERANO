from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import logging

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # En una app real, esto extraería el tenant_slug del JWT o un header Auth
        # Por ahora lo simulamos con un header X-Tenant-Slug o usando "demo" por defecto
        tenant_slug = request.headers.get("X-Tenant-Slug", "demo")
        request.state.tenant_slug = tenant_slug
        response = await call_next(request)
        return response
