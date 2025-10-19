"""
Synthetic Options Data Generator

Generates synthetic options data using Black-Scholes model for backtesting
and development when real options data is unavailable.
"""

import os
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import structlog
from dotenv import load_dotenv

from .calculator import BlackScholesCalculator
from supabase_client import SupabaseClient

load_dotenv()
logger = structlog.get_logger()


class SyntheticOptionsGenerator:
    """Generates synthetic options data using Black-Scholes model."""
    
    def __init__(self):
        """Initialize the synthetic data generator."""
        self.calculator = BlackScholesCalculator()
        self.supabase_client = SupabaseClient()
        
        # Market parameters
        self.risk_free_rate = 0.05  # 5% annual risk-free rate
        self.base_volatility = 0.20  # 20% base volatility
        
        logger.info("synthetic_options_generator_initialized")
    
    def generate_0dte_options_for_date(
        self,
        date: datetime,
        ticker: str = "QQQ",
        base_price: float = 600.0,
        strike_range: float = 50.0,
        strike_increment: float = 5.0,
        time_intervals: int = 60
    ) -> pd.DataFrame:
        """
        Generate 0DTE options data for a specific date.
        
        Args:
            date: Date to generate options for
            ticker: Stock ticker symbol
            base_price: Base stock price for the day
            strike_range: Range around base price for strikes
            strike_increment: Increment between strikes
            time_intervals: Number of time intervals during the day
            
        Returns:
            DataFrame with synthetic options data
        """
        # Generate strike prices
        strikes = self._generate_strike_prices(base_price, strike_range, strike_increment)
        
        # Generate time intervals throughout the trading day
        time_points = self._generate_time_intervals(date, time_intervals)
        
        # Generate price movements (random walk)
        price_movements = self._generate_price_movements(base_price, len(time_points))
        
        all_data = []
        
        for i, (timestamp, spot_price) in enumerate(zip(time_points, price_movements)):
            # Calculate time to expiry (decreasing throughout the day)
            time_to_expiry = self._calculate_time_to_expiry(timestamp, date)
            
            # Calculate volatility (can vary throughout the day)
            volatility = self._calculate_volatility(spot_price, base_price, time_to_expiry)
            
            for strike in strikes:
                # Generate both call and put options
                for option_type in ['call', 'put']:
                    # Calculate theoretical price
                    if option_type == 'call':
                        theoretical_price = self.calculator.calculate_call_price(
                            spot_price, strike, time_to_expiry, self.risk_free_rate, volatility
                        )
                    else:
                        theoretical_price = self.calculator.calculate_put_price(
                            spot_price, strike, time_to_expiry, self.risk_free_rate, volatility
                        )
                    
                    # Calculate Greeks
                    greeks = self.calculator.calculate_greeks(
                        spot_price, strike, time_to_expiry, self.risk_free_rate, volatility, option_type
                    )
                    
                    # Add some realistic market noise
                    market_noise = np.random.normal(0, theoretical_price * 0.02)  # 2% noise
                    market_price = max(0.01, theoretical_price + market_noise)
                    
                    # Generate realistic bid/ask spread
                    spread = max(0.01, market_price * 0.01)  # 1% spread
                    bid = market_price - spread / 2
                    ask = market_price + spread / 2
                    
                    # Generate volume and open interest
                    volume = np.random.poisson(100) if theoretical_price > 0.05 else 0
                    open_interest = np.random.poisson(1000)
                    
                    # Create option symbol
                    option_symbol = self._create_option_symbol(ticker, date, strike, option_type)
                    
                    all_data.append({
                        'timestamp': timestamp,
                        'ticker': ticker,
                        'option_symbol': option_symbol,
                        'option_type': option_type.upper(),
                        'strike_price': strike,
                        'expiration_date': date.date(),
                        'spot_price': spot_price,
                        'theoretical_price': theoretical_price,
                        'market_price': market_price,
                        'bid': bid,
                        'ask': ask,
                        'volume': volume,
                        'open_interest': open_interest,
                        'implied_volatility': volatility,
                        'delta': greeks['delta'],
                        'gamma': greeks['gamma'],
                        'theta': greeks['theta'],
                        'vega': greeks['vega'],
                        'time_to_expiry': time_to_expiry,
                        'data_source': 'black_scholes_synthetic',
                        'risk_free_rate': self.risk_free_rate
                    })
        
        df = pd.DataFrame(all_data)
        logger.info("synthetic_0dte_options_generated",
                   date=date.date(),
                   ticker=ticker,
                   rows=len(df),
                   strikes=len(strikes),
                   time_points=len(time_points))
        
        return df
    
    def generate_october_2025_data(
        self,
        ticker: str = "QQQ",
        base_price: float = 600.0
    ) -> pd.DataFrame:
        """
        Generate synthetic options data for the entire month of October 2025.
        
        Args:
            ticker: Stock ticker symbol
            base_price: Starting base price
            
        Returns:
            DataFrame with all October 2025 synthetic options data
        """
        # Generate dates for October 2025 (weekdays only)
        start_date = datetime(2025, 10, 1)
        end_date = datetime(2025, 10, 31)
        
        october_dates = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                october_dates.append(current_date)
            current_date += timedelta(days=1)
        
        all_data = []
        current_price = base_price
        
        for date in october_dates:
            # Generate some daily price movement
            daily_return = np.random.normal(0, 0.02)  # 2% daily volatility
            current_price *= (1 + daily_return)
            
            # Generate options data for this date
            daily_data = self.generate_0dte_options_for_date(
                date=date,
                ticker=ticker,
                base_price=current_price,
                strike_range=50.0,
                strike_increment=5.0,
                time_intervals=60
            )
            
            all_data.append(daily_data)
        
        combined_df = pd.concat(all_data, ignore_index=True)
        
        logger.info("synthetic_october_2025_data_generated",
                   ticker=ticker,
                   total_rows=len(combined_df),
                   trading_days=len(october_dates))
        
        return combined_df
    
    def save_to_database(self, df: pd.DataFrame, table_name: str = "synthetic_option_prices") -> bool:
        """
        Save synthetic options data to database.
        
        Args:
            df: DataFrame with synthetic options data
            table_name: Name of the table to save to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert DataFrame to list of dictionaries
            data = df.to_dict('records')
            
            # Save to Supabase
            result = self.supabase_client.supabase.table(table_name).insert(data).execute()
            
            logger.info("synthetic_options_data_saved",
                       table=table_name,
                       rows=len(data))
            
            return True
            
        except Exception as e:
            logger.error("synthetic_options_data_save_failed",
                        error=str(e),
                        table=table_name)
            return False
    
    def _generate_strike_prices(self, base_price: float, range: float, increment: float) -> List[float]:
        """Generate strike prices around the base price."""
        strikes = []
        start_strike = base_price - range
        end_strike = base_price + range
        
        current_strike = start_strike
        while current_strike <= end_strike:
            strikes.append(round(current_strike, 2))
            current_strike += increment
        
        return strikes
    
    def _generate_time_intervals(self, date: datetime, intervals: int) -> List[datetime]:
        """Generate time intervals throughout the trading day."""
        # Trading hours: 9:30 AM to 4:00 PM ET
        start_time = datetime.combine(date.date(), time(9, 30))
        end_time = datetime.combine(date.date(), time(16, 0))
        
        time_points = []
        current_time = start_time
        interval_minutes = (end_time - start_time).total_seconds() / 60 / intervals
        
        while current_time <= end_time:
            time_points.append(current_time)
            current_time += timedelta(minutes=interval_minutes)
        
        return time_points
    
    def _generate_price_movements(self, base_price: float, num_points: int) -> List[float]:
        """Generate realistic price movements using random walk."""
        # Generate random returns
        returns = np.random.normal(0, 0.001, num_points)  # 0.1% volatility per interval
        
        # Calculate cumulative price movements
        prices = [base_price]
        for i in range(1, num_points):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(max(0.01, new_price))  # Ensure positive prices
        
        return prices
    
    def _calculate_time_to_expiry(self, current_time: datetime, expiry_date: datetime) -> float:
        """Calculate time to expiry in years."""
        # For 0DTE options, expiry is at market close (4:00 PM)
        expiry_time = datetime.combine(expiry_date.date(), time(16, 0))
        
        if current_time >= expiry_time:
            return 0.0
        
        time_diff = expiry_time - current_time
        return time_diff.total_seconds() / (365 * 24 * 3600)  # Convert to years
    
    def _calculate_volatility(self, spot_price: float, base_price: float, time_to_expiry: float) -> float:
        """Calculate dynamic volatility based on price movement and time to expiry."""
        # Base volatility
        volatility = self.base_volatility
        
        # Increase volatility as we approach expiry (volatility smile)
        if time_to_expiry < 1.0 / 365:  # Less than 1 day
            volatility *= 1.5
        
        # Increase volatility for larger price movements
        price_change = abs(spot_price - base_price) / base_price
        if price_change > 0.02:  # More than 2% move
            volatility *= 1.2
        
        return volatility
    
    def _create_option_symbol(self, ticker: str, expiry_date: datetime, strike: float, option_type: str) -> str:
        """Create option symbol in standard format."""
        # Format: TICKERYYMMDDC/P00000000
        exp_str = expiry_date.strftime("%y%m%d")
        type_code = "C" if option_type == "call" else "P"
        strike_str = f"{int(strike * 1000):08d}"
        
        return f"{ticker}{exp_str}{type_code}{strike_str}"


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic options data using Black-Scholes model")
    parser.add_argument("--date", help="Date to generate data for (YYYY-MM-DD)")
    parser.add_argument("--ticker", default="QQQ", help="Ticker symbol")
    parser.add_argument("--october", action="store_true", help="Generate data for entire October 2025")
    parser.add_argument("--save", action="store_true", help="Save to database")
    parser.add_argument("--base-price", type=float, default=600.0, help="Base stock price")
    
    args = parser.parse_args()
    
    try:
        generator = SyntheticOptionsGenerator()
        
        if args.october:
            print("Generating synthetic options data for October 2025...")
            df = generator.generate_october_2025_data(
                ticker=args.ticker,
                base_price=args.base_price
            )
            
            print(f"✅ Generated {len(df)} rows of synthetic options data")
            print(f"📊 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"📈 Strike range: ${df['strike_price'].min():.2f} to ${df['strike_price'].max():.2f}")
            
            if args.save:
                if generator.save_to_database(df):
                    print("💾 Data saved to database successfully")
                else:
                    print("❌ Failed to save data to database")
            else:
                # Save to CSV
                filename = f"synthetic_options_october_2025_{args.ticker}.csv"
                df.to_csv(filename, index=False)
                print(f"💾 Saved to {filename}")
        
        else:
            if not args.date:
                print("❌ Error: --date required (or use --october)")
                exit(1)
            
            date = datetime.strptime(args.date, "%Y-%m-%d")
            print(f"Generating synthetic options data for {args.ticker} on {args.date}...")
            
            df = generator.generate_0dte_options_for_date(
                date=date,
                ticker=args.ticker,
                base_price=args.base_price
            )
            
            print(f"✅ Generated {len(df)} rows of synthetic options data")
            print(df.head())
            
            if args.save:
                if generator.save_to_database(df):
                    print("💾 Data saved to database successfully")
                else:
                    print("❌ Failed to save data to database")
            else:
                # Save to CSV
                filename = f"synthetic_options_{args.ticker}_{args.date}.csv"
                df.to_csv(filename, index=False)
                print(f"💾 Saved to {filename}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
