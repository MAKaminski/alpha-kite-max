-- Create equity_data table
CREATE TABLE IF NOT EXISTS public.equity_data (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create composite index on ticker and timestamp for efficient queries
CREATE INDEX idx_equity_ticker_timestamp ON public.equity_data(ticker, timestamp DESC);

-- Create index on timestamp alone for time-based queries
CREATE INDEX idx_equity_timestamp ON public.equity_data(timestamp DESC);

-- Create unique constraint to prevent duplicate entries
CREATE UNIQUE INDEX idx_equity_unique ON public.equity_data(ticker, timestamp);

-- Add comment to table
COMMENT ON TABLE public.equity_data IS 'Stores minute-level equity price and volume data';

-- Create indicators table
CREATE TABLE IF NOT EXISTS public.indicators (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    sma9 DECIMAL(10, 2),
    vwap DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create composite index on ticker and timestamp
CREATE INDEX idx_indicators_ticker_timestamp ON public.indicators(ticker, timestamp DESC);

-- Create index on timestamp alone
CREATE INDEX idx_indicators_timestamp ON public.indicators(timestamp DESC);

-- Create unique constraint
CREATE UNIQUE INDEX idx_indicators_unique ON public.indicators(ticker, timestamp);

-- Add comment to table
COMMENT ON TABLE public.indicators IS 'Stores calculated technical indicators (SMA9, VWAP) for equities';

-- Enable Row Level Security (RLS)
ALTER TABLE public.equity_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.indicators ENABLE ROW LEVEL SECURITY;

-- Create policy to allow anonymous read access (for dashboard)
CREATE POLICY "Allow anonymous read access to equity_data"
    ON public.equity_data
    FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "Allow anonymous read access to indicators"
    ON public.indicators
    FOR SELECT
    TO anon
    USING (true);

-- Create policy to allow service role full access (for backend services)
CREATE POLICY "Allow service role full access to equity_data"
    ON public.equity_data
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access to indicators"
    ON public.indicators
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

