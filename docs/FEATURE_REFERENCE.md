# Feature Reference

Complete reference for all features in Alpha Kite Max.

---

## 📊 Core Features

### Real-Time Data Streaming
- **Status**: ✅ Production Ready
- **Description**: Live minute-by-minute equity data from Schwab API
- **Ticker**: QQQ (default), configurable
- **Frequency**: Every minute during trading hours
- **Data**: OHLCV (Open, High, Low, Close, Volume)

### Technical Indicators
- **SMA9**: 9-period Simple Moving Average
- **Session VWAP**: Volume-Weighted Average Price (resets daily at 10 AM)
- **Auto-Calculation**: Computed on every data update

### Trading Strategy
- **Signal**: SMA9/VWAP cross detection
- **Down Cross** (SMA9 below VWAP): Sell 25 PUT contracts
- **Up Cross** (SMA9 above VWAP): Close PUTs, Sell 25 CALL contracts
- **Profit Target**: 50% of entry credit
- **Stop Loss**: 200% loss
- **Position Limit**: 1 at a time (serial strategy)

### Trading Hours
- **Active Trading**: 10:00 AM - 2:30 PM ET
- **Close-Only**: 2:30 PM - 3:00 PM ET
- **Market Close**: 3:00 PM ET
- **Weekends**: No trading
- **Holidays**: US market holidays observed

---

## 🎨 Frontend Features

### Dashboard
- **Component**: `frontend/src/components/Dashboard.tsx`
- **Features**:
  - Date navigation (previous/next day, date picker)
  - Real-time data refresh (every 60 seconds)
  - Cross detection visualization
  - Market hours highlighting

### Price Chart
- **Component**: `frontend/src/components/EquityChart.tsx`
- **Visualizations**:
  - Price line (with hover tooltips)
  - SMA9 indicator (blue line)
  - VWAP indicator (purple line)
  - Cross markers (red circles)
  - Market hours highlighting
- **Time Range**: Full trading day (10 AM - 3 PM)
- **X-Axis**: Time in EST
- **Y-Axis**: Price in USD

### Volume Chart
- **Position**: Below price chart
- **Height**: 120px
- **Type**: Bar chart
- **Axis**: Separate left-aligned Y-axis
- **Formatting**: Volume in K/M (thousands/millions)
- **Synchronization**: Market hours highlighting matches price chart

### Data Management Dashboard
- **Component**: `frontend/src/components/DataManagementDashboard.tsx`
- **Features**:
  1. **Historical Download Panel**:
     - Ticker selection
     - Single day or date range mode
     - Date pickers
     - Download button
     - Status display
  2. **Live Streaming Panel**:
     - ON/OFF toggle switch
     - Status indicator (🟢 Live / ⚫ Stopped)
     - Live data feed (terminal-style)
     - Auto-scrolling (last 15 updates)
     - Displays: Time, Ticker, Price, Volume, SMA9, VWAP
  3. **Info Panel**:
     - Quick tips
     - Market hours reference
     - Feature explanations

### Dark Mode
- **Context**: `frontend/src/contexts/DarkModeContext.tsx`
- **Toggle**: Available in header
- **Persistence**: Saved to localStorage
- **Coverage**: All components styled for dark mode

---

## 🔧 Backend Features

### Data Downloader
- **Module**: `backend/schwab_integration/downloader.py`
- **Capabilities**:
  - Download historical equity data
  - Multi-day downloads
  - Automatic pagination
  - Error handling and retries

### Option Downloader
- **Module**: `backend/schwab_integration/option_downloader.py`
- **Capabilities**:
  - Download 0DTE options
  - Specific strike prices
  - Both CALL and PUT contracts
  - Auto-find closest strike
  - Multi-day historical downloads
  - Weekend filtering

### Trading Engine
- **Module**: `backend/schwab_integration/trading_engine.py`
- **Capabilities**:
  - Cross detection
  - Order building (SELL TO OPEN, BUY TO CLOSE)
  - Strike selection (nearest to current price)
  - Position tracking
  - P&L calculation
  - Risk management (profit targets, stop loss)

### ETL Pipeline
- **Module**: `backend/etl_pipeline.py`
- **Flow**:
  1. Download data from Schwab
  2. Calculate indicators
  3. Transform data format
  4. Upsert to Supabase
  5. Log results

### Real-Time Streaming
- **Module**: `backend/schwab_integration/streaming.py`
- **Features**:
  - WebSocket connection to Schwab
  - Level 1 quotes
  - Real-time indicator calculation
  - Automatic reconnection

---

## 💾 Database Features

### Tables

**equity_data**:
- ticker, timestamp, price, volume
- Unique index on (ticker, timestamp)

**indicators**:
- ticker, timestamp, sma9, vwap
- Unique index on (ticker, timestamp)

**option_prices**:
- ticker, timestamp, option_type, strike_price, expiration_date
- last_price, bid, ask, volume, open_interest
- Greeks: implied_volatility, delta, gamma, theta, vega

**positions**:
- ticker, option_symbol, option_type, strike, expiration
- entry_price, entry_credit, current_price, current_pnl
- quantity, status (OPEN/CLOSED/EXPIRED)

**trades**:
- ticker, option_symbol, action (SELL_TO_OPEN/BUY_TO_CLOSE)
- quantity, price, total_value
- Links to position

**trading_signals**:
- ticker, signal_timestamp, signal_type (UP_CROSS/DOWN_CROSS)
- sma9, vwap, price
- action_taken (boolean)

**daily_pnl**:
- ticker, trade_date, total_pnl, realized_pnl, unrealized_pnl
- total_trades, winning_trades, losing_trades

**transactions**:
- transaction_type, feature_name, status
- ticker, parameters (JSONB)
- rows_affected, execution_time_ms
- error_message

**feature_usage**:
- feature_name, total_calls, successful_calls, failed_calls
- avg_execution_time_ms, total_rows_processed
- Auto-updated via trigger

---

## 🚀 AWS Lambda Features

### Real-Time Streamer Lambda
- **Function**: `alpha-kite-real-time-streamer`
- **Runtime**: Python 3.10
- **Memory**: 256 MB
- **Timeout**: 60 seconds
- **Trigger**: EventBridge (every minute during market hours)
- **Purpose**: Download data, calculate indicators, upload to Supabase

### Token Management
- **Storage**: AWS Secrets Manager (`schwab-api-token-prod`)
- **Auto-Refresh**: Lambda checks expiration and refreshes
- **Lifespan**: 7 days (access), 90 days (refresh)

### Monitoring
- **Logs**: CloudWatch (`/aws/lambda/alpha-kite-real-time-streamer`)
- **Metrics**: Custom metrics for data points, errors, latency
- **Alarms**: (Optional) Token expiration, function failures

---

## 🔐 Authentication Features

### Schwab OAuth 2.0
- **Flow**: Authorization Code Flow
- **Token Lifespan**: 7 days (access), 90 days (refresh)
- **Auto-Refresh**: Lambda handles automatically
- **Manual Refresh**: Via `./reauth_schwab.sh` or VS Code

### Storage
- **Local**: `backend/config/schwab_token.json`
- **Production**: AWS Secrets Manager
- **Security**: Never committed to Git, encrypted at rest

---

## 🧪 Testing Features

### Unit Tests
- **Count**: 19 tests
- **Status**: ✅ All passing
- **Coverage**: Core business logic
- **Files**: `tests/test_trading_engine.py`, `tests/test_option_downloader.py`

### Integration Tests
- **Count**: 5 tests
- **Coverage**: API + Database interactions
- **Files**: `tests/test_real_time_streaming.py`, `tests/integration/`

### End-to-End Tests
- **Count**: 2 tests
- **Coverage**: Complete trading workflow
- **Files**: `tests/test_e2e_trading_cycle.py`, `backend/test_live_trading_workflow.py`

---

## 📈 Analytics Features

### Transaction Logging
- **Module**: `backend/transaction_logger.py`
- **Tracks**: Every API call, download, trade, action
- **Storage**: `transactions` table
- **Auto-Aggregation**: Updates `feature_usage` table

### Feature Usage Views
- **daily_feature_usage**: Daily stats per feature
- **hourly_feature_usage**: Hourly stats per feature
- **feature_performance**: Performance metrics

### P&L Tracking
- **Daily**: `daily_pnl` table
- **Per-Trade**: `trades` table
- **Per-Position**: `positions` table with current P&L

---

## 🎛️ VS Code Integration

### Launch Configurations (F5 Menu)

**Authentication**:
- 🔐 1. Automatic/Non-Interactive Auth
- 🌐 2. Interactive Auth

**Data Operations**:
- 📥 3. Download Historical Data (QQQ, 5 days)
- 📥 3b. Download Historical Data (Custom)
- 📥 3c. Download Historical Data (SPY, 7 days)
- 📡 4. Stream Real-Time Data
- 📊 5. Download 0DTE Options (QQQ $600)
- 📊 5b. Download 0DTE Options (Custom Strikes)

**Trading & Testing**:
- 🧪 Test Live Trading Workflow (Paper Account)
- 📈 Trading Engine (Paper Trading)

**Development**:
- 🧪 Run All Tests
- 🧪 Run Schwab Tests
- 🧪 Run Streaming Tests
- 🚀 Frontend Dev Server
- 🏗️ Frontend Build

**Utilities**:
- 📊 Quick Demo (Standalone QQQ)
- 🔍 Check Token Status

---

## 🌐 API Routes

### Frontend API Routes

**`/api/download-data` (POST)**:
- Triggers historical data download
- **Parameters**: ticker, date/dateRange, mode
- **Returns**: success status, row count

**`/api/stream-control` (POST)**:
- Controls real-time streaming
- **Parameters**: action (start/stop), ticker
- **Returns**: success status, timestamp

---

## ⚙️ Configuration Features

### Environment Variables

**Frontend** (`.env.local`):
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

**Backend** (`.env`):
- `SCHWAB_APP_KEY`
- `SCHWAB_APP_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `LOG_LEVEL`
- `DEFAULT_TICKER`

### Feature Flags

Currently, features are always-on. Future feature flag system could be added for:
- Beta features
- A/B testing
- Gradual rollouts

---

## 📊 Data Flow Summary

### Historical Download
```
User → VS Code/Frontend → Backend Python → Schwab API → Database
```

### Real-Time Streaming
```
EventBridge → Lambda → Schwab API → Database → Frontend Poll
```

### Option Trading
```
Cross Detected → Trading Engine → Schwab API (Order) → Database (Position)
```

### Analytics
```
Any Action → Transaction Logger → transactions table → Auto-Aggregate → feature_usage
```

---

## 🔍 Data Storage

### Where Data Goes

**Supabase** (Cloud Database):
- All ETL pipeline data
- Real-time streaming data
- Trading positions and trades
- Analytics and transactions

**Local CSV** (Optional):
- Standalone demo script only
- Not used by main system

**AWS Secrets Manager**:
- OAuth tokens (production only)

---

## 🚨 Limitations

### Known Limitations

1. **Historical Options**: Schwab API doesn't provide historical option prices
   - **Workaround**: Capture snapshots every minute to build history

2. **Single Ticker**: Currently optimized for QQQ only
   - **Future**: Multi-ticker support planned

3. **Paper Trading Only**: No live trading mode yet
   - **Safety**: Prevents accidental real trades

4. **No WebSocket UI**: Frontend polls every 60 seconds
   - **Future**: Real-time WebSocket connection planned

5. **No Mobile App**: Web-only currently
   - **Future**: React Native app planned

---

## 📝 FAQs

### Why doesn't historical options data exist?

Schwab API only provides current option chains, not historical. We capture snapshots every minute to build our own historical database.

### Where is downloaded data stored?

- **Main System**: Supabase database (cloud)
- **Standalone Demo**: Local CSV files

### How do I add a new ticker?

Change `DEFAULT_TICKER` in `backend/.env` or pass `--ticker` flag to commands.

### Can I run multiple strategies?

Currently, only SMA9/VWAP cross strategy is implemented. To add more strategies, create new modules in `backend/schwab_integration/`.

### How do I switch to live trading?

**Not recommended yet!** System is tested on paper account only. To enable, change `--mode paper` to `--mode live` in trading commands, but thorough testing required first.

---

## 🎯 Future Features

### Planned Enhancements

1. **Multi-Ticker Support**: Track multiple symbols simultaneously
2. **Advanced Strategies**: More technical indicators and strategies
3. **Machine Learning**: Predictive models for price movements
4. **Mobile App**: iOS and Android apps
5. **WebSocket UI**: Real-time updates without polling
6. **Backtesting**: Historical simulation of strategies
7. **Alert System**: SMS/Email notifications for signals
8. **Performance Dashboard**: Advanced analytics and reports

---

**All features documented and production-ready!** 🎉

**Last Updated**: October 19, 2025

