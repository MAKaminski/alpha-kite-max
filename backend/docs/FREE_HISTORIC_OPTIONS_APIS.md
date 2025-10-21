# Free Historical Options Data APIs

## 🎯 Best Free Options for Historic Options Data

---

## 🥇 Recommended: Polygon.io (Best Overall)

### Features:
- ✅ **Historical options data** (EOD and intraday)
- ✅ Options contracts, strikes, expirations
- ✅ Greeks history (delta, gamma, theta, vega)
- ✅ IV (implied volatility) history
- ✅ Open interest and volume history
- ✅ Free tier: 5 API calls/minute

### Free Tier Limits:
- 5 requests/minute
- 2 years of historical data
- Delayed data (15 minutes for stocks, EOD for options)

### Python Integration:
```python
import requests

API_KEY = "your_polygon_api_key"  # Free at polygon.io

# Get historical options for QQQ
url = f"https://api.polygon.io/v3/reference/options/contracts"
params = {
    "underlying_ticker": "QQQ",
    "strike_price": 600,
    "expiration_date": "2025-10-20",
    "apiKey": API_KEY
}

response = requests.get(url, params=params)
options_data = response.json()

# Get historical option prices
contract_ticker = "O:QQQ251020P00600000"
url = f"https://api.polygon.io/v2/aggs/ticker/{contract_ticker}/range/1/day/2025-10-01/2025-10-20"
params = {"apiKey": API_KEY}

response = requests.get(url, params=params)
historical_prices = response.json()
```

### Sign Up:
- Website: https://polygon.io/
- Free tier: No credit card required
- Upgrade: $199/month for real-time + unlimited calls

---

## 🥈 Runner-Up: Alpha Vantage

### Features:
- ✅ Historical options data (limited)
- ✅ Options chains
- ✅ Greeks available
- ✅ Free tier: 25 API calls/day

### Free Tier Limits:
- 25 requests per day (very limited)
- 5 requests per minute

### Python Integration:
```python
import requests

API_KEY = "your_alpha_vantage_api_key"

# Get option chain
url = "https://www.alphavantage.co/query"
params = {
    "function": "HISTORICAL_OPTIONS",
    "symbol": "QQQ",
    "apikey": API_KEY
}

response = requests.get(url, params=params)
options_data = response.json()
```

### Sign Up:
- Website: https://www.alphavantage.co/
- Free tier: No credit card required
- Premium: $49.99/month for more calls

---

## 🥉 Third Place: Yahoo Finance (yfinance)

### Features:
- ✅ **Current** options chains (free, unlimited)
- ⚠️ **Limited** historical options (not reliable)
- ✅ Easy Python library
- ✅ No API key required

### Limitations:
- **Historical options NOT officially supported**
- May work occasionally but unreliable
- Best for current snapshots only

### Python Integration:
```python
import yfinance as yf

# Get current option chain
ticker = yf.Ticker("QQQ")

# Get available expiration dates
expirations = ticker.options

# Get option chain for specific expiration
exp_date = "2025-10-25"
opt_chain = ticker.option_chain(exp_date)

# Access calls and puts
calls = opt_chain.calls
puts = opt_chain.puts

# Filter for $600 strike
qqq_600_puts = puts[puts['strike'] == 600]
print(qqq_600_puts)
```

### Sign Up:
- No signup required
- Install: `pip install yfinance`
- Free and unlimited for current data

---

## 🆓 Other Free Options

### 4. Tradier (Developer Account)

**Features**:
- ✅ Options data (historical + real-time)
- ✅ Sandbox/paper trading account
- ✅ Free developer tier

**Limits**:
- Free: Delayed data (15 minutes)
- Requires account verification

**Website**: https://tradier.com/

### 5. CBOE DataShop (Limited Free)

**Features**:
- ✅ Official options data from CBOE
- ✅ Very high quality
- ⚠️ Mostly paid, some free samples

**Limits**:
- Very limited free access
- Best for production use (paid)

**Website**: https://datashop.cboe.com/

### 6. Nasdaq Data Link (formerly Quandl)

**Features**:
- ✅ Historical financial data
- ⚠️ Limited free options data
- ✅ Good for academic use

**Limits**:
- 50 calls/day free tier
- Premium datasets require payment

**Website**: https://data.nasdaq.com/

---

## 🎯 Recommended Solution for Your Use Case

### For QQQ 0DTE @ $600 Strike:

**Best Approach**: **Polygon.io Free Tier**

### Why Polygon.io:
1. ✅ Actually supports historical options
2. ✅ 5 calls/minute (enough for daily backfill)
3. ✅ 2 years of history
4. ✅ Includes Greeks
5. ✅ No credit card for free tier
6. ✅ Good Python SDK

### Implementation Plan:

**1. Sign up for Polygon.io** (5 minutes)
- Go to https://polygon.io/
- Create free account
- Get API key

**2. Install Polygon SDK**:
```bash
cd backend
source venv/bin/activate
pip install polygon-api-client
```

**3. Create Integration** (`backend/schwab_integration/polygon_client.py`):
```python
from polygon import RESTClient
import pandas as pd
from datetime import datetime, timedelta

class PolygonOptionsClient:
    def __init__(self, api_key: str):
        self.client = RESTClient(api_key)
    
    def get_historical_options(
        self, 
        ticker: str,
        strike: float,
        exp_date: str,
        option_type: str,
        days_back: int = 30
    ) -> pd.DataFrame:
        """Download historical options data."""
        
        # Build option contract ticker
        # Format: O:QQQ251020P00600000
        contract = self._build_polygon_symbol(
            ticker, strike, exp_date, option_type
        )
        
        # Get historical data
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        aggs = self.client.get_aggs(
            ticker=contract,
            multiplier=1,
            timespan="day",
            from_=start_date,
            to=end_date
        )
        
        # Convert to DataFrame
        records = []
        for agg in aggs:
            records.append({
                'timestamp': datetime.fromtimestamp(agg.timestamp / 1000),
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume
            })
        
        return pd.DataFrame(records)
    
    def _build_polygon_symbol(self, ticker, strike, exp_date, opt_type):
        """Build Polygon option symbol."""
        # O:QQQ251020P00600000
        exp_str = datetime.strptime(exp_date, '%Y-%m-%d').strftime('%y%m%d')
        strike_str = f"{int(strike * 1000):08d}"
        type_letter = 'P' if opt_type == 'PUT' else 'C'
        return f"O:{ticker}{exp_str}{type_letter}{strike_str}"
```

**4. Add CLI Command**:
```bash
# Download 30 days of historical options for QQQ $600 PUT
python download_historic_options_polygon.py \
    --ticker QQQ \
    --strike 600 \
    --option-type PUT \
    --days 30
```

**5. Result**:
- Backfill last 30 days of option data
- Get daily open/high/low/close
- Store in Supabase
- Merge with real-time captures going forward

---

## 📊 Comparison Table

| Provider | Free Tier | Historical Options | Ease of Use | Best For |
|----------|-----------|-------------------|-------------|----------|
| **Polygon.io** | 5/min, 2 years | ✅ Yes | ⭐⭐⭐⭐⭐ | Production |
| **Alpha Vantage** | 25/day | ⚠️ Limited | ⭐⭐⭐⭐ | Light use |
| **yfinance** | Unlimited | ❌ No | ⭐⭐⭐⭐⭐ | Current only |
| **Tradier** | 15min delay | ✅ Yes | ⭐⭐⭐ | Testing |
| **IEX Cloud** | 50k/month | ❌ No options | ⭐⭐⭐⭐ | Stocks only |

---

## 💡 Hybrid Recommendation

### Optimal Strategy:

**1. For Current Data**: Use **Schwab API** (what we have now)
- Real-time during trading
- No rate limits
- Already integrated ✅

**2. For Historical Backfill**: Use **Polygon.io Free Tier**
- Backfill last 30-60 days
- Run once to populate database
- Provides baseline historical data

**3. Going Forward**: Use **Lambda + Schwab**
- Capture snapshots every minute
- Build ongoing historical record
- Free and unlimited

### Implementation:

**One-Time Backfill** (This Weekend):
```bash
# Use Polygon.io to backfill last 30 days
python download_historic_options_polygon.py --days 30
```

**Ongoing Collection** (Starting Monday):
```bash
# Lambda runs automatically
# OR manual downloads with Schwab API
python download_0dte_options.py --strike 600 --today-only
```

**Result**: Complete historical database with minimal cost!

---

## 🔧 Quick Start: Polygon.io Integration

### 1. Sign Up (Free)
```
1. Go to https://polygon.io/
2. Click "Sign Up"
3. Choose "Starter" (Free)
4. Verify email
5. Get API key from dashboard
```

### 2. Install SDK
```bash
cd backend
source venv/bin/activate
pip install polygon-api-client
```

### 3. Add to requirements.txt
```bash
echo "polygon-api-client>=1.14.1" >> requirements.txt
```

### 4. Set Environment Variable
```bash
# In backend/.env
POLYGON_API_KEY=your_polygon_api_key_here
```

### 5. Run Backfill
```bash
# Create the script first (I can help!)
python download_historic_options_polygon.py --strike 600 --days 30
```

---

## ⚡ Want Me to Build It?

I can create the complete Polygon.io integration:
- ✅ Polygon client module
- ✅ Historical download script
- ✅ VS Code launch configuration
- ✅ Database integration
- ✅ Backfill automation

**Just say the word and I'll build it!**

---

## 📝 Summary

### Question: Who provides free historical options data?

**Answer**: 
1. **Polygon.io** (Best) - 5 calls/min, 2 years history
2. **Alpha Vantage** - 25 calls/day, limited coverage
3. **yfinance** - Current only, no true historical

### Recommendation:
Use **Polygon.io free tier** for one-time backfill, then rely on our Schwab-based Lambda to build ongoing history.

**Cost**: $0 (free tier sufficient)  
**Effort**: ~30 minutes to integrate  
**Result**: Complete historical + ongoing database

---

**Want me to build the Polygon.io integration now?** 🚀

