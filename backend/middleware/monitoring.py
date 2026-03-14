from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger("nexo.perf")

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = round((time.perf_counter() - start) * 1000, 2)
        
        # Logear latencia
        logger.info(f"{request.method} {request.url.path} → {response.status_code} [{duration}ms]")
        
        # Añadir header a la respuesta
        response.headers["X-Response-Time"] = f"{duration}ms"
        return response
