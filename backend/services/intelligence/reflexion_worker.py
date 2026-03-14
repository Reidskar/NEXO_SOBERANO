"""
backend/services/intelligence/reflexion_worker.py
================================================
Orquestador del Bucle de Reflexión y Publicación de NEXO SOBERANO.

Este componente se encarga de:
1. Ejecutar el DailySummarizer periódicamente.
2. Disparar al AutonomousCommunityAgent para publicar hallazgos clave.
3. Mantener la coherencia del sistema de inteligencia.
"""

import asyncio
import logging
from backend.services.intelligence.daily_summarizer import daily_summarizer
from backend.services.intelligence.autonomous_agent import community_agent

logger = logging.getLogger(__name__)

async def run_reflexion_cycle():
    """Ciclo completo de reflexión: Resumen -> Publicación."""
    logger.info("⚡ Iniciando ciclo de Reflexión de NEXO...")
    
    # 1. Generar Reporte Diario (The Magazine)
    # En producción esto podría correr una vez al día a las 00:00
    report = await daily_summarizer.generate_magazine()
    logger.info("🗞️ 'The Magazine' actualizado.")
    
    # 2. Análisis de Difusión (Social Media)
    # Busca hallazgos de alto impacto para compartir
    publication = await community_agent.review_and_publish_highlight()
    if publication.get("ok"):
        logger.info(f"📢 Difusión activa: {publication.get('text')[:50]}...")
    else:
        logger.info(f"ℹ️ Difusión en espera: {publication.get('reason')}")

async def reflexion_daemon(interval_hours: int = 6):
    """Loop infinito para el agente de reflexión."""
    logger.info(f"🤖 Agente de Reflexión activado (Intervalo: {interval_hours}h)")
    while True:
        try:
            await run_reflexion_cycle()
        except Exception as e:
            logger.error(f"❌ Error en el loop de reflexión: {e}")
        
        # Esperar el intervalo
        await asyncio.sleep(interval_hours * 3600)

if __name__ == "__main__":
    # Prueba puntual
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reflexion_cycle())
