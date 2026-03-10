-- Tablas para el sistema de alertas profesionales

CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level TEXT NOT NULL, -- 'info', 'warning', 'error', 'critical'
    source TEXT NOT NULL, -- 'nexo-bot', 'supabase-prober', etc.
    title TEXT NOT NULL,
    body TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para búsqueda rápida
CREATE INDEX IF NOT EXISTS idx_alerts_level ON public.alerts(level);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON public.alerts(created_at DESC);

COMMENT ON TABLE public.alerts IS 'Registro persistente de alertas del sistema NEXO';
