-- Migración: 001_create_live_schedule_and_policies.sql
-- Propósito: Configurar el esquema global de inteligencia en Supabase.

-- 1. Tabla de Credenciales OAuth
CREATE TABLE IF NOT EXISTS public.oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    refresh_token TEXT,
    access_token TEXT,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Tabla de Documentos Vectorizados (Semántica)
CREATE TABLE IF NOT EXISTS public.nexo_documentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id INTEGER REFERENCES public.evidencia(id),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(1536), -- Ajustado para OpenAI (1536) o Supabase.ai (384)
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Tabla de Programación Live / Publicaciones
CREATE TABLE IF NOT EXISTS public.live_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT,
    data JSONB,
    status TEXT DEFAULT 'pending',
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Políticas RLS (Seguridad)
ALTER TABLE public.evidencia ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nexo_documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.live_schedule ENABLE ROW LEVEL SECURITY;

-- Política: Solo lectura para usuarios autenticados, escritura para el service_role (Edge Functions)
CREATE POLICY "Select_Authenticated" ON public.evidencia FOR SELECT TO authenticated USING (true);
CREATE POLICY "Select_Documents_Authenticated" ON public.nexo_documentos FOR SELECT TO authenticated USING (true);

-- 5. Índices de Búsqueda
CREATE INDEX IF NOT EXISTS idx_evidencia_categoria ON public.evidencia(categoria);
CREATE INDEX IF NOT EXISTS idx_nexo_docs_metadata ON public.nexo_documentos USING gin (metadata);
