"""Tests for Schwab equity downloader."""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch

from schwab_integration.downloader import EquityDownloader
from schwab_integration.client import SchwabClient


@pytest.fixture
def mock_schwab_client():
    """Mock Schwab client."""
    client = Mock(spec=SchwabClient)
    return client


@pytest.fixture
def sample_schwab_response():
    """Sample Schwab API response."""
    return {
        "candles": [
            {
                "datetime": 1697558400000,  # milliseconds
                "open": 450.00,
                "high": 451.00,
                "low": 449.50,
                "close": 450.25,
                "volume": 1000000
            },
            {
                "datetime": 1697558460000,
                "open": 450.25,
                "high": 451.25,
                "low": 450.00,
                "close": 450.50,
                "volume": 1500000
            }
        ]
    }


class TestEquityDownloader:
    """Test equity downloader."""
    
    def test_initialization(self, mock_schwab_client):
        """Test downloader initialization."""
        downloader = EquityDownloader(mock_schwab_client)
        assert downloader.client == mock_schwab_client
    
    def test_download_minute_data(self, mock_schwab_client, sample_schwab_response):
        """Test downloading minute data."""
        mock_schwab_client.get_price_history.return_value = sample_schwab_response
        
        downloader = EquityDownloader(mock_schwab_client)
        df = downloader.download_minute_data("QQQ", days=5)
        
        assert len(df) == 2
        assert list(df.columns) == ["ticker", "timestamp", "price", "volume"]
        assert df.iloc[0]["ticker"] == "QQQ"
        assert df.iloc[0]["price"] == 450.25
        assert df.iloc[0]["volume"] == 1000000
    
    def test_transform_to_dataframe(self, mock_schwab_client, sample_schwab_response):
        """Test transformation of Schwab data to DataFrame."""
        downloader = EquityDownloader(mock_schwab_client)
        df = downloader._transform_to_dataframe("QQQ", sample_schwab_response)
        
        assert len(df) == 2
        assert all(df["ticker"] == "QQQ")
        assert df["timestamp"].is_monotonic_increasing
    
    def test_calculate_indicators(self, mock_schwab_client):
        """Test indicator calculation."""
        # Create sample equity data
        equity_df = pd.DataFrame({
            "ticker": ["QQQ"] * 10,
            "timestamp": pd.date_range(start="2024-01-01", periods=10, freq="min"),
            "price": [450.0, 450.5, 451.0, 450.8, 451.2, 451.5, 451.8, 452.0, 452.2, 452.5],
            "volume": [1000000] * 10
        })
        
        downloader = EquityDownloader(mock_schwab_client)
        indicators_df = downloader.calculate_indicators(equity_df)
        
        assert len(indicators_df) == 10
        assert list(indicators_df.columns) == ["ticker", "timestamp", "sma9", "vwap"]
        assert indicators_df["sma9"].notna().all()
        assert indicators_df["vwap"].notna().all()
    
    def test_calculate_indicators_empty(self, mock_schwab_client):
        """Test indicator calculation with empty DataFrame."""
        downloader = EquityDownloader(mock_schwab_client)
        empty_df = pd.DataFrame()
        
        result = downloader.calculate_indicators(empty_df)
        
        assert result.empty
        assert list(result.columns) == ["ticker", "timestamp", "sma9", "vwap"]

