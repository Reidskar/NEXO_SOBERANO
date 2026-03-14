import sys
import os

# Ensure the root directory is in the absolute path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.auth_manager import get_google_credentials, get_microsoft_token

def main():
    print("="*50)
    print("RENOVACIÓN DE CREDENCIALES OAUTH")
    print("="*50)
    
    print("\n--- Renovando Google Drive & Photos ---")
    try:
        g_creds = get_google_credentials()
        if g_creds and g_creds.valid:
            print("[OK] Credenciales de Google válidas y guardadas.")
        else:
            print("[X] No se pudo obtener credenciales de Google.")
    except Exception as e:
        print(f"[ERROR] Fallo en el flujo de Google: {e}")

    print("\n--- Renovando Microsoft OneDrive ---")
    try:
        m_creds = get_microsoft_token()
        if m_creds and "access_token" in m_creds:
            print("[OK] Credenciales de Microsoft válidas y guardadas.")
        else:
            print("[X] No se pudo obtener credenciales de Microsoft.")
    except Exception as e:
        print(f"[ERROR] Fallo en el flujo de Microsoft: {e}")

    print("\nProceso finalizado. Ya puedes cerrar esta ventana.")

if __name__ == "__main__":
    main()
