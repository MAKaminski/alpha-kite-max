"""Schwab API client wrapper using official schwab-py package."""

import os
import json
from typing import Optional
from datetime import datetime, timedelta
import structlog

from schwab import auth, client
from schwab.orders.equities import equity_buy_market

from .config import SchwabConfig


logger = structlog.get_logger()


class SchwabClient:
    """Wrapper for Schwab API client with authentication management."""
    
    def __init__(self, config: Optional[SchwabConfig] = None):
        """Initialize Schwab client.
        
        Args:
            config: Schwab configuration. If None, loads from environment.
        """
        self.config = config or SchwabConfig()
        self._client: Optional[client.Client] = None
        logger.info("schwab_client_initialized", app_key_prefix=self.config.app_key[:8])
    
    def authenticate(self) -> client.Client:
        """Authenticate with Schwab API and return client.
        
        Returns:
            Authenticated Schwab client.
            
        Note:
            On first run, this will print a URL for manual authentication.
            User must click the URL and authorize the app.
        """
        if self._client is not None:
            logger.debug("using_cached_client")
            return self._client
        
        try:
            # Try to load existing tokens
            if os.path.exists(self.config.token_path):
                logger.info("loading_existing_tokens", path=self.config.token_path)
                self._client = auth.client_from_token_file(
                    self.config.token_path,
                    self.config.app_key,
                    self.config.app_secret
                )
            else:
                # First time authentication - requires manual callback
                logger.warning(
                    "first_time_authentication_required",
                    message="Will open browser for OAuth. Click callback URL manually."
                )
                self._client = auth.client_from_manual_flow(
                    self.config.app_key,
                    self.config.app_secret,
                    self.config.callback_url,
                    self.config.token_path
                )
            
            logger.info("schwab_authentication_successful")
            return self._client
            
        except Exception as e:
            logger.error("schwab_authentication_failed", error=str(e))
            raise
    
    def get_option_chains(self, symbol: str, contract_type: str = "ALL") -> dict:
        """Fetch option chains for a symbol."""
        logger.info(
            "fetching_option_chains",
            symbol=symbol,
            contract_type=contract_type
        )

        client_instance = self.authenticate()
        
        # Map contract type to Schwab enum
        contract_enum = None
        if contract_type == "CALL":
            contract_enum = client.Client.Options.ContractType.CALL
        elif contract_type == "PUT":
            contract_enum = client.Client.Options.ContractType.PUT
        else:  # ALL
            contract_enum = client.Client.Options.ContractType.ALL

        response = client_instance.get_option_chains(
            symbol=symbol,
            contract_type=contract_enum,
            include_quotes=True
        )

        if response.status_code != 200:
            logger.error(
                "option_chains_fetch_failed",
                status_code=response.status_code,
                response=response.text
            )
            response.raise_for_status()

        logger.info("option_chains_fetched", symbol=symbol)
        return response.json()

    def get_option_quote(self, symbol: str) -> dict:
        """Get option quote for a specific option symbol."""
        logger.info("fetching_option_quote", symbol=symbol)

        client_instance = self.authenticate()
        
        response = client_instance.get_option_quotes([symbol])

        if response.status_code != 200:
            logger.error(
                "option_quote_fetch_failed",
                status_code=response.status_code,
                response=response.text
            )
            response.raise_for_status()

        logger.info("option_quote_fetched", symbol=symbol)
        return response.json()
    
    def get_price_history(
        self,
        symbol: str,
        period_type: str = "day",
        period: int = 5,
        frequency_type: str = "minute",
        frequency: int = 1,
        need_extended_hours_data: bool = False
    ) -> dict:
        """Get price history for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            period_type: Type of period (day, month, year, ytd)
            period: Number of periods
            frequency_type: Type of frequency (minute, daily, weekly, monthly)
            frequency: Frequency value (1, 5, 10, 15, 30 for minutes)
            need_extended_hours_data: Include extended hours data
            
        Returns:
            Price history data from Schwab API
        """
        client_instance = self.authenticate()
        
        logger.info(
            "fetching_price_history",
            symbol=symbol,
            period_type=period_type,
            period=period,
            frequency=f"{frequency}{frequency_type}"
        )
        
        # Map period to appropriate Schwab enum
        if period_type == "day":
            if period == 1:
                period_enum = client.Client.PriceHistory.Period.ONE_DAY
            elif period == 2:
                period_enum = client.Client.PriceHistory.Period.TWO_DAYS
            elif period == 3:
                period_enum = client.Client.PriceHistory.Period.THREE_DAYS
            elif period == 5:
                period_enum = client.Client.PriceHistory.Period.FIVE_DAYS
            elif period == 10:
                period_enum = client.Client.PriceHistory.Period.TEN_DAYS
            else:
                # For periods > 10 days, use month
                period_type = "month"
                period = 1
                period_enum = client.Client.PriceHistory.Period.ONE_MONTH
        
        if period_type == "month":
            period_enum = client.Client.PriceHistory.Period.ONE_MONTH
        
        response = client_instance.get_price_history(
            symbol,
            period_type=client.Client.PriceHistory.PeriodType.DAY if period_type == "day" else client.Client.PriceHistory.PeriodType.MONTH,
            period=period_enum,
            frequency_type=client.Client.PriceHistory.FrequencyType.MINUTE,
            frequency=client.Client.PriceHistory.Frequency.EVERY_MINUTE
        )
        
        if response.status_code != 200:
            logger.error(
                "price_history_fetch_failed",
                status_code=response.status_code,
                response=response.text
            )
            response.raise_for_status()
        
        data = response.json()
        logger.info(
            "price_history_fetched",
            symbol=symbol,
            candles_count=len(data.get("candles", []))
        )
        
        return data
    
    def close(self):
        """Close the client session."""
        if self._client:
            logger.info("closing_schwab_client")
            # schwab-py client doesn't have explicit close, but we clear reference
            self._client = None

