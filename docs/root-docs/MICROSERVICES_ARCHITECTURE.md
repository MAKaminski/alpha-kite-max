# Alpha Kite Max - Microservices Architecture

## Overview

Alpha Kite Max is built as a distributed microservices architecture with each service running independently and communicating through Supabase as the central data layer.

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     MICROSERVICES ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│  Schwab WebSocket    │  ← Real-time market data
│  (Market Data Source)│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  MICROSERVICE #1: Data Streaming (Lightsail)                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  • Perpetual streaming service                             │  │
│  │  • Streams equity prices every second                      │  │
│  │  • Calculates real-time indicators (SMA9, VWAP)            │  │
│  │  • Writes to Supabase every second                         │  │
│  │  • Auto-restart on failures                                │  │
│  │  • Cost: $3.50/month                                       │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   SUPABASE DATABASE   │
                    │  (Central Data Layer) │
                    │                       │
                    │  Tables:              │
                    │  • equity_data        │
                    │  • indicators         │
                    │  • option_prices      │
                    │  • positions          │
                    │  • trades             │
                    │  • trading_signals    │
                    │  • daily_pnl          │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
┌───────────────────────────┐   ┌──────────────────────────┐
│  MICROSERVICE #2:         │   │  MICROSERVICE #3:        │
│  Frontend (Vercel)        │   │  Trading Engine (Future) │
│  ┌─────────────────────┐  │   │  ┌────────────────────┐  │
│  │ • Trade submission  │  │   │  │ • Auto-trading     │  │
│  │ • Real-time charts  │  │   │  │ • Signal detection │  │
│  │ • Portfolio view    │  │   │  │ • Risk management  │  │
│  │ • P&L tracking      │  │   │  │ • Order execution  │  │
│  └─────────────────────┘  │   │  └────────────────────┘  │
└───────────────────────────┘   └──────────────────────────┘
```

## 🎯 Microservices

### 1️⃣ Data Streaming Service (✅ IMPLEMENTED)

**Location**: `infrastructure/lightsail/`  
**Platform**: AWS Lightsail  
**Status**: Production-ready  

**Responsibilities**:
- Stream real-time equity prices from Schwab WebSocket
- Calculate technical indicators (SMA9, VWAP) in real-time
- Write data to Supabase **every second**
- Monitor service health
- Auto-recover from failures

**Configuration**:
```bash
STREAM_TICKER=QQQ
BATCH_SIZE=1          # Write every tick
BATCH_INTERVAL=1      # Flush every second
```

**Endpoints**: None (streaming service)  
**Database Access**: Service role (write access)  
**Cost**: $3.50/month  

**Key Features**:
- ✅ Real-time streaming (every second)
- ✅ Automatic failover and restart
- ✅ Health monitoring
- ✅ Structured logging
- ✅ Market hours detection

---

### 2️⃣ Frontend Service (🚧 IN PROGRESS)

**Location**: `frontend/`  
**Platform**: Vercel (Next.js)  
**Status**: In development  

**Responsibilities**:
- Display real-time equity prices and charts
- Submit manual trades
- Show portfolio positions
- Display P&L and performance metrics
- Provide trading controls

**Features**:
- Real-time price updates (via Supabase realtime)
- Trade submission interface
- Portfolio dashboard
- Historical charts
- Risk metrics

**Database Access**: Anonymous (read-only)  
**Cost**: Free (Vercel hobby plan)  

---

### 3️⃣ Trading Engine Service (📋 PLANNED)

**Location**: TBD  
**Platform**: AWS Lightsail or ECS  
**Status**: Not yet implemented  

**Responsibilities**:
- Detect trading signals from indicators
- Execute automated trades
- Manage risk and position sizing
- Track P&L in real-time
- Handle order routing to Schwab

**Features** (planned):
- Signal detection (SMA9/VWAP crossovers)
- Automated trade execution
- Risk management rules
- Position tracking
- Performance analytics

**Database Access**: Service role (read/write)  

---

## 🔄 Data Flow

### Real-Time Market Data Flow

```
1. Schwab WebSocket → Data Streaming Service
   ↓
2. Data Streaming Service → Processes & Calculates Indicators
   ↓
3. Data Streaming Service → Supabase (every second)
   ↓
4. Supabase Realtime → Frontend (instant updates)
   ↓
5. Frontend → User sees live data
```

### Trade Submission Flow

```
1. User → Frontend (submit trade)
   ↓
2. Frontend → Supabase (insert trade record)
   ↓
3. Trading Engine → Detects new trade (listening to Supabase)
   ↓
4. Trading Engine → Schwab API (execute trade)
   ↓
5. Trading Engine → Supabase (update trade status)
   ↓
6. Supabase Realtime → Frontend (trade confirmation)
   ↓
7. Frontend → User sees confirmation
```

### Automated Trading Flow

```
1. Data Streaming Service → Writes indicator data to Supabase
   ↓
2. Trading Engine → Detects indicator crossover
   ↓
3. Trading Engine → Generates trading signal
   ↓
4. Trading Engine → Writes signal to Supabase
   ↓
5. Trading Engine → Executes trade via Schwab API
   ↓
6. Trading Engine → Updates positions/trades in Supabase
   ↓
7. Frontend → Shows updated positions (via realtime)
```

---

## 🗄️ Supabase as Central Data Layer

### Why Supabase?

1. **Single Source of Truth**: All services read/write from one database
2. **Real-time Updates**: Built-in pub/sub for instant frontend updates
3. **Authentication**: Integrated auth for frontend users
4. **Row Level Security**: Fine-grained access control per service
5. **API Auto-generation**: REST and GraphQL APIs out of the box
6. **Cost-effective**: Free tier supports our use case

### Access Patterns

| Service | Access Type | Key |
|---------|-------------|-----|
| Data Streaming | Service Role (full access) | `SUPABASE_SERVICE_ROLE_KEY` |
| Frontend | Anonymous (read-only) | `SUPABASE_ANON_KEY` |
| Trading Engine | Service Role (full access) | `SUPABASE_SERVICE_ROLE_KEY` |

### Real-time Subscriptions

Frontend subscribes to these tables for live updates:
- `equity_data` - Live price updates
- `positions` - Position changes
- `trades` - Trade confirmations
- `trading_signals` - New signals

---

## 🚀 Deployment Strategy

### Current State

✅ **Microservice #1 (Data Streaming)**: Deployed to Lightsail  
🚧 **Microservice #2 (Frontend)**: Local development  
📋 **Microservice #3 (Trading Engine)**: Not yet built  

### Deployment Process

#### Data Streaming Service
```bash
cd infrastructure/lightsail
./deploy.sh
```

#### Frontend
```bash
cd frontend
vercel deploy --prod
```

#### Trading Engine (Future)
```bash
# TBD - likely similar to data streaming
cd infrastructure/trading-engine
./deploy.sh
```

---

## 🔒 Security Model

### Service Isolation

Each service runs independently:
- **Data Streaming**: No public endpoints, writes to Supabase only
- **Frontend**: Public, read-only database access
- **Trading Engine**: No public endpoints, full database access

### API Keys & Secrets

| Secret | Used By | Stored In |
|--------|---------|-----------|
| `SCHWAB_APP_KEY` | Data Streaming, Trading Engine | Environment variables |
| `SCHWAB_APP_SECRET` | Data Streaming, Trading Engine | Environment variables |
| `SUPABASE_SERVICE_ROLE_KEY` | Data Streaming, Trading Engine | Environment variables |
| `SUPABASE_ANON_KEY` | Frontend | Environment variables |
| `SUPABASE_URL` | All services | Environment variables |

### Network Security

- **Data Streaming**: No inbound traffic (outbound only)
- **Frontend**: Public HTTPS only
- **Trading Engine**: No inbound traffic (outbound only)
- **Supabase**: HTTPS with API key authentication

---

## 💰 Cost Breakdown

| Service | Platform | Monthly Cost |
|---------|----------|--------------|
| Data Streaming | AWS Lightsail (Nano) | $3.50 |
| Frontend | Vercel (Hobby) | $0.00 |
| Trading Engine | AWS Lightsail (Small) | ~$5.00 (future) |
| Supabase | Free tier | $0.00 |
| **Total** | | **$3.50** (currently) |

### Scaling Costs

As we scale:
- More tickers → More Lightsail instances ($3.50 each)
- More data → Supabase Pro ($25/month)
- High traffic → Vercel Pro ($20/month)

---

## 📊 Monitoring & Observability

### Per-Service Monitoring

**Data Streaming Service**:
- Health check script: `python health_check.py`
- Logs: `sudo docker-compose logs -f`
- Metrics table: `streaming_metrics` in Supabase

**Frontend**:
- Vercel analytics (built-in)
- Browser console logs
- Supabase query performance

**Trading Engine** (future):
- Health endpoints
- Trade execution logs
- Error tracking

### Centralized Monitoring (Future)

Consider adding:
- CloudWatch for Lightsail metrics
- Sentry for error tracking
- Datadog/New Relic for APM
- Custom dashboard in frontend

---

## 🔄 Service Communication

### Communication Pattern: Event-Driven via Database

Services don't call each other directly. Instead:

1. **Write to database**: Service A writes data
2. **Database triggers**: Supabase realtime or triggers
3. **Service B reacts**: Reads new data and acts

**Benefits**:
- Loose coupling
- No service discovery needed
- Automatic retry via database
- Easy to add new services

**Example**:
```
Frontend writes trade → Trading Engine listens → Executes trade
```

---

## 🎯 Roadmap

### Phase 1: Foundation (✅ COMPLETE)
- [x] Data streaming service
- [x] Supabase schema
- [x] Real-time equity data
- [x] Indicator calculations

### Phase 2: User Interface (🚧 IN PROGRESS)
- [ ] Frontend deployment to Vercel
- [ ] Real-time charts
- [ ] Trade submission interface
- [ ] Portfolio dashboard

### Phase 3: Automation (📋 PLANNED)
- [ ] Trading engine service
- [ ] Signal detection
- [ ] Automated trade execution
- [ ] Risk management

### Phase 4: Enhancement (📋 PLANNED)
- [ ] Multi-ticker support
- [ ] Options trading
- [ ] Backtesting service
- [ ] Advanced analytics

---

## 🛠️ Development Workflow

### Local Development

Each service can be developed independently:

```bash
# Data Streaming (local testing)
cd infrastructure/lightsail
python streaming_service.py

# Frontend (local dev server)
cd frontend
npm run dev

# Trading Engine (future)
cd backend
python trading_main.py
```

### Testing

```bash
# Data Streaming
cd infrastructure/lightsail
python health_check.py

# Frontend
cd frontend
npm test

# Integration
# Use Supabase as test database with separate project
```

### Deployment

Each service deploys independently:
- **Data Streaming**: `./deploy.sh` (Lightsail)
- **Frontend**: `vercel deploy --prod`
- **Trading Engine**: TBD

---

## 📚 Documentation per Service

### Data Streaming Service
- [QUICKSTART.md](infrastructure/lightsail/QUICKSTART.md)
- [README.md](infrastructure/lightsail/README.md)
- [SCHEMA.md](infrastructure/lightsail/SCHEMA.md)

### Frontend
- [README.md](frontend/README.md)

### Shared
- [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
- This file - Microservices architecture

---

## ✅ Best Practices

### Service Design
- ✅ Each service has one responsibility
- ✅ Services communicate via database
- ✅ Services can restart independently
- ✅ No direct service-to-service calls

### Data Management
- ✅ Supabase is single source of truth
- ✅ Use Row Level Security (RLS)
- ✅ Separate service roles and anonymous access
- ✅ Real-time subscriptions for live updates

### Deployment
- ✅ Each service has own deployment script
- ✅ Environment-specific configuration
- ✅ Health checks for each service
- ✅ Automated restarts on failure

### Security
- ✅ Principle of least privilege
- ✅ No hardcoded credentials
- ✅ Environment variables for secrets
- ✅ HTTPS everywhere

---

## 🎉 Summary

**Current Architecture**:
- ✅ Microservice #1: Data streaming to Supabase (every second)
- ✅ Central data layer: Supabase with real-time capabilities
- 🚧 Microservice #2: Frontend for trade submission (in progress)
- 📋 Microservice #3: Trading engine (planned)

**Key Characteristics**:
- Event-driven communication via database
- Independent deployment and scaling
- Cost-effective ($3.50/month currently)
- Production-ready monitoring and health checks

**Next Steps**:
1. Complete frontend deployment
2. Build trade submission interface
3. Implement trading engine service

---

*Last Updated: October 21, 2025*  
*Architecture Version: 1.0*  
*Current Services: 1/3 deployed*

