"""
backend/routes/auth_google.py
OAuth Google via web callback — no requiere browser local.
El frontend abre la URL, el usuario aprueba, Google redirige al /callback.
"""
from __future__ import annotations

import os
import secrets
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/google", tags=["auth"])

AUTH_DIR = Path("backend/auth")
AUTH_DIR.mkdir(parents=True, exist_ok=True)

_SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]
_TOKEN_PATH = AUTH_DIR / "token_google_manage_full.json"
_CREDS_PATH = AUTH_DIR / "credenciales_google.json"

# State tokens en memoria (TTL no crítico — autorización única)
_state_store: dict[str, str] = {}


def _get_redirect_uri(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/google/callback"


@router.get("/url")
def google_auth_url(request: Request):
    """
    Genera la URL de autorización de Google.
    El frontend redirige al usuario a esta URL o la abre en una ventana nueva.
    """
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise HTTPException(500, "google-auth-oauthlib no instalado")

    if not _CREDS_PATH.exists():
        raise HTTPException(
            400,
            detail=f"Archivo de credenciales no encontrado: {_CREDS_PATH}. "
                   "Descárgalo de Google Cloud Console y colócalo en backend/auth/credenciales_google.json",
        )

    redirect_uri = _get_redirect_uri(request)
    state = secrets.token_urlsafe(16)

    flow = Flow.from_client_secrets_file(
        str(_CREDS_PATH),
        scopes=_SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    _state_store[state] = redirect_uri
    logger.info("[AUTH] URL de autorización Google generada")
    return {"auth_url": auth_url, "state": state, "redirect_uri": redirect_uri}


@router.get("/callback")
def google_auth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Google redirige aquí después de que el usuario aprueba.
    Intercambia el code por tokens y los guarda en backend/auth/.
    """
    if error:
        logger.warning(f"[AUTH] Google rechazó autorización: {error}")
        return HTMLResponse(
            f"""<html><body style='font-family:monospace;background:#0a0a0a;color:#f55;padding:40px'>
            <h2>❌ Autorización rechazada</h2>
            <p>Error: {error}</p>
            <p>Posible causa: tu correo no está en la lista de usuarios de prueba.<br>
            Ve a <b>Google Cloud Console → OAuth Consent Screen → Test users</b> y agrega tu cuenta.</p>
            </body></html>""",
            status_code=400,
        )

    if not code:
        raise HTTPException(400, "Falta el código de autorización")

    if state not in _state_store:
        raise HTTPException(400, "State inválido o expirado — reinicia el flujo de autorización")

    try:
        from google_auth_oauthlib.flow import Flow

        redirect_uri = _state_store.pop(state)
        flow = Flow.from_client_secrets_file(
            str(_CREDS_PATH),
            scopes=_SCOPES,
            redirect_uri=redirect_uri,
            state=state,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        token_json = creds.to_json()

        # Guardar en todos los paths esperados por google_connector.py
        token_paths = [
            AUTH_DIR / "token_google_manage_full.json",
            AUTH_DIR / "token_google_manage.json",
            AUTH_DIR / "token_google_full.json",
            AUTH_DIR / "token_google_drive.json",
            Path("token_google.json"),
        ]
        for p in token_paths:
            p.write_text(token_json, encoding="utf-8")

        logger.info("[AUTH] ✅ Google OAuth completado — tokens guardados")
        return HTMLResponse(
            """<html><body style='font-family:monospace;background:#0a0a0a;color:#0f0;padding:40px;text-align:center'>
            <h1>✅ Autorización Google Exitosa</h1>
            <p>Nexo Soberano ahora tiene acceso a Drive y Photos.</p>
            <p>Puedes cerrar esta ventana y volver al sistema.</p>
            <script>setTimeout(()=>window.close(),3000)</script>
            </body></html>"""
        )

    except Exception as e:
        logger.error(f"[AUTH] Error en callback: {e}")
        return HTMLResponse(
            f"""<html><body style='font-family:monospace;background:#0a0a0a;color:#f55;padding:40px'>
            <h2>❌ Error en autorización</h2><pre>{e}</pre>
            </body></html>""",
            status_code=500,
        )


@router.get("/status")
def google_auth_status():
    """Verifica si hay tokens válidos guardados."""
    results = {}
    token_paths = {
        "manage_full": AUTH_DIR / "token_google_manage_full.json",
        "drive": AUTH_DIR / "token_google_drive.json",
    }
    for name, path in token_paths.items():
        if path.exists():
            try:
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_file(str(path), _SCOPES)
                results[name] = {
                    "exists": True,
                    "valid": creds.valid,
                    "expired": creds.expired,
                    "has_refresh_token": bool(creds.refresh_token),
                }
            except Exception as e:
                results[name] = {"exists": True, "valid": False, "error": str(e)}
        else:
            results[name] = {"exists": False}

    authorized = any(v.get("valid") or v.get("has_refresh_token") for v in results.values())
    return {"authorized": authorized, "tokens": results}
