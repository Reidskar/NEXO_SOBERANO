import asyncio
import os

async def test_postgres():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        # Ensure we use the local env variable or fallback
        url = os.getenv("DATABASE_URL", "postgresql+asyncpg://nexo:nexo_dev_pass@localhost:5432/nexo_soberano")
        engine = create_async_engine(url)
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("[OK] PostgreSQL: Conectado")
    except Exception as e:
        log.info(f"[FAIL] PostgreSQL: {e}")

def test_redis():
    try:
        from redis import Redis
        # Ensure we use the local env variable or fallback
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = Redis.from_url(url)
        r.ping()
        log.info("[OK] Redis: Conectado")
    except Exception as e:
        log.info(f"[FAIL] Redis: {e}")

def test_qdrant():
    try:
        from qdrant_client import QdrantClient
        # Ensure we use the local env variable or fallback
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=url)
        client.get_collections()
        log.info("[OK] Qdrant: Conectado")
    except Exception as e:
        log.info(f"[FAIL] Qdrant: {e}")

async def main():
    log.info("=== TEST INFRAESTRUCTURA SPRINT 1.1 ===")
    await test_postgres()
    test_redis()
    test_qdrant()
    log.info("=== FIN TEST ===")

if __name__ == "__main__":
    asyncio.run(main())
