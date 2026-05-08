-- Enable Supabase Realtime for the tables the /status page subscribes to.
-- Without this, Postgres logical-replication doesn't include these tables in
-- the realtime publication, so anon clients never see INSERT events.
--
-- Apply: psql "$SUPABASE_DB_URL" -f infra/supabase/migrations/0003_realtime_publication.sql

-- The publication is named "supabase_realtime" by Supabase convention.
-- Tables added here will broadcast INSERT/UPDATE/DELETE to subscribed clients.

ALTER PUBLICATION supabase_realtime ADD TABLE audit_log;
ALTER PUBLICATION supabase_realtime ADD TABLE bars;
ALTER PUBLICATION supabase_realtime ADD TABLE signals;
ALTER PUBLICATION supabase_realtime ADD TABLE order_intents;
ALTER PUBLICATION supabase_realtime ADD TABLE fills;
ALTER PUBLICATION supabase_realtime ADD TABLE positions;
ALTER PUBLICATION supabase_realtime ADD TABLE daily_pnl;

-- The RLS read policies from migration 0002 already permit anon SELECTs on
-- these tables, which Realtime requires for clients to receive the events.
