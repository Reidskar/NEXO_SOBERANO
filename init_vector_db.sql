-- Migración de Supabase Vector (pgvector)
-- Este script activa pgvector y crea la tabla para almacenar la memoria de NEXO SOBERANO

-- 1. Habilitar la extensión vectorial (esto requiere privilegios de superusuario, que Supabase otorga)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Crear la tabla principal de documentos
CREATE TABLE IF NOT EXISTS public.nexo_documentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Dimensionamos a 384 porque all-MiniLM-L6-v2 de sentence-transformers arroja 384 dimensiones.
    -- Si migramos a OpenAI o Gemini más tarde, ajustar a 1536 o 768 según modelo.
    embedding VECTOR(384),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    hash_sha256 TEXT UNIQUE
);

-- 3. Crear índice RLS (Row Level Security) - por ahora desactivado para que el backend pueda escribir
ALTER TABLE public.nexo_documentos DISABLE ROW LEVEL SECURITY;

-- 4. Crear índice HNSW o IVFFLAT para acelerar las búsquedas (opcional para bd muy grandes pero recomendado)
-- El tamaño de la lista de IVFFLAT depende del nro de filas. HNSW es más moderno en pgvector >= 0.5.0
CREATE INDEX IF NOT EXISTS nexo_documentos_embedding_idx 
ON public.nexo_documentos 
USING hnsw (embedding vector_cosine_ops);

-- Nota: Si usas Supabase free tier y metes millones de vectores, el índice hnsw usará mucha RAM.
-- Si hay problemas de memoria con hnsw, se puede usar:
-- CREATE INDEX ON public.nexo_documentos USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
