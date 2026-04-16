-- ============================================================
-- NEXO SOBERANO — Vector DB Schema
-- Modelo: gemini-embedding-exp-03-07 (Gemini Embedding 2)
-- Dimensiones: 768 — primary store: Qdrant, pgvector es fallback
-- ============================================================

-- 1. Extensión pgvector (opcional — solo si está instalada en la imagen)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
        CREATE EXTENSION IF NOT EXISTS vector;
    END IF;
END
$$;

-- 2. Tabla principal de documentos vectorizados
--    Si pgvector no está disponible, el campo embedding se almacena como TEXT (JSON array)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE TABLE IF NOT EXISTS public.nexo_documentos (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            content      TEXT        NOT NULL,
            metadata     JSONB       NOT NULL DEFAULT '{}'::jsonb,
            embedding    VECTOR(768),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            hash_sha256  TEXT        UNIQUE,
            categoria    TEXT        GENERATED ALWAYS AS (metadata->>'categoria') STORED,
            fuente       TEXT        GENERATED ALWAYS AS (metadata->>'fuente') STORED
        );
    ELSE
        -- Tabla sin tipo VECTOR (fallback — Qdrant maneja los embeddings reales)
        CREATE TABLE IF NOT EXISTS public.nexo_documentos (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            content      TEXT        NOT NULL,
            metadata     JSONB       NOT NULL DEFAULT '{}'::jsonb,
            embedding    TEXT,                       -- JSON array como fallback
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            hash_sha256  TEXT        UNIQUE,
            categoria    TEXT        GENERATED ALWAYS AS (metadata->>'categoria') STORED,
            fuente       TEXT        GENERATED ALWAYS AS (metadata->>'fuente') STORED
        );
    END IF;
END
$$;

-- 3. Trigger: actualiza updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS nexo_documentos_updated_at ON public.nexo_documentos;
CREATE TRIGGER nexo_documentos_updated_at
    BEFORE UPDATE ON public.nexo_documentos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 4. Índice HNSW (solo si pgvector disponible)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        DROP INDEX IF EXISTS nexo_documentos_embedding_hnsw;
        EXECUTE 'CREATE INDEX nexo_documentos_embedding_hnsw
                 ON public.nexo_documentos
                 USING hnsw (embedding vector_cosine_ops)
                 WITH (m = 16, ef_construction = 64)';
    END IF;
END
$$;

-- 5. Índices generales
CREATE INDEX IF NOT EXISTS nexo_documentos_metadata_gin
    ON public.nexo_documentos USING gin (metadata);
CREATE INDEX IF NOT EXISTS nexo_documentos_categoria_idx ON public.nexo_documentos (categoria);
CREATE INDEX IF NOT EXISTS nexo_documentos_fuente_idx    ON public.nexo_documentos (fuente);
CREATE INDEX IF NOT EXISTS nexo_documentos_created_idx   ON public.nexo_documentos (created_at DESC);

ALTER TABLE public.nexo_documentos DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.nexo_documentos IS
    'Memoria semántica de NEXO SOBERANO. Vector store primario: Qdrant. Fallback: pgvector si disponible.';
