from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from NEXO_CORE import config
from NEXO_CORE.core.state_manager import state_manager

logger = logging.getLogger(__name__)


class DiscordManager:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._rate_limited_until: float = 0.0

    def is_rate_limited(self) -> bool:
        return time.time() < self._rate_limited_until

    def _register_rate_limit(self, retry_after_header: Optional[str]) -> None:
        retry_after_seconds = 60.0
        if retry_after_header:
            try:
                retry_after_seconds = float(retry_after_header)
            except (TypeError, ValueError):
                retry_after_seconds = 60.0
        self._rate_limited_until = time.time() + max(10.0, retry_after_seconds)

    def _remaining_cooldown_seconds(self) -> int:
        return max(0, int(self._rate_limited_until - time.time()))

    def _track_usage(self, operaciones: int, tipo_operacion: str) -> None:
        try:
            from backend.services.unified_cost_tracker import get_cost_tracker

            tracker = get_cost_tracker()
            tracker.track_service_call(
                servicio="discord_webhook",
                operaciones=operaciones,
                tipo_operacion=tipo_operacion,
                metadata={"source": "NEXO_CORE.discord_manager"},
            )
        except Exception:
            return

    async def health_check(self) -> bool:
        if not config.DISCORD_ENABLED or not config.DISCORD_WEBHOOK_URL:
            state_manager.set_discord_connected(False)
            return False

        if self.is_rate_limited():
            remaining = self._remaining_cooldown_seconds()
            state_manager.set_discord_connected(False)
            state_manager.set_last_error(f"Discord cooldown activo por rate limit ({remaining}s)")
            return False

        try:
            import aiohttp

            session_timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.get(config.DISCORD_WEBHOOK_URL) as response:
                    if response.status == 429:
                        self._register_rate_limit(response.headers.get("Retry-After"))
                        state_manager.set_discord_connected(False)
                        state_manager.set_last_error("Discord rate limited during health check")
                        return False
                    ok = response.status in (200, 204)
                    state_manager.set_discord_connected(ok)
                    if ok:
                        self._track_usage(1, "health_check")
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

    async def send_message(self, content: str) -> bool:
        if not config.DISCORD_ENABLED or not config.DISCORD_WEBHOOK_URL:
            return False

        if self.is_rate_limited():
            remaining = self._remaining_cooldown_seconds()
            state_manager.set_last_error(f"Discord send omitido por cooldown ({remaining}s)")
            return False

        text = (content or "").strip()
        if not text:
            return False

        try:
            import aiohttp

            payload = {"content": text[:1900]}
            session_timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.post(config.DISCORD_WEBHOOK_URL, json=payload) as response:
                    if response.status == 429:
                        self._register_rate_limit(response.headers.get("Retry-After"))
                        state_manager.set_discord_connected(False)
                        state_manager.set_last_error("Discord rate limited while sending message")
                        return False
                    ok = response.status in (200, 204)
                    state_manager.set_discord_connected(ok)
                    if not ok:
                        body = await response.text()
                        state_manager.set_last_error(f"Discord send failed: {response.status} {body[:250]}")
                    else:
                        self._track_usage(1, "send_message")
                    return ok
        except Exception as exc:
            state_manager.set_discord_connected(False)
            state_manager.set_last_error(f"Discord send failed: {exc}")
            logger.warning("Discord send failed: %s", exc)
            return False

    async def notify_stream_state(self, active: bool, current_scene: str | None) -> bool:
        """Envía notificación enriquecida de cambio de estado del stream"""
        if not config.DISCORD_ENABLED or not config.DISCORD_WEBHOOK_URL:
            return False

        if self.is_rate_limited():
            remaining = self._remaining_cooldown_seconds()
            state_manager.set_last_error(f"Discord notify omitido por cooldown ({remaining}s)")
            return False

        try:
            import aiohttp

            if active:
                title = "🔴 Stream INICIADO"
                description = "El stream está ahora **en vivo**"
                color = 0x43B581  # Verde Discord
            else:
                title = "⚫ Stream FINALIZADO"
                description = "El stream se ha **detenido**"
                color = 0x747F8D  # Gris Discord

            fields = []
            if current_scene:
                fields.append({
                    "name": "🎬 Escena Actual",
                    "value": current_scene,
                    "inline": True
                })
            
            fields.append({
                "name": "⏰ Hora",
                "value": datetime.now().strftime("%H:%M:%S"),
                "inline": True
            })

            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "NEXO Stream Control"
                }
            }

            payload = {"embeds": [embed]}
            session_timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.post(config.DISCORD_WEBHOOK_URL, json=payload) as response:
                    if response.status == 429:
                        self._register_rate_limit(response.headers.get("Retry-After"))
                        state_manager.set_discord_connected(False)
                        state_manager.set_last_error("Discord rate limited while sending stream notification")
                        return False
                    ok = response.status in (200, 204)
                    state_manager.set_discord_connected(ok)
                    if ok:
                        self._track_usage(1, "stream_notification")
                    return ok
        except Exception as exc:
            state_manager.set_discord_connected(False)
            state_manager.set_last_error(f"Discord notify failed: {exc}")
            logger.warning("Discord notification failed: %s", exc)
            return False


discord_manager = DiscordManager()
