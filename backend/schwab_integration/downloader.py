"""Equity data downloader from Schwab API."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import structlog

from .client import SchwabClient
from .config import SchwabConfig


logger = structlog.get_logger()


class EquityDownloader:
    """Downloads and transforms equity data from Schwab API."""
    
    def __init__(self, schwab_client: Optional[SchwabClient] = None):
        """Initialize downloader.
        
        Args:
            schwab_client: Schwab client instance. If None, creates new one.
        """
        self.client = schwab_client or SchwabClient()
        logger.info("equity_downloader_initialized")
    
    def download_minute_data(
        self,
        ticker: str,
        days: int = 5
    ) -> pd.DataFrame:
        """Download minute-level price data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of historical data to fetch
            
        Returns:
            DataFrame with columns: ticker, timestamp, price, volume
        """
        logger.info("downloading_minute_data", ticker=ticker, days=days)
        
        # Schwab API supports max 10 days of minute data at once
        # For > 10 days, download in chunks
        if days <= 10:
            data = self.client.get_price_history(
                symbol=ticker,
                period_type="day",
                period=days,
                frequency_type="minute",
                frequency=1
            )
            df = self._transform_to_dataframe(ticker, data)
        else:
            # Download in 10-day chunks
            all_dfs = []
            remaining_days = days
            
            while remaining_days > 0:
                chunk_days = min(10, remaining_days)
                logger.info("downloading_chunk", chunk_days=chunk_days, remaining=remaining_days)
                
                data = self.client.get_price_history(
                    symbol=ticker,
                    period_type="day",
                    period=chunk_days,
                    frequency_type="minute",
                    frequency=1
                )
                
                chunk_df = self._transform_to_dataframe(ticker, data)
                if not chunk_df.empty:
                    all_dfs.append(chunk_df)
                
                remaining_days -= 10
            
            # Combine all chunks
            if all_dfs:
                df = pd.concat(all_dfs, ignore_index=True)
                df = df.drop_duplicates(subset=["ticker", "timestamp"], keep="last")
                df = df.sort_values("timestamp")
            else:
                df = pd.DataFrame(columns=["ticker", "timestamp", "price", "volume"])
        
        logger.info(
            "minute_data_downloaded",
            ticker=ticker,
            rows=len(df),
            date_range=f"{df['timestamp'].min()} to {df['timestamp'].max()}" if len(df) > 0 else "empty"
        )
        
        return df
    
    def _transform_to_dataframe(self, ticker: str, schwab_data: dict) -> pd.DataFrame:
        """Transform Schwab API response to DataFrame.
        
        Args:
            ticker: Stock ticker symbol
            schwab_data: Raw data from Schwab API
            
        Returns:
            DataFrame with equity data
        """
        candles = schwab_data.get("candles", [])
        
        if not candles:
            logger.warning("no_candles_in_response", ticker=ticker)
            return pd.DataFrame(columns=["ticker", "timestamp", "price", "volume"])
        
        # Extract data from candles
        records = []
        for candle in candles:
            # Schwab returns timestamp in milliseconds
            timestamp = pd.to_datetime(candle["datetime"], unit="ms", utc=True)
            
            # Truncate to second precision (per user preference memory #6839034)
            timestamp = timestamp.floor("s")
            
            records.append({
                "ticker": ticker,
                "timestamp": timestamp,
                "price": candle["close"],  # Using close price
                "volume": candle["volume"]
            })
        
        df = pd.DataFrame(records)
        
        # Remove duplicates (keep last)
        df = df.drop_duplicates(subset=["ticker", "timestamp"], keep="last")
        
        # Sort by timestamp
        df = df.sort_values("timestamp")
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators (SMA9, VWAP).
        
        Args:
            df: DataFrame with equity data (ticker, timestamp, price, volume)
            
        Returns:
            DataFrame with indicators (ticker, timestamp, sma9, vwap)
        """
        if df.empty:
            logger.warning("empty_dataframe_for_indicators")
            return pd.DataFrame(columns=["ticker", "timestamp", "sma9", "vwap"])
        
        logger.info("calculating_indicators", rows=len(df))
        
        # Work on a copy to avoid modifying original DataFrame
        temp_df = df.copy()
        temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
        
        # Calculate SMA9 (9-period Simple Moving Average)
        temp_df["sma9"] = temp_df["price"].rolling(window=9, min_periods=1).mean()
        
        # Calculate Session VWAP (resets each trading day at 9:30 AM EST)
        # Convert to EST and identify trading sessions
        temp_df['est_time'] = temp_df['timestamp'].dt.tz_convert('America/New_York')
        temp_df['session_date'] = temp_df['est_time'].dt.date
        
        # Calculate VWAP within each session
        def calc_session_vwap(group):
            group = group.sort_values('timestamp')
            group['vwap'] = (group['price'] * group['volume']).cumsum() / group['volume'].cumsum()
            return group
        
        temp_df = temp_df.groupby('session_date', group_keys=False).apply(calc_session_vwap)
        
        # Create indicators DataFrame with only required columns
        indicators_df = temp_df[["ticker", "timestamp", "sma9", "vwap"]].copy()
        
        # Round to 2 decimal places
        indicators_df["sma9"] = indicators_df["sma9"].round(2)
        indicators_df["vwap"] = indicators_df["vwap"].round(2)
        
        logger.info("indicators_calculated", rows=len(indicators_df))
        
        return indicators_df

