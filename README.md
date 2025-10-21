# Alpha Kite Max

Real-time trading dashboard with automated 0DTE options trading based on SMA9/VWAP cross signals.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Trading Status](https://img.shields.io/badge/Trading-Paper%20Trading%20Ready-green.svg)](docs/LIVE_TRADING_READINESS.md)

---

## 🚀 Architecture: Lightsail Microservices

**Current Setup:**
- ✅ AWS Lightsail for perpetual data streaming ($3.50/month)
- ✅ Streams equity/options data **every second** to Supabase
- ✅ Vercel for frontend deployment
- ✅ Complete microservices architecture

**📚 [Read Complete Architecture Guide](docs/root-docs/MICROSERVICES_ARCHITECTURE.md)**

---

## ⚡ Quick Start

### New Users
👉 **[GETTING STARTED GUIDE](docs/root-docs/GETTING_STARTED.md)** (15-minute setup)

### Deploy Streaming Service
```bash
cd infrastructure/lightsail
cp env.template .env  # Add your credentials
./deploy.sh
```

📖 **[Lightsail Deployment Guide](infrastructure/lightsail/README.md)**

---

## 📚 Documentation

### 🎯 Essential Guides
| Guide | Purpose |
|-------|---------|
| [GETTING_STARTED.md](docs/root-docs/GETTING_STARTED.md) | Complete setup (start here!) |
| [MICROSERVICES_ARCHITECTURE.md](docs/root-docs/MICROSERVICES_ARCHITECTURE.md) | System architecture |
| [ARCHITECTURE.md](docs/root-docs/ARCHITECTURE.md) | Technical details |
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Production deployment |

### 🔧 Reference
| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](docs/root-docs/CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](docs/root-docs/SECURITY.md) | Security best practices |
| [CHANGELOG.md](docs/root-docs/CHANGELOG.md) | Version history |
| [ENV_FILE_GUIDE.md](docs/root-docs/ENV_FILE_GUIDE.md) | Environment variables |

### 📊 Implementation Guides
- [Schwab OAuth Setup](docs/guides/QUICKSTART_OAUTH.md)
- [Testing Guide](docs/TESTING_GUIDE.md)
- [Feature Reference](docs/FEATURE_REFERENCE.md)
- [Data Flow](docs/DATA_FLOW.md)
- [Polygon.io Integration](docs/POLYGON.md)

### 🚀 Deployment
- [Lightsail Quickstart](infrastructure/lightsail/QUICKSTART.md)
- [Database Schema](infrastructure/lightsail/SCHEMA.md)
- [Monitoring Guide](infrastructure/lightsail/MONITORING.md)
- [Testing & Observability](infrastructure/lightsail/TESTING_OBSERVABILITY.md)

---

## 🎯 What Is This?

Alpha Kite Max is an automated trading system that:
- 📊 Monitors QQQ in real-time (every second)
- 📈 Calculates technical indicators (SMA9, Session VWAP)
- 🎯 Detects trading signals (SMA9/VWAP crosses)
- 🤖 Automatically trades 0DTE options
- 💰 Tracks performance and P&L

---

## 🏗️ Tech Stack

### Frontend
- **Framework**: Next.js 15 (React 18)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Deployment**: Vercel

### Backend
- **Language**: Python 3.10
- **API**: Schwab API (schwab-py)
- **Database**: Supabase (PostgreSQL)
- **Streaming**: AWS Lightsail (Docker)

### Infrastructure
- **AWS Lightsail**: $3.50/month (nano instance)
- **Supabase**: Free tier
- **Total Cost**: $3.50/month

---

## 💰 Cost & Performance

| Metric | Value |
|--------|-------|
| **Monthly Cost** | $3.50 |
| **Data Latency** | <2 seconds |
| **Update Frequency** | Every 1 second |
| **Uptime** | 99.9%+ |

---

## 🚀 Deployment Status

- ✅ Microservices architecture implemented
- ✅ Lightsail streaming service ready
- ✅ Database schema optimized
- ✅ Documentation complete
- ✅ Monitoring tools ready

---

## 🛡️ Security

⚠️ **Never commit credentials!**

- Schwab tokens → `.env` file (gitignored)
- API keys → Environment variables
- Database credentials → Supabase Service Role Key

**See**: [Security Guide](docs/root-docs/SECURITY.md)

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](docs/root-docs/CONTRIBUTING.md) first.

---

## 📜 License

MIT License with commercial use restrictions. See [LICENSE](LICENSE) for details.

**Summary**: Free for personal/educational use. Commercial use requires permission.

---

## 🔗 Quick Links

- **[AWS Lightsail Console](https://lightsail.aws.amazon.com/)** - Monitor service
- **[Supabase Dashboard](https://app.supabase.com/)** - View database
- **[GitHub Issues](https://github.com/MAKaminski/alpha-kite-max/issues)** - Report bugs

---

## 📞 Support

- **Documentation**: See [docs/](docs/) folder
- **Security**: Email MKaminski1337@Gmail.com
- **Issues**: Use [GitHub Issues](https://github.com/MAKaminski/alpha-kite-max/issues)

---

**Built with ❤️ for algorithmic traders**

**Last Updated**: October 21, 2025
