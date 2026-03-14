from NEXO_CORE import config

def build_cors_options() -> dict:
    return {
        "allow_origins": getattr(config, "CORS_ORIGINS", ["*"]),
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
