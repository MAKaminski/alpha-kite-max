# 📚 Alpha Kite Max - Documentation Map

Quick reference guide for navigating the project documentation.

---

## 🎯 START HERE

**New Developer?** → [GETTING_STARTED.md](./GETTING_STARTED.md) (15-minute setup)

**Experienced?** → [README.md](./README.md#developer-setup) (Jump to Developer Setup)

---

## 📖 Core Documentation (Root Level)

| File | Purpose | When to Read |
|------|---------|--------------|
| [README.md](./README.md) | Project overview, features, quick start | First thing to read |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Complete setup guide | When setting up for the first time |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture and design | Understanding how it all works |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Contribution guidelines | Before submitting PRs |
| [SECURITY.md](./SECURITY.md) | Security policies | Before handling credentials |
| [CHANGELOG.md](./CHANGELOG.md) | Version history | Tracking changes and updates |
| [LICENSE](./LICENSE) | MIT License | Legal information |

---

## 📋 Guides (docs/guides/)

| File | Purpose | When to Use |
|------|---------|-------------|
| [QUICKSTART_OAUTH.md](./docs/guides/QUICKSTART_OAUTH.md) | Schwab OAuth setup | First-time authentication |
| [BLACK_SCHOLES_SYNTHETIC_OPTIONS.md](./docs/guides/BLACK_SCHOLES_SYNTHETIC_OPTIONS.md) | Generate synthetic options data | Testing without real options data |

---

## 🔧 Technical Docs (docs/)

| File | Purpose | When to Use |
|------|---------|-------------|
| [DATA_FLOW.md](./docs/DATA_FLOW.md) | Data flow diagrams | Understanding data persistence |
| [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) | Deploy to production | Deploying to AWS/Vercel |
| [TESTING_GUIDE.md](./docs/TESTING_GUIDE.md) | Testing strategy | Running/writing tests |
| [FEATURE_REFERENCE.md](./docs/FEATURE_REFERENCE.md) | Complete feature list | Feature discovery |
| [POLYGON.md](./docs/POLYGON.md) | Polygon.io integration | Using Polygon API |

---

## 📊 Status Reports (docs/status/)

| File | Purpose | When to Check |
|------|---------|---------------|
| [PROJECT_STATUS.md](./docs/status/PROJECT_STATUS.md) | Current project status | Before starting work |
| [FINAL_DEPLOYMENT_STATUS.md](./docs/status/FINAL_DEPLOYMENT_STATUS.md) | Deployment status | Before deploying |

---

## 📦 Backend Documentation (backend/)

| File | Purpose | When to Use |
|------|---------|-------------|
| [README.md](./backend/README.md) | Backend overview | Backend development |
| [TESTING.md](./backend/TESTING.md) | Backend testing | Running backend tests |
| [env.template](./backend/env.template) | Environment variables | Setting up .env file |

### Backend Subsystems

| Path | Purpose |
|------|---------|
| [polygon_integration/README.md](./backend/polygon_integration/README.md) | Polygon API integration |
| [black_scholes/](./backend/black_scholes/) | Synthetic options generation |
| [schwab_integration/](./backend/schwab_integration/) | Schwab API wrapper |
| [tests/](./backend/tests/) | Test suite |

---

## 🗂️ Archive (docs/archive/)

Historical and deprecated documentation. Reference only.

| File | Status |
|------|--------|
| POLYGON_API_STATUS.md | Archived - See docs/POLYGON.md |
| POLYGON_IMPLEMENTATION_STATUS.md | Archived - See docs/POLYGON.md |
| POLYGON_INTEGRATION_GUIDE.md | Archived - See docs/POLYGON.md |
| POLYGON_S3_STATUS.md | Archived - See docs/POLYGON.md |
| POLYGON_SETUP_GUIDE.md | Archived - See docs/POLYGON.md |
| POLYGON_TIER_LIMITATIONS.md | Archived - See docs/POLYGON.md |
| SECURITY_INCIDENT_REPORT.md | Archived - Historical record |

---

## 🔍 Quick Find

### I want to...

| Goal | Go Here |
|------|---------|
| **Set up the project** | [GETTING_STARTED.md](./GETTING_STARTED.md) |
| **Authenticate with Schwab** | [docs/guides/QUICKSTART_OAUTH.md](./docs/guides/QUICKSTART_OAUTH.md) |
| **Generate test data** | [docs/guides/BLACK_SCHOLES_SYNTHETIC_OPTIONS.md](./docs/guides/BLACK_SCHOLES_SYNTHETIC_OPTIONS.md) |
| **Deploy to production** | [docs/DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) |
| **Run tests** | [docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md) |
| **Understand data flow** | [docs/DATA_FLOW.md](./docs/DATA_FLOW.md) |
| **Configure environment** | [backend/env.template](./backend/env.template) |
| **Use Polygon API** | [docs/POLYGON.md](./docs/POLYGON.md) |
| **Check project status** | [docs/status/PROJECT_STATUS.md](./docs/status/PROJECT_STATUS.md) |

---

## 📝 Environment Configuration

| File | Purpose | Location |
|------|---------|----------|
| `backend/env.template` | Backend environment variables template | Copy to `backend/.env` |
| `env.example` | Frontend environment variables template | Copy to `frontend/.env.local` |

### Required Environment Variables

**Backend (backend/.env):**
- ✅ SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET (Required)
- ✅ SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (Required)
- ⚠️ POLYGON_API (Optional - stock data only)

**Frontend (frontend/.env.local):**
- ✅ NEXT_PUBLIC_SUPABASE_URL (Required)
- ✅ NEXT_PUBLIC_SUPABASE_ANON_KEY (Required)

See [backend/env.template](./backend/env.template) for complete details.

---

## 🎯 Documentation by Task

### First-Time Setup
1. [README.md](./README.md) - Overview
2. [GETTING_STARTED.md](./GETTING_STARTED.md) - Setup guide
3. [backend/env.template](./backend/env.template) - Configure environment
4. [docs/guides/QUICKSTART_OAUTH.md](./docs/guides/QUICKSTART_OAUTH.md) - Authenticate

### Development
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - Understand the system
2. [docs/DATA_FLOW.md](./docs/DATA_FLOW.md) - Data persistence
3. [docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md) - Write tests
4. [CONTRIBUTING.md](./CONTRIBUTING.md) - Code standards

### Deployment
1. [docs/status/PROJECT_STATUS.md](./docs/status/PROJECT_STATUS.md) - Check status
2. [docs/DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) - Deploy
3. [docs/status/FINAL_DEPLOYMENT_STATUS.md](./docs/status/FINAL_DEPLOYMENT_STATUS.md) - Verify

---

*Last Updated: October 19, 2025*
*Total Documentation Files: 30+ organized across 4 categories*
