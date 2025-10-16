-- ============================================================================
-- APPLY ALL PENDING MIGRATIONS TO SUPABASE
-- Copy and paste this entire file into Supabase SQL Editor and run it
-- ============================================================================

-- Migration 1: Option Prices Table
-- ============================================================================

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

CREATE UNIQUE INDEX IF NOT EXISTS idx_option_prices_ticker_timestamp_type_strike_exp 
  ON option_prices (ticker, timestamp, option_type, strike_price, expiration_date);

CREATE INDEX IF NOT EXISTS idx_option_prices_timestamp 
  ON option_prices (timestamp DESC);

ALTER TABLE option_prices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON option_prices;
CREATE POLICY "Public read access" ON option_prices
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "Service role write access" ON option_prices;
CREATE POLICY "Service role write access" ON option_prices
  FOR ALL USING (auth.role() = 'service_role');

COMMENT ON TABLE option_prices IS 'Stores option chain data for nearest ATM strikes, updated every minute during market hours';


-- Migration 2: Trading Tables (Positions, Trades, Daily P&L)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ticker TEXT NOT NULL,
  option_symbol TEXT NOT NULL,
  option_type TEXT NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
  strike_price NUMERIC(10, 2) NOT NULL,
  expiration_date DATE NOT NULL,
  contracts INTEGER NOT NULL,
  entry_price NUMERIC(10, 4) NOT NULL,
  entry_credit NUMERIC(12, 2) NOT NULL,
  entry_timestamp TIMESTAMPTZ NOT NULL,
  exit_price NUMERIC(10, 4),
  exit_debit NUMERIC(12, 2),
  exit_timestamp TIMESTAMPTZ,
  profit_loss NUMERIC(12, 2),
  unrealized_pnl NUMERIC(12, 2),
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  option_symbol TEXT NOT NULL,
  option_type TEXT NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
  strike_price NUMERIC(10, 2) NOT NULL,
  expiration_date DATE NOT NULL,
  trade_type TEXT NOT NULL CHECK (trade_type IN ('BUY_TO_OPEN', 'SELL_TO_OPEN', 'BUY_TO_CLOSE', 'SELL_TO_CLOSE')),
  contracts INTEGER NOT NULL,
  price NUMERIC(10, 4) NOT NULL,
  total_value NUMERIC(12, 2) NOT NULL,
  trade_timestamp TIMESTAMPTZ NOT NULL,
  pnl NUMERIC(12, 2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily P&L table
CREATE TABLE IF NOT EXISTS daily_pnl (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ticker TEXT NOT NULL,
  trade_date DATE NOT NULL,
  realized_pnl NUMERIC(12, 2) DEFAULT 0,
  unrealized_pnl NUMERIC(12, 2) DEFAULT 0,
  total_pnl NUMERIC(12, 2) DEFAULT 0,
  win_count INTEGER DEFAULT 0,
  loss_count INTEGER DEFAULT 0,
  total_trades INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(ticker, trade_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_positions_ticker_status ON positions (ticker, status);
CREATE INDEX IF NOT EXISTS idx_positions_timestamp ON positions (entry_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_position_id ON trades (position_id);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades (trade_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_ticker_date ON trades (ticker, DATE(trade_timestamp));
CREATE INDEX IF NOT EXISTS idx_daily_pnl_ticker_date ON daily_pnl (ticker, trade_date DESC);

-- Enable RLS
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_pnl ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Public read access" ON positions;
DROP POLICY IF EXISTS "Public read access" ON trades;
DROP POLICY IF EXISTS "Public read access" ON daily_pnl;
DROP POLICY IF EXISTS "Service role write access" ON positions;
DROP POLICY IF EXISTS "Service role write access" ON trades;
DROP POLICY IF EXISTS "Service role write access" ON daily_pnl;

-- Public read access policies
CREATE POLICY "Public read access" ON positions FOR SELECT USING (true);
CREATE POLICY "Public read access" ON trades FOR SELECT USING (true);
CREATE POLICY "Public read access" ON daily_pnl FOR SELECT USING (true);

-- Service role write access
CREATE POLICY "Service role write access" ON positions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write access" ON trades FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role write access" ON daily_pnl FOR ALL USING (auth.role() = 'service_role');

-- Comments
COMMENT ON TABLE positions IS 'Tracks simulated option positions (open and closed)';
COMMENT ON TABLE trades IS 'Records all simulated trade executions';
COMMENT ON TABLE daily_pnl IS 'Aggregates daily trading performance metrics';

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS update_positions_updated_at ON positions;
DROP TRIGGER IF EXISTS update_daily_pnl_updated_at ON daily_pnl;

-- Triggers
CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_pnl_updated_at BEFORE UPDATE ON daily_pnl
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION QUERIES (run these after applying migrations)
-- ============================================================================

-- Verify tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('option_prices', 'positions', 'trades', 'daily_pnl')
ORDER BY table_name;

-- Check row counts
SELECT 'option_prices' as table_name, COUNT(*) as row_count FROM option_prices
UNION ALL
SELECT 'positions', COUNT(*) FROM positions
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'daily_pnl', COUNT(*) FROM daily_pnl;

