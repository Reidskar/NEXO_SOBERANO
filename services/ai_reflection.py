import json
import logging
from core.config import settings
from core.system_config import get_config, update_config
from core.learning_log import get_recent_changes, log_change, get_recent_epochs
try:
    from openai import AsyncAzureOpenAI
except ImportError:
    AsyncAzureOpenAI = None
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Control Anti-Loop (Cooldown State)
last_deploy_time = None

class AIReflectionEngine:
    def __init__(self):
        self.client = None
        if AsyncAzureOpenAI and settings.AZURE_OPENAI_KEY:
            self.client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_KEY,
                api_version="2023-12-01-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )

    async def evaluate_system_performance(self):
        """Analiza telemetría histórica y decide mutar autónomamente el sistema."""
        logger.info("🧠 [REFLECTION ENGINE] Iniciando Auto-Evaluación del Rendimiento Sistémico...")
        logs = get_recent_changes()
        
        if not logs or len(logs) < 1:
            logger.info("No hay suficientes logs vectoriales para iniciar una época de reflexión.")
            return

        latest_epoch = logs[-1]
        metrics = latest_epoch.get("metrics", [])
        
        # Necesitamos algo de data para reflexionar responsablemente
        if len(metrics) < 1:
            logger.info("Esperando acumulación de telemetría orgánica para ejecutar reflexión...")
            return

        current_config = get_config()

        prompt = (
            "You are the NEXO SOBERANO AI Reflection Engine. You evaluate if the current intelligence system configuration is optimal based on historical execution metrics.\n"
        try:
            if not self.client:
                logger.warning("No Azure OpenAI disponible. Fallback Reflection Engine.")
                return

            # Recuperación de Memoria Sensitiva + Analíticas
            docs = get_recent_changes(limit=3)
            # Todo: Aquí se inyectarían métricas del AnalyticsService en Memoria para Growth Optimization
            
            prompt = (
                "You are the Nexo Soberano Evolutionary Architect. "
                "Analyze recent error logs, user engagement patterns, and config changes. "
                "PROPOSE AT MOST ONE (1) CONFIG MUTATION if necessary to improve conversion, SEO reach, or stability. "
                "Current Config:\n"
                f"{json.dumps(current_config, indent=2)}\n\n"
                "Recent Memory:\n"
                f"{json.dumps(docs, indent=2)}\n\n"
                "Return ONLY a strictly valid JSON with no markdown:\n"
                "{\n"
                "  \"mutate\": true/false,\n"
                "  \"reason\": \"explanation\",\n"
                "  \"proposed_config\": { ...full modified config... }\n"
                "}"
            )

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if result.get("mutate") == False:
                logger.info("ℹ️ Mutación rechazada por la Heurística IA.")
                return

            if "proposed_config" in result:
                new_config = result["proposed_config"]
                reason = result.get("reason", "Evolución autónoma de Growth / Stability")
                
                # 🛡️ RESTRICTION SHIELD: MAXIMUM 1 MUTACIÓN & 15m Cooldown Centralizado
                global last_deploy_time
                if last_deploy_time and (datetime.utcnow() - last_deploy_time).seconds < 900:
                    logger.warning("🛡️ [AI REFLECTION] Bloqueado. Máximo 1 mutación cada 15m para proteger estabilidad.")
                    return

                logger.warning(f"⚡ [REFLECTION ENGINE] INICIANDO MUTACIÓN EVOLUTIVA AUTÓNOMA.")
                log_change("ai_reflection_adjustment", current_config, new_config, reason)
                update_config(new_config)
                
                # ⬅️ INYECCIÓN PARA RECONSTRUIR VERCEL Front-end automáticamente
                self._trigger_vercel_redeploy()

        except Exception as e:
            logger.error(f"Error crítico durante la heurística de reflexión: {e}")

    def _trigger_vercel_redeploy(self):
        global last_deploy_time
        if last_deploy_time and (datetime.utcnow() - last_deploy_time).seconds < 900:
            logger.warning("⏳ [VERCEL LIMIT GUARD] Cooldown activo (<15min). Se ignora petición para evitar loop de facturación.")
            return

        hook_url = getattr(settings, "VERCEL_DEPLOY_HOOK_URL", None)
        if not hook_url:
            logger.info("ℹ️ No VERCEL_DEPLOY_HOOK_URL configurado. Frontend de Vercel no recompilará automáticamente.")
            return
            
        try:
            import urllib.request
            req = urllib.request.Request(hook_url, method="POST")
            with urllib.request.urlopen(req) as response:
                if response.status in (200, 201):
                    last_deploy_time = datetime.utcnow()
                    logger.info("🚀 [VERCEL CI/CD] Despliegue automático disparado y registrado en cooldown.")
        except Exception as e:
            logger.error(f"Falla notificando a Vercel Webhook: {e}")

reflection_engine = AIReflectionEngine()
