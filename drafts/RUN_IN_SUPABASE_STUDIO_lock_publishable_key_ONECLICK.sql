-- ============================================================================
-- LOCK THE PUBLISHABLE KEY OUT OF MISSION CONTROL DATA  (exo3 audit fix #1)
-- Run in: Supabase Studio → SQL Editor → project pcrgpuoljylqcumijvnw → Run
--
-- WHY: the publishable ("anon") key could read the whole CRM (7,191 contacts
-- pulled with it 9/27). As of 2026-09-27 the MC server, all 31 scripts, the
-- backup page and the Decisions Daily cron use the PRIVATE service_role key,
-- which is unaffected by this file. After it runs, the publishable key reads
-- and writes NOTHING.
--
-- Safe to re-run. Rollback is at the bottom.
-- ============================================================================

-- 1) Every public table: RLS on, and no access for anon/authenticated.
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', r.tablename);
    EXECUTE format('REVOKE ALL ON public.%I FROM anon, authenticated;', r.tablename);
  END LOOP;
END $$;

-- 2) Views + sequences too (covers anything that isn't a plain table).
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;

-- 3) New tables created later don't silently re-open the hole.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES    FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;

-- 4) service_role keeps full access (it bypasses RLS; this just makes the grant explicit).
GRANT ALL ON ALL TABLES    IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- 5) VERIFY — expect zero rows (no table readable by anon/authenticated).
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
ORDER BY 1, 2;

-- ── ROLLBACK (only if something breaks — restores read access for the publishable key) ──
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
-- DO $$ DECLARE r record; BEGIN
--   FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
--     EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY;', r.tablename);
--   END LOOP; END $$;
