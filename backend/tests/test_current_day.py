#!/usr/bin/env python3
"""
Quick test script to verify current day (10/15/25) data is streaming correctly.
Run this from the backend directory: python test_current_day.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.client import SchwabClient
from schwab_integration.downloader import EquityDownloader
from schwab_integration.config import SchwabConfig, SupabaseConfig
from clients.supabase_client import SupabaseClient
import structlog

logger = structlog.get_logger()


def test_current_day_streaming():
    """Test current day data streaming end-to-end."""
    
    ticker = "QQQ"
    today = datetime.now().date()
    
    print("=" * 80)
    print(f"TESTING CURRENT DAY DATA STREAMING FOR {ticker}")
    print(f"Date: {today}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Step 1: Initialize clients
    print("\n📋 Step 1: Initializing clients...")
    try:
        schwab_config = SchwabConfig()
        schwab_client = SchwabClient(schwab_config)
        
        supabase_config = SupabaseConfig()
        supabase_client = SupabaseClient(supabase_config)
        
        downloader = EquityDownloader(schwab_client)
        
        print("✅ Clients initialized")
    except Exception as e:
        print(f"❌ Failed to initialize clients: {e}")
        return False
    
    # Step 2: Test Schwab API connection
    print("\n📡 Step 2: Testing Schwab API connection...")
    try:
        response = schwab_client.get_price_history(
            symbol=ticker,
            period_type="day",
            period=1,
            frequency_type="minute",
            frequency=1
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        candles = data.get('candles', [])
        
        print(f"✅ API connection successful")
        print(f"   Candles received: {len(candles)}")
        
        if candles:
            first_candle = candles[0]
            last_candle = candles[-1]
            
            first_time = datetime.fromtimestamp(first_candle['datetime'] / 1000)
            last_time = datetime.fromtimestamp(last_candle['datetime'] / 1000)
            
            print(f"   Time range: {first_time.strftime('%Y-%m-%d %H:%M')} to {last_time.strftime('%H:%M')}")
            print(f"   Price range: ${first_candle['close']:.2f} to ${last_candle['close']:.2f}")
            
            # Check if data is from today
            data_date = first_time.date()
            if data_date != today:
                print(f"⚠️  WARNING: Data is from {data_date}, not today ({today})")
                print("   This might be normal if today is a weekend or holiday")
        else:
            print("⚠️  WARNING: No candles returned")
            print("   Market might be closed or before market open")
            
    except Exception as e:
        print(f"❌ Schwab API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Download and process data
    print("\n📥 Step 3: Downloading and processing data...")
    try:
        df = downloader.download_minute_data(ticker, days=1)
        
        if df.empty:
            print("⚠️  No data downloaded (market might be closed)")
            print("   Try running this during market hours (9:30 AM - 4:00 PM ET)")
            return False
        
        print(f"✅ Downloaded {len(df)} data points")
        print(f"   Columns: {list(df.columns)}")
        
        # Show time range
        first_ts = df['timestamp'].min()
        last_ts = df['timestamp'].max()
        print(f"   Time range: {first_ts} to {last_ts}")
        
        # Show sample data
        print(f"\n   Sample (last 5 rows):")
        print(df.tail(5).to_string())
        
    except Exception as e:
        print(f"❌ Data download failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Calculate indicators
    print("\n📊 Step 4: Calculating indicators...")
    try:
        indicators = downloader.calculate_indicators(df)
        
        if indicators.empty:
            print("❌ No indicators calculated")
            return False
        
        print(f"✅ Calculated indicators for {len(indicators)} data points")
        
        # Show last indicators
        last_row = indicators.iloc[-1]
        print(f"\n   Latest values:")
        print(f"   Timestamp: {last_row['timestamp']}")
        print(f"   SMA9: ${last_row['sma9']:.2f}")
        print(f"   VWAP: ${last_row['vwap']:.2f}")
        
        # Check for NaN
        nan_count = indicators.isna().sum().sum()
        if nan_count > 0:
            print(f"   ⚠️  Warning: {nan_count} NaN values found")
        
    except Exception as e:
        print(f"❌ Indicator calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Upload to Supabase
    print("\n📤 Step 5: Uploading to Supabase...")
    try:
        # Upload equity data
        equity_success = supabase_client.upsert_equity_data(df)
        if not equity_success:
            print("❌ Failed to upload equity data")
            return False
        
        print(f"✅ Uploaded {len(df)} equity data rows")
        
        # Upload indicators
        indicator_success = supabase_client.upsert_indicators(indicators)
        if not indicator_success:
            print("❌ Failed to upload indicators")
            return False
        
        print(f"✅ Uploaded {len(indicators)} indicator rows")
        
    except Exception as e:
        print(f"❌ Supabase upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Verify data retrieval
    print("\n🔍 Step 6: Verifying data can be retrieved...")
    try:
        start_date = datetime.combine(today, datetime.min.time())
        end_date = datetime.combine(today, datetime.max.time())
        
        # Get equity data
        equity_data = supabase_client.get_equity_data(ticker, start_date, end_date)
        print(f"✅ Retrieved {len(equity_data)} equity data rows")
        
        # Get indicators
        indicator_data = supabase_client.get_indicators(ticker, start_date, end_date)
        print(f"✅ Retrieved {len(indicator_data)} indicator rows")
        
        if equity_data and indicator_data:
            last_equity_time = equity_data[-1]['timestamp']
            last_indicator_time = indicator_data[-1]['timestamp']
            
            print(f"\n   Last equity timestamp: {last_equity_time}")
            print(f"   Last indicator timestamp: {last_indicator_time}")
            
            # Check freshness
            last_time = datetime.fromisoformat(last_equity_time.replace('Z', '+00:00'))
            now = datetime.now(last_time.tzinfo)
            age = now - last_time
            
            print(f"   Data age: {age}")
            
            if age < timedelta(hours=1):
                print("   ✅ Data is fresh (< 1 hour old)")
            else:
                print("   ⚠️  Data is older than 1 hour")
                print("      Market might be closed")
        
    except Exception as e:
        print(f"❌ Data retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Success!
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - CURRENT DAY DATA IS STREAMING CORRECTLY")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  • Downloaded {len(df)} data points for {ticker}")
    print(f"  • Calculated {len(indicators)} indicators")
    print(f"  • Successfully uploaded to Supabase")
    print(f"  • Data can be retrieved by frontend")
    print(f"\nNext steps:")
    print(f"  1. Check frontend at http://localhost:3000")
    print(f"  2. Verify chart shows data for {today}")
    print(f"  3. Check that indicators (SMA9, VWAP) are displayed")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = test_current_day_streaming()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

