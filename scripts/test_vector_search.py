import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

async def test_search():
    print("Verificando documentos en Supabase...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 1. Contar documentos
    count = await conn.fetchval("SELECT COUNT(*) FROM public.nexo_documentos")
    print(f"Total de documentos en Supabase: {count}")
    
    if count == 0:
        print("Error: No se encontraron documentos.")
        await conn.close()
        return

    # 2. Probar busqueda vectorial (usando el primer embedding como referencia)
    row = await conn.fetchrow("SELECT content, embedding FROM public.nexo_documentos LIMIT 1")
    embedding = row['embedding']
    
    print(f"\nProbando busqueda de similitud para: '{row['content'][:50]}...'")
    
    # Busqueda k-NN usando correlacion de coseno (vector_cosine_ops => 1 - distance)
    # En pgvector, <=> es distancia de coseno. El indice se creo con vector_cosine_ops.
    results = await conn.fetch("""
        SELECT content, 1 - (embedding <=> $1::vector) as similarity
        FROM public.nexo_documentos
        ORDER BY embedding <=> $1::vector
        LIMIT 3
    """, embedding)
    
    print("\nResultados Top 3:")
    for i, r in enumerate(results):
        print(f"{i+1}. [{r['similarity']:.4f}] {r['content'][:60]}...")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_search())
