-- ============================================================================
-- APPLY ALL MIGRATIONS TO SUPABASE
-- ============================================================================
-- Run this in Supabase SQL Editor to apply all pending migrations
-- Dashboard → SQL Editor → New Query → Paste this entire file → Run
-- ============================================================================

-- Migration 1: Create equity and indicators tables
-- File: 20251015151016_create_equity_and_indicators_tables.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS equity_data (
  id BIGSERIAL PRIMARY KEY,
  ticker TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  price NUMERIC(10, 2) NOT NULL,
  volume BIGINT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_equity_data_ticker_timestamp 
  ON equity_data (ticker, timestamp DESC);

CREATE TABLE IF NOT EXISTS indicators (
  id BIGSERIAL PRIMARY KEY,
  ticker TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  sma9 NUMERIC(10, 2),
  vwap NUMERIC(10, 2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_indicators_ticker_timestamp 
  ON indicators (ticker, timestamp DESC);

ALTER TABLE equity_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicators ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Public read access" ON equity_data
  FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Service role write access" ON equity_data
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY IF NOT EXISTS "Public read access" ON indicators
  FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Service role write access" ON indicators
  FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- Migration 2: Add option prices table
-- File: 20251016130700_add_option_prices_table.sql
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

CREATE POLICY IF NOT EXISTS "Public read access for option_prices" ON option_prices
  FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Service role write access for option_prices" ON option_prices
  FOR ALL USING (auth.role() = 'service_role');

COMMENT ON TABLE option_prices IS 'Stores option chain data for nearest ATM strikes, updated every minute during market hours';

-- ============================================================================
-- Migration 3: Add trading tables (positions, trades, daily_pnl)
-- File: 20251016131000_add_trading_tables.sql
-- ============================================================================

-- Note: Check if 20250116000000_create_trading_tables.sql is similar/duplicate

CREATE TABLE IF NOT EXISTS positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  option_symbol TEXT NOT NULL,
  option_type TEXT NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
  strike_price NUMERIC(10, 2) NOT NULL,
  expiration_date DATE NOT NULL,
  contracts INTEGER NOT NULL,
  entry_price NUMERIC(10, 4) NOT NULL,
  entry_credit NUMERIC(10, 2) NOT NULL,
  entry_timestamp TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('OPEN', 'CLOSED')) DEFAULT 'OPEN',
  exit_price NUMERIC(10, 4),
  exit_debit NUMERIC(10, 2),
  exit_timestamp TIMESTAMPTZ,
  profit_loss NUMERIC(10, 2),
  unrealized_pnl NUMERIC(10, 2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_ticker_status 
  ON positions (ticker, status);

CREATE INDEX IF NOT EXISTS idx_positions_entry_timestamp 
  ON positions (entry_timestamp DESC);

CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  position_id UUID REFERENCES positions(id),
  ticker TEXT NOT NULL,
  option_symbol TEXT NOT NULL,
  option_type TEXT NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
  strike_price NUMERIC(10, 2) NOT NULL,
  expiration_date DATE NOT NULL,
  trade_type TEXT NOT NULL CHECK (trade_type IN ('SELL_TO_OPEN', 'BUY_TO_CLOSE')),
  contracts INTEGER NOT NULL,
  price NUMERIC(10, 4) NOT NULL,
  trade_timestamp TIMESTAMPTZ NOT NULL,
  pnl NUMERIC(10, 2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_ticker_timestamp 
  ON trades (ticker, trade_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_trades_position_id 
  ON trades (position_id);

CREATE TABLE IF NOT EXISTS daily_pnl (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  trade_date DATE NOT NULL,
  realized_pnl NUMERIC(10, 2) DEFAULT 0,
  unrealized_pnl NUMERIC(10, 2) DEFAULT 0,
  total_pnl NUMERIC(10, 2) DEFAULT 0,
  win_count INTEGER DEFAULT 0,
  loss_count INTEGER DEFAULT 0,
  total_trades INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (ticker, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_pnl_ticker_date 
  ON daily_pnl (ticker, trade_date DESC);

-- Enable RLS for trading tables
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_pnl ENABLE ROW LEVEL SECURITY;

-- Public read access policies
CREATE POLICY IF NOT EXISTS "Public read access for positions" ON positions
  FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Public read access for trades" ON trades
  FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Public read access for daily_pnl" ON daily_pnl
  FOR SELECT USING (true);

-- Service role write access policies
CREATE POLICY IF NOT EXISTS "Service role write access for positions" ON positions
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role write access for trades" ON trades
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role write access for daily_pnl" ON daily_pnl
  FOR ALL USING (auth.role() = 'service_role');

-- Add comments
COMMENT ON TABLE positions IS 'Tracks open and closed option positions';
COMMENT ON TABLE trades IS 'Records all trade executions';
COMMENT ON TABLE daily_pnl IS 'Daily profit/loss summary by ticker';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these after applying migrations to verify tables were created

-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('equity_data', 'indicators', 'option_prices', 'positions', 'trades', 'daily_pnl')
ORDER BY table_name;

-- Check row counts
SELECT 
  'equity_data' as table_name, COUNT(*) as row_count FROM equity_data
UNION ALL
SELECT 'indicators', COUNT(*) FROM indicators
UNION ALL
SELECT 'option_prices', COUNT(*) FROM option_prices
UNION ALL
SELECT 'positions', COUNT(*) FROM positions
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'daily_pnl', COUNT(*) FROM daily_pnl;

-- ============================================================================
-- MIGRATIONS APPLIED SUCCESSFULLY! ✅
-- ============================================================================

