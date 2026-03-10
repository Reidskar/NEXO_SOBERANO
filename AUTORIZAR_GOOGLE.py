import sys
sys.path.insert(0, '.')
import logging
from services.connectors.google_connector import authorize_drive_interactive, authorize_photos_interactive

logging.basicConfig(level=logging.INFO, format="%(message)s")

log.info("=====================================================")
log.info("  INICIANDO AUTORIZACION DE GOOGLE PARA NEXO         ")
log.info("=====================================================")
log.info("Se va a abrir tu navegador web para que inicies sesion.")
log.info("Por favor, acepta TODOS los permisos que solicite la app.")

try:
    log.info("\n1. Autorizando Google Drive...")
    res_drive = authorize_drive_interactive(require_write=True)
    if res_drive.get("ok"):
        log.info("✅ Google Drive Autorizado exitosamente.")
        
    log.info("\n2. Autorizando Google Photos...")
    res_photos = authorize_photos_interactive(include_drive_write=True)
    if res_photos.get("ok"):
        log.info("✅ Google Photos Autorizado exitosamente.")
        
    log.info("\n=====================================================")
    log.info("  ¡TODO LISTO! Ya puedes volver a la consola de NEXO ")
    log.info("=====================================================")
    
except Exception as e:
    log.info(f"\n❌ Error durante la autorización: {e}")

input("\nPresiona ENTER para salir...")
