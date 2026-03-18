import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./nexo.db"
    DISCORD_TOKEN: str = ""
    GOOGLE_CREDENTIALS_PATH: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    DISCORD_WEBHOOK_URL: str = ""
    SUPABASE_WEBHOOK_SECRET: str = "super_secure_nexo_token"
    VERCEL_DEPLOY_HOOK_URL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
