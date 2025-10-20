#!/usr/bin/env python3
"""
Manual Trading Tests

Comprehensive tests for manual order entry, portfolio tracking,
and trade execution scenarios.
"""

import unittest
import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio_tracker import PortfolioTracker
from models.trading import Position, Trade

class TestManualTrading(unittest.TestCase):
    """Test manual trading functionality."""
    
    def setUp(self):
        """Set up test portfolio tracker."""
        self.tracker = PortfolioTracker(initial_balance=Decimal("100000.00"))
    
    def test_sell_to_open_trade(self):
        """Test opening a new position with SELL_TO_OPEN."""
        # Create a SELL_TO_OPEN trade
        trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020C00600000",
            option_type="CALL",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("5.50"),
            credit_debit=Decimal("5500.00"),  # Credit received
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        # Add trade to portfolio
        success = self.tracker.add_trade(trade)
        self.assertTrue(success, "Trade should be added successfully")
        
        # Verify portfolio state
        self.assertEqual(self.tracker.get_position_count(), 1,
                        "Should have 1 open position")
        self.assertEqual(self.tracker.current_balance, Decimal("105500.00"),
                        "Cash balance should include credit received")
        
        # Verify account balance
        account_balance = self.tracker.get_account_balance()
        self.assertGreater(account_balance, Decimal("100000.00"),
                          "Account balance should be positive")
    
    def test_buy_to_close_trade(self):
        """Test closing a position with BUY_TO_CLOSE."""
        # First, open a position
        open_trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00600000",
            option_type="PUT",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("5.50"),
            credit_debit=Decimal("5500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(open_trade)
        self.assertEqual(self.tracker.get_position_count(), 1)
        
        # Now close the position
        close_trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00600000",
            option_type="PUT",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="BUY_TO_CLOSE",
            contracts=10,
            price=Decimal("4.00"),
            credit_debit=Decimal("4000.00"),  # Debit paid
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        success = self.tracker.add_trade(close_trade)
        self.assertTrue(success, "Close trade should succeed")
        
        # Verify position is closed
        self.assertEqual(self.tracker.get_position_count(), 0,
                        "Should have 0 open positions")
        
        # Verify P&L: $5500 credit - $4000 debit = $1500 profit
        expected_balance = Decimal("101500.00")
        self.assertEqual(self.tracker.current_balance, expected_balance,
                        f"Cash balance should be ${expected_balance}")
    
    def test_profitable_trade_scenario(self):
        """Test a profitable trade scenario."""
        # Sell a PUT at $5.50
        sell_trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00595000",
            option_type="PUT",
            strike_price=Decimal("595.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("5.50"),
            credit_debit=Decimal("5500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(sell_trade)
        
        # Price drops, buy back at $3.00
        buy_trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00595000",
            option_type="PUT",
            strike_price=Decimal("595.0"),
            expiration_date=date(2025, 10, 20),
            action="BUY_TO_CLOSE",
            contracts=10,
            price=Decimal("3.00"),
            credit_debit=Decimal("3000.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(buy_trade)
        
        # Verify profit: $5500 - $3000 = $2500
        profit = self.tracker.current_balance - self.tracker.initial_balance
        self.assertEqual(profit, Decimal("2500.00"),
                        "Profit should be $2500")
        
        # Verify no open positions
        self.assertEqual(self.tracker.get_position_count(), 0)
    
    def test_losing_trade_scenario(self):
        """Test a losing trade scenario."""
        # Sell a CALL at $4.00
        sell_trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020C00605000",
            option_type="CALL",
            strike_price=Decimal("605.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("4.00"),
            credit_debit=Decimal("4000.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(sell_trade)
        
        # Price rises, buy back at $6.50 (loss)
        buy_trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020C00605000",
            option_type="CALL",
            strike_price=Decimal("605.0"),
            expiration_date=date(2025, 10, 20),
            action="BUY_TO_CLOSE",
            contracts=10,
            price=Decimal("6.50"),
            credit_debit=Decimal("6500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(buy_trade)
        
        # Verify loss: $4000 - $6500 = -$2500
        pnl = self.tracker.current_balance - self.tracker.initial_balance
        self.assertEqual(pnl, Decimal("-2500.00"),
                        "Loss should be -$2500")
    
    def test_multiple_positions(self):
        """Test managing multiple positions simultaneously."""
        # Open two different positions
        trade1 = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00595000",
            option_type="PUT",
            strike_price=Decimal("595.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=5,
            price=Decimal("5.00"),
            credit_debit=Decimal("2500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        trade2 = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020C00605000",
            option_type="CALL",
            strike_price=Decimal("605.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=5,
            price=Decimal("4.00"),
            credit_debit=Decimal("2000.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(trade1)
        self.tracker.add_trade(trade2)
        
        # Verify we have 2 positions
        self.assertEqual(self.tracker.get_position_count(), 2,
                        "Should have 2 open positions")
        
        # Verify total credits received
        expected_balance = Decimal("100000.00") + Decimal("2500.00") + Decimal("2000.00")
        self.assertEqual(self.tracker.current_balance, expected_balance,
                        "Cash balance should include both credits")
    
    def test_portfolio_summary(self):
        """Test portfolio summary generation."""
        # Open a position
        trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00600000",
            option_type="PUT",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("5.50"),
            credit_debit=Decimal("5500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(trade)
        
        # Get summary
        summary = self.tracker.get_portfolio_summary()
        
        # Verify summary structure
        self.assertIn('account_balance', summary)
        self.assertIn('cash_balance', summary)
        self.assertIn('total_pnl', summary)
        self.assertIn('open_positions', summary)
        self.assertIn('positions', summary)
        self.assertIn('balance_history', summary)
        
        # Verify values
        self.assertEqual(summary['open_positions'], 1)
        self.assertEqual(summary['cash_balance'], 105500.00)
        self.assertTrue(len(summary['positions']) > 0)
        self.assertTrue(len(summary['balance_history']) > 0)
    
    def test_balance_history_tracking(self):
        """Test that balance history is tracked correctly."""
        initial_count = len(self.tracker.balance_history)
        
        # Execute a trade
        trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00600000",
            option_type="PUT",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("5.50"),
            credit_debit=Decimal("5500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(trade)
        
        # Verify balance history was updated
        self.assertEqual(len(self.tracker.balance_history), initial_count + 1,
                        "Balance history should have one more entry")
        
        # Verify latest entry
        latest = self.tracker.balance_history[-1]
        self.assertIn('timestamp', latest)
        self.assertIn('balance', latest)
        self.assertIn('open_positions', latest)
        self.assertEqual(latest['open_positions'], 1)
    
    def test_cannot_close_nonexistent_position(self):
        """Test that closing a non-existent position fails gracefully."""
        # Try to close a position that doesn't exist
        trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00600000",
            option_type="PUT",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="BUY_TO_CLOSE",
            contracts=10,
            price=Decimal("4.00"),
            credit_debit=Decimal("4000.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        success = self.tracker.add_trade(trade)
        
        # Should fail gracefully
        self.assertFalse(success, "Should not be able to close non-existent position")
        
        # Verify balance unchanged
        self.assertEqual(self.tracker.current_balance, self.tracker.initial_balance,
                        "Balance should remain unchanged")
    
    def test_position_pnl_calculation(self):
        """Test P&L calculation for open positions."""
        # Open a position
        trade = Trade(
            ticker="QQQ",
            option_symbol="QQQ251020P00600000",
            option_type="PUT",
            strike_price=Decimal("600.0"),
            expiration_date=date(2025, 10, 20),
            action="SELL_TO_OPEN",
            contracts=10,
            price=Decimal("5.50"),
            credit_debit=Decimal("5500.00"),
            trade_timestamp=datetime.now(),
            signal_timestamp=datetime.now()
        )
        
        self.tracker.add_trade(trade)
        
        # Update position price
        position_key = "QQQ_QQQ251020P00600000"
        position = self.tracker.positions[position_key]
        position.current_price = Decimal("4.00")  # Price dropped, profitable
        
        # Calculate P&L
        pnl = self.tracker.calculate_position_pnl(position)
        
        # For sold options: entry_credit - current_value
        # $5500 - ($4.00 * 10 * 100) = $5500 - $4000 = $1500
        expected_pnl = Decimal("1500.00")
        self.assertEqual(pnl, expected_pnl,
                        f"P&L should be ${expected_pnl}")

def run_tests():
    """Run all manual trading tests."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestManualTrading)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

