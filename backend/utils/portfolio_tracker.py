#!/usr/bin/env python3
"""
Portfolio Tracker

Tracks account balance, open positions, and trade history.
Provides real-time portfolio metrics for dashboard display.
"""

import os
import sys
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.trading import Position, Trade, TradingSignal
from clients.supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PortfolioTracker:
    """Track portfolio state including account balance and positions."""
    
    def __init__(self, initial_balance: Decimal = Decimal("100000.00"), use_database: bool = False):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        self.balance_history: List[Dict] = []
        self.use_database = use_database
        self.supabase_client = SupabaseClient() if use_database else None
        
    def get_account_balance(self) -> Decimal:
        """Get current account balance including unrealized P&L."""
        # Start with current cash balance
        total = self.current_balance
        
        # Add unrealized P&L from open positions
        for position in self.positions.values():
            if position.current_price:
                unrealized_pnl = self.calculate_position_pnl(position)
                total += unrealized_pnl
        
        return total
    
    def calculate_position_pnl(self, position: Position) -> Decimal:
        """Calculate P&L for a position."""
        if not position.current_price:
            return Decimal("0.00")
        
        # For sold options (SELL_TO_OPEN), we profit when price goes down
        if position.action == "SELL_TO_OPEN":
            # Entry credit - current value
            current_value = position.current_price * Decimal(position.contracts) * Decimal(100)
            pnl = position.entry_credit - current_value
        else:
            # For bought options, we profit when price goes up
            entry_cost = position.entry_price * Decimal(position.contracts) * Decimal(100)
            current_value = position.current_price * Decimal(position.contracts) * Decimal(100)
            pnl = current_value - entry_cost
        
        return pnl
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())
    
    def get_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.positions)
    
    def get_total_exposure(self) -> Decimal:
        """Get total capital at risk in open positions."""
        total = Decimal("0.00")
        for position in self.positions.values():
            if position.action == "SELL_TO_OPEN":
                # For sold options, exposure is the potential max loss
                # Simplified: current value of the option
                total += position.current_price * Decimal(position.contracts) * Decimal(100)
            else:
                # For bought options, exposure is the cost
                total += position.entry_price * Decimal(position.contracts) * Decimal(100)
        return total
    
    def add_trade(self, trade: Trade) -> bool:
        """
        Add a trade and update portfolio state.
        
        Args:
            trade: Trade object with all trade details
            
        Returns:
            bool: True if trade was successfully added
        """
        try:
            # Add to trade history
            self.trade_history.append(trade)
            
            # Update position or close it
            position_key = f"{trade.ticker}_{trade.option_symbol}"
            
            if trade.action == "SELL_TO_OPEN":
                # Opening a new position
                if position_key in self.positions:
                    logger.warning(f"Position {position_key} already exists, adding to it")
                    # Add to existing position
                    existing = self.positions[position_key]
                    total_contracts = existing.contracts + trade.contracts
                    total_credit = existing.entry_credit + trade.credit_debit
                    avg_price = total_credit / (Decimal(total_contracts) * Decimal(100))
                    
                    existing.contracts = total_contracts
                    existing.entry_credit = total_credit
                    existing.entry_price = avg_price
                else:
                    # Create new position
                    position = Position(
                        ticker=trade.ticker,
                        option_symbol=trade.option_symbol,
                        option_type=trade.option_type,
                        strike_price=trade.strike_price,
                        expiration_date=trade.expiration_date,
                        action=trade.action,
                        contracts=trade.contracts,
                        entry_price=trade.price,
                        entry_credit=trade.credit_debit,
                        current_price=trade.price
                    )
                    self.positions[position_key] = position
                
                # Update cash balance (credit received)
                self.current_balance += trade.credit_debit
                
            elif trade.action == "BUY_TO_CLOSE":
                # Closing a position
                if position_key not in self.positions:
                    logger.error(f"Cannot close position {position_key} - not found")
                    return False
                
                position = self.positions[position_key]
                
                # Calculate final P&L
                pnl = position.entry_credit - trade.credit_debit
                
                # Update cash balance (debit paid)
                self.current_balance -= trade.credit_debit
                
                # Remove position
                del self.positions[position_key]
                
                logger.info(f"Closed position {position_key} with P&L: ${pnl}")
            
            # Record balance snapshot
            self.balance_history.append({
                'timestamp': trade.trade_timestamp,
                'balance': float(self.get_account_balance()),
                'cash': float(self.current_balance),
                'open_positions': self.get_position_count(),
                'trade_id': trade.option_symbol
            })
            
            # Save to database
            self._save_to_database(trade)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            return False
    
    def update_position_prices(self, option_prices: Dict[str, Decimal]) -> None:
        """
        Update current prices for all open positions.
        
        Args:
            option_prices: Dict mapping option_symbol to current price
        """
        for position in self.positions.values():
            if position.option_symbol in option_prices:
                position.current_price = option_prices[position.option_symbol]
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary."""
        return {
            'account_balance': float(self.get_account_balance()),
            'cash_balance': float(self.current_balance),
            'initial_balance': float(self.initial_balance),
            'total_pnl': float(self.get_account_balance() - self.initial_balance),
            'open_positions': self.get_position_count(),
            'total_exposure': float(self.get_total_exposure()),
            'positions': [
                {
                    'ticker': p.ticker,
                    'option_symbol': p.option_symbol,
                    'option_type': p.option_type,
                    'strike_price': float(p.strike_price),
                    'contracts': p.contracts,
                    'entry_price': float(p.entry_price),
                    'current_price': float(p.current_price) if p.current_price else None,
                    'unrealized_pnl': float(self.calculate_position_pnl(p))
                }
                for p in self.positions.values()
            ],
            'balance_history': self.balance_history
        }
    
    def _save_to_database(self, trade: Trade) -> bool:
        """Save trade to database."""
        if not self.use_database or not self.supabase_client:
            return True  # Skip database save in test mode
            
        try:
            self.supabase_client.create_trade(trade)
            logger.info(f"Saved trade to database: {trade.option_symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving trade to database: {e}")
            return False
    
    def load_from_database(self, start_date: Optional[date] = None) -> bool:
        """Load trade history and rebuild portfolio state from database."""
        if not self.use_database or not self.supabase_client:
            logger.warning("Database not enabled, skipping load")
            return False
            
        try:
            # Query trades from database
            query = self.supabase_client.client.table('trades').select('*').order('trade_timestamp')
            
            if start_date:
                query = query.gte('trade_timestamp', start_date.isoformat())
            
            result = query.execute()
            
            # Reset portfolio state
            self.current_balance = self.initial_balance
            self.positions = {}
            self.trade_history = []
            self.balance_history = []
            
            # Replay all trades
            for trade_data in result.data:
                trade = Trade(
                    ticker=trade_data['ticker'],
                    option_symbol=trade_data['option_symbol'],
                    option_type=trade_data['option_type'],
                    strike_price=Decimal(str(trade_data['strike_price'])),
                    expiration_date=datetime.fromisoformat(trade_data['expiration_date']).date(),
                    action=trade_data['action'],
                    contracts=trade_data['contracts'],
                    price=Decimal(str(trade_data['price'])),
                    credit_debit=Decimal(str(trade_data['credit_debit'])),
                    trade_timestamp=datetime.fromisoformat(trade_data['trade_timestamp']),
                    signal_timestamp=datetime.fromisoformat(trade_data['signal_timestamp']) if trade_data.get('signal_timestamp') else None
                )
                
                # Don't save back to database when loading
                self.trade_history.append(trade)
                self._process_trade_for_position(trade)
            
            logger.info(f"Loaded {len(self.trade_history)} trades from database")
            return True
            
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return False
    
    def _process_trade_for_position(self, trade: Trade) -> None:
        """Process a trade to update positions without saving to database."""
        position_key = f"{trade.ticker}_{trade.option_symbol}"
        
        if trade.action == "SELL_TO_OPEN":
            if position_key in self.positions:
                existing = self.positions[position_key]
                total_contracts = existing.contracts + trade.contracts
                total_credit = existing.entry_credit + trade.credit_debit
                avg_price = total_credit / (Decimal(total_contracts) * Decimal(100))
                
                existing.contracts = total_contracts
                existing.entry_credit = total_credit
                existing.entry_price = avg_price
            else:
                position = Position(
                    ticker=trade.ticker,
                    option_symbol=trade.option_symbol,
                    option_type=trade.option_type,
                    strike_price=trade.strike_price,
                    expiration_date=trade.expiration_date,
                    action=trade.action,
                    contracts=trade.contracts,
                    entry_price=trade.price,
                    entry_credit=trade.credit_debit,
                    current_price=trade.price
                )
                self.positions[position_key] = position
            
            self.current_balance += trade.credit_debit
            
        elif trade.action == "BUY_TO_CLOSE":
            if position_key in self.positions:
                self.current_balance -= trade.credit_debit
                del self.positions[position_key]

# Global portfolio tracker instance
portfolio_tracker = PortfolioTracker()

if __name__ == "__main__":
    # Test the portfolio tracker
    tracker = PortfolioTracker()
    
    # Create a test trade
    test_trade = Trade(
        ticker="QQQ",
        option_symbol="QQQ251220C00600000",
        option_type="CALL",
        strike_price=Decimal("600.0"),
        expiration_date=date(2025, 12, 20),
        action="SELL_TO_OPEN",
        contracts=10,
        price=Decimal("5.50"),
        credit_debit=Decimal("5500.00"),  # 10 contracts * $5.50 * 100
        trade_timestamp=datetime.now(),
        signal_timestamp=datetime.now()
    )
    
    success = tracker.add_trade(test_trade)
    print(f"Trade added: {success}")
    
    summary = tracker.get_portfolio_summary()
    print(f"\nPortfolio Summary:")
    print(f"Account Balance: ${summary['account_balance']:,.2f}")
    print(f"Cash Balance: ${summary['cash_balance']:,.2f}")
    print(f"Open Positions: {summary['open_positions']}")
    print(f"Total P&L: ${summary['total_pnl']:,.2f}")

