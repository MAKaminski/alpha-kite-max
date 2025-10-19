"""
Transaction and Feature Usage Logger

Tracks all API calls, downloads, trades, and system actions for:
- Auditing
- Analytics
- Performance monitoring
- Usage tracking
"""

from typing import Optional, Dict, Any
from datetime import datetime
import json
import structlog
from supabase_client import SupabaseClient

logger = structlog.get_logger()


class TransactionLogger:
    """Logs transactions and tracks feature usage."""
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize transaction logger.
        
        Args:
            supabase_client: Supabase client for logging. If None, creates new one.
        """
        self.supabase = supabase_client or SupabaseClient()
    
    def log_transaction(
        self,
        transaction_type: str,
        feature_name: str,
        status: str = 'success',
        ticker: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        rows_affected: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Log a transaction.
        
        Args:
            transaction_type: Type of transaction ('download_data', 'stream_data', 'place_order', etc.)
            feature_name: Name of feature ('historical_download', 'option_download', etc.)
            status: 'success', 'failed', or 'pending'
            ticker: Stock ticker symbol
            parameters: Dictionary of parameters used
            rows_affected: Number of rows affected
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if failed
            user_id: User ID if applicable
            
        Returns:
            Transaction ID
        """
        try:
            transaction_data = {
                'transaction_type': transaction_type,
                'feature_name': feature_name,
                'status': status,
                'ticker': ticker,
                'parameters': json.dumps(parameters) if parameters else None,
                'rows_affected': rows_affected,
                'execution_time_ms': execution_time_ms,
                'error_message': error_message,
                'user_id': user_id,
                'created_at': datetime.now().isoformat()
            }
            
            response = self.supabase.client.table('transactions')\
                .insert(transaction_data)\
                .execute()
            
            if response.data:
                transaction_id = response.data[0]['id']
                logger.info(
                    "transaction_logged",
                    transaction_id=transaction_id,
                    feature=feature_name,
                    status=status
                )
                return transaction_id
            
        except Exception as e:
            logger.error("transaction_logging_failed", error=str(e))
            # Don't fail the main operation if logging fails
            return None
    
    def get_feature_stats(self, feature_name: Optional[str] = None) -> Dict[str, Any]:
        """Get feature usage statistics.
        
        Args:
            feature_name: Specific feature to get stats for. If None, returns all features.
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            query = self.supabase.client.table('feature_usage').select('*')
            
            if feature_name:
                query = query.eq('feature_name', feature_name)
            
            response = query.execute()
            
            return response.data
            
        except Exception as e:
            logger.error("feature_stats_fetch_failed", error=str(e))
            return {}
    
    def get_daily_usage(self, days: int = 7) -> list:
        """Get daily usage statistics.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of daily usage records
        """
        try:
            response = self.supabase.client.rpc(
                'feature_usage_daily',
                {}
            ).limit(days * 10).execute()  # Rough estimate
            
            return response.data
            
        except Exception as e:
            logger.error("daily_usage_fetch_failed", error=str(e))
            return []


# Example usage decorators
def track_transaction(feature_name: str, transaction_type: str):
    """Decorator to automatically track function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger = TransactionLogger()
            
            try:
                result = func(*args, **kwargs)
                
                # Calculate execution time
                exec_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Log success
                logger.log_transaction(
                    transaction_type=transaction_type,
                    feature_name=feature_name,
                    status='success',
                    execution_time_ms=exec_time
                )
                
                return result
                
            except Exception as e:
                # Calculate execution time
                exec_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Log failure
                logger.log_transaction(
                    transaction_type=transaction_type,
                    feature_name=feature_name,
                    status='failed',
                    execution_time_ms=exec_time,
                    error_message=str(e)
                )
                
                raise
        
        return wrapper
    return decorator


# Usage example:
# @track_transaction(feature_name='historical_download', transaction_type='download_data')
# def download_data(ticker, days):
#     # Your function code
#     pass

