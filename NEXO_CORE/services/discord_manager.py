from __future__ import annotations

import asyncio
import logging
from typing import Optional

from NEXO_CORE import config
from NEXO_CORE.core.state_manager import state_manager

logger = logging.getLogger(__name__)


class DiscordManager:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None

    async def health_check(self) -> bool:
        if not config.DISCORD_ENABLED or not config.DISCORD_WEBHOOK_URL:
            state_manager.set_discord_connected(False)
            return False

        try:
            import aiohttp

            session_timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.get(config.DISCORD_WEBHOOK_URL) as response:
                    ok = response.status in (200, 204)
                    state_manager.set_discord_connected(ok)
                    return ok
        except Exception as exc:
            state_manager.set_discord_connected(False)
            state_manager.set_last_error(f"Discord health check failed: {exc}")
            logger.warning("Discord health check failed: %s", exc)
            return False

    async def reconnect_loop(self) -> None:
        while True:
            if not config.DISCORD_ENABLED:
                await asyncio.sleep(config.DISCORD_RECONNECT_SECONDS)
                continue
            await self.health_check()
            await asyncio.sleep(config.DISCORD_RECONNECT_SECONDS)

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


discord_manager = DiscordManager()
