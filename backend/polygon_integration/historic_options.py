"""
Polygon.io Historic Options Data Downloader

Downloads historical options data from Polygon.io REST API.
Free tier limits: 5 calls/minute, 2 years of historical data.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests
import pandas as pd
import structlog
from dotenv import load_dotenv

load_dotenv()
logger = structlog.get_logger()


class PolygonHistoricOptions:
    """Downloads historical options data from Polygon.io."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Polygon API client.
        
        Args:
            api_key: Polygon.io API key. If None, reads from POLYGON_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not found in environment variables")
        
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        
        logger.info("polygon_historic_options_initialized", api_key_length=len(self.api_key))
    
    def get_option_contract_details(
        self,
        ticker: str,
        expiration_date: str,
        strike: float,
        option_type: str = "call"
    ) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific option contract.
        
        Args:
            ticker: Underlying ticker symbol (e.g., "QQQ")
            expiration_date: Expiration date in YYYY-MM-DD format
            strike: Strike price
            option_type: "call" or "put"
            
        Returns:
            Option contract details or None if not found
        """
        # Build OCC option symbol (e.g., QQQ251024C00600000)
        exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
        exp_str = exp_date.strftime("%y%m%d")
        type_code = "C" if option_type.lower() == "call" else "P"
        strike_str = f"{int(strike * 1000):08d}"
        option_symbol = f"O:{ticker}{exp_str}{type_code}{strike_str}"
        
        url = f"{self.base_url}/v3/reference/options/contracts/{option_symbol}"
        params = {"apiKey": self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                logger.info("option_contract_found", symbol=option_symbol)
                return data["results"]
            else:
                logger.warning("option_contract_not_found", symbol=option_symbol)
                return None
                
        except requests.RequestException as e:
            logger.error("option_contract_lookup_failed", error=str(e), symbol=option_symbol)
            return None
    
    def get_option_chain_snapshot(
        self,
        ticker: str,
        expiration_date: str,
        strikes: Optional[List[float]] = None
    ) -> pd.DataFrame:
        """
        Get current snapshot of option chain for specific expiration.
        
        Args:
            ticker: Underlying ticker symbol
            expiration_date: Expiration date in YYYY-MM-DD format
            strikes: List of strike prices to query (if None, gets all)
            
        Returns:
            DataFrame with option chain data
        """
        url = f"{self.base_url}/v3/snapshot/options/{ticker}"
        params = {
            "apiKey": self.api_key,
            "expiration_date": expiration_date,
            "limit": 250  # Max results per request
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                results = data["results"]
                
                # Filter by strikes if specified
                if strikes:
                    results = [r for r in results if r.get("details", {}).get("strike_price") in strikes]
                
                # Convert to DataFrame
                records = []
                for result in results:
                    details = result.get("details", {})
                    last_quote = result.get("last_quote", {})
                    last_trade = result.get("last_trade", {})
                    greeks = result.get("greeks", {})
                    
                    records.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "ticker": ticker,
                        "option_symbol": details.get("ticker"),
                        "option_type": details.get("contract_type", "").upper(),
                        "strike_price": details.get("strike_price"),
                        "expiration_date": details.get("expiration_date"),
                        "last_price": last_trade.get("price"),
                        "bid": last_quote.get("bid"),
                        "ask": last_quote.get("ask"),
                        "volume": last_trade.get("size", 0) * 100,  # Convert to contract volume
                        "open_interest": result.get("open_interest", 0),
                        "implied_volatility": greeks.get("iv"),
                        "delta": greeks.get("delta"),
                        "gamma": greeks.get("gamma"),
                        "theta": greeks.get("theta"),
                        "vega": greeks.get("vega"),
                    })
                
                df = pd.DataFrame(records)
                logger.info("option_chain_snapshot_retrieved", 
                           ticker=ticker,
                           expiration=expiration_date,
                           contracts=len(records))
                return df
            else:
                logger.warning("no_option_chain_data", ticker=ticker, expiration=expiration_date)
                return pd.DataFrame()
                
        except requests.RequestException as e:
            logger.error("option_chain_snapshot_failed", error=str(e), ticker=ticker)
            return pd.DataFrame()
    
    def get_historical_option_prices(
        self,
        option_symbol: str,
        start_date: str,
        end_date: str,
        timespan: str = "minute",
        multiplier: int = 1
    ) -> pd.DataFrame:
        """
        Get historical aggregate bars for an option contract.
        
        Args:
            option_symbol: Full option symbol (e.g., "O:QQQ251024C00600000")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            timespan: Bar size ("minute", "hour", "day")
            multiplier: Bar multiplier (e.g., 5 for 5-minute bars)
            
        Returns:
            DataFrame with OHLCV data
        """
        url = f"{self.base_url}/v2/aggs/ticker/{option_symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}"
        params = {
            "apiKey": self.api_key,
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000  # Max results
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                results = data["results"]
                
                # Convert to DataFrame
                df = pd.DataFrame(results)
                df.rename(columns={
                    "t": "timestamp",
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                    "vw": "vwap",
                    "n": "transactions"
                }, inplace=True)
                
                # Convert timestamp from milliseconds to datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df["option_symbol"] = option_symbol
                
                logger.info("historical_option_prices_retrieved",
                           symbol=option_symbol,
                           rows=len(df),
                           start=start_date,
                           end=end_date)
                return df
            else:
                logger.warning("no_historical_option_data",
                              symbol=option_symbol,
                              start=start_date,
                              end=end_date)
                return pd.DataFrame()
                
        except requests.RequestException as e:
            logger.error("historical_option_prices_failed",
                        error=str(e),
                        symbol=option_symbol)
            return pd.DataFrame()
    
    def download_0dte_options_historic(
        self,
        ticker: str,
        strike: float,
        date: str
    ) -> pd.DataFrame:
        """
        Download historical 0DTE options data for a specific strike.
        
        Args:
            ticker: Underlying ticker (e.g., "QQQ")
            strike: Strike price
            date: Date in YYYY-MM-DD format (should be expiration date)
            
        Returns:
            DataFrame with both CALL and PUT data
        """
        all_data = []
        
        for option_type in ["call", "put"]:
            # Build option symbol
            exp_date = datetime.strptime(date, "%Y-%m-%d")
            exp_str = exp_date.strftime("%y%m%d")
            type_code = "C" if option_type == "call" else "P"
            strike_str = f"{int(strike * 1000):08d}"
            option_symbol = f"O:{ticker}{exp_str}{type_code}{strike_str}"
            
            # Get historical data
            df = self.get_historical_option_prices(
                option_symbol=option_symbol,
                start_date=date,
                end_date=date,
                timespan="minute",
                multiplier=1
            )
            
            if not df.empty:
                df["ticker"] = ticker
                df["option_type"] = option_type.upper()
                df["strike_price"] = strike
                df["expiration_date"] = date
                all_data.append(df)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info("0dte_historic_download_complete",
                       ticker=ticker,
                       strike=strike,
                       date=date,
                       rows=len(combined_df))
            return combined_df
        else:
            logger.warning("no_0dte_data_found", ticker=ticker, strike=strike, date=date)
            return pd.DataFrame()


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download historical options data from Polygon.io")
    parser.add_argument("--ticker", default="QQQ", help="Ticker symbol")
    parser.add_argument("--strike", type=float, required=True, help="Strike price")
    parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    parser.add_argument("--test", action="store_true", help="Test connection only")
    
    args = parser.parse_args()
    
    try:
        client = PolygonHistoricOptions()
        
        if args.test:
            print("✅ Polygon API connection successful!")
            print(f"API Key: {client.api_key[:10]}...")
        else:
            print(f"Downloading {args.ticker} options for strike ${args.strike} on {args.date}...")
            df = client.download_0dte_options_historic(
                ticker=args.ticker,
                strike=args.strike,
                date=args.date
            )
            
            if not df.empty:
                print(f"✅ Downloaded {len(df)} rows")
                print(df.head())
                
                # Save to CSV
                filename = f"polygon_{args.ticker}_{args.date}_strike{int(args.strike)}.csv"
                df.to_csv(filename, index=False)
                print(f"💾 Saved to {filename}")
            else:
                print("❌ No data found")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

