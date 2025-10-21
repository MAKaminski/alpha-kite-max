"""
Unit tests for Trading Engine module.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from schwab_integration.trading_engine import TradingEngine
from schwab_integration.client import SchwabClient
from clients.supabase_client import SupabaseClient
from models.trading import Position, Trade, TradingSignal


class TestTradingEngine:
    """Unit tests for TradingEngine class."""
    
    @pytest.fixture
    def mock_schwab_client(self):
        """Create mock Schwab client."""
        mock = Mock(spec=SchwabClient)
        return mock
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        mock = Mock(spec=SupabaseClient)
        return mock
    
    @pytest.fixture
    def trading_engine(self, mock_schwab_client, mock_supabase_client):
        """Create TradingEngine with mocked clients."""
        return TradingEngine(mock_schwab_client, mock_supabase_client)
    
    def test_initialization(self, trading_engine):
        """Test TradingEngine initializes correctly."""
        assert trading_engine is not None
        assert trading_engine.contract_size == 25
        assert trading_engine.profit_target == 0.50
        assert trading_engine.stop_loss == 2.00
    
    def test_is_trading_allowed_within_hours(self, trading_engine):
        """Test trading is allowed during trading hours."""
        # 11:00 AM ET (within 10 AM - 2:30 PM window)
        test_time = pd.Timestamp('2025-10-20 11:00:00', tz='America/New_York')
        result = trading_engine._is_trading_allowed(test_time.isoformat())
        
        assert result is True
    
    def test_is_trading_allowed_end_of_session(self, trading_engine):
        """Test trading is not allowed in last 30 mins."""
        # 2:35 PM ET (after 2:30 PM cutoff)
        test_time = pd.Timestamp('2025-10-20 14:35:00', tz='America/New_York')
        result = trading_engine._is_trading_allowed(test_time.isoformat())
        
        assert result is False
    
    def test_is_trading_allowed_after_close(self, trading_engine):
        """Test trading is not allowed after market close."""
        # 3:30 PM ET (after 3:00 PM close)
        test_time = pd.Timestamp('2025-10-20 15:30:00', tz='America/New_York')
        result = trading_engine._is_trading_allowed(test_time.isoformat())
        
        assert result is False
    
    def test_get_signal_type_down(self, trading_engine):
        """Test signal type for downward cross."""
        signal_type = trading_engine._get_signal_type('down')
        assert signal_type == 'PUT_SELL'
    
    def test_get_signal_type_up(self, trading_engine):
        """Test signal type for upward cross."""
        signal_type = trading_engine._get_signal_type('up')
        assert signal_type == 'CALL_SELL'
    
    def test_find_nearest_put_strike_fallback(self, trading_engine, mock_schwab_client):
        """Test PUT strike finding with fallback."""
        mock_schwab_client.get_option_chains.return_value = {}
        
        strike = trading_engine._find_nearest_put_strike('QQQ', 600.5)
        
        # Should use fallback: int(price) - 1
        assert strike == 599.0
    
    def test_find_nearest_call_strike_fallback(self, trading_engine, mock_schwab_client):
        """Test CALL strike finding with fallback."""
        mock_schwab_client.get_option_chains.return_value = {}
        
        strike = trading_engine._find_nearest_call_strike('QQQ', 600.5)
        
        # Should use fallback: int(price) + 1
        assert strike == 601.0
    
    def test_build_option_symbol(self, trading_engine):
        """Test option symbol building."""
        test_date = date(2025, 10, 24)  # Friday
        
        with patch.object(trading_engine, '_get_next_friday', return_value=test_date):
            # Test PUT symbol
            put_symbol = trading_engine._build_option_symbol('QQQ', 600.0, 'PUT')
            assert 'QQQ' in put_symbol
            assert '251024' in put_symbol  # YYMMDD
            assert 'P' in put_symbol
            
            # Test CALL symbol
            call_symbol = trading_engine._build_option_symbol('QQQ', 600.0, 'CALL')
            assert 'QQQ' in call_symbol
            assert '251024' in call_symbol
            assert 'C' in call_symbol
    
    def test_get_next_friday(self, trading_engine):
        """Test getting next Friday expiration."""
        next_friday = trading_engine._get_next_friday()
        
        # _get_next_friday returns datetime, not date
        # Convert to date for comparison
        next_friday_date = next_friday.date() if hasattr(next_friday, 'date') else next_friday
        
        assert next_friday_date.weekday() == 4  # Friday
        assert next_friday_date >= datetime.now().date()
    
    def test_process_cross_signal_down_no_position(self, trading_engine, mock_supabase_client):
        """Test downward cross with no open positions."""
        mock_supabase_client.get_open_positions.return_value = []
        
        # Mock the _sell_puts method
        expected_result = {
            'action': 'PUT_SELL',
            'strike_price': 599.0,
            'contracts': 25
        }
        
        with patch.object(trading_engine, '_sell_puts', return_value=expected_result):
            result = trading_engine.process_cross_signal(
                ticker='QQQ',
                signal_timestamp='2025-10-20T11:00:00',
                current_price=600.0,
                sma9=599.0,
                vwap=600.0,
                direction='down'
            )
            
            assert result is not None
            assert result['action'] == 'PUT_SELL'
    
    def test_process_cross_signal_down_position_exists(self, trading_engine, mock_supabase_client):
        """Test downward cross when position already exists."""
        # Mock existing position
        existing_position = Mock(spec=Position)
        mock_supabase_client.get_open_positions.return_value = [existing_position]
        
        result = trading_engine.process_cross_signal(
            ticker='QQQ',
            signal_timestamp='2025-10-20T11:00:00',
            current_price=600.0,
            sma9=599.0,
            vwap=600.0,
            direction='down'
        )
        
        # Should skip because position already exists
        assert result is None
    
    def test_process_cross_signal_outside_trading_hours(self, trading_engine):
        """Test signal processing outside trading hours."""
        # 2:45 PM (after 2:30 PM cutoff)
        result = trading_engine.process_cross_signal(
            ticker='QQQ',
            signal_timestamp='2025-10-20T14:45:00-04:00',
            current_price=600.0,
            sma9=599.0,
            vwap=600.0,
            direction='down'
        )
        
        # Should return None (outside trading window)
        assert result is None
    
    def test_check_profit_loss_targets_profit_hit(self, trading_engine, mock_supabase_client):
        """Test profit target checking."""
        # Create mock position with profit
        mock_position = Mock(spec=Position)
        mock_position.id = 'test-id'
        mock_position.option_symbol = 'QQQ251020P00600000'
        mock_position.contracts = 25
        mock_position.entry_credit = 6000  # Entry credit $6000
        
        mock_supabase_client.get_open_positions.return_value = [mock_position]
        
        # Mock quote showing profit (current price much lower than entry)
        mock_quote = {
            'last': 1.0,  # Entered at ~$2.40, now at $1.00 = 58% profit
            'bid': 0.95,
            'ask': 1.05
        }
        
        with patch.object(trading_engine, '_get_option_quote', return_value=mock_quote):
            with patch.object(trading_engine, '_close_positions', return_value=True):
                closed = trading_engine.check_profit_loss_targets('QQQ')
                
                assert len(closed) > 0
                assert closed[0]['reason'] == 'profit_target'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

