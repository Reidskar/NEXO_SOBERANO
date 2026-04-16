import sys
sys.path.insert(0, '.')
import logging
from dotenv import load_dotenv
load_dotenv()
from services.connectors.google_connector import authorize_drive_interactive, authorize_photos_interactive

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

log.info("=====================================================")
log.info("  INICIANDO AUTORIZACION DE GOOGLE PARA NEXO         ")
log.info("=====================================================")
log.info("Se va a abrir tu navegador web para que inicies sesion.")
log.info("Por favor, acepta TODOS los permisos que solicite la app.")

try:
    log.info("\n1. Autorizando Google Drive (write)...")
    res_drive = authorize_drive_interactive(require_write=True)
    if res_drive.get("ok"):
        log.info("✅ Google Drive Autorizado exitosamente.")
    else:
        log.warning("⚠️ Google Drive — token no válido tras autorizar.")

    log.info("\n2. Autorizando Google Photos + Drive (full)...")
    res_photos = authorize_photos_interactive(include_drive_write=True)
    if res_photos.get("ok"):
        log.info("✅ Google Photos Autorizado exitosamente.")
    else:
        log.warning("⚠️ Google Photos — token no válido tras autorizar.")

    log.info("\n3. Autorizando Google Drive (read-only)...")
    res_ro = authorize_drive_interactive(require_write=False)
    if res_ro.get("ok"):
        log.info("✅ Google Drive (read-only) Autorizado exitosamente.")

    log.info("\n=====================================================")
    log.info("  ¡TODO LISTO! Ya puedes volver a la consola de NEXO ")
    log.info("=====================================================")

except Exception as e:
    log.error(f"\n❌ Error durante la autorización: {e}")

input("\nPresiona ENTER para salir...")
