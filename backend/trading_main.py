#!/usr/bin/env python3
"""
Main trading script for SMA9/VWAP cross strategy.

This script:
1. Monitors for SMA9/VWAP crosses
2. Executes trading signals
3. Manages positions and P&L
4. Runs continuously during market hours
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from schwab_integration.client import SchwabClient
from schwab_integration.downloader import DataDownloader
from schwab_integration.trading_engine import TradingEngine
from schwab_integration.config import SchwabConfig, SupabaseConfig, AppConfig
from supabase_client import SupabaseClient
from models.trading import DailyPnL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot for SMA9/VWAP strategy."""
    
    def __init__(self):
        # Load configurations
        self.schwab_config = SchwabConfig()
        self.supabase_config = SupabaseConfig()
        self.app_config = AppConfig()
        
        # Initialize clients
        self.schwab_client = SchwabClient(self.schwab_config)
        self.supabase_client = SupabaseClient(self.supabase_config)
        self.data_downloader = DataDownloader(self.schwab_client, self.supabase_client)
        self.trading_engine = TradingEngine(self.schwab_client, self.supabase_client)
        
        self.ticker = self.app_config.default_ticker
        self.running = False
        
    async def start(self):
        """Start the trading bot."""
        logger.info("starting_trading_bot", ticker=self.ticker)
        self.running = True
        
        try:
            # Test connections
            await self._test_connections()
            
            # Start main trading loop
            await self._trading_loop()
            
        except KeyboardInterrupt:
            logger.info("trading_bot_stopped_by_user")
        except Exception as e:
            logger.error("trading_bot_error", error=str(e))
        finally:
            self.running = False
    
    async def _test_connections(self):
        """Test all connections before starting."""
        logger.info("testing_connections")
        
        # Test Schwab connection
        if not self.schwab_client.test_connection():
            raise Exception("Schwab API connection failed")
        
        # Test Supabase connection
        if not self.supabase_client.test_connection():
            raise Exception("Supabase connection failed")
        
        logger.info("all_connections_successful")
    
    async def _trading_loop(self):
        """Main trading loop - runs every minute during market hours."""
        logger.info("starting_trading_loop")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if we're in market hours
                if self._is_market_hours(current_time):
                    await self._process_trading_minute(current_time)
                else:
                    logger.debug("outside_market_hours", time=current_time)
                
                # Wait 60 seconds before next iteration
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error("trading_loop_error", error=str(e))
                await asyncio.sleep(30)  # Wait 30 seconds on error
    
    async def _process_trading_minute(self, timestamp: datetime):
        """Process one trading minute."""
        logger.debug("processing_trading_minute", timestamp=timestamp)
        
        try:
            # Download latest data
            await self._update_market_data()
            
            # Check for cross signals
            await self._check_cross_signals(timestamp)
            
            # Check profit/loss targets
            await self._check_profit_loss_targets()
            
            # Update daily P&L
            await self._update_daily_pnl(timestamp.date())
            
        except Exception as e:
            logger.error("trading_minute_error", error=str(e), timestamp=timestamp)
    
    async def _update_market_data(self):
        """Update market data for the ticker."""
        try:
            # Download latest minute data
            df = self.data_downloader.download_minute_data(self.ticker, days=1)
            
            if not df.empty:
                # Calculate indicators
                indicators_df = self.data_downloader.calculate_indicators(df)
                
                # Save to Supabase
                self.data_downloader.save_to_supabase(df, indicators_df)
                
                logger.debug("market_data_updated", rows=len(df))
            
        except Exception as e:
            logger.error("market_data_update_failed", error=str(e))
    
    async def _check_cross_signals(self, timestamp: datetime):
        """Check for SMA9/VWAP cross signals."""
        try:
            # Get latest data
            equity_data = self.supabase_client.get_equity_data(self.ticker, limit=10)
            indicators_data = self.supabase_client.get_indicators(self.ticker, limit=10)
            
            if equity_data.empty or indicators_data.empty:
                return
            
            # Merge data
            merged_data = equity_data.merge(
                indicators_data, 
                on=['ticker', 'timestamp'], 
                how='inner'
            )
            
            if len(merged_data) < 2:
                return
            
            # Check for crosses (compare last 2 points)
            prev_point = merged_data.iloc[-2]
            curr_point = merged_data.iloc[-1]
            
            # Check if SMA9 crossed VWAP
            prev_diff = prev_point['sma9'] - prev_point['vwap']
            curr_diff = curr_point['sma9'] - curr_point['vwap']
            
            if prev_diff * curr_diff < 0:  # Cross occurred
                direction = 'up' if curr_diff > 0 else 'down'
                
                logger.info(
                    "cross_signal_detected",
                    direction=direction,
                    timestamp=curr_point['timestamp'],
                    price=curr_point['price'],
                    sma9=curr_point['sma9'],
                    vwap=curr_point['vwap']
                )
                
                # Process the signal
                result = self.trading_engine.process_cross_signal(
                    ticker=self.ticker,
                    signal_timestamp=curr_point['timestamp'].isoformat(),
                    current_price=curr_point['price'],
                    sma9=curr_point['sma9'],
                    vwap=curr_point['vwap'],
                    direction=direction
                )
                
                if result:
                    logger.info("trade_executed", result=result)
        
        except Exception as e:
            logger.error("cross_signal_check_failed", error=str(e))
    
    async def _check_profit_loss_targets(self):
        """Check if any positions should be closed due to profit/loss targets."""
        try:
            closed_positions = self.trading_engine.check_profit_loss_targets(self.ticker)
            
            if closed_positions:
                logger.info("positions_closed_for_targets", count=len(closed_positions))
                
        except Exception as e:
            logger.error("profit_loss_check_failed", error=str(e))
    
    async def _update_daily_pnl(self, trade_date):
        """Update daily P&L summary."""
        try:
            # Get daily summary
            summary = self.supabase_client.get_trading_summary(self.ticker, trade_date)
            
            if summary:
                # Calculate daily metrics
                total_trades = len(summary.get('recent_trades', []))
                open_positions = summary.get('open_positions', [])
                total_unrealized_pnl = summary.get('total_unrealized_pnl', 0)
                
                # Create or update daily P&L
                daily_pnl = DailyPnL(
                    ticker=self.ticker,
                    trade_date=trade_date,
                    total_trades=total_trades,
                    total_unrealized_pnl=total_unrealized_pnl,
                    total_credits_received=0  # Calculate from trades
                )
                
                self.supabase_client.update_daily_pnl(daily_pnl)
                
                logger.debug("daily_pnl_updated", date=trade_date, pnl=total_unrealized_pnl)
        
        except Exception as e:
            logger.error("daily_pnl_update_failed", error=str(e))
    
    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is within market hours."""
        # Simple check - can be enhanced with holiday calendar
        if timestamp.weekday() >= 5:  # Weekend
            return False
        
        # Market hours: 10:00 AM - 3:00 PM EST
        est_time = timestamp.replace(tzinfo=None)  # Assume local time is EST for now
        market_open = est_time.replace(hour=10, minute=0, second=0, microsecond=0)
        market_close = est_time.replace(hour=15, minute=0, second=0, microsecond=0)
        
        return market_open <= est_time < market_close

async def main():
    """Main entry point."""
    bot = TradingBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
