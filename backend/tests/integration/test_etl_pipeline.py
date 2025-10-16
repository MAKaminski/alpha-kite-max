"""Integration tests for ETL pipeline."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

from etl_pipeline import ETLPipeline


@pytest.fixture
def mock_schwab_data():
    """Mock Schwab API response data."""
    return {
        "candles": [
            {
                "datetime": 1697558400000,
                "open": 450.00,
                "high": 451.00,
                "low": 449.50,
                "close": 450.25,
                "volume": 1000000
            }
        ]
    }


class TestETLPipeline:
    """Integration tests for ETL pipeline."""
    
    @patch("etl_pipeline.SupabaseClient")
    @patch("etl_pipeline.SchwabClient")
    def test_full_pipeline_run(self, mock_schwab_cls, mock_supabase_cls, mock_schwab_data):
        """Test complete ETL pipeline execution."""
        # Setup Schwab mock
        mock_schwab_instance = Mock()
        mock_schwab_instance.get_price_history.return_value = mock_schwab_data
        mock_schwab_cls.return_value = mock_schwab_instance
        
        # Setup Supabase mock
        mock_supabase_instance = Mock()
        mock_supabase_instance.insert_equity_data.return_value = 1
        mock_supabase_instance.insert_indicators.return_value = 1
        mock_supabase_cls.return_value = mock_supabase_instance
        
        # Run pipeline
        pipeline = ETLPipeline()
        result = pipeline.run(ticker="QQQ", days=1)
        
        assert result["success"] is True
        assert result["ticker"] == "QQQ"
        assert result["equity_rows"] == 1
        assert result["indicator_rows"] == 1
        mock_supabase_instance.insert_equity_data.assert_called_once()
        mock_supabase_instance.insert_indicators.assert_called_once()
    
    @patch("etl_pipeline.SupabaseClient")
    @patch("etl_pipeline.SchwabClient")
    def test_pipeline_with_no_data(self, mock_schwab_cls, mock_supabase_cls):
        """Test pipeline when no data is downloaded."""
        # Setup Schwab mock to return empty candles
        mock_schwab_instance = Mock()
        mock_schwab_instance.get_price_history.return_value = {"candles": []}
        mock_schwab_cls.return_value = mock_schwab_instance
        
        mock_supabase_instance = Mock()
        mock_supabase_cls.return_value = mock_supabase_instance
        
        # Run pipeline
        pipeline = ETLPipeline()
        result = pipeline.run(ticker="QQQ", days=1)
        
        assert result["success"] is False
        assert result["equity_rows"] == 0
        assert "No data downloaded" in result["message"]
    
    @patch("etl_pipeline.SupabaseClient")
    @patch("etl_pipeline.SchwabClient")
    def test_connection_tests(self, mock_schwab_cls, mock_supabase_cls):
        """Test connection testing functionality."""
        # Setup mocks
        mock_schwab_instance = Mock()
        mock_schwab_instance.authenticate.return_value = Mock()
        mock_schwab_cls.return_value = mock_schwab_instance
        
        mock_supabase_instance = Mock()
        mock_supabase_instance.test_connection.return_value = True
        mock_supabase_cls.return_value = mock_supabase_instance
        
        # Test connections
        pipeline = ETLPipeline()
        results = pipeline.test_connections()
        
        assert results["schwab"] is True
        assert results["supabase"] is True

