# Utils - Utility Modules

Shared utility modules and helper functions.

## Files

- **transaction_logger.py** - Transaction logging utility
- **portfolio_tracker.py** - Portfolio tracking and P&L calculations

## Usage

```python
from utils.transaction_logger import TransactionLogger
from utils.portfolio_tracker import PortfolioTracker

# Log transactions
logger = TransactionLogger()
logger.log_trade(trade_data)

# Track portfolio
tracker = PortfolioTracker()
positions = tracker.get_open_positions('QQQ')
```

