# Historic Options Data - API Limitation & Workaround

## ⚠️ Current Limitation

**The Schwab API does NOT support historical options data.**

### What's Available:
- ✅ **Current/Live** option chains with real-time pricing
- ✅ Current Greeks (delta, gamma, theta, vega, IV)
- ✅ Current bid/ask/last prices
- ✅ Current volume and open interest

### What's NOT Available:
- ❌ Historical option prices (past days/hours)
- ❌ Historical Greeks
- ❌ Historical IV changes
- ❌ Time series of option prices

## 🔍 What We're Currently Doing

### Real-Time Option Capture
When you run the Lambda or download options, we capture **current snapshot**:

```python
# This gets CURRENT option chains
option_data = schwab_client.get_option_chains('QQQ', 'ALL')

# We save the current snapshot with timestamp
option_df = process_option_chains(option_data, ticker, timestamp, current_price)
supabase_client.upsert_option_prices(option_df)  # Saves to database
```

**Result**: Each time we run it, we get a new snapshot with current timestamp.

### Building Historical Data Over Time

To get "historical" options data, we:
1. **Run downloads regularly** (every minute/hour/day)
2. **Save each snapshot** with timestamp to `option_prices` table
3. **Build history** by accumulating snapshots over time

**Example**:
- Monday 10:00 AM: Download QQQ $600 PUT → Save (last_price: $2.50)
- Monday 10:01 AM: Download QQQ $600 PUT → Save (last_price: $2.48)
- Monday 10:02 AM: Download QQQ $600 PUT → Save (last_price: $2.52)

After 3 downloads, we have 3 historical data points!

## 📊 Current Implementation

### What Works Now:

**1. Lambda Real-Time Streamer** (`backend/lambda/real_time_streamer.py`):
- Runs every minute during market hours
- Downloads equity data
- Downloads CURRENT option chains
- Saves both to Supabase
- ✅ Builds historical record over time

**2. Manual Option Download** (`backend/download_0dte_options.py`):
```bash
# Download current 0DTE options at $600 strike
python download_0dte_options.py --strike 600 --today-only
```
- Gets CURRENT snapshot
- Saves with current timestamp
- ✅ One data point added to history

**3. Database Storage**:
- Table: `option_prices`
- Each row has `timestamp` field
- Query by date range to see historical progression
- ✅ Historical data accumulates

## 🚀 Workaround Solution

### Option A: Scheduled Downloads (Recommended)

**Deploy Lambda to run every minute**:
```bash
# Already configured in infrastructure/lambda.tf
# CloudWatch triggers Lambda every 1 minute during market hours
```

**Result**:
- 300+ snapshots per day (5 hours × 60 minutes)
- Complete intraday historical record
- Fully automated

### Option B: Manual Periodic Downloads

**Run manually at key times**:
```bash
# At market open (10 AM)
python download_0dte_options.py --strike 600 --today-only

# Mid-day (12 PM)
python download_0dte_options.py --strike 600 --today-only

# Before close (2:30 PM)
python download_0dte_options.py --strike 600 --today-only
```

**Result**:
- 3 snapshots per day
- Enough for daily analysis
- Requires manual execution

### Option C: Continuous Monitoring Script

**Create a local script that runs all day**:
```python
# download_options_continuously.py
while market_is_open():
    download_options(strike=600)
    time.sleep(60)  # Wait 1 minute
```

**Result**:
- Runs on your local machine
- Collects data all day
- Stops when market closes

## 📈 Querying Historical Options Data

Once you've been collecting for a while:

```sql
-- Get all $600 PUT prices for QQQ today
SELECT timestamp, last_price, bid, ask, volume, delta
FROM option_prices
WHERE ticker = 'QQQ'
  AND strike_price = 600
  AND option_type = 'PUT'
  AND DATE(timestamp) = CURRENT_DATE
ORDER BY timestamp;

-- Get price movement over time
SELECT 
  timestamp,
  last_price,
  implied_volatility,
  delta
FROM option_prices
WHERE ticker = 'QQQ'
  AND strike_price = 600
  AND option_type = 'PUT'
  AND timestamp >= NOW() - INTERVAL '1 day'
ORDER BY timestamp;
```

## 🎯 Recommended Approach for Monday

### Starting Monday:

**1. Deploy Lambda** (if not already):
```bash
cd backend
./deploy_lambda.sh
```

**2. Lambda Configuration**:
- Runs every 1 minute: 10:00 AM - 3:00 PM
- Downloads equity data + option chains
- Saves to database automatically

**3. After One Week**:
You'll have:
- ~1,500 option snapshots (5 hours × 60 min × 5 days)
- Complete historical record
- Intraday price movements
- IV and Greeks progression

### Query Your Historical Data:

```python
# In Python
from supabase_client import SupabaseClient

client = SupabaseClient()

# Get all option data for QQQ $600 from last week
query = client.client.table('option_prices')\
    .select('*')\
    .eq('ticker', 'QQQ')\
    .eq('strike_price', 600)\
    .gte('timestamp', '2025-10-13')\
    .order('timestamp')\
    .execute()

df = pd.DataFrame(query.data)
# Now you have historical options data!
```

## 🆕 Alternative: Third-Party Historical Options Data

If you need historical data from BEFORE you started collecting:

### Paid Services:
1. **CBOE DataShop** - Historical options data
2. **OptionMetrics** - Academic/institutional
3. **iVolatility** - Comprehensive historical IV
4. **ThetaData** - Options time series

### Free/Limited:
1. **Yahoo Finance** - Limited historical options
2. **Market Chameleon** - Sample historical data

### Import Process:
1. Download CSV from provider
2. Convert to our schema
3. Bulk insert into `option_prices` table

## ✅ Summary

### Current Status:
- ❌ Schwab API: No historical options endpoint
- ✅ Our System: Captures current snapshots
- ✅ Database: Stores with timestamps
- ✅ Result: Builds history over time

### What You'll Have After Monday:
- Day 1: Current snapshots (starting point)
- Week 1: 5 days of intraday options history
- Month 1: 20+ days of complete records
- Year 1: Full historical database

### Action Required:
- **Deploy Lambda** (runs automatically)
- **OR run manual downloads** periodically
- Data accumulates automatically

---

**Bottom Line**: We're not downloading "historic" data because the API doesn't provide it. Instead, we're **creating** historic data by capturing snapshots over time. Starting Monday, you'll begin building your own historical options database! 🚀

---

**Last Updated**: October 19, 2025  
**API Limitation**: Confirmed - No historical options endpoint  
**Workaround**: ✅ Implemented - Time-series snapshots

