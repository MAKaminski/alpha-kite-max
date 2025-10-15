-- Trading System Tables
-- This migration creates tables for tracking positions, trades, and daily P&L

-- Positions table - tracks current open positions
CREATE TABLE IF NOT EXISTS positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('PUT', 'CALL')),
    strike_price DECIMAL(10,2) NOT NULL,
    expiration_date DATE NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('SELL_TO_OPEN', 'BUY_TO_CLOSE')),
    contracts INTEGER NOT NULL DEFAULT 25,
    entry_price DECIMAL(10,4) NOT NULL,
    entry_credit DECIMAL(10,2) NOT NULL, -- Total credit received
    current_price DECIMAL(10,4),
    unrealized_pnl DECIMAL(10,2),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'EXPIRED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Trades table - historical record of all trades
CREATE TABLE IF NOT EXISTS trades (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    position_id UUID REFERENCES positions(id),
    ticker VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('PUT', 'CALL')),
    strike_price DECIMAL(10,2) NOT NULL,
    expiration_date DATE NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('SELL_TO_OPEN', 'BUY_TO_CLOSE')),
    contracts INTEGER NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    credit_debit DECIMAL(10,2) NOT NULL, -- Positive for credit, negative for debit
    trade_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    signal_timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- When the cross signal occurred
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily P&L table - tracks daily performance
CREATE TABLE IF NOT EXISTS daily_pnl (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_realized_pnl DECIMAL(10,2) DEFAULT 0,
    total_unrealized_pnl DECIMAL(10,2) DEFAULT 0,
    total_credits_received DECIMAL(10,2) DEFAULT 0,
    max_drawdown DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(ticker, trade_date)
);

-- Trading signals table - tracks all cross signals
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    signal_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('PUT_SELL', 'CALL_SELL', 'CLOSE_POSITION')),
    current_price DECIMAL(10,4) NOT NULL,
    sma9_value DECIMAL(10,4) NOT NULL,
    vwap_value DECIMAL(10,4) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
    action_taken BOOLEAN DEFAULT FALSE,
    position_id UUID REFERENCES positions(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_positions_ticker_status ON positions(ticker, status);
CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);
CREATE INDEX IF NOT EXISTS idx_trades_ticker_timestamp ON trades(ticker, trade_timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_position_id ON trades(position_id);
CREATE INDEX IF NOT EXISTS idx_daily_pnl_ticker_date ON daily_pnl(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_trading_signals_ticker_timestamp ON trading_signals(ticker, signal_timestamp);

-- Row Level Security (RLS)
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_pnl ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;

-- RLS Policies (allow all for now - can be restricted later)
CREATE POLICY "Allow all operations on positions" ON positions FOR ALL USING (true);
CREATE POLICY "Allow all operations on trades" ON trades FOR ALL USING (true);
CREATE POLICY "Allow all operations on daily_pnl" ON daily_pnl FOR ALL USING (true);
CREATE POLICY "Allow all operations on trading_signals" ON trading_signals FOR ALL USING (true);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_pnl_updated_at BEFORE UPDATE ON daily_pnl
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
