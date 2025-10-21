# Supabase Database Schema for Streaming Service

Complete schema documentation for the Equity/Options streaming service.

## 📊 Core Tables

### 1. equity_data

Stores minute-level equity price and volume data from the streaming service.

```sql
CREATE TABLE public.equity_data (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_equity_ticker_timestamp ON public.equity_data(ticker, timestamp DESC);
CREATE INDEX idx_equity_timestamp ON public.equity_data(timestamp DESC);
CREATE UNIQUE INDEX idx_equity_unique ON public.equity_data(ticker, timestamp);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `ticker`: Stock symbol (e.g., "QQQ", "SPY")
- `timestamp`: When the price/volume was recorded (UTC)
- `price`: Stock price at this timestamp
- `volume`: Trading volume at this tick
- `created_at`: When the record was inserted into the database

**Usage:**
```python
# Insert from streaming service
df = pd.DataFrame([{
    'ticker': 'QQQ',
    'timestamp': datetime.now(),
    'price': 389.45,
    'volume': 1000
}])
supabase_client.insert_equity_data(df)

# Query recent data
df = supabase_client.get_equity_data('QQQ', limit=390)
```

**Typical Row:**
```json
{
  "id": 12345,
  "ticker": "QQQ",
  "timestamp": "2025-10-21T14:30:00Z",
  "price": 389.45,
  "volume": 1000,
  "created_at": "2025-10-21T14:30:01Z"
}
```

---

### 2. indicators

Stores calculated technical indicators (SMA9, VWAP) for equities.

```sql
CREATE TABLE public.indicators (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    sma9 DECIMAL(10, 2),
    vwap DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_indicators_ticker_timestamp ON public.indicators(ticker, timestamp DESC);
CREATE INDEX idx_indicators_timestamp ON public.indicators(timestamp DESC);
CREATE UNIQUE INDEX idx_indicators_unique ON public.indicators(ticker, timestamp);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `ticker`: Stock symbol
- `timestamp`: When the indicators were calculated (UTC)
- `sma9`: 9-period Simple Moving Average
- `vwap`: Volume Weighted Average Price
- `created_at`: When the record was inserted

**Usage:**
```python
# Insert indicators
df = pd.DataFrame([{
    'ticker': 'QQQ',
    'timestamp': datetime.now(),
    'sma9': 389.12,
    'vwap': 389.34
}])
supabase_client.insert_indicators(df)

# Query indicators
df = supabase_client.get_indicators('QQQ', limit=390)
```

**Typical Row:**
```json
{
  "id": 12345,
  "ticker": "QQQ",
  "timestamp": "2025-10-21T14:30:00Z",
  "sma9": 389.12,
  "vwap": 389.34,
  "created_at": "2025-10-21T14:30:01Z"
}
```

---

### 3. option_prices

Stores option pricing data, particularly for 0DTE (zero days to expiration) options.

```sql
CREATE TABLE public.option_prices (
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

-- Indexes
CREATE INDEX idx_option_prices_ticker_timestamp ON public.option_prices(ticker, timestamp DESC);
CREATE INDEX idx_option_prices_expiration ON public.option_prices(expiration_date);
CREATE INDEX idx_option_prices_strike ON public.option_prices(ticker, strike_price);
CREATE UNIQUE INDEX idx_option_prices_unique ON public.option_prices(
    ticker, timestamp, option_type, strike_price, expiration_date
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `ticker`: Underlying stock symbol
- `timestamp`: When the option data was recorded (UTC)
- `option_type`: "CALL" or "PUT"
- `strike_price`: Option strike price
- `expiration_date`: Option expiration date
- `last_price`: Last traded price
- `bid`: Current bid price
- `ask`: Current ask price
- `volume`: Trading volume
- `open_interest`: Number of outstanding contracts
- `implied_volatility`: IV percentage
- `delta`: Delta (price sensitivity to underlying)
- `gamma`: Gamma (delta sensitivity)
- `theta`: Theta (time decay)
- `vega`: Vega (volatility sensitivity)
- `option_symbol`: Full option symbol (e.g., "O:QQQ251024C00600000")
- `created_at`: When inserted into database

**Usage:**
```python
# Insert option data
df = pd.DataFrame([{
    'ticker': 'QQQ',
    'timestamp': datetime.now(),
    'option_type': 'CALL',
    'strike_price': 390.00,
    'expiration_date': '2025-10-21',
    'last_price': 2.45,
    'bid': 2.40,
    'ask': 2.50,
    'volume': 500,
    'open_interest': 1000,
    'implied_volatility': 0.25,
    'delta': 0.45,
    'gamma': 0.02,
    'theta': -0.05,
    'vega': 0.15,
    'option_symbol': 'O:QQQ251021C00390000'
}])
supabase_client.upsert_option_prices(df)
```

**Typical Row:**
```json
{
  "id": 12345,
  "ticker": "QQQ",
  "timestamp": "2025-10-21T14:30:00Z",
  "option_type": "CALL",
  "strike_price": 390.00,
  "expiration_date": "2025-10-21",
  "last_price": 2.45,
  "bid": 2.40,
  "ask": 2.50,
  "volume": 500,
  "open_interest": 1000,
  "implied_volatility": 0.25,
  "delta": 0.45,
  "gamma": 0.02,
  "theta": -0.05,
  "vega": 0.15,
  "option_symbol": "O:QQQ251021C00390000",
  "created_at": "2025-10-21T14:30:01Z"
}
```

---

### 4. streaming_metrics

Monitors the health and performance of the streaming service.

```sql
CREATE TABLE streaming_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ticker VARCHAR(10) NOT NULL,
    records_processed BIGINT NOT NULL,
    batch_size INTEGER,
    processing_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    service_status VARCHAR(20) DEFAULT 'running'
);

-- Indexes
CREATE INDEX idx_streaming_metrics_timestamp ON streaming_metrics(timestamp DESC);
CREATE INDEX idx_streaming_metrics_ticker ON streaming_metrics(ticker, timestamp DESC);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `timestamp`: When the metric was recorded
- `ticker`: Stock symbol being streamed
- `records_processed`: Number of records processed in this batch
- `batch_size`: Size of the batch
- `processing_time_ms`: Time taken to process the batch (milliseconds)
- `error_count`: Number of errors in this batch
- `service_status`: Service status ("running", "stopped", "error")

**Usage:**
```sql
-- Check streaming health
SELECT * FROM get_streaming_health('QQQ');

-- View recent metrics
SELECT * FROM streaming_metrics 
WHERE ticker = 'QQQ' 
ORDER BY timestamp DESC 
LIMIT 100;
```

---

## 📈 Materialized Views

### equity_data_stats

Pre-aggregated daily statistics for fast dashboard queries.

```sql
CREATE MATERIALIZED VIEW equity_data_stats AS
SELECT 
    ticker,
    DATE(timestamp) AS trade_date,
    COUNT(*) AS tick_count,
    MIN(price) AS low_price,
    MAX(price) AS high_price,
    AVG(price) AS avg_price,
    SUM(volume) AS total_volume,
    MIN(timestamp) AS first_tick,
    MAX(timestamp) AS last_tick
FROM equity_data
GROUP BY ticker, DATE(timestamp);

CREATE UNIQUE INDEX idx_equity_stats_ticker_date 
ON equity_data_stats(ticker, trade_date DESC);
```

**Refresh:**
```sql
-- Refresh manually
REFRESH MATERIALIZED VIEW CONCURRENTLY equity_data_stats;

-- Or use the helper function
SELECT refresh_equity_stats();

-- Schedule with pg_cron (if available)
SELECT cron.schedule(
    'refresh-equity-stats',
    '*/15 * * * *',  -- Every 15 minutes
    'SELECT refresh_equity_stats()'
);
```

**Query:**
```sql
-- Get today's stats for QQQ
SELECT * FROM equity_data_stats 
WHERE ticker = 'QQQ' 
  AND trade_date = CURRENT_DATE;

-- Get stats for last 30 days
SELECT * FROM equity_data_stats 
WHERE ticker = 'QQQ' 
  AND trade_date > CURRENT_DATE - INTERVAL '30 days'
ORDER BY trade_date DESC;
```

---

## 🔧 Helper Functions

### cleanup_old_equity_data

Deletes old equity data to manage database size.

```sql
-- Delete data older than 90 days (default)
SELECT cleanup_old_equity_data();

-- Delete data older than 30 days
SELECT cleanup_old_equity_data(30);

-- Schedule automatic cleanup (requires pg_cron extension)
SELECT cron.schedule(
    'cleanup-old-data',
    '0 2 * * *',  -- 2 AM daily
    'SELECT cleanup_old_equity_data(90)'
);
```

### get_streaming_health

Returns streaming service health metrics.

```sql
-- Get health for all tickers
SELECT * FROM get_streaming_health();

-- Get health for specific ticker
SELECT * FROM get_streaming_health('QQQ');
```

**Returns:**
- `ticker`: Stock symbol
- `last_update`: Timestamp of last update
- `records_last_hour`: Number of records processed in the last hour
- `avg_batch_size`: Average batch size
- `error_rate`: Percentage of errors
- `status`: "healthy", "warning", or "error"

---

## 🔒 Row Level Security (RLS)

All tables have RLS enabled with two policies:

### Service Role (Backend)
Full access for backend services using the service role key.

```sql
CREATE POLICY "Allow service role full access to {table}"
    ON {table}
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
```

### Anonymous (Frontend)
Read-only access for dashboards and frontends.

```sql
CREATE POLICY "Allow anonymous read access to {table}"
    ON {table}
    FOR SELECT
    TO anon
    USING (true);
```

---

## 📊 Query Examples

### Get Latest Price

```sql
SELECT ticker, price, timestamp
FROM equity_data
WHERE ticker = 'QQQ'
ORDER BY timestamp DESC
LIMIT 1;
```

### Get Price for Last Hour

```sql
SELECT ticker, timestamp, price, volume
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### Get 0DTE Options

```sql
SELECT 
    option_symbol,
    option_type,
    strike_price,
    last_price,
    bid,
    ask,
    volume,
    delta
FROM option_prices
WHERE ticker = 'QQQ'
  AND expiration_date = CURRENT_DATE
  AND timestamp > NOW() - INTERVAL '5 minutes'
ORDER BY strike_price;
```

### Get Trading Volume by Hour

```sql
SELECT 
    DATE_TRUNC('hour', timestamp) AS hour,
    COUNT(*) AS ticks,
    SUM(volume) AS total_volume,
    AVG(price) AS avg_price
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > CURRENT_DATE
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour;
```

### Check Streaming Service Health

```sql
SELECT 
    ticker,
    MAX(timestamp) AS last_update,
    AGE(NOW(), MAX(timestamp)) AS time_since_update,
    COUNT(*) AS updates_last_hour
FROM streaming_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY ticker;
```

---

## 🚀 Performance Optimization

### Indexes

All tables have optimized indexes for:
- Time-series queries: `(ticker, timestamp DESC)`
- Ticker lookups: `ticker`
- Unique constraints: Prevent duplicates

### Partitioning (For Large Datasets)

For datasets with millions of rows, consider partitioning:

```sql
-- Install pg_partman extension
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- Partition equity_data by month
SELECT partman.create_parent(
    p_parent_table := 'public.equity_data',
    p_control := 'timestamp',
    p_type := 'native',
    p_interval := '1 month',
    p_premake := 2  -- Create 2 future partitions
);

-- Schedule maintenance
SELECT cron.schedule(
    'partition-maintenance',
    '0 3 * * *',  -- 3 AM daily
    'CALL partman.run_maintenance_proc()'
);
```

### Connection Pooling

For high-throughput streaming, use connection pooling:

```python
from supabase import create_client

# Enable connection pooling in Supabase dashboard
# Or use pgbouncer for local pooling
```

---

## 📏 Data Retention

Recommended retention policies:

- **equity_data**: 90 days (for intraday analysis)
- **indicators**: 90 days (same as equity data)
- **option_prices**: 30 days (for recent options activity)
- **streaming_metrics**: 30 days (for service monitoring)

Implement with:

```sql
-- Schedule cleanup jobs
SELECT cron.schedule(
    'cleanup-equity',
    '0 2 * * *',
    'SELECT cleanup_old_equity_data(90)'
);

SELECT cron.schedule(
    'cleanup-indicators',
    '0 2 * * *',
    'DELETE FROM indicators WHERE created_at < NOW() - INTERVAL ''90 days'''
);

SELECT cron.schedule(
    'cleanup-options',
    '0 2 * * *',
    'DELETE FROM option_prices WHERE created_at < NOW() - INTERVAL ''30 days'''
);

SELECT cron.schedule(
    'cleanup-metrics',
    '0 2 * * *',
    'DELETE FROM streaming_metrics WHERE timestamp < NOW() - INTERVAL ''30 days'''
);
```

---

## 🔍 Monitoring Queries

### Database Size

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Record Counts

```sql
SELECT 
    'equity_data' AS table_name, 
    COUNT(*) AS records,
    MIN(timestamp) AS oldest,
    MAX(timestamp) AS newest
FROM equity_data
UNION ALL
SELECT 
    'indicators' AS table_name, 
    COUNT(*) AS records,
    MIN(timestamp) AS oldest,
    MAX(timestamp) AS newest
FROM indicators
UNION ALL
SELECT 
    'option_prices' AS table_name, 
    COUNT(*) AS records,
    MIN(timestamp) AS oldest,
    MAX(timestamp) AS newest
FROM option_prices;
```

### Index Usage

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

---

## 🆘 Troubleshooting

### Duplicate Key Errors

If you see unique constraint violations:

```sql
-- Check for duplicates
SELECT ticker, timestamp, COUNT(*)
FROM equity_data
GROUP BY ticker, timestamp
HAVING COUNT(*) > 1;

-- Remove duplicates (keep first)
DELETE FROM equity_data a
USING equity_data b
WHERE a.id > b.id
  AND a.ticker = b.ticker
  AND a.timestamp = b.timestamp;
```

### Slow Queries

Enable query logging to identify slow queries:

```sql
-- In Supabase dashboard: Settings → Database → Query Performance
-- Or manually:
ALTER DATABASE postgres SET log_min_duration_statement = 1000;  -- Log queries > 1s
```

### Connection Issues

Check active connections:

```sql
SELECT 
    datname,
    usename,
    application_name,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'postgres'
ORDER BY state, query_start DESC;
```

Kill stuck connections:

```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'postgres'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '1 hour';
```

