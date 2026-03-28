"""
Gemini Live Voice Service — NEXO SOBERANO
Conversación en tiempo real (texto + audio) usando Gemini 2.0/3.1 Flash Live.
Requiere: google-genai (ya en requirements.txt)
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import AsyncGenerator, Literal

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# gemini-2.0-flash-live-001 es el modelo estable; gemini-3.1-flash-live-preview es el preview
LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.0-flash-live-001")

NEXO_SYSTEM_PROMPT = """Eres NEXO, el asistente de IA personal soberano de Estefano.
Formas parte de la plataforma NEXO SOBERANO — infraestructura de IA que corre en la Torre
(i5-12600KF, 48 GB RAM, RTX 3060) y en Railway como respaldo en la nube.

Respondes en español, de manera directa y concisa. Tienes contexto sobre:
- Estado de los servicios del sistema (Docker, OBS, Discord, Drive)
- Geopolítica, economía y análisis de contenido
- Automatizaciones y pipelines de datos del usuario

Eres soberano: los datos no salen del ecosistema del usuario salvo cuando él lo ordena.
"""


class GeminiLiveService:
    """Servicio de sesión de voz/texto en tiempo real con Gemini Live."""

    def __init__(self) -> None:
        self.api_key = GEMINI_API_KEY
        self.model = LIVE_MODEL
        self._available = bool(self.api_key)
        if not self._available:
            logger.warning("[GeminiLive] GEMINI_API_KEY no configurada — servicio desactivado")
        else:
            logger.info(f"[GeminiLive] Iniciado con modelo {self.model}")

    @property
    def available(self) -> bool:
        return self._available

    async def chat(
        self,
        text: str,
        modality: Literal["TEXT", "AUDIO"] = "TEXT",
    ) -> AsyncGenerator[dict, None]:
        """
        Envía un mensaje de texto y recibe la respuesta en streaming.

        Yields dicts:
          {"type": "text",  "content": str}
          {"type": "audio", "data": str}   ← base64 PCM 16-bit 24kHz mono
          {"type": "done"}
          {"type": "error", "content": str}
        """
        if not self._available:
            yield {"type": "error", "content": "GEMINI_API_KEY no configurada"}
            return

        try:
            from google import genai  # type: ignore
            from google.genai import types as gtypes  # type: ignore

            client = genai.Client(api_key=self.api_key)
            live_config = gtypes.LiveConnectConfig(
                response_modalities=[modality],
                system_instruction=NEXO_SYSTEM_PROMPT,
            )

            async with client.aio.live.connect(model=self.model, config=live_config) as session:
                await session.send_message(
                    gtypes.Content(parts=[gtypes.Part(text=text)])
                )
                async for response in session.receive():
                    if hasattr(response, "text") and response.text:
                        yield {"type": "text", "content": response.text}
                    elif hasattr(response, "data") and response.data:
                        yield {
                            "type": "audio",
                            "data": base64.b64encode(response.data).decode(),
                        }

        except Exception as exc:
            logger.error(f"[GeminiLive] Error en sesión: {exc}")
            yield {"type": "error", "content": str(exc)}

        yield {"type": "done"}

    async def audio_bytes(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Envía texto y recibe chunks de PCM raw (sin base64).
        Útil para pipelines de audio directo.
        """
        if not self._available:
            return

        try:
            from google import genai  # type: ignore
            from google.genai import types as gtypes  # type: ignore

            client = genai.Client(api_key=self.api_key)
            live_config = gtypes.LiveConnectConfig(
                response_modalities=["AUDIO"],
                system_instruction=NEXO_SYSTEM_PROMPT,
            )

            async with client.aio.live.connect(model=self.model, config=live_config) as session:
                await session.send_message(
                    gtypes.Content(parts=[gtypes.Part(text=text)])
                )
                async for response in session.receive():
                    if hasattr(response, "data") and response.data:
                        yield response.data

        except Exception as exc:
            logger.error(f"[GeminiLive] Error en stream de audio: {exc}")


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: GeminiLiveService | None = None


def get_live_service() -> GeminiLiveService:
    global _instance
    if _instance is None:
        _instance = GeminiLiveService()
    return _instance
