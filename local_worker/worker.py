import asyncio
import httpx
import logging
import os

# Configuración de Logging para el Supervisor Local
logging.basicConfig(level=logging.INFO, format="%(asctime)s - WORKER (LOCAL) - %(message)s")
logger = logging.getLogger(__name__)

# En producción, esto apuntará a HTTPS del Railway
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

class LocalWorker:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0) # Timeout alto por si baja archivos pesados

    async def poll_tasks(self):
        logger.info(f"🔄 Iniciando Polling hacia Frontend Cloud [{API_BASE_URL}/tasks/pending]...")
        while True:
            try:
                response = await self.client.get(f"{API_BASE_URL}/tasks/pending")
                if response.status_code == 200:
                    tasks = response.json()
                    
                    if not tasks:
                        # logger.debug("0 tareas en cola.")
                        pass
                    else:
                        logger.info(f"⚡ {len(tasks)} TAREAS PESADAS recibidas desde Cloud.")
                        for task in tasks:
                            await self.process_task(task)
                else:
                    logger.warning(f"Respuesta inesperada del servidor: Code {response.status_code}")
            except httpx.ConnectError:
                logger.error("❌ No se pudo conectar al Backend Cloud. Reintentando...")
            except Exception as e:
                logger.error(f"Error desconocido en pooling loop: {e}")
                
            await asyncio.sleep(15) # Poll cada 15 segundos

    async def process_task(self, task: dict):
        logger.info(f"🚀 Procesando tarea localmente: {task['title']} (Prioridad: {task.get('priority')})")
        try:
            # 1. Simular descarga del archivo desde Drive (El ID o URL viene en task['drive_url'])
            # NOTA: Aquí insertar el Google Drive SDK para bajar el Content y pasarlo por PDF o Tesseract
            await asyncio.sleep(1) 
            logger.info("  -> Archivo descargado en Memoria RAM Local.")
            
            # 2. Extracción de Texto con PyMuPDF / Tesseract (OCR) de forma local.
            # Aquí ocurre el consumo intensivo de CPU sin afectar a Railway.
            logger.info("  -> Ejecutando PyMuPDF / Motor OCR localmente (CPU Heavy Task)...")
            await asyncio.sleep(2) # Simular parsing de 30 páginas
            extracted_text = f"Texto simulado procesado por CPU LOCAL para el documento {task['title']}..."
            
            # 3. Postear los Resultados Limpios devuelta al Motor en la Nube
            payload = {
                "document_id": task["id"],
                "extracted_text": extracted_text,
                "error": None
            }
            logger.info("  -> Subiendo resultados de texto extraído a la Nube (para inferencia Azure OpenAI)...")
            
            res = await self.client.post(f"{API_BASE_URL}/tasks/complete", json=payload)
            if res.status_code == 200:
                logger.info(f"✅ Tarea {task['id']} enviada a Cloud exitosamente. Cloud tomará el control del análisis.")
            else:
                logger.error(f"Fallo enviando tarea {task['id']} a la Nube (Code {res.status_code}: {res.text})")
                
        except Exception as e:
            payload = {"document_id": task["id"], "extracted_text": "", "error": f"Local Worker Crash: {str(e)}"}
            await self.client.post(f"{API_BASE_URL}/tasks/complete", json=payload)
            logger.error(f"Error procesando documento localmente: {e}")

if __name__ == "__main__":
    print(r"""
     _   _ _______   ______  
    | \ | |  ___\ \ / / __ \ 
    |  \| | |__  \ V /|  | | 
    | . ` |  __| > < |  | | 
    | |\  | |___/ . \|  |_| |
    \_| \_/\____/_/ \_\____/  LOCAL_WORKER v1.0
    """)
    logger.info("🚀 Arrancando Worker de Computación Descentralizada...")
    worker = LocalWorker()
    asyncio.run(worker.poll_tasks())
