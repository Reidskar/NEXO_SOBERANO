-- ============================================================
-- NEXO SOBERANO — PostgreSQL init script
-- Ejecutado por Docker en el primer arranque del contenedor.
-- Variables: POSTGRES_DB, POSTGRES_USER ya creadas por la imagen.
-- ============================================================

-- 1. Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- búsqueda por similitud de texto
CREATE EXTENSION IF NOT EXISTS "unaccent";   -- normalización sin acentos

-- 2. Permisos al usuario principal
GRANT ALL PRIVILEGES ON DATABASE nexo TO nexo;
ALTER USER nexo CREATEDB;

-- 3. Esquema público — asegurar acceso
GRANT ALL ON SCHEMA public TO nexo;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO nexo;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO nexo;

-- 4. Tabla de evidencia (fuente de verdad documental)
CREATE TABLE IF NOT EXISTS public.evidencia (
    id              SERIAL      PRIMARY KEY,
    hash_sha256     TEXT        UNIQUE NOT NULL,
    nombre_archivo  TEXT,
    ruta_local      TEXT,
    link_nube       TEXT,
    dominio         TEXT,
    categoria       TEXT,
    resumen_ia      TEXT,
    fecha_ingesta   TIMESTAMPTZ NOT NULL DEFAULT now(),
    nivel_confianza REAL        DEFAULT 0.8,
    impacto         TEXT,
    vectorizado     BOOLEAN     NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_evidencia_categoria   ON public.evidencia (categoria);
CREATE INDEX IF NOT EXISTS idx_evidencia_dominio     ON public.evidencia (dominio);
CREATE INDEX IF NOT EXISTS idx_evidencia_ingesta     ON public.evidencia (fecha_ingesta DESC);

-- 5. Tabla de consultas/sesiones RAG
CREATE TABLE IF NOT EXISTS public.consultas (
    id          BIGSERIAL   PRIMARY KEY,
    fecha       TIMESTAMPTZ NOT NULL DEFAULT now(),
    pregunta    TEXT        NOT NULL,
    respuesta   TEXT,
    fuentes     JSONB       DEFAULT '[]'::jsonb,
    chunks      INTEGER     DEFAULT 0,
    ms          INTEGER     DEFAULT 0,
    modelo      TEXT        DEFAULT 'gemini-2.0-flash'
);

CREATE INDEX IF NOT EXISTS idx_consultas_fecha ON public.consultas (fecha DESC);

-- 6. Tabla de alertas del sistema
CREATE TABLE IF NOT EXISTS public.alertas (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    level      TEXT        NOT NULL CHECK (level IN ('info','warning','error','critical')),
    source     TEXT        NOT NULL,
    title      TEXT        NOT NULL,
    body       TEXT,
    meta       JSONB       DEFAULT '{}'::jsonb,
    leida      BOOLEAN     NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alertas_level      ON public.alertas (level);
CREATE INDEX IF NOT EXISTS idx_alertas_created_at ON public.alertas (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alertas_leida      ON public.alertas (leida) WHERE NOT leida;

-- 7. Tabla de indicadores de conflicto (Realismo Ofensivo)
CREATE TABLE IF NOT EXISTS public.conflict_indicators (
    id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    country        TEXT    NOT NULL,
    indicator_type TEXT    NOT NULL,
    score          FLOAT   NOT NULL CHECK (score BETWEEN 0.0 AND 1.0),
    metadata       JSONB   DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conflict_country  ON public.conflict_indicators (country);
CREATE INDEX IF NOT EXISTS idx_conflict_type     ON public.conflict_indicators (indicator_type);
CREATE INDEX IF NOT EXISTS idx_conflict_date     ON public.conflict_indicators (created_at DESC);

-- 8. Tabla de seguimiento de costos API
CREATE TABLE IF NOT EXISTS public.costos_api (
    id           BIGSERIAL   PRIMARY KEY,
    fecha        DATE        NOT NULL DEFAULT CURRENT_DATE,
    proveedor    TEXT        NOT NULL DEFAULT 'gemini',
    modelo       TEXT,
    total_tokens BIGINT      DEFAULT 0,
    total_costo  NUMERIC(10,6) DEFAULT 0,
    UNIQUE (fecha, proveedor, modelo)
);

-- Nota: pgvector se instala en 02_vector.sql (init_vector_db.sql)
-- Nota: La extensión pg_cron debe activarse desde Supabase Dashboard en producción.
