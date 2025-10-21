# Paper Trading Setup Guide

This guide explains how to set up and use Schwab's paper trading account with the Alpha Kite Max trading dashboard.

## Overview

The application uses Schwab's **official paper trading account** to execute real option trades in a simulated environment. This allows you to:

- Test the SMA9/VWAP cross strategy without risking real capital
- Execute actual option orders on Schwab's paper trading platform
- Track positions, P&L, and trading performance
- Verify strategy logic before going live

## Prerequisites

1. **Schwab Account**: You need a Schwab brokerage account
2. **Paper Trading Access**: Enable paper trading in your Schwab account
3. **Schwab API Access**: Register for API access at [Schwab Developer Portal](https://developer.schwab.com/)
4. **API Credentials**: Obtain your App Key and App Secret

## Configuration

### 1. Environment Variables

Add the following to your `backend/.env` file:

```bash
# Schwab API Credentials
SCHWAB_APP_KEY=your-app-key-here
SCHWAB_APP_SECRET=your-app-secret-here
SCHWAB_CALLBACK_URL=https://localhost:8000/callback

# Paper Trading Configuration
SCHWAB_ACCOUNT_ID=your-paper-account-number
SCHWAB_PAPER=true
SCHWAB_BASE_URL=https://api.schwab.com
```

### 2. Get Your Paper Trading Account Number

Run the test script to retrieve your paper trading account number:

```bash
cd backend
python test_paper_trading.py
```

This will display:
- Your paper trading account number
- Account type
- Paper trading status
- Available option chains (verification)

### 3. Update Configuration

Copy the account number from the test output and add it to your `.env` file:

```bash
SCHWAB_ACCOUNT_ID=12345678  # Your paper account number
```

## Paper Trading Features

### Automated Trading

The trading engine automatically:

1. **Monitors Crosses**: Detects SMA9/VWAP crosses during market hours
2. **Places Orders**: Executes option orders on your paper account
3. **Manages Positions**: Tracks open positions and P&L
4. **Risk Management**: Implements stop-loss and take-profit rules
5. **End-of-Day Close**: Closes positions 30 minutes before market close

### Trading Strategy

**Signal Rules:**
- **Downward Cross** (SMA9 < VWAP): Sell 25 PUT contracts
- **Upward Cross** (SMA9 > VWAP): Close existing position + Sell 25 CALL contracts
- **Profit Target**: Close at 50% of entry credit
- **Stop Loss**: Close at 200% of entry credit (loss)
- **End-of-Session**: Close all positions 30 mins before market close

### API Methods

The Schwab client now supports:

#### Get Account Information
```python
from schwab_integration.client import SchwabClient

client = SchwabClient()
account_info = client.get_account_info()
print(f"Account: {account_info['accountNumber']}")
```

#### Place Option Order
```python
# Sell to open (enter position)
order = client.place_option_order(
    account_id="12345678",
    symbol="QQQ",
    option_symbol="QQQ_102524P500",  # 0DTE Put @ 500 strike
    instruction="SELL_TO_OPEN",
    quantity=25,
    price=0.50  # Limit price
)

# Buy to close (exit position)
close_order = client.place_option_order(
    account_id="12345678",
    symbol="QQQ",
    option_symbol="QQQ_102524P500",
    instruction="BUY_TO_CLOSE",
    quantity=25,
    price=0.25  # Take profit at 50% credit
)
```

#### Check Order Status
```python
status = client.get_order_status(
    account_id="12345678",
    order_id="order-123"
)
print(f"Order Status: {status['status']}")
```

## Testing Paper Trading

### Step 1: Test Connectivity

```bash
cd backend
python test_paper_trading.py
```

Expected output:
```
✓ Account found!
  Account ID: 12345678
  Account Type: MARGIN
  Is Paper Trading: True

✓ Option chains retrieved successfully
  Available expiration dates: 12
  First expiration: 2025-10-16:0
```

### Step 2: Verify Configuration

```bash
python main.py --test-connections
```

Should show:
```
Connection Test Results:
  Supabase: ✓ Connected
  Schwab:   ✓ Connected
```

### Step 3: Manual Order Test

Create a test script to place a small order:

```python
# test_order.py
from schwab_integration.client import SchwabClient
from schwab_integration.config import SchwabConfig

config = SchwabConfig()
client = SchwabClient(config)

# Get account
account = client.get_account_info()
account_id = account['accountNumber']

# Place a test order (1 contract for testing)
order = client.place_option_order(
    account_id=account_id,
    symbol="SPY",
    option_symbol="SPY_102524P500",
    instruction="SELL_TO_OPEN",
    quantity=1,
    price=0.50
)

print(f"Order placed: {order['order_id']}")
```

## Monitoring Paper Trades

### Frontend Dashboard

The TradingDashboard component displays:
- **Open Positions**: Currently held option contracts
- **Recent Trades**: Last 10 trades for the selected date
- **Daily P&L**: Realized and unrealized profit/loss
- **Trade History**: Full trading activity

### Database Tables

All trades are stored in Supabase:

- **`positions`**: Open and closed positions
- **`trades`**: Individual trade executions
- **`daily_pnl`**: Daily profit/loss summary

Query example:
```sql
SELECT * FROM positions WHERE status = 'OPEN';
SELECT * FROM trades WHERE trade_date = '2025-10-16';
SELECT * FROM daily_pnl WHERE ticker = 'QQQ';
```

## Safety Features

### Paper Trading Safeguards

1. **Paper Mode Flag**: Must be explicitly enabled (`SCHWAB_PAPER=true`)
2. **Account Verification**: Verifies paper account before placing orders
3. **Dry Run Logging**: All orders are logged before execution
4. **Position Limits**: Max 25 contracts per trade
5. **Time Restrictions**: No trading 30 mins before close

### Risk Management

- **Stop Loss**: Auto-close at 200% loss
- **Take Profit**: Auto-close at 50% profit
- **Max Contracts**: Limited to 25 per position
- **Session Close**: Force close all positions before market close

## Switching to Live Trading

⚠️ **WARNING**: Only switch to live trading after thorough testing!

To enable live trading:

1. **Update Configuration**:
   ```bash
   SCHWAB_PAPER=false
   SCHWAB_ACCOUNT_ID=your-live-account-number
   ```

2. **Verify Account**:
   ```bash
   python test_paper_trading.py
   ```

3. **Start Small**: Begin with minimal position sizes

4. **Monitor Closely**: Watch first day of live trading carefully

## Troubleshooting

### Issue: "Token Invalid" Error

**Solution**:
1. Delete `backend/config/schwab_token.json`
2. Run authentication flow again
3. Click the callback URL and authorize

### Issue: "Account Not Found"

**Solution**:
1. Verify Schwab account has paper trading enabled
2. Check API credentials are correct
3. Ensure account ID matches paper account

### Issue: "Order Placement Failed"

**Solution**:
1. Verify option symbol format is correct
2. Check market hours (must be during trading hours)
3. Ensure account has sufficient buying power
4. Verify paper trading is enabled

## Best Practices

1. **Test Thoroughly**: Run paper trading for at least 2 weeks
2. **Monitor Daily**: Review positions and P&L every day
3. **Analyze Performance**: Track win rate, avg profit, max drawdown
4. **Adjust Strategy**: Refine rules based on paper trading results
5. **Keep Logs**: Save all trade logs for analysis

## Support

For issues:
1. Check logs in `backend/logs/`
2. Review Schwab API documentation
3. Verify environment variables are set correctly
4. Test with `test_paper_trading.py`

## Summary

✅ **Paper Trading Enabled**: Place real orders on Schwab's paper account
✅ **Full Strategy Support**: SMA9/VWAP cross logic with risk management
✅ **Position Tracking**: Monitor all trades in Supabase
✅ **Safety Features**: Stop-loss, take-profit, and session close rules
✅ **Easy Testing**: Simple scripts to verify setup

You're now ready to paper trade with Alpha Kite Max! 🚀

