# Getting Started with Alpha Kite Max

Welcome! This guide will get you up and running in **15 minutes**.

## 🎯 What Is This?

Alpha Kite Max is an automated trading system that:
- Monitors QQQ (NASDAQ-100 ETF) in real-time
- Detects SMA9/VWAP crosses (trading signals)
- Automatically trades 0DTE options
- Tracks performance and P&L

---

## 🚀 Quick Start (Choose Your Path)

### For Traders (Run the System)

1. **Prerequisites**: Schwab account, Python 3.10+, Node.js 18+
2. **Apply Database Setup** (5 minutes): [Jump to Setup](#database-setup)
3. **Authenticate** (2 minutes): [Jump to Auth](#authentication)
4. **Download Data** (3 minutes): [Jump to Data](#download-data)
5. **Start Trading** (1 minute): [Jump to Trading](#start-trading)

### For Developers (Contribute/Customize)

1. **Clone & Install** (5 minutes): [Jump to Dev Setup](#developer-setup)
2. **Run Tests** (2 minutes): [Jump to Testing](#running-tests)
3. **Understand Architecture**: Read [`ARCHITECTURE.md`](./ARCHITECTURE.md)
4. **Make Changes**: Follow [`CONTRIBUTING.md`](./CONTRIBUTING.md)

---

##  Database Setup

### 1. Apply Migrations

```bash
# Login to Supabase
supabase login

# Link your project
supabase link --project-ref xwcauibwyxhsifnotnzz

# Apply all migrations
supabase db push
```

**What this creates**:
- `equity_data` - Stock prices
- `indicators` - SMA9, VWAP
- `option_prices` - Options data with Greeks
- `positions`, `trades`, `trading_signals`, `daily_pnl` - Trading tracking
- `transactions`, `feature_usage` - System analytics

---

## 🔐 Authentication

### Schwab OAuth Setup

**Option 1: Automated (Recommended)**
```bash
./reauth_schwab.sh
```

**Option 2: VS Code**
```
Press F5 → Select "🔐 1. Automatic/Non-Interactive Auth"
```

**What happens**:
1. Opens browser to Schwab
2. You click "Allow"
3. Script captures token automatically
4. Token saved to `backend/config/schwab_token.json`

**Troubleshooting**: See [`QUICKSTART_OAUTH.md`](./QUICKSTART_OAUTH.md)

---

## 📊 Download Data

### Get Historical Data

**Via VS Code** (Easiest):
```
Press F5 → Select "📥 3. Download Historical Data (QQQ, 5 days)"
```

**Via Command Line**:
```bash
cd backend
source venv/bin/activate
python main.py --ticker QQQ --days 5
```

**Result**: ~2,000 rows of minute-level data in Supabase

---

## 📈 Start Trading

### Paper Trading Mode (Recommended First)

**Via VS Code**:
```
Press F5 → Select "📈 Trading Engine (Paper Trading)"
```

**Via Command Line**:
```bash
cd backend
python trading_main.py --mode paper --ticker QQQ
```

**What happens**:
- Monitors SMA9/VWAP crosses every minute
- Submits orders when signals detected
- Tracks positions automatically
- Closes positions at profit/loss targets
- Stops at 3:00 PM ET

**Monitor**: Watch terminal output for real-time status

---

## 🧪 Testing Before Live Trading

### Run Complete Workflow Test

```
Press F5 → "🧪 Test Live Trading Workflow (Paper Account)"
```

**Validates**:
- ✅ Schwab API connection
- ✅ Supabase connection
- ✅ Cross detection
- ✅ Order submission
- ✅ Position tracking
- ✅ Order closing

**Must pass** before live trading!

For detailed testing: See [`docs/TESTING_GUIDE.md`](./docs/TESTING_GUIDE.md)

---

## 🖥️ Developer Setup

### 1. Clone Repository
```bash
git clone https://github.com/MAKaminski/alpha-kite-max.git
cd alpha-kite-max
```

### 2. Backend Setup
```bash
cd backend

# Install uv (fast package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Configure environment
cp ../env.example .env
# Edit .env with your credentials
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp ../env.example .env.local
# Edit .env.local with Supabase credentials

# Run dev server
npm run dev
```

Open http://localhost:3000

---

## 🔧 VS Code Integration

### All Tasks via F5 Menu

**Authentication**:
- 🔐 Automatic/Non-Interactive Auth
- 🌐 Interactive Auth

**Data Operations**:
- 📥 Download Historical Data (QQQ, 5 days)
- 📥 Download Historical Data (Custom)
- 📡 Stream Real-Time Data
- 📊 Download 0DTE Options

**Trading & Testing**:
- 🧪 Test Live Trading Workflow (Paper Account)
- 📈 Trading Engine (Paper Trading)

**Development**:
- 🧪 Run All Tests
- 🚀 Frontend Dev Server

**See**: `.vscode/launch.json` for all configurations

---

## 📚 Next Steps

### For Traders

1. ✅ Complete this guide
2. ✅ Run trading workflow test
3. ✅ Verify all tests pass
4. ✅ Download fresh data
5. 🚀 Start paper trading

**Then**: Read [`docs/DEPLOYMENT_GUIDE.md`](./docs/DEPLOYMENT_GUIDE.md) for production deployment

### For Developers

1. ✅ Set up dev environment
2. ✅ Run test suite
3. ✅ Make changes
4. ✅ Run tests again
5. 🚀 Submit PR

**Then**: Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines

---

## 📖 Documentation

### Essential Reading
- **[README.md](./README.md)** - Project overview
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design
- **[SECURITY.md](./SECURITY.md)** - Security best practices

### Implementation Guides
- **[docs/DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md)** - Testing workflows
- **[docs/FEATURE_REFERENCE.md](./docs/FEATURE_REFERENCE.md)** - Feature documentation
- **[docs/DATA_FLOW.md](./docs/DATA_FLOW.md)** - Where data goes

### Reference
- **[backend/README.md](./backend/README.md)** - Backend API reference
- **[frontend/README.md](./frontend/README.md)** - Frontend component docs

---

## ❓ Common Issues

### "No historical data found"
```bash
# Download data first
python main.py --ticker QQQ --days 5
```

### "Authentication failed"
```bash
# Re-authenticate
./reauth_schwab.sh
```

### "Database connection failed"
```bash
# Check .env file has correct SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
cat backend/.env
```

### "Tests failing"
```bash
# Ensure migrations are applied
supabase db push

# Re-run tests
cd backend
pytest tests/
```

---

## 🎯 System Status

### Current Features
- ✅ Real-time data streaming
- ✅ SMA9/VWAP indicator calculation
- ✅ Cross signal detection
- ✅ Automated option trading
- ✅ Position management
- ✅ P&L tracking
- ✅ Paper trading mode
- ✅ Transaction logging
- ✅ Feature usage analytics

### Trading Hours
- **Active Trading**: 10:00 AM - 2:30 PM ET
- **Close-Only**: 2:30 PM - 3:00 PM ET
- **Market Closed**: After 3:00 PM ET

---

## 📞 Get Help

- **Documentation**: Check [`docs/`](./docs/) folder
- **Issues**: Use [GitHub Issues](https://github.com/MAKaminski/alpha-kite-max/issues)
- **Security**: Email MKaminski1337@Gmail.com

---

**Ready to start? Follow the steps above!** 🚀

**Last Updated**: October 19, 2025

