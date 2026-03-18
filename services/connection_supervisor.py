import logging
import asyncio
import time
from datetime import datetime
import httpx

from core.config import settings
from services.auto_repair import auto_repair

logger = logging.getLogger(__name__)

class ConnectionSupervisor:
    def __init__(self):
        self.system_status = {
            "api": {"status": "ok", "latency": 0.0, "last_checked": None, "failures": 0},
            "supabase": {"status": "ok", "latency": 0.0, "last_checked": None, "failures": 0},
            "ai": {"status": "ok", "latency": 0.0, "last_checked": None, "failures": 0},
            "discord": {"status": "ok", "latency": 0.0, "last_checked": None, "failures": 0},
            "drive": {"status": "ok", "latency": 0.0, "last_checked": None, "failures": 0}
        }
        self.running = False
        self.port = 8000

    async def start_monitoring(self):
        if self.running: return
        self.running = True
        logger.info("🛡️ [SUPERVISOR] Loop de monitoreo de conexiones de nivel Producción iniciado.")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            while self.running:
                await self._run_health_checks(client)
                await asyncio.sleep(60)

    async def _run_health_checks(self, client: httpx.AsyncClient):
        # API PING
        await self._check_service("api", self._ping_api(client))
        # SUPABASE PING
        await self._check_service("supabase", self._ping_supabase(client))
        # AI PING
        await self._check_service("ai", self._ping_ai(client))
        # DISCORD PING
        await self._check_service("discord", self._ping_discord(client))
        
        # Opcional Drive ping 
        # await self._check_service("drive", self._ping_drive(client))

    async def _check_service(self, service_name: str, coro_check):
        start = time.time()
        try:
            success, message = await coro_check
            latency = (time.time() - start) * 1000
            
            if success:
                self.system_status[service_name]["status"] = "ok"
                self.system_status[service_name]["failures"] = 0
            else:
                self._record_failure(service_name, message)
                
            self.system_status[service_name]["latency"] = round(latency, 2)
            self.system_status[service_name]["last_checked"] = datetime.utcnow().isoformat()
            
        except httpx.TimeoutException:
            self._record_failure(service_name, "Timeout 5s superado")
        except Exception as e:
            self._record_failure(service_name, str(e))

    def _record_failure(self, service_name: str, message: str):
        self.system_status[service_name]["failures"] += 1
        failures = self.system_status[service_name]["failures"]
        
        if failures >= 3:
            self.system_status[service_name]["status"] = "critical"
            logger.critical(f"❌ [CRÍTICO] Servicio {service_name.upper()} caído ({failures} fails). Razón: {message}")
            asyncio.create_task(auto_repair.handle_connection_issue(service_name, "critical"))
        elif failures == 2:
            self.system_status[service_name]["status"] = "degraded"
            logger.warning(f"⚠️ [DEGRADADO] Servicio {service_name.upper()} inestable ({failures} fails). Razón: {message}")
            asyncio.create_task(auto_repair.handle_connection_issue(service_name, "degraded"))

    # Métodos de Ping Reales
    async def _ping_api(self, client: httpx.AsyncClient):
        try:
            res = await client.get(f"http://127.0.0.1:{self.port}/health")
            return res.status_code == 200, "OK" if res.status_code == 200 else f"HTTP {res.status_code}"
        except httpx.RequestError as e:
            return False, str(e)

    async def _ping_supabase(self, client: httpx.AsyncClient):
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            return False, "Credenciales no configuradas"
        url = f"{settings.SUPABASE_URL}/rest/v1/"
        headers = {"apikey": settings.SUPABASE_KEY}
        res = await client.get(url, headers=headers)
        return res.status_code in [200, 400], f"HTTP {res.status_code}" # /rest/v1 sin endopoint da 400 (Bad Request), lo cual indica que la app está viva

    async def _ping_ai(self, client: httpx.AsyncClient):
        if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_KEY:
            return False, "Credenciales AI no configuradas"
        url = f"{settings.AZURE_OPENAI_ENDPOINT}openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT}?api-version=2024-02-15-preview"
        headers = {"api-key": settings.AZURE_OPENAI_KEY}
        # HEAD no está siempre soportado en Azure o OpenAI, hacemos un GET crudo al Endpoint (devolverá 404 o 401 si no auth, pero confirmaremos alcance)
        res = await client.get(url, headers=headers)
        return res.status_code in [200, 401, 404, 405], f"HTTP {res.status_code} Reachable"

    async def _ping_discord(self, client: httpx.AsyncClient):
        if not settings.DISCORD_WEBHOOK_URL:
            return False, "Discord Webhook no configurado"
        res = await client.get(settings.DISCORD_WEBHOOK_URL)
        return res.status_code in [200, 401], f"HTTP {res.status_code}" # Webhooks suelen dar 200 al GET si existe

connection_supervisor = ConnectionSupervisor()
