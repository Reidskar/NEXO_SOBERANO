import asyncio
import logging
from NEXO_CORE.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="sync_drive_onedrive")
def sync_drive_onedrive_task(self, params_dict: dict):
    """
    Ejecuta la sincronización pesada en el worker de Celery
    para no bloquear el hilo principal de FastAPI.
    """
    logger.info("Iniciando tarea pesada de sincronización unificada en Celery...")
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from backend.services.unified_sync_service import run_unified_sync
        
        # Ejecutamos la corrutina en un event loop nuevo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                run_unified_sync(**params_dict)
            )
            return result
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error en tarea Celery sync_unificado: {e}", exc_info=True)
        raise
