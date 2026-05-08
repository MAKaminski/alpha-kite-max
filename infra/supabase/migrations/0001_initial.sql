-- alpha-kite-v2 initial schema
-- Owns: ticks, bars, signals, order_intents, fills, positions, daily_pnl, audit_log
-- Idempotent: every CREATE uses IF NOT EXISTS.

-- ──────────────────────────────────────────────────────────────────────────
-- Reference: strategy/symbol metadata. Lightweight enough to be in-band.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategies (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT        NOT NULL UNIQUE,
    config_hash TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ──────────────────────────────────────────────────────────────────────────
-- Equity ticks (NBBO last). Append-only; high write rate.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ticks (
    id          BIGSERIAL PRIMARY KEY,
    symbol      TEXT        NOT NULL,
    ts          TIMESTAMPTZ NOT NULL,
    bid         NUMERIC(18,4),
    ask         NUMERIC(18,4),
    last        NUMERIC(18,4),
    volume      BIGINT,
    feed        TEXT        NOT NULL
);
CREATE INDEX IF NOT EXISTS ticks_symbol_ts_idx ON ticks (symbol, ts DESC);

-- ──────────────────────────────────────────────────────────────────────────
-- Equity bars (1-minute by default).
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bars (
    id                BIGSERIAL PRIMARY KEY,
    symbol            TEXT        NOT NULL,
    interval_seconds  INT         NOT NULL,
    open_time         TIMESTAMPTZ NOT NULL,
    open              NUMERIC(18,4) NOT NULL,
    high              NUMERIC(18,4) NOT NULL,
    low               NUMERIC(18,4) NOT NULL,
    close             NUMERIC(18,4) NOT NULL,
    volume            BIGINT       NOT NULL,
    vwap              NUMERIC(18,4),
    feed              TEXT        NOT NULL,
    UNIQUE (symbol, interval_seconds, open_time)
);
CREATE INDEX IF NOT EXISTS bars_symbol_open_time_idx ON bars (symbol, open_time DESC);

-- ──────────────────────────────────────────────────────────────────────────
-- Strategy signals (cross events, exit triggers, etc).
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signals (
    id           BIGSERIAL PRIMARY KEY,
    strategy     TEXT        NOT NULL,
    symbol       TEXT        NOT NULL,
    direction    TEXT        NOT NULL,   -- LONG_VOL_UP | LONG_VOL_DOWN | EXIT | NONE
    ts           TIMESTAMPTZ NOT NULL,
    strength     NUMERIC(8,4) NOT NULL DEFAULT 1,
    metadata     JSONB        NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS signals_strategy_ts_idx ON signals (strategy, ts DESC);
CREATE INDEX IF NOT EXISTS signals_symbol_ts_idx ON signals (symbol, ts DESC);

-- ──────────────────────────────────────────────────────────────────────────
-- Order intents (pre-broker). Includes dry-run intents that never reach broker.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_intents (
    intent_id     UUID         PRIMARY KEY,
    created_at    TIMESTAMPTZ  NOT NULL,
    symbol        TEXT         NOT NULL,
    is_option     BOOLEAN      NOT NULL,
    option_expiry DATE,
    option_strike NUMERIC(18,4),
    option_right  CHAR(1),                -- 'C' or 'P'
    side          TEXT         NOT NULL,  -- BUY | SELL
    quantity      INT          NOT NULL,
    order_type    TEXT         NOT NULL,  -- MKT | LMT
    limit_price   NUMERIC(18,4),
    time_in_force TEXT         NOT NULL DEFAULT 'DAY',
    dry_run       BOOLEAN      NOT NULL,
    tag           TEXT         NOT NULL DEFAULT '',
    submitted     BOOLEAN      NOT NULL DEFAULT FALSE,
    broker_order_id TEXT
);
CREATE INDEX IF NOT EXISTS order_intents_created_idx ON order_intents (created_at DESC);

-- ──────────────────────────────────────────────────────────────────────────
-- Fills (executions reported by broker).
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fills (
    id              BIGSERIAL PRIMARY KEY,
    fill_id         TEXT         NOT NULL UNIQUE,
    intent_id       UUID         REFERENCES order_intents(intent_id),
    broker_order_id TEXT         NOT NULL,
    ts              TIMESTAMPTZ  NOT NULL,
    symbol          TEXT         NOT NULL,
    is_option       BOOLEAN      NOT NULL,
    option_expiry   DATE,
    option_strike   NUMERIC(18,4),
    option_right    CHAR(1),
    side            TEXT         NOT NULL,
    quantity        INT          NOT NULL,
    price           NUMERIC(18,4) NOT NULL,
    commission      NUMERIC(12,4) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS fills_intent_idx ON fills (intent_id);
CREATE INDEX IF NOT EXISTS fills_ts_idx ON fills (ts DESC);

-- ──────────────────────────────────────────────────────────────────────────
-- Positions (current snapshot, upsert-on-conflict).
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS positions (
    id              BIGSERIAL PRIMARY KEY,
    as_of           TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol          TEXT        NOT NULL,
    is_option       BOOLEAN     NOT NULL,
    option_expiry   DATE,
    option_strike   NUMERIC(18,4),
    option_right    CHAR(1),
    quantity        INT          NOT NULL,
    avg_cost        NUMERIC(18,4) NOT NULL,
    market_value    NUMERIC(18,4),
    unrealized_pnl  NUMERIC(18,4),
    UNIQUE (symbol, is_option, option_expiry, option_strike, option_right)
);

-- ──────────────────────────────────────────────────────────────────────────
-- Daily P&L roll-ups.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_pnl (
    trading_day    DATE         PRIMARY KEY,
    realized_usd   NUMERIC(18,4) NOT NULL DEFAULT 0,
    unrealized_usd NUMERIC(18,4) NOT NULL DEFAULT 0,
    trades         INT           NOT NULL DEFAULT 0,
    wins           INT           NOT NULL DEFAULT 0,
    losses         INT           NOT NULL DEFAULT 0,
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ──────────────────────────────────────────────────────────────────────────
-- Audit log: every safety-critical decision lands here, regardless of outcome.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor       TEXT        NOT NULL,    -- engine | broker | risk | operator
    event_type  TEXT        NOT NULL,    -- e.g. ORDER_INTENT, RISK_BLOCK, KILL_SWITCH
    severity    TEXT        NOT NULL DEFAULT 'INFO',  -- INFO | WARN | ERROR
    message     TEXT        NOT NULL,
    payload     JSONB       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS audit_log_ts_idx ON audit_log (ts DESC);
CREATE INDEX IF NOT EXISTS audit_log_event_idx ON audit_log (event_type, ts DESC);
