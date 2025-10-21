# Backend - Python Services

## Directory Structure

```
backend/
├── main.py ............................ Main entry point for data operations
├── trading_main.py .................... Main entry point for trading operations
├── etl_pipeline.py .................... ETL pipeline orchestration
│
├── clients/ ........................... External service clients
│   └── supabase_client.py ............. Supabase database client
│
├── models/ ............................ Data models
│   └── trading.py ..................... Trading-related Pydantic models
│
├── schwab_integration/ ................ Schwab API integration
│   ├── client.py ...................... Schwab API client wrapper
│   ├── downloader.py .................. Data downloader
│   ├── streaming.py ................... Real-time streaming
│   ├── trading_engine.py .............. Trading execution engine
│   ├── option_downloader.py ........... Options data downloader
│   └── config.py ...................... Configuration models
│
├── polygon_integration/ ............... Polygon.io API integration
│   ├── historic_options.py ............ Historical options data
│   ├── options_stream.py .............. Real-time options streaming
│   └── s3_bulk_downloader.py .......... S3 bulk data downloader
│
├── black_scholes/ ..................... Black-Scholes calculations
│   ├── calculator.py .................. Black-Scholes calculator
│   └── synthetic_generator.py ......... Synthetic options data generator
│
├── utils/ ............................. Utility modules
│   ├── transaction_logger.py .......... Transaction logging
│   └── portfolio_tracker.py ........... Portfolio tracking utilities
│
├── scripts/ ........................... Standalone scripts & tools
│   ├── auto_backfill.py ............... Automatic data backfill
│   ├── bulk_backfill_options.py ....... Bulk options backfill
│   ├── download_0dte_options.py ....... 0DTE options downloader
│   ├── standalone_qqq_download.py ..... Standalone QQQ downloader
│   └── generate_synthetic_options.py .. Generate synthetic data
│
├── tests/ ............................. Test suite
│   ├── test_schwab/ ................... Schwab integration tests
│   ├── test_supabase/ ................. Supabase tests
│   ├── integration/ ................... Integration tests
│   ├── test_live_trading_workflow.py .. Live trading workflow tests
│   └── [other test files]
│
└── sys_testing/ ....................... System testing & diagnostics
    ├── auto_reauth.py ................. Automated re-authentication
    ├── check_data_status.py ........... Data status checker
    ├── token_diagnostics.py ........... Token health diagnostics
    └── reauth_schwab.py ............... Schwab re-authentication
```

## Main Entry Points

### Data Operations
```bash
python main.py --ticker QQQ --days 5
```

### Trading Operations
```bash
python trading_main.py --mode paper --ticker QQQ
```

### ETL Pipeline
```bash
python etl_pipeline.py
```

## Scripts

All standalone scripts are in `scripts/` directory:

```bash
# Backfill data
python scripts/auto_backfill.py

# Download 0DTE options
python scripts/download_0dte_options.py

# Generate synthetic options
python scripts/generate_synthetic_options.py
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_schwab/ -v

# Run integration tests
pytest tests/integration/ -v

# Test live trading workflow
pytest tests/test_live_trading_workflow.py -v
```

## System Testing

```bash
# Check token status
python sys_testing/token_diagnostics.py

# Re-authenticate with Schwab
python sys_testing/reauth_schwab.py

# Check data status
python sys_testing/check_data_status.py
```

## Import Examples

```python
# Using clients
from clients.supabase_client import SupabaseClient

# Using models
from models.trading import Position, Trade, TradingSignal

# Using Schwab integration
from schwab_integration.client import SchwabClient
from schwab_integration.trading_engine import TradingEngine

# Using utilities
from utils.transaction_logger import TransactionLogger
from utils.portfolio_tracker import PortfolioTracker
```

## Development

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Code Organization Rules

1. **Only `main.py`, `trading_main.py`, and `etl_pipeline.py` should be in backend root**
2. **Clients go in `clients/`** - Database clients, API clients
3. **Models go in `models/`** - Pydantic models, data structures
4. **Integrations go in `*_integration/`** - Third-party API integrations
5. **Utils go in `utils/`** - Shared utilities and helpers
6. **Scripts go in `scripts/`** - Standalone scripts and tools
7. **Tests go in `tests/`** - All test files
8. **System testing goes in `sys_testing/`** - Diagnostics and system tests

---

*Last Updated: October 21, 2025*  
*Directory structure organized and cleaned*
