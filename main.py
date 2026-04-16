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

    # 🌐 Iniciar OSINT Engine (sweep cada 15 min en background)
    try:
        from backend.services.osint_feeds import osint_engine
        osint_engine.start_background_loop()
        logger.info("OSINT Engine background loop iniciado (sweep cada 15 min).")
    except Exception as e:
        logger.warning(f"OSINT Engine no pudo arrancar: {e}")

    # 🤖 Warm-up Ollama (precargar modelo en VRAM para evitar cold-start)
    try:
        import asyncio as _aio, threading as _thr
        def _warmup():
            import asyncio
            from NEXO_CORE.services.ollama_service import ollama_service
            async def _ping():
                ok = await ollama_service.is_available()
                if ok:
                    await ollama_service.consultar("ping", modelo="general", temperature=0)
                    logger.info("Ollama warm-up completado — qwen3.5 en VRAM.")
            asyncio.run(_ping())
        _thr.Thread(target=_warmup, daemon=True, name="ollama-warmup").start()
    except Exception as e:
        logger.warning(f"Ollama warm-up falló: {e}")

    # 🏭 Iniciar Agent Factory (agentes autónomos con schedule)
    bg_task_agents = None
    try:
        from backend.services.agent_factory import agent_factory
        bg_task_agents = asyncio.create_task(agent_factory.start_loop())
        logger.info("Agent Factory iniciado — agentes autónomos activos.")
    except Exception as e:
        logger.warning(f"Agent Factory no pudo arrancar: {e}")

    yield

    # Shutdown Events
    logger.info("=== NEXO SOBERANO SYSTEM SHUTTING DOWN ===")
    connection_supervisor.running = False
    ops_agent.running = False
    if bg_task_agents:
        agent_factory.running = False
        bg_task_agents.cancel()
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
    from NEXO_CORE.api.webhooks import router as core_webhook_router
    app.include_router(endpoint_router, prefix="/api")
    app.include_router(agente_router, prefix="/api")
    app.include_router(tools_router)
    app.include_router(core_webhook_router)
    logger.info("Endpoints API (/api), Agente, Tools y Webhooks importados correctamente.")
except ImportError as e:
    logger.error(f"Falla importando endpoints de API: {e}")

try:
    from NEXO_CORE.api.drive import router as drive_router
    app.include_router(drive_router)
    logger.info("Drive API (/api/drive) registrada.")
except ImportError as e:
    logger.warning(f"Drive API no disponible: {e}")

try:
    from NEXO_CORE.api.social import router as social_router
    app.include_router(social_router)
    logger.info("Social API (/api/social) registrada.")
except ImportError as e:
    logger.warning(f"Social API no disponible: {e}")

try:
    from NEXO_CORE.api.files import router as files_api_router
    app.include_router(files_api_router)
    logger.info("Files API (/api/files) registrada.")
except ImportError as e:
    logger.warning(f"Files API no disponible: {e}")

try:
    from backend.routes.sesiones import router as sesiones_router
    app.include_router(sesiones_router)
    logger.info("Sesiones API (/api/sesiones) registrada.")
except ImportError as e:
    logger.warning(f"Sesiones API no disponible: {e}")

try:
    from backend.routes.video import router as video_router
    app.include_router(video_router, prefix="/api")
    logger.info("Video API (/api/agente/analizar-video, /api/agente/exportar-docx) registrada.")
except ImportError as e:
    logger.warning(f"Video API no disponible: {e}")

try:
    from backend.routes.video_studio import router as video_studio_router
    app.include_router(video_studio_router, prefix="/api")
    logger.info("Video Studio (/api/video/*) registrado.")
except ImportError as e:
    logger.warning(f"Video Studio no disponible: {e}")

try:
    from backend.routes.device import router as device_router
    app.include_router(device_router)
    logger.info("Device Control API (/api/device/*) registrada.")
except ImportError as e:
    logger.warning(f"Device Control no disponible: {e}")

try:
    from backend.routes.content import router as content_router
    app.include_router(content_router)
    logger.info("Content Pipeline + Research Guide (/api/content/*, /api/research/*) registrados.")
except ImportError as e:
    logger.warning(f"Content Pipeline no disponible: {e}")

try:
    from backend.routes.osint import router as osint_router
    app.include_router(osint_router)
    logger.info("OSINT Engine (/api/osint/*) registrado.")
except ImportError as e:
    logger.warning(f"OSINT Engine no disponible: {e}")

try:
    from backend.routes.topics import router as topics_router
    app.include_router(topics_router)
    logger.info("Topic Tracker (/api/topics/*) registrado.")
except ImportError as e:
    logger.warning(f"Topic Tracker no disponible: {e}")

try:
    from backend.routes.cognitive import router as cognitive_router
    app.include_router(cognitive_router)
    logger.info("Motor Cognitivo (/api/cognitive/*) registrado.")
except ImportError as e:
    logger.warning(f"Motor Cognitivo no disponible: {e}")

try:
    from backend.routes.mcp import router as mcp_router
    app.include_router(mcp_router)
    logger.info("MCP Gateway + Agent Factory (/api/mcp/*, /api/agents/*) registrados.")
except ImportError as e:
    logger.warning(f"MCP/Agents no disponible: {e}")

try:
    from NEXO_CORE.api.hunter import router as hunter_router
    from fastapi.responses import FileResponse
    import os as _os_hunter
    app.include_router(hunter_router)

    @app.get("/hunter")
    async def hunter_dashboard():
        path = _os_hunter.path.join(_os_hunter.path.dirname(__file__), "frontend_public", "hunter_dashboard.html")
        return FileResponse(path)

    logger.info("NEXO HUNTER (/api/hunter/*, /hunter) registrado.")
except Exception as e:
    logger.warning(f"NEXO HUNTER no disponible: {e}")

@app.get("/health")
async def health():
    db_status = await check_db_connection()
    return {
        "status": "ok",
        "db": "connected" if db_status else "error",
        "system": "running" if nexo.running else "stopped"
    }

# StaticFiles SIEMPRE al final — si se monta antes captura /health y /api/*
import os as _os
if _os.path.isdir("frontend/dist"):
    from starlette.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Arrancando servidor ASGI en puerto {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
