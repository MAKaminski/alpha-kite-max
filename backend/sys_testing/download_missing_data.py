#!/usr/bin/env python3
"""
Download missing historical data for 10/15 and 10/16.
Run this after re-authorizing Schwab token.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, str(Path(__file__).parent))

import structlog
from etl_pipeline import ETLPipeline

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def main():
    print("\n" + "="*70)
    print("BACKFILL MISSING DATA")
    print("="*70)
    print()
    
    ticker = "QQQ"
    pipeline = ETLPipeline()
    
    # Get dates to backfill
    est = pytz.timezone('America/New_York')
    today = datetime.now(est).date()
    
    # Calculate days to backfill (10/15 to today)
    start_date = datetime(2025, 10, 15).date()
    days_to_backfill = (today - start_date).days + 1
    
    print(f"📅 Backfilling data from {start_date} to {today}")
    print(f"   Ticker: {ticker}")
    print(f"   Days: {days_to_backfill}")
    print()
    
    # Schwab API limits to 10 days max for minute data
    if days_to_backfill > 10:
        print(f"⚠️  Note: Schwab API max is 10 days for minute data")
        print(f"   Will download last 10 days only")
        days_to_backfill = 10
        print()
    
    print(f"🚀 Starting download...")
    print()
    
    try:
        result = pipeline.run(ticker=ticker, days=days_to_backfill)
        
        if result['success']:
            print()
            print("="*70)
            print("✅ DOWNLOAD SUCCESSFUL!")
            print("="*70)
            print()
            print(f"Ticker:         {result['ticker']}")
            print(f"Equity rows:    {result['equity_rows']:,}")
            print(f"Indicator rows: {result['indicator_rows']:,}")
            if 'date_range' in result:
                print(f"Date range:     {result['date_range']['start']} to {result['date_range']['end']}")
            print()
            print("📊 Verify data:")
            print("   python3 check_data_status.py")
            print()
            print("🌐 Check frontend:")
            print("   Visit your Vercel deployment and navigate to 10/15 or 10/16")
            print()
            return 0
        else:
            print()
            print("="*70)
            print("❌ DOWNLOAD FAILED")
            print("="*70)
            print()
            print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")
            print()
            
            if 'token_invalid' in str(result.get('error', '')):
                print("💡 Token is still invalid. Did you:")
                print("   1. Run: python3 auto_reauth.py")
                print("   2. Click the browser auth link")
                print("   3. Upload token to AWS Secrets Manager?")
                print()
            
            return 1
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

