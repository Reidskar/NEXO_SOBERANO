# ============================================================
# NEXO SOBERANO — Ollama Local Service  v2.0
# © 2026 elanarcocapital.com
# Gemma 4 primero (costo $0) → Gemma 3/2 fallback → cloud
# ============================================================
from __future__ import annotations
import logging
import os
import asyncio
from typing import Optional
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger("NEXO.ollama_service")

OLLAMA_URL   = os.getenv("OLLAMA_URL",          "http://localhost:11434")
OLLAMA_HOST  = os.getenv("OLLAMA_TORRE_HOST",   "")          # IP Torre en LAN si es remota
ENABLED      = os.getenv("OLLAMA_ENABLED",      "true").lower() == "true"

# Modelos configurables — se auto-detectan si están en blanco
MODEL_GENERAL = os.getenv("OLLAMA_MODEL_GENERAL", "")        # gemma4:27b o gemma3:27b
MODEL_FAST    = os.getenv("OLLAMA_MODEL_FAST",    "")        # gemma4:12b o gemma3:12b
MODEL_CODE    = os.getenv("OLLAMA_MODEL_CODE",    "")        # qwen2.5-coder:7b o devstral
MODEL_EMBED   = os.getenv("OLLAMA_MODEL_EMBED",   "nomic-embed-text")

# Prioridad de modelos por categoría (se usa el primero disponible)
GEMMA_PRIORITY = [
    "gemma4:27b", "gemma4:12b", "gemma4:4b", "gemma4",
    "gemma3:27b", "gemma3:12b", "gemma3:4b", "gemma3",
    "gemma2:27b", "gemma2:9b",  "gemma2",
    "gemma:7b",   "gemma",
]
CODE_PRIORITY = [
    "devstral:24b", "devstral",
    "qwen2.5-coder:14b", "qwen2.5-coder:7b", "qwen2.5-coder",
    "codellama:13b", "codellama",
]


class OllamaRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    system: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096


class OllamaResponse(BaseModel):
    text: str
    model: str
    success: bool
    tokens_used: int = 0
    source: str = "ollama_local"
    cost_usd: float = 0.0          # siempre 0 — local es gratis
    error: Optional[str] = None


class OllamaService:
    """
    Servicio de IA 100% local — costo $0/consulta.

    Estrategia de modelos:
    - General / RAG / OSINT  → Gemma 4 27B (o mejor disponible)
    - Rápido / clasificar     → Gemma 4 12B / 4B
    - Código / debug          → Devstral / Qwen2.5-Coder
    - Fallback                → cualquier Gemma disponible

    La auto-detección ocurre en el primer uso o al llamar
    refresh_models(). No requiere reinicio para nuevos modelos.
    """

    def __init__(self):
        self.base_url   = OLLAMA_HOST or OLLAMA_URL
        self.enabled    = ENABLED
        self._models_cache: list[str] = []
        self._general_model = MODEL_GENERAL
        self._fast_model    = MODEL_FAST
        self._code_model    = MODEL_CODE
        self._initialized   = False
        logger.info(f"OllamaService v2 init | url={self.base_url} | enabled={self.enabled}")

    # ── MODEL AUTO-DETECTION ─────────────────────────────────────────────────

    async def _fetch_models(self) -> list[str]:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as r:
                    if r.status == 200:
                        d = await r.json()
                        return [m["name"] for m in d.get("models", [])]
        except Exception as e:
            logger.debug(f"Ollama model fetch error: {e}")
        return []

    def _pick_model(self, priority_list: list[str], available: list[str]) -> str:
        """Devuelve el primer modelo de la lista que esté instalado."""
        avail_lower = [m.lower() for m in available]
        for candidate in priority_list:
            for avail in available:
                if candidate.lower() in avail.lower() or avail.lower() in candidate.lower():
                    return avail
        return available[0] if available else ""

    async def _init_models(self):
        """Auto-detecta y selecciona los mejores modelos disponibles."""
        if self._initialized:
            return
        self._models_cache = await self._fetch_models()
        if not self._models_cache:
            logger.warning("Ollama: no hay modelos disponibles")
            self._initialized = True
            return

        if not self._general_model:
            self._general_model = self._pick_model(GEMMA_PRIORITY, self._models_cache)
        if not self._fast_model:
            # Para tareas rápidas usa el modelo más pequeño de Gemma disponible
            small_priority = list(reversed(GEMMA_PRIORITY))
            self._fast_model = self._pick_model(small_priority, self._models_cache) or self._general_model
        if not self._code_model:
            self._code_model = self._pick_model(CODE_PRIORITY, self._models_cache) or self._general_model

        logger.info(
            f"Ollama modelos detectados:\n"
            f"  general={self._general_model}\n"
            f"  fast={self._fast_model}\n"
            f"  code={self._code_model}\n"
            f"  total disponibles={len(self._models_cache)}"
        )
        self._initialized = True

    async def refresh_models(self):
        """Fuerza re-detección de modelos (usar cuando se instale uno nuevo)."""
        self._initialized = False
        await self._init_models()
        return {
            "general": self._general_model,
            "fast":    self._fast_model,
            "code":    self._code_model,
            "all":     self._models_cache,
        }

    # ── AVAILABILITY ────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        if not self.enabled:
            return False
        models = await self._fetch_models()
        return len(models) > 0

    async def get_available_models(self) -> list[str]:
        return await self._fetch_models()

    def _resolve_model(self, tipo: str) -> str:
        """Mapea tipo de tarea → nombre de modelo."""
        if tipo in ("code", "debug", "refactor", "script"):
            return self._code_model or self._general_model
        if tipo in ("fast", "clasif", "clasificacion", "traduccion", "bool"):
            return self._fast_model or self._general_model
        return self._general_model

    # ── CORE QUERY ──────────────────────────────────────────────────────────

    async def consultar(
        self,
        prompt: str,
        modelo: str = "general",
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> OllamaResponse:
        """Consulta principal — $0 costo, respuesta local."""
        if not self.enabled:
            return OllamaResponse(text="", model="none", success=False, error="Ollama desactivado")

        await self._init_models()
        model_name = self._resolve_model(modelo) if modelo in (
            "general", "rag", "fast", "code", "debug", "clasif",
            "clasificacion", "traduccion", "refactor", "script", "bool"
        ) else modelo

        if not model_name:
            return OllamaResponse(text="", model="none", success=False, error="Sin modelos en Ollama")

        payload = {
            "model":  model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        if system:
            payload["system"] = system

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"Ollama HTTP {resp.status}: {err[:200]}")
                        return OllamaResponse(text="", model=model_name, success=False, error=err[:200])
                    data = await resp.json()
                    tokens = data.get("eval_count", 0)
                    logger.debug(f"Ollama OK | model={model_name} tokens={tokens}")
                    return OllamaResponse(
                        text=data.get("response", ""),
                        model=model_name,
                        success=True,
                        tokens_used=tokens,
                        cost_usd=0.0,
                    )
        except asyncio.TimeoutError:
            logger.error(f"Ollama timeout | model={model_name}")
            return OllamaResponse(text="", model=model_name, success=False, error="timeout")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return OllamaResponse(text="", model=model_name, success=False, error=str(e))

    # ── SPECIALIZED QUERIES ──────────────────────────────────────────────────

    async def consultar_rag(self, pregunta: str, contexto: str) -> OllamaResponse:
        """RAG local con Gemma 4 — $0."""
        system = (
            "Eres NEXO, asistente de inteligencia de El Anarcocapital. "
            "Responde ÚNICAMENTE con información del contexto dado. "
            "Si no está en el contexto, di 'No encontré esa información en los documentos'. "
            "Responde en el mismo idioma de la pregunta. Sé conciso y preciso."
        )
        prompt = f"CONTEXTO:\n{contexto}\n\nPREGUNTA:\n{pregunta}"
        return await self.consultar(prompt=prompt, modelo="general", system=system, temperature=0.05)

    async def analizar_osint(self, datos: str, objetivo: str = "") -> OllamaResponse:
        """Análisis OSINT con Gemma 4 — enriquece datos de TheBigBrother, Shodan, etc."""
        system = (
            "Eres un analista de inteligencia OSINT de NEXO SOBERANO. "
            "Analiza los datos proporcionados, extrae conclusiones clave, "
            "identifica patrones, amenazas y conexiones. "
            "Formato: resumen ejecutivo, hallazgos clave (bullets), nivel de amenaza (BAJO/MEDIO/ALTO/CRÍTICO), "
            "acciones recomendadas. Responde en español."
        )
        prompt = f"OBJETIVO DEL ANÁLISIS: {objetivo}\n\nDATOS OSINT:\n{datos}"
        return await self.consultar(prompt=prompt, modelo="general", system=system, temperature=0.1)

    async def resumir(self, texto: str, max_palabras: int = 200) -> OllamaResponse:
        """Resumen rápido con modelo fast — $0."""
        system = f"Resume el siguiente texto en máximo {max_palabras} palabras. Responde solo el resumen."
        return await self.consultar(prompt=texto, modelo="fast", system=system, temperature=0.05)

    async def clasificar(self, texto: str, categorias: list[str]) -> OllamaResponse:
        """Clasificación binaria/multicategoría — ultra rápido, $0."""
        cats = ", ".join(categorias)
        system = f"Clasifica el texto en UNA de estas categorías: {cats}. Responde SOLO el nombre de la categoría."
        return await self.consultar(prompt=texto, modelo="fast", system=system, temperature=0.0)

    async def generar_codigo(self, instruccion: str, lenguaje: str = "python") -> OllamaResponse:
        """Generación de código con modelo especializado — $0."""
        system = (
            f"Eres un experto en {lenguaje}. Genera código limpio, funcional y bien comentado. "
            "Responde SOLO con el código, sin explicaciones adicionales."
        )
        return await self.consultar(prompt=instruccion, modelo="code", system=system, temperature=0.05)

    async def supervisor_check(self) -> dict:
        """Estado completo del servicio Ollama para el supervisor."""
        available = await self.is_available()
        models = await self.get_available_models() if available else []
        await self._init_models()
        return {
            "available": available,
            "url": self.base_url,
            "models_count": len(models),
            "models": models,
            "active_general": self._general_model,
            "active_fast": self._fast_model,
            "active_code": self._code_model,
            "cost_usd_per_query": 0.0,
            "status": "online" if available else "offline",
        }


# Instancia global
ollama_service = OllamaService()
