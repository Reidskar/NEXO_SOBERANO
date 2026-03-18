import logging
import uuid
import asyncio
from datetime import datetime
from core.database import SessionLocal, SystemErrorLog
from sqlalchemy.future import select
from services.auto_repair import auto_repair

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.repair_engine = auto_repair

    async def log_error(self, module: str, message: str, severity: str = "MEDIUM", event_id: str = None):
        """Registro Inmutable de Caídas y Heurística de Reparación"""
        error_id = str(uuid.uuid4())
        logger.error(f"🚨 [{severity}] [{module}] {message}")
        
        async with SessionLocal() as db:
            try:
                err_log = SystemErrorLog(
                    error_id=error_id,
                    event_id=event_id,
                    module=module,
                    error_message=message,
                    severity=severity,
                    timestamp=datetime.utcnow()
                )
                db.add(err_log)
                await db.commit()
                
                # Intervención Reparadora Asíncrona Opcional
                if severity in ["HIGH", "CRITICAL"]:
                    # No bloqueamos el pipeline central
                    asyncio.create_task(self._delegate_repair(err_log.id))
                    
                return error_id
            except Exception as e:
                logger.critical(f"FATAL: Monitor de Errores Desconectado de BD. {e}")
                return None

    async def _delegate_repair(self, db_id: int):
        async with SessionLocal() as db:
            error_record = await db.get(SystemErrorLog, db_id)
            if error_record:
                resolved = await self.repair_engine.attempt_repair(error_record)
                if resolved:
                    error_record.resolved = True
                    await db.commit()
                    logger.info(f"✅ [AUTO-REPAIR] Error {error_record.error_id} neutralizado y parcheado.")

system_monitor = SystemMonitor()
