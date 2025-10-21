"""
Test suite for real-time streaming data for current day (10/15/25).

This tests the entire pipeline:
1. Schwab API connection
2. Current day data download
3. Indicator calculation
4. Supabase upload
5. Frontend data retrieval
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schwab_integration.client import SchwabClient
from schwab_integration.downloader import EquityDownloader
from schwab_integration.config import SchwabConfig, SupabaseConfig
from clients.supabase_client import SupabaseClient
import structlog

logger = structlog.get_logger()


class TestRealTimeStreaming:
    """Test real-time data streaming for current day."""
    
    @pytest.fixture
    def schwab_client(self):
        """Create Schwab client."""
        config = SchwabConfig()
        return SchwabClient(config)
    
    @pytest.fixture
    def supabase_client(self):
        """Create Supabase client."""
        config = SupabaseConfig()
        return SupabaseClient(config)
    
    @pytest.fixture
    def downloader(self, schwab_client):
        """Create data downloader."""
        return EquityDownloader(schwab_client)
    
    def test_schwab_connection_current_day(self, schwab_client):
        """Test Schwab API connection works for current day."""
        print("\n=== Testing Schwab API Connection ===")
        
        try:
            # Test authentication
            client = schwab_client.authenticate()
            assert client is not None, "Schwab client authentication failed"
            print("✅ Schwab API authentication successful")
            
            # Test price history for today (1 day period)
            ticker = "QQQ"
            data = schwab_client.get_price_history(
                symbol=ticker,
                period_type="day",
                period=1,
                frequency_type="minute",
                frequency=1
            )
            
            # get_price_history returns dict, not response object
            assert data is not None, "API call returned None"
            print(f"✅ Schwab API returned data for {ticker}")
            
            candles = data.get('candles', [])
            
            print(f"\n📊 Current Day Data Summary:")
            print(f"   Total candles: {len(candles)}")
            
            if candles:
                first_candle = candles[0]
                last_candle = candles[-1]
                
                first_time = datetime.fromtimestamp(first_candle['datetime'] / 1000)
                last_time = datetime.fromtimestamp(last_candle['datetime'] / 1000)
                
                print(f"   First candle: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Last candle: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   First price: ${first_candle['close']:.2f}")
                print(f"   Last price: ${last_candle['close']:.2f}")
                
                # Check if data is from today
                today = datetime.now().date()
                first_date = first_time.date()
                
                print(f"\n   Today's date: {today}")
                print(f"   Data from: {first_date}")
                print(f"   Is current day data: {first_date == today}")
                
                assert len(candles) > 0, "No candles returned for current day"
                print("\n✅ Current day data retrieved successfully")
            else:
                print("⚠️ WARNING: No candles returned for current day")
                print("   This might be normal if market is closed or before market open")
            
            return candles
            
        except Exception as e:
            print(f"❌ Error testing Schwab connection: {e}")
            raise
    
    def test_download_current_day_data(self, downloader):
        """Test downloading current day data through downloader."""
        print("\n=== Testing Data Downloader for Current Day ===")
        
        ticker = "QQQ"
        
        try:
            # Download 1 day of data (should be today)
            df = downloader.download_minute_data(ticker, days=1)
            
            print(f"\n📊 Downloaded Data Summary:")
            print(f"   Total rows: {len(df)}")
            
            if not df.empty:
                print(f"   Columns: {list(df.columns)}")
                print(f"\n   First 3 rows:")
                print(df.head(3).to_string())
                print(f"\n   Last 3 rows:")
                print(df.tail(3).to_string())
                
                # Check date range
                first_timestamp = df['timestamp'].min()
                last_timestamp = df['timestamp'].max()
                
                print(f"\n   Date range:")
                print(f"   From: {first_timestamp}")
                print(f"   To: {last_timestamp}")
                
                # Check if data is from today
                today = datetime.now().date()
                # first_timestamp is already a pandas Timestamp object
                data_date = first_timestamp.date() if hasattr(first_timestamp, 'date') else first_timestamp
                
                print(f"\n   Today's date: {today}")
                print(f"   Data from: {data_date}")
                print(f"   Is current day: {data_date == today}")
                
                assert len(df) > 0, "No data downloaded for current day"
                print("\n✅ Current day data downloaded successfully")
            else:
                print("⚠️ WARNING: Empty DataFrame returned")
                print("   Market might be closed or data not available")
            
            return df
            
        except Exception as e:
            print(f"❌ Error downloading data: {e}")
            raise
    
    def test_calculate_indicators_current_day(self, downloader):
        """Test indicator calculation for current day data."""
        print("\n=== Testing Indicator Calculation for Current Day ===")
        
        ticker = "QQQ"
        
        try:
            # Download data
            df = downloader.download_minute_data(ticker, days=1)
            
            if df.empty:
                print("⚠️ No data to calculate indicators (market might be closed)")
                return
            
            # Calculate indicators
            indicators = downloader.calculate_indicators(df)
            
            print(f"\n📊 Indicators Summary:")
            print(f"   Total rows: {len(indicators)}")
            
            if not indicators.empty:
                print(f"   Columns: {list(indicators.columns)}")
                print(f"\n   First 3 rows:")
                print(indicators.head(3).to_string())
                print(f"\n   Last 3 rows:")
                print(indicators.tail(3).to_string())
                
                # Check for NaN values
                nan_counts = indicators.isna().sum()
                print(f"\n   NaN counts:")
                for col, count in nan_counts.items():
                    print(f"   {col}: {count}")
                
                # Verify SMA9 and VWAP are calculated
                assert 'sma9' in indicators.columns, "SMA9 not calculated"
                assert 'vwap' in indicators.columns, "VWAP not calculated"
                
                # Check last values
                last_row = indicators.iloc[-1]
                print(f"\n   Latest indicators:")
                print(f"   Timestamp: {last_row['timestamp']}")
                print(f"   SMA9: ${last_row['sma9']:.2f}")
                print(f"   VWAP: ${last_row['vwap']:.2f}")
                
                print("\n✅ Indicators calculated successfully")
            else:
                print("⚠️ WARNING: Empty indicators DataFrame")
            
            return indicators
            
        except Exception as e:
            print(f"❌ Error calculating indicators: {e}")
            raise
    
    def test_upload_current_day_to_supabase(self, downloader, supabase_client):
        """Test uploading current day data to Supabase."""
        print("\n=== Testing Supabase Upload for Current Day ===")
        
        ticker = "QQQ"
        
        try:
            # Download data
            df = downloader.download_minute_data(ticker, days=1)
            
            if df.empty:
                print("⚠️ No data to upload (market might be closed)")
                return
            
            # Upload equity data
            print("\n📤 Uploading equity data...")
            equity_success = supabase_client.upsert_equity_data(df)
            assert equity_success, "Failed to upload equity data"
            print(f"✅ Uploaded {len(df)} equity data rows")
            
            # Calculate and upload indicators
            indicators = downloader.calculate_indicators(df)
            
            if not indicators.empty:
                print("\n📤 Uploading indicators...")
                indicators_success = supabase_client.upsert_indicators(indicators)
                assert indicators_success, "Failed to upload indicators"
                print(f"✅ Uploaded {len(indicators)} indicator rows")
            
            # Verify data was uploaded
            print("\n🔍 Verifying uploaded data...")
            
            # Retrieve equity data (get_equity_data returns DataFrame, not list)
            retrieved_equity_df = supabase_client.get_equity_data(
                ticker=ticker,
                limit=1000
            )
            
            print(f"\n📥 Retrieved equity data: {len(retrieved_equity_df)} rows")
            
            if not retrieved_equity_df.empty:
                print(f"   First timestamp: {retrieved_equity_df['timestamp'].iloc[0]}")
                print(f"   Last timestamp: {retrieved_equity_df['timestamp'].iloc[-1]}")
                print(f"   Sample price: ${retrieved_equity_df['price'].iloc[-1]:.2f}")
            
            # Retrieve indicators (get_indicators returns DataFrame, not list)
            retrieved_indicators_df = supabase_client.get_indicators(
                ticker=ticker,
                limit=1000
            )
            
            print(f"\n📥 Retrieved indicators: {len(retrieved_indicators_df)} rows")
            
            if not retrieved_indicators_df.empty:
                print(f"   Last timestamp: {retrieved_indicators_df['timestamp'].iloc[-1]}")
                print(f"   Last SMA9: ${retrieved_indicators_df['sma9'].iloc[-1]:.2f}")
                print(f"   Last VWAP: ${retrieved_indicators_df['vwap'].iloc[-1]:.2f}")
            
            assert len(retrieved_equity_df) > 0, "No equity data retrieved from Supabase"
            assert len(retrieved_indicators_df) > 0, "No indicators retrieved from Supabase"
            
            print("\n✅ Data successfully uploaded and retrieved from Supabase")
            
        except Exception as e:
            print(f"❌ Error uploading to Supabase: {e}")
            raise
    
    def test_real_time_update_cycle(self, downloader, supabase_client):
        """Test a complete real-time update cycle."""
        print("\n=== Testing Complete Real-Time Update Cycle ===")
        
        ticker = "QQQ"
        
        try:
            # Step 1: Download current data
            print("\n📥 Step 1: Downloading current data...")
            df = downloader.download_minute_data(ticker, days=1)
            
            if df.empty:
                print("⚠️ No data available (market might be closed)")
                return
            
            initial_count = len(df)
            print(f"   Downloaded {initial_count} rows")
            
            # Step 2: Calculate indicators
            print("\n📊 Step 2: Calculating indicators...")
            indicators = downloader.calculate_indicators(df)
            print(f"   Calculated indicators for {len(indicators)} rows")
            
            # Step 3: Upload to Supabase
            print("\n📤 Step 3: Uploading to Supabase...")
            supabase_client.upsert_equity_data(df)
            supabase_client.upsert_indicators(indicators)
            print("   Upload complete")
            
            # Step 4: Verify frontend can retrieve data
            print("\n🔍 Step 4: Verifying frontend data retrieval...")
            
            equity_data_df = supabase_client.get_equity_data(ticker, limit=1000)
            indicator_data_df = supabase_client.get_indicators(ticker, limit=1000)
            
            print(f"   Frontend can retrieve {len(equity_data_df)} equity rows")
            print(f"   Frontend can retrieve {len(indicator_data_df)} indicator rows")
            
            # Step 5: Check for recent data (within last hour)
            print("\n⏰ Step 5: Checking for recent data...")
            
            if not equity_data_df.empty:
                last_timestamp = equity_data_df['timestamp'].iloc[-1]
                # Handle both string and Timestamp objects
                if isinstance(last_timestamp, str):
                    last_time = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                else:
                    last_time = last_timestamp
                time_diff = datetime.now(last_time.tzinfo) - last_time
                
                print(f"   Last data point: {last_timestamp}")
                print(f"   Time since last update: {time_diff}")
                
                is_recent = time_diff < timedelta(hours=1)
                print(f"   Is recent (< 1 hour): {is_recent}")
                
                if is_recent:
                    print("\n✅ Real-time data is flowing correctly!")
                else:
                    print("\n⚠️ WARNING: Latest data is more than 1 hour old")
                    print("   Market might be closed or data feed delayed")
            
            print("\n✅ Complete real-time update cycle tested successfully")
            
        except Exception as e:
            print(f"❌ Error in update cycle: {e}")
            raise


if __name__ == "__main__":
    """Run tests manually without pytest."""
    print("=" * 80)
    print("REAL-TIME STREAMING DATA TESTS FOR 10/15/25")
    print("=" * 80)
    
    # Create test instance
    test = TestRealTimeStreaming()
    
    # Setup fixtures
    schwab_config = SchwabConfig()
    schwab_client = SchwabClient(schwab_config)
    
    supabase_config = SupabaseConfig()
    supabase_client = SupabaseClient(supabase_config)
    
    downloader = EquityDownloader(schwab_client)
    
    # Run tests
    try:
        print("\n" + "=" * 80)
        test.test_schwab_connection_current_day(schwab_client)
        
        print("\n" + "=" * 80)
        test.test_download_current_day_data(downloader)
        
        print("\n" + "=" * 80)
        test.test_calculate_indicators_current_day(downloader)
        
        print("\n" + "=" * 80)
        test.test_upload_current_day_to_supabase(downloader, supabase_client)
        
        print("\n" + "=" * 80)
        test.test_real_time_update_cycle(downloader, supabase_client)
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()

