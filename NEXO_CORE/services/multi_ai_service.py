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

    # --- FALLBACK FINAL: OLLAMA LOCAL → GEMINI CLOUD ---
    force_local = os.getenv("FORCE_LOCAL_AI", "false").lower() == "true"
    prompt_emergencia = f"Responde como NEXO SOBERANO (Oficial de Inteligencia). Query: {query}"

    # Intentar Ollama local primero (siempre disponible, sin costo)
    try:
        import requests as _req
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL_RAG", "gemma3:12b")
        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": "Eres NEXO SOBERANO, un Oficial de Inteligencia. Responde de forma precisa."},
                {"role": "user", "content": prompt_emergencia}
            ],
            "stream": False,
            "options": {"temperature": 0.1}
        }
        resp = _req.post(f"{ollama_url}/api/chat", json=payload, timeout=25)
        resp.raise_for_status()
        text = resp.json().get("message", {}).get("content", "").strip()
        if text:
            try:
                get_cost_tracker().track_ai_call(
                    "ollama_local", ollama_model,
                    len(prompt_emergencia) // 4, len(text) // 4,
                    "multi_ai_fallback"
                )
            except Exception:
                pass
            return text
    except Exception as e:
        logger.warning(f"[Multi-AI] Ollama fallback falló: {e}")

    if force_local:
        return "Error IA SOBERANA: Ollama no disponible y FORCE_LOCAL_AI=true bloquea APIs cloud."

    # Gemini cloud como último recurso
    try:
        if not config.GEMINI_API_KEY:
             return "Error: GEMINI_API_KEY no configurada y Ollama no disponible."

        from google import genai as new_genai

        client = new_genai.Client(api_key=config.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=config.MODELO_FLASH,
            contents=prompt_emergencia,
        )

        if resp.text:
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
    logger.info("Probando Multi-AI Service...")
    logger.info(consultar_ia("hola, ¿cuál es tu estatus?"))
