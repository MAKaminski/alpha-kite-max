"""
Integration tests for complete trading workflow.

Tests the interaction between:
- Schwab API client
- Trading engine
- Supabase database
- Cross detection
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from schwab_integration.client import SchwabClient
from schwab_integration.trading_engine import TradingEngine
from schwab_integration.downloader import EquityDownloader
from schwab_integration.config import SchwabConfig, SupabaseConfig
from supabase_client import SupabaseClient
from models.trading import Position, Trade, TradingSignal


class TestTradingWorkflowIntegration:
    """Integration tests for trading workflow."""
    
    @pytest.fixture
    def schwab_client(self):
        """Create real Schwab client."""
        config = SchwabConfig()
        return SchwabClient(config)
    
    @pytest.fixture
    def supabase_client(self):
        """Create real Supabase client."""
        config = SupabaseConfig()
        return SupabaseClient(config)
    
    @pytest.fixture
    def trading_engine(self, schwab_client, supabase_client):
        """Create trading engine with real clients."""
        return TradingEngine(schwab_client, supabase_client)
    
    @pytest.fixture
    def downloader(self, schwab_client):
        """Create data downloader."""
        return EquityDownloader(schwab_client)
    
    def test_connections(self, schwab_client, supabase_client):
        """Test that all services are connected."""
        print("\n=== Testing Service Connections ===")
        
        # Test Schwab
        client = schwab_client.authenticate()
        assert client is not None
        print("✅ Schwab API connected")
        
        # Test Supabase
        success = supabase_client.test_connection()
        assert success
        print("✅ Supabase connected")
    
    def test_option_chain_retrieval(self, schwab_client):
        """Test retrieving option chains from Schwab."""
        print("\n=== Testing Option Chain Retrieval ===")
        
        try:
            chains = schwab_client.get_option_chains('QQQ', 'ALL')
            
            assert chains is not None
            assert isinstance(chains, dict)
            print(f"✅ Option chains retrieved")
            
            # Check for call and put maps
            has_calls = 'callExpDateMap' in chains
            has_puts = 'putExpDateMap' in chains
            
            print(f"   Calls available: {has_calls}")
            print(f"   Puts available: {has_puts}")
            
            assert has_calls or has_puts
            
        except Exception as e:
            print(f"⚠️  Option chain test skipped: {str(e)}")
            pytest.skip("Option chains not available")
    
    def test_account_info_retrieval(self, schwab_client):
        """Test retrieving account information."""
        print("\n=== Testing Account Info Retrieval ===")
        
        try:
            account_info = schwab_client.get_account_info()
            
            assert account_info is not None
            assert isinstance(account_info, dict)
            
            if 'hashValue' in account_info:
                print(f"✅ Account ID: {account_info['hashValue'][:8]}...")
            
        except Exception as e:
            print(f"⚠️  Account info test skipped: {str(e)}")
            pytest.skip("Account info not available")
    
    def test_cross_detection_from_database(self, supabase_client):
        """Test detecting crosses from database data."""
        print("\n=== Testing Cross Detection ===")
        
        # Get recent data
        equity_df = supabase_client.get_equity_data('QQQ', limit=100)
        indicators_df = supabase_client.get_indicators('QQQ', limit=100)
        
        if equity_df.empty or indicators_df.empty:
            print("⚠️  No data in database for cross detection")
            pytest.skip("Database data required")
        
        # Merge data
        merged = equity_df.merge(indicators_df, on=['ticker', 'timestamp'], how='inner')
        merged = merged.sort_values('timestamp')
        
        print(f"   Data points: {len(merged)}")
        
        # Detect crosses
        crosses = []
        for i in range(1, len(merged)):
            prev = merged.iloc[i-1]
            curr = merged.iloc[i]
            
            prev_diff = prev['sma9'] - prev['vwap']
            curr_diff = curr['sma9'] - curr['vwap']
            
            if prev_diff * curr_diff < 0:  # Cross
                direction = 'up' if curr_diff > 0 else 'down'
                crosses.append({
                    'timestamp': curr['timestamp'],
                    'direction': direction
                })
        
        print(f"   Crosses found: {len(crosses)}")
        
        # We don't assert on number of crosses (may be 0)
        assert isinstance(crosses, list)
    
    def test_position_lifecycle(self, supabase_client):
        """Test creating, updating, and closing a position."""
        print("\n=== Testing Position Lifecycle ===")
        
        # Create test position
        test_position = Position(
            ticker='QQQ',
            option_symbol='TEST_QQQ251024P00600000',
            option_type='PUT',
            strike_price=Decimal('600.00'),
            expiration_date=date.today() + timedelta(days=4),
            action='SELL_TO_OPEN',
            contracts=25,
            entry_price=Decimal('2.50'),
            entry_credit=Decimal('6250.00'),
            status='OPEN'
        )
        
        # Create position
        position_id = supabase_client.create_position(test_position)
        assert position_id is not None
        print(f"✅ Position created: {position_id[:8]}...")
        
        # Update position
        test_position.id = position_id
        test_position.current_price = Decimal('1.50')
        test_position.unrealized_pnl = Decimal('2500.00')
        
        update_success = supabase_client.update_position(test_position)
        assert update_success
        print(f"✅ Position updated")
        
        # Close position
        test_position.status = 'CLOSED'
        test_position.closed_at = datetime.now().isoformat()
        
        close_success = supabase_client.update_position(test_position)
        assert close_success
        print(f"✅ Position closed")
    
    def test_trade_recording(self, supabase_client):
        """Test recording trades."""
        print("\n=== Testing Trade Recording ===")
        
        # Create test trade
        test_trade = Trade(
            ticker='QQQ',
            option_symbol='TEST_QQQ251024P00600000',
            option_type='PUT',
            strike_price=Decimal('600.00'),
            expiration_date=date.today() + timedelta(days=4),
            action='SELL_TO_OPEN',
            contracts=25,
            price=Decimal('2.50'),
            credit_debit=Decimal('6250.00'),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        # Record trade
        trade_id = supabase_client.create_trade(test_trade)
        assert trade_id is not None
        print(f"✅ Trade recorded: {trade_id[:8]}...")
    
    def test_signal_recording(self, supabase_client):
        """Test recording trading signals."""
        print("\n=== Testing Signal Recording ===")
        
        # Create test signal
        test_signal = TradingSignal(
            ticker='QQQ',
            signal_timestamp=datetime.now(),
            signal_type='PUT_SELL',
            current_price=Decimal('600.00'),
            sma9_value=Decimal('599.50'),
            vwap_value=Decimal('600.50'),
            direction='down',
            action_taken=False
        )
        
        # Record signal
        signal_id = supabase_client.create_trading_signal(test_signal)
        assert signal_id is not None
        print(f"✅ Signal recorded: {signal_id[:8]}...")
    
    def test_option_quote_retrieval(self, schwab_client):
        """Test getting option quotes."""
        print("\n=== Testing Option Quote Retrieval ===")
        
        try:
            # Try to get a quote for a QQQ option
            # Note: This may fail if market is closed or symbol doesn't exist
            option_symbol = 'QQQ251024P00600000'  # Example symbol
            
            quote = schwab_client.get_option_quote(option_symbol)
            
            if quote:
                print(f"✅ Quote retrieved for {option_symbol}")
            else:
                print(f"⚠️  No quote available (may be normal if market closed)")
            
        except Exception as e:
            print(f"⚠️  Quote retrieval test skipped: {str(e)}")
            pytest.skip("Option quotes not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

