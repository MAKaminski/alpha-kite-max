"""AWS Lambda function for real-time equity data streaming."""

import os
import sys
import json
from datetime import datetime, time
from pathlib import Path
import structlog
import pytz

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schwab_integration.client import SchwabClient
from schwab_integration.downloader import EquityDownloader
from schwab_integration.config import SchwabConfig, SupabaseConfig
from supabase_client import SupabaseClient
from token_manager import TokenManager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def process_option_chains(option_data: dict, ticker: str, timestamp: str, current_price: float):
    """Process option chain data to extract nearest ATM strike for 0DTE options.
    
    Args:
        option_data: Raw option chain data from Schwab API
        ticker: Stock ticker symbol
        timestamp: Current timestamp
        current_price: Current stock price
        
    Returns:
        DataFrame with option prices for nearest strike (both CALL and PUT)
    """
    import pandas as pd
    from datetime import date
    
    try:
        # Find nearest strike price (round to nearest $5 for QQQ)
        nearest_strike = round(current_price / 5) * 5
        
        # Get today's date for 0DTE options
        today = date.today()
        expiration_str = today.strftime('%Y-%m-%d')
        
        options_list = []
        
        # Process CALL and PUT maps
        for option_type in ['callExpDateMap', 'putExpDateMap']:
            if option_type not in option_data:
                continue
                
            exp_map = option_data[option_type]
            opt_type = 'CALL' if option_type == 'callExpDateMap' else 'PUT'
            
            # Find options for today's expiration
            for exp_date, strikes in exp_map.items():
                # Schwab format: "2025-10-16:0" (date:days to expiration)
                exp_date_only = exp_date.split(':')[0]
                
                if exp_date_only != expiration_str:
                    continue
                    
                # Find nearest strike
                strike_key = f'{nearest_strike:.1f}'
                if strike_key in strikes:
                    option_chain = strikes[strike_key][0]  # Get first option contract
                    
                    options_list.append({
                        'ticker': ticker,
                        'timestamp': timestamp,
                        'option_type': opt_type,
                        'strike_price': nearest_strike,
                        'expiration_date': exp_date_only,
                        'bid': option_chain.get('bid', 0),
                        'ask': option_chain.get('ask', 0),
                        'last': option_chain.get('last', 0),
                        'volume': option_chain.get('totalVolume', 0),
                        'open_interest': option_chain.get('openInterest', 0),
                        'implied_volatility': option_chain.get('volatility', 0),
                        'delta': option_chain.get('delta', 0),
                        'gamma': option_chain.get('gamma', 0),
                        'theta': option_chain.get('theta', 0),
                        'vega': option_chain.get('vega', 0)
                    })
        
        return pd.DataFrame(options_list)
        
    except Exception as e:
        logger.error("process_option_chains_error", error=str(e))
        return pd.DataFrame()


def is_market_open() -> bool:
    """Check if market is currently open (9:30 AM - 4:00 PM ET, weekdays).
    
    Returns:
        True if market is open, False otherwise
    """
    # Get current time in EST
    est = pytz.timezone('America/New_York')
    now_est = datetime.now(est)
    
    # Check if weekday (Monday=0, Sunday=6)
    if now_est.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if within market hours (9:30 AM - 4:00 PM)
    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = now_est.time()
    
    is_open = market_open <= current_time < market_close
    
    logger.info(
        "market_hours_check",
        current_time=current_time.isoformat(),
        is_open=is_open,
        day_of_week=now_est.strftime('%A')
    )
    
    return is_open


def lambda_handler(event, context):
    """Lambda function triggered every minute during market hours.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Response with status and metrics
    """
    logger.info("lambda_invoked", lambda_event=event)
    
    try:
        # Check if market is open
        if not is_market_open():
            logger.info("market_closed", message="Skipping data fetch - market is closed")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Market is closed',
                    'skipped': True
                })
            }
        
        # Get configuration from environment variables
        ticker = os.environ.get('DEFAULT_TICKER', 'QQQ')
        
        # Initialize token manager
        token_manager = TokenManager(
            secret_name=os.environ.get('SCHWAB_TOKEN_SECRET', 'schwab-api-token'),
            region=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Initialize Schwab client
        schwab_config = SchwabConfig(
            app_key=os.environ['SCHWAB_APP_KEY'],
            app_secret=os.environ['SCHWAB_APP_SECRET'],
            callback_url=os.environ.get('SCHWAB_CALLBACK_URL', 'https://localhost:8000/callback'),
            token_path='/tmp/schwab_token.json'  # Lambda temp storage
        )
        
        # Check if token needs refresh
        token_data = token_manager.get_token()
        if token_data:
            # Save token to temp file for schwab-py to use
            with open(schwab_config.token_path, 'w') as f:
                json.dump(token_data, f)
            
            if token_manager.token_needs_refresh(token_data):
                logger.info("refreshing_expired_token")
                schwab_client = SchwabClient(schwab_config)
                token_manager.refresh_token(schwab_client)
        else:
            logger.error("no_token_found", message="Schwab token not found in Secrets Manager")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Token not found',
                    'message': 'Please initialize Schwab token in Secrets Manager'
                })
            }
        
        schwab_client = SchwabClient(schwab_config)
        
        # Initialize Supabase client
        supabase_config = SupabaseConfig(
            url=os.environ['SUPABASE_URL'],
            service_role_key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
        )
        supabase_client = SupabaseClient(supabase_config)
        
        # Initialize downloader
        downloader = EquityDownloader(schwab_client)
        
        # Download last 1 day of data (which includes latest minute)
        logger.info("downloading_latest_data", ticker=ticker)
        df = downloader.download_minute_data(ticker, days=1)
        
        if df.empty:
            logger.warning("no_data_downloaded", ticker=ticker)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No data available',
                    'ticker': ticker,
                    'data_points': 0
                })
            }
        
        # Filter to only the last minute of data to avoid duplicates
        # This ensures we only upsert the most recent data point
        latest_timestamp = df['timestamp'].max()
        latest_df = df[df['timestamp'] == latest_timestamp].copy()
        
        logger.info(
            "data_downloaded",
            ticker=ticker,
            total_points=len(df),
            latest_points=len(latest_df),
            latest_timestamp=latest_timestamp
        )
        
        # Upload equity data
        equity_success = supabase_client.upsert_equity_data(latest_df)
        
        if not equity_success:
            logger.error("equity_upload_failed", ticker=ticker)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to upload equity data',
                    'ticker': ticker
                })
            }
        
        # Calculate and upload indicators
        indicators = downloader.calculate_indicators(df)  # Calculate on full day for accurate SMA9/VWAP
        
        if not indicators.empty:
            # Filter to latest indicator values
            latest_indicators = indicators[indicators['timestamp'] == latest_timestamp].copy()
            
            indicators_success = supabase_client.upsert_indicators(latest_indicators)
            
            if not indicators_success:
                logger.error("indicators_upload_failed", ticker=ticker)
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Failed to upload indicators',
                        'ticker': ticker
                    })
                }
            
            logger.info(
                "data_uploaded_successfully",
                ticker=ticker,
                equity_rows=len(latest_df),
                indicator_rows=len(latest_indicators)
            )
        
        # Download and upload option chain data (0DTE options for nearest strike)
        option_rows = 0
        try:
            current_price = latest_df['price'].iloc[0]
            logger.info("downloading_option_chains", ticker=ticker, current_price=current_price)
            
            # Get 0DTE option chains
            option_data = schwab_client.get_option_chains(ticker)
            
            if option_data:
                # Process and upload option data
                option_df = process_option_chains(option_data, ticker, latest_timestamp, current_price)
                
                if not option_df.empty:
                    option_success = supabase_client.upsert_option_prices(option_df)
                    
                    if option_success:
                        option_rows = len(option_df)
                        logger.info("option_data_uploaded", ticker=ticker, option_rows=option_rows)
                    else:
                        logger.warning("option_upload_failed", ticker=ticker)
        except Exception as e:
            logger.warning("option_download_error", error=str(e), ticker=ticker)
            # Don't fail the entire Lambda if option download fails
        
        # Return success
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data fetched and uploaded successfully',
                'ticker': ticker,
                'timestamp': latest_timestamp,
                'equity_rows': len(latest_df),
                'indicator_rows': len(latest_indicators) if not indicators.empty else 0,
                'option_rows': option_rows
            })
        }
        
    except Exception as e:
        logger.error("lambda_execution_error", error=str(e), error_type=type(e).__name__)
        import traceback
        logger.error("traceback", trace=traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'error_type': type(e).__name__
            })
        }

