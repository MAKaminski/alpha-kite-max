"""Supabase client for CRUD operations."""

from typing import List, Dict, Any, Optional
import pandas as pd
import structlog
from supabase import create_client, Client

from schwab_integration.config import SupabaseConfig


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

