-- Migración: 003_admin_user_and_cleanup.sql
-- Propósito: Crear usuario admin, limpiar tabla duplicada alerts, activar pg_cron

-- ══════════════════════════════════════════════════════════
-- 1. CREAR USUARIO ADMIN EN public.users
--    Requiere que primero exista en auth.users (Supabase Auth)
--    Reemplaza 'TU-AUTH-UUID' con el UUID de tu usuario en Auth > Users
-- ══════════════════════════════════════════════════════════
INSERT INTO public.users (id, email, role, created_at)
VALUES (
  'TU-AUTH-UUID',   -- reemplazar con UUID real de auth.users
  'admin@elanarcocapital.com',
  'admin',
  now()
)
ON CONFLICT (id) DO UPDATE SET role = 'admin';

-- ══════════════════════════════════════════════════════════
-- 2. LIMPIAR TABLA DUPLICADA: alerts (vacía) vs alertas (5 filas)
--    Renombramos alerts → alerts_legacy y la vaciamos,
--    o simplemente la eliminamos si no hay foreign keys
-- ══════════════════════════════════════════════════════════

-- Verificar antes de borrar (ejecutar primero como SELECT, luego DROP):
-- SELECT COUNT(*) FROM public.alerts;

DROP TABLE IF EXISTS public.alerts CASCADE;

-- Crear vista para unificar nombre (opcional - compatibilidad):
-- CREATE VIEW public.alerts AS SELECT * FROM public.alertas;

-- ══════════════════════════════════════════════════════════
-- 3. ACTIVAR pg_cron (requiere superuser / Supabase Dashboard)
--    Ir a: Database > Extensions > pg_cron → activar
--    Luego ejecutar esto:
-- ══════════════════════════════════════════════════════════

-- Limpieza diaria de consultas antiguas (>30 días)
-- SELECT cron.schedule(
--   'cleanup-old-queries',
--   '0 3 * * *',
--   $$DELETE FROM public.consultas WHERE created_at < now() - interval '30 days'$$
-- );

-- Cost tracking diario - resumen
-- SELECT cron.schedule(
--   'daily-cost-summary',
--   '0 0 * * *',
--   $$INSERT INTO public.costos_api (fecha, total_tokens, total_costo)
--     SELECT CURRENT_DATE - 1, SUM(tokens), SUM(costo)
--     FROM public.consultas
--     WHERE DATE(created_at) = CURRENT_DATE - 1$$
-- );

-- ══════════════════════════════════════════════════════════
-- 4. SESIONES Y CONVERSACIONES - habilitar escritura
--    (las tablas existen pero están vacías por falta de RLS permisiva)
-- ══════════════════════════════════════════════════════════
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mensajes ENABLE ROW LEVEL SECURITY;

-- Permitir inserción desde el backend (service_role bypassa RLS por defecto)
-- Si usas anon key desde el frontend, necesitas estas políticas:
CREATE POLICY IF NOT EXISTS "service_role_all_sessions"
  ON public.sessions FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "service_role_all_conversaciones"
  ON public.conversaciones FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "service_role_all_mensajes"
  ON public.mensajes FOR ALL TO service_role USING (true) WITH CHECK (true);
