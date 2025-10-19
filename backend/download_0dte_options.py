#!/usr/bin/env python3
"""
Download 0DTE QQQ Option Data
===============================
Downloads call and put option data for QQQ at specific strike prices for 0DTE (zero days to expiration).

Usage:
    python download_0dte_options.py --strike 600 --days 5
    python download_0dte_options.py --strike 600 605 610 --days 1

Features:
    - Downloads both CALL and PUT options
    - Tracks specific strike prices
    - Stores data in Supabase option_prices table
    - Supports multiple strikes and dates
"""

import argparse
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

import structlog
from schwab_integration.client import SchwabClient
from schwab_integration.option_downloader import OptionDownloader
from supabase_client import SupabaseClient


# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download 0DTE option data from Schwab and load into Supabase"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="QQQ",
        help="Stock ticker symbol (default: QQQ)"
    )
    parser.add_argument(
        "--strike",
        type=float,
        nargs='+',
        default=[600.0],
        help="Strike price(s) to download (default: 600). Can specify multiple strikes."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to look back (default: 1)"
    )
    parser.add_argument(
        "--today-only",
        action="store_true",
        help="Only download today's 0DTE options"
    )
    parser.add_argument(
        "--test-connections",
        action="store_true",
        help="Test connections to Schwab and Supabase only"
    )
    
    args = parser.parse_args()
    
    logger.info(
        "starting_option_download",
        ticker=args.ticker,
        strikes=args.strike,
        days=args.days
    )
    
    # Initialize clients
    schwab_client = SchwabClient()
    option_downloader = OptionDownloader(schwab_client)
    supabase_client = SupabaseClient()
    
    if args.test_connections:
        logger.info("testing_connections")
        
        # Test Schwab
        try:
            schwab_client.authenticate()
            print("✓ Schwab: Connected")
        except Exception as e:
            print(f"✗ Schwab: Failed - {e}")
            return 1
        
        # Test Supabase
        try:
            supabase_client.test_connection()
            print("✓ Supabase: Connected")
        except Exception as e:
            print(f"✗ Supabase: Failed - {e}")
            return 1
        
        print("\n✓ All connections successful")
        return 0
    
    try:
        if args.today_only:
            # Download only today's 0DTE options
            target_date = date.today()
            all_options = []
            
            for strike in args.strike:
                logger.info("fetching_strike", strike=strike, date=target_date.isoformat())
                df = option_downloader.get_0dte_options_at_strike(
                    args.ticker,
                    strike,
                    target_date
                )
                if not df.empty:
                    all_options.append(df)
            
            if all_options:
                import pandas as pd
                combined_df = pd.concat(all_options, ignore_index=True)
            else:
                combined_df = pd.DataFrame()
        else:
            # Download multiple days
            combined_df = option_downloader.download_daily_0dte_options(
                args.ticker,
                args.strike,
                args.days
            )
        
        if combined_df.empty:
            print(f"\n✗ No option data found for {args.ticker}")
            print(f"  Strikes: {args.strike}")
            print(f"  This might be because:")
            print(f"  - Market is closed")
            print(f"  - No options exist at these strikes")
            print(f"  - Options have already expired")
            return 1
        
        # Display summary
        print(f"\n✓ Downloaded {len(combined_df)} option records")
        print(f"\n📊 Summary:")
        print(f"  Ticker: {args.ticker}")
        print(f"  Strikes: {combined_df['strike_price'].unique().tolist()}")
        print(f"  Option Types: {combined_df['option_type'].unique().tolist()}")
        print(f"  Expiration Dates: {combined_df['expiration_date'].unique().tolist()}")
        
        # Show breakdown by option type
        print(f"\n📈 Breakdown by Option Type:")
        for option_type in combined_df['option_type'].unique():
            count = len(combined_df[combined_df['option_type'] == option_type])
            print(f"  {option_type}: {count} contracts")
        
        # Show sample data
        print(f"\n📋 Sample Data (first 3 rows):")
        display_cols = ['ticker', 'option_type', 'strike_price', 'last_price', 'bid', 'ask', 'volume']
        available_cols = [col for col in display_cols if col in combined_df.columns]
        print(combined_df[available_cols].head(3).to_string(index=False))
        
        # Upload to Supabase
        print(f"\n📤 Uploading to Supabase...")
        success = supabase_client.upsert_option_prices(combined_df)
        
        if success:
            print(f"✓ Successfully uploaded {len(combined_df)} option records to Supabase")
            logger.info("option_upload_successful", rows=len(combined_df))
            return 0
        else:
            print(f"✗ Failed to upload option data to Supabase")
            logger.error("option_upload_failed")
            return 1
            
    except Exception as e:
        logger.error("option_download_failed", error=str(e))
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

