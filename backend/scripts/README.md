# Scripts - Standalone Utilities & Data Tools

Standalone scripts for data operations, backfill, and utilities.

## Data Download Scripts

### auto_backfill.py
Automatically backfill missing data in Supabase.

```bash
python scripts/auto_backfill.py
```

### bulk_backfill_options.py
Bulk backfill options data.

```bash
python scripts/bulk_backfill_options.py --ticker QQQ --days 5
```

### download_0dte_options.py
Download 0DTE (zero days to expiration) options data.

```bash
python scripts/download_0dte_options.py
```

### standalone_qqq_download.py
Standalone script for downloading QQQ data.

```bash
python scripts/standalone_qqq_download.py
```

## Data Generation Scripts

### generate_synthetic_options.py
Generate synthetic options data using Black-Scholes model.

```bash
python scripts/generate_synthetic_options.py --ticker QQQ --output data/
```

## Data Files

- **data/** - CSV files and generated data
  - `synthetic_options_october_2025_QQQ.csv` - Synthetic options data

## Usage Notes

All scripts assume you're running from the backend root directory:

```bash
cd backend
python scripts/script_name.py
```

Or add backend to your PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
python backend/scripts/script_name.py
```

