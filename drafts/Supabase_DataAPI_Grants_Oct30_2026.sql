-- ============================================================================
-- Supabase Data API GRANTS — 2026-10-30 policy change
-- Run in: Supabase Studio → SQL Editor (project pcrgpuoljylqcumijvnw)
--
-- CONTEXT: From 2026-10-30, Supabase stops AUTO-granting Data API access to
-- NEW tables in the public schema. Existing tables are UNAFFECTED and keep all
-- current grants — nothing we run today breaks. This file is (A) a read-only
-- audit you can run anytime, and (B) the template to paste into any migration
-- that creates a new public table so it stays reachable via PostgREST /
-- supabase-js — including with the service_role key (all Exos crons use it).
--
-- NOTE: DDL/GRANTs cannot be run headless (no DB password / mgmt token / psql;
-- the REST service_role key can't do DDL). Studio SQL Editor is the only path.
-- ============================================================================

-- ── (A) AUDIT: list every public table missing anon/authenticated/service_role
--        access (read-only; run this first). Empty result = nothing to fix.
SELECT t.tablename,
       bool_or(g.grantee = 'anon')          AS has_anon,
       bool_or(g.grantee = 'authenticated')  AS has_authenticated,
       bool_or(g.grantee = 'service_role')   AS has_service_role
FROM pg_tables t
LEFT JOIN information_schema.role_table_grants g
       ON g.table_schema = 'public'
      AND g.table_name   = t.tablename
      AND g.grantee IN ('anon','authenticated','service_role')
WHERE t.schemaname = 'public'
GROUP BY t.tablename
HAVING NOT (bool_or(g.grantee = 'anon')
        AND bool_or(g.grantee = 'authenticated')
        AND bool_or(g.grantee = 'service_role'))
ORDER BY t.tablename;

-- ── (B) TEMPLATE: paste into the SAME migration that creates a new table.
--        Replace your_table. Idempotent — safe to re-run.
-- GRANT SELECT                         ON public.your_table TO anon;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.your_table TO authenticated;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.your_table TO service_role;

-- ── (C) OPTIONAL belt-and-suspenders: grant ALL public tables in one shot.
--        Existing tables already have grants, so this is a no-op today; run it
--        only if the (A) audit ever returns rows.
-- DO $$
-- DECLARE r record;
-- BEGIN
--   FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
--     EXECUTE format('GRANT SELECT ON public.%I TO anon;', r.tablename);
--     EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO authenticated;', r.tablename);
--     EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO service_role;', r.tablename);
--   END LOOP;
-- END $$;
