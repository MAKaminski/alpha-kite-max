# Supabase Migrations Guide

## Quick Apply (Recommended)

**Single File with All Migrations**: `supabase/APPLY_ALL_MIGRATIONS.sql`

1. Go to your Supabase Dashboard: https://supabase.com/dashboard/project/xwcauibwyxhsifnotnzz
2. Click **SQL Editor** (left sidebar)
3. Click **New Query**
4. Copy the entire contents of `supabase/APPLY_ALL_MIGRATIONS.sql`
5. Paste into the SQL editor
6. Click **Run** (or press Cmd/Ctrl + Enter)

This will create all required tables:
- ✅ `equity_data` - Stock price and volume data
- ✅ `indicators` - SMA9 and VWAP indicators
- ✅ `option_prices` - Option chain data (nearest ATM strikes)
- ✅ `positions` - Trading positions (open/closed)
- ✅ `trades` - Trade execution history
- ✅ `daily_pnl` - Daily profit/loss summary

## Individual Migrations

If you prefer to apply migrations one at a time:

### 1. Equity & Indicators Tables
**File**: `supabase/migrations/20251015151016_create_equity_and_indicators_tables.sql`

Creates the base tables for stock data and technical indicators.

### 2. Option Prices Table
**File**: `supabase/migrations/20251016130700_add_option_prices_table.sql`

Stores option chain data updated every minute during market hours.

### 3. Trading Tables
**File**: `supabase/migrations/20251016131000_add_trading_tables.sql`

Creates tables for tracking positions, trades, and daily P&L.

## Using Supabase CLI (Alternative)

If you have Supabase CLI installed:

```bash
# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref xwcauibwyxhsifnotnzz

# Apply all migrations
supabase db push
```

## Verification

After applying migrations, run these queries to verify:

```sql
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
```

## Table Schemas

### equity_data
- Stores minute-level price and volume data
- Primary key: `id`
- Indexed on: `(ticker, timestamp)`

### indicators
- Stores calculated SMA9 and VWAP values
- Primary key: `id`
- Indexed on: `(ticker, timestamp)`

### option_prices
- Stores option chain data for nearest ATM strikes
- Primary key: `id`
- Unique index on: `(ticker, timestamp, option_type, strike_price, expiration_date)`

### positions
- Tracks open and closed option positions
- Primary key: `id` (UUID)
- Indexed on: `(ticker, status)` and `entry_timestamp`

### trades
- Records all trade executions
- Primary key: `id` (UUID)
- References: `position_id` → `positions(id)`
- Indexed on: `(ticker, trade_timestamp)` and `position_id`

### daily_pnl
- Daily profit/loss summary
- Primary key: `id` (UUID)
- Unique on: `(ticker, trade_date)`
- Indexed on: `(ticker, trade_date)`

## Security

All tables have **Row Level Security (RLS)** enabled:

- **Public Read Access**: Anyone can SELECT data
- **Service Role Write**: Only backend (with service_role key) can INSERT/UPDATE/DELETE

This ensures the frontend can read data but only the backend can modify it.

## Troubleshooting

### Error: "relation already exists"
**Solution**: The table is already created. You can skip that migration or use `IF NOT EXISTS` (already included in APPLY_ALL_MIGRATIONS.sql).

### Error: "must be owner of table"
**Solution**: Run the SQL as the database owner or use the Supabase SQL Editor (which runs as the owner).

### No Data Showing
**Solution**: 
1. Verify tables exist with the verification queries
2. Run the ETL pipeline to populate data: `python backend/main.py --ticker QQQ --days 5`
3. Check the Lambda function is running for real-time updates

## Next Steps

After applying migrations:

1. **Test Backend**: `python backend/main.py --test-connections`
2. **Download Data**: `python backend/main.py --ticker QQQ --days 5`
3. **Verify in Supabase**: Check Table Editor to see the data
4. **Test Frontend**: Navigate to your Vercel deployment

---

**Need Help?** Check the backend logs or Supabase Table Editor to inspect the data.

