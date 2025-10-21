# Deployment Guide

## Current Status ✅

**Production Deployment**: Live on Vercel  
**Database**: Supabase with migrations applied  
**Backend**: Python ETL pipeline operational  
**Test Coverage**: 13/13 tests passing  

## Quick Start

### View Dashboard

Your dashboard is deployed and accessible at your Vercel URL. It displays:
- QQQ equity data
- SMA9 (9-period Simple Moving Average)
- Session VWAP (Volume Weighted Average Price)
- Minute-level granularity

### Download Fresh Data

```bash
cd backend
source venv/bin/activate
python main.py --ticker QQQ --days 5
```

This downloads the latest market data from Schwab and loads it into Supabase.

## Architecture

```
┌─────────────────┐
│   Schwab API    │ ──► Download minute-level equity data
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  ETL Pipeline   │ ──► Calculate SMA9 & VWAP indicators
└─────────────────┘
         │
         ▼
┌─────────────────┐
│    Supabase     │ ──► Store equity_data & indicators
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Vercel Dashboard│ ──► Display interactive charts
└─────────────────┘
```

## Maintenance

### Refresh Data Daily

Set up a cron job or GitHub Action to run:
```bash
cd backend && source venv/bin/activate && python main.py --ticker QQQ --days 1
```

### Monitor Limits

Per `context/TECHNICAL.md`, monitor:
- Supabase: 500 MB database (currently ~0.5 MB with 737 rows)
- Supabase: 5 GB egress
- Schwab API: Rate limits apply

### Update Schema

To add new tables or modify existing ones:
```bash
supabase migration new description_of_change
# Edit the migration file
supabase db push
```

## Completed Features

✅ **Issue #1**: Dashboard deployed to Vercel  
✅ **Issue #3**: Supabase schema & Schwab integration  

## Next Steps (Future Features)

- Option data download (as per context)
- Options indicators and analytics
- Additional tickers beyond QQQ
- Automated scheduled downloads
- Real-time data updates
- Historical data backfill

