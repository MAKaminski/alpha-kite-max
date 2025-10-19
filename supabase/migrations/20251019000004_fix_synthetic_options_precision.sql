-- Fix numeric field precision for synthetic options table
-- Drop and recreate the table with proper precision

-- Drop existing table and recreate with correct precision
DROP TABLE IF EXISTS synthetic_option_prices CASCADE;

-- Create synthetic options prices table with proper precision
CREATE TABLE IF NOT EXISTS synthetic_option_prices (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    option_type VARCHAR(5) NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
    strike_price DECIMAL(10,2) NOT NULL,
    expiration_date DATE NOT NULL,
    spot_price DECIMAL(10,2) NOT NULL,
    theoretical_price DECIMAL(15,6) NOT NULL,
    market_price DECIMAL(15,6) NOT NULL,
    bid DECIMAL(15,6),
    ask DECIMAL(15,6),
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    implied_volatility DECIMAL(12,6) NOT NULL,
    delta DECIMAL(12,6) NOT NULL,
    gamma DECIMAL(12,8) NOT NULL,
    theta DECIMAL(12,6) NOT NULL,
    vega DECIMAL(12,6) NOT NULL,
    time_to_expiry DECIMAL(8,6) NOT NULL,
    data_source VARCHAR(50) DEFAULT 'black_scholes_synthetic',
    risk_free_rate DECIMAL(6,4) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recreate indexes for efficient querying
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

-- Grant permissions
GRANT SELECT ON synthetic_option_prices TO authenticated;
GRANT INSERT ON synthetic_option_prices TO authenticated;
GRANT UPDATE ON synthetic_option_prices TO authenticated;
GRANT DELETE ON synthetic_option_prices TO authenticated;
