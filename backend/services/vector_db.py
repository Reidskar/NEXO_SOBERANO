import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional

import asyncpg
from sentence_transformers import SentenceTransformer

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
# Leer desde variables de entorno. Usa DATABASE_URL de Supabase.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no encontrada en el entorno. Asegúrate de tenerla configurada.")

# Asegurar formato postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Usamos asyncpg connection pool
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool

# Modelo local (mismo que RAG service actual)
_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model

def get_embedding(text: str) -> List[float]:
    model = get_embed_model()
    return model.encode(text[:2000]).tolist()

async def ensure_table():
    """Verifica si la tabla nexo_documentos existe, si no, ejecuta el SQL"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verificar extensión
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Crear tabla (384 dimensiones para all-MiniLM-L6-v2)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.nexo_documentos (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb,
                embedding VECTOR(384),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                hash_sha256 TEXT UNIQUE
            );
        """)
        
        # Crear índice HNSW para búsqueda por similitud de coseno
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS nexo_documentos_embedding_idx 
            ON public.nexo_documentos 
            USING hnsw (embedding vector_cosine_ops);
        """)
        log.info("✅ Tabla nexo_documentos verificada en Supabase")

async def asimilar_documento(hash_sha256: str, contenido: str, metadata: dict):
    """
    Inserta o actualiza un documento y su embedding en Supabase.
    Equivalente a coleccion.add() en ChromaDB.
    """
    try:
        embedding = get_embedding(contenido)
        # Formato de pgvector para arrays: '[0.1, 0.2, ...]'
        # asyncpg convierte listas si la extensión vector está integrada, 
        # pero es más seguro pasarlo como string pre-formateado.
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        metadata_str = json.dumps(metadata)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO public.nexo_documentos (hash_sha256, content, metadata, embedding)
                VALUES ($1, $2, $3::jsonb, $4::vector)
                ON CONFLICT (hash_sha256) 
                DO UPDATE SET 
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding
            """, hash_sha256, contenido, metadata_str, embedding_str)
            
            log.info(f"✅ Documento asimilado: {metadata.get('archivo', hash_sha256)}")
            return True
            
    except Exception as e:
        log.error(f"❌ Error asimilando {hash_sha256}: {e}")
        return False

async def buscar_similares(query: str, k: int = 5, categoria: Optional[str] = None) -> List[Dict]:
    """
    Realiza una búsqueda semántica usando pgvector.
    Equivalente a coleccion.query() en ChromaDB.
    """
    try:
        query_embedding = get_embedding(query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            if categoria:
                # Búsqueda filtrada por categoría en metadata JSON
                rows = await conn.fetch("""
                    SELECT content, metadata, 1 - (embedding <=> $1::vector) as similarity
                    FROM public.nexo_documentos
                    WHERE metadata->>'categoria' = $2
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                """, embedding_str, categoria, k)
            else:
                # Búsqueda general
                rows = await conn.fetch("""
                    SELECT content, metadata, 1 - (embedding <=> $1::vector) as similarity
                    FROM public.nexo_documentos
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                """, embedding_str, k)
                
            resultados = []
            for row in rows:
                metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                resultados.append({
                    "content": row['content'],
                    "metadata": metadata,
                    "similarity": float(row['similarity'])
                })
                
            return resultados
            
    except Exception as e:
        log.error(f"❌ Error en búsqueda semántica: {e}")
        return []

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
