#!/usr/bin/env python3
"""
Auto-Backfill System

Automatically backfills missing data from Schwab/Polygon APIs.
Tracks data ranges and prevents duplicate data storage.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import json

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from schwab_integration.client import SchwabClient
from schwab_integration.downloader import PolygonDownloader
from supabase_client import supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoBackfillSystem:
    """Automatic data backfill system with duplicate prevention."""
    
    def __init__(self):
        self.schwab_client = SchwabClient(paper_trading=True)
        self.polygon_downloader = PolygonDownloader()
        self.data_ranges = {}  # Track data ranges per ticker
        
    async def get_data_range(self, ticker: str, data_type: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the current data range for a ticker and data type."""
        try:
            # Query the database for existing data range
            if data_type == 'equity':
                table = 'minute_data'
                timestamp_col = 'timestamp'
            elif data_type == 'options':
                table = 'synthetic_options'
                timestamp_col = 'timestamp'
            else:
                return None, None
            
            # Get earliest and latest timestamps
            result = supabase.table(table).select(timestamp_col).eq('ticker', ticker).order(timestamp_col).limit(1).execute()
            earliest = result.data[0][timestamp_col] if result.data else None
            
            result = supabase.table(table).select(timestamp_col).eq('ticker', ticker).order(timestamp_col, desc=True).limit(1).execute()
            latest = result.data[0][timestamp_col] if result.data else None
            
            if earliest:
                earliest = datetime.fromisoformat(earliest.replace('Z', '+00:00'))
            if latest:
                latest = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            
            return earliest, latest
            
        except Exception as e:
            logger.error(f"Error getting data range for {ticker} {data_type}: {e}")
            return None, None
    
    async def determine_backfill_range(self, ticker: str, data_type: str) -> Optional[Tuple[datetime, datetime]]:
        """Determine what data range needs to be backfilled."""
        try:
            # Get current data range
            earliest, latest = await self.get_data_range(ticker, data_type)
            
            # If no data exists, backfill last 30 days
            if not earliest or not latest:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                logger.info(f"No existing data for {ticker} {data_type}, backfilling last 30 days")
                return start_date, end_date
            
            # Check if we need to backfill recent data (last 24 hours)
            now = datetime.now()
            hours_since_last = (now - latest).total_seconds() / 3600
            
            if hours_since_last > 24:
                # Backfill from last data point to now
                start_date = latest
                end_date = now
                logger.info(f"Backfilling {ticker} {data_type} from {start_date} to {end_date}")
                return start_date, end_date
            
            # Check if we need to backfill historical data (older than 30 days)
            days_since_earliest = (now - earliest).total_seconds() / (24 * 3600)
            if days_since_earliest < 30:
                # Backfill older data
                start_date = earliest - timedelta(days=30)
                end_date = earliest
                logger.info(f"Backfilling historical {ticker} {data_type} from {start_date} to {end_date}")
                return start_date, end_date
            
            logger.info(f"No backfill needed for {ticker} {data_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error determining backfill range for {ticker} {data_type}: {e}")
            return None
    
    async def backfill_equity_data(self, ticker: str, start_date: datetime, end_date: datetime) -> bool:
        """Backfill equity data from Schwab API."""
        try:
            logger.info(f"Backfilling equity data for {ticker} from {start_date} to {end_date}")
            
            # Download data from Schwab
            data = await self.schwab_client.get_historical_data(
                ticker, start_date, end_date, 'minute'
            )
            
            if not data:
                logger.warning(f"No equity data received for {ticker}")
                return False
            
            # Check for duplicates before inserting
            existing_timestamps = set()
            for row in data:
                timestamp = row['datetime']
                existing_timestamps.add(timestamp)
            
            # Query existing data to avoid duplicates
            result = supabase.table('minute_data').select('timestamp').eq('ticker', ticker).in_('timestamp', list(existing_timestamps)).execute()
            existing_timestamps_in_db = {row['timestamp'] for row in result.data}
            
            # Filter out duplicates
            new_data = [row for row in data if row['datetime'] not in existing_timestamps_in_db]
            
            if not new_data:
                logger.info(f"No new equity data to insert for {ticker}")
                return True
            
            # Insert new data
            result = supabase.table('minute_data').insert(new_data).execute()
            
            logger.info(f"Inserted {len(new_data)} new equity data points for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error backfilling equity data for {ticker}: {e}")
            return False
    
    async def backfill_options_data(self, ticker: str, start_date: datetime, end_date: datetime) -> bool:
        """Backfill options data from Polygon API."""
        try:
            logger.info(f"Backfilling options data for {ticker} from {start_date} to {end_date}")
            
            # Download options data from Polygon
            data = await self.polygon_downloader.download_options_data(
                ticker, start_date.date(), end_date.date()
            )
            
            if not data:
                logger.warning(f"No options data received for {ticker}")
                return False
            
            # Check for duplicates before inserting
            existing_timestamps = set()
            for row in data:
                timestamp = row['timestamp']
                existing_timestamps.add(timestamp)
            
            # Query existing data to avoid duplicates
            result = supabase.table('synthetic_options').select('timestamp').eq('ticker', ticker).in_('timestamp', list(existing_timestamps)).execute()
            existing_timestamps_in_db = {row['timestamp'] for row in result.data}
            
            # Filter out duplicates
            new_data = [row for row in data if row['timestamp'] not in existing_timestamps_in_db]
            
            if not new_data:
                logger.info(f"No new options data to insert for {ticker}")
                return True
            
            # Insert new data
            result = supabase.table('synthetic_options').insert(new_data).execute()
            
            logger.info(f"Inserted {len(new_data)} new options data points for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error backfilling options data for {ticker}: {e}")
            return False
    
    async def auto_backfill(self, ticker: str, data_types: List[str] = ['equity', 'options']) -> Dict[str, bool]:
        """Automatically backfill missing data for a ticker."""
        results = {}
        
        for data_type in data_types:
            try:
                # Determine what needs to be backfilled
                backfill_range = await self.determine_backfill_range(ticker, data_type)
                
                if not backfill_range:
                    results[data_type] = True
                    continue
                
                start_date, end_date = backfill_range
                
                # Backfill the data
                if data_type == 'equity':
                    success = await self.backfill_equity_data(ticker, start_date, end_date)
                elif data_type == 'options':
                    success = await self.backfill_options_data(ticker, start_date, end_date)
                else:
                    success = False
                
                results[data_type] = success
                
            except Exception as e:
                logger.error(f"Error in auto backfill for {ticker} {data_type}: {e}")
                results[data_type] = False
        
        return results
    
    async def run_continuous_backfill(self, ticker: str, interval_minutes: int = 60):
        """Run continuous backfill every specified interval."""
        logger.info(f"Starting continuous backfill for {ticker} every {interval_minutes} minutes")
        
        while True:
            try:
                logger.info(f"Running auto backfill for {ticker}")
                results = await self.auto_backfill(ticker)
                
                for data_type, success in results.items():
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    logger.info(f"  {data_type}: {status}")
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in continuous backfill: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

async def main():
    """Main function for testing the auto backfill system."""
    backfill_system = AutoBackfillSystem()
    
    # Test with QQQ
    ticker = "QQQ"
    results = await backfill_system.auto_backfill(ticker)
    
    logger.info(f"Auto backfill results for {ticker}: {results}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
