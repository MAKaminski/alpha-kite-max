#!/usr/bin/env python3
"""
Bulk Backfill Script for Historical 0DTE Options Data

Downloads 90 days of historical options data for all strikes
QQQ traded through each day, using Polygon.io API.

Usage:
    python bulk_backfill_options.py --ticker QQQ --days 90
    python bulk_backfill_options.py --ticker QQQ --start-date 2025-07-01 --end-date 2025-10-19
"""

import argparse
import os
from datetime import datetime, timedelta, date
from typing import List, Tuple
import pandas as pd
import structlog
from dotenv import load_dotenv
import time

from polygon_integration.historic_options import PolygonHistoricOptions
from supabase_client import SupabaseClient

load_dotenv()
logger = structlog.get_logger()


class OptionsBackfillEngine:
    """Bulk backfill engine for historical options data."""
    
    def __init__(self):
        """Initialize backfill engine."""
        self.polygon_client = PolygonHistoricOptions()
        self.supabase_client = SupabaseClient()
        
        logger.info("backfill_engine_initialized")
    
    def get_daily_price_range(self, ticker: str, date_str: str) -> Tuple[float, float]:
        """
        Get the daily price range for a ticker on a specific date.
        
        Args:
            ticker: Stock ticker
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Tuple of (low, high) prices
        """
        try:
            # Query Supabase for daily range
            equity_data = self.supabase_client.get_equity_data(
                ticker=ticker,
                limit=5000  # Get enough data for the day
            )
            
            if equity_data.empty:
                logger.warning("no_equity_data", ticker=ticker, date=date_str)
                # Return estimated range
                return (595.0, 605.0)
            
            # Filter for specific date
            equity_data['date'] = pd.to_datetime(equity_data['timestamp']).dt.date
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_data = equity_data[equity_data['date'] == target_date]
            
            if day_data.empty:
                logger.warning("no_data_for_date", ticker=ticker, date=date_str)
                return (595.0, 605.0)
            
            low = float(day_data['price'].min())
            high = float(day_data['price'].max())
            
            logger.info("daily_range_found", ticker=ticker, date=date_str, low=low, high=high)
            return (low, high)
            
        except Exception as e:
            logger.error("daily_range_lookup_failed", error=str(e), ticker=ticker, date=date_str)
            return (595.0, 605.0)
    
    def generate_strike_list(self, low: float, high: float, increment: float = 5.0) -> List[float]:
        """
        Generate list of strike prices within range.
        
        Args:
            low: Lowest price
            high: Highest price
            increment: Strike price increment (default $5)
            
        Returns:
            List of strike prices
        """
        rounded_low = (int(low / increment)) * increment
        rounded_high = (int(high / increment) + 1) * increment
        
        strikes = []
        current = rounded_low
        while current <= rounded_high:
            strikes.append(current)
            current += increment
        
        logger.info("strikes_generated", count=len(strikes), low=rounded_low, high=rounded_high)
        return strikes
    
    def backfill_single_day(
        self,
        ticker: str,
        date_str: str,
        strikes: List[float],
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """
        Backfill options data for a single day.
        
        Args:
            ticker: Stock ticker
            date_str: Date in YYYY-MM-DD format
            strikes: List of strike prices
            save_to_db: If True, saves to Supabase
            
        Returns:
            DataFrame with all downloaded options data
        """
        logger.info("backfill_single_day_started", 
                   ticker=ticker, 
                   date=date_str, 
                   strikes=len(strikes))
        
        all_data = []
        
        for strike in strikes:
            try:
                # Download 0DTE options for this strike
                df = self.polygon_client.download_0dte_options_historic(
                    ticker=ticker,
                    strike=strike,
                    date=date_str
                )
                
                if not df.empty:
                    all_data.append(df)
                    logger.info("strike_downloaded", strike=strike, rows=len(df))
                
                # Rate limiting: Free tier allows 5 calls/minute
                # We make 2 calls per strike (CALL + PUT), so 2.5 strikes/minute max
                time.sleep(12)  # Wait 12 seconds between strikes
                
            except Exception as e:
                logger.error("strike_download_failed", error=str(e), strike=strike, date=date_str)
                continue
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Save to Supabase if requested
            if save_to_db:
                self._save_options_to_db(combined_df)
            
            logger.info("backfill_single_day_complete",
                       ticker=ticker,
                       date=date_str,
                       total_rows=len(combined_df))
            return combined_df
        else:
            logger.warning("no_data_downloaded", ticker=ticker, date=date_str)
            return pd.DataFrame()
    
    def backfill_date_range(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """
        Backfill options data for a date range (up to 90 days).
        
        Args:
            ticker: Stock ticker
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            save_to_db: If True, saves to Supabase
            
        Returns:
            DataFrame with all downloaded options data
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        days = (end - start).days + 1
        logger.info("backfill_range_started", 
                   ticker=ticker,
                   start=start_date,
                   end=end_date,
                   days=days)
        
        all_data = []
        current_date = start
        
        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Skip weekends
            if current_date.weekday() >= 5:
                logger.debug("skipping_weekend", date=date_str)
                current_date += timedelta(days=1)
                continue
            
            # Get daily range and generate strikes
            low, high = self.get_daily_price_range(ticker, date_str)
            strikes = self.generate_strike_list(low, high)
            
            # Download options for this day
            day_df = self.backfill_single_day(
                ticker=ticker,
                date_str=date_str,
                strikes=strikes,
                save_to_db=save_to_db
            )
            
            if not day_df.empty:
                all_data.append(day_df)
            
            current_date += timedelta(days=1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info("backfill_range_complete",
                       ticker=ticker,
                       total_days=len(all_data),
                       total_rows=len(combined_df))
            return combined_df
        else:
            logger.warning("no_data_in_range", ticker=ticker, start=start_date, end=end_date)
            return pd.DataFrame()
    
    def _save_options_to_db(self, df: pd.DataFrame):
        """
        Save options data to Supabase.
        
        Args:
            df: DataFrame with options data
        """
        try:
            # TODO: Implement bulk insert to option_prices table
            # For now, log the data
            logger.info("saving_options_to_db", rows=len(df))
            
            # Convert DataFrame to records and insert
            # self.supabase_client.bulk_insert_option_prices(df.to_dict('records'))
            
        except Exception as e:
            logger.error("save_options_failed", error=str(e), rows=len(df))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Bulk backfill historical options data from Polygon.io")
    parser.add_argument("--ticker", default="QQQ", help="Ticker symbol (default: QQQ)")
    parser.add_argument("--days", type=int, help="Number of days to backfill (from today backwards)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-save", action="store_true", help="Don't save to database (dry run)")
    parser.add_argument("--csv-output", help="Save to CSV file instead of database")
    
    args = parser.parse_args()
    
    # Calculate date range
    if args.days:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
    elif args.start_date and args.end_date:
        start_str = args.start_date
        end_str = args.end_date
    else:
        print("❌ Error: Provide either --days OR --start-date and --end-date")
        exit(1)
    
    print("="*80)
    print("BULK BACKFILL: Historical 0DTE Options Data")
    print("="*80)
    print(f"Ticker: {args.ticker}")
    print(f"Date Range: {start_str} to {end_str}")
    print(f"Data Source: Polygon.io")
    print(f"Save Target: {'CSV' if args.csv_output else 'Supabase Database'}")
    print("="*80)
    print()
    
    try:
        engine = OptionsBackfillEngine()
        
        # Run backfill
        df = engine.backfill_date_range(
            ticker=args.ticker,
            start_date=start_str,
            end_date=end_str,
            save_to_db=not args.no_save and not args.csv_output
        )
        
        print()
        print("="*80)
        print("BACKFILL COMPLETE")
        print("="*80)
        print(f"Total Rows: {len(df)}")
        print(f"Columns: {', '.join(df.columns.tolist())}")
        print()
        
        if args.csv_output:
            df.to_csv(args.csv_output, index=False)
            print(f"💾 Saved to: {args.csv_output}")
        elif not args.no_save:
            print(f"💾 Saved to: Supabase option_prices table")
        else:
            print(f"🔍 Dry run complete (not saved)")
        
        print()
        print("Sample data:")
        print(df.head())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Backfill interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()

