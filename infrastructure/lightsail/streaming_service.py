#!/usr/bin/env python3
"""
Minimal Lightsail Streaming Service
Perpetually streams Equity and Options data to Supabase
"""

import os
import asyncio
import signal
import sys
from datetime import datetime, time as dt_time
from typing import Dict, Any
import structlog
from dotenv import load_dotenv
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from schwab_integration.client import SchwabClient
from schwab_integration.streaming import SchwabStreamingClient
from supabase_client import SupabaseClient

load_dotenv()
logger = structlog.get_logger()

class StreamingService:
    """Minimal streaming service for Lightsail deployment."""
    
    def __init__(self):
        """Initialize streaming service."""
        self.running = True
        self.schwab_client = SchwabClient()
        self.streaming_client = None
        self.supabase_client = SupabaseClient()
        
        # Configuration - Stream every second for real-time data
        self.ticker = os.getenv('STREAM_TICKER', 'QQQ')
        self.batch_size = int(os.getenv('BATCH_SIZE', '1'))  # Write every record immediately
        self.batch_interval = int(os.getenv('BATCH_INTERVAL', '1'))  # Flush every second
        
        # Buffers for batching
        self.equity_buffer = []
        self.indicator_buffer = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("streaming_service_initialized", 
                   ticker=self.ticker,
                   batch_size=self.batch_size,
                   batch_interval=self.batch_interval)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours (9:30 AM - 4:00 PM ET)."""
        now = datetime.now()
        # Simple check - adjust for your timezone/needs
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        current_time = now.time()
        
        # Check if weekday (Monday=0, Sunday=6)
        is_weekday = now.weekday() < 5
        is_market_hours = market_open <= current_time <= market_close
        
        return is_weekday and is_market_hours
    
    def _process_streaming_data(self, data: Dict[str, Any]):
        """Process incoming streaming data and add to buffers.
        
        Args:
            data: Parsed streaming data with price, volume, indicators
        """
        try:
            # Add to equity buffer
            self.equity_buffer.append({
                'ticker': data['ticker'],
                'timestamp': data['timestamp'],
                'price': data['price'],
                'volume': data['volume']
            })
            
            # Add to indicator buffer if we have indicators
            if data.get('sma9') and data.get('vwap'):
                self.indicator_buffer.append({
                    'ticker': data['ticker'],
                    'timestamp': data['timestamp'],
                    'sma9': data['sma9'],
                    'vwap': data['vwap']
                })
            
            logger.debug("data_buffered", 
                        ticker=data['ticker'],
                        equity_buffer_size=len(self.equity_buffer),
                        indicator_buffer_size=len(self.indicator_buffer))
            
            # Check if we should flush buffers
            if len(self.equity_buffer) >= self.batch_size:
                asyncio.create_task(self._flush_buffers())
                
        except Exception as e:
            logger.error("data_processing_error", error=str(e), data=data)
    
    async def _flush_buffers(self):
        """Flush buffered data to Supabase."""
        try:
            # Flush equity data
            if self.equity_buffer:
                df_equity = pd.DataFrame(self.equity_buffer)
                df_equity['timestamp'] = pd.to_datetime(df_equity['timestamp'])
                
                count = self.supabase_client.insert_equity_data(df_equity)
                logger.info("equity_data_flushed", rows=count)
                self.equity_buffer.clear()
            
            # Flush indicator data
            if self.indicator_buffer:
                df_indicators = pd.DataFrame(self.indicator_buffer)
                df_indicators['timestamp'] = pd.to_datetime(df_indicators['timestamp'])
                
                count = self.supabase_client.insert_indicators(df_indicators)
                logger.info("indicator_data_flushed", rows=count)
                self.indicator_buffer.clear()
                
        except Exception as e:
            logger.error("buffer_flush_error", error=str(e))
    
    async def _periodic_flush(self):
        """Periodically flush buffers even if not full."""
        while self.running:
            await asyncio.sleep(self.batch_interval)
            if self.equity_buffer or self.indicator_buffer:
                await self._flush_buffers()
    
    async def run(self):
        """Main run loop for streaming service."""
        logger.info("streaming_service_starting", ticker=self.ticker)
        
        try:
            # Test Supabase connection
            if not self.supabase_client.test_connection():
                logger.error("supabase_connection_failed")
                return
            
            # Initialize streaming client
            self.streaming_client = SchwabStreamingClient(self.schwab_client)
            await self.streaming_client.connect()
            
            # Start periodic flush task
            flush_task = asyncio.create_task(self._periodic_flush())
            
            # Check if market is open
            if not self._is_market_hours():
                logger.warning("market_closed", 
                             message="Starting anyway - set SKIP_MARKET_HOURS=true to skip this check")
            
            # Start streaming
            logger.info("starting_stream", ticker=self.ticker)
            await self.streaming_client.stream_level_one_quotes(
                ticker=self.ticker,
                on_message=self._process_streaming_data
            )
            
        except Exception as e:
            logger.error("streaming_service_error", error=str(e))
            raise
        finally:
            # Cleanup
            logger.info("streaming_service_shutting_down")
            
            # Flush any remaining data
            await self._flush_buffers()
            
            # Disconnect streaming client
            if self.streaming_client:
                await self.streaming_client.disconnect()
            
            logger.info("streaming_service_stopped")


async def main():
    """Main entry point."""
    service = StreamingService()
    await service.run()


if __name__ == '__main__':
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("service_interrupted")
    except Exception as e:
        logger.error("service_fatal_error", error=str(e))
        sys.exit(1)

