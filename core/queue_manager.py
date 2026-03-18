import asyncio
import logging

logger = logging.getLogger(__name__)

class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_task = None

    async def enqueue(self, task_func, *args, **kwargs):
        event_id = kwargs.get("event_id", "NO_ID")
        logger.info(f"📥 [QUEUE] Encolando tarea. Event ID: {event_id}")
        await self.queue.put((task_func, args, kwargs))
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        logger.info("👷 [WORKER] Iniciando consumidor de cola asíncrona.")
        while not self.queue.empty():
            task_func, args, kwargs = await self.queue.get()
            event_id = kwargs.get("event_id", "NO_ID")
            try:
                logger.info(f"⚙️ [WORKER] Procesando Tarea (Event ID: {event_id})")
                await task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ [WORKER] Fallo en la tarea (Event ID: {event_id}): {e}")
            finally:
                self.queue.task_done()
        logger.info("💤 [WORKER] Cola agotada. Ahorrando recursos.")

system_queue = TaskQueue()
