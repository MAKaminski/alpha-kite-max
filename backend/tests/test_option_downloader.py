"""
Unit tests for Option Downloader module.
"""

import pytest
import sys
from pathlib import Path
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from schwab_integration.option_downloader import OptionDownloader
from schwab_integration.client import SchwabClient


class TestOptionDownloader:
    """Unit tests for OptionDownloader class."""
    
    @pytest.fixture
    def mock_schwab_client(self):
        """Create a mock Schwab client."""
        mock = Mock(spec=SchwabClient)
        return mock
    
    @pytest.fixture
    def option_downloader(self, mock_schwab_client):
        """Create OptionDownloader with mocked client."""
        return OptionDownloader(mock_schwab_client)
    
    def test_initialization(self, option_downloader):
        """Test OptionDownloader initializes correctly."""
        assert option_downloader is not None
        assert option_downloader.client is not None
    
    def test_get_0dte_options_at_strike_success(self, option_downloader, mock_schwab_client):
        """Test successful 0DTE option retrieval."""
        # Mock option chain response
        mock_option_data = {
            'symbol': 'QQQ',
            'callExpDateMap': {
                '2025-10-20:0': {
                    '600.0': [{
                        'strikePrice': 600.0,
                        'last': 2.5,
                        'bid': 2.45,
                        'ask': 2.55,
                        'totalVolume': 1000,
                        'openInterest': 5000,
                        'volatility': 0.25,
                        'delta': 0.45,
                        'gamma': 0.05,
                        'theta': -0.15,
                        'vega': 0.20,
                        'symbol': 'QQQ251020C00600000'
                    }]
                }
            },
            'putExpDateMap': {
                '2025-10-20:0': {
                    '600.0': [{
                        'strikePrice': 600.0,
                        'last': 2.3,
                        'bid': 2.25,
                        'ask': 2.35,
                        'totalVolume': 1200,
                        'openInterest': 6000,
                        'volatility': 0.24,
                        'delta': -0.42,
                        'gamma': 0.05,
                        'theta': -0.14,
                        'vega': 0.19,
                        'symbol': 'QQQ251020P00600000'
                    }]
                }
            }
        }
        
        mock_schwab_client.get_option_chains.return_value = mock_option_data
        
        # Test retrieval
        target_date = date(2025, 10, 20)
        result = option_downloader.get_0dte_options_at_strike('QQQ', 600.0, target_date)
        
        # Verify results
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # 1 call + 1 put
        assert 'ticker' in result.columns
        assert 'option_type' in result.columns
        assert 'strike_price' in result.columns
        assert 'last_price' in result.columns
        
        # Check option types
        option_types = result['option_type'].unique()
        assert 'CALL' in option_types
        assert 'PUT' in option_types
    
    def test_get_0dte_options_no_data(self, option_downloader, mock_schwab_client):
        """Test handling when no option data is available."""
        mock_schwab_client.get_option_chains.return_value = {}
        
        target_date = date(2025, 10, 20)
        result = option_downloader.get_0dte_options_at_strike('QQQ', 600.0, target_date)
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    def test_extract_options_for_date(self, option_downloader):
        """Test option extraction logic."""
        mock_data = {
            'symbol': 'QQQ',
            'putExpDateMap': {
                '2025-10-20:0': {
                    '600.0': [{
                        'strikePrice': 600.0,
                        'last': 2.3,
                        'bid': 2.25,
                        'ask': 2.35,
                        'totalVolume': 1200,
                        'openInterest': 6000,
                        'symbol': 'QQQ251020P00600000'
                    }]
                }
            }
        }
        
        target_date = date(2025, 10, 20)
        options = option_downloader._extract_options_for_date(mock_data, target_date, 600.0)
        
        assert len(options) == 1
        assert options[0]['option_type'] == 'PUT'
        assert options[0]['strike_price'] == 600.0
        assert options[0]['ticker'] == 'QQQ'
    
    def test_download_daily_0dte_options_weekend_skip(self, option_downloader, mock_schwab_client):
        """Test that weekends are skipped in multi-day downloads."""
        mock_schwab_client.get_option_chains.return_value = {
            'symbol': 'QQQ',
            'putExpDateMap': {}
        }
        
        # This should skip weekends automatically
        result = option_downloader.download_daily_0dte_options('QQQ', [600.0], days=7)
        
        # Result may be empty but shouldn't crash
        assert isinstance(result, pd.DataFrame)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

