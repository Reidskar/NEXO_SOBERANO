import sys
import os

# Ensure the root directory is in the absolute path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.auth_manager import get_google_credentials, get_microsoft_token

def main():
    log.info("="*50)
    log.info("RENOVACIÓN DE CREDENCIALES OAUTH")
    log.info("="*50)
    
    log.info("\n--- Renovando Google Drive & Photos ---")
    try:
        g_creds = get_google_credentials()
        if g_creds and g_creds.valid:
            log.info("[OK] Credenciales de Google válidas y guardadas.")
        else:
            log.info("[X] No se pudo obtener credenciales de Google.")
    except Exception as e:
        log.info(f"[ERROR] Fallo en el flujo de Google: {e}")

    log.info("\n--- Renovando Microsoft OneDrive ---")
    try:
        m_creds = get_microsoft_token()
        if m_creds and "access_token" in m_creds:
            log.info("[OK] Credenciales de Microsoft válidas y guardadas.")
        else:
            log.info("[X] No se pudo obtener credenciales de Microsoft.")
    except Exception as e:
        log.info(f"[ERROR] Fallo en el flujo de Microsoft: {e}")

    log.info("\nProceso finalizado. Ya puedes cerrar esta ventana.")

if __name__ == "__main__":
    main()
