# Testing Real-Time Data Streaming for Current Day (10/15/25)

## Problem

Current day data is not streaming into the dashboard, while historic days work fine. We need to diagnose and fix the real-time data pipeline.

## Test Suite Overview

Three tools have been created to test and debug the real-time data streaming:

### 1. **Quick Test Script** (`test_current_day.py`)

**Purpose**: Fast diagnostic test for current day data streaming

**Usage**:
```bash
cd backend
source venv/bin/activate
python test_current_day.py
```

**What it tests**:
- ✅ Schwab API connection
- ✅ Current day data download (1 day period)
- ✅ Indicator calculation (SMA9, VWAP)
- ✅ Supabase upload
- ✅ Data retrieval verification
- ✅ Data freshness (< 1 hour old)

**Output**: Detailed step-by-step diagnostics with colored output

---

### 2. **Full Test Suite** (`tests/test_real_time_streaming.py`)

**Purpose**: Comprehensive pytest-based test suite

**Usage**:
```bash
cd backend
source venv/bin/activate
pytest tests/test_real_time_streaming.py -v
```

**Or run manually**:
```bash
python tests/test_real_time_streaming.py
```

**What it tests**:
- All the tests from `test_current_day.py` plus:
- Complete real-time update cycle
- Pagination and data retrieval
- Error handling
- Edge cases

---

### 3. **Auth Refresh Script** (`refresh_schwab_auth.py`)

**Purpose**: Refresh Schwab API authentication when tokens expire

**Usage**:
```bash
cd backend
source venv/bin/activate
python refresh_schwab_auth.py
```

**Interactive steps**:
1. Script will open a browser window
2. Log in to your Schwab account
3. Authorize the application
4. Copy the redirect URL from browser
5. Paste the URL when prompted
6. Script saves new token and tests connection

---

## Current Issue Found

**❌ Schwab Token Invalid/Expired**

The test revealed that the Schwab API token is invalid or expired. This is why current day data isn't streaming.

### Solution

**Step 1: Refresh Authentication**
```bash
cd backend
source venv/bin/activate
python refresh_schwab_auth.py
```

Follow the interactive prompts to re-authenticate with Schwab.

**Step 2: Verify Data Streaming**
```bash
python test_current_day.py
```

You should see:
- ✅ All steps passing
- Data for current day (10/15/25)
- Fresh data (< 1 hour old)

**Step 3: Download Current Day Data**
```bash
python main.py --ticker QQQ --days 1
```

This will download today's data to Supabase.

**Step 4: Check Frontend**

Visit http://localhost:3000 and verify:
- Chart shows data for today
- Latest timestamp is recent
- SMA9 and VWAP indicators are displayed

---

## Expected Test Output

### ✅ Successful Test Run

```
================================================================================
TESTING CURRENT DAY DATA STREAMING FOR QQQ
Date: 2025-10-15
Time: 2025-10-15 15:30:00
================================================================================

📋 Step 1: Initializing clients...
✅ Clients initialized

📡 Step 2: Testing Schwab API connection...
✅ API connection successful
   Candles received: 390
   Time range: 2025-10-15 09:30 to 15:30
   Price range: $585.50 to $590.25

📥 Step 3: Downloading and processing data...
✅ Downloaded 390 data points
   Columns: ['ticker', 'timestamp', 'price', 'volume']
   Time range: 2025-10-15T09:30:00+00:00 to 2025-10-15T15:30:00+00:00

📊 Step 4: Calculating indicators...
✅ Calculated indicators for 390 data points
   Latest values:
   Timestamp: 2025-10-15T15:30:00+00:00
   SMA9: $589.75
   VWAP: $587.92

📤 Step 5: Uploading to Supabase...
✅ Uploaded 390 equity data rows
✅ Uploaded 390 indicator rows

🔍 Step 6: Verifying data can be retrieved...
✅ Retrieved 390 equity data rows
✅ Retrieved 390 indicator rows
   Last equity timestamp: 2025-10-15T15:30:00+00:00
   Last indicator timestamp: 2025-10-15T15:30:00+00:00
   Data age: 0:00:05
   ✅ Data is fresh (< 1 hour old)

================================================================================
✅ ALL TESTS PASSED - CURRENT DAY DATA IS STREAMING CORRECTLY
================================================================================
```

### ❌ Failed Test (Token Invalid)

```
📡 Step 2: Testing Schwab API connection...
❌ Schwab API test failed: token_invalid:

ACTION REQUIRED:
Run: python refresh_schwab_auth.py
```

---

## Troubleshooting

### Issue: No Data During Market Hours

**Check**:
1. Market is actually open (9:30 AM - 4:00 PM ET)
2. Not a weekend or holiday
3. Schwab API is working

**Test**:
```bash
python test_current_day.py
```

If you see "market might be closed", this is expected outside trading hours.

### Issue: Data is Stale

**Symptoms**: Last timestamp is more than 1 hour old

**Solution**:
1. Run data download manually:
```bash
python main.py --ticker QQQ --days 1
```

2. Set up automatic updates (cron job):
```bash
# Run every minute during market hours
*/1 9-16 * * 1-5 cd /path/to/backend && source venv/bin/activate && python main.py --ticker QQQ --days 1
```

### Issue: Frontend Shows No Data

**Check**:
1. Supabase credentials in `frontend/.env.local`
2. Data actually exists in Supabase:
```bash
python test_current_day.py
```

3. Frontend is fetching correct date:
- Open browser console
- Check for errors
- Verify selected date matches today

---

## Continuous Monitoring

### Option 1: Manual Updates

Run during market hours:
```bash
# Every 5-10 minutes
python main.py --ticker QQQ --days 1
```

### Option 2: Automated Cron Job

Add to crontab:
```bash
# Update every minute during market hours (9:30 AM - 4:00 PM ET)
*/1 9-16 * * 1-5 cd /Users/makaminski1337/Developer/alpha-kite-max/backend && source venv/bin/activate && python main.py --ticker QQQ --days 1 >> logs/data_update.log 2>&1
```

### Option 3: Background Service

Create a systemd service or use a process manager like `pm2` for Node.js or `supervisor` for Python.

---

## Next Steps

1. **Immediate**: Run `refresh_schwab_auth.py` to fix authentication
2. **Verify**: Run `test_current_day.py` to confirm data streaming
3. **Deploy**: Set up automated data updates for real-time streaming
4. **Monitor**: Check frontend displays current day data correctly

---

## Questions?

If tests are still failing after refreshing authentication:

1. Check Schwab API status
2. Verify Supabase connection
3. Check backend logs for errors
4. Ensure .env file has correct credentials
5. Verify paper trading mode is enabled (`SCHWAB_PAPER=true`)

