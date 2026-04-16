# ============================================================
# NEXO SOBERANO — AI Router (Sovereign First)
# © 2026 elanarcocapital.com
# Prioridad: Ollama local → Gemini → Anthropic
# Nunca gasta tokens de pago si Ollama puede resolverlo
# ============================================================
from __future__ import annotations
import logging
import os
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger("NEXO.ai_router")

FORCE_LOCAL    = os.getenv("FORCE_LOCAL_AI", "false").lower() == "true"
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
GEMMA_ENABLED  = os.getenv("GEMMA_ENABLED", "false").lower() == "true"


class AIRequest(BaseModel):
    prompt: str
    tipo: str = "general"
    system: Optional[str] = None
    temperatura: float = 0.1
    max_tokens: int = 2048
    forzar_cloud: bool = False


class AIResponse(BaseModel):
    texto: str
    modelo_usado: str
    fuente: str
    tokens: int = 0
    success: bool
    error: Optional[str] = None


# Clasificación de tareas por tipo
TAREAS_LOCALES = [
    "rag",           # consultas RAG → gemma2:9b
    "resumen",       # resumir textos → gemma2:9b
    "clasificacion", # clasificar → gemma2:9b
    "traduccion",    # traducir → gemma2:9b
    "codigo",        # generar código → qwen2.5-coder:7b
    "debug",         # debugging → qwen2.5-coder:7b
    "refactor",      # refactoring → qwen2.5-coder:7b
    "general",       # consultas generales → gemma2:9b
]

TAREAS_CLOUD = [
    "arquitectura",  # decisiones de arquitectura → Gemini
    "critico",       # análisis crítico complejo → Gemini
    "multimodal",    # imágenes/audio → Gemini
    "auditoria",     # auditoría de seguridad → Gemini
]


class AIRouter:
    """
    Router soberano de IA.
    Dirige cada consulta al modelo más eficiente
    priorizando siempre recursos locales.
    """

    def __init__(self):
        self._ollama = None
        self._gemini = None
        self._gemma  = None
        logger.info("AIRouter inicializado — modo soberano activado")

    @property
    def ollama(self):
        if self._ollama is None:
            from NEXO_CORE.services.ollama_service import ollama_service
            self._ollama = ollama_service
        return self._ollama

    @property
    def gemma(self):
        if self._gemma is None:
            from NEXO_CORE.services.gemma_service import gemma_service
            self._gemma = gemma_service
        return self._gemma

    def _debe_usar_local(self, tipo: str, forzar_cloud: bool) -> bool:
        if forzar_cloud:
            return False
        if FORCE_LOCAL:
            return True
        if not OLLAMA_ENABLED:
            return False
        return tipo in TAREAS_LOCALES

    def _modelo_ollama_para_tipo(self, tipo: str) -> str:
        if tipo in ["codigo", "debug", "refactor"]:
            return "code"
        if tipo in ["general", "critico", "arquitectura", "auditoria"]:
            return "general"
        return "rag"

    async def consultar(self, request: AIRequest) -> AIResponse:
        """
        Punto de entrada único para todas las consultas de IA.
        Decide automáticamente qué modelo usar.
        """
        usar_local = self._debe_usar_local(
            request.tipo, request.forzar_cloud
        )

        if usar_local:
            # 1️⃣ Intentar Ollama (más rápido en CPU si está corriendo)
            disponible = await self.ollama.is_available()
            if disponible:
                modelo_ollama = self._modelo_ollama_para_tipo(request.tipo)
                logger.info(
                    f"Router → OLLAMA ({modelo_ollama}) tipo={request.tipo}"
                )
                resp = await self.ollama.consultar(
                    prompt=request.prompt,
                    modelo=modelo_ollama,
                    system=request.system,
                    temperature=request.temperatura
                )
                if resp.success:
                    return AIResponse(
                        texto=resp.text,
                        modelo_usado=resp.model,
                        fuente="ollama_local",
                        tokens=resp.tokens_used,
                        success=True
                    )
                logger.warning(f"Ollama falló ({resp.error}), probando Gemma…")

            # 2️⃣ Fallback a Gemma local (HuggingFace Transformers)
            if GEMMA_ENABLED and self.gemma.is_available():
                try:
                    logger.info(f"Router → GEMMA LOCAL tipo={request.tipo}")
                    system = request.system or "Eres el asistente de NEXO SOBERANO. Responde en español."
                    texto = self.gemma.consultar(
                        prompt=request.prompt,
                        system=system,
                    )
                    return AIResponse(
                        texto=texto,
                        modelo_usado=self.gemma.model_id,
                        fuente="gemma_local",
                        success=True
                    )
                except Exception as e:
                    logger.warning(f"Gemma local falló: {e}")

            if FORCE_LOCAL:
                return AIResponse(
                    texto="Error IA SOBERANA: Ollama y Gemma local fallaron. Fallback a Cloud deshabilitado (FORCE_LOCAL_AI=true).",
                    modelo_usado="none",
                    fuente="error_local",
                    success=False,
                    error="local_engines_unavailable"
                )
            logger.warning("Local no disponible, fallback a cloud…")

        # 3️⃣ Fallback a Gemini cloud
        logger.info(f"Router → CLOUD (gemini) tipo={request.tipo}")
        return await self._consultar_gemini(request)

    async def consultar_rag(
        self,
        pregunta: str,
        contexto: str
    ) -> AIResponse:
        """RAG siempre usa Ollama local si está disponible."""
        request = AIRequest(
            prompt=pregunta,
            tipo="rag",
            system=(
                "Eres el asistente de NEXO SOBERANO. "
                "Responde solo con el contexto dado. "
                "Si no está en el contexto, dilo claramente."
            )
        )
        # Inyectar contexto en el prompt
        request.prompt = (
            f"CONTEXTO:\n{contexto}\n\nPREGUNTA:\n{pregunta}"
        )
        return await self.consultar(request)

    async def _consultar_gemini(
        self, request: AIRequest
    ) -> AIResponse:
        """Fallback a Gemini para tareas que requieren cloud."""
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(request.prompt)
            return AIResponse(
                texto=response.text,
                modelo_usado="gemini-2.0-flash",
                fuente="gemini_cloud",
                success=True
            )
        except Exception as e:
            logger.error(f"Error en Gemini fallback: {e}")
            return AIResponse(
                texto="",
                modelo_usado="none",
                fuente="error",
                success=False,
                error=str(e)
            )


# Instancia global
ai_router = AIRouter()
