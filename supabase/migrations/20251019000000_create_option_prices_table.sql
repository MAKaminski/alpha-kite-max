-- Create option_prices table for 0DTE options tracking
CREATE TABLE IF NOT EXISTS public.option_prices (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
    strike_price DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    last_price DECIMAL(10, 4),
    bid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    volume BIGINT,
    open_interest BIGINT,
    implied_volatility DECIMAL(10, 4),
    delta DECIMAL(10, 4),
    gamma DECIMAL(10, 4),
    theta DECIMAL(10, 4),
    vega DECIMAL(10, 4),
    option_symbol VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create composite index on ticker, timestamp, and option details for efficient queries
CREATE INDEX idx_option_prices_ticker_timestamp ON public.option_prices(ticker, timestamp DESC);

-- Create index for querying by expiration date (for 0DTE specifically)
CREATE INDEX idx_option_prices_expiration ON public.option_prices(expiration_date);

-- Create index for strike price queries
CREATE INDEX idx_option_prices_strike ON public.option_prices(ticker, strike_price);

-- Create unique constraint to prevent duplicate entries
CREATE UNIQUE INDEX idx_option_prices_unique ON public.option_prices(
    ticker, timestamp, option_type, strike_price, expiration_date
);

-- Add comment to table
COMMENT ON TABLE public.option_prices IS 'Stores option pricing data, particularly for 0DTE (zero days to expiration) options';

-- Enable Row Level Security (RLS)
ALTER TABLE public.option_prices ENABLE ROW LEVEL SECURITY;

-- Create policy to allow anonymous read access (for dashboard)
CREATE POLICY "Allow anonymous read access to option_prices"
    ON public.option_prices
    FOR SELECT
    TO anon
    USING (true);

-- Create policy to allow service role full access (for backend services)
CREATE POLICY "Allow service role full access to option_prices"
    ON public.option_prices
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

