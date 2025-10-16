"""Schwab WebSocket streaming client for real-time equity data."""

import asyncio
import json
from typing import Callable, Optional, Dict, Any
from datetime import datetime
import structlog

from schwab import client
from .config import SchwabConfig
from .client import SchwabClient

logger = structlog.get_logger()


class SchwabStreamingClient:
    """Real-time streaming via Schwab WebSocket API."""
    
    def __init__(self, schwab_client: SchwabClient):
        """Initialize streaming client.
        
        Args:
            schwab_client: Authenticated Schwab client instance
        """
        self.schwab_client = schwab_client
        self.streaming_client = None
        self.running_totals = {}  # For VWAP calculation
        self.price_buffer = {}    # For SMA9 calculation
        logger.info("streaming_client_initialized")
    
    async def connect(self):
        """Establish WebSocket connection to Schwab streaming API."""
        try:
            # Get authenticated client
            auth_client = self.schwab_client.authenticate()
            
            # Get streaming client
            self.streaming_client = auth_client.stream_client()
            
            await self.streaming_client.login()
            logger.info("streaming_connection_established")
            
        except Exception as e:
            logger.error("streaming_connection_failed", error=str(e))
            raise
    
    async def stream_level_one_quotes(
        self, 
        ticker: str,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """Stream real-time Level 1 quotes (price, volume).
        
        Args:
            ticker: Stock ticker symbol to stream
            on_message: Callback function to process each message
        """
        if not self.streaming_client:
            await self.connect()
        
        logger.info("starting_level_one_stream", ticker=ticker)
        
        try:
            # Subscribe to Level One Equities service
            await self.streaming_client.level_one_equity_subs([ticker])
            
            # Process incoming messages
            async for message in self.streaming_client.stream():
                try:
                    parsed_data = self._parse_level_one_message(message, ticker)
                    
                    if parsed_data and on_message:
                        on_message(parsed_data)
                        
                except Exception as e:
                    logger.error("message_processing_error", error=str(e), message=message)
                    continue
                    
        except Exception as e:
            logger.error("streaming_error", error=str(e), ticker=ticker)
            raise
    
    def _parse_level_one_message(self, message: Dict[str, Any], ticker: str) -> Optional[Dict[str, Any]]:
        """Parse Level 1 equity message.
        
        Args:
            message: Raw message from streaming API
            ticker: Stock ticker being streamed
            
        Returns:
            Parsed data with price, volume, timestamp, and calculated indicators
        """
        try:
            # Extract relevant fields from message
            # Schwab Level 1 format: service, timestamp, command, content
            if message.get('service') != 'LEVELONE_EQUITIES':
                return None
            
            content = message.get('content', [])
            if not content:
                return None
            
            # Find data for our ticker
            ticker_data = None
            for item in content:
                if item.get('key') == ticker:
                    ticker_data = item
                    break
            
            if not ticker_data:
                return None
            
            # Extract price and volume
            last_price = ticker_data.get('LAST_PRICE')
            last_size = ticker_data.get('LAST_SIZE')
            quote_time = ticker_data.get('QUOTE_TIME')
            
            if last_price is None:
                return None
            
            # Calculate indicators
            sma9 = self._calculate_sma9(ticker, last_price)
            vwap = self._calculate_vwap(ticker, last_price, last_size or 0)
            
            return {
                'ticker': ticker,
                'timestamp': datetime.fromtimestamp(quote_time / 1000).isoformat() if quote_time else datetime.now().isoformat(),
                'price': float(last_price),
                'volume': int(last_size) if last_size else 0,
                'sma9': sma9,
                'vwap': vwap
            }
            
        except Exception as e:
            logger.error("parse_error", error=str(e), message=message)
            return None
    
    def _calculate_sma9(self, ticker: str, price: float) -> float:
        """Calculate 9-period Simple Moving Average.
        
        Args:
            ticker: Stock ticker
            price: Current price
            
        Returns:
            SMA9 value
        """
        if ticker not in self.price_buffer:
            self.price_buffer[ticker] = []
        
        # Add current price
        self.price_buffer[ticker].append(price)
        
        # Keep only last 9 prices
        if len(self.price_buffer[ticker]) > 9:
            self.price_buffer[ticker].pop(0)
        
        # Calculate average
        return sum(self.price_buffer[ticker]) / len(self.price_buffer[ticker])
    
    def _calculate_vwap(self, ticker: str, price: float, volume: int) -> float:
        """Calculate Volume Weighted Average Price.
        
        Args:
            ticker: Stock ticker
            price: Current price
            volume: Current volume
            
        Returns:
            VWAP value
        """
        if ticker not in self.running_totals:
            self.running_totals[ticker] = {
                'cumulative_pv': 0.0,
                'cumulative_volume': 0
            }
        
        # Update running totals
        self.running_totals[ticker]['cumulative_pv'] += price * volume
        self.running_totals[ticker]['cumulative_volume'] += volume
        
        # Calculate VWAP
        if self.running_totals[ticker]['cumulative_volume'] > 0:
            return self.running_totals[ticker]['cumulative_pv'] / self.running_totals[ticker]['cumulative_volume']
        else:
            return price
    
    def reset_session_indicators(self, ticker: str):
        """Reset indicators at start of new trading session.
        
        Args:
            ticker: Stock ticker to reset
        """
        if ticker in self.running_totals:
            self.running_totals[ticker] = {
                'cumulative_pv': 0.0,
                'cumulative_volume': 0
            }
        
        if ticker in self.price_buffer:
            self.price_buffer[ticker] = []
        
        logger.info("session_indicators_reset", ticker=ticker)
    
    async def disconnect(self):
        """Close WebSocket connection."""
        if self.streaming_client:
            try:
                await self.streaming_client.logout()
                logger.info("streaming_connection_closed")
            except Exception as e:
                logger.error("disconnect_error", error=str(e))

