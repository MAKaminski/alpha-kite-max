-- Create synthetic options prices table for Black-Scholes generated data
-- This table mirrors the structure of the real options data but with additional fields
-- to distinguish synthetic data from real market data

CREATE TABLE IF NOT EXISTS synthetic_option_prices (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    option_type VARCHAR(5) NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
    strike_price DECIMAL(10,2) NOT NULL,
    expiration_date DATE NOT NULL,
    spot_price DECIMAL(10,2) NOT NULL,
    theoretical_price DECIMAL(10,4) NOT NULL,
    market_price DECIMAL(10,4) NOT NULL,
    bid DECIMAL(10,4),
    ask DECIMAL(10,4),
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    implied_volatility DECIMAL(8,4) NOT NULL,
    delta DECIMAL(8,4) NOT NULL,
    gamma DECIMAL(8,6) NOT NULL,
    theta DECIMAL(8,4) NOT NULL,
    vega DECIMAL(8,4) NOT NULL,
    time_to_expiry DECIMAL(8,6) NOT NULL,
    data_source VARCHAR(50) DEFAULT 'black_scholes_synthetic',
    risk_free_rate DECIMAL(6,4) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_synthetic_options_timestamp ON synthetic_option_prices(timestamp);
CREATE INDEX IF NOT EXISTS idx_synthetic_options_ticker ON synthetic_option_prices(ticker);
CREATE INDEX IF NOT EXISTS idx_synthetic_options_expiration ON synthetic_option_prices(expiration_date);
CREATE INDEX IF NOT EXISTS idx_synthetic_options_strike ON synthetic_option_prices(strike_price);
CREATE INDEX IF NOT EXISTS idx_synthetic_options_type ON synthetic_option_prices(option_type);
CREATE INDEX IF NOT EXISTS idx_synthetic_options_data_source ON synthetic_option_prices(data_source);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_synthetic_options_ticker_date ON synthetic_option_prices(ticker, expiration_date);
CREATE INDEX IF NOT EXISTS idx_synthetic_options_ticker_strike ON synthetic_option_prices(ticker, strike_price);

-- Add RLS (Row Level Security) policies
ALTER TABLE synthetic_option_prices ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read synthetic options data
CREATE POLICY "Allow authenticated users to read synthetic options data" ON synthetic_option_prices
    FOR SELECT TO authenticated
    USING (true);

-- Allow authenticated users to insert synthetic options data
CREATE POLICY "Allow authenticated users to insert synthetic options data" ON synthetic_option_prices
    FOR INSERT TO authenticated
    WITH CHECK (true);

-- Allow authenticated users to update synthetic options data
CREATE POLICY "Allow authenticated users to update synthetic options data" ON synthetic_option_prices
    FOR UPDATE TO authenticated
    USING (true)
    WITH CHECK (true);

-- Allow authenticated users to delete synthetic options data
CREATE POLICY "Allow authenticated users to delete synthetic options data" ON synthetic_option_prices
    FOR DELETE TO authenticated
    USING (true);

-- Create a view that combines real and synthetic options data
CREATE OR REPLACE VIEW all_option_prices AS
SELECT 
    id,
    timestamp,
    ticker,
    option_symbol,
    option_type,
    strike_price,
    expiration_date,
    spot_price,
    last_price as market_price,
    bid,
    ask,
    volume,
    open_interest,
    implied_volatility,
    delta,
    gamma,
    theta,
    vega,
    'real_market_data' as data_source,
    created_at,
    updated_at
FROM option_prices
UNION ALL
SELECT 
    id,
    timestamp,
    ticker,
    option_symbol,
    option_type,
    strike_price,
    expiration_date,
    spot_price,
    market_price,
    bid,
    ask,
    volume,
    open_interest,
    implied_volatility,
    delta,
    gamma,
    theta,
    vega,
    data_source,
    created_at,
    updated_at
FROM synthetic_option_prices;

-- Add RLS policy for the view
ALTER VIEW all_option_prices SET (security_invoker = true);

-- Create a function to get options data by date range with data source indication
CREATE OR REPLACE FUNCTION get_options_data_by_date_range(
    p_ticker VARCHAR(10),
    p_start_date DATE,
    p_end_date DATE,
    p_data_source VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE (
    timestamp TIMESTAMPTZ,
    ticker VARCHAR(10),
    option_symbol VARCHAR(50),
    option_type VARCHAR(5),
    strike_price DECIMAL(10,2),
    expiration_date DATE,
    spot_price DECIMAL(10,2),
    market_price DECIMAL(10,4),
    bid DECIMAL(10,4),
    ask DECIMAL(10,4),
    volume INTEGER,
    open_interest INTEGER,
    implied_volatility DECIMAL(8,4),
    delta DECIMAL(8,4),
    gamma DECIMAL(8,6),
    theta DECIMAL(8,4),
    vega DECIMAL(8,4),
    data_source VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.timestamp,
        o.ticker,
        o.option_symbol,
        o.option_type,
        o.strike_price,
        o.expiration_date,
        o.spot_price,
        o.market_price,
        o.bid,
        o.ask,
        o.volume,
        o.open_interest,
        o.implied_volatility,
        o.delta,
        o.gamma,
        o.theta,
        o.vega,
        o.data_source
    FROM all_option_prices o
    WHERE o.ticker = p_ticker
        AND o.expiration_date >= p_start_date
        AND o.expiration_date <= p_end_date
        AND (p_data_source IS NULL OR o.data_source = p_data_source)
    ORDER BY o.timestamp, o.strike_price, o.option_type;
END;
$$;

-- Grant permissions
GRANT SELECT ON synthetic_option_prices TO authenticated;
GRANT INSERT ON synthetic_option_prices TO authenticated;
GRANT UPDATE ON synthetic_option_prices TO authenticated;
GRANT DELETE ON synthetic_option_prices TO authenticated;
GRANT SELECT ON all_option_prices TO authenticated;
GRANT EXECUTE ON FUNCTION get_options_data_by_date_range TO authenticated;
