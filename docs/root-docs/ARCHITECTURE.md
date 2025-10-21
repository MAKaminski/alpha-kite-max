# Alpha Kite Max - System Architecture

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Infrastructure & Deployment](#infrastructure--deployment)
6. [Cost Analysis](#cost-analysis)
7. [Execution Frequency & Scheduling](#execution-frequency--scheduling)
8. [Security & Access Control](#security--access-control)
9. [Monitoring & Observability](#monitoring--observability)
10. [Scalability & Performance](#scalability--performance)

---

## System Overview

**Alpha Kite Max** is a real-time trading dashboard that streams equity market data, calculates technical indicators (SMA9, Session VWAP), and provides interactive data visualization using a microservices architecture.

### Key Characteristics

- **Architecture**: Microservices (AWS Lightsail + Vercel + Supabase)
- **Data Source**: Charles Schwab WebSocket API (OAuth 2.0)
- **Update Frequency**: Every second (real-time streaming)
- **Data Granularity**: Second-level price/volume ticks
- **Default Ticker**: QQQ (Invesco QQQ Trust)
- **Operating Hours**: During market hours (9:30 AM - 4:00 PM ET)
- **Latency Target**: < 2 seconds from market data to database

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Vercel (Frontend Hosting)                       │    │
│  │  - Next.js 15 Application (App Router)                       │    │
│  │  - TypeScript, Tailwind CSS                                  │    │
│  │  - Recharts (Data Visualization)                             │    │
│  │  - Real-time chart updates via client-side polling           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             ↓ HTTPS                                  │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE LAYER                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Supabase (PostgreSQL)                           │    │
│  │                                                              │    │
│  │  Tables:                                                     │    │
│  │    • equity_data (ticker, timestamp, price, volume)          │    │
│  │    • indicators (ticker, timestamp, sma9, vwap)              │    │
│  │                                                              │    │
│  │  Indexes:                                                    │    │
│  │    • (ticker, timestamp) - B-tree for time-series queries    │    │
│  │                                                              │    │
│  │  RLS Policies: Public read access                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             ↑ REST API                               │
└──────────────────────────────────────────────────────────────────────┘
                                ↑
┌──────────────────────────────────────────────────────────────────────┐
│                   DATA INGESTION LAYER (AWS Lightsail)                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  AWS Lightsail Instance (Nano - $3.50/month)               │     │
│  │  • Perpetual streaming service (Docker)                     │     │
│  │  • Streams data every second                                │     │
│  │  • Auto-restart on failures                                 │     │
│  │  • Health monitoring built-in                               │     │
│  └────────────────────────────────────────────────────────────┘     │
│                             ↓ Streaming                              │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Streaming Service (Python)                                 │     │
│  │  • Schwab WebSocket connection                              │     │
│  │  • Real-time indicator calculation                          │     │
│  │  • Batch writes every second                                │     │
│  │  • Structured logging                                       │     │
│  │                                                             │     │
│  │  Dependencies:                                              │     │
│  │    - schwab-py (Schwab API client)                          │     │
│  │    - pandas (data processing)                               │     │
│  │    - supabase-py (database client)                          │     │
│  │    - structlog (structured logging)                         │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                                ↑
┌──────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCE                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Schwab API (api.schwab.com)                     │    │
│  │  • Endpoint: /marketdata/v1/pricehistory                     │    │
│  │  • Authentication: OAuth 2.0 (Authorization Code Flow)       │    │
│  │  • Rate Limits: 120 requests/minute                          │    │
│  │  • Data: 1-minute OHLCV candles                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 0. Backend Project Structure

The Python backend is organized into several key directories:

**`backend/schwab_integration/`**: Schwab API integration layer
- `client.py`: Wrapper around schwab-py official client
- `downloader.py`: Historical data download orchestration
- `streaming.py`: Real-time data streaming logic
- `config.py`: Configuration models using Pydantic
- `trading_engine.py`: Trading execution engine

**`backend/models/`**: Pydantic data models
- `trading.py`: Trading-related models (positions, orders, P&L)

**`backend/tests/`**: Test suites
- `test_schwab/`: Unit tests for Schwab integration
- `test_supabase/`: Unit tests for database operations
- `integration/`: End-to-end integration tests
- `test_paper_trading.py`: Paper trading system tests
- `test_current_day.py`: Current trading day tests
- `fortified_test_suite.py`: Comprehensive test suite

**`backend/sys_testing/`**: System testing and ad-hoc utilities
- OAuth scripts: `auto_reauth.py`, `reauth_schwab.py`, `get_auth_url.py`
- Diagnostics: `token_diagnostics.py`, `check_data_status.py`
- Utilities: `download_missing_data.py`, `fortified_token_manager.py`
- See `backend/sys_testing/README.md` for detailed documentation

**`backend/lambda/`**: AWS Lambda deployment
- `real_time_streamer.py`: Lambda function handler
- `token_manager.py`: Token refresh logic
- `monitoring.py`: CloudWatch metrics utilities
- `deploy_*.sh`: Deployment scripts using `uv`

**`backend/`** (root):
- `main.py`: CLI entry point for data download
- `trading_main.py`: CLI entry point for paper trading
- `etl_pipeline.py`: ETL orchestration
- `supabase_client.py`: Database CRUD operations

---

### 1. Frontend (Vercel + Next.js)

#### Technology Stack
- **Framework**: Next.js 15.0 (React 18)
- **Language**: TypeScript 5.x
- **Styling**: Tailwind CSS 3.x
- **Charts**: Recharts 2.x (D3.js wrapper)
- **State Management**: React Hooks (useState, useEffect)
- **Data Fetching**: Supabase JS Client

#### Key Components

**Dashboard** (`frontend/src/components/Dashboard.tsx`)
- Fetches equity data and indicators from Supabase
- Paginated data retrieval (1000 rows per page)
- Date navigation (previous/next day, date picker)
- Real-time polling (every 60 seconds during market hours)
- Cross detection for SMA9/VWAP intersections

**EquityChart** (`frontend/src/components/EquityChart.tsx`)
- Responsive line chart with multiple data series
- Time series: Price, SMA9, VWAP
- Cross markers (red circles at intersection points)
- Market hours highlighting (lighter background for 9:30 AM - 4:00 PM ET)
- Timezone conversion to EST for all labels

**SignalsDashboard** (`frontend/src/components/SignalsDashboard.tsx`)
- Table of detected SMA9/VWAP crosses
- Columns: Time, Value, Direction (up/down)
- Prevents consecutive same-direction crosses

**ESTClock** (`frontend/src/components/ESTClock.tsx`)
- Real-time clock displaying current time in EST
- Format: HH:MM:SS:MS
- Updates every 100ms

#### Deployment Configuration
- **Platform**: Vercel (Next.js optimized)
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Node Version**: 18.x
- **Environment Variables**:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

#### Performance Optimizations
- Static generation for layout components
- Client-side data fetching for dynamic content
- Memoized chart calculations
- Debounced date navigation

---

### 2. Database (Supabase)

#### PostgreSQL Schema

**Table: `equity_data`**
```sql
CREATE TABLE equity_data (
  id BIGSERIAL PRIMARY KEY,
  ticker TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  price NUMERIC(10, 2) NOT NULL,
  volume BIGINT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_equity_data_ticker_timestamp 
  ON equity_data (ticker, timestamp);
```

**Table: `indicators`**
```sql
CREATE TABLE indicators (
  id BIGSERIAL PRIMARY KEY,
  ticker TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  sma9 NUMERIC(10, 2),
  vwap NUMERIC(10, 2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_indicators_ticker_timestamp 
  ON indicators (ticker, timestamp);
```

#### Data Retention
- **Current Policy**: Unlimited retention (for historical analysis)
- **Estimated Growth**: 
  - 390 rows/day × 22 days/month = 8,580 rows/month
  - ~100 KB/month (PostgreSQL row overhead + indexes)
  - Annual: ~1.2 MB

#### Row-Level Security (RLS)
```sql
-- Public read access for frontend
ALTER TABLE equity_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON equity_data
  FOR SELECT USING (true);

ALTER TABLE indicators ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON indicators
  FOR SELECT USING (true);
```

#### API Access
- **Client**: Supabase JS Client (frontend) + Supabase Python Client (Lambda)
- **Authentication**: Service Role Key (backend), Anon Key (frontend)
- **RLS**: Enabled for all tables

---

### 3. Data Ingestion Pipeline (AWS Lightsail)

#### Streaming Service Specifications

| Property | Value |
|----------|-------|
| **Platform** | AWS Lightsail (Nano instance) |
| **Runtime** | Python 3.10 (Docker container) |
| **Service** | `infrastructure/lightsail/streaming_service.py` |
| **Memory** | 512 MB |
| **Execution** | Perpetual (always running) |
| **Update Frequency** | Every 1 second |
| **Deployment** | Via `infrastructure/lightsail/deploy.sh` |

#### Execution Flow

1. **Market Hours Check**
   - Convert current UTC time to EST
   - Verify 9:30 AM - 4:00 PM ET, Monday-Friday
   - Skip execution if market closed

2. **Token Retrieval**
   - Fetch Schwab OAuth token from AWS Secrets Manager
   - Check token expiration (7 days)
   - Refresh if needed using `schwab-py` client

3. **Data Download**
   - Call Schwab API: `GET /marketdata/v1/pricehistory`
   - Parameters: `ticker=QQQ`, `period=1 day`, `frequency=1 minute`
   - Response: JSON with OHLCV candles

4. **Indicator Calculation**
   - **SMA9**: Simple Moving Average over 9 periods
     ```python
     df['sma9'] = df['close'].rolling(window=9).mean()
     ```
   - **Session VWAP**: Volume-weighted average price (resets at 9:30 AM ET)
     ```python
     df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
     ```

5. **Data Upload**
   - Upsert equity data to `equity_data` table
   - Upsert indicators to `indicators` table
   - Use `ON CONFLICT (ticker, timestamp) DO UPDATE` for idempotency

6. **Logging**
   - Structured JSON logs to CloudWatch
   - Metrics: data points fetched, upload success, latency

#### Error Handling
- **Token Errors**: Log error, trigger SNS alert (future)
- **Schwab API Errors**: Retry with exponential backoff
- **Supabase Errors**: Log and alert (does not fail entire function)
- **Market Closed**: Return success with `skipped: true`

---

### 4. Streaming Service (Perpetual Operation)

#### Operating Model

The streaming service runs perpetually on AWS Lightsail:

**Characteristics:**
- **Always On**: No scheduling needed - service runs 24/7
- **Market Hours Detection**: Built-in check (9:30 AM - 4:00 PM ET)
- **Auto-restart**: Docker container restarts on failure
- **Health Monitoring**: Built-in health check script

**Data Flow:**
```
Schwab WebSocket → Streaming Service (1-second batches) → Supabase
```

**Writes per day**: ~23,400 records (during 6.5 hour trading session)

---

### 5. Secret Management (Environment Variables)

#### Schwab OAuth Token

**Storage Location**: `backend/config/schwab_token.json` (development)

**Lightsail Production**: Stored in `.env` file on Lightsail instance

**Token Data**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2t...",
  "expires_at": "2024-10-23T12:00:00Z",
  "token_type": "Bearer"
}
```

**Rotation Policy**: Manual (7-day token expiration)

**Access Control**: File permissions (chmod 600) on Lightsail instance

---

### 6. Monitoring (Docker Logs + Supabase)

#### Docker Container Logs

**Access**: SSH into Lightsail instance

**Command**: `sudo docker-compose logs -f`

**Log Format**: JSON (structured logging via `structlog`)

**Sample Log Entry**:
```json
{
  "timestamp": "2024-10-16T13:30:15.123Z",
  "level": "info",
  "event": "data_uploaded_successfully",
  "ticker": "QQQ",
  "equity_rows": 1,
  "indicator_rows": 1,
  "latest_timestamp": "2024-10-16T13:30:00Z"
}
```

#### Supabase Metrics Table

**Table**: `streaming_metrics`

**Tracks**:
- Records processed per batch
- Processing time
- Error counts
- Service status

**Query Health**:
```sql
SELECT * FROM get_streaming_health('QQQ');
```

#### Health Check Script

**Local/Remote**: `python health_check.py`

**Checks**:
- Database connectivity
- Data freshness (< 1 minute old)
- Recent data presence
- Error rates

---

## Data Flow

### Real-Time Data Ingestion Flow

```
1. EventBridge Cron Trigger (every minute)
        ↓
2. Lambda Function Invocation
        ↓
3. Market Hours Check
        ↓ (if market open)
4. Retrieve Schwab Token from Secrets Manager
        ↓
5. Call Schwab API: GET /marketdata/v1/pricehistory?ticker=QQQ&period=1day&frequency=1min
        ↓
6. Parse JSON Response → Pandas DataFrame
        ↓
7. Calculate Indicators (SMA9, Session VWAP)
        ↓
8. Upsert to Supabase (equity_data + indicators tables)
        ↓
9. Log Metrics to CloudWatch
        ↓
10. Return Success Response
```

### Frontend Data Retrieval Flow

```
1. User Opens Dashboard (https://your-app.vercel.app)
        ↓
2. Next.js Server-Side Rendering (initial page load)
        ↓
3. Client-Side: Fetch Data from Supabase
        ↓
4. Query: SELECT * FROM equity_data WHERE ticker='QQQ' AND timestamp >= '2024-10-16' ORDER BY timestamp
        ↓
5. Paginated Retrieval (1000 rows per request)
        ↓
6. Join with Indicators: LEFT JOIN indicators USING (ticker, timestamp)
        ↓
7. Render Chart with Recharts
        ↓
8. Detect SMA9/VWAP Crosses
        ↓
9. Display Cross Markers on Chart
        ↓
10. Set Interval: Refetch Every 60 Seconds (during market hours)
```

---

## Infrastructure & Deployment

### Terraform Configuration

**Provider**: AWS (v5.0+)

**Resources Created**:
- **Lambda Function**: `aws_lambda_function.real_time_streamer`
- **IAM Role**: `aws_iam_role.lambda_role`
- **IAM Policy**: `aws_iam_role_policy.lambda_policy`
- **EventBridge Rules** (3): Market open, midday, close
- **EventBridge Targets** (3): Lambda invocations
- **Lambda Permissions** (3): Allow EventBridge to invoke
- **Secrets Manager Secret**: `aws_secretsmanager_secret.schwab_token`
- **CloudWatch Log Group**: `/aws/lambda/alpha-kite-real-time-streamer`
- **S3 Bucket**: `alpha-kite-max-lambda-deployments-{random-suffix}` (for Lambda code)

**State Management**: Local state file (not recommended for production)

**Recommended**: Use Terraform Cloud or S3 backend for state locking

### Deployment Process

```bash
# 1. Package Lambda function with dependencies
cd backend
./deploy_lambda.sh

# This script:
# - Creates lambda/package/ directory
# - Installs Python dependencies to package/
# - Copies Lambda code and parent modules
# - Creates lambda_deployment.zip (~80 MB)
# - Uploads to S3 bucket
# - Runs terraform apply
```

**Deployment Time**: ~5 minutes (first deploy), ~2 minutes (updates)

**Zero Downtime**: Lambda updates are atomic (new version deployed before old removed)

---

## Cost Analysis

### Monthly Cost Breakdown

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **AWS Lambda** | | | |
| Invocations | 8,580/month | $0.20 per 1M requests | $0.00 (Free Tier) |
| Compute | 8,580 × 256 MB × 5 sec avg | $0.0000166667 per GB-second | $0.18 |
| **AWS Secrets Manager** | 1 secret | $0.40/month | $0.40 |
| **AWS CloudWatch** | | | |
| Log Storage | ~500 MB/month (14-day retention) | $0.50 per GB | $0.25 |
| Metrics | 4 custom metrics | $0.30 per metric | $1.20 |
| **AWS EventBridge** | 8,580 events/month | Free | $0.00 |
| **AWS S3** | 80 MB Lambda package | $0.023 per GB | $0.00 |
| **Supabase** | Free tier | 500 MB database, 5 GB egress | $0.00 |
| **Vercel** | Free tier | Personal projects | $0.00 |
| **Total** | | | **~$2.03/month** |

### Free Tier Eligibility (First 12 Months)

| Service | Free Tier | Our Usage | Overage Cost |
|---------|-----------|-----------|--------------|
| Lambda Requests | 1M/month | 8,580/month | $0.00 |
| Lambda Compute | 400,000 GB-sec/month | ~10,800 GB-sec/month | $0.00 |
| CloudWatch Logs | 5 GB ingestion | ~0.5 GB/month | $0.00 |

**Estimated Cost with Free Tier**: **~$1.60/month** (Secrets Manager + partial CloudWatch)

---

## Data Capacity Planning

### Current Data Usage (As of 2025-10-16)

**Supabase Database**:
- **Used**: ~50 MB (1,000 rows equity_data + 1,000 rows indicators from 2025-10-09)
- **Free Tier Limit**: 500 MB
- **Utilization**: 10% of free tier

**Storage Breakdown**:
| Table | Rows | Avg Row Size | Total Size | % of DB |
|-------|------|--------------|------------|---------|
| equity_data | 1,000 | ~100 bytes | ~100 KB | 0.2% |
| indicators | 1,000 | ~80 bytes | ~80 KB | 0.16% |
| option_prices | 0 | ~150 bytes | 0 KB | 0% |
| positions | 0 | ~200 bytes | 0 KB | 0% |
| trades | 0 | ~180 bytes | 0 KB | 0% |
| daily_pnl | 0 | ~120 bytes | 0 KB | 0% |
| **TOTAL** | **2,000** | | **~180 KB** | **0.036%** |

### Monthly Forecast (Expected Usage)

**Assumptions**:
- 22 trading days/month
- 391 data points/day (9:30 AM - 4:00 PM, every minute)
- 2 tables per minute (equity_data + indicators)
- Option chains: 2 rows/minute (nearest PUT + CALL strikes)
- Trading: ~10 crosses/day × 2 trades/cross = 20 trades/day

**Expected Monthly Data**:
| Table | Rows/Month | Size/Month | Notes |
|-------|------------|------------|-------|
| equity_data | 8,602 | ~860 KB | 391 points × 22 days |
| indicators | 8,602 | ~688 KB | Matches equity_data |
| option_prices | 17,204 | ~2.5 MB | 2 strikes × 391 × 22 |
| positions | 440 | ~88 KB | ~10 crosses × 2 positions × 22 days |
| trades | 880 | ~158 KB | 2 trades/position × 440 positions |
| daily_pnl | 22 | ~3 KB | 1 summary/day |
| **TOTAL** | **35,750** | **~4.3 MB/month** | |

**Database Growth**: ~4.3 MB/month

### Annual Forecast

**Expected Annual Data**:
- **Rows**: 35,750 × 12 = **429,000 rows/year**
- **Storage**: 4.3 MB × 12 = **~52 MB/year**
- **Free Tier Limit**: 500 MB
- **Years Until Limit**: 500 MB ÷ 52 MB = **~9.6 years**

### Data Retention Strategy

**Current**: Indefinite retention (no auto-delete)

**Recommended** (future):
1. **Equity/Indicators**: Keep 2 years (104 MB)
2. **Option Prices**: Keep 90 days (~13 MB)
3. **Positions/Trades**: Keep all (archival value)
4. **Daily P&L**: Keep all (minimal size)

**With Retention**:
- **Steady State**: ~117 MB after 2 years
- **% of Free Tier**: 23.4%
- **Upgrade Needed**: Never (well within limits)

### Capacity vs Usage

| Metric | Free Tier | Current | Forecast (Month) | Forecast (Year) | % Used |
|--------|-----------|---------|------------------|-----------------|--------|
| **Database Size** | 500 MB | 0.18 MB | 4.3 MB | 52 MB | 0.036% → 10.4% |
| **Egress Bandwidth** | 5 GB/month | <10 MB | ~50 MB | ~600 MB | <1% → 12% |
| **API Requests** | Unlimited | 2,000 | ~100,000 | ~1.2M | N/A |

### Actuals vs Forecast vs Plan

**Actuals** (Last 7 days):
- ❌ **0 rows added** (Lambda token issue)
- ✅ **1,000 rows exist** from 2025-10-09
- **Expected**: Should have ~2,700 rows (391 × 7 days)
- **Gap**: 2,700 rows missing = ~270 KB missing data

**Forecast** (Next 30 days after fix):
- **New Rows**: 35,750 rows
- **New Storage**: 4.3 MB
- **Cumulative**: 35,750 + 2,000 = 37,750 rows, ~4.5 MB total

**Plan** (Capacity Headroom):
- **Free Tier**: 500 MB database
- **Forecast Usage**: 4.5 MB (0.9% of limit)
- **Safety Margin**: 495.5 MB available (99.1%)
- **Comfortable for**: 9+ years at current rate

### Scaling Triggers

**When to upgrade Supabase**:
- [ ] Database > 400 MB (80% of free tier)
- [ ] Egress > 4 GB/month (80% of free tier)
- [ ] Need advanced features (real-time, edge functions)

**When to add caching**:
- [ ] Frontend queries > 1,000/minute
- [ ] Chart load time > 2 seconds
- [ ] Bandwidth costs become significant

### Lambda Scaling

**Current Configuration**:
- Memory: 256 MB
- Timeout: 60 seconds
- Concurrency: 1

**Scaling Thresholds**:
| Metric | Current | Trigger Upgrade | Action |
|--------|---------|-----------------|--------|
| Duration | ~400-500 ms | > 50 seconds | Increase memory |
| Memory Used | ~193 MB | > 200 MB | Increase to 512 MB |
| Error Rate | 100% (token issue) | > 5% | Alert + investigate |
| Data Size | 0 KB | > 10 MB/response | Add pagination |

## Summary

### Current State
- **Database**: 0.18 MB used (0.036% of 500 MB limit)
- **Lambda**: Executing but failing due to invalid token
- **Bandwidth**: Minimal (<1% of limit)
- **Cost**: ~$1.60/month (within free tier for compute)

### Expected State (After Fix)
- **Database**: 4.5 MB used (0.9% of limit) after 1 month
- **Lambda**: 8,602 successful executions/month
- **Bandwidth**: ~50 MB/month (1% of 5 GB limit)
- **Cost**: ~$2.03/month (negligible increase)

### Capacity Headroom
- **Database**: 99.1% available (495.5 MB free)
- **Lambda**: Unlimited (pay-per-use, well within free tier)
- **Bandwidth**: 99% available (4.95 GB free/month)
- **Runway**: 9+ years before hitting limits

---

**The system is designed to scale efficiently within free tiers for years.**

---

## Execution Frequency & Scheduling

### Trading Day Schedule

| Time (ET) | Activity | Executions |
|-----------|----------|------------|
| 9:30 AM - 9:59 AM | Market Open | 30 |
| 10:00 AM - 3:59 PM | Market Midday | 360 |
| 4:00 PM | Market Close | 1 |
| **Total** | | **391/day** |

### Monthly Execution Estimate

- **Trading Days**: ~22 days/month (excluding weekends, holidays)
- **Total Executions**: 391 × 22 = **8,602 executions/month**

### Annual Execution Estimate

- **Trading Days**: ~252 days/year
- **Total Executions**: 391 × 252 = **98,532 executions/year**

### Lambda Concurrency

- **Reserved Concurrency**: 1 (no parallel executions needed)
- **Burst Concurrency**: Not applicable (sequential minute-by-minute execution)

### Schwab API Rate Limits

- **Limit**: 120 requests/minute
- **Our Usage**: 1 request/minute (well within limits)
- **Buffer**: 119 requests/minute available for future features

---

## Security & Access Control

⚠️ **See [SECURITY.md](./SECURITY.md) for comprehensive security guidelines and best practices.**

### AWS IAM Permissions

**Lambda Execution Role**: `alpha-kite-real-time-streamer-role`

**Permissions**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:schwab-api-token-*"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:PutMetricData"],
      "Resource": "*"
    }
  ]
}
```

**Security Principle:** Least privilege access - Lambda only has permissions for its specific operations.

### Supabase Access Control

**Service Role Key** (Backend):
- Full read/write access to all tables
- Used by Lambda for data ingestion
- Stored in Lambda environment variables

**Anon Key** (Frontend):
- Read-only access to `equity_data` and `indicators`
- Enforced via RLS policies
- Public-facing (safe to expose in client-side code)

### Schwab API Authentication

- **Protocol**: OAuth 2.0 Authorization Code Flow
- **Token Lifespan**: 7 days (access token), 90 days (refresh token)
- **Storage**: AWS Secrets Manager (encrypted at rest) for production; local `.schwab_tokens.json` for development
- **Rotation**: Automatic refresh via Lambda when expiration detected
- **Manual Refresh**: Use `backend/sys_testing/auto_reauth.py` for local re-authentication
- **Token Diagnostics**: Use `backend/sys_testing/token_diagnostics.py` to check token health

**Important:** Never commit token files to Git. See [SECURITY.md](./SECURITY.md) for credential management guidelines.

---

## Monitoring & Observability

### CloudWatch Dashboards (Recommended Setup)

**Dashboard Name**: `AlphaKiteMax-RealTime-Dashboard`

**Widgets**:
1. **Lambda Invocations** (line graph, 1-hour window)
2. **Lambda Errors** (line graph, 1-hour window)
3. **Lambda Duration** (histogram, p50/p90/p99)
4. **Data Points Fetched** (metric, last 10 minutes)
5. **Supabase Upload Success Rate** (percentage, 1-hour window)

### Alerting Strategy

**SNS Topic**: `alpha-kite-alerts`

**Alarms**:
1. **No Data Alert**: If `DataPointsFetched < 1` for 15 minutes during market hours
2. **Lambda Failure Alert**: If `Errors > 3` in 5-minute period
3. **Token Refresh Alert**: If token refresh fails (manual intervention needed)

### Log Queries (CloudWatch Insights)

**Query 1: Average Execution Time**
```
fields @timestamp, @duration
| stats avg(@duration) as avg_duration_ms by bin(5m)
```

**Query 2: Error Rate**
```
fields @timestamp, level, event, error
| filter level = "error"
| stats count() as error_count by bin(5m)
```

**Query 3: Data Points Fetched**
```
fields @timestamp, equity_rows, indicator_rows
| stats sum(equity_rows) as total_equity_rows by bin(1h)
```

---

## Scalability & Performance

### Current Limitations

1. **Single Ticker**: Only QQQ supported
2. **No Horizontal Scaling**: Lambda concurrency set to 1
3. **No Caching**: Every request hits Schwab API
4. **Database Queries**: No query optimization (indexes exist but not extensively used)

### Scaling Strategies (Future)

#### Multi-Ticker Support

**Approach 1: Lambda Fan-Out**
- EventBridge triggers parent Lambda
- Parent Lambda invokes child Lambdas (one per ticker)
- Each child fetches data for its assigned ticker
- **Pros**: Parallel execution, faster overall
- **Cons**: Increased Lambda invocations, potential rate limit issues

**Approach 2: Single Lambda with Loop**
- Lambda iterates through list of tickers
- Sequential API calls
- **Pros**: Simple, stays within rate limits
- **Cons**: Longer execution time, potential timeout

**Recommended**: Approach 2 for < 10 tickers, Approach 1 for > 10 tickers

#### Caching Layer

**Redis/ElastiCache**:
- Cache latest data point (1-minute TTL)
- Frontend reads from cache instead of Supabase
- **Cost**: ~$15/month (t3.micro instance)
- **Benefit**: Reduced Supabase egress, faster frontend loads

#### Database Optimization

**Partitioning**:
- Partition `equity_data` by date (monthly partitions)
- **Benefit**: Faster queries for specific date ranges
- **Implementation**: PostgreSQL table partitioning

**Read Replicas**:
- Supabase Pro tier supports read replicas
- **Benefit**: Offload read queries from primary
- **Cost**: +$25/month per replica

---

## Disaster Recovery & Business Continuity

### Backup Strategy

**Supabase**:
- Automatic daily backups (Supabase Pro tier)
- Point-in-time recovery (PITR) available
- Manual backups via `pg_dump` (recommended weekly)

**Lambda Code**:
- Stored in Git repository
- Deployment artifacts in S3 (versioned bucket recommended)

**Secrets**:
- Schwab token backed up locally (encrypted)
- Manual export from Secrets Manager (emergency access)

### Failure Scenarios

| Scenario | Impact | Recovery | RTO | RPO |
|----------|--------|----------|-----|-----|
| Lambda Failure | No new data | EventBridge retries, manual trigger | 5 min | 1 min |
| Schwab API Outage | No new data | Wait for API recovery | 30 min | 30 min |
| Supabase Downtime | Frontend fails, no data ingestion | Supabase SLA (99.9%) | 1 hour | 1 min |
| Vercel Outage | Frontend unavailable | Vercel SLA (99.99%) | 10 min | 0 |
| Token Expiry | Authentication failure | Manual re-auth, upload new token | 10 min | 0 |

**RTO**: Recovery Time Objective  
**RPO**: Recovery Point Objective

---

## Technology Versions & Dependencies

### Frontend

```json
{
  "next": "15.0.2",
  "react": "18.3.1",
  "typescript": "5.6.3",
  "tailwindcss": "3.4.14",
  "recharts": "2.13.3",
  "@supabase/supabase-js": "2.46.1",
  "date-fns": "4.1.0",
  "date-fns-tz": "3.2.0",
  "react-datepicker": "7.5.0"
}
```

### Backend (Local Development)

**Package Manager:** `uv` (ultra-fast Python package manager) [[memory:6995111]]

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
cd backend
uv venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
uv pip install -r requirements.txt
```

**Dependencies:**
```
schwab-py==1.5.1
supabase==2.22.0
pandas==2.3.2
numpy==2.2.6
boto3==1.40.53
structlog==25.4.0
python-dateutil==2.9.0
pytz==2025.2
pydantic==2.12.2
pydantic-settings==2.11.0
```

### Backend (Lambda)

**Deployment Tool:** `uv` for 10-100x faster package installation

**Minimal Runtime Dependencies** (Lambda-optimized):
```
schwab-py==1.5.1
supabase==2.22.0
boto3==1.40.53
structlog==25.4.0
python-dateutil==2.9.0
pytz==2025.2
pydantic==2.12.2
```

**Note:** Heavy dependencies (pandas, numpy) excluded for smaller Lambda package size unless required for specific Lambda functions.

### Infrastructure

```
terraform >= 1.0
aws provider ~> 5.0
python 3.10 (Lambda runtime)
```

---

## Future Enhancements

1. **WebSocket Streaming**: Replace polling with Schwab WebSocket API for sub-second latency
2. **Multi-Ticker Support**: Extend to SPY, DIA, IWM, etc.
3. **Options Data**: Add real-time 0DTE option prices
4. **Trading Signals**: Automated trade execution based on SMA9/VWAP crosses
5. **Machine Learning**: Predictive models for price movements
6. **Mobile App**: React Native or Flutter for iOS/Android
7. **Alerting**: SMS/Email notifications for signal triggers
8. **Backtesting**: Historical simulation of trading strategies

---

## Appendix

### Useful Commands

**View Lambda Logs**:
```bash
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow --region us-east-1
```

**Test Lambda Manually**:
```bash
aws lambda invoke --function-name alpha-kite-real-time-streamer --payload '{}' response.json
```

**Query Supabase**:
```sql
SELECT COUNT(*), MAX(timestamp) FROM equity_data WHERE ticker='QQQ' AND timestamp::date = CURRENT_DATE;
```

**Update Lambda Code**:
```bash
cd backend && ./deploy_lambda.sh
```

**Refresh Schwab Token**:
```bash
cd backend && python refresh_schwab_auth.py
aws secretsmanager put-secret-value --secret-id schwab-api-token-prod --secret-string file://config/schwab_token.json
```

### Support Contacts

- **AWS Support**: https://console.aws.amazon.com/support/
- **Supabase Support**: https://supabase.com/support
- **Schwab Developer Portal**: https://developer.schwab.com/support

---

**Document Version**: 1.0  
**Last Updated**: October 16, 2024  
**Author**: Infrastructure Team  
**Review Cycle**: Quarterly

