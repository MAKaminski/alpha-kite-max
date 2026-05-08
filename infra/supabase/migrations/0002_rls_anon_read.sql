-- Read-only access for the anon role used by the public dashboard.
-- Service-role writes (engine, market-data-stream) are unaffected because
-- service_role bypasses RLS automatically.
--
-- Apply: psql "$SUPABASE_DB_URL" -f infra/supabase/migrations/0002_rls_anon_read.sql

ALTER TABLE audit_log    ENABLE ROW LEVEL SECURITY;
ALTER TABLE bars         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals      ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE fills        ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_pnl    ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies   ENABLE ROW LEVEL SECURITY;

-- Drop existing anon-read policies if re-running this migration.
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables
           WHERE schemaname='public'
             AND tablename IN (
               'audit_log','bars','ticks','signals','order_intents',
               'fills','positions','daily_pnl','strategies'
             )
  LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS %I ON %I',
      'anon_read_' || t, t
    );
  END LOOP;
END$$;

-- Anon (and authenticated) can SELECT every row. Writes still require service_role.
CREATE POLICY anon_read_audit_log    ON audit_log    FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_bars         ON bars         FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_ticks        ON ticks        FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_signals      ON signals      FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_order_intents ON order_intents FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_fills        ON fills        FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_positions    ON positions    FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_daily_pnl    ON daily_pnl    FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_strategies   ON strategies   FOR SELECT TO anon, authenticated USING (true);
