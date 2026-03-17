import os
import json
import logging
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- CONFIGURATION ---
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "autorizaciones.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("nexo.auth")

# Paths based on google_connector.py logic
AUTH_DIR = Path("backend/auth")
AUTH_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_SECRETS_FILE = AUTH_DIR / "credenciales_google.json"

# Combined Scopes for Drive and Photos
SCOPES = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/photoslibrary',
    'https://www.googleapis.com/auth/photoslibrary.readonly',
]

TOKEN_FILES = {
    "manage_full": AUTH_DIR / "token_google_manage_full.json",
    "manage": AUTH_DIR / "token_google_manage.json",
    "full": AUTH_DIR / "token_google_full.json",
    "drive": AUTH_DIR / "token_google_drive.json",
}

def run_authorization():
    """Ejecuta el flujo interactivo de OAuth2 para Google Drive y Photos."""
    log.info("\n" + "="*60)
    log.info("NEXO SOBERANO — INICIADOR DE AUTORIZACIONES GOOGLE")
    log.info("="*60 + "\n")

    if not CLIENT_SECRETS_FILE.exists():
        # Intentar buscar en localizaciones comunes
        common_paths = [
            Path("credenciales_google.json"),
            Path.home() / "Desktop" / "credenciales_google.json",
            Path.home() / "Downloads" / "credenciales_google.json"
        ]
        found = False
        for p in common_paths:
            if p.exists():
                import shutil
                shutil.copy(p, CLIENT_SECRETS_FILE)
                logger.info(f"Copiando credenciales desde {p} a {CLIENT_SECRETS_FILE}")
                found = True
                break
        
        if not found:
            logger.error(f"FATAL: No se encontró '{CLIENT_SECRETS_FILE}'.")
            log.info(f"\n[!] ERROR: Coloca el archivo 'credenciales_google.json' de Google Cloud Console")
            log.info(f"    en la carpeta '{AUTH_DIR}' y vuelve a ejecutar este script.")
            return

    try:
        log.info("[*] Iniciando servidor local para autorización...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

        if creds and creds.valid:
            # Guardamos el token en todas las variantes para asegurar compatibilidad con google_connector.py
            token_json = creds.to_json()
            for name, path in TOKEN_FILES.items():
                path.write_text(token_json, encoding="utf-8")
                logger.info(f"Token guardado: {path}")

            log.info("\n" + "✓"*60)
            log.info("¡AUTORIZACIÓN EXITOSA!")
            log.info(f"Tokens generados en: {AUTH_DIR}")
            log.info("Nexo Soberano ahora tiene acceso a Drive y Photos.")
            log.info("✓"*60 + "\n")
        else:
            logger.error("No se recibieron credenciales válidas.")

    except Exception as e:
        logger.error(f"Error durante la autorización: {e}")
        log.info(f"\n[!] ERROR CRÍTICO: {e}")

if __name__ == "__main__":
    run_authorization()
