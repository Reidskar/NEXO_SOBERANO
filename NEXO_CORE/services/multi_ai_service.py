import logging
import os
from typing import Optional

# Evitar colisión de imports si se ejecuta desde diferentes contextos
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from NEXO_CORE.agents.web_ai_supervisor import web_ai_supervisor
from backend.services.rag_service import get_rag_service
from backend.services.unified_cost_tracker import get_cost_tracker
from backend import config

logger = logging.getLogger(__name__)

def consultar_ia(query: str) -> str:
    """
    Función síncrona maestra para consultar a la IA.
    
    Esta función centraliza las peticiones de IA para componentes que no pueden
    usar async/await (como hilos de monitoreo o legacy code).
    
    Prioridad:
    1. Motor de generación RAG (síncrono, con fallbacks internos Gemini -> Claude).
    2. Fallback directo a Gemini si el servicio RAG no está disponible.
    """
    logger.info(f"[Multi-AI] Procesando query: {query[:60]}...")
    
    try:
        # Intentamos usar el servicio RAG existente
        # Invocamos _generar_respuesta directamente: es síncrona y ya gestiona 
        # el ruteo entre proveedores de IA (Gemini, Anthropic, etc.)
        rag = get_rag_service()
        
        # Enriquecemos el contexto con el estado actual del sistema vía supervisor
        contexto_adicional = ""
        try:
            snapshot = web_ai_supervisor.snapshot()
            contexto_adicional = f"\n\nCONTEXTO OPERATIVO ACTUAL:\n{snapshot}"
        except Exception:
            pass

        # Nota: La búsqueda vectorial es asíncrona, por lo que en esta llamada síncrona
        # pasamos una lista vacía de fragmentos. El motor usará su base de conocimiento
        # base y el contexto del sistema proporcionado.
        respuesta = rag._generar_respuesta(query, contexto_adicional, [])
        
        if respuesta and not respuesta.startswith("❌ Error IA"):
            return respuesta
            
    except Exception as e:
        logger.warning(f"[Multi-AI] Falla en motor RAG síncrono: {e}")

    # --- FALLBACK FINAL A GEMINI DIRECTO ---
    # Si el motor RAG falló o no devolvió una respuesta válida, usamos Gemini directamente
    try:
        force_local = os.getenv("FORCE_LOCAL_AI", "false").lower() == "true"
        if force_local:
             return "Error IA SOBERANA: El motor RAG local falló y las APIs en la nube están deshabilitadas por seguridad (FORCE_LOCAL_AI=true)."

        if not config.GEMINI_API_KEY:
             return "Error: GEMINI_API_KEY no configurada y el motor RAG falló."
             
        import google.generativeai as genai
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.MODELO_FLASH)
        
        # Prompt de emergencia ultra-rápido
        prompt_emergencia = f"Responde como NEXO SOBERANO (Oficial de Inteligencia). Query: {query}"
        resp = model.generate_content(prompt_emergencia)
        
        if resp.text:
            # Registro de costo para el fallback directo
            try:
                tokens_in = len(prompt_emergencia) // 4
                tokens_out = len(resp.text) // 4
                get_cost_tracker().track_ai_call("gemini", config.MODELO_FLASH, tokens_in, tokens_out, "multi_ai_fallback")
            except Exception:
                pass
            return resp.text.strip()
    except Exception as e:
        logger.error(f"[Multi-AI] Fallback final de Gemini falló: {e}")
        return f"IA indispuesta: {e}"

if __name__ == "__main__":
    # Test rápido si se ejecuta directamente
    logging.basicConfig(level=logging.INFO)
    log.info("Probando Multi-AI Service...")
    log.info(consultar_ia("hola, ¿cuál es tu estatus?"))
