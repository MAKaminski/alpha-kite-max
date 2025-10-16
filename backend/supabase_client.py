"""Supabase client for CRUD operations."""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import pandas as pd
import structlog
from supabase import create_client, Client
from datetime import date

from schwab_integration.config import SupabaseConfig

# Conditional import to avoid circular dependencies
if TYPE_CHECKING:
    from models.trading import Position, Trade, TradingSignal, DailyPnL

logger = structlog.get_logger()


class SupabaseClient:
    """Client for interacting with Supabase database."""
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        """Initialize Supabase client.
        
        Args:
            config: Supabase configuration. If None, loads from environment.
        """
        self.config = config or SupabaseConfig()
        self.client: Client = create_client(
            self.config.url,
            self.config.service_role_key
        )
        logger.info("supabase_client_initialized", url=self.config.url)
    
    def insert_equity_data(self, df: pd.DataFrame) -> int:
        """Insert equity data into Supabase.
        
        Args:
            df: DataFrame with columns: ticker, timestamp, price, volume
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("empty_dataframe_for_equity_insert")
            return 0
        
        # Convert DataFrame to list of dicts
        records = df.to_dict("records")
        
        # Convert timestamps to ISO format strings
        for record in records:
            record["timestamp"] = record["timestamp"].isoformat()
        
        logger.info("inserting_equity_data", rows=len(records))
        
        try:
            # Upsert to handle duplicates
            response = self.client.table("equity_data").upsert(
                records,
                on_conflict="ticker,timestamp"
            ).execute()
            
            inserted_count = len(response.data) if response.data else 0
            logger.info("equity_data_inserted", count=inserted_count)
            return inserted_count
            
        except Exception as e:
            logger.error("equity_insert_failed", error=str(e))
            raise
    
    def insert_indicators(self, df: pd.DataFrame) -> int:
        """Insert indicator data into Supabase.
        
        Args:
            df: DataFrame with columns: ticker, timestamp, sma9, vwap
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("empty_dataframe_for_indicators_insert")
            return 0
        
        # Convert DataFrame to list of dicts
        records = df.to_dict("records")
        
        # Convert timestamps to ISO format strings
        for record in records:
            record["timestamp"] = record["timestamp"].isoformat()
        
        logger.info("inserting_indicators", rows=len(records))
        
        try:
            # Upsert to handle duplicates
            response = self.client.table("indicators").upsert(
                records,
                on_conflict="ticker,timestamp"
            ).execute()
            
            inserted_count = len(response.data) if response.data else 0
            logger.info("indicators_inserted", count=inserted_count)
            return inserted_count
            
        except Exception as e:
            logger.error("indicators_insert_failed", error=str(e))
            raise
    
    def get_equity_data(
        self,
        ticker: str,
        limit: int = 390
    ) -> pd.DataFrame:
        """Retrieve equity data from Supabase.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of records to retrieve
            
        Returns:
            DataFrame with equity data
        """
        logger.info("fetching_equity_data", ticker=ticker, limit=limit)
        
        try:
            all_data = []
            page_size = 1000
            page = 0
            
            # Paginate through all data
            while len(all_data) < limit:
                response = self.client.table("equity_data")\
                    .select("*")\
                    .eq("ticker", ticker)\
                    .order("timestamp", desc=False)\
                    .range(page * page_size, (page + 1) * page_size - 1)\
                    .execute()
                
                if not response.data or len(response.data) == 0:
                    break
                
                all_data.extend(response.data)
                
                if len(response.data) < page_size:
                    break
                    
                page += 1
            
            # Limit to requested number
            all_data = all_data[:limit]
            
            if not all_data:
                logger.warning("no_equity_data_found", ticker=ticker)
                return pd.DataFrame()
            
            df = pd.DataFrame(all_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            
            logger.info("equity_data_fetched", ticker=ticker, rows=len(df))
            return df
            
        except Exception as e:
            logger.error("equity_fetch_failed", error=str(e))
            raise
    
    def get_indicators(
        self,
        ticker: str,
        limit: int = 390
    ) -> pd.DataFrame:
        """Retrieve indicator data from Supabase.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of records to retrieve
            
        Returns:
            DataFrame with indicator data
        """
        logger.info("fetching_indicators", ticker=ticker, limit=limit)
        
        try:
            response = self.client.table("indicators")\
                .select("*")\
                .eq("ticker", ticker)\
                .order("timestamp", desc=True)\
                .limit(limit)\
                .execute()
            
            if not response.data:
                logger.warning("no_indicators_found", ticker=ticker)
                return pd.DataFrame()
            
            df = pd.DataFrame(response.data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            
            logger.info("indicators_fetched", ticker=ticker, rows=len(df))
            return df
            
        except Exception as e:
            logger.error("indicators_fetch_failed", error=str(e))
            raise
    
    # Trading Operations
    
    def get_open_positions(self, ticker: str) -> List[Any]:
        """Get all open positions for a ticker."""
        try:
            response = self.client.table("positions")\
                .select("*")\
                .eq("ticker", ticker)\
                .eq("status", "OPEN")\
                .execute()
            
            positions = []
            for row in response.data:
                positions.append(Position(**row))
            
            logger.info("open_positions_fetched", ticker=ticker, count=len(positions))
            return positions
            
        except Exception as e:
            logger.error("open_positions_fetch_failed", error=str(e))
            return []
    
    def create_position(self, position: Any) -> str:
        """Create a new position."""
        try:
            position_data = position.model_dump(exclude={'id', 'created_at', 'updated_at'})
            response = self.client.table("positions")\
                .insert(position_data)\
                .execute()
            
            if response.data:
                position_id = response.data[0]['id']
                logger.info("position_created", position_id=position_id, ticker=position.ticker)
                return position_id
            
        except Exception as e:
            logger.error("position_creation_failed", error=str(e))
            raise
    
    def update_position(self, position: Any) -> bool:
        """Update an existing position."""
        try:
            if not position.id:
                raise ValueError("Position ID is required for updates")
            
            update_data = position.model_dump(exclude={'id', 'created_at'}, exclude_none=True)
            response = self.client.table("positions")\
                .update(update_data)\
                .eq("id", position.id)\
                .execute()
            
            logger.info("position_updated", position_id=position.id)
            return True
            
        except Exception as e:
            logger.error("position_update_failed", error=str(e))
            return False
    
    def create_trade(self, trade: Any) -> str:
        """Create a new trade record."""
        try:
            trade_data = trade.model_dump(exclude={'id', 'created_at'})
            response = self.client.table("trades")\
                .insert(trade_data)\
                .execute()
            
            if response.data:
                trade_id = response.data[0]['id']
                logger.info("trade_created", trade_id=trade_id, ticker=trade.ticker)
                return trade_id
            
        except Exception as e:
            logger.error("trade_creation_failed", error=str(e))
            raise
    
    def create_trading_signal(self, signal: Any) -> str:
        """Create a new trading signal record."""
        try:
            signal_data = signal.model_dump(exclude={'id', 'created_at'})
            response = self.client.table("trading_signals")\
                .insert(signal_data)\
                .execute()
            
            if response.data:
                signal_id = response.data[0]['id']
                logger.info("trading_signal_created", signal_id=signal_id, ticker=signal.ticker)
                return signal_id
            
        except Exception as e:
            logger.error("trading_signal_creation_failed", error=str(e))
            raise
    
    def get_daily_pnl(self, ticker: str, trade_date: date) -> Optional[Any]:
        """Get daily P&L for a specific date."""
        try:
            response = self.client.table("daily_pnl")\
                .select("*")\
                .eq("ticker", ticker)\
                .eq("trade_date", trade_date.isoformat())\
                .execute()
            
            if response.data:
                return DailyPnL(**response.data[0])
            
            return None
            
        except Exception as e:
            logger.error("daily_pnl_fetch_failed", error=str(e))
            return None
    
    def update_daily_pnl(self, daily_pnl: Any) -> bool:
        """Update or create daily P&L record."""
        try:
            pnl_data = daily_pnl.model_dump(exclude={'id', 'created_at'}, exclude_none=True)
            
            if daily_pnl.id:
                # Update existing record
                response = self.client.table("daily_pnl")\
                    .update(pnl_data)\
                    .eq("id", daily_pnl.id)\
                    .execute()
            else:
                # Create new record
                response = self.client.table("daily_pnl")\
                    .insert(pnl_data)\
                    .execute()
            
            logger.info("daily_pnl_updated", ticker=daily_pnl.ticker, date=daily_pnl.trade_date)
            return True
            
        except Exception as e:
            logger.error("daily_pnl_update_failed", error=str(e))
            return False
    
    def get_trading_summary(self, ticker: str, trade_date: date) -> dict:
        """Get comprehensive trading summary for dashboard."""
        try:
            # Get daily P&L
            daily_pnl = self.get_daily_pnl(ticker, trade_date)
            
            # Get open positions
            open_positions = self.get_open_positions(ticker)
            
            # Get recent trades (last 10)
            trades_response = self.client.table("trades")\
                .select("*")\
                .eq("ticker", ticker)\
                .order("trade_timestamp", desc=True)\
                .limit(10)\
                .execute()
            
            recent_trades = [Trade(**row) for row in trades_response.data]
            
            # Get recent signals (last 10)
            signals_response = self.client.table("trading_signals")\
                .select("*")\
                .eq("ticker", ticker)\
                .order("signal_timestamp", desc=True)\
                .limit(10)\
                .execute()
            
            recent_signals = [TradingSignal(**row) for row in signals_response.data]
            
            # Calculate position summary
            total_unrealized_pnl = sum(pos.unrealized_pnl or 0 for pos in open_positions)
            
            return {
                'ticker': ticker,
                'date': trade_date,
                'daily_pnl': daily_pnl,
                'open_positions': open_positions,
                'recent_trades': recent_trades,
                'recent_signals': recent_signals,
                'total_unrealized_pnl': total_unrealized_pnl,
                'position_count': len(open_positions)
            }
            
        except Exception as e:
            logger.error("trading_summary_fetch_failed", error=str(e))
            return {}
    
    def upsert_equity_data(self, df: pd.DataFrame) -> bool:
        """Upsert equity data (wrapper for insert_equity_data for compatibility).
        
        Args:
            df: DataFrame with equity data
            
        Returns:
            True if successful
        """
        try:
            self.insert_equity_data(df)
            return True
        except:
            return False
    
    def upsert_indicators(self, df: pd.DataFrame) -> bool:
        """Upsert indicator data (wrapper for insert_indicators for compatibility).
        
        Args:
            df: DataFrame with indicator data
            
        Returns:
            True if successful
        """
        try:
            self.insert_indicators(df)
            return True
        except:
            return False
    
    def upsert_option_prices(self, df: pd.DataFrame) -> bool:
        """Upsert option prices into Supabase.
        
        Args:
            df: DataFrame with option price data
            
        Returns:
            True if successful
        """
        if df.empty:
            logger.warning("empty_dataframe_for_option_prices")
            return False
        
        # Convert DataFrame to list of dicts
        records = df.to_dict("records")
        
        # Convert timestamps to ISO format strings
        for record in records:
            if 'timestamp' in record:
                record["timestamp"] = record["timestamp"].isoformat() if hasattr(record["timestamp"], 'isoformat') else record["timestamp"]
            if 'expiration_date' in record:
                record["expiration_date"] = str(record["expiration_date"])
        
        logger.info("inserting_option_prices", rows=len(records))
        
        try:
            # Upsert to handle duplicates
            response = self.client.table("option_prices").upsert(
                records,
                on_conflict="ticker,timestamp,option_type,strike_price,expiration_date"
            ).execute()
            
            inserted_count = len(response.data) if response.data else 0
            logger.info("option_prices_inserted", count=inserted_count)
            return True
            
        except Exception as e:
            logger.error("option_prices_insert_failed", error=str(e))
            return False
    
    def test_connection(self) -> bool:
        """Test connection to Supabase.
        
        Returns:
            True if connection is successful
        """
        try:
            # Simple query to test connection
            self.client.table("equity_data").select("count", count="exact", head=True).execute()
            logger.info("supabase_connection_successful")
            return True
        except Exception as e:
            logger.error("supabase_connection_failed", error=str(e))
            return False

