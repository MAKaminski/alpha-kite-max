"""Schwab API client wrapper using official schwab-py package."""

import os
import json
from typing import Optional
from datetime import datetime, timedelta
import structlog

from schwab import auth, client
from schwab.orders.equities import equity_buy_market
from schwab.orders.options import option_sell_to_open_limit, option_buy_to_close_limit

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
    
    def get_account_info(self) -> dict:
        """Get account information including account number.
        
        Returns:
            Dictionary with account information
        """
        logger.info("fetching_account_info")
        
        client_instance = self.authenticate()
        response = client_instance.get_account_numbers()
        
        if response.status_code != 200:
            logger.error(
                "account_info_fetch_failed",
                status_code=response.status_code,
                response=response.text
            )
            response.raise_for_status()
        
        accounts = response.json()
        logger.info("account_info_fetched", account_count=len(accounts))
        
        # Return the first account (typically paper trading account)
        if accounts:
            return accounts[0]
        return {}
    
    def place_option_order(
        self,
        account_id: str,
        symbol: str,
        option_symbol: str,
        instruction: str,  # 'SELL_TO_OPEN' or 'BUY_TO_CLOSE'
        quantity: int,
        price: float
    ) -> dict:
        """Place an option order.
        
        Args:
            account_id: Schwab account ID
            symbol: Underlying stock symbol
            option_symbol: Full option symbol (e.g., QQQ_102524P500)
            instruction: Order instruction ('SELL_TO_OPEN' or 'BUY_TO_CLOSE')
            quantity: Number of contracts
            price: Limit price per contract
            
        Returns:
            Dictionary with order details
        """
        logger.info(
            "placing_option_order",
            symbol=symbol,
            option_symbol=option_symbol,
            instruction=instruction,
            quantity=quantity,
            price=price
        )
        
        client_instance = self.authenticate()
        
        # Build order based on instruction
        if instruction == 'SELL_TO_OPEN':
            order = option_sell_to_open_limit(option_symbol, quantity, price)
        elif instruction == 'BUY_TO_CLOSE':
            order = option_buy_to_close_limit(option_symbol, quantity, price)
        else:
            raise ValueError(f"Invalid instruction: {instruction}")
        
        # Place the order
        response = client_instance.place_order(account_id, order)
        
        if response.status_code not in [200, 201]:
            logger.error(
                "option_order_failed",
                status_code=response.status_code,
                response=response.text
            )
            response.raise_for_status()
        
        # Extract order ID from location header
        order_id = None
        if 'Location' in response.headers:
            location = response.headers['Location']
            order_id = location.split('/')[-1]
        
        logger.info(
            "option_order_placed",
            order_id=order_id,
            symbol=symbol,
            option_symbol=option_symbol
        )
        
        return {
            'order_id': order_id,
            'status_code': response.status_code,
            'symbol': symbol,
            'option_symbol': option_symbol,
            'instruction': instruction,
            'quantity': quantity,
            'price': price
        }
    
    def get_order_status(self, account_id: str, order_id: str) -> dict:
        """Get order status.
        
        Args:
            account_id: Schwab account ID
            order_id: Order ID
            
        Returns:
            Dictionary with order status
        """
        logger.info("fetching_order_status", order_id=order_id)
        
        client_instance = self.authenticate()
        response = client_instance.get_order(account_id, order_id)
        
        if response.status_code != 200:
            logger.error(
                "order_status_fetch_failed",
                status_code=response.status_code,
                response=response.text
            )
            response.raise_for_status()
        
        order_data = response.json()
        logger.info("order_status_fetched", order_id=order_id, status=order_data.get('status'))
        
        return order_data
    
    def close(self):
        """Close the client session."""
        if self._client:
            logger.info("closing_schwab_client")
            # schwab-py client doesn't have explicit close, but we clear reference
            self._client = None

