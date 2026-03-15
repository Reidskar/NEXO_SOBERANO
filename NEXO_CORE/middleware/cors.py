from __future__ import annotations

from typing import Dict, Any

from NEXO_CORE import config


def build_cors_options() -> Dict[str, Any]:
    allow_origins = config.CORS_ORIGINS or ["*"]
    wildcard = "*" in allow_origins
    return {
        "allow_origins": allow_origins,
        "allow_credentials": not wildcard,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
