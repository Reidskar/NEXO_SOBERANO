# ============================================================
# NEXO SOBERANO — Ollama Local Service
# © 2026 elanarcocapital.com
# Conecta NEXO_CORE con modelos locales via Ollama
# Prioridad: local primero, cloud como fallback
# ============================================================
from __future__ import annotations
import logging
import os
import json
import asyncio
from typing import Optional, AsyncGenerator
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger("NEXO.ollama_service")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_RAG  = os.getenv("OLLAMA_MODEL_RAG", "gemma2:9b")
MODEL_CODE = os.getenv("OLLAMA_MODEL_CODE", "qwen2.5-coder:7b")
ENABLED    = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"


class OllamaRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    system: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2048


class OllamaResponse(BaseModel):
    text: str
    model: str
    success: bool
    tokens_used: int = 0
    source: str = "ollama_local"
    error: Optional[str] = None


class OllamaService:
    """
    Servicio de IA 100% local usando Ollama.
    Reemplaza llamadas a Gemini/Anthropic para tareas
    que no requieren modelos de frontera.

    Estrategia de routing:
    - RAG y consultas generales → gemma2:9b
    - Código y debugging       → qwen2.5-coder:7b
    - Decisiones críticas      → fallback a Gemini
    """

    def __init__(self):
        self.base_url = OLLAMA_URL
        self.enabled  = ENABLED
        logger.info(
            f"OllamaService init: enabled={self.enabled} "
            f"url={self.base_url} rag={MODEL_RAG}"
        )

    async def is_available(self) -> bool:
        """Verifica si Ollama está corriendo."""
        if not self.enabled:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def get_available_models(self) -> list[str]:
        """Lista modelos disponibles en Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags"
                ) as resp:
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error listando modelos Ollama: {e}")
            return []

    async def consultar(
        self,
        prompt: str,
        modelo: str = "rag",
        system: Optional[str] = None,
        temperature: float = 0.1
    ) -> OllamaResponse:
        """
        Consulta principal a Ollama.

        Args:
            prompt: Texto de la consulta
            modelo: "rag" (gemma2) | "code" (qwen) | nombre exacto
            system: Prompt de sistema opcional
            temperature: Creatividad (0.0-1.0)

        Returns:
            OllamaResponse con el texto generado
        """
        if not self.enabled:
            return OllamaResponse(
                text="", model="none", success=False,
                error="Ollama desactivado"
            )

        # Resolver modelo
        model_name = {
            "rag":  MODEL_RAG,
            "code": MODEL_CODE
        }.get(modelo, modelo)

        payload = {
            "model":  model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        if system:
            payload["system"] = system

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return OllamaResponse(
                            text="", model=model_name,
                            success=False, error=error_text
                        )
                    data = await resp.json()
                    return OllamaResponse(
                        text=data.get("response", ""),
                        model=model_name,
                        success=True,
                        tokens_used=data.get("eval_count", 0)
                    )
        except asyncio.TimeoutError:
            logger.error(f"Timeout en Ollama ({model_name})")
            return OllamaResponse(
                text="", model=model_name,
                success=False, error="timeout"
            )
        except Exception as e:
            logger.error(f"Error en OllamaService.consultar: {e}")
            return OllamaResponse(
                text="", model=model_name,
                success=False, error=str(e)
            )

    async def consultar_rag(
        self,
        pregunta: str,
        contexto: str
    ) -> OllamaResponse:
        """
        Consulta RAG optimizada para gemma2:9b.
        Usa el contexto recuperado de Qdrant.
        """
        system = (
            "Eres el asistente de NEXO SOBERANO. "
            "Responde SOLO basándote en el contexto dado. "
            "Si no está en el contexto, dilo claramente. "
            "Responde en el mismo idioma de la pregunta."
        )
        prompt = f"CONTEXTO:\n{contexto}\n\nPREGUNTA:\n{pregunta}"
        return await self.consultar(
            prompt=prompt,
            modelo="rag",
            system=system,
            temperature=0.05
        )


# Instancia global
ollama_service = OllamaService()
