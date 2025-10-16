# Technical Flow Analysis - AST Mapping

## Overview

This document provides an Abstract Syntax Tree (AST) style mapping of the application's data flow, decision points, and architectural patterns. It helps identify where issues occur and explains design decisions.

## Application Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                        │
│  Next.js 15 + React + TypeScript + Tailwind CSS             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │─>│EquityChart│─>│ Signals  │─>│ Trading  │   │
│  │Component │  │ Component │  │Dashboard │  │Dashboard │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │              │          │
│       └─────────────┴──────────────┴──────────────┘          │
│                        │                                      │
│                   [Supabase Client]                          │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                           │
│                   Supabase (PostgreSQL)                      │
│  ┌──────────────┐  ┌───────────┐  ┌──────────────┐         │
│  │ equity_data  │  │indicators │  │option_prices │         │
│  │(price/volume)│  │(SMA9/VWAP)│  │(chain data)  │         │
│  └──────────────┘  └───────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌───────────┐  ┌──────────────┐         │
│  │  positions   │  │  trades   │  │  daily_pnl   │         │
│  │(open/closed) │  │(execution)│  │  (summary)   │         │
│  └──────────────┘  └───────────┘  └──────────────┘         │
└───────────────────────▲──────────────────────────────────────┘
                        │
                        │ (Upsert Data)
                        │
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND LAYER                            │
│              Python + schwab-py + AWS Lambda                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           AWS Lambda (Real-time Streamer)            │   │
│  │  Triggered: Every minute (9:30 AM - 4:00 PM EST)     │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  1. Check market hours                               │   │
│  │  2. Fetch token from Secrets Manager                 │   │
│  │  3. Download QQQ data from Schwab API                │   │
│  │  4. Calculate SMA9/VWAP indicators                   │   │
│  │  5. Upsert to Supabase                               │   │
│  │  6. Process option chains (0DTE nearest strikes)     │   │
│  │  7. Execute trading strategy (if enabled)            │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                          │
│                   ▼                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         ETL Pipeline (Manual/Backfill)               │   │
│  │  Usage: python main.py --ticker QQQ --days 5         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  1. Initialize Schwab + Supabase clients             │   │
│  │  2. Download historical data                         │   │
│  │  3. Calculate indicators on full dataset             │   │
│  │  4. Batch upsert to database                         │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────▲──────────────────────────────────────┘
                        │
                        │ (API Calls)
                        │
┌─────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                          │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │   Schwab API     │    │  AWS Services    │              │
│  │ ───────────────  │    │ ───────────────  │              │
│  │ • Price History  │    │ • EventBridge    │              │
│  │ • Option Chains  │    │ • Secrets Mgr    │              │
│  │ • Account Info   │    │ • CloudWatch     │              │
│  │ • Order Place    │    │ • Lambda         │              │
│  └──────────────────┘    └──────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow: Real-Time Streaming

### Entry Point: Lambda Handler

**File**: `backend/lambda/real_time_streamer.py`

```python
def lambda_handler(event, context):
    """
    AST Mapping:
    ┌─ lambda_handler()
    │  ├─ is_market_open() ──> [Decision Point 1]
    │  │  ├─ TRUE:  Continue ──┐
    │  │  └─ FALSE: Return (skip) ──> EXIT
    │  │
    │  ├─ TokenManager.get_token() ──> [Critical Path 1]
    │  │  ├─ Token exists: Load from Secrets Manager
    │  │  ├─ Token expired: Attempt refresh ──> [CURRENT FAILURE POINT]
    │  │  └─ No token: ERROR
    │  │
    │  ├─ SchwabClient.get_price_history() ──> [Critical Path 2]
    │  │  ├─ Auth valid: Fetch data
    │  │  └─ Auth invalid: InvalidTokenError ──> [ERROR OBSERVED]
    │  │
    │  ├─ EquityDownloader.calculate_indicators()
    │  │  ├─ Calculate SMA9 (rolling 9-period average)
    │  │  └─ Calculate VWAP (cumulative volume-weighted)
    │  │
    │  ├─ SupabaseClient.upsert_equity_data()
    │  │  ├─ Upsert equity_data table
    │  │  └─ Upsert indicators table
    │  │
    │  └─ Return success/failure
    └─ END
    ```

### Decision Point 1: Market Hours Check

**Function**: `is_market_open()`
**Location**: `backend/lambda/real_time_streamer.py:72-96`

```python
def is_market_open() -> bool:
    """
    Flow:
    1. Get current time in EST
    2. Check if weekday (Monday-Friday)
       - IF weekend: return False
    3. Check if within hours (9:30 AM - 4:00 PM)
       - IF outside hours: return False
    4. Return True
    
    Design Decision:
    - Why EST? US market operates in Eastern Time
    - Why this specific check? Prevents unnecessary API calls
    - Lambda cost optimization: Skip execution when market closed
    """
    est = pytz.timezone('America/New_York')
    now_est = datetime.now(est)
    
    if now_est.weekday() >= 5:  # Weekend
        return False
    
    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = now_est.time()
    
    return market_open <= current_time < market_close
```

**Issue Potential**: Doesn't check market holidays
**Future Enhancement**: Add holiday calendar check

### Critical Path 1: Token Management

**Class**: `TokenManager`
**Location**: `backend/lambda/token_manager.py`

```python
class TokenManager:
    """
    AST Flow:
    ┌─ get_token()
    │  ├─ secretsmanager.get_secret_value()
    │  ├─ json.loads(secret_string)
    │  └─ return token_dict
    │
    ├─ token_needs_refresh()
    │  ├─ Check 'expires_at' field
    │  │  ├─ Missing: return True (assume expired) ──> [ISSUE HERE]
    │  │  └─ Present: Compare with now
    │  └─ return bool
    │
    └─ refresh_token()
       ├─ schwab_client.authenticate()  # Calls schwab-py
       │  ├─ Reads /tmp/schwab_token.json
       │  ├─ Attempts OAuth refresh
       │  └─ Writes updated token
       ├─ Read updated token file
       └─ update_token() to Secrets Manager
    ```

**Current Issue**:
```python
# Line 99-104 in token_manager.py
if 'expires_at' not in token_data:
    logger.warning("token_missing_expiration")
    return True  # Assume expired if no expiration
```

**Why This Fails**:
1. Token missing `expires_at` field
2. Lambda assumes expired, attempts refresh
3. Refresh succeeds (new access token generated)
4. But original OAuth consent is invalid
5. API calls still fail with `Invalid TokenError`

**Root Cause**: The token in Secrets Manager was never properly authorized with full OAuth consent. The refresh mechanism can't fix a fundamentally invalid refresh token.

### Critical Path 2: Schwab API Data Fetch

**Class**: `SchwabClient`
**Method**: `get_price_history()`
**Location**: `backend/schwab_integration/client.py:140-206`

```python
def get_price_history(symbol, period_type, period, frequency):
    """
    AST Flow:
    ┌─ get_price_history()
    │  ├─ authenticate() ──> Returns schwab-py client
    │  │  ├─ Load token from file
    │  │  ├─ Initialize OAuth2 session
    │  │  └─ Validate token
    │  │
    │  ├─ Map period/frequency to Schwab enums
    │  │  ├─ period_type='day', period=1-10
    │  │  └─ frequency='1minute'
    │  │
    │  ├─ client.get_price_history() ──> [schwab-py library]
    │  │  ├─ Build API request
    │  │  ├─ Add OAuth headers
    │  │  ├─ Make HTTP GET request ──> [FAILURE POINT]
    │  │  │  ├─ 200: Success, return data
    │  │  │  ├─ 401: InvalidTokenError ──> [CURRENT STATE]
    │  │  │  └─ Other: HTTPError
    │  │  └─ Parse JSON response
    │  │
    │  └─ return candle data
    └─ END
    ```

**Error Stack Trace Analysis**:
```
File "/var/task/schwab/client/base.py", line 794
  -> return self._get_request(path, params)

File "/var/task/schwab/client/synchronous.py", line 19
  -> resp = self.session.get(dest, params=params)

File "/var/task/httpx/_client.py", line 1053
  -> return self.request(...)

File "/var/task/authlib/integrations/httpx_client/oauth2_client.py", line 267
  -> raise InvalidTokenError()
```

**Why**: authlib (OAuth library) validates the token before making the HTTP request. The token is rejected at the OAuth layer, not by Schwab's servers.

**Design Decision**: Why not catch and retry?
- OAuth errors require user interaction
- Automatic retry would waste Lambda executions
- Better to fail fast and alert

## Frontend Data Flow

### Component Hierarchy

```
App (layout.tsx)
 ├─ DarkModeProvider
 │   └─ Dashboard (page.tsx)
 │       ├─ ESTClock
 │       ├─ EquityChart
 │       │   ├─ Line (Price)
 │       │   ├─ Line (SMA9)
 │       │   ├─ Line (VWAP)
 │       │   ├─ Line (Cross Markers)
 │       │   ├─ Scatter (Option Prices)
 │       │   └─ ReferenceArea (Market Hours)
 │       ├─ SignalsDashboard
 │       ├─ TradingDashboard
 │       └─ AdminPanel
 │           └─ FeatureFlagsDashboard
 └─ [End]
```

### State Management Flow

**File**: `frontend/src/components/Dashboard.tsx`

```typescript
/*
AST State Flow:
┌─ Dashboard Component
│  ├─ STATE
│  │  ├─ allData: ChartDataPoint[]        // All fetched data
│  │  ├─ displayData: ChartDataPoint[]    // Filtered by selectedDate
│  │  ├─ selectedDate: Date               // Date picker value
│  │  ├─ todayCrosses: Cross[]            // Detected crosses
│  │  ├─ period: 'minute' | 'hour'        // NEW: Period selector
│  │  └─ ...
│  │
│  ├─ EFFECTS
│  │  ├─ useEffect([ticker, period]) ──> fetchData()
│  │  │  ├─ Query Supabase for equity_data + indicators
│  │  │  ├─ Paginate (1000 rows/page)
│  │  │  ├─ Merge data by timestamp
│  │  │  ├─ IF period='hour': aggregateToHourly() ──> [Decision Point 2]
│  │  │  └─ setAllData(processedData)
│  │  │
│  │  ├─ useEffect([allData, selectedDate]) ──> Filter + Detect Crosses
│  │  │  ├─ Filter allData by selectedDate
│  │  │  ├─ detectCrosses(allData)
│  │  │  ├─ filterCrossesByDate(selectedDate)
│  │  │  └─ setDisplayData(), setTodayCrosses()
│  │  │
│  │  ├─ useEffect([ticker]) ──> Real-time updates (if enabled)
│  │  │  ├─ setInterval(fetchLatestData, 60000)
│  │  │  └─ Cleanup on unmount
│  │  │
│  │  └─ useEffect([ticker]) ──> Option price streaming (if enabled)
│  │     ├─ realTimeOptionsService.start(ticker)
│  │     ├─ subscribe(updateHandler)
│  │     └─ Cleanup on unmount
│  │
│  └─ RENDER
│     ├─ Header (metrics, ticker input, period selector, dark mode)
│     ├─ Date Navigation (prev/next, date picker)
│     ├─ EquityChart (with conditional props based on feature flags)
│     ├─ TradingDashboard (if enabled)
│     ├─ SignalsDashboard (if enabled)
│     └─ AdminPanel (toggle button + modal)
└─ END
*/
```

### Decision Point 2: Period Aggregation

**Function**: `aggregateToHourly()`
**Location**: `frontend/src/components/Dashboard.tsx:47-102`

```typescript
/*
AST Flow:
┌─ aggregateToHourly(data: ChartDataPoint[])
│  │
│  ├─ IF data.length === 0: return []
│  │
│  ├─ Group by hour
│  │  └─ FOR EACH point in data:
│  │     ├─ Extract hour from timestamp
│  │     ├─ Create hourKey (YYYY-MM-DD HH:00:00)
│  │     └─ Add to hourlyGroups[hourKey]
│  │
│  ├─ Aggregate each hour
│  │  └─ FOR EACH (hourKey, points) in hourlyGroups:
│  │     ├─ Extract prices, volumes, sma9, vwap arrays
│  │     ├─ Calculate close = last price
│  │     ├─ Calculate totalVolume = sum(volumes)
│  │     ├─ Calculate volume-weighted SMA9
│  │     │  └─ sma9 = Σ(sma9[i] * volume[i]) / Σ(volume)
│  │     ├─ Calculate volume-weighted VWAP
│  │     │  └─ vwap = Σ(vwap[i] * volume[i]) / Σ(volume)
│  │     └─ Return {timestamp, price, volume, sma9, vwap}
│  │
│  ├─ Sort by timestamp
│  └─ return hourlyData[]
└─ END

Design Decisions:
- Why volume-weighted? Preserves accuracy of SMA9/VWAP
- Why close price? Represents end-of-hour value
- Why this approach? Maintains indicator integrity vs simple averages

KNOWN BUG (Issue #4):
- Period selector UI updates but chart may not reflect changes
- Potential cause: React state batching or memo dependencies
- See .github/ISSUE_TEMPLATE/bug_period_selector.md for diagnostic plan
*/
```

## Trading Strategy Flow

### Cross Detection Algorithm

**File**: `frontend/src/lib/crossDetection.ts`

```typescript
/*
AST Flow:
┌─ detectCrosses(data: ChartDataPoint[])
│  │
│  ├─ Initialize: crosses = [], lastDirection = null
│  │
│  ├─ FOR i = 1 to data.length:
│  │  ├─ prev = data[i-1], curr = data[i]
│  │  │
│  │  ├─ IF NOT isRegularTradingHours(curr.timestamp):
│  │  │  └─ continue  ──> [Design: Only trade during market hours]
│  │  │
│  │  ├─ prevDiff = prev.sma9 - prev.vwap
│  │  ├─ currDiff = curr.sma9 - curr.vwap
│  │  │
│  │  ├─ IF prevDiff * currDiff < 0:  # Signs differ = cross occurred
│  │  │  ├─ direction = (currDiff > 0) ? 'up' : 'down'
│  │  │  │
│  │  │  ├─ IF lastDirection == null OR lastDirection != direction:
│  │  │  │  ├─ crosses.push({timestamp, price, sma9, vwap, direction})
│  │  │  │  └─ lastDirection = direction
│  │  │  │     [Design: Prevents consecutive same-direction crosses]
│  │  │  │
│  │  │  └─ ELSE: skip (would be duplicate)
│  │  │
│  │  └─ continue to next
│  │
│  └─ return crosses[]
└─ END

Design Decisions:
- Why check signs? Mathematical way to detect line intersection
- Why prevent duplicates? Avoid false signals from noise
- Why require direction change? Ensures alternating up/down crosses
- Why only market hours? No trading outside 9:30 AM - 4:00 PM EST
*/
```

### Trading Engine Logic

**File**: `backend/schwab_integration/trading_engine.py`

```python
"""
AST Flow:
┌─ process_cross_signal(ticker, timestamp, price, sma9, vwap, direction)
│  │
│  ├─ IF NOT is_trading_allowed(timestamp):
│  │  └─ return None  [No trading 30 mins before close]
│  │
│  ├─ Record signal to database
│  │
│  ├─ Get current open position for ticker
│  │  ├─ Query Supabase positions table
│  │  └─ position = first OPEN position or None
│  │
│  ├─ [Decision Tree: Trading Action]
│  │
│  ├─ IF direction == 'down':  # SMA9 crossed below VWAP
│  │  ├─ IF position exists AND position.option_type == 'PUT':
│  │  │  └─ Skip (already in PUT position)
│  │  │
│  │  ├─ ELSE:
│  │  │  ├─ IF position exists: close_position(position)
│  │  │  ├─ Get nearest PUT strike below current price
│  │  │  ├─ Get option chain for 0DTE
│  │  │  ├─ option_symbol = build_option_symbol(PUT, strike, 0DTE)
│  │  │  ├─ Place order: SELL_TO_OPEN 25 contracts @ ask price
│  │  │  ├─ Create Position record (OPEN)
│  │  │  └─ Create Trade record (SELL_TO_OPEN)
│  │
│  ├─ ELIF direction == 'up':  # SMA9 crossed above VWAP  
│  │  ├─ IF position exists:
│  │  │  ├─ close_position(position)  # Take profit/loss
│  │  │  └─ Open new CALL position (same logic as PUT above)
│  │  │
│  │  └─ ELSE:
│  │     └─ Skip (no position to close)
│  │
│  └─ return trade_result
└─ END

Design Decisions:
- Why 25 contracts? Balances risk vs capital efficiency
- Why 0DTE? Same-day expiration for momentum strategy
- Why nearest strike? Highest liquidity, tightest spreads
- Why close before new position? Avoid holding both CALL + PUT
- Why 30-min halt before close? Prevents EOD execution risk
*/
"""
```

## Database Schema & Relationships

```sql
/*
AST Entity Relationship:

equity_data (1) ──┬──> (1) indicators
    │             └──── JOIN ON (ticker, timestamp)
    │
    ├─ Used by: Chart visualization
    ├─ Updated by: Lambda every minute
    └─ Retention: Indefinite (for historical analysis)

option_prices (1:N) ──> trades
    │
    ├─ Stores: Bid/ask/last for nearest strikes
    ├─ Updated by: Lambda (0DTE chains)
    └─ Used by: Trading engine for order pricing

positions (1) ──> (N) trades
    │             └──── FK: position_id
    │
    ├─ Tracks: Open/closed option positions
    ├─ Updated by: Trading engine
    └─ Queried by: TradingDashboard component

daily_pnl (1:1) per (ticker, date)
    │
    ├─ Aggregates: Daily trading performance
    ├─ Updated by: Trading engine (on trade close)
    └─ Displayed: TradingDashboard summary

Design Decisions:
- Why separate equity_data and indicators? 
  -> Different update frequencies (data vs calc)
- Why unique index on option_prices?
  -> Prevent duplicate chain data
- Why UUID for positions/trades?
  -> Distributed systems compatibility
- Why UNIQUE(ticker, trade_date) on daily_pnl?
  -> One summary per ticker per day
*/
```

## Feature Flag System

**File**: `frontend/src/lib/featureFlags.ts`

```typescript
/*
AST Flow:
┌─ FeatureFlagsService
│  ├─ INITIALIZATION
│  │  ├─ Load defaultFlags (18 features)
│  │  ├─ loadFromStorage() ──> localStorage
│  │  │  ├─ IF exists: merge with defaults
│  │  │  └─ ELSE: use defaults only
│  │  └─ flags = merged state
│  │
│  ├─ isEnabled(flagId)
│  │  ├─ Get flag by ID
│  │  ├─ Check dependencies
│  │  │  └─ IF has dependencies: check each dependency.enabled
│  │  └─ return flag.enabled AND all dependencies enabled
│  │
│  ├─ setFlag(id, enabled, modifiedBy)
│  │  ├─ Update flag.enabled
│  │  ├─ Update flag.lastModified
│  │  ├─ saveToStorage()
│  │  └─ notifyListeners() ──> React components re-render
│  │
│  └─ subscribe(callback)
│     ├─ Add callback to listeners[]
│     └─ return unsubscribe function
│
└─ React Hooks
   ├─ useFeatureFlag(flagId)
   │  ├─ useState(featureFlags.isEnabled(flagId))
   │  ├─ useEffect(() => subscribe())
   │  └─ return enabled (reactive to changes)
   │
   └─ useFeatureFlags()
      ├─ useState(featureFlags.getAllFlags())
      ├─ useEffect(() => subscribe())
      └─ return flags{} (reactive)

Design Decisions:
- Why singleton service? Central state management
- Why localStorage? Persist user preferences
- Why dependencies? Ensure related features work together
- Why listeners pattern? React component reactivity
- Why default values? Safe degradation without DB

Example Dependency Chain:
auto-trading
  └─ depends on: paper-trading, position-tracking
     └─ IF paper-trading OFF: auto-trading disabled
        [Prevents accidental live trading]
*/
```

## Error Handling Patterns

### Pattern 1: Graceful Degradation

```typescript
// Frontend: Dashboard.tsx
const fetchData = async () => {
  try {
    // Attempt data fetch
  } catch (err) {
    setError(err.message);  // Show error to user
    setLoading(false);      // Stop loading indicator
    // App continues to function, just shows error message
  }
};
```

**Why**: User can still interact with other features even if data fetch fails.

### Pattern 2: Feature Flag Guards

```typescript
{realTimeDataEnabled && (
  <Component />  // Only render if feature enabled
)}
```

**Why**: Failed features don't break entire app. Can disable problematic features via admin panel.

### Pattern 3: Retry with Backoff (Lambda)

```python
# Lambda attempts token refresh automatically
if token_needs_refresh(token_data):
    logger.info("refreshing_expired_token")
    token_manager.refresh_token(schwab_client)
    # Retry API call with refreshed token
```

**Why**: Transient token issues resolved automatically. But doesn't help with fundamentally invalid tokens (current issue).

## Performance Optimizations

### 1. Data Pagination

```typescript
// Dashboard.tsx: fetchData()
while (true) {
  const { data } = await supabase
    .from('equity_data')
    .select('*')
    .range(page * 1000, (page + 1) * 1000 - 1);
  
  if (!data || data.length === 0) break;
  allData = [...allData, ...data];
  if (data.length < 1000) break;
  page++;
}
```

**Why**: Prevents memory issues with large datasets. Supabase has row limits per query.

### 2. React.useMemo for Expensive Calculations

```typescript
const chartData = React.useMemo(() => {
  return filteredData.map(point => ({
    ...point,
    crossMarker: crosses.find(c => c.timestamp === point.timestamp)
  }));
}, [filteredData, crosses]);
```

**Why**: Avoids recalculating on every render. Only recomputes when dependencies change.

### 3. Lambda Package Optimization

**Package size**: 80MB → 20KB (using `uv` + minimal dependencies)

```bash
# deploy_simple.sh
- Excludes: pandas, numpy (not needed for Lambda)
- Includes: Only essential runtime deps
- Cleans: __pycache__, *.pyc, tests
```

**Why**: 
- Faster cold starts (less code to load)
- Lower costs (less storage/transfer)
- Faster deployments

## Common Failure Points

### 1. Token Expiration (CURRENT ISSUE)

**Where**: `TokenManager.get_token()` → `schwab_client.get_price_history()`

**Symptoms**:
- Lambda logs show `token_refresh_successful`
- Immediately followed by `InvalidTokenError`
- Pattern repeats every minute

**Fix**: Re-authorize OAuth token with proper consent

### 2. Missing Feature Flag Dependencies

**Where**: `featureFlags.isEnabled()` checks dependencies

**Symptoms**:
- Feature appears enabled but doesn't work
- Component renders but functionality missing

**Fix**: Enable all dependent features or check dependency chain

### 3. Timezone Mismatches

**Where**: Market hours checks, cross detection, chart display

**Symptoms**:
- Data appears at wrong times
- Market hours highlighting incorrect
- Crosses detected outside trading hours

**Fix**: Always use EST timezone for market data

### 4. Supabase RLS Policies

**Where**: Database queries from frontend

**Symptoms**:
- `SELECT` works but `INSERT`/`UPDATE` fails
- Frontend can read but not write

**Fix**: Ensure policies allow `service_role` for writes, `anon` for reads

## Testing Strategy

### Unit Tests (Future)

```typescript
// Test cross detection
describe('detectCrosses', () => {
  it('detects upward cross when SMA9 crosses above VWAP', () => {
    const data = [
      { sma9: 100, vwap: 101 },  // SMA9 below
      { sma9: 102, vwap: 101 }   // SMA9 above = cross!
    ];
    const crosses = detectCrosses(data);
    expect(crosses).toHaveLength(1);
    expect(crosses[0].direction).toBe('up');
  });
});
```

### Integration Tests

```python
# Test Lambda end-to-end
def test_lambda_handler():
    # Mock Schwab API response
    # Mock Supabase client
    # Call lambda_handler()
    # Assert data inserted correctly
```

### Manual Testing Checklist

- [ ] Date navigation (prev/next/calendar)
- [ ] Period selector (minute/hour)
- [ ] Cross detection (verify red circles)
- [ ] Real-time updates (new data every minute)
- [ ] Dark mode toggle
- [ ] Feature flags enable/disable
- [ ] Admin panel navigation
- [ ] Trading dashboard displays

## Architecture Decision Log

### Why Next.js 15?

- Server components for performance
- Built-in API routes (if needed later)
- Vercel deployment optimization
- Modern React features (server actions)

### Why Supabase?

- Real-time subscriptions (future)
- Row-level security (fine-grained access)
- PostgreSQL (robust, familiar)
- Auto-generated APIs
- Built-in authentication (if needed)

### Why AWS Lambda instead of Vercel Cron?

**Vercel Cron Limitations**:
- Max 1 execution per minute (too slow for options)
- 10-second timeout on Hobby plan
- Limited to 100 executions/day on free tier

**AWS Lambda Advantages**:
- Sub-second invocations possible
- 15-minute timeout
- Unlimited executions (pay per use)
- Better for data-intensive tasks

### Why Schwab API?

Per memory: "Project should use only the Schwab API for options data; do not use polygon.io or Yahoo Finance."

### Why Pydantic instead of dataclasses?

Per memory: "Project uses pydantic for data modeling instead of dataclasses for model classes."
- Better validation
- Environment variable parsing
- JSON serialization
- Type coercion

## Debugging Quick Reference

### Frontend Issues

```typescript
// Enable debug logging
localStorage.setItem('DEBUG', 'true');

// Check feature flags
console.log(featureFlags.getAllFlags());

// Verify Supabase config
console.log('Supabase URL:', process.env.NEXT_PUBLIC_SUPABASE_URL);
```

### Backend Issues

```bash
# Test connections
python main.py --test-connections

# Check data
python check_data_status.py

# Test paper trading
python test_paper_trading.py

# Check Lambda logs
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 1h
```

### Lambda Issues

```bash
# Test invoke
aws lambda invoke --function-name alpha-kite-real-time-streamer response.json

# Check Secrets Manager
aws secretsmanager get-secret-value --secret-id schwab-api-token-prod

# Verify EventBridge
aws events list-rules --name-prefix alpha-kite
```

---

**This document serves as the technical foundation for debugging, testing, and future development.**

