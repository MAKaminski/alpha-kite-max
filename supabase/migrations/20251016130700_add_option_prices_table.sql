-- Add option_prices table for tracking option chain data
CREATE TABLE IF NOT EXISTS option_prices (
  id BIGSERIAL PRIMARY KEY,
  ticker TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  option_type TEXT NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
  strike_price NUMERIC(10, 2) NOT NULL,
  expiration_date DATE NOT NULL,
  bid NUMERIC(10, 4),
  ask NUMERIC(10, 4),
  last NUMERIC(10, 4),
  volume BIGINT,
  open_interest BIGINT,
  implied_volatility NUMERIC(10, 6),
  delta NUMERIC(10, 6),
  gamma NUMERIC(10, 6),
  theta NUMERIC(10, 6),
  vega NUMERIC(10, 6),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient queries
CREATE UNIQUE INDEX IF NOT EXISTS idx_option_prices_ticker_timestamp_type_strike_exp 
  ON option_prices (ticker, timestamp, option_type, strike_price, expiration_date);

CREATE INDEX IF NOT EXISTS idx_option_prices_timestamp 
  ON option_prices (timestamp DESC);

-- Enable RLS
ALTER TABLE option_prices ENABLE ROW LEVEL SECURITY;

-- Public read access policy
CREATE POLICY "Public read access" ON option_prices
  FOR SELECT USING (true);

-- Service role write access (backend only)
CREATE POLICY "Service role write access" ON option_prices
  FOR ALL USING (auth.role() = 'service_role');

-- Add comment
COMMENT ON TABLE option_prices IS 'Stores option chain data for nearest ATM strikes, updated every minute during market hours';

