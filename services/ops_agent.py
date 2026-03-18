import asyncio
import logging
import time
from datetime import datetime
import httpx

from services.connection_supervisor import connection_supervisor
from services.auto_repair import auto_repair
from core.database import SessionLocal, Document, SystemErrorLog
from sqlalchemy.future import select
from sqlalchemy import func
from core.system_config import get_config, update_config

logger = logging.getLogger(__name__)

class OpsAgent:
    def __init__(self):
        self.running = False
        self.last_mutation_time = 0
        self.cooldown_seconds = 300 # 5 min cooldown
        self.state = {
            "services": {},
            "domains": {},
            "queue_load": 0,
            "error_rate": 0.0,
            "ai_usage": 0,
            "risk_level": "LOW",
            "last_decisions": []
        }

    async def start_operations(self):
        if self.running: return
        self.running = True
        logger.info("🧠 [OPS AGENT] AIOps Controller activado (Loop Inteligente de 60s).")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            while self.running:
                await self._run_cycle(client)
                await asyncio.sleep(60)

    async def _run_cycle(self, client: httpx.AsyncClient):
        try:
            # 1. Aggregate State
            await self._aggregate_state(client)
            
            # 2. Decision Engine
            if time.time() - self.last_mutation_time > self.cooldown_seconds:
                await self._evaluate_and_act()
                
        except Exception as e:
            logger.error(f"❌ [OPS AGENT] Fallo crítico simulado de controlador: {e}")

    async def _aggregate_state(self, client: httpx.AsyncClient):
        # Supervisión Híbrida de Servicios Pasivos
        self.state["services"] = connection_supervisor.system_status
        
        # Domain Monitoring Remoto Real
        domains = ["https://elanarcocapital.com", "http://127.0.0.1:8000/health"]
        for url in domains:
            try:
                start = time.time()
                res = await client.get(url)
                lat = (time.time() - start) * 1000
                self.state["domains"][url] = {"status": res.status_code, "latency": round(lat, 2)}
            except Exception as e:
                self.state["domains"][url] = {"status": "FAIL", "error": str(e)}

        # DB Metrics: Queue Load + Error Rate
        async with SessionLocal() as db:
            # Queue Load
            stmt_queue = select(func.count()).where(Document.status == "pending")
            q_res = await db.execute(stmt_queue)
            self.state["queue_load"] = q_res.scalar_one_or_none() or 0
            
            # Error Rate (últimos errores / total docs recientes) pseudo-calculado
            stmt_errors = select(func.count()).where(SystemErrorLog.resolved == False)
            e_res = await db.execute(stmt_errors)
            e_count = e_res.scalar_one_or_none() or 0
            
            # Si hay más de 5 errores sin resolver, el error rate sube agresivamente
            self.state["error_rate"] = e_count / 10.0 if e_count > 0 else 0.0

    async def _evaluate_and_act(self):
        actions_taken = []
        config = get_config()
        mutation = False

        # RULE 1: Queue Backpressure
        if self.state["queue_load"] > 15: # Critical threshold
            logger.warning("🧠 [OPS AGENT] Queue Load CRITICAL. Reduciendo Ingestion Frequency.")
            config["pipeline"]["interval_seconds"] = 300 # 5 minutes
            actions_taken.append("THROTTLE_PIPELINE")
            mutation = True
            
        # RULE 2: AI Latency Cost Control
        ai_model = self.state["services"].get("ai", {})
        if ai_model.get("latency", 0) > 3000: # 3 segundos
            logger.warning("🧠 [OPS AGENT] IA Lenta. Recortando Max Tokens para ahorrar latencia/costo.")
            config["ai"]["max_tokens"] = 500
            actions_taken.append("REDUCE_TOKENS")
            mutation = True

        # RULE 3: Error Cascade Safemode
        if self.state["error_rate"] > 0.5:
            logger.error("🧠 [OPS AGENT] Error Rate Alto. Activando SAFE MODE.")
            self.state["risk_level"] = "HIGH"
            actions_taken.append("ACTIVATE_SAFE_MODE")
            
        # RULE 4: Domain Ping Checks
        domain_prod = self.state["domains"].get("https://elanarcocapital.com", {})
        if domain_prod.get("status") == "FAIL":
            logger.critical("🧠 [OPS AGENT] DOMINIO CAÍDO. Disparando Alerta Discord Inmediata.")
            actions_taken.append("DOMAIN_DOWN_ALERT")

        # RULE 5: Supabase / Connectivity Down
        supa_status = self.state["services"].get("supabase", {}).get("status")
        if supa_status == "critical":
            logger.error("🧠 [OPS AGENT] Supabase fuera de línea. Pausando uploads.")
            actions_taken.append("PAUSE_UPLOADS")

        if mutation:
            update_config(config)
            self.last_mutation_time = time.time()
            self.state["last_decisions"] = actions_taken
            logger.info(f"🧠 [OPS AGENT] Mutación de Sistema en Caliente Ejecutada: {actions_taken}")
            
ops_agent = OpsAgent()
