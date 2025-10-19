#!/usr/bin/env python3
"""
Standalone QQQ Data Downloader
==============================
Downloads the last 7 days of market data for QQQ with visible progress.

This script is completely standalone and NOT affiliated with deployment infrastructure.
Run it directly to see authentication and data download in action.

Usage:
    python standalone_qqq_download.py

Features:
    - Schwab OAuth authentication with token caching
    - Downloads minute-level OHLCV data for QQQ
    - Shows progress for each day's data
    - Exports to timestamped CSV file
    - Displays summary statistics in terminal

Requirements:
    - schwab-py>=1.5.1
    - python-dotenv>=1.0.0
    - pandas>=2.0.0

Environment Variables Required:
    - SCHWAB_APP_KEY (or SCHWAB_CLIENT_ID)
    - SCHWAB_APP_SECRET (or SCHWAB_CLIENT_SECRET)
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from schwab import auth, client
import pandas as pd
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION - Edit these values to customize the script
# ============================================================================

# Schwab API credentials (loaded from .env file)
APP_KEY = os.getenv("SCHWAB_APP_KEY", os.getenv("SCHWAB_CLIENT_ID"))
APP_SECRET = os.getenv("SCHWAB_APP_SECRET", os.getenv("SCHWAB_CLIENT_SECRET"))

# OAuth callback URL (must match your Schwab app configuration)
CALLBACK_URL = "https://127.0.0.1:8182/"

# Where to store the OAuth token for future use
TOKEN_PATH = "config/schwab_token.json"

# Stock ticker to download (change to any symbol)
TICKER = "QQQ"

# Number of days to download (1-10, Schwab limit is 10 days for minute data)
DAYS = 7

# ============================================================================

# Create config directory if it doesn't exist
Path("config").mkdir(exist_ok=True)


def print_header():
    """Print a nice header for the script."""
    print("\n" + "=" * 70)
    print("  📊  STANDALONE QQQ DATA DOWNLOADER")
    print("=" * 70)
    print(f"Ticker: {TICKER}")
    print(f"Days to Download: {DAYS}")
    print(f"Target Period: {(datetime.now() - timedelta(days=DAYS)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 70 + "\n")


def authenticate_schwab():
    """Authenticate with Schwab API and return client."""
    print("🔐 Starting Schwab Authentication...")
    
    if not APP_KEY or not APP_SECRET:
        print("❌ ERROR: Missing SCHWAB_APP_KEY or SCHWAB_APP_SECRET environment variables!")
        print("   Please set them in your .env file or environment.")
        sys.exit(1)
    
    print(f"   App Key: {APP_KEY[:8]}...")
    print(f"   Token Path: {TOKEN_PATH}")
    
    try:
        # Try to load existing tokens
        if os.path.exists(TOKEN_PATH):
            print("   ✅ Found existing token file, authenticating...")
            schwab_client = auth.client_from_token_file(
                TOKEN_PATH,
                APP_KEY,
                APP_SECRET
            )
            print("   ✅ Authentication successful with existing tokens!\n")
        else:
            # First time authentication - requires manual callback
            print("\n   ⚠️  FIRST TIME AUTHENTICATION REQUIRED")
            print("   📝 A browser will open for OAuth authorization.")
            print("   📝 After authorizing, you'll be redirected to a callback URL.")
            print("   📝 Copy the ENTIRE callback URL and paste it when prompted.\n")
            
            schwab_client = auth.client_from_manual_flow(
                APP_KEY,
                APP_SECRET,
                CALLBACK_URL,
                TOKEN_PATH
            )
            print("   ✅ Authentication successful! Token saved for future use.\n")
        
        return schwab_client
    
    except Exception as e:
        print(f"   ❌ Authentication failed: {str(e)}")
        print("\n   💡 TROUBLESHOOTING:")
        print("   1. Make sure your SCHWAB_APP_KEY and SCHWAB_APP_SECRET are correct")
        print("   2. If this is the first run, you'll need to complete OAuth flow")
        print("   3. Check that your Schwab app callback URL is https://127.0.0.1:8182/")
        sys.exit(1)


def download_all_data(schwab_client):
    """Download data for the last 7 days."""
    print("\n" + "-" * 70)
    print("  🔄 DOWNLOADING DATA")
    print("-" * 70 + "\n")
    
    print(f"📥 Fetching {DAYS} days of minute data for {TICKER}...", end=" ", flush=True)
    
    try:
        # Download all data in one call (Schwab supports up to 10 days)
        response = schwab_client.get_price_history(
            TICKER,
            period_type=client.Client.PriceHistory.PeriodType.DAY,
            period=client.Client.PriceHistory.Period.TEN_DAYS,  # Get 10 days, we'll filter to 7
            frequency_type=client.Client.PriceHistory.FrequencyType.MINUTE,
            frequency=client.Client.PriceHistory.Frequency.EVERY_MINUTE,
            need_extended_hours_data=False
        )
        
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}")
            return None
        
        data = response.json()
        candles = data.get("candles", [])
        
        if not candles:
            print("⚠️  No data available")
            return None
        
        # Convert to DataFrame
        records = []
        for candle in candles:
            timestamp = pd.to_datetime(candle["datetime"], unit="ms", utc=True)
            records.append({
                "timestamp": timestamp,
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"]
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values("timestamp")
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
        
        # Filter to last 7 days
        cutoff_date = datetime.now() - timedelta(days=DAYS)
        df = df[df["timestamp"] >= cutoff_date.replace(tzinfo=pd.Timestamp.now(tz='UTC').tzinfo)]
        
        print(f"✅ {len(df):,} candles downloaded")
        
        # Show breakdown by day
        print("\n📊 Data breakdown by day:")
        df['date'] = df['timestamp'].dt.date
        day_counts = df.groupby('date').size()
        
        for i, (date, count) in enumerate(day_counts.items(), 1):
            day_name = pd.Timestamp(date).strftime('%A')
            print(f"   Day {i}/7: {date} ({day_name}) - {count:,} candles")
        
        return df
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def print_summary(df):
    """Print summary statistics of downloaded data."""
    print("\n" + "-" * 70)
    print("  📈 DATA SUMMARY")
    print("-" * 70)
    
    print(f"\nTotal Candles: {len(df):,}")
    print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"\nPrice Statistics:")
    print(f"  Highest: ${df['high'].max():.2f}")
    print(f"  Lowest: ${df['low'].min():.2f}")
    print(f"  Latest Close: ${df['close'].iloc[-1]:.2f}")
    print(f"  Average Volume: {df['volume'].mean():,.0f}")
    
    # Show first few rows
    print(f"\n📊 First 5 Candles:")
    print("-" * 70)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(df.head().to_string(index=False))
    
    # Show last few rows
    print(f"\n📊 Last 5 Candles:")
    print("-" * 70)
    print(df.tail().to_string(index=False))
    
    print("\n" + "=" * 70)


def main():
    """
    Main execution function.
    
    This function orchestrates the entire process:
    1. Authenticate with Schwab (uses cached token if available)
    2. Download QQQ data for the last 7 days
    3. Display summary statistics
    4. Save data to CSV file
    """
    print_header()
    
    # Step 1: Authenticate with Schwab API
    # This will either use existing tokens or prompt for OAuth
    schwab_client = authenticate_schwab()
    
    # Step 2: Download the data
    # Downloads minute-level data and shows progress by day
    df = download_all_data(schwab_client)
    
    if df is None or df.empty:
        print("\n❌ Failed to download data. Exiting.")
        print("   💡 TIP: Make sure the market is open or try a recent trading day.")
        sys.exit(1)
    
    # Step 3: Print summary statistics to terminal
    # Shows date range, price stats, and sample data
    print_summary(df)
    
    # Step 4: Save to timestamped CSV file for further analysis
    output_file = f"qqq_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    print(f"\n💾 Data saved to: {output_file}")
    print(f"   📊 Open in Excel, Python, or any data analysis tool")
    
    print("\n✅ Download complete!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

