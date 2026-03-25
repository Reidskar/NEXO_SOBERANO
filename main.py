import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from core.database import check_db_connection

# Logging Profesional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("NexoSystem")

class NexoSystem:
    """Sistema Orquestador Central controlado por estado"""
    def __init__(self):
        self.db = None
        self.tasks = []
        self.running = False

    async def init_services(self):
        logger.info("Inicializando servicios (DB, Drive, AI, Discord)...")
        try:
            from core.database import engine, Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Base de datos inicializada correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {e}")
            
        self.running = True

    async def start_background_tasks(self):
        logger.info("Lanzando tareas en segundo plano...")
        # Ejemplo: guardar referencia a la tarea
        self.tasks.append(asyncio.create_task(self.run_pipeline()))

    async def run_pipeline(self):
        logger.info("Pipeline background task iniciada. Esperando 10s antes del primer ciclo...")
        await asyncio.sleep(10) # Dar tiempo a que el sistema suba completamente
        try:
            from workers.pipeline import pipeline_orchestrator
            while self.running:
                await pipeline_orchestrator.run_cycle()
                await asyncio.sleep(120)  # Cada 2 minutos
        except Exception as e:
            logger.error(f"Error fatal en el loop del orquestador: {e}")

    async def shutdown(self):
        logger.info("Iniciando apagado controlado...")
        self.running = False
        
        for task in self.tasks:
            task.cancel()
            
        # Esperar a que las tareas se cancelen
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()
            
        logger.info("Cerrando conexión a base de datos...")
        try:
            from core.database import engine
            await engine.dispose()
        except Exception as e:
            logger.error(f"Error al cerrar la base de datos: {e}")

nexo = NexoSystem()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    logger.info("=== NEXO SOBERANO SYSTEM INITIALIZED ===")
    await nexo.init_services()
    await nexo.start_background_tasks()
    
    # 🛡️ Iniciar Supervisor Constante
    from services.connection_supervisor import connection_supervisor
    from services.ops_agent import ops_agent
    
    bg_task_conn = asyncio.create_task(connection_supervisor.start_monitoring())
    bg_task_ops = asyncio.create_task(ops_agent.start_operations())
    
    yield
    
    # Shutdown Events
    logger.info("=== NEXO SOBERANO SYSTEM SHUTTING DOWN ===")
    connection_supervisor.running = False
    ops_agent.running = False
    bg_task_conn.cancel()
    bg_task_ops.cancel()
    await nexo.shutdown()

app = FastAPI(title="NEXO SOBERANO Main API", lifespan=lifespan)

@app.get("/api/health")
async def health_check():
    import subprocess, os
    from datetime import datetime
    
    # Docker services
    docker_ok = False
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=nexo_", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5
        )
        running = result.stdout.strip().split('\n')
        docker_ok = len([s for s in running if s]) >= 3
    except:
        running = []

    # Leer estado de circuit breakers
    circuit_status = {}
    open_circuits = []
    try:
        import json
        from pathlib import Path
        cb_file = Path("logs/circuit_states.json")
        if cb_file.exists():
            circuit_data = json.loads(cb_file.read_text())
            open_circuits = [k for k,v in circuit_data.items()
                           if v.get("state") == "OPEN"]
            circuit_status = {k: v.get("state","CLOSED")
                            for k,v in circuit_data.items()}
    except Exception as e:
        circuit_status = {"error": str(e)}

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "NEXO SOBERANO v1.0",
        "web": "elanarcocapital.com",
        "services": {
            "api": "online",
            "docker_nexo": "ok" if docker_ok else "degraded",
            "containers_running": [s for s in running if s]
        },
        "circuit_breakers": {
            "status": "warning" if open_circuits else "ok",
            "open_circuits": open_circuits,
            "states": circuit_status
        },
        "agents": {
            "total_registered": 9,
            "registry": "docs/agent_registry.md"
        }
    }

# CORS PRO-MODE PARA EL FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir en prod a https://elanarcocapital.com
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from api.endpoints import router as endpoint_router
    from backend.routes.agente import router as agente_router
    from backend.routes.tools import router as tools_router
    app.include_router(endpoint_router, prefix="/api")
    app.include_router(agente_router, prefix="/api")
    app.include_router(tools_router)
    logger.info("Endpoints API (/api), Agente y Tools importados correctamente.")
except ImportError as e:
    logger.error(f"Falla importando endpoints de API: {e}")

try:
    from NEXO_CORE.api.drive import router as drive_router
    app.include_router(drive_router)
    logger.info("Drive API (/api/drive) registrada.")
except ImportError as e:
    logger.warning(f"Drive API no disponible: {e}")

import os as _os
if _os.path.isdir("frontend/dist"):
    from starlette.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

@app.get("/health")
async def health():
    db_status = await check_db_connection()
    return {
        "status": "ok",
        "db": "connected" if db_status else "error",
        "system": "running" if nexo.running else "stopped"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Arrancando servidor ASGI en puerto {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
