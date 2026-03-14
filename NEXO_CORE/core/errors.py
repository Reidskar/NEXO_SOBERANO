import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
