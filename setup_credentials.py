"""Helper script to guide setup of Google credentials.

Run this first if you don't have credenciales_google.json yet.
"""
import os
import json

TEMPLATE = {
    "type": "oauth2.0",
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost:8080/"],
    "scopes": [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/photoslibrary.readonly"
    ]
}

def setup_credentials():
    """Guide user through getting Google OAuth credentials."""
    log.info("\n" + "="*70)
    log.info("🔑 SETUP DE CREDENCIALES GOOGLE - NEXO SOBERANO")
    log.info("="*70 + "\n")
    
    print("""
Para conectar NEXO a tu Google Drive y Google Photos, necesitas:

1. Ve a: https://console.cloud.google.com/
2. Crea un NUEVO PROYECTO (ej: "Nexo Soberano")
3. Habilita estas APIs:
   - Google Drive API v3
   - Google Photos Library API
4. Ve a "APIs y Servicios > Credenciales"
5. Crea "Credenciales > ID de cliente de OAuth > Escritorio (Desktop)"
6. Descarga el JSON
7. Renómbralo a: credenciales_google.json
8. Colócalo EN ESTA CARPETA (NEXO_SOBERANO)

Las instrucciones completas en:
https://developers.google.com/drive/api/quickstart/python

Una vez lo tengas, vuelve aquí y ejecuta:
  python core/orquestador.py

¡El navegador se abrirá automáticamente para autorizar!
    """)
    
    # Create a template for reference
    template_path = "credenciales_google_TEMPLATE.json"
    if not os.path.exists(template_path):
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(TEMPLATE, f, indent=2)
        log.info(f"\n✅ Se creó un template en: {template_path}")
        log.info("   (Esto es SOLO una referencia; NO uses este archivo directamente)")
    
    log.info("\n" + "="*70)
    log.info("Una vez descargues el archivo real de Google Cloud, colócalo aquí:")
    log.info(f"  {os.path.abspath('credenciales_google.json')}")
    log.info("="*70 + "\n")

if __name__ == "__main__":
    setup_credentials()
