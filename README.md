# Alpha Kite Max

Real-time trading dashboard with automated 0DTE options trading based on SMA9/VWAP cross signals.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Trading Status](https://img.shields.io/badge/Trading-Paper%20Trading%20Ready-green.svg)](docs/LIVE_TRADING_READINESS.md)

---

## 🚀 Current Status: Ready for Live Paper Trading

**✅ System Ready**: All components operational and tested
**✅ Data Streaming**: Real-time Schwab API integration active
**✅ Trading Engine**: SMA9/VWAP cross strategy implemented
**✅ Risk Management**: Comprehensive risk controls in place
**✅ Paper Trading**: Full simulation mode ready for live testing

**🎯 Next Steps**: Begin autonomous paper trading with real market data

---

## ⚡ Quick Start

**New to Alpha Kite Max?** → Read [**GETTING_STARTED.md**](./GETTING_STARTED.md) (15-minute setup)

**Ready for Trading?** → Read [**LIVE_TRADING_READINESS.md**](./docs/LIVE_TRADING_READINESS.md) (Trading checklist)

**Experienced Developer?** → Jump to [Developer Setup](#developer-setup)

---

## 📚 Documentation

### 📖 Core Documentation
- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - Complete setup guide (start here!)
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture and design
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute to the project
- **[SECURITY.md](./SECURITY.md)** - Security policies and best practices
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history and changes

### 📋 Guides
- **[docs/guides/QUICKSTART_OAUTH.md](./docs/guides/QUICKSTART_OAUTH.md)** - Schwab OAuth setup
- **[docs/guides/BLACK_SCHOLES_SYNTHETIC_OPTIONS.md](./docs/guides/BLACK_SCHOLES_SYNTHETIC_OPTIONS.md)** - Synthetic options data generation
- **[docs/POLYGON.md](./docs/POLYGON.md)** - Polygon.io integration guide

### 🔧 Technical Documentation
- **[docs/DATA_FLOW.md](./docs/DATA_FLOW.md)** - How data flows through the system
- **[docs/DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md)** - Deploy to production
- **[docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md)** - Run and write tests
- **[docs/FEATURE_REFERENCE.md](./docs/FEATURE_REFERENCE.md)** - Complete feature list

### 📊 Status & Reports
- **[docs/status/PROJECT_STATUS.md](./docs/status/PROJECT_STATUS.md)** - Current project status
- **[docs/status/FINAL_DEPLOYMENT_STATUS.md](./docs/status/FINAL_DEPLOYMENT_STATUS.md)** - Deployment status

### 📦 Backend-Specific
- **[backend/README.md](./backend/README.md)** - Backend overview
- **[backend/TESTING.md](./backend/TESTING.md)** - Backend testing guide
- **[backend/polygon_integration/README.md](./backend/polygon_integration/README.md)** - Polygon API integration

---

## 🎯 What Is This?

Alpha Kite Max is an automated trading system that:
- 📊 Monitors QQQ in real-time (minute-by-minute)
- 📈 Calculates technical indicators (SMA9, Session VWAP)
- 🎯 Detects trading signals (SMA9/VWAP crosses)
- 🤖 Automatically trades 0DTE options
- 💰 Tracks performance and P&L

### Trading Strategy
- **Down Cross** (SMA9 below VWAP): Sell 25 PUT contracts
- **Up Cross** (SMA9 above VWAP): Sell 25 CALL contracts
- **Profit Target**: 50% of entry credit
- **Stop Loss**: 200% loss
- **Trading Hours**: 10:00 AM - 3:00 PM ET

---

## ✨ Features

### Trading & Analytics
- ✅ Real-time data streaming from Schwab API
- ✅ Automated cross signal detection
- ✅ Automated option trading (paper trading mode)
- ✅ Position and P&L tracking
- ✅ Transaction logging and analytics

### Visualization
- ✅ Interactive price charts with indicators
- ✅ Volume bar charts
- ✅ Cross markers on charts
- ✅ Market hours highlighting
- ✅ Dark mode support

### Infrastructure
- ✅ AWS Lambda for real-time data collection
- ✅ Supabase (PostgreSQL) for data storage
- ✅ Vercel deployment for frontend
- ✅ Comprehensive test suite (19/19 passing)

---

## 🏗️ Tech Stack

### Frontend
- **Framework**: Next.js 15 (React 18)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Deployment**: Vercel

### Backend
- **Language**: Python 3.10
- **API**: Schwab API (schwab-py)
- **Database**: Supabase (PostgreSQL)
- **Cloud**: AWS Lambda, EventBridge, Secrets Manager
- **Infrastructure**: Terraform

### Development Tools
- **Package Manager**: `uv` (Python), `npm` (Node.js)
- **Testing**: pytest, React Testing Library
- **VS Code**: Integrated launch configurations

---

## 🚀 Quick Start Commands

```bash
# Clone repository
git clone https://github.com/MAKaminski/alpha-kite-max.git
cd alpha-kite-max

# Apply database migrations
supabase login
supabase link --project-ref xwcauibwyxhsifnotnzz
supabase db push

# Backend setup
cd backend
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp ../env.example .env  # Edit with your credentials

# Authenticate with Schwab
./reauth_schwab.sh

# Download historical data
python main.py --ticker QQQ --days 5

# Start paper trading
python trading_main.py --mode paper --ticker QQQ
```

**Full Setup Guide**: [GETTING_STARTED.md](./GETTING_STARTED.md)

---

## 📖 Documentation

### Getting Started
- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - 15-minute setup guide
- **[QUICKSTART_OAUTH.md](./QUICKSTART_OAUTH.md)** - Schwab authentication

### Core Documentation
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture and design
- **[SECURITY.md](./SECURITY.md)** - Security best practices
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Contribution guidelines

### Implementation Guides
- **[docs/DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md)** - Testing workflows
- **[docs/FEATURE_REFERENCE.md](./docs/FEATURE_REFERENCE.md)** - Feature documentation
- **[docs/DATA_FLOW.md](./docs/DATA_FLOW.md)** - Data storage and flow

### Component Documentation
- **[backend/README.md](./backend/README.md)** - Backend API reference
- **[frontend/README.md](./frontend/README.md)** - Frontend components
- **[infrastructure/README.md](./infrastructure/README.md)** - Terraform setup

---

## 🔧 Developer Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Schwab Developer Account
- Supabase Account
- AWS Account (optional, for Lambda)

### Backend

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

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp ../env.example .env.local
# Edit .env.local with Supabase credentials

# Run development server
npm run dev
```

Open http://localhost:3000

### VS Code Integration

Press **F5** to access all tasks:
- 🔐 Authentication
- 📥 Download Data
- 📡 Stream Data
- 🧪 Run Tests
- 📈 Trading Engine

See [`.vscode/launch.json`](./.vscode/launch.json) for all configurations.

---

## 🧪 Testing

```bash
# Run all unit tests
cd backend
pytest tests/ -v

# Test trading workflow (paper account)
python test_live_trading_workflow.py

# Or via VS Code
Press F5 → "🧪 Test Live Trading Workflow (Paper Account)"
```

**Testing Guide**: [docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md)

---

## 📊 Project Structure

```
alpha-kite-max/
├── frontend/                # Next.js application
│   ├── src/
│   │   ├── app/            # App router pages
│   │   ├── components/     # React components
│   │   └── lib/            # Utilities
│   └── package.json
├── backend/                # Python services
│   ├── schwab_integration/ # Schwab API integration
│   │   ├── client.py      # API client
│   │   ├── downloader.py  # Data downloader
│   │   ├── streaming.py   # Real-time streaming
│   │   └── trading_engine.py # Trading logic
│   ├── models/            # Pydantic models
│   ├── tests/             # Test suites
│   ├── lambda/            # AWS Lambda functions
│   ├── main.py            # CLI entry point
│   └── requirements.txt
├── supabase/              # Database migrations
│   └── migrations/        # SQL files
├── infrastructure/        # Terraform IaC
│   ├── lambda.tf
│   └── secrets.tf
├── docs/                  # Implementation guides
│   ├── DEPLOYMENT_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── FEATURE_REFERENCE.md
│   └── DATA_FLOW.md
├── .vscode/               # VS Code configurations
│   └── launch.json        # F5 menu tasks
├── GETTING_STARTED.md     # Quick start guide
├── ARCHITECTURE.md        # System design
├── SECURITY.md            # Security policy
└── README.md              # This file
```

---

## 🌟 Key Workflows

### Download Historical Data

**Via VS Code**:
```
Press F5 → "📥 3. Download Historical Data (QQQ, 5 days)"
```

**Via CLI**:
```bash
cd backend
python main.py --ticker QQQ --days 5
```

### Start Paper Trading

**Via VS Code**:
```
Press F5 → "📈 Trading Engine (Paper Trading)"
```

**Via CLI**:
```bash
cd backend
python trading_main.py --mode paper --ticker QQQ
```

### Test Complete Workflow

**Via VS Code**:
```
Press F5 → "🧪 Test Live Trading Workflow (Paper Account)"
```

---

## 🎯 Current Status

### Production Ready
- ✅ All 19 unit tests passing
- ✅ Database migrations applied
- ✅ Trading logic validated
- ✅ Paper trading functional
- ✅ Frontend dashboard complete
- ✅ AWS Lambda deployed
- ✅ Documentation complete

### Trading Hours
- **Active**: 10:00 AM - 2:30 PM ET
- **Close-Only**: 2:30 PM - 3:00 PM ET
- **Market Close**: 3:00 PM ET

### System Metrics
- **Database**: 0.9% of free tier used
- **Lambda**: Within free tier
- **Monthly Cost**: ~$2
- **Uptime**: 99.9% (Vercel + Supabase)

---

## 🛡️ Security

⚠️ **Never commit credentials!**

- Schwab tokens → AWS Secrets Manager (production) or local `.schwab_tokens.json` (dev)
- API keys → Environment variables only
- Database credentials → Supabase Service Role Key (backend only)

**See**: [SECURITY.md](./SECURITY.md) for complete security guidelines

---

## 📈 Performance

### Data Processing
- **Latency**: < 5 seconds from Schwab to database
- **Throughput**: 390 data points/day
- **Storage**: ~4.3 MB/month

### Trading Execution
- **Signal Detection**: Real-time (every minute)
- **Order Submission**: < 2 seconds
- **Position Tracking**: Instant database updates

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) first.

### Quick Contribution Guide
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

### Development Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
pytest tests/

# Commit and push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature
```

---

## 📜 License

This project is licensed under the MIT License with commercial use restrictions. See [LICENSE](./LICENSE) for details.

**Summary**: Free for personal and educational use. Commercial use requires explicit written permission.

---

## 🙋 Support

### Documentation
- **Issues**: [GitHub Issues](https://github.com/MAKaminski/alpha-kite-max/issues)
- **Security**: Email MKaminski1337@Gmail.com
- **Docs**: See [`docs/`](./docs/) folder

### Quick Links
- [Getting Started](./GETTING_STARTED.md)
- [Architecture](./ARCHITECTURE.md)
- [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)
- [Testing Guide](./docs/TESTING_GUIDE.md)

---

## 🎉 Acknowledgments

- **Schwab API**: Charles Schwab for API access
- **schwab-py**: Tyler Bowers for the excellent Python client
- **Supabase**: For the amazing PostgreSQL platform
- **Vercel**: For seamless Next.js deployment

---

**Built with ❤️ for algorithmic traders**

**Last Updated**: October 19, 2025
