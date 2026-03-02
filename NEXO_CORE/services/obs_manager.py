from __future__ import annotations

import asyncio
import logging
from typing import Optional

from NEXO_CORE import config
from NEXO_CORE.core.state_manager import state_manager

logger = logging.getLogger(__name__)


class OBSManager:
    def __init__(self) -> None:
        self._client = None
        self._task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        if not config.OBS_ENABLED:
            state_manager.set_obs_connected(False)
            return False
        try:
            import obsws_python as obs

            self._client = obs.ReqClient(
                host=config.OBS_HOST,
                port=config.OBS_PORT,
                password=config.OBS_PASSWORD,
                timeout=3,
            )
            state_manager.set_obs_connected(True)
            logger.info("OBS connected at %s:%s", config.OBS_HOST, config.OBS_PORT)
            return True
        except Exception as exc:
            state_manager.set_obs_connected(False)
            state_manager.set_last_error(f"OBS connect failed: {exc}")
            logger.warning("OBS connection failed: %s", exc)
            self._client = None
            return False

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


obs_manager = OBSManager()
