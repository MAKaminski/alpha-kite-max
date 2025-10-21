"""Tests for Supabase client."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from clients.supabase_client import SupabaseClient
from schwab_integration.config import SupabaseConfig


@pytest.fixture
def mock_config():
    """Mock Supabase configuration."""
    return SupabaseConfig(
        url="https://test.supabase.co",
        service_role_key="test-key"
    )


@pytest.fixture
def sample_equity_df():
    """Sample equity data DataFrame."""
    return pd.DataFrame({
        "ticker": ["QQQ", "QQQ"],
        "timestamp": [
            datetime.now() - timedelta(minutes=2),
            datetime.now() - timedelta(minutes=1)
        ],
        "price": [450.25, 450.50],
        "volume": [1000000, 1500000]
    })


@pytest.fixture
def sample_indicators_df():
    """Sample indicators DataFrame."""
    return pd.DataFrame({
        "ticker": ["QQQ", "QQQ"],
        "timestamp": [
            datetime.now() - timedelta(minutes=2),
            datetime.now() - timedelta(minutes=1)
        ],
        "sma9": [449.80, 450.10],
        "vwap": [450.00, 450.20]
    })


class TestSupabaseClient:
    """Test Supabase client operations."""
    
    @patch("supabase_client.create_client")
    def test_initialization(self, mock_create_client, mock_config):
        """Test client initialization."""
        client = SupabaseClient(mock_config)
        
        assert client.config == mock_config
        mock_create_client.assert_called_once_with(
            mock_config.url,
            mock_config.service_role_key
        )
    
    @patch("supabase_client.create_client")
    def test_insert_equity_data(self, mock_create_client, mock_config, sample_equity_df):
        """Test inserting equity data."""
        # Setup mock
        mock_table = Mock()
        mock_table.upsert.return_value.execute.return_value.data = [{"id": 1}, {"id": 2}]
        mock_create_client.return_value.table.return_value = mock_table
        
        client = SupabaseClient(mock_config)
        count = client.insert_equity_data(sample_equity_df)
        
        assert count == 2
        mock_table.upsert.assert_called_once()
    
    @patch("supabase_client.create_client")
    def test_insert_empty_dataframe(self, mock_create_client, mock_config):
        """Test inserting empty DataFrame."""
        client = SupabaseClient(mock_config)
        empty_df = pd.DataFrame()
        
        count = client.insert_equity_data(empty_df)
        
        assert count == 0
    
    @patch("supabase_client.create_client")
    def test_get_equity_data(self, mock_create_client, mock_config):
        """Test retrieving equity data."""
        # Setup mock
        mock_response = Mock()
        mock_response.data = [
            {
                "ticker": "QQQ",
                "timestamp": datetime.now().isoformat(),
                "price": 450.25,
                "volume": 1000000
            }
        ]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_create_client.return_value.table.return_value = mock_table
        
        client = SupabaseClient(mock_config)
        df = client.get_equity_data("QQQ", limit=100)
        
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "QQQ"
    
    @patch("supabase_client.create_client")
    def test_connection_test(self, mock_create_client, mock_config):
        """Test connection testing."""
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value = Mock()
        mock_create_client.return_value.table.return_value = mock_table
        
        client = SupabaseClient(mock_config)
        result = client.test_connection()
        
        assert result is True

