"""Option data downloader for 0DTE options from Schwab API."""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import pandas as pd
import structlog

from .client import SchwabClient
from .config import SchwabConfig


logger = structlog.get_logger()


class OptionDownloader:
    """Downloads 0DTE option data from Schwab API."""
    
    def __init__(self, schwab_client: Optional[SchwabClient] = None):
        """Initialize option downloader.
        
        Args:
            schwab_client: Schwab client instance. If None, creates new one.
        """
        self.client = schwab_client or SchwabClient()
        logger.info("option_downloader_initialized")
    
    def get_0dte_options_at_strike(
        self,
        ticker: str,
        target_strike: float,
        target_date: Optional[date] = None
    ) -> pd.DataFrame:
        """Get 0DTE call and put options at a specific strike price.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'QQQ')
            target_strike: Target strike price (e.g., 600.0)
            target_date: Target expiration date (defaults to today)
            
        Returns:
            DataFrame with option data for both calls and puts at the strike
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info(
            "fetching_0dte_options",
            ticker=ticker,
            strike=target_strike,
            expiration=target_date.isoformat()
        )
        
        try:
            # Get full option chain from Schwab
            option_data = self.client.get_option_chains(ticker, contract_type="ALL")
            
            if not option_data:
                logger.warning("no_option_data_returned", ticker=ticker)
                return pd.DataFrame()
            
            # Extract options for the target expiration date
            options = self._extract_options_for_date(
                option_data, 
                target_date, 
                target_strike
            )
            
            if not options:
                logger.warning(
                    "no_options_found_for_strike",
                    ticker=ticker,
                    strike=target_strike,
                    date=target_date
                )
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(options)
            
            logger.info(
                "0dte_options_downloaded",
                ticker=ticker,
                strike=target_strike,
                rows=len(df)
            )
            
            return df
            
        except Exception as e:
            logger.error(
                "option_download_failed",
                error=str(e),
                ticker=ticker,
                strike=target_strike
            )
            raise
    
    def _extract_options_for_date(
        self,
        option_data: Dict[str, Any],
        target_date: date,
        target_strike: float
    ) -> List[Dict[str, Any]]:
        """Extract option data for a specific expiration date and strike.
        
        Args:
            option_data: Raw option chain data from Schwab API
            target_date: Target expiration date
            target_strike: Target strike price
            
        Returns:
            List of option records
        """
        options = []
        current_timestamp = datetime.now()
        
        # Schwab API structure:
        # - callExpDateMap: { "2025-10-19:0": { "600.0": [option_data] } }
        # - putExpDateMap: { "2025-10-19:0": { "600.0": [option_data] } }
        
        for option_type in ['CALL', 'PUT']:
            exp_map_key = 'callExpDateMap' if option_type == 'CALL' else 'putExpDateMap'
            exp_date_map = option_data.get(exp_map_key, {})
            
            if not exp_date_map:
                continue
            
            # Find the expiration date key that matches our target
            target_date_str = target_date.isoformat()
            
            for exp_key, strike_map in exp_date_map.items():
                # exp_key format: "2025-10-19:0" (date:DTE)
                exp_date_part = exp_key.split(':')[0]
                
                if exp_date_part != target_date_str:
                    continue
                
                # Look for our target strike price
                strike_key = str(target_strike)
                
                if strike_key not in strike_map:
                    # Try to find closest strike
                    available_strikes = [float(k) for k in strike_map.keys()]
                    if not available_strikes:
                        continue
                    
                    closest_strike = min(available_strikes, key=lambda x: abs(x - target_strike))
                    strike_key = str(closest_strike)
                    logger.info(
                        "using_closest_strike",
                        target_strike=target_strike,
                        closest_strike=closest_strike
                    )
                
                option_list = strike_map.get(strike_key, [])
                
                for option in option_list:
                    try:
                        options.append({
                            'ticker': option_data.get('symbol', ''),
                            'timestamp': current_timestamp.isoformat(),
                            'option_type': option_type,
                            'strike_price': float(option.get('strikePrice', 0)),
                            'expiration_date': exp_date_part,
                            'last_price': float(option.get('last', 0)) if option.get('last') else None,
                            'bid': float(option.get('bid', 0)) if option.get('bid') else None,
                            'ask': float(option.get('ask', 0)) if option.get('ask') else None,
                            'volume': int(option.get('totalVolume', 0)),
                            'open_interest': int(option.get('openInterest', 0)),
                            'implied_volatility': float(option.get('volatility', 0)) if option.get('volatility') else None,
                            'delta': float(option.get('delta', 0)) if option.get('delta') else None,
                            'gamma': float(option.get('gamma', 0)) if option.get('gamma') else None,
                            'theta': float(option.get('theta', 0)) if option.get('theta') else None,
                            'vega': float(option.get('vega', 0)) if option.get('vega') else None,
                            'option_symbol': option.get('symbol', '')
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning("error_parsing_option", error=str(e), option=option)
                        continue
        
        return options
    
    def download_daily_0dte_options(
        self,
        ticker: str,
        strikes: List[float],
        days: int = 5
    ) -> pd.DataFrame:
        """Download 0DTE options for multiple strikes over multiple days.
        
        Args:
            ticker: Stock ticker symbol
            strikes: List of strike prices to track
            days: Number of past days to collect (defaults to 5)
            
        Returns:
            DataFrame with all collected option data
        """
        logger.info(
            "downloading_daily_0dte_options",
            ticker=ticker,
            strikes=strikes,
            days=days
        )
        
        all_options = []
        
        for day_offset in range(days):
            target_date = date.today() - timedelta(days=day_offset)
            
            # Skip weekends (basic check - doesn't account for holidays)
            if target_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                continue
            
            logger.info("fetching_options_for_date", date=target_date.isoformat())
            
            for strike in strikes:
                try:
                    df = self.get_0dte_options_at_strike(ticker, strike, target_date)
                    if not df.empty:
                        all_options.append(df)
                except Exception as e:
                    logger.error(
                        "failed_to_fetch_strike_date",
                        strike=strike,
                        date=target_date,
                        error=str(e)
                    )
                    continue
        
        if not all_options:
            logger.warning("no_options_collected")
            return pd.DataFrame()
        
        # Combine all data
        combined_df = pd.concat(all_options, ignore_index=True)
        combined_df = combined_df.drop_duplicates(
            subset=['ticker', 'timestamp', 'option_type', 'strike_price', 'expiration_date'],
            keep='last'
        )
        
        logger.info("daily_0dte_options_downloaded", rows=len(combined_df))
        
        return combined_df

