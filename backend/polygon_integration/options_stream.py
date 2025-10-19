"""
Polygon.io Real-Time Options Streaming

⚠️ REQUIRES PAID TIER - Not available on free tier

Streams real-time options data via Polygon.io WebSocket.
Requires:
- Polygon.io paid subscription (Starter tier or higher)
- websocket-client package: pip install websocket-client

Free tier limitations:
- ❌ No WebSocket streaming
- ❌ No real-time options quotes
- ✅ Historical data via REST API only
"""

import os
import json
from typing import Callable, Dict, Any, Optional
import websocket
import structlog
from dotenv import load_dotenv
import threading

load_dotenv()
logger = structlog.get_logger()


class PolygonOptionsStream:
    """Real-time options data streaming via Polygon.io WebSocket."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Polygon WebSocket client.
        
        Args:
            api_key: Polygon.io API key. If None, reads from POLYGON_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not found in environment variables")
        
        self.ws_url = f"wss://socket.polygon.io/options"
        self.ws: Optional[websocket.WebSocketApp] = None
        self.callbacks: Dict[str, Callable] = {}
        self.is_connected = False
        self.thread: Optional[threading.Thread] = None
        
        logger.info("polygon_options_stream_initialized")
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Handle different message types
            for item in data:
                event_type = item.get("ev")
                
                if event_type == "status":
                    # Connection status message
                    status = item.get("status")
                    msg = item.get("message", "")
                    logger.info("polygon_ws_status", status=status, message=msg)
                    
                elif event_type == "T":
                    # Trade message
                    if "trade" in self.callbacks:
                        self.callbacks["trade"](item)
                    
                elif event_type == "Q":
                    # Quote message
                    if "quote" in self.callbacks:
                        self.callbacks["quote"](item)
                    
                elif event_type == "A":
                    # Aggregate (bar) message
                    if "aggregate" in self.callbacks:
                        self.callbacks["aggregate"](item)
                
        except json.JSONDecodeError as e:
            logger.error("polygon_ws_json_decode_error", error=str(e), message=message[:100])
        except Exception as e:
            logger.error("polygon_ws_message_error", error=str(e))
    
    def on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error("polygon_ws_error", error=str(error))
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        self.is_connected = False
        logger.info("polygon_ws_closed", code=close_status_code, message=close_msg)
    
    def on_open(self, ws):
        """Handle WebSocket open - authenticate and subscribe."""
        self.is_connected = True
        logger.info("polygon_ws_connected")
        
        # Send authentication
        auth_message = {"action": "auth", "params": self.api_key}
        ws.send(json.dumps(auth_message))
    
    def connect(self):
        """Establish WebSocket connection."""
        if self.is_connected:
            logger.warning("polygon_ws_already_connected")
            return
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run WebSocket in separate thread
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("polygon_ws_connection_initiated")
    
    def disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            self.ws.close()
            self.is_connected = False
            logger.info("polygon_ws_disconnected")
    
    def subscribe_option(self, option_symbol: str, stream_type: str = "T"):
        """
        Subscribe to real-time data for an option contract.
        
        Args:
            option_symbol: Full option symbol (e.g., "O:QQQ251024C00600000")
            stream_type: "T" for trades, "Q" for quotes, "A" for aggregates
        """
        if not self.is_connected:
            logger.error("polygon_ws_not_connected")
            return
        
        subscribe_message = {
            "action": "subscribe",
            "params": f"{stream_type}.{option_symbol}"
        }
        
        self.ws.send(json.dumps(subscribe_message))
        logger.info("polygon_option_subscribed", symbol=option_symbol, type=stream_type)
    
    def unsubscribe_option(self, option_symbol: str, stream_type: str = "T"):
        """
        Unsubscribe from an option contract.
        
        Args:
            option_symbol: Full option symbol
            stream_type: "T" for trades, "Q" for quotes, "A" for aggregates
        """
        if not self.is_connected:
            return
        
        unsubscribe_message = {
            "action": "unsubscribe",
            "params": f"{stream_type}.{option_symbol}"
        }
        
        self.ws.send(json.dumps(unsubscribe_message))
        logger.info("polygon_option_unsubscribed", symbol=option_symbol, type=stream_type)
    
    def on_trade(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for trade messages."""
        self.callbacks["trade"] = callback
    
    def on_quote(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for quote messages."""
        self.callbacks["quote"] = callback
    
    def on_aggregate(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for aggregate messages."""
        self.callbacks["aggregate"] = callback


# Example Usage
if __name__ == "__main__":
    import time
    
    def handle_trade(data):
        print(f"Trade: {data.get('sym')} @ ${data.get('p')} x {data.get('s')}")
    
    def handle_quote(data):
        print(f"Quote: {data.get('sym')} Bid: ${data.get('bp')} Ask: ${data.get('ap')}")
    
    stream = PolygonOptionsStream()
    stream.on_trade(handle_trade)
    stream.on_quote(handle_quote)
    
    stream.connect()
    time.sleep(2)  # Wait for connection
    
    # Subscribe to QQQ option (example)
    stream.subscribe_option("O:QQQ251024C00600000", "T")
    stream.subscribe_option("O:QQQ251024C00600000", "Q")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        stream.disconnect()

