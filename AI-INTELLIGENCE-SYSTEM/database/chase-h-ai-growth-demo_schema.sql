CREATE TABLE IF NOT EXISTS video_system_runs (
  id SERIAL PRIMARY KEY,
  slug TEXT NOT NULL,
  source_video TEXT NOT NULL,
  mode TEXT NOT NULL,
  final_decider TEXT NOT NULL,
  modo_ahorro BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);