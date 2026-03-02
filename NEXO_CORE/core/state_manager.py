from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Optional, Dict, Any


@dataclass
class SystemState:
    stream_active: bool = False
    obs_connected: bool = False
    discord_connected: bool = False
    ai_requests_today: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    current_scene: Optional[str] = None
    uptime_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StateManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state = SystemState()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "stream_active": self._state.stream_active,
                "obs_connected": self._state.obs_connected,
                "discord_connected": self._state.discord_connected,
                "ai_requests_today": self._state.ai_requests_today,
                "last_error": self._state.last_error,
                "last_error_at": self._state.last_error_at.isoformat() if self._state.last_error_at else None,
                "current_scene": self._state.current_scene,
                "uptime_start": self._state.uptime_start.isoformat(),
            }

    def set_stream_active(self, active: bool) -> None:
        with self._lock:
            self._state.stream_active = active

    def set_obs_connected(self, connected: bool) -> None:
        with self._lock:
            self._state.obs_connected = connected

    def set_discord_connected(self, connected: bool) -> None:
        with self._lock:
            self._state.discord_connected = connected

    def set_current_scene(self, scene_name: Optional[str]) -> None:
        with self._lock:
            self._state.current_scene = scene_name

    def set_last_error(self, message: str) -> None:
        with self._lock:
            self._state.last_error = message
            self._state.last_error_at = datetime.now(timezone.utc)

    def increase_ai_requests(self, count: int = 1) -> None:
        with self._lock:
            self._state.ai_requests_today += count


state_manager = StateManager()
