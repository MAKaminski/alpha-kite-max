# Monday Trading Preparation Checklist

## 🎯 Goal: Go Live Monday, October 20, 2025 @ 10:00 AM ET

---

## ✅ COMPLETED TODAY

### Trading Window Updated
- ✅ Changed from 9:30 AM - 4:00 PM → **10:00 AM - 3:00 PM ET**
- ✅ Stop new positions at 2:30 PM (30 mins before close)
- ✅ Updated across all files (frontend + backend + Lambda)

### Volume Chart
- ✅ Added volume bar chart below price chart
- ✅ Separate Y-axis for volume
- ✅ Auto-scaling and formatting (K/M)
- ✅ Synchronized market hours highlighting

### 0DTE Options System
- ✅ Database schema created (`option_prices` table)
- ✅ Option downloader module created
- ✅ CLI script for downloading option data
- ✅ VS Code launch configurations added

### Data Management Dashboard
- ✅ Manual download interface (single day or range)
- ✅ Real-time streaming toggle
- ✅ Live data feed (shows last 15 updates)
- ✅ Auto-scrolling terminal-style display
- ✅ API routes created for backend integration

### Trading Workflow Test
- ✅ Complete end-to-end test script created
- ✅ Tests all order types (PUT/CALL)
- ✅ Tests order submission and confirmation
- ✅ Tests position tracking
- ✅ Tests order closing (BUY TO CLOSE)
- ✅ Ready to run on paper account

---

## 📋 TODO BEFORE MONDAY

### 1. Apply Database Migrations ⚠️ CRITICAL

**Option Prices Table**:
```bash
# 1. Open Supabase Dashboard
https://supabase.com/dashboard/project/xwcauibwyxhsifnotnzz/editor

# 2. Go to SQL Editor
# 3. Copy content from:
supabase/migrations/20251019000000_create_option_prices_table.sql

# 4. Paste and run
```

**Trading Tables**:
```bash
# In same SQL Editor, run:
supabase/migrations/20251019000001_create_trading_tables.sql
```

**Tables to be created**:
- `option_prices` - Stores 0DTE option data
- `positions` - Tracks open/closed positions
- `trades` - Records all trade executions
- `trading_signals` - Logs SMA9/VWAP crosses
- `daily_pnl` - Daily performance metrics

### 2. Run Trading Workflow Test ⚠️ CRITICAL

**When**: Today (Saturday) or Sunday  
**Where**: VS Code

```bash
Press F5 → Select "🧪 Test Live Trading Workflow (Paper Account)"
```

**Verify**:
- [ ] Schwab connection works
- [ ] Option chains retrieved successfully
- [ ] PUT order submits (SELL TO OPEN)
- [ ] Order ID received
- [ ] Position tracked in database
- [ ] Close order works (BUY TO CLOSE)
- [ ] CALL order submits

**If it fails**: Review `TRADING_TEST_GUIDE.md` for troubleshooting

### 3. Download Fresh Data for Monday

**Sunday Evening** (after 8 PM ET):
```bash
# Download last 5 days of QQQ data
Press F5 → Select "📥 3. Download Historical Data (QQQ, 5 days)"
```

This ensures you have:
- Fresh price data
- Current SMA9/VWAP values
- Clean baseline for Monday

### 4. Test Data Management Dashboard (Optional)

**Add to your dashboard page**:
```tsx
// frontend/src/app/page.tsx or your main dashboard
import DataManagementDashboard from '@/components/DataManagementDashboard';

export default function Page() {
  return (
    <div>
      {/* ... existing components ... */}
      <DataManagementDashboard />
    </div>
  );
}
```

**Test**:
- Toggle streaming ON/OFF
- Watch data feed update
- Try manual download

---

## 🚀 MONDAY MORNING LAUNCH SEQUENCE

### 9:30 AM ET - Pre-Market Setup

```bash
# 1. Navigate to backend
cd backend
source venv/bin/activate

# 2. Test connections
python main.py --test-connections
```

**Expected output**:
```
Connection Test Results:
  Supabase: ✓ Connected
  Schwab:   ✓ Connected
```

### 9:45 AM ET - Download Pre-Market Data

```bash
# Download latest data
python main.py --ticker QQQ --days 1
```

**Expected**: ~390 rows of equity data

### 10:00 AM ET - START TRADING 🚀

**Option A: VS Code**
```
Press F5 → Select "📈 Trading Engine (Paper Trading)"
```

**Option B: Command Line**
```bash
python trading_main.py --mode paper --ticker QQQ
```

**What happens**:
- Bot starts monitoring SMA9/VWAP
- Detects crosses every minute
- Submits orders automatically
- Tracks positions
- Manages profit/loss targets
- Closes all positions at 2:30 PM

### Monitor During Trading

Watch for:
- 🔴 Cross signals (log output)
- 📤 Order submissions
- ✅ Order confirmations
- 📊 Position updates
- 💰 P&L tracking

### 3:00 PM ET - Market Close

- Bot automatically stops
- All positions should be closed
- Review daily P&L
- Check trade history

---

## 📊 Monitoring & Logs

### Real-Time Monitoring

**Terminal Output**:
```bash
# Shows live:
- Cross detections
- Order submissions
- Position updates
- P&L calculations
```

**Supabase Dashboard**:
```
https://supabase.com/dashboard/project/xwcauibwyxhsifnotnzz/editor

Tables to watch:
- positions (should show OPEN → CLOSED)
- trades (should show SELL_TO_OPEN → BUY_TO_CLOSE)
- trading_signals (all crosses logged)
- daily_pnl (running P&L)
```

### Frontend Dashboard

**If using Data Management Dashboard**:
- Toggle streaming ON
- Watch live data feed
- See price/volume/indicators update

---

## 🔐 Safety Measures

### Paper Account First
- ✅ All tests use paper account
- ✅ No real money at risk
- ✅ Validates workflow without financial exposure

### Error Handling
- ✅ Connection failures → retry logic
- ✅ Order failures → logged and skipped
- ✅ Position tracking → persisted to database
- ✅ P&L limits → auto-close on stop loss

### Manual Override
- You can stop the bot anytime (Ctrl+C)
- Manually close positions via Schwab if needed
- Database tracks everything for review

---

## 📈 Expected Monday Performance

### Trading Strategy:
- **Signal**: SMA9/VWAP crosses
- **Action**: Sell PUTs (down) or CALLs (up)
- **Size**: 25 contracts per trade
- **Risk**: Limited to premium collected
- **Profit Target**: 50% of entry credit
- **Stop Loss**: 200% loss

### Realistic Expectations:
- **Crosses per day**: 0-5 (depends on volatility)
- **Max positions**: 1 at a time (serial strategy)
- **Win rate**: Target 60-70%
- **Profit per trade**: $500-$3,000 (varies by premium)

---

## 🛑 Emergency Procedures

### If Something Goes Wrong:

1. **Stop the bot**: Ctrl+C in terminal
2. **Check positions**: 
   ```bash
   cd backend/sys_testing
   python check_data_status.py
   ```
3. **Manually close via Schwab**: Log into schwab.com
4. **Review logs**: Check terminal output
5. **Contact support**: If needed

---

## 📞 Quick Reference Commands

```bash
# Test trading workflow (run today!)
python test_live_trading_workflow.py

# Download data
python main.py --ticker QQQ --days 5

# Test connections
python main.py --test-connections

# Start trading bot (Monday)
python trading_main.py --mode paper --ticker QQQ

# Download 0DTE options
python download_0dte_options.py --strike 600 --today-only

# Check token status
cd sys_testing && python token_diagnostics.py
```

---

## ✅ Final Pre-Launch Checklist

**Today (Saturday/Sunday)**:
- [ ] Apply database migrations (option_prices, positions, trades, signals, daily_pnl)
- [ ] Run trading workflow test successfully
- [ ] Verify all 9 test steps pass
- [ ] Confirm orders submit to paper account
- [ ] Test position tracking

**Sunday Evening**:
- [ ] Download fresh QQQ data (5 days)
- [ ] Verify data in Supabase
- [ ] Test connections one more time
- [ ] Set alarm for Monday 9:30 AM

**Monday Morning (9:30-9:55 AM)**:
- [ ] Test connections
- [ ] Download latest data
- [ ] Review strategy parameters
- [ ] Clear test positions (if any)

**Monday 10:00 AM**:
- [ ] Launch trading bot
- [ ] Confirm monitoring active
- [ ] Watch first cross signal

---

## 🎉 You're Ready!

After completing this checklist, your system will be:
- ✅ Fully tested on paper account
- ✅ Ready for automated trading
- ✅ Monitored and logged
- ✅ Safe with stop-loss protections

**Next Action**: Run the trading workflow test!

```bash
Press F5 → "🧪 Test Live Trading Workflow (Paper Account)"
```

---

**Last Updated**: October 19, 2025, 4:00 PM ET  
**Status**: Ready for final testing  
**Go-Live**: Monday, October 20, 2025 @ 10:00 AM ET

