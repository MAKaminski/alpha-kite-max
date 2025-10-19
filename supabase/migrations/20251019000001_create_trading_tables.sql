-- Create positions table for tracking open/closed positions
CREATE TABLE IF NOT EXISTS public.positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
    strike_price DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    action VARCHAR(20) NOT NULL,
    contracts INTEGER NOT NULL DEFAULT 25,
    entry_price DECIMAL(10, 4) NOT NULL,
    entry_credit DECIMAL(12, 2) NOT NULL,
    current_price DECIMAL(10, 4),
    unrealized_pnl DECIMAL(12, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'EXPIRED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

-- Create index on ticker and status for efficient queries
CREATE INDEX IF NOT EXISTS idx_positions_ticker_status ON public.positions(ticker, status);

-- Create index on status and created_at
CREATE INDEX IF NOT EXISTS idx_positions_status_created ON public.positions(status, created_at DESC);

-- Add comment
COMMENT ON TABLE public.positions IS 'Tracks option positions (open, closed, expired)';

-- Create trades table for recording all trades
CREATE TABLE IF NOT EXISTS public.trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID REFERENCES public.positions(id),
    ticker VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
    strike_price DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    action VARCHAR(20) NOT NULL,
    contracts INTEGER NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    credit_debit DECIMAL(12, 2) NOT NULL,
    trade_timestamp TIMESTAMPTZ NOT NULL,
    signal_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_ticker_timestamp ON public.trades(ticker, trade_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_position_id ON public.trades(position_id);

-- Add comment
COMMENT ON TABLE public.trades IS 'Records all trade executions (entries and exits)';

-- Create trading_signals table for tracking all signals
CREATE TABLE IF NOT EXISTS public.trading_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    signal_timestamp TIMESTAMPTZ NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    current_price DECIMAL(10, 2) NOT NULL,
    sma9_value DECIMAL(10, 2) NOT NULL,
    vwap_value DECIMAL(10, 2) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
    action_taken BOOLEAN DEFAULT FALSE,
    position_id UUID REFERENCES public.positions(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_signals_ticker_timestamp ON public.trading_signals(ticker, signal_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_action_taken ON public.trading_signals(action_taken);

-- Add comment
COMMENT ON TABLE public.trading_signals IS 'Records all SMA9/VWAP cross signals';

-- Create daily_pnl table for daily performance tracking
CREATE TABLE IF NOT EXISTS public.daily_pnl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_realized_pnl DECIMAL(12, 2) DEFAULT 0,
    total_unrealized_pnl DECIMAL(12, 2) DEFAULT 0,
    total_credits_received DECIMAL(12, 2) DEFAULT 0,
    max_drawdown DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, trade_date)
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_daily_pnl_ticker_date ON public.daily_pnl(ticker, trade_date DESC);

-- Add comment
COMMENT ON TABLE public.daily_pnl IS 'Daily profit and loss tracking';

-- Enable Row Level Security (RLS)
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_pnl ENABLE ROW LEVEL SECURITY;

-- Create policies for anonymous read access
CREATE POLICY "Allow anonymous read access to positions"
    ON public.positions FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anonymous read access to trades"
    ON public.trades FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anonymous read access to trading_signals"
    ON public.trading_signals FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anonymous read access to daily_pnl"
    ON public.daily_pnl FOR SELECT TO anon USING (true);

-- Create policies for service role full access
CREATE POLICY "Allow service role full access to positions"
    ON public.positions FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow service role full access to trades"
    ON public.trades FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow service role full access to trading_signals"
    ON public.trading_signals FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow service role full access to daily_pnl"
    ON public.daily_pnl FOR ALL TO service_role USING (true) WITH CHECK (true);

