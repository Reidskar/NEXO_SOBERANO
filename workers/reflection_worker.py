import asyncio
import logging
import sys
import os

# Asegurar que el path sea visible para importar desde /core y /services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_reflection import reflection_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - REFLECTION_WORKER - %(message)s")
logger = logging.getLogger(__name__)

async def run_reflection_loop():
    logger.info("🔄 [REFLECTION WORKER] Daemon de Auto-Evolución iniciado. Escuchando ciclo de épocas...")
    while True:
        try:
            # En modo MVP, vamos a evaluar el sistema rápido. 
            # En prod, esto correría cada 12 horas.
            await asyncio.sleep(180) 
            logger.info("⏳ Disparando pulso de reflexión periódica...")
            
            await reflection_engine.evaluate_system_performance()
            
            # Sleepear 1 hora o 2 para no saturar tokens
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Falla crítica en loop de reflexión: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    print(r"""
     _____       __ _           _   _             
    |  __ \     / _| |         | | (_)            
    | |__) |___| |_| | ___  ___| |_ _  ___  _ __  
    |  _  // _ \  _| |/ _ \/ __| __| |/ _ \| '_ \ 
    | | \ \  __/ | | |  __/ (__| |_| | (_) | | | |
    |_|  \_\___|_| |_|\___|\___|\__|_|\___/|_| |_| 
                CORTEX EVOLUTION ENGINE v1.0
    """)
    asyncio.run(run_reflection_loop())
