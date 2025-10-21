#!/usr/bin/env python3
"""
Generate Synthetic Options Data for October 2025

This script generates Black-Scholes synthetic options data for the entire month
of October 2025, providing a foundation for backtesting and development when
real options data is unavailable.
"""

import argparse
from datetime import datetime
import structlog
from dotenv import load_dotenv

from black_scholes.synthetic_generator import SyntheticOptionsGenerator

load_dotenv()
logger = structlog.get_logger()


def main():
    """Main function to generate synthetic options data."""
    parser = argparse.ArgumentParser(description="Generate synthetic options data for October 2025")
    parser.add_argument("--ticker", default="QQQ", help="Ticker symbol (default: QQQ)")
    parser.add_argument("--base-price", type=float, default=600.0, help="Base stock price (default: 600.0)")
    parser.add_argument("--save-db", action="store_true", help="Save to database")
    parser.add_argument("--save-csv", action="store_true", help="Save to CSV file")
    parser.add_argument("--strike-range", type=float, default=50.0, help="Strike range around base price (default: 50.0)")
    parser.add_argument("--strike-increment", type=float, default=5.0, help="Strike increment (default: 5.0)")
    parser.add_argument("--time-intervals", type=int, default=60, help="Number of time intervals per day (default: 60)")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🎯 SYNTHETIC OPTIONS DATA GENERATOR - OCTOBER 2025")
    print("="*80)
    print(f"📊 Ticker: {args.ticker}")
    print(f"💰 Base Price: ${args.base_price:.2f}")
    print(f"📈 Strike Range: ±${args.strike_range:.2f}")
    print(f"🔢 Strike Increment: ${args.strike_increment:.2f}")
    print(f"⏰ Time Intervals per Day: {args.time_intervals}")
    print(f"💾 Save to Database: {args.save_db}")
    print(f"📄 Save to CSV: {args.save_csv}")
    print("="*80)
    
    try:
        # Initialize generator
        generator = SyntheticOptionsGenerator()
        
        # Generate data for October 2025
        print(f"\n🚀 Generating synthetic options data for {args.ticker} in October 2025...")
        print("   This may take a few minutes...")
        
        df = generator.generate_october_2025_data(
            ticker=args.ticker,
            base_price=args.base_price
        )
        
        print(f"\n✅ Generation complete!")
        print(f"📊 Total rows generated: {len(df):,}")
        print(f"📅 Date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
        print(f"🎯 Strike range: ${df['strike_price'].min():.2f} to ${df['strike_price'].max():.2f}")
        print(f"📈 Price range: ${df['spot_price'].min():.2f} to ${df['spot_price'].max():.2f}")
        
        # Show sample data
        print(f"\n📋 Sample data:")
        sample = df.head(3)[['timestamp', 'ticker', 'option_type', 'strike_price', 'market_price', 'implied_volatility']]
        print(sample.to_string(index=False))
        
        # Save to database if requested
        if args.save_db:
            print(f"\n💾 Saving to database...")
            if generator.save_to_database(df):
                print("✅ Successfully saved to database!")
            else:
                print("❌ Failed to save to database")
        
        # Save to CSV if requested
        if args.save_csv:
            filename = f"synthetic_options_october_2025_{args.ticker}.csv"
            print(f"\n📄 Saving to CSV: {filename}")
            df.to_csv(filename, index=False)
            print("✅ Successfully saved to CSV!")
        
        if not args.save_db and not args.save_csv:
            print(f"\n💡 Tip: Use --save-db to save to database or --save-csv to save to CSV")
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Apply database migration: supabase migration up")
        print(f"   2. View data in frontend with clear 'SYNTHETIC' labeling")
        print(f"   3. Plot options prices on the chart")
        print(f"   4. Compare with real Schwab data when available")
        
        print(f"\n📊 Data Summary:")
        print(f"   • Trading days: {df['expiration_date'].nunique()}")
        print(f"   • Unique strikes: {df['strike_price'].nunique()}")
        print(f"   • Total option contracts: {len(df) // 2}")  # Divide by 2 for calls/puts
        print(f"   ≈ {(len(df) // 2) // df['expiration_date'].nunique()} contracts per day")
        
    except Exception as e:
        logger.error("synthetic_data_generation_failed", error=str(e))
        print(f"\n❌ Error generating synthetic data: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
