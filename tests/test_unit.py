"""
Unit tests for NEXO SOBERANO — run with `pytest tests/` (no live server required).

These tests validate configuration loading, core state management, and rate-limiting
logic without relying on external services (Gemini, ChromaDB, SQLite on disk, etc.).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so all local packages are importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# backend.config
# ---------------------------------------------------------------------------

class TestBackendConfig:
    def test_app_metadata(self):
        from backend import config
        assert config.APP_TITLE
        assert config.APP_VERSION
        assert config.APP_DESCRIPTION

    def test_cors_origins_are_strings(self):
        from backend import config
        assert isinstance(config.CORS_ORIGINS, list)
        for origin in config.CORS_ORIGINS:
            assert isinstance(origin, str)
            assert origin.startswith("http")

    def test_token_budget_positive(self):
        from backend import config
        assert config.MAX_TOKENS_DIA > 0

    def test_chunk_settings(self):
        from backend import config
        assert config.CHUNK_SIZE > 0
        assert config.CHUNK_OVERLAP >= 0
        assert config.CHUNK_OVERLAP < config.CHUNK_SIZE

    def test_supported_extensions(self):
        from backend import config
        assert ".pdf" in config.EXTENSION_SOPORTADAS
        assert ".txt" in config.EXTENSION_SOPORTADAS
        assert ".md" in config.EXTENSION_SOPORTADAS


# ---------------------------------------------------------------------------
# NEXO_CORE.config
# ---------------------------------------------------------------------------

class TestNexoCoreConfig:
    def test_app_metadata(self):
        from NEXO_CORE import config
        assert config.APP_TITLE
        assert config.APP_VERSION
        assert config.APP_DESCRIPTION

    def test_cors_origins_are_strings(self):
        from NEXO_CORE import config
        assert isinstance(config.CORS_ORIGINS, list)
        for origin in config.CORS_ORIGINS:
            assert isinstance(origin, str)
            assert origin.startswith("http")

    def test_rate_limits_positive(self):
        from NEXO_CORE import config
        assert config.RATE_LIMIT_READ_PER_MIN > 0
        assert config.RATE_LIMIT_WRITE_PER_MIN > 0

    def test_request_max_bytes_positive(self):
        from NEXO_CORE import config
        assert config.REQUEST_MAX_BYTES > 0

    def test_token_budget_positive(self):
        from NEXO_CORE import config
        assert config.MAX_TOKENS_DIA > 0


# ---------------------------------------------------------------------------
# NEXO_CORE.core.state_manager
# ---------------------------------------------------------------------------

class TestStateManager:
    def _fresh(self):
        from NEXO_CORE.core.state_manager import StateManager
        return StateManager()

    def test_initial_snapshot_defaults(self):
        sm = self._fresh()
        snap = sm.snapshot()
        assert snap["stream_active"] is False
        assert snap["obs_connected"] is False
        assert snap["discord_connected"] is False
        assert snap["ai_requests_today"] == 0
        assert snap["last_error"] is None
        assert snap["uptime_start"] is not None

    def test_set_stream_active(self):
        sm = self._fresh()
        sm.set_stream_active(True)
        assert sm.snapshot()["stream_active"] is True

    def test_set_obs_connected(self):
        sm = self._fresh()
        sm.set_obs_connected(True)
        assert sm.snapshot()["obs_connected"] is True

    def test_set_discord_connected(self):
        sm = self._fresh()
        sm.set_discord_connected(True)
        assert sm.snapshot()["discord_connected"] is True

    def test_set_current_scene(self):
        sm = self._fresh()
        sm.set_current_scene("GameCapture")
        assert sm.snapshot()["current_scene"] == "GameCapture"

    def test_set_last_error(self):
        sm = self._fresh()
        sm.set_last_error("timeout")
        snap = sm.snapshot()
        assert snap["last_error"] == "timeout"
        assert snap["last_error_at"] is not None

    def test_increase_ai_requests(self):
        sm = self._fresh()
        sm.increase_ai_requests(3)
        assert sm.snapshot()["ai_requests_today"] == 3
        sm.increase_ai_requests()
        assert sm.snapshot()["ai_requests_today"] == 4


# ---------------------------------------------------------------------------
# NEXO_CORE.middleware.rate_limit
# ---------------------------------------------------------------------------

class TestInMemoryRateLimiter:
    def test_allows_requests_under_limit(self):
        from NEXO_CORE.middleware.rate_limit import InMemoryRateLimiter
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            limiter.check("client1")  # should not raise

    def test_raises_on_exceeded_limit(self):
        import pytest
        from fastapi import HTTPException
        from NEXO_CORE.middleware.rate_limit import InMemoryRateLimiter
        limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.check("client2")
        with pytest.raises(HTTPException) as exc_info:
            limiter.check("client2")
        assert exc_info.value.status_code == 429

    def test_different_keys_are_isolated(self):
        from NEXO_CORE.middleware.rate_limit import InMemoryRateLimiter
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        limiter.check("a")
        limiter.check("a")
        # "b" is a fresh key and should still be allowed
        limiter.check("b")
