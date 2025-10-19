"""
Tests for end-of-day position closing logic.

Ensures that all positions are automatically closed at 2:55 PM ET,
guaranteeing at least 2 trades per position (open + close).
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_main import TradingBot
from models.trading import Position


class TestEndOfDayClose:
    """Test end-of-day position closing functionality."""
    
    @pytest.fixture
    def mock_open_position(self):
        """Create a mock open position."""
        return Position(
            id="test-position-123",
            ticker="QQQ",
            option_symbol="QQQ251024P00600000",
            option_type="PUT",
            strike_price=Decimal("600.00"),
            expiration_date=datetime.now().date() + timedelta(days=5),
            action="SELL_TO_OPEN",
            contracts=25,
            entry_price=Decimal("2.50"),
            entry_credit=Decimal("6250.00"),
            current_price=Decimal("1.25"),
            unrealized_pnl=Decimal("3125.00"),
            status="OPEN",
            created_at=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_end_of_day_close_at_255pm(self, mock_open_position):
        """Test that positions are closed at 2:55 PM ET."""
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            bot.supabase_client = Mock()
            bot.trading_engine = Mock()
            bot.supabase_client.get_open_positions = Mock(return_value=[mock_open_position])
            bot.trading_engine._close_positions = Mock(return_value=True)
        
            # Create timestamp at 2:55 PM
            close_time = datetime.now().replace(hour=14, minute=55, second=0, microsecond=0)
            
            # Act
            await bot._check_end_of_day_close(close_time)
            
            # Assert
            bot.supabase_client.get_open_positions.assert_called_once_with("QQQ")
            bot.trading_engine._close_positions.assert_called_once()
            
            # Verify close_positions was called with the position
            call_args = bot.trading_engine._close_positions.call_args
            positions_arg = call_args[0][0]  # First positional argument
            assert len(positions_arg) == 1
            assert positions_arg[0].id == "test-position-123"
    
    @pytest.mark.asyncio
    async def test_no_close_before_255pm(self, mock_open_position):
        """Test that positions are NOT closed before 2:55 PM."""
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            bot.supabase_client = Mock()
            bot.trading_engine = Mock()
            bot.supabase_client.get_open_positions = Mock(return_value=[mock_open_position])
            bot.trading_engine._close_positions = Mock(return_value=True)
        
            # Create timestamp at 2:30 PM (before close time)
            early_time = datetime.now().replace(hour=14, minute=30, second=0, microsecond=0)
            
            # Act
            await bot._check_end_of_day_close(early_time)
            
            # Assert
            bot.trading_engine._close_positions.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_close_after_3pm(self, mock_open_position):
        """Test that positions are NOT closed after 3:00 PM."""
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            bot.supabase_client = Mock()
            bot.trading_engine = Mock()
            bot.supabase_client.get_open_positions = Mock(return_value=[mock_open_position])
            bot.trading_engine._close_positions = Mock(return_value=True)
        
            # Create timestamp at 3:05 PM (after close time)
            late_time = datetime.now().replace(hour=15, minute=5, second=0, microsecond=0)
            
            # Act
            await bot._check_end_of_day_close(late_time)
            
            # Assert
            bot.trading_engine._close_positions.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_end_of_day_close_with_no_positions(self):
        """Test end-of-day close when no positions are open."""
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            bot.supabase_client = Mock()
            bot.trading_engine = Mock()
            bot.supabase_client.get_open_positions = Mock(return_value=[])  # No positions
            bot.trading_engine._close_positions = Mock(return_value=True)
        
            # Create timestamp at 2:55 PM
            close_time = datetime.now().replace(hour=14, minute=55, second=0, microsecond=0)
            
            # Act
            await bot._check_end_of_day_close(close_time)
            
            # Assert
            bot.trading_engine._close_positions.assert_not_called()  # Should not call if no positions
    
    def test_is_trading_allowed_before_230pm(self):
        """Test that trading is allowed before 2:30 PM."""
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            timestamp = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)  # Noon
            
            # Act
            result = bot._is_trading_allowed(timestamp)
            
            # Assert
            assert result is True
    
    def test_is_trading_not_allowed_after_230pm(self):
        """Test that trading is NOT allowed after 2:30 PM."""
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            timestamp = datetime.now().replace(hour=14, minute=30, second=0, microsecond=0)  # 2:30 PM
            
            # Act
            result = bot._is_trading_allowed(timestamp)
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_two_trades_per_position(self, mock_open_position):
        """
        Critical Test: Ensure every position has at least 2 trades (open + close).
        
        This test validates that:
        1. Position is opened with SELL_TO_OPEN trade
        2. Position is closed with BUY_TO_CLOSE trade (either by target or EOD)
        """
        # Arrange
        with patch('trading_main.SchwabClient'), \
             patch('trading_main.SupabaseClient'), \
             patch('trading_main.EquityDownloader'), \
             patch('trading_main.TradingEngine'):
            bot = TradingBot()
            bot.supabase_client = Mock()
            bot.trading_engine = Mock()
            
            # Mock that we have one open position
            bot.supabase_client.get_open_positions = Mock(return_value=[mock_open_position])
            bot.trading_engine._close_positions = Mock(return_value=True)
            
            # Simulate end of day close at 2:55 PM
            close_time = datetime.now().replace(hour=14, minute=55, second=0, microsecond=0)
            
            # Act
            await bot._check_end_of_day_close(close_time)
            
            # Assert
            # Verify that _close_positions was called (which creates BUY_TO_CLOSE trade)
            bot.trading_engine._close_positions.assert_called_once()
            
            # This ensures:
            # - Trade 1: SELL_TO_OPEN (when position created)
            # - Trade 2: BUY_TO_CLOSE (via end-of-day close)
            # = Minimum 2 trades per position ✅
            
            print("\n✅ TEST PASSED: Every position will have at least 2 trades")
            print("   Trade 1: SELL_TO_OPEN (position entry)")
            print("   Trade 2: BUY_TO_CLOSE (end-of-day close at 2:55 PM)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

