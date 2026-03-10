import os
import json
import pickle
import logging
import time
from pathlib import Path
from typing import Optional

# Configure logging
log = logging.getLogger(__name__)

# Google OAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.credentials import Credentials as BaseCredentials

# Microsoft OAuth (MSAL)
import msal

# Constants
GOOGLE_CREDENTIALS_FILE = Path("credenciales_google.json")
GOOGLE_TOKEN_FILE = Path("token_google.json")
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly"
]

MICROSOFT_CREDENTIALS_FILE = Path("credenciales_microsoft.json")
MICROSOFT_TOKEN_FILE = Path("token_microsoft.json")
MICROSOFT_SCOPES = ["User.Read", "Files.Read.All"]


def get_google_credentials() -> Optional[BaseCredentials]:
    """Return valid Google credentials, refreshing or performing OAuth if necessary.
    
    If credentials file doesn't exist, returns None (demo mode).
    """
    creds: Optional[BaseCredentials] = None
    
    if not GOOGLE_CREDENTIALS_FILE.exists():
        log.info(f"⚠️ [{GOOGLE_CREDENTIALS_FILE}] no encontrado.")
        log.info("   Ejecuta: python setup_credentials.py")
        return None
    
    if GOOGLE_TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), GOOGLE_SCOPES)
        except Exception as e:
            log.info(f"❌ Error cargando token previo: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                log.info("✅ Token de Google refrescado.")
            except Exception as e:
                log.info(f"🔁 fallo al refrescar credenciales de Google: {e}")
                creds = None
        
        if not creds or not creds.valid:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(GOOGLE_CREDENTIALS_FILE), GOOGLE_SCOPES
                )
                log.info("🌐 Abriendo navegador para autorizar Google...")
                creds = flow.run_local_server(port=0)
                log.info("✅ Autorización exitosa.")
            except Exception as e:
                log.info(f"❌ Fallo en autorización OAuth: {e}")
                return None
        
        # Save the credentials for the next run
        try:
            with open(GOOGLE_TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
            log.info(f"💾 Token guardado en {GOOGLE_TOKEN_FILE}")
        except Exception as e:
            log.info(f"❌ Error guardando token: {e}")
    
    return creds


class MicrosoftAuth:
    def __init__(self):
        if not MICROSOFT_CREDENTIALS_FILE.exists():
            raise FileNotFoundError(f"No se encuentra {MICROSOFT_CREDENTIALS_FILE}")

        with open(MICROSOFT_CREDENTIALS_FILE, "r") as f:
            data = json.load(f)
        # Expecting client_id, client_secret, tenant_id
        self.client_id = data.get("client_id")
        self.client_secret = data.get("client_secret")
        self.tenant_id = data.get("tenant_id")
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret,
        )

    def get_token(self) -> dict:
        """Acquire or refresh a Microsoft access token."""
        # Try to load from file
        if MICROSOFT_TOKEN_FILE.exists():
            with open(MICROSOFT_TOKEN_FILE, "r") as f:
                token_data = json.load(f)
            # check expiration
            if token_data.get("expires_at") and token_data["expires_at"] > time.time():
                return token_data
        # Acquire new
        result = self.app.acquire_token_for_client(scopes=MICROSOFT_SCOPES)
        if result and "access_token" in result:
            # persist
            with open(MICROSOFT_TOKEN_FILE, "w") as f:
                json.dump(result, f)
            return result
        else:
            raise RuntimeError(f"failed to acquire Microsoft token: {result}")


def get_microsoft_token() -> dict:
    auth = MicrosoftAuth()
    return auth.get_token()
