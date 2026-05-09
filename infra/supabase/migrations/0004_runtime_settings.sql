-- Runtime overrides that the engine reads each heartbeat. Lets the dashboard
-- flip a small set of safety-critical config values WITHOUT a redeploy.
--
-- Usage: the engine SELECTs `runtime_settings.value` for known keys and
-- overlays them on the YAML-loaded config. Keys we currently support:
--
--   * dry_run_override   -- {"value": false} flips broker.dry_run from true
--                          to false at runtime (the live-enable gate).
--   * strategy_override  -- {"value": "sell_put_qqq_cross"} switches the
--                          active strategy without restarting.
--
-- Apply: psql "$SUPABASE_DB_URL" -f infra/supabase/migrations/0004_runtime_settings.sql

CREATE TABLE IF NOT EXISTS runtime_settings (
    key         TEXT         PRIMARY KEY,
    value       JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by  TEXT         NOT NULL DEFAULT 'system'
);

-- Enable RLS read for the anon key; writes still require service-role.
ALTER TABLE runtime_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS runtime_settings_anon_read ON runtime_settings;
CREATE POLICY runtime_settings_anon_read
    ON runtime_settings FOR SELECT
    TO anon
    USING (true);

-- Surface inserts/updates over Supabase Realtime so the dashboard can
-- reflect override changes without a refresh.
ALTER PUBLICATION supabase_realtime ADD TABLE runtime_settings;
