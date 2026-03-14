-- Migration: 002_create_conflict_indicators
-- Purpose: Almacenar métricas del Realismo Ofensivo (Polymarket, Heatmaps, Parásitos)

DROP TABLE IF EXISTS public.conflict_indicators CASCADE;

CREATE TABLE IF NOT EXISTS public.conflict_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country VARCHAR(100) NOT NULL,
    indicator_type VARCHAR(50) NOT NULL, -- 'polymarket', 'sentiment', 'parasite'
    score FLOAT NOT NULL, -- Escala de 0.0 a 1.0 (Probabilidad de colapso/Riesgo)
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- Indexing for fast regional scans
CREATE INDEX IF NOT EXISTS idx_conflict_indicators_country ON public.conflict_indicators(country);
CREATE INDEX IF NOT EXISTS idx_conflict_indicators_type ON public.conflict_indicators(indicator_type);
CREATE INDEX IF NOT EXISTS idx_conflict_indicators_date ON public.conflict_indicators(created_at);

-- RLS
ALTER TABLE public.conflict_indicators ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for conflict indicators"
    ON public.conflict_indicators FOR SELECT
    USING (true);

CREATE POLICY "Allow service role full access to conflict indicators"
    ON public.conflict_indicators FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');
