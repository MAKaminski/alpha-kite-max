# Data Flow & Storage

## Where Does Downloaded Data Go?

There are **two different data paths** in this project, depending on which method you use:

---

## 📊 Method 1: Main ETL Pipeline → Supabase (Database)

### Launch Configurations:
- 🔐 1. Automatic/Non-Interactive Auth
- 📥 3. Download Historical Data (all variants)
- 📡 4. Stream Real-Time Data

### Files Used:
- `backend/main.py`
- `backend/etl_pipeline.py`
- `backend/schwab_integration/downloader.py`

### Data Destination:
**✅ Supabase Database** (cloud storage)

### Tables:
1. **`equity_data`** table
   - Columns: `ticker`, `timestamp`, `price`, `volume`
   - Indexes on `(ticker, timestamp)` for fast queries

2. **`indicators`** table
   - Columns: `ticker`, `timestamp`, `sma9`, `vwap`
   - Indexes on `(ticker, timestamp)` for fast queries

### How to Access:
```bash
# Via Supabase Dashboard
https://supabase.com/dashboard/project/xwcauibwyxhsifnotnzz/editor

# Via Frontend
http://localhost:3000 (when running dev server)

# Via Python
from supabase_client import SupabaseClient
client = SupabaseClient()
data = client.get_equity_data(ticker="QQQ", start_date=..., end_date=...)
```

### Example Flow:
```
1. You run: VS Code Launch → "📥 Download Historical Data (QQQ, 5 days)"
2. Downloads minute data from Schwab API
3. Calculates indicators (SMA9, VWAP)
4. Inserts into Supabase database
5. ✅ Data is immediately available to frontend
```

**No local CSV files created** ❌

---

## 📁 Method 2: Standalone Script → Local CSV Files

### Launch Configuration:
- 📊 Quick Demo (Standalone QQQ)

### Files Used:
- `backend/standalone_qqq_download.py`
- `backend/run_standalone_qqq.sh`

### Data Destination:
**✅ Local CSV File** in `backend/` directory

### File Format:
```
backend/qqq_data_YYYYMMDD_HHMMSS.csv
```

### Example Filename:
```
backend/qqq_data_20251019_143022.csv
```

### Columns in CSV:
- `timestamp` - ISO format with timezone (e.g., 2025-10-19 09:30:00+00:00)
- `open` - Opening price
- `high` - High price
- `low` - Low price
- `close` - Closing price
- `volume` - Volume traded

### Example Flow:
```
1. You run: VS Code Launch → "📊 Quick Demo (Standalone QQQ)"
2. Downloads 7 days of minute data from Schwab API
3. Displays progress and statistics in terminal
4. Saves to timestamped CSV file
5. ✅ File saved in: backend/qqq_data_20251019_143022.csv
```

### How to Use CSV:
```python
import pandas as pd

# Load the data
df = pd.read_csv('backend/qqq_data_20251019_143022.csv')

# Convert timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Analyze
print(df.describe())
print(df.head())
```

Or open in **Excel**, **Google Sheets**, or any spreadsheet software.

---

## 🔍 Quick Reference

| Method | Destination | File Location | Access |
|--------|-------------|---------------|--------|
| **Main ETL Pipeline** | Supabase Database | Cloud (no local file) | Frontend app, Supabase dashboard, Python client |
| **Standalone Script** | Local CSV File | `backend/qqq_data_*.csv` | Excel, Python, any CSV reader |

---

## 🎯 When to Use Each Method

### Use Main ETL Pipeline When:
- ✅ Building the trading dashboard
- ✅ Need real-time data access from frontend
- ✅ Running production data collection
- ✅ Want data persistence and history
- ✅ Multiple users/systems need access

### Use Standalone Script When:
- ✅ Testing authentication
- ✅ Quick data exploration
- ✅ One-time data download
- ✅ Offline analysis
- ✅ Exporting data for other tools

---

## 📊 Check Your Downloaded Data

### Method 1 (Supabase):
```bash
# Run this in VS Code terminal
cd backend
source venv/bin/activate
python sys_testing/check_data_status.py
```

This will show you:
- How many rows of equity data
- How many rows of indicators
- Date ranges
- Latest timestamps

### Method 2 (CSV Files):
```bash
# List all downloaded CSV files
ls -lh backend/*.csv

# View first few rows
head backend/qqq_data_*.csv

# Count rows
wc -l backend/qqq_data_*.csv
```

---

## 🗂️ Data Retention

### Supabase (Database):
- **Retention**: Permanent (until manually deleted)
- **Storage**: Supabase free tier: 500 MB
- **Backup**: Automatic daily backups by Supabase

### CSV Files (Local):
- **Retention**: Until you delete them
- **Storage**: Your local disk space
- **Backup**: Manual (add to .gitignore to avoid committing)

**Note**: CSV files are already in `.gitignore`, so they won't be committed to Git.

---

## 📈 Example: Complete Data Download Flow

### Scenario 1: Production Data Collection
```
1. Open VS Code
2. Press F5 → Select "📥 3. Download Historical Data (QQQ, 5 days)"
3. Data downloads from Schwab
4. Data inserted into Supabase
5. Frontend refreshes and shows new data
6. ✅ Done! No files to manage.
```

### Scenario 2: Quick Analysis
```
1. Open VS Code
2. Press F5 → Select "📊 Quick Demo (Standalone QQQ)"
3. Data downloads from Schwab
4. CSV file created: backend/qqq_data_20251019_143022.csv
5. Open in Excel or Python for analysis
6. Delete CSV when done (optional)
```

---

## 🔧 Configuration

### Where the Data Goes (Supabase)
Configured in `backend/.env`:
```bash
SUPABASE_URL=https://xwcauibwyxhsifnotnzz.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key-here
```

### What Data is Downloaded (Defaults)
Configured in `backend/schwab_integration/config.py`:
```python
default_ticker = "QQQ"        # Which symbol to download
lookback_days = 5             # How many days of history
```

---

## ❓ FAQ

**Q: Why doesn't the main pipeline create CSV files?**  
A: It's designed for production use where data needs to be in a database for the frontend to access. CSV files would be redundant.

**Q: Can I export data from Supabase to CSV?**  
A: Yes! Use the Supabase dashboard SQL editor:
```sql
COPY (
  SELECT * FROM equity_data 
  WHERE ticker = 'QQQ' 
  AND timestamp > '2025-10-01'
) TO '/tmp/export.csv' CSV HEADER;
```

**Q: How do I view data in Supabase?**  
A: Supabase Dashboard → Table Editor → Select `equity_data` or `indicators` table

**Q: Where are the authentication tokens stored?**  
A: `backend/config/schwab_token.json` (auto-created on first auth)

---

**Last Updated**: October 19, 2025  
**Related Docs**: 
- [Backend README](backend/README.md)
- [Authentication Summary](backend/AUTHENTICATION_SUMMARY.md)
- [Testing Guide](backend/TESTING.md)

