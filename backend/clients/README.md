# Clients - External Service Clients

This directory contains client wrappers for external services.

## Files

- **supabase_client.py** - Supabase database client with CRUD operations

## Usage

```python
from clients.supabase_client import SupabaseClient

# Initialize client
client = SupabaseClient()

# Insert equity data
import pandas as pd
df = pd.DataFrame([{
    'ticker': 'QQQ',
    'timestamp': datetime.now(),
    'price': 389.45,
    'volume': 1000
}])
client.insert_equity_data(df)

# Query data
data = client.get_equity_data('QQQ', limit=390)
```

## Testing

```bash
pytest tests/test_supabase/ -v
```

