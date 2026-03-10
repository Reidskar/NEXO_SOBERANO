import sys
sys.path.insert(0, '.')
import logging
from services.connectors.google_connector import authorize_drive_interactive, authorize_photos_interactive

logging.basicConfig(level=logging.INFO, format="%(message)s")

print("=====================================================")
print("  INICIANDO AUTORIZACION DE GOOGLE PARA NEXO         ")
print("=====================================================")
print("Se va a abrir tu navegador web para que inicies sesion.")
print("Por favor, acepta TODOS los permisos que solicite la app.")

try:
    print("\n1. Autorizando Google Drive...")
    res_drive = authorize_drive_interactive(require_write=True)
    if res_drive.get("ok"):
        print("✅ Google Drive Autorizado exitosamente.")
        
    print("\n2. Autorizando Google Photos...")
    res_photos = authorize_photos_interactive(include_drive_write=True)
    if res_photos.get("ok"):
        print("✅ Google Photos Autorizado exitosamente.")
        
    print("\n=====================================================")
    print("  ¡TODO LISTO! Ya puedes volver a la consola de NEXO ")
    print("=====================================================")
    
except Exception as e:
    print(f"\n❌ Error durante la autorización: {e}")

input("\nPresiona ENTER para salir...")
