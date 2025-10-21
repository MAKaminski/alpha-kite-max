-- Streaming Service Optimizations
-- This migration adds optimizations for the Lightsail streaming service

-- Add partitioning for equity_data (optional, for large datasets)
-- Uncomment if you expect millions of rows and want to partition by month

-- CREATE EXTENSION IF NOT EXISTS pg_partman;
-- 
-- SELECT partman.create_parent(
--     p_parent_table := 'public.equity_data',
--     p_control := 'timestamp',
--     p_type := 'native',
--     p_interval := '1 month',
--     p_premake := 2
-- );

-- Add materialized view for quick stats (useful for dashboards)
CREATE MATERIALIZED VIEW IF NOT EXISTS equity_data_stats AS
SELECT 
    ticker,
    DATE(timestamp) AS trade_date,
    COUNT(*) AS tick_count,
    MIN(price) AS low_price,
    MAX(price) AS high_price,
    AVG(price) AS avg_price,
    SUM(volume) AS total_volume,
    MIN(timestamp) AS first_tick,
    MAX(timestamp) AS last_tick
FROM equity_data
GROUP BY ticker, DATE(timestamp);

-- Create index on the materialized view
CREATE UNIQUE INDEX idx_equity_stats_ticker_date 
ON equity_data_stats(ticker, trade_date DESC);

-- Add function to refresh stats (call this periodically)
CREATE OR REPLACE FUNCTION refresh_equity_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY equity_data_stats;
END;
$$ LANGUAGE plpgsql;

-- Add streaming metrics table
CREATE TABLE IF NOT EXISTS streaming_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ticker VARCHAR(10) NOT NULL,
    records_processed BIGINT NOT NULL,
    batch_size INTEGER,
    processing_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    service_status VARCHAR(20) DEFAULT 'running'
);

-- Create index for metrics queries
CREATE INDEX idx_streaming_metrics_timestamp 
ON streaming_metrics(timestamp DESC);

CREATE INDEX idx_streaming_metrics_ticker 
ON streaming_metrics(ticker, timestamp DESC);

-- Add comments
COMMENT ON MATERIALIZED VIEW equity_data_stats IS 'Aggregated daily statistics for equity data';
COMMENT ON TABLE streaming_metrics IS 'Metrics and health monitoring for streaming service';

-- Enable RLS for new tables
ALTER TABLE streaming_metrics ENABLE ROW LEVEL SECURITY;

-- Create policies for streaming_metrics
CREATE POLICY "Allow service role full access to streaming_metrics"
    ON streaming_metrics
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow anonymous read access to streaming_metrics"
    ON streaming_metrics
    FOR SELECT
    TO anon
    USING (true);

-- Add function to clean up old data (call via cron or manually)
CREATE OR REPLACE FUNCTION cleanup_old_equity_data(days_to_keep INTEGER DEFAULT 90)
RETURNS TABLE(deleted_count BIGINT) AS $$
DECLARE
    del_count BIGINT;
BEGIN
    DELETE FROM equity_data 
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS del_count = ROW_COUNT;
    
    RETURN QUERY SELECT del_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_equity_data IS 'Delete equity data older than specified days (default 90)';

-- Add function to get streaming health
CREATE OR REPLACE FUNCTION get_streaming_health(ticker_param VARCHAR DEFAULT NULL)
RETURNS TABLE(
    ticker VARCHAR,
    last_update TIMESTAMPTZ,
    records_last_hour BIGINT,
    avg_batch_size NUMERIC,
    error_rate NUMERIC,
    status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.ticker,
        MAX(m.timestamp) AS last_update,
        COUNT(*) AS records_last_hour,
        AVG(m.batch_size)::NUMERIC(10,2) AS avg_batch_size,
        (SUM(m.error_count)::NUMERIC / NULLIF(COUNT(*), 0) * 100)::NUMERIC(10,2) AS error_rate,
        CASE 
            WHEN MAX(m.timestamp) > NOW() - INTERVAL '5 minutes' THEN 'healthy'
            WHEN MAX(m.timestamp) > NOW() - INTERVAL '15 minutes' THEN 'warning'
            ELSE 'error'
        END AS status
    FROM streaming_metrics m
    WHERE m.timestamp > NOW() - INTERVAL '1 hour'
        AND (ticker_param IS NULL OR m.ticker = ticker_param)
    GROUP BY m.ticker;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_streaming_health IS 'Get streaming service health status for monitoring';

