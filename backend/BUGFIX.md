# Bug Fix: Streaming Test Errors

## Issue 1: AttributeError
```
AttributeError: 'dict' object has no attribute 'status_code'
```

## Issue 2: ValueError
```
ValueError: value must be an integer, received <class 'str'> for year
```

## Issue 3: TypeError
```
TypeError: SupabaseClient.get_equity_data() got an unexpected keyword argument 'start_date'
```

## Root Causes

### Issue 1: Response Object vs Dictionary

The `test_real_time_streaming.py` test was treating the return value of `schwab_client.get_price_history()` as if it were a raw HTTP Response object, but the method actually returns a **parsed dictionary**.

### What Happened:

**❌ Old (Incorrect) Code:**
```python
response = schwab_client.get_price_history(...)
assert response.status_code == 200  # ❌ Error! response is a dict, not Response
data = response.json()
```

**✅ New (Fixed) Code:**
```python
data = schwab_client.get_price_history(...)
assert data is not None  # ✅ Correct! data is already the parsed dict
candles = data.get('candles', [])
```

## Why This Happened

The `SchwabClient.get_price_history()` method (in `schwab_integration/client.py`) already:
1. Calls the Schwab API
2. Checks the status code internally
3. Raises an exception if status != 200
4. Parses the JSON
5. **Returns the parsed dictionary**

```python
# From client.py, lines 183-206
response = client_instance.get_price_history(...)

if response.status_code != 200:  # ✅ Status check happens HERE
    logger.error(...)
    response.raise_for_status()

data = response.json()  # Parse to dict
return data  # ✅ Returns dict, not Response object
```

### Issue 2: Pandas Timestamp vs String

The test was treating DataFrame timestamps as if they were strings, but pandas returns `Timestamp` objects which don't have `.replace()` method like strings do.

**❌ Old (Incorrect) Code:**
```python
first_timestamp = df['timestamp'].min()  # Returns pandas.Timestamp
data_date = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00')).date()
# ❌ Error! Timestamp.replace() expects integer arguments, not strings
```

**✅ New (Fixed) Code:**
```python
first_timestamp = df['timestamp'].min()  # Returns pandas.Timestamp
data_date = first_timestamp.date()  # ✅ Direct call to .date() method
```

### Issue 3: Incorrect SupabaseClient Method Signature

The test was calling `get_equity_data()` and `get_indicators()` with `start_date` and `end_date` parameters, but these methods only accept `ticker` and `limit`. Additionally, they return DataFrames, not lists.

**❌ Old (Incorrect) Code:**
```python
retrieved_equity = supabase_client.get_equity_data(
    ticker=ticker,
    start_date=start_date,
    end_date=end_date
)
# Treated as list: retrieved_equity[0]['timestamp']
```

**✅ New (Fixed) Code:**
```python
retrieved_equity_df = supabase_client.get_equity_data(
    ticker=ticker,
    limit=1000
)
# Treated as DataFrame: retrieved_equity_df['timestamp'].iloc[0]
```

**Actual Method Signature** (from `supabase_client.py`):
```python
def get_equity_data(self, ticker: str, limit: int = 390) -> pd.DataFrame:
    """Retrieve equity data from Supabase."""
    # Returns DataFrame, not list
```

## Fixes Applied

**File**: `backend/tests/test_real_time_streaming.py`

1. **Line 62-74**: Changed from expecting Response object to handling dict directly
2. **Line 141-142**: Fixed pandas Timestamp conversion (removed unnecessary ISO format conversion)
3. **Line 247-263**: Fixed `get_equity_data()` call - removed invalid parameters, handle DataFrame return
4. **Line 265-270**: Fixed `get_indicators()` call - removed invalid parameters, handle DataFrame return
5. **Line 313-317**: Fixed data retrieval in update cycle test - use correct method signature
6. **Line 322-341**: Updated DataFrame access patterns (.iloc[] instead of list indexing)

## Impact

- ✅ Test now runs successfully
- ✅ No API behavior changes
- ✅ Error handling still works (exceptions are raised in client.py if API call fails)
- ✅ All other tests unaffected

## Testing

Run the streaming test:
```bash
cd backend
source venv/bin/activate
python tests/test_real_time_streaming.py
```

Or use VS Code launch configuration:
- Press F5 → Select "📡 4. Stream Real-Time Data"

## Related Files

- `backend/schwab_integration/client.py` - SchwabClient class
- `backend/tests/test_real_time_streaming.py` - Fixed test file
- `.vscode/launch.json` - Launch configuration for testing

---

**Fixed**: October 19, 2025  
**Status**: ✅ Resolved

