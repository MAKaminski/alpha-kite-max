"""
Trading Engine for SMA9/VWAP Cross Strategy

Strategy Rules:
1. SMA9 crosses VWAP downward → Sell puts (25 contracts)
2. SMA9 crosses VWAP upward + open position → Close position + Sell calls (25 contracts)
3. Close positions 30 mins before market close
4. Take profit at 50% entry credit, Stop loss at 200% entry credit
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from decimal import Decimal

from .client import SchwabClient
from .config import SchwabConfig

# Import from parent package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_client import SupabaseClient
from models.trading import Position, Trade, TradingSignal, DailyPnL

logger = logging.getLogger(__name__)

class TradingEngine:
    """Main trading engine for SMA9/VWAP cross strategy."""
    
    def __init__(self, schwab_client: SchwabClient, supabase_client: SupabaseClient):
        self.schwab_client = schwab_client
        self.supabase_client = supabase_client
        self.contract_size = 25
        self.profit_target = 0.50  # 50% of entry credit
        self.stop_loss = 2.00      # 200% of entry credit
        
    def process_cross_signal(
        self,
        ticker: str,
        signal_timestamp: str,
        current_price: float,
        sma9: float,
        vwap: float,
        direction: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a cross signal and execute appropriate trading action.
        
        Args:
            ticker: Stock ticker symbol
            signal_timestamp: When the cross occurred
            current_price: Current stock price
            sma9: SMA9 value at cross
            vwap: VWAP value at cross
            direction: 'up' or 'down'
            
        Returns:
            Dict with trade execution details or None if no action taken
        """
        logger.info(
            "processing_cross_signal",
            ticker=ticker,
            signal_timestamp=signal_timestamp,
            current_price=current_price,
            direction=direction
        )
        
        # Check if we're within trading hours (not 30 mins before close)
        if not self._is_trading_allowed(signal_timestamp):
            logger.info("trading_not_allowed", reason="outside_trading_window")
            return None
            
        # Record the signal
        signal = TradingSignal(
            ticker=ticker,
            signal_timestamp=signal_timestamp,
            signal_type=self._get_signal_type(direction),
            current_price=current_price,
            sma9_value=sma9,
            vwap_value=vwap,
            direction=direction
        )
        
        # Get current open positions
        open_positions = self._get_open_positions(ticker)
        
        if direction == 'down':
            # SMA9 crosses VWAP downward → Sell puts
            if not open_positions:
                return self._sell_puts(ticker, current_price, signal)
            else:
                logger.info("position_already_open", action="skipping_put_sell")
                return None
                
        elif direction == 'up':
            # SMA9 crosses VWAP upward → Close position + Sell calls
            if open_positions:
                close_result = self._close_positions(open_positions, signal_timestamp)
                if close_result:
                    return self._sell_calls(ticker, current_price, signal)
            else:
                return self._sell_calls(ticker, current_price, signal)
                
        return None
    
    def _is_trading_allowed(self, timestamp: str) -> bool:
        """Check if trading is allowed at this time (not 30 mins before close)."""
        dt = pd.to_datetime(timestamp)
        
        # Handle timezone-naive timestamps
        if dt.tz is None:
            est_time = dt.tz_localize('America/New_York')
        else:
            est_time = dt.tz_convert('America/New_York')
        
        # Market close is 3:00 PM EST, stop trading at 2:30 PM EST
        market_close = est_time.replace(hour=15, minute=0, second=0, microsecond=0)
        stop_trading = market_close - timedelta(minutes=30)
        
        return est_time < stop_trading
    
    def _get_signal_type(self, direction: str) -> str:
        """Get signal type based on direction."""
        if direction == 'down':
            return 'PUT_SELL'
        elif direction == 'up':
            return 'CALL_SELL'
        return 'CLOSE_POSITION'
    
    def _get_open_positions(self, ticker: str) -> List[Position]:
        """Get all open positions for a ticker."""
        return self.supabase_client.get_open_positions(ticker)
    
    def _sell_puts(self, ticker: str, current_price: float, signal: TradingSignal) -> Dict[str, Any]:
        """Sell puts at nearest strike to current price."""
        logger.info("selling_puts", ticker=ticker, current_price=current_price)
        
        # Find nearest put strike (slightly below current price)
        strike_price = self._find_nearest_put_strike(ticker, current_price)
        
        # Get option quote
        option_symbol = self._build_option_symbol(ticker, strike_price, 'PUT')
        quote = self._get_option_quote(option_symbol)
        
        if not quote:
            logger.error("no_option_quote", option_symbol=option_symbol)
            return None
            
        # Execute sell to open
        entry_price = quote.get('bid', 0)
        entry_credit = entry_price * self.contract_size * 100  # 100 shares per contract
        
        position = Position(
            ticker=ticker,
            option_symbol=option_symbol,
            option_type='PUT',
            strike_price=strike_price,
            expiration_date=self._get_next_friday(),
            action='SELL_TO_OPEN',
            contracts=self.contract_size,
            entry_price=entry_price,
            entry_credit=entry_credit,
            status='OPEN'
        )
        
        # Save position to database
        position_id = self.supabase_client.create_position(position)
        
        # Record trade
        trade = Trade(
            position_id=position_id,
            ticker=ticker,
            option_symbol=option_symbol,
            option_type='PUT',
            strike_price=strike_price,
            expiration_date=position.expiration_date,
            action='SELL_TO_OPEN',
            contracts=self.contract_size,
            price=entry_price,
            credit_debit=entry_credit,
            trade_timestamp=signal.signal_timestamp,
            signal_timestamp=signal.signal_timestamp
        )
        
        self.supabase_client.create_trade(trade)
        
        return {
            'action': 'PUT_SELL',
            'position_id': position_id,
            'strike_price': strike_price,
            'entry_price': entry_price,
            'entry_credit': entry_credit,
            'contracts': self.contract_size
        }
    
    def _sell_calls(self, ticker: str, current_price: float, signal: TradingSignal) -> Dict[str, Any]:
        """Sell calls at nearest strike to current price."""
        logger.info("selling_calls", ticker=ticker, current_price=current_price)
        
        # Find nearest call strike (slightly above current price)
        strike_price = self._find_nearest_call_strike(ticker, current_price)
        
        # Get option quote
        option_symbol = self._build_option_symbol(ticker, strike_price, 'CALL')
        quote = self._get_option_quote(option_symbol)
        
        if not quote:
            logger.error("no_option_quote", option_symbol=option_symbol)
            return None
            
        # Execute sell to open
        entry_price = quote.get('bid', 0)
        entry_credit = entry_price * self.contract_size * 100
        
        position = Position(
            ticker=ticker,
            option_symbol=option_symbol,
            option_type='CALL',
            strike_price=strike_price,
            expiration_date=self._get_next_friday(),
            action='SELL_TO_OPEN',
            contracts=self.contract_size,
            entry_price=entry_price,
            entry_credit=entry_credit,
            status='OPEN'
        )
        
        # Save position to database
        position_id = self.supabase_client.create_position(position)
        
        # Record trade
        trade = Trade(
            position_id=position_id,
            ticker=ticker,
            option_symbol=option_symbol,
            option_type='CALL',
            strike_price=strike_price,
            expiration_date=position.expiration_date,
            action='SELL_TO_OPEN',
            contracts=self.contract_size,
            price=entry_price,
            credit_debit=entry_credit,
            trade_timestamp=signal.signal_timestamp,
            signal_timestamp=signal.signal_timestamp
        )
        
        self.supabase_client.create_trade(trade)
        
        return {
            'action': 'CALL_SELL',
            'position_id': position_id,
            'strike_price': strike_price,
            'entry_price': entry_price,
            'entry_credit': entry_credit,
            'contracts': self.contract_size
        }
    
    def _close_positions(self, positions: List[Position], close_timestamp: str) -> bool:
        """Close all open positions."""
        logger.info("closing_positions", count=len(positions))
        
        for position in positions:
            # Get current option quote
            quote = self._get_option_quote(position.option_symbol)
            if not quote:
                logger.error("no_close_quote", option_symbol=position.option_symbol)
                continue
                
            # Execute buy to close
            exit_price = quote.get('ask', 0)
            exit_debit = exit_price * position.contracts * 100
            
            # Calculate P&L
            pnl = position.entry_credit - exit_debit
            
            # Update position
            position.status = 'CLOSED'
            position.current_price = exit_price
            position.unrealized_pnl = pnl
            position.closed_at = close_timestamp
            
            self.supabase_client.update_position(position)
            
            # Record closing trade
            close_trade = Trade(
                position_id=position.id,
                ticker=position.ticker,
                option_symbol=position.option_symbol,
                option_type=position.option_type,
                strike_price=position.strike_price,
                expiration_date=position.expiration_date,
                action='BUY_TO_CLOSE',
                contracts=position.contracts,
                price=exit_price,
                credit_debit=-exit_debit,  # Negative for debit
                trade_timestamp=close_timestamp,
                signal_timestamp=close_timestamp
            )
            
            self.supabase_client.create_trade(close_trade)
            
        return True
    
    def get_0dte_option_chain(self, ticker: str, current_price: float) -> Dict[str, Any]:
        """Get 0DTE option chain for nearest strikes."""
        try:
            # Get option chains for today's expiration (0DTE)
            option_chains = self.schwab_client.get_option_chains(ticker, "ALL")
            
            if not option_chains:
                logger.warning("no_option_chains", ticker=ticker)
                return {}
            
            # Find today's expiration date
            today = datetime.now().date()
            today_str = today.strftime("%Y-%m-%d")
            
            # Look for today's expiration in the option chains
            today_options = {}
            for exp_date_str, expiration_data in option_chains.items():
                if today_str in exp_date_str:
                    today_options = expiration_data
                    break
            
            if not today_options:
                logger.warning("no_0dte_options", ticker=ticker, date=today_str)
                return {}
            
            # Find nearest strikes to current price
            put_strikes = today_options.get('PUT', {})
            call_strikes = today_options.get('CALL', {})
            
            # Find nearest put strike (below current price)
            put_strike = None
            put_price = None
            for strike_str in sorted(put_strikes.keys(), key=float, reverse=True):
                strike_price = float(strike_str)
                if strike_price < current_price:
                    contracts = put_strikes[strike_str]
                    if contracts:
                        put_strike = strike_price
                        put_price = contracts[0].get('mark', 0)
                        break
            
            # Find nearest call strike (above current price)
            call_strike = None
            call_price = None
            for strike_str in sorted(call_strikes.keys(), key=float):
                strike_price = float(strike_str)
                if strike_price > current_price:
                    contracts = call_strikes[strike_str]
                    if contracts:
                        call_strike = strike_price
                        call_price = contracts[0].get('mark', 0)
                        break
            
            return {
                'put_strike': put_strike,
                'put_price': put_price,
                'call_strike': call_strike,
                'call_price': call_price,
                'current_price': current_price,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("0dte_option_chain_failed", error=str(e))
            return {}
    
    def _find_nearest_put_strike(self, ticker: str, current_price: float) -> Optional[float]:
        """Find nearest put strike below current price with good liquidity."""
        try:
            # Get option chains for puts
            option_chains = self.schwab_client.get_option_chains(ticker, "PUT")
            
            if not option_chains or 'putExpDateMap' not in option_chains:
                # Fallback to simple calculation
                return float(int(current_price) - 1)
            
            # Find puts with strikes below current price and good liquidity
            best_strike = None
            best_liquidity = 0
            
            for exp_date, strikes in option_chains.items():
                for strike, contracts in strikes.items():
                    strike_price = float(strike)
                    if strike_price < current_price:
                        # Check liquidity (volume + open interest)
                        total_liquidity = 0
                        for contract in contracts:
                            total_liquidity += contract.get('totalVolume', 0) + contract.get('openInterest', 0)
                        
                        if total_liquidity > best_liquidity:
                            best_liquidity = total_liquidity
                            best_strike = strike_price
            
            return best_strike if best_strike else float(int(current_price) - 1)
            
        except Exception as e:
            logger.error("put_strike_search_failed", error=str(e))
            return float(int(current_price) - 1)
    
    def _find_nearest_call_strike(self, ticker: str, current_price: float) -> Optional[float]:
        """Find nearest call strike above current price with good liquidity."""
        try:
            # Get option chains for calls
            option_chains = self.schwab_client.get_option_chains(ticker, "CALL")
            
            if not option_chains or 'callExpDateMap' not in option_chains:
                # Fallback to simple calculation
                return float(int(current_price) + 1)
            
            # Find calls with strikes above current price and good liquidity
            best_strike = None
            best_liquidity = 0
            
            for exp_date, strikes in option_chains.items():
                for strike, contracts in strikes.items():
                    strike_price = float(strike)
                    if strike_price > current_price:
                        # Check liquidity (volume + open interest)
                        total_liquidity = 0
                        for contract in contracts:
                            total_liquidity += contract.get('totalVolume', 0) + contract.get('openInterest', 0)
                        
                        if total_liquidity > best_liquidity:
                            best_liquidity = total_liquidity
                            best_strike = strike_price
            
            return best_strike if best_strike else float(int(current_price) + 1)
            
        except Exception as e:
            logger.error("call_strike_search_failed", error=str(e))
            return float(int(current_price) + 1)
    
    def _build_option_symbol(self, ticker: str, strike: float, option_type: str) -> str:
        """Build option symbol for Schwab API."""
        # Format: TICKER + YYMMDD + P/C + StrikePrice
        exp_date = self._get_next_friday()
        exp_str = exp_date.strftime("%y%m%d")
        strike_str = f"{strike:08.0f}"  # 8 digits, zero-padded
        option_letter = 'P' if option_type == 'PUT' else 'C'
        
        return f"{ticker}{exp_str}{option_letter}{strike_str}"
    
    def _get_next_friday(self) -> datetime:
        """Get next Friday expiration date."""
        today = datetime.now()
        days_ahead = 4 - today.weekday()  # Friday is weekday 4
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _get_option_quote(self, option_symbol: str) -> Optional[Dict[str, float]]:
        """Get option quote from Schwab API."""
        try:
            quote_data = self.schwab_client.get_option_quote(option_symbol)
            
            # Extract quote information from Schwab response
            if quote_data and 'quotes' in quote_data:
                quote = quote_data['quotes'][0] if quote_data['quotes'] else None
                if quote:
                    return {
                        'bid': float(quote.get('bid', 0)),
                        'ask': float(quote.get('ask', 0)),
                        'last': float(quote.get('last', 0)),
                        'volume': int(quote.get('totalVolume', 0)),
                        'openInterest': int(quote.get('openInterest', 0))
                    }
            
            logger.warning("no_quote_data", option_symbol=option_symbol)
            return None
            
        except Exception as e:
            logger.error("option_quote_error", error=str(e), option_symbol=option_symbol)
            return None
    
    def check_profit_loss_targets(self, ticker: str) -> List[Dict[str, Any]]:
        """Check if any positions should be closed due to profit/loss targets."""
        open_positions = self._get_open_positions(ticker)
        closed_positions = []
        
        for position in open_positions:
            # Get current quote
            quote = self._get_option_quote(position.option_symbol)
            if not quote:
                continue
                
            current_price = quote.get('last', 0)
            current_value = current_price * position.contracts * 100
            
            # Calculate current P&L
            current_pnl = position.entry_credit - current_value
            pnl_percentage = current_pnl / position.entry_credit
            
            # Check profit target (50%)
            if pnl_percentage >= self.profit_target:
                logger.info("profit_target_hit", position_id=position.id, pnl_percentage=pnl_percentage)
                self._close_positions([position], datetime.now().isoformat())
                closed_positions.append({'position_id': position.id, 'reason': 'profit_target'})
                
            # Check stop loss (200%)
            elif pnl_percentage <= -self.stop_loss:
                logger.info("stop_loss_hit", position_id=position.id, pnl_percentage=pnl_percentage)
                self._close_positions([position], datetime.now().isoformat())
                closed_positions.append({'position_id': position.id, 'reason': 'stop_loss'})
                
        return closed_positions
