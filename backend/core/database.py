from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

# Debug placeholders to trap rogue imports (REMOVE LATER)
core_webhook_router = None
core_health_router = None

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or "sqlite" in DATABASE_URL.lower():
    raise ValueError("❌ Usa PostgreSQL en producción. DATABASE_URL debe empezar con postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,           # Railway/Render no necesita pooling extra
    echo=False
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def test_connection():
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        print("✅ Conexión PostgreSQL OK")
        return True
    except Exception as e:
        print(f"❌ Error DB: {e}")
        return False
