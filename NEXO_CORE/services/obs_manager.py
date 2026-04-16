from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from NEXO_CORE import config
from NEXO_CORE.core.state_manager import state_manager

logger = logging.getLogger(__name__)


class OBSManager:
    def __init__(self) -> None:
        self._client = None
        self._task: Optional[asyncio.Task] = None
        self._last_connect_log = 0.0
        self._log_interval_seconds = float(getattr(config, "OBS_DEGRADED_LOG_SECONDS", 60.0))

    def _should_log_now(self) -> bool:
        now = time.monotonic()
        if now - self._last_connect_log < self._log_interval_seconds:
            return False
        self._last_connect_log = now
        return True

    def _connect_sync(self):
        """Sync helper — runs in a thread to avoid blocking the event loop."""
        import obsws_python as obs
        return obs.ReqClient(
            host=config.OBS_HOST,
            port=config.OBS_PORT,
            password=config.OBS_PASSWORD,
            timeout=3,
        )

    async def connect(self) -> bool:
        if not config.OBS_ENABLED:
            state_manager.set_obs_connected(False)
            return False
        try:
            # Run the blocking TCP connect in a thread so the event loop stays free
            self._client = await asyncio.to_thread(self._connect_sync)
            state_manager.set_obs_connected(True)
            logger.info("OBS connected at %s:%s", config.OBS_HOST, config.OBS_PORT)
            return True
        except Exception as exc:
            state_manager.set_obs_connected(False)
            state_manager.set_last_error(f"OBS connect failed: {exc}")
            if self._should_log_now():
                logger.warning("OBS connection failed (degraded mode): %s", exc)
            self._client = None
            return False

    async def ensure_connected(self) -> bool:
        if state_manager.snapshot()["obs_connected"] and self._client is not None:
            return True
        return await self.connect()

    async def reconnect_loop(self) -> None:
        while True:
            if not config.OBS_ENABLED:
                await asyncio.sleep(config.OBS_RECONNECT_SECONDS)
                continue
            if not state_manager.snapshot()["obs_connected"]:
                await self.connect()
            await asyncio.sleep(config.OBS_RECONNECT_SECONDS)

    def start_background_reconnect(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.reconnect_loop())

    async def shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def get_current_scene(self) -> Optional[str]:
        if not self._client:
            return None
        try:
            current = self._client.get_current_program_scene()
            scene_name = getattr(current, "current_program_scene_name", None)
            state_manager.set_current_scene(scene_name)
            return scene_name
        except Exception as exc:
            state_manager.set_obs_connected(False)
            state_manager.set_last_error(f"OBS read scene failed: {exc}")
            logger.warning("OBS get_current_scene failed: %s", exc)
            return None

    async def get_stream_active(self) -> Optional[bool]:
        if not self._client:
            return None
        try:
            status = await asyncio.to_thread(self._client.get_stream_status)
            active = getattr(status, "output_active", None)
            if active is None:
                active = getattr(status, "active", None)
            if active is None:
                return None
            state_manager.set_stream_active(bool(active))
            return bool(active)
        except Exception as exc:
            state_manager.set_obs_connected(False)
            state_manager.set_last_error(f"OBS get_stream_status failed: {exc}")
            logger.warning("OBS get_stream_status failed: %s", exc)
            return None

    async def set_stream_active(self, active: bool) -> tuple[bool, str | None]:
        connected = await self.ensure_connected()
        if not connected or not self._client:
            return False, "OBS no conectado"

        try:
            current_active = await self.get_stream_active()
            if current_active is not None and bool(current_active) == bool(active):
                state_manager.set_stream_active(active)
                return True, None

            if active:
                await asyncio.to_thread(self._client.start_stream)
            else:
                await asyncio.to_thread(self._client.stop_stream)
            state_manager.set_stream_active(active)
            return True, None
        except Exception as exc:
            message = str(exc)
            if not active and "code 501" in message:
                state_manager.set_stream_active(False)
                state_manager.set_obs_connected(True)
                logger.info("OBS stop_stream idempotente (501): stream ya estaba detenido")
                return True, None

            state_manager.set_obs_connected(False)
            state_manager.set_last_error(f"OBS set_stream_active failed: {message}")
            logger.warning("OBS set_stream_active failed: %s", message)
            return False, message


obs_manager = OBSManager()
