from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
import hmac
import hashlib
import os

NEXO_PASSWORD_HASH = os.getenv("NEXO_UI_PASSWORD_HASH", "")

async def verify_ui_access(request: Request, call_next):
    if request.url.path.startswith("/api") or request.url.path in ["/login", "/auth/login", "/docs", "/openapi.json", "/"]:
        return await call_next(request)
        
    session_token = request.cookies.get("nexo_session")
    if not session_token or not _verify_token(session_token):
        return RedirectResponse(url="/login")
        
    return await call_next(request)

def _verify_token(token: str) -> bool:
    try:
        expected = hmac.new(
            os.getenv("NEXO_SECRET_KEY", "changeme").encode(),
            b"nexo_session",
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(token, expected)
    except Exception:
        return False
