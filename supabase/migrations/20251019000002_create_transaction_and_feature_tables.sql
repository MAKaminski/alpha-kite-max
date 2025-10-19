-- Create transactions table for tracking every API call/action
CREATE TABLE IF NOT EXISTS public.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_type VARCHAR(50) NOT NULL, -- 'download_data', 'stream_data', 'place_order', etc.
    feature_name VARCHAR(100) NOT NULL,    -- 'historical_download', 'real_time_stream', 'option_download', etc.
    user_id VARCHAR(100),                  -- Optional: track by user
    ticker VARCHAR(10),                    -- Symbol being traded/downloaded
    parameters JSONB,                      -- Store request parameters (dates, strikes, etc.)
    status VARCHAR(20) NOT NULL,           -- 'success', 'failed', 'pending'
    error_message TEXT,                    -- Error details if failed
    rows_affected INTEGER,                 -- Number of rows downloaded/updated
    execution_time_ms INTEGER,             -- How long the operation took
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_transactions_feature ON public.transactions(feature_name, created_at DESC);
CREATE INDEX idx_transactions_type ON public.transactions(transaction_type, created_at DESC);
CREATE INDEX idx_transactions_status ON public.transactions(status, created_at DESC);
CREATE INDEX idx_transactions_ticker ON public.transactions(ticker, created_at DESC);
CREATE INDEX idx_transactions_created ON public.transactions(created_at DESC);

-- Add comment
COMMENT ON TABLE public.transactions IS 'Tracks every API call, download, trade, and system action for auditing and analytics';

-- Create feature_usage table for aggregated metrics
CREATE TABLE IF NOT EXISTS public.feature_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name VARCHAR(100) NOT NULL UNIQUE,
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    total_rows_processed BIGINT DEFAULT 0,
    avg_execution_time_ms INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    first_used_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index
CREATE INDEX idx_feature_usage_name ON public.feature_usage(feature_name);
CREATE INDEX idx_feature_usage_last_used ON public.feature_usage(last_used_at DESC);

-- Add comment
COMMENT ON TABLE public.feature_usage IS 'Aggregated metrics for each feature showing usage statistics';

-- Create view for daily feature usage stats
CREATE OR REPLACE VIEW public.feature_usage_daily AS
SELECT 
    feature_name,
    DATE(created_at) as usage_date,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE status = 'success') as successful_calls,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_calls,
    SUM(rows_affected) as total_rows,
    AVG(execution_time_ms)::INTEGER as avg_execution_ms,
    MIN(created_at) as first_call,
    MAX(created_at) as last_call
FROM public.transactions
GROUP BY feature_name, DATE(created_at)
ORDER BY usage_date DESC, total_calls DESC;

-- Create view for hourly feature usage (for real-time monitoring)
CREATE OR REPLACE VIEW public.feature_usage_hourly AS
SELECT 
    feature_name,
    DATE_TRUNC('hour', created_at) as usage_hour,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE status = 'success') as successful_calls,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_calls,
    AVG(execution_time_ms)::INTEGER as avg_execution_ms
FROM public.transactions
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY feature_name, DATE_TRUNC('hour', created_at)
ORDER BY usage_hour DESC, total_calls DESC;

-- Create view for feature performance metrics
CREATE OR REPLACE VIEW public.feature_performance AS
SELECT 
    feature_name,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE status = 'success') as successful_calls,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_calls,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'success') / NULLIF(COUNT(*), 0), 2) as success_rate,
    SUM(rows_affected) as total_rows_processed,
    AVG(execution_time_ms)::INTEGER as avg_execution_ms,
    MAX(execution_time_ms) as max_execution_ms,
    MIN(execution_time_ms) as min_execution_ms,
    MAX(created_at) as last_used_at,
    MIN(created_at) as first_used_at
FROM public.transactions
GROUP BY feature_name
ORDER BY total_calls DESC;

-- Function to update feature_usage aggregates
CREATE OR REPLACE FUNCTION update_feature_usage()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.feature_usage (
        feature_name,
        total_calls,
        successful_calls,
        failed_calls,
        total_rows_processed,
        avg_execution_time_ms,
        last_used_at,
        first_used_at,
        updated_at
    )
    SELECT 
        NEW.feature_name,
        1,
        CASE WHEN NEW.status = 'success' THEN 1 ELSE 0 END,
        CASE WHEN NEW.status = 'failed' THEN 1 ELSE 0 END,
        COALESCE(NEW.rows_affected, 0),
        COALESCE(NEW.execution_time_ms, 0),
        NEW.created_at,
        NEW.created_at,
        NOW()
    ON CONFLICT (feature_name) DO UPDATE SET
        total_calls = feature_usage.total_calls + 1,
        successful_calls = feature_usage.successful_calls + 
            CASE WHEN NEW.status = 'success' THEN 1 ELSE 0 END,
        failed_calls = feature_usage.failed_calls + 
            CASE WHEN NEW.status = 'failed' THEN 1 ELSE 0 END,
        total_rows_processed = feature_usage.total_rows_processed + COALESCE(NEW.rows_affected, 0),
        avg_execution_time_ms = (
            (feature_usage.avg_execution_time_ms * feature_usage.total_calls + COALESCE(NEW.execution_time_ms, 0)) 
            / (feature_usage.total_calls + 1)
        )::INTEGER,
        last_used_at = NEW.created_at,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update feature_usage
CREATE TRIGGER trigger_update_feature_usage
    AFTER INSERT ON public.transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_feature_usage();

-- Enable Row Level Security
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_usage ENABLE ROW LEVEL SECURITY;

-- Create policies for anonymous read access to views
CREATE POLICY "Allow anonymous read access to transactions"
    ON public.transactions FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anonymous read access to feature_usage"
    ON public.feature_usage FOR SELECT TO anon USING (true);

-- Create policies for service role full access
CREATE POLICY "Allow service role full access to transactions"
    ON public.transactions FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow service role full access to feature_usage"
    ON public.feature_usage FOR ALL TO service_role USING (true) WITH CHECK (true);

