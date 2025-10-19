# Trading Workflow Test Guide

## 🎯 Purpose

Test the complete trading workflow on your **paper account** before Monday's live trading session.

---

## 📋 Pre-Flight Checklist

Before running the test, ensure:

- [ ] You have a Schwab **paper trading account**
- [ ] Your `.env` file has valid Schwab credentials
- [ ] You have authenticated at least once (token exists)
- [ ] Supabase database migrations are applied
- [ ] Historical QQQ data exists in database

---

## 🧪 What Gets Tested

### Complete Round-Trip Workflow:

```
1. ✅ Connection to Schwab API
2. ✅ Connection to Supabase database
3. ✅ Cross detection from historical data
4. ✅ Current market price retrieval
5. ✅ Option chain retrieval
6. ✅ PUT order submission (SELL TO OPEN)
7. ✅ Order confirmation & status check
8. ✅ Position tracking in database
9. ✅ Order closing (BUY TO CLOSE)
10. ✅ CALL order submission
```

---

## 🚀 How to Run the Test

### Method 1: VS Code (Recommended)

1. Press **F5**
2. Select: **"🧪 Test Live Trading Workflow (Paper Account)"**
3. Watch the output in integrated terminal

### Method 2: Command Line

```bash
cd backend
source venv/bin/activate
python test_live_trading_workflow.py
```

---

## 📊 Trading Strategy (Validated)

### Entry Rules:

**Downward Cross (SMA9 crosses below VWAP)**:
- **Action**: Sell 25 PUT contracts
- **Strike**: Nearest strike below current price
- **Expiration**: Next Friday (weekly options)
- **Entry**: Credit received from selling puts

**Upward Cross (SMA9 crosses above VWAP)**:
- **Action 1**: Close existing PUT position (if any)
- **Action 2**: Sell 25 CALL contracts
- **Strike**: Nearest strike above current price

### Exit Rules:

- **Profit Target**: Close at 50% of entry credit
- **Stop Loss**: Close at 200% loss of entry credit
- **End of Day**: Close all positions at 2:30 PM ET (30 mins before market close)

### Trading Hours:

- **Active Trading**: 10:00 AM - 2:30 PM ET
- **No New Positions**: 2:30 PM - 3:00 PM ET
- **Market Close**: 3:00 PM ET

---

## 📝 Expected Test Output

```
================================================================================
LIVE TRADING WORKFLOW TEST - PAPER ACCOUNT
================================================================================

Ticker: QQQ
Test Time: 2025-10-19 16:30:00 ET
Account: PAPER TRADING
================================================================================

📡 STEP 1: Testing Connections
--------------------------------------------------------------------------------
   ✓ Schwab API connected
   ✓ Supabase connected
✅ Connections successful

📊 STEP 2: Detecting Crosses from Historical Data
--------------------------------------------------------------------------------
   ⬇️ Cross detected: 2025-10-17 11:23:00+00:00
      Direction: DOWN
      Price: $598.50
      SMA9: $598.25, VWAP: $598.75
✅ Found 1 cross signal(s)

💹 STEP 3: Getting Current Market Data
--------------------------------------------------------------------------------
   ✓ Latest price: $600.25
✅ Current QQQ price: $600.25

📋 STEP 4: Retrieving Option Chains
--------------------------------------------------------------------------------
   ✓ Retrieved PUT option chains
   ✓ Found 12 PUT expiration dates
   ✓ Retrieved CALL option chains
   ✓ Found 12 CALL expiration dates
✅ Option chains retrieved successfully

🔴 STEP 5: Testing PUT Order Submission
--------------------------------------------------------------------------------
   Selected strike: $599.00
   Option symbol: QQQ251024P00599000
   Bid price: $2.45
   Entry credit: $6125.00 (25 contracts)
   Using account: 12345678...
   📤 Submitting SELL TO OPEN order...
✅ PUT order submitted successfully
   Order ID: 12345-abcdef
   Strike: $599.0
   Contracts: 25
   Entry Price: $2.45

📊 STEP 6: Checking Order Status
--------------------------------------------------------------------------------
   Checking order 12345-abcdef...
   ✓ Order status: WORKING
   ✓ Order confirmation received

📈 STEP 7: Testing Position Tracking
--------------------------------------------------------------------------------
   ✓ Found 1 open position(s)
      • PUT @ $599.0 - 25 contracts

🔵 STEP 8: Testing Order Close (BUY TO CLOSE)
--------------------------------------------------------------------------------
   Closing position: QQQ251024P00599000
   Ask price: $1.20
   📤 Submitting BUY TO CLOSE order...
   ✓ Close order submitted
   ✓ Close order ID: 12346-ghijkl
   📊 Simulated P&L: $3125.00

🟢 STEP 9: Testing CALL Order Submission
--------------------------------------------------------------------------------
   Selected strike: $602.00
   Option symbol: QQQ251024C00602000
   Bid price: $1.85
   📤 Submitting SELL TO OPEN order...
✅ CALL order submitted successfully
   Order ID: 12347-mnopqr
   Strike: $602.0
   Contracts: 25

================================================================================
TEST SUMMARY
================================================================================
✅ Connection to Schwab API: PASSED
✅ Connection to Supabase: PASSED
✅ Cross detection: PASSED
✅ Option chain retrieval: PASSED
✅ PUT order submission: PASSED
✅ CALL order submission: PASSED
================================================================================

🎉 WORKFLOW TEST COMPLETE!
   System is ready for Monday's live trading
```

---

## 🔧 What Happens During the Test

### 1. Detect Crosses
- Pulls last 100 data points from Supabase
- Calculates where SMA9 crossed VWAP
- Identifies direction (up/down)

### 2. Retrieve Option Chains
- Calls Schwab API for current option prices
- Finds strikes with good liquidity
- Identifies 0DTE or weekly options

### 3. Submit Orders
- **PUT**: SELL TO OPEN at strike below current price
- **CALL**: SELL TO OPEN at strike above current price
- Uses paper account (no real money)
- 25 contracts per order

### 4. Verify Orders
- Checks order status via Schwab API
- Confirms order ID received
- Tracks position in Supabase

### 5. Close Orders
- Submits BUY TO CLOSE
- Calculates P&L
- Updates position status

---

## ⚠️ Important Notes

### Paper Account Only
- **All orders go to paper account**
- No real money is used
- Orders may fill differently than live market
- Use this to validate the workflow, not strategy profitability

### Market Hours
- Run this test **today (Saturday)** or **Sunday**
- Orders won't fill immediately (market closed)
- Order submission and confirmation still work
- Validates the complete technical workflow

### Database Setup Required
```bash
# Apply trading tables migration
cd supabase
# Copy the SQL from migrations/20251019000001_create_trading_tables.sql
# Paste into Supabase SQL Editor and run
```

---

## 🛠️ Troubleshooting

### "No historical data found"
**Solution**: Download some data first
```bash
# Run this first:
python main.py --ticker QQQ --days 5
```

### "Could not get account ID"
**Solution**: Verify paper account is set up in Schwab
- Log into developer.schwab.com
- Ensure paper trading account exists
- Check account permissions

### "Order submission failed"
**Possible reasons**:
- Invalid option symbol format
- Strike price doesn't exist
- Market hours (use paper account - works anytime)
- Account permissions

### "Connection failed"
**Solution**: Re-authenticate
```bash
# Run interactive auth:
cd backend/sys_testing
python reauth_schwab.py
```

---

## 📅 Before Monday Trading

### Pre-Market Checklist:

- [ ] Run this test successfully (all steps pass)
- [ ] Verify orders submit to paper account
- [ ] Confirm order IDs are received
- [ ] Test position tracking works
- [ ] Validate close orders work
- [ ] Download fresh data for Monday morning
- [ ] Clear any test positions from database
- [ ] Review trading hours (10 AM - 3 PM ET)
- [ ] Set up monitoring/alerts

### Monday Morning (Before 10 AM):

```bash
# 1. Download latest data
python main.py --ticker QQQ --days 1

# 2. Verify connections
python main.py --test-connections

# 3. Start trading bot
python trading_main.py --mode paper --ticker QQQ
```

---

## 📊 Database Tables Used

### `positions`
- Tracks open/closed option positions
- Records entry credit, current P&L
- Status: OPEN, CLOSED, EXPIRED

### `trades`
- Records every trade execution
- SELL_TO_OPEN and BUY_TO_CLOSE
- Links to position ID

### `trading_signals`
- Logs all SMA9/VWAP crosses
- Records whether action was taken
- Provides audit trail

### `daily_pnl`
- Aggregates daily performance
- Win/loss counts
- Total P&L tracking

---

## ✅ Success Criteria

The test is successful if:

1. ✅ All connections work (Schwab + Supabase)
2. ✅ Crosses can be detected from data
3. ✅ Option chains can be retrieved
4. ✅ PUT order submits and returns order ID
5. ✅ Order status can be checked
6. ✅ Position appears in database
7. ✅ Close order can be submitted
8. ✅ CALL order submits successfully

---

## 🚨 If Test Fails

### Review Each Step:
1. Check authentication token
2. Verify paper account access
3. Confirm database tables exist
4. Check option symbol format
5. Validate strike prices exist

### Get Help:
- Check `backend/BUGFIX.md` for common issues
- Review logs in integrated terminal
- Test individual components separately

---

**Ready to test? Press F5 → Select "🧪 Test Live Trading Workflow (Paper Account)"**

Good luck! 🚀

---

**Last Updated**: October 19, 2025  
**Test Account**: Paper Trading  
**Live Trading**: Monday, October 20, 2025 @ 10:00 AM ET

