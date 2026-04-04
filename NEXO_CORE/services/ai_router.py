# ============================================================
# NEXO SOBERANO — AI Router v2.0 (Sovereign First)
# © 2026 elanarcocapital.com
# Local (Gemma 4, $0) → Gemini Flash (barato) → Claude/GPT (crítico)
# Objetivo: 95%+ consultas resueltas localmente
# ============================================================
from __future__ import annotations
import logging
import os
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger("NEXO.ai_router")

FORCE_LOCAL    = os.getenv("FORCE_LOCAL_AI",   "false").lower() == "true"
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED",   "true").lower()  == "true"
GEMINI_KEY     = os.getenv("GEMINI_API_KEY",   "") or os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY","")


class AIRequest(BaseModel):
    prompt: str
    tipo: str = "general"
    system: Optional[str] = None
    temperatura: float = 0.1
    max_tokens: int = 4096
    forzar_cloud: bool = False
    forzar_local: bool = False
    contexto: Optional[str] = None   # para RAG inline


class AIResponse(BaseModel):
    texto: str
    modelo_usado: str
    fuente: str           # ollama_local | gemini_cloud | claude_cloud | error
    tokens: int = 0
    cost_usd: float = 0.0
    success: bool
    error: Optional[str] = None


# ── TASK ROUTING TABLE ───────────────────────────────────────────────────────
# LOCAL ($0): todo lo que Gemma 4 puede hacer bien
TAREAS_LOCAL = {
    # RAG y consultas de base de conocimiento
    "rag", "resumen", "resumir", "summarize",
    # Clasificación y análisis de texto
    "clasificacion", "clasif", "bool", "sentiment", "sentimiento",
    # Traducción
    "traduccion", "translate",
    # Código
    "codigo", "code", "debug", "refactor", "script", "test",
    # Consultas generales de bajo riesgo
    "general", "chat", "info",
    # OSINT y análisis de inteligencia (Gemma 4 es excelente aquí)
    "osint", "osint_analysis", "threat", "threat_analysis",
    "recon", "profile", "network_analysis", "geoint",
    # Análisis de mercados/datos
    "market", "mercados", "datos", "data_analysis",
    # Generación de contenido
    "contenido", "draft", "email", "report", "informe",
    # Preguntas sobre el sistema
    "system", "status", "config",
}

# CLOUD GEMINI FLASH (barato, ~$0.0001/1K tokens)
TAREAS_GEMINI_FLASH = {
    "multimodal", "imagen", "image", "audio", "video_analysis",
    "largo", "long_context",   # contextos >4K tokens
    "busqueda", "search", "web",
}

# CLOUD CARO (Gemini Pro / Claude — solo cuando es crítico)
TAREAS_CLOUD_CARO = {
    "arquitectura", "architecture",
    "critico", "critical",
    "auditoria", "security_audit",
    "estrategia", "strategy",
    "legal",
}


class AIRouter:
    """
    Router soberano de IA v2.0.

    Jerarquía de costo:
    1. Ollama local (Gemma 4) — $0.00  ← preferido para 95%+ de consultas
    2. Gemini Flash             — ~$0.0001/1K tokens
    3. Gemini Pro / Claude      — ~$0.003/1K tokens (solo casos críticos)

    El objetivo es que el 95%+ de consultas se resuelvan localmente.
    """

    def __init__(self):
        self._ollama  = None
        self._gemini  = None
        logger.info("AIRouter v2.0 — modo soberano, Gemma 4 primero")

    @property
    def ollama(self):
        if self._ollama is None:
            from NEXO_CORE.services.ollama_service import ollama_service
            self._ollama = ollama_service
        return self._ollama

    def _routing_decision(self, tipo: str, forzar_cloud: bool, forzar_local: bool) -> str:
        """Devuelve: 'local' | 'gemini_flash' | 'gemini_pro' | 'claude'"""
        if forzar_local:
            return "local"
        if forzar_cloud:
            return "gemini_flash"
        if FORCE_LOCAL:
            return "local"
        if not OLLAMA_ENABLED:
            return "gemini_flash"
        tipo_lower = tipo.lower().replace("-", "_").replace(" ", "_")
        if tipo_lower in TAREAS_CLOUD_CARO:
            return "gemini_pro"
        if tipo_lower in TAREAS_GEMINI_FLASH:
            return "gemini_flash"
        # Por defecto: local
        return "local"

    def _ollama_model_type(self, tipo: str) -> str:
        if tipo in {"codigo", "code", "debug", "refactor", "script", "test"}:
            return "code"
        if tipo in {"clasificacion", "clasif", "bool", "sentiment", "traduccion", "fast"}:
            return "fast"
        return "general"

    async def consultar(self, request: AIRequest) -> AIResponse:
        """Punto de entrada único para todas las consultas de IA."""
        decision = self._routing_decision(
            request.tipo, request.forzar_cloud, request.forzar_local
        )

        # 1. Intentar local primero
        if decision == "local":
            disponible = await self.ollama.is_available()
            if disponible:
                modelo_tipo = self._ollama_model_type(request.tipo)
                prompt = request.prompt
                if request.contexto:
                    prompt = f"CONTEXTO:\n{request.contexto}\n\nCONSULTA:\n{request.prompt}"
                logger.info(f"Router → LOCAL/{modelo_tipo} | tipo={request.tipo}")
                resp = await self.ollama.consultar(
                    prompt=prompt,
                    modelo=modelo_tipo,
                    system=request.system,
                    temperature=request.temperatura,
                    max_tokens=request.max_tokens,
                )
                if resp.success:
                    return AIResponse(
                        texto=resp.text, modelo_usado=resp.model,
                        fuente="ollama_local", tokens=resp.tokens_used,
                        cost_usd=0.0, success=True,
                    )
                logger.warning(f"Ollama falló ({resp.error}) → fallback cloud")

        # 2. Gemini Flash
        if decision in ("local", "gemini_flash"):
            logger.info(f"Router → GEMINI FLASH | tipo={request.tipo}")
            return await self._gemini_flash(request)

        # 3. Gemini Pro (tareas críticas)
        if decision == "gemini_pro":
            logger.info(f"Router → GEMINI PRO | tipo={request.tipo}")
            return await self._gemini_pro(request)

        return await self._gemini_flash(request)

    async def consultar_rag(self, pregunta: str, contexto: str) -> AIResponse:
        """RAG siempre local con Gemma 4."""
        req = AIRequest(
            prompt=pregunta, tipo="rag", contexto=contexto,
            system=(
                "Eres NEXO, asistente soberano. Responde solo con el contexto dado. "
                "Si no está en el contexto, dilo claramente. Sé conciso."
            ),
            forzar_local=True,
        )
        return await self.consultar(req)

    async def analizar_osint(self, datos: str, objetivo: str = "") -> AIResponse:
        """Análisis OSINT completo con Gemma 4 — $0."""
        req = AIRequest(
            prompt=f"OBJETIVO: {objetivo}\n\nDATOS:\n{datos}",
            tipo="osint_analysis",
            system=(
                "Eres un analista de inteligencia OSINT de NEXO SOBERANO. "
                "Analiza los datos, extrae hallazgos clave, nivel de amenaza "
                "(BAJO/MEDIO/ALTO/CRÍTICO) y acciones recomendadas. Español."
            ),
            forzar_local=True,
        )
        resp = await self.consultar(req)
        return resp

    async def _gemini_flash(self, request: AIRequest) -> AIResponse:
        """Gemini 2.0 Flash — barato, rápido."""
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = request.prompt
            if request.system:
                prompt = f"{request.system}\n\n{prompt}"
            response = model.generate_content(prompt)
            return AIResponse(
                texto=response.text, modelo_usado="gemini-2.0-flash",
                fuente="gemini_cloud", cost_usd=0.0001, success=True,
            )
        except Exception as e:
            logger.error(f"Gemini Flash error: {e}")
            return AIResponse(
                texto="", modelo_usado="gemini-2.0-flash",
                fuente="error", success=False, error=str(e),
            )

    async def _gemini_pro(self, request: AIRequest) -> AIResponse:
        """Gemini Pro — solo para tareas críticas."""
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(request.prompt)
            return AIResponse(
                texto=response.text, modelo_usado="gemini-1.5-pro",
                fuente="gemini_cloud", cost_usd=0.003, success=True,
            )
        except Exception as e:
            logger.error(f"Gemini Pro error, intentando Flash: {e}")
            return await self._gemini_flash(request)

    async def revisar_codigo(self, diff: str, archivo: str = "") -> AIResponse:
        """Revisión de código — Gemma 4 primero, Claude Sonnet fallback."""
        req = AIRequest(
            prompt=diff[:8000],
            tipo="codigo",
            contexto=f"Revisando {archivo}" if archivo else "",
            forzar_local=True,
            max_tokens=2048,
        )
        resp = await self.consultar(req)
        if not resp.success:
            # Fallback: Claude para code review
            resp = await self._claude_sonnet(AIRequest(
                prompt=diff[:8000],
                tipo="codigo",
                system="Senior code reviewer. Report CRITICAL/HIGH/MEDIUM issues with file:line format.",
                max_tokens=2048,
            ))
        return resp

    async def _claude_sonnet(self, request: AIRequest) -> AIResponse:
        """Claude Sonnet — fallback para tareas críticas."""
        if not ANTHROPIC_KEY:
            return AIResponse(
                texto="", modelo_usado="claude-sonnet",
                fuente="error", success=False, error="ANTHROPIC_API_KEY no configurado",
            )
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            messages = [{"role": "user", "content": request.prompt}]
            kwargs = {"model": "claude-sonnet-4-6", "max_tokens": request.max_tokens, "messages": messages}
            if request.system:
                kwargs["system"] = request.system
            msg = client.messages.create(**kwargs)
            text = msg.content[0].text if msg.content else ""
            tokens = msg.usage.input_tokens + msg.usage.output_tokens
            cost = round(tokens * 0.000003, 6)  # ~$3/M tokens
            logger.info(f"Claude Sonnet | tokens={tokens} | cost=${cost:.6f}")
            return AIResponse(
                texto=text, modelo_usado="claude-sonnet-4-6",
                fuente="claude_cloud", tokens=tokens, cost_usd=cost, success=True,
            )
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return AIResponse(
                texto="", modelo_usado="claude-sonnet",
                fuente="error", success=False, error=str(e),
            )

    async def get_routing_stats(self) -> dict:
        """Estado del router para el dashboard."""
        ollama_ok = await self.ollama.is_available()
        ollama_status = await self.ollama.supervisor_check() if ollama_ok else {}
        return {
            "local_available": ollama_ok,
            "local_model": ollama_status.get("active_general", "N/A"),
            "local_cost": "$0.00/consulta",
            "cloud_fallback_1": "gemini-2.0-flash",
            "cloud_fallback_2": "claude-sonnet-4-6",
            "force_local": FORCE_LOCAL,
            "tareas_locales": len(TAREAS_LOCAL),
            "tareas_cloud": len(TAREAS_GEMINI_FLASH) + len(TAREAS_CLOUD_CARO),
            "cerebros": {
                "local_primario": "Gemma 4 (Ollama) — $0.00",
                "cloud_barato":   "Gemini 2.0 Flash — ~$0.0001/1K",
                "cloud_potente":  "Claude Sonnet 4.6 — ~$0.003/1K",
                "cloud_critico":  "Gemini 1.5 Pro / Claude Opus — bajo demanda",
            },
            "ollama": ollama_status,
        }


# Instancia global
ai_router = AIRouter()
