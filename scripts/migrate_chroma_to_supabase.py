import os
import asyncio
import asyncpg
import chromadb
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import json

load_dotenv()

# --- CONFIG ---
CHROMA_DIR = Path("c:/Users/Admn/Desktop/NEXO_SOBERANO/NEXO_SOBERANO/memoria_vectorial")
COLLECTION_NAME = "inteligencia_geopolitica"
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

async def migrate():
    print("Iniciando migracion de ChromaDB a Supabase...")
    
    # 1. Conectar a Chroma
    if not CHROMA_DIR.exists():
        print(f"Error: No se encontro el directorio de Chroma en {CHROMA_DIR}")
        return
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        col = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"Error obteniendo coleccion '{COLLECTION_NAME}': {e}")
        return

    data = col.get(include=['documents', 'metadatas', 'embeddings'])
    count = len(data['ids'])
    print(f"Encontrados {count} documentos en ChromaDB.")

    if count == 0:
        print("Nada que migrar.")
        return

    # 2. Conectar a Supabase
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error conectando a Supabase: {e}")
        return
    
    # 3. Migrar en lotes
    batch_size = 50
    migrated = 0
    errors = 0

    for i in range(0, count, batch_size):
        end = min(i + batch_size, count)
        batch_ids = data['ids'][i:end]
        batch_docs = data['documents'][i:end]
        batch_metas = data['metadatas'][i:end]
        batch_embs = data['embeddings'][i:end]

        async with conn.transaction():
            for j in range(len(batch_ids)):
                doc_id = batch_ids[j]
                content = batch_docs[j]
                meta = batch_metas[j]
                embedding = batch_embs[j]
                
                h = hashlib.sha256(content.encode()).hexdigest()
                emb_str = "[" + ",".join(map(str, embedding)) + "]"
                
                # Convert metadata dict to JSON string for asyncpg JSONB insert
                meta_json = json.dumps(meta)
                
                try:
                    await conn.execute("""
                        INSERT INTO public.nexo_documentos (content, metadata, embedding, hash_sha256)
                        VALUES ($1, $2, $3::vector, $4)
                        ON CONFLICT (hash_sha256) DO NOTHING
                    """, content, meta_json, emb_str, h)
                    migrated += 1
                except Exception as e:
                    print(f"Error migrando doc {doc_id}: {e}")
                    errors += 1

        print(f"Procesados {end}/{count}...")

    await conn.close()
    print("\nMIGRACION COMPLETADA")
    print(f"   - Migrados: {migrated}")
    print(f"   - Errores/Omitidos: {errors}")

if __name__ == "__main__":
    asyncio.run(migrate())
