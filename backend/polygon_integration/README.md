# Polygon.io API Integration

**Free Tier Features**: ✅ Historical data only  
**Paid Tier Features**: ⚠️ Real-time streaming (NOT available on your plan)

---

## ✅ What Works on FREE TIER

### Historical Options Data (REST API)
- ✅ Download up to 2 years of historical options data
- ✅ Get option chains with Greeks (IV, delta, gamma, theta, vega)
- ✅ Minute-level OHLCV bars
- ✅ Rate limit: 5 calls/minute

**Available Scripts**:
1. `historic_options.py` - Download specific strikes/dates
2. `bulk_backfill_options.py` - Backfill 90 days automatically

---

## ❌ What DOESN'T Work on FREE TIER

### Real-Time Streaming (WebSocket)
- ❌ Live option quotes
- ❌ Real-time Greeks updates
- ❌ Streaming trades and quotes

**File**: `options_stream.py` (placeholder for future upgrade)

**To enable**: Upgrade to Polygon.io Starter tier ($99/month)

---

## 🚀 Quick Start (Free Tier)

### 1. Install Dependencies
```bash
cd backend
source .venv/bin/activate
pip install requests structlog
```

### 2. Add API Key to .env
```bash
nano .env

# Add:
POLYGON_API_KEY=fbe942c1-688b-4107-b964-1be5e3a8e52c
```

### 3. Test Connection
```bash
python polygon_integration/historic_options.py --test
```

**Expected Output**:
```
✅ Polygon API connection successful!
API Key: fbe942c1...
```

### 4. Download Single Day
```bash
python polygon_integration/historic_options.py \
  --ticker QQQ \
  --strike 600 \
  --date 2025-10-19
```

**Result**: Downloads CALL + PUT for $600 strike on Oct 19

### 5. Bulk Backfill 90 Days
```bash
python bulk_backfill_options.py --ticker QQQ --days 90
```

**Result**: Downloads all in-range strikes for last 90 trading days

---

## 📊 Data You Can Download (Free Tier)

### Available
- ✅ Historical aggregate bars (1min, 5min, 1hour, 1day)
- ✅ Option chain snapshots (current state)
- ✅ Greeks (IV, delta, gamma, theta, vega)
- ✅ Volume and open interest
- ✅ Bid/ask spreads
- ✅ Last trade prices

### Coverage
- ✅ 2 years of historical data
- ✅ All US equity options
- ✅ Minute-level granularity

### Rate Limits
- 5 API calls per minute
- Unlimited data per call
- 100 API calls per day

---

## 🔧 Usage Examples

### Download Specific Strike
```python
from polygon_integration.historic_options import PolygonHistoricOptions

client = PolygonHistoricOptions()

# Download QQQ $600 strike for Oct 19
df = client.download_0dte_options_historic(
    ticker="QQQ",
    strike=600,
    date="2025-10-19"
)

print(f"Downloaded {len(df)} rows")
# Result: ~780 rows (390 CALL + 390 PUT)
```

### Get Option Chain Snapshot
```python
# Get current option chain for specific expiration
df = client.get_option_chain_snapshot(
    ticker="QQQ",
    expiration_date="2025-10-24",
    strikes=[595, 600, 605]
)

print(df[['option_symbol', 'last_price', 'delta', 'iv']])
```

### Get Historical Prices for Specific Contract
```python
# Download minute bars for specific option
df = client.get_historical_option_prices(
    option_symbol="O:QQQ251024C00600000",
    start_date="2025-10-19",
    end_date="2025-10-19",
    timespan="minute"
)

print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']])
```

---

## 🎯 Bulk Backfill Usage

### Download Last 90 Days
```bash
# Automatic mode (recommended)
python bulk_backfill_options.py --ticker QQQ --days 90

# Custom date range
python bulk_backfill_options.py \
  --ticker QQQ \
  --start-date 2025-07-20 \
  --end-date 2025-10-19

# Save to CSV instead of database
python bulk_backfill_options.py \
  --ticker QQQ \
  --days 90 \
  --csv-output polygon_qqq_90days.csv

# Dry run (don't save)
python bulk_backfill_options.py \
  --ticker QQQ \
  --days 30 \
  --no-save
```

### What Happens
1. For each trading day:
   - Queries Supabase for QQQ daily range
   - Generates strikes in $5 increments
   - Downloads CALL + PUT for each in-range strike
   - Waits 12 seconds between strikes (rate limit)
2. Saves all data to `option_prices` table (or CSV)
3. Shows progress in terminal

**Estimated Time**: 
- 30 days: ~1 hour
- 90 days: ~3-4 hours
(depends on how many strikes QQQ traded through each day)

---

## ⚠️ Rate Limiting

### Free Tier Limits
- **5 calls per minute**
- **100 calls per day**

### Our Strategy
- Each strike = 2 API calls (CALL + PUT)
- Wait 12 seconds between strikes = 5 strikes/minute = 2.5 API calls/min ✅
- Well within 5 calls/min limit

### Daily Quota
- 100 calls/day = 50 strikes/day max
- Typical day: 2-4 in-range strikes
- 90 days × 3 strikes avg = 270 strikes = **270 API calls**
- Split across 3 days to stay within daily quota

---

## 🚀 VS Code Integration

### F5 Menu
```
Press F5 → "📊 5c. Bulk Backfill Options (90 Days)"
```

Automatically runs with optimal settings.

---

## 📈 What You'll Get (90-Day Backfill)

### Example Data Volume
- **Days**: 90 trading days
- **Strikes per day**: ~3 (avg in-range)
- **Contracts per strike**: 2 (CALL + PUT)
- **Minutes per day**: 390 (10 AM - 3 PM)

**Total Rows**: 90 × 3 × 2 × 390 = **~210,000 rows**

**Database Size**: ~30-40 MB

**Time to Download**: 3-4 hours (rate limited)

---

## 🔒 Important Notes

### Free Tier Limitations
- ✅ Historical data: YES
- ❌ Real-time streaming: NO (requires paid tier)
- ✅ Greeks: YES
- ✅ All US options: YES
- ✅ 2 years history: YES

### Upgrade to Paid Tier For
- Real-time WebSocket streaming
- Higher rate limits (100+ calls/min)
- Lower latency
- More concurrent connections

**Cost**: Starter tier ~$99/month

---

## 📝 Summary

**What Works Now** (Free Tier):
- ✅ Download historical options data
- ✅ Get option chains with Greeks
- ✅ Bulk backfill 90 days
- ✅ Save to Supabase or CSV
- ✅ GUI with strike selection

**What's a Placeholder** (Requires Paid):
- ⏳ Real-time options streaming (`options_stream.py`)
- ⏳ WebSocket connections
- ⏳ Live Greeks updates

**Action**: Use historic data REST API for now, upgrade later for streaming.

