"""
Polygon.io API Integration

This module provides integration with Polygon.io API for:
- Historical options data (REST API) ✅ FREE TIER
- Real-time options streaming (WebSocket) ⚠️ REQUIRES PAID TIER

Note: Real-time streaming requires Polygon.io paid subscription.
      Free tier only supports historical data via REST API.
"""

from .historic_options import PolygonHistoricOptions

# Real-time streaming requires paid tier and websocket-client package
# from .options_stream import PolygonOptionsStream

__all__ = ['PolygonHistoricOptions']

