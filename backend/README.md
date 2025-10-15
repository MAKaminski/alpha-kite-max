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
```

With coverage:
```bash
pytest --cov=. --cov-report=html
```

## Architecture

```
backend/
├── schwab/              # Schwab API integration
│   ├── client.py       # API client wrapper
│   ├── downloader.py   # Data downloader
│   └── config.py       # Configuration models
├── supabase_client.py  # Supabase CRUD operations
├── etl_pipeline.py     # ETL orchestration
├── main.py             # CLI entry point
└── tests/              # Test suites
    ├── test_schwab/
    ├── test_supabase/
    └── integration/
```

## Data Flow

1. **Extract**: Download minute-level price data from Schwab API
2. **Transform**: Calculate technical indicators (SMA9, VWAP)
3. **Load**: Insert data into Supabase (equity_data and indicators tables)

## Dependencies

- `schwab-py`: Official Schwab API Python client
- `supabase`: Supabase Python client
- `pandas`: Data manipulation
- `pydantic`: Configuration management
- `pytest`: Testing framework
- `structlog`: Structured logging

