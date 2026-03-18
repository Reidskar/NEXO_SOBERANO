import json
import logging
from core.config import settings
from core.system_config import get_config, update_config
from core.learning_log import get_recent_changes, log_change
try:
    from openai import AsyncAzureOpenAI
except ImportError:
    AsyncAzureOpenAI = None

logger = logging.getLogger(__name__)

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
            "Analyze the latest epoch metrics and decide if the configuration should be kept, reverted, or adjusted to improve performance or accuracy.\n"
            f"Current Active Configuration:\n{json.dumps(current_config, indent=2)}\n\n"
            f"Recent Telemetry Metrics:\n{json.dumps(metrics, indent=2)}\n\n"
            "Strict Rules:\n"
            "1. You MAY ONLY modify ['video']['style'], ['video']['min_impact_score'], and ['ai']['temperature'].\n"
            "2. Ensure the structural integrity of the output JSON.\n"
            "Output strictly JSON:\n"
            "{\n"
            "  \"decision\": \"keep\" | \"adjust\",\n"
            "  \"reason\": \"Explain your highly analytical reason based purely on given metrics\",\n"
            "  \"suggested_changes\": { \"video\": { \"style\": \"aggressive\" } }\n"
            "}\n"
            "If 'keep', leave 'suggested_changes' empty."
        )

        try:
            if not self.client:
                logger.warning("No Azure OpenAI disponible. Fallback Reflection Engine.")
                return

            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            decision = evaluation.get("decision", "keep")
            reason = evaluation.get("reason", "No reason provided")
            
            logger.info(f"🔍 [REFLECTION ENGINE] Decisión Autónoma: {decision.upper()} | Razonamiento: {reason}")

            if decision == "adjust" and evaluation.get("suggested_changes"):
                # Shallow Merge dinámico
                new_config = {**current_config} 
                for section, values in evaluation["suggested_changes"].items():
                    if section in new_config and isinstance(values, dict):
                        new_config[section] = {**new_config[section], **values}
                
                logger.warning(f"⚡ [REFLECTION ENGINE] INICIANDO MUTACIÓN EVOLUTIVA AUTÓNOMA.")
                log_change("ai_reflection_adjustment", current_config, new_config, reason)
                update_config(new_config)

        except Exception as e:
            logger.error(f"Error crítico durante la heurística de reflexión: {e}")

reflection_engine = AIReflectionEngine()
