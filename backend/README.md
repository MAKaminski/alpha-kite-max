# Backend Services

Python backend for downloading equity data from Schwab API and loading into Supabase.

## Setup

### Prerequisites

- **Python 3.10+** required (schwab-py dependency)
- Check your version: `python3 --version`
- If needed, use: `/opt/homebrew/bin/python3.10` (macOS Homebrew)

### 1. Install Dependencies

```bash
cd backend
# Use Python 3.10 or higher
python3.10 -m venv venv  # Or python3 if default is 3.10+
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `backend` directory:

```bash
# Schwab API
SCHWAB_APP_KEY=your-schwab-app-key
SCHWAB_APP_SECRET=your-schwab-app-secret

# Supabase
SUPABASE_URL=https://xwcauibwyxhsifnotnzz.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 3. First-Time Schwab Authentication

The first time you run the script, it will require manual OAuth authentication:

```bash
python main.py --test-connections
```

This will:
1. Print a URL to authorize the application
2. Open your browser to Schwab's OAuth page
3. After authorization, you'll be redirected to a callback URL
4. Copy the full callback URL and paste it back into the terminal
5. Tokens will be saved to `.schwab_tokens.json` for future use

**Note**: The callback URL will be shown - you need to click it yourself (per user preference).

## Usage

### Test Connections

```bash
python main.py --test-connections
```

### Download Data

Download 5 days of QQQ data:
```bash
python main.py --ticker QQQ --days 5
```

Download 10 days of SPY data:
```bash
python main.py --ticker SPY --days 10
```

## Testing

Run all tests:
```bash
cd backend
source venv/bin/activate  # or .venv/bin/activate
pytest
```

Run specific test suites:
```bash
# Supabase tests only
pytest tests/test_supabase/

# Schwab tests only
pytest tests/test_schwab/

# Integration tests only
pytest tests/integration/

# Paper trading tests
pytest tests/test_paper_trading.py

# Current day tests
pytest tests/test_current_day.py

# Comprehensive test suite
pytest tests/fortified_test_suite.py
```

With coverage:
```bash
pytest --cov=. --cov-report=html
```

## System Testing & Utilities

The `sys_testing/` directory contains ad-hoc scripts for debugging, authentication, and maintenance:

### OAuth & Authentication
- `auto_reauth.py`: Automated Schwab OAuth re-authentication
- `reauth_schwab.py`: Manual re-authentication flow
- `get_auth_url.py`: Generate OAuth authorization URL
- `process_callback.py`: Process OAuth callback and save tokens
- `refresh_schwab_auth.py`: Refresh existing tokens

### Diagnostics
- `token_diagnostics.py`: Check token health and expiration
- `check_data_status.py`: Verify data integrity in Supabase
- `download_missing_data.py`: Backfill missing historical data
- `fortified_token_manager.py`: Production-ready token management

See `sys_testing/README.md` for detailed usage instructions.

## Architecture

```
backend/
├── schwab_integration/  # Schwab API integration
│   ├── client.py       # API client wrapper
│   ├── downloader.py   # Historical data downloader
│   ├── streaming.py    # Real-time streaming
│   ├── config.py       # Configuration models
│   └── trading_engine.py # Trading execution
├── models/             # Pydantic data models
│   └── trading.py      # Trading models
├── tests/              # Test suites
│   ├── test_schwab/    # Schwab API tests
│   ├── test_supabase/  # Database tests
│   ├── integration/    # Integration tests
│   ├── test_paper_trading.py
│   ├── test_current_day.py
│   └── fortified_test_suite.py
├── sys_testing/        # System testing & ad-hoc utilities
│   ├── auto_reauth.py  # Automated OAuth re-auth
│   ├── token_diagnostics.py # Token health checks
│   ├── check_data_status.py # Data integrity
│   └── README.md       # Utilities documentation
├── lambda/             # AWS Lambda deployment
│   ├── real_time_streamer.py # Lambda handler
│   ├── token_manager.py      # Token management
│   └── deploy_*.sh           # Deployment scripts
├── supabase_client.py  # Supabase CRUD operations
├── etl_pipeline.py     # ETL orchestration
├── main.py             # CLI entry point (data download)
└── trading_main.py     # CLI entry point (trading)
```

## Data Flow

1. **Extract**: Download minute-level price data from Schwab API
2. **Transform**: Calculate technical indicators (SMA9, VWAP)
3. **Load**: Insert data into Supabase (equity_data and indicators tables)

## Dependencies

Core dependencies:
- `schwab-py`: Official Schwab API Python client
- `supabase`: Supabase Python client
- `pandas`: Data manipulation and indicator calculation
- `pydantic`: Configuration and data model validation
- `pytest`: Testing framework
- `structlog`: Structured logging
- `boto3`: AWS SDK (for Lambda and Secrets Manager)
- `pytz`: Timezone handling

### Package Management

This project uses `uv` for faster package installation:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
cd backend
uv venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies (10-100x faster than pip)
uv pip install -r requirements.txt
```

**Why uv?**
- 10-100x faster than pip for package resolution
- Better dependency conflict detection
- More efficient package caching
- Drop-in replacement for pip

## Security

⚠️ **Important**: Never commit credentials or tokens to Git!

See [SECURITY.md](../SECURITY.md) for:
- Credential management best practices
- OAuth token handling
- Environment variable setup
- AWS Secrets Manager configuration

**Quick checklist:**
- [ ] `.env` file is in `.gitignore`
- [ ] `.schwab_tokens.json` is in `.gitignore`
- [ ] Use `env.example` as template, never commit `.env`
- [ ] Set file permissions: `chmod 600 .env`

