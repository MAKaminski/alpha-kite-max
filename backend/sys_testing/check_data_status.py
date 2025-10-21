#!/usr/bin/env python3
"""Check data status in Supabase for diagnostics."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import structlog
from schwab_integration.config import SupabaseConfig
from clients.supabase_client import SupabaseClient

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def check_data_for_dates(ticker: str, start_date: str, end_date: str):
    """Check data availability for specific date range."""
    print(f"\n📊 Checking data for {ticker} from {start_date} to {end_date}\n")
    
    try:
        # Initialize Supabase client
        config = SupabaseConfig()
        client = SupabaseClient(config)
        
        # Query equity data
        response = client.client.table('equity_data')\
            .select('timestamp, price, volume')\
            .eq('ticker', ticker)\
            .gte('timestamp', f'{start_date}T00:00:00')\
            .lte('timestamp', f'{end_date}T23:59:59')\
            .order('timestamp', desc=False)\
            .execute()
        
        if not response.data:
            print(f"❌ No equity data found for {ticker} between {start_date} and {end_date}")
            return
        
        # Group by date
        dates = {}
        for row in response.data:
            date_str = row['timestamp'][:10]
            if date_str not in dates:
                dates[date_str] = []
            dates[date_str].append(row)
        
        # Report findings
        print(f"✅ Found data for {len(dates)} day(s):\n")
        
        for date_str in sorted(dates.keys()):
            points = dates[date_str]
            first_time = points[0]['timestamp'][11:19]
            last_time = points[-1]['timestamp'][11:19]
            avg_price = sum(p['price'] for p in points) / len(points)
            total_volume = sum(p['volume'] for p in points)
            
            print(f"  📅 {date_str}:")
            print(f"     • Data points: {len(points)}")
            print(f"     • Time range: {first_time} to {last_time}")
            print(f"     • Avg price: ${avg_price:.2f}")
            print(f"     • Total volume: {total_volume:,}")
            print()
        
        # Check for missing dates
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        print("📌 Date coverage analysis:")
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            # Skip weekends
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                if date_str in dates:
                    print(f"  ✅ {date_str}: {len(dates[date_str])} data points")
                else:
                    print(f"  ❌ {date_str}: NO DATA (weekday)")
            current += timedelta(days=1)
        
        print()
        
        # Check indicators
        response = client.client.table('indicators')\
            .select('timestamp')\
            .eq('ticker', ticker)\
            .gte('timestamp', f'{start_date}T00:00:00')\
            .lte('timestamp', f'{end_date}T23:59:59')\
            .execute()
        
        if response.data:
            print(f"✅ Indicators: {len(response.data)} rows")
        else:
            print(f"❌ Indicators: NO DATA")
        
        return True
        
    except Exception as e:
        logger.error("check_failed", error=str(e))
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Main function."""
    ticker = "QQQ"
    
    print("=" * 70)
    print("DATA STATUS DIAGNOSTIC")
    print("=" * 70)
    
    # Check 10/15/2025
    print("\n1️⃣  Checking 10/15/2025 (Tuesday)")
    check_data_for_dates(ticker, "2025-10-15", "2025-10-15")
    
    # Check 10/16/2025
    print("\n2️⃣  Checking 10/16/2025 (Wednesday - TODAY)")
    check_data_for_dates(ticker, "2025-10-16", "2025-10-16")
    
    # Check last 7 days
    today = datetime.now(pytz.timezone('America/New_York'))
    week_ago = today - timedelta(days=7)
    
    print(f"\n3️⃣  Checking last 7 days ({week_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})")
    check_data_for_dates(ticker, week_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
    
    print("\n" + "=" * 70)
    print("✅ Diagnostic complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

