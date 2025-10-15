"""ETL Pipeline: Schwab → Transform → Supabase."""

from typing import Optional
import structlog

from schwab_integration.client import SchwabClient
from schwab_integration.downloader import EquityDownloader
from schwab_integration.config import SchwabConfig, SupabaseConfig, AppConfig
from supabase_client import SupabaseClient


logger = structlog.get_logger()


class ETLPipeline:
    """Orchestrates data flow from Schwab API to Supabase."""
    
    def __init__(
        self,
        schwab_config: Optional[SchwabConfig] = None,
        supabase_config: Optional[SupabaseConfig] = None,
        app_config: Optional[AppConfig] = None
    ):
        """Initialize ETL pipeline.
        
        Args:
            schwab_config: Schwab API configuration
            supabase_config: Supabase configuration
            app_config: Application configuration
        """
        self.app_config = app_config or AppConfig()
        
        # Initialize clients
        self.schwab_client = SchwabClient(schwab_config)
        self.downloader = EquityDownloader(self.schwab_client)
        self.supabase_client = SupabaseClient(supabase_config)
        
        logger.info("etl_pipeline_initialized")
    
    def run(self, ticker: Optional[str] = None, days: Optional[int] = None) -> dict:
        """Run the full ETL pipeline.
        
        Args:
            ticker: Stock ticker symbol (default from config)
            days: Number of days to fetch (default from config)
            
        Returns:
            Dictionary with pipeline results
        """
        ticker = ticker or self.app_config.default_ticker
        days = days or self.app_config.lookback_days
        
        logger.info("starting_etl_pipeline", ticker=ticker, days=days)
        
        try:
            # Step 1: Download equity data from Schwab
            logger.info("step_1_download_equity_data")
            equity_df = self.downloader.download_minute_data(ticker, days)
            
            if equity_df.empty:
                logger.warning("no_data_downloaded", ticker=ticker)
                return {
                    "success": False,
                    "ticker": ticker,
                    "equity_rows": 0,
                    "indicator_rows": 0,
                    "message": "No data downloaded from Schwab"
                }
            
            # Step 2: Calculate indicators
            logger.info("step_2_calculate_indicators")
            indicators_df = self.downloader.calculate_indicators(equity_df)
            
            # Step 3: Insert equity data into Supabase
            logger.info("step_3_insert_equity_data")
            equity_count = self.supabase_client.insert_equity_data(equity_df)
            
            # Step 4: Insert indicators into Supabase
            logger.info("step_4_insert_indicators")
            indicator_count = self.supabase_client.insert_indicators(indicators_df)
            
            logger.info(
                "etl_pipeline_completed",
                ticker=ticker,
                equity_rows=equity_count,
                indicator_rows=indicator_count
            )
            
            return {
                "success": True,
                "ticker": ticker,
                "equity_rows": equity_count,
                "indicator_rows": indicator_count,
                "date_range": {
                    "start": equity_df["timestamp"].min().isoformat(),
                    "end": equity_df["timestamp"].max().isoformat()
                }
            }
            
        except Exception as e:
            logger.error("etl_pipeline_failed", error=str(e), ticker=ticker)
            return {
                "success": False,
                "ticker": ticker,
                "equity_rows": 0,
                "indicator_rows": 0,
                "error": str(e)
            }
    
    def test_connections(self) -> dict:
        """Test all connections.
        
        Returns:
            Dictionary with connection test results
        """
        logger.info("testing_connections")
        
        results = {
            "supabase": False,
            "schwab": False
        }
        
        # Test Supabase
        try:
            results["supabase"] = self.supabase_client.test_connection()
        except Exception as e:
            logger.error("supabase_test_failed", error=str(e))
        
        # Test Schwab (just authenticate)
        try:
            self.schwab_client.authenticate()
            results["schwab"] = True
            logger.info("schwab_connection_successful")
        except Exception as e:
            logger.error("schwab_test_failed", error=str(e))
        
        return results

