# ============================================================
# NEXO SOBERANO — OBS Coordinator v1.0
# © 2026 elanarcocapital.com
#
# Coordina OBS Studio basándose en eventos del OmniGlobe.
# - Cambia escenas según severidad de eventos
# - Actualiza overlays con inteligencia en tiempo real
# - Controla grabación/streaming automático
# - Sincroniza con el globo para capturas de pantalla
# ============================================================
from __future__ import annotations
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NEXO.obs_coordinator")

OBS_HOST     = os.getenv("OBS_HOST",     "localhost")
OBS_PORT     = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

# Escenas según nivel de actividad del globo
SCENE_MAP = {
    "idle":       os.getenv("OBS_SCENE_IDLE",    "NEXO - Standby"),
    "monitoring": os.getenv("OBS_SCENE_MONITOR", "NEXO - Monitor"),
    "alert":      os.getenv("OBS_SCENE_ALERT",   "NEXO - Alerta"),
    "critical":   os.getenv("OBS_SCENE_CRITICAL","NEXO - Crítico"),
    "globe":      os.getenv("OBS_SCENE_GLOBE",   "NEXO - OmniGlobe"),
    "analysis":   os.getenv("OBS_SCENE_ANALYSIS","NEXO - Análisis"),
}

SOURCE_GLOBE    = os.getenv("OBS_SOURCE_GLOBE",   "OmniGlobe Browser")
SOURCE_TICKER   = os.getenv("OBS_SOURCE_TICKER",  "Intel Ticker")
SOURCE_LOGO     = os.getenv("OBS_SOURCE_LOGO",    "NEXO Logo")


class OBSCoordinator:
    """
    Coordina OBS basándose en la actividad del OmniGlobe.
    Usa obsws-python para control via WebSocket.
    """

    def __init__(self):
        self._client = None
        self._current_scene = "idle"
        self._event_queue: list[dict] = []
        self._connected = False

    async def connect(self) -> bool:
        if not OBS_PASSWORD:
            logger.info("OBS_PASSWORD no configurado — modo simulado")
            return False
        try:
            import obsws_python as obs
            self._client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
            self._connected = True
            logger.info(f"OBS conectado: {OBS_HOST}:{OBS_PORT}")
            return True
        except Exception as e:
            logger.warning(f"OBS no disponible: {e}")
            self._connected = False
            return False

    def disconnect(self):
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False

    async def cambiar_escena(self, escena_key: str) -> bool:
        """Cambia la escena activa de OBS."""
        scene_name = SCENE_MAP.get(escena_key, escena_key)
        if self._current_scene == escena_key:
            return True
        try:
            if self._connected and self._client:
                self._client.set_current_program_scene(scene_name)
            self._current_scene = escena_key
            logger.info(f"OBS escena → {scene_name}")
            return True
        except Exception as e:
            logger.warning(f"OBS scene change error: {e}")
            return False

    async def actualizar_texto(self, source_name: str, texto: str) -> bool:
        """Actualiza una fuente de texto en OBS (ticker, alertas, etc.)."""
        try:
            if self._connected and self._client:
                self._client.set_input_settings(
                    name=source_name,
                    settings={"text": texto[:500]},
                    overlay=True,
                )
            return True
        except Exception as e:
            logger.debug(f"OBS text update: {e}")
            return False

    async def iniciar_grabacion(self) -> bool:
        try:
            if self._connected and self._client:
                self._client.start_record()
                logger.info("OBS grabación iniciada")
            return True
        except Exception as e:
            logger.warning(f"OBS record start: {e}")
            return False

    async def captura_pantalla(self, source: str = SOURCE_GLOBE) -> Optional[str]:
        """Toma screenshot de una fuente (ej: el globo para compartir)."""
        try:
            if self._connected and self._client:
                path = f"/tmp/nexo_capture_{int(__import__('time').time())}.png"
                self._client.save_source_screenshot(
                    name=source, img_format="png", file_path=path, width=1920, height=1080,
                )
                return path
        except Exception as e:
            logger.debug(f"OBS screenshot: {e}")
        return None

    # ── COORDINACIÓN CON OMNIGLOBE ────────────────────────────────────────────

    async def on_globe_event(self, event: dict):
        """
        Responde a eventos del OmniGlobe.
        - Severidad alta → cambiar a escena de alerta
        - Severidad crítica → iniciar grabación, cambiar escena crítica
        - Narrativa → actualizar ticker
        """
        event_type = event.get("type", "")
        severity   = float(event.get("severity", 0))

        if event_type == "narrative":
            texto = event.get("text", event.get("content", ""))
            await self.actualizar_texto(SOURCE_TICKER, f"NEXO INTEL: {texto}")
            await self.cambiar_escena("globe")

        elif event_type in ("add_event",):
            if severity >= 0.8:
                await self.cambiar_escena("critical")
                await self.iniciar_grabacion()
                label = event.get("label", "Evento crítico")
                await self.actualizar_texto(SOURCE_TICKER, f"⚠ ALERTA: {label}")
            elif severity >= 0.6:
                await self.cambiar_escena("alert")
            elif severity >= 0.3:
                await self.cambiar_escena("monitoring")

        elif event_type == "fly_to":
            await self.cambiar_escena("globe")

    async def sincronizar_con_intel(self, events: list[dict]):
        """Procesa múltiples eventos del ciclo de intel en tiempo real."""
        if not events:
            return
        max_severity = max(float(e.get("severity", 0)) for e in events)
        if max_severity >= 0.8:
            await self.cambiar_escena("critical")
        elif max_severity >= 0.6:
            await self.cambiar_escena("alert")
        else:
            await self.cambiar_escena("monitoring")

        # Actualizar ticker con el evento más grave
        top_event = max(events, key=lambda e: float(e.get("severity", 0)))
        await self.actualizar_texto(SOURCE_TICKER, f"NEXO INTEL: {top_event.get('label', '')}")

    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "current_scene": self._current_scene,
            "host": f"{OBS_HOST}:{OBS_PORT}",
            "scenes_configured": list(SCENE_MAP.keys()),
        }


# Instancia global
obs_coordinator = OBSCoordinator()
