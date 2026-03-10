import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SQL_FILE = Path("c:/Users/Admn/Desktop/NEXO_SOBERANO/init_vector_db.sql")

async def init_db():
    if not SQL_FILE.exists():
        print(f"Error: No se encontro {SQL_FILE}")
        return

    print(f"Ejecutando {SQL_FILE} en Supabase...")
    sql_content = SQL_FILE.read_text(encoding='utf-8')
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        # Split by semicolon to run multiple commands if needed, 
        # or just run as one block if pgvector extension allows.
        # asyncpg.execute can run multiple statements.
        await conn.execute(sql_content)
        await conn.close()
        print("Esquema inicializado correctamente.")
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())
