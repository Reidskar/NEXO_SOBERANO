import asyncio
import logging
from datetime import datetime, timedelta
from services.drive_service import drive_service
from services.document_processor import document_processor

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.folder_id = "INSERT_FOLDER_ID_HERE" 
        self.last_modified_time = datetime.utcnow() - timedelta(days=1)
        self.lock = asyncio.Lock()
        # Semáforo de concurrencia para proteger el uso de CPU si se procesara algo aquí
        self.semaphore = asyncio.Semaphore(5)
        
    async def run_cycle(self):
        """Ciclo protegido: Chequea Drive y delega tareas a la BD (Local Worker las consumirá)."""
        async with self.lock:
            logger.info("--- 🔄 INICIANDO CLOUD PIPELINE: Spawning Tareas ---")
            try:
                files = await drive_service.get_changes_since(self.folder_id, self.last_modified_time)
                
                if not files:
                    logger.info("No hay archivos nuevos detectados.")
                    return

                tasks_spawned = 0
                max_time_seen = self.last_modified_time
                
                for file_meta in files:
                    file_time_str = file_meta.get('modifiedTime')
                    if file_time_str:
                        file_time = datetime.fromisoformat(file_time_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        if file_time > max_time_seen:
                            max_time_seen = file_time
                    
                    # Sistema de Prioridad
                    name_lower = file_meta.get('name', '').lower()
                    if "military" in name_lower:
                        priority = 1
                    elif "economic" in name_lower or "budget" in name_lower:
                        priority = 2
                    else:
                        priority = 3
                        
                    logger.info(f"📝 Creando tarea (Prioridad {priority}) para: {file_meta.get('name')}")
                    
                    async with self.semaphore:
                        # Creamos el Documento en status="pending", el Local Worker hará la descarga y el OCR
                        success = await document_processor.create_pending_task(file_meta, priority)
                        if success:
                            tasks_spawned += 1
                        
                if max_time_seen > self.last_modified_time:
                    self.last_modified_time = max_time_seen
                    
                logger.info(f"✅ Ciclo Completado: {tasks_spawned} tareas encoladas para el Local Worker.")
                
            except Exception as e:
                logger.error(f"❌ Error fatal en ciclo de Pipeline Cloud: {e}")

pipeline_orchestrator = PipelineOrchestrator()
