"""
Black-Scholes Options Pricing Calculator

Implements the Black-Scholes model for calculating theoretical option prices.
"""

import math
from typing import Dict, Tuple
import structlog

logger = structlog.get_logger()


class BlackScholesCalculator:
    """Black-Scholes options pricing calculator."""
    
    def __init__(self):
        """Initialize the calculator."""
        pass
    
    def calculate_call_price(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float
    ) -> float:
        """
        Calculate Black-Scholes call option price.
        
        Args:
            spot_price: Current stock price
            strike_price: Option strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate (annual)
            volatility: Implied volatility (annual)
            
        Returns:
            Theoretical call option price
        """
        if time_to_expiry <= 0:
            # At expiry, option value is intrinsic value
            return max(0, spot_price - strike_price)
        
        # Calculate d1 and d2
        d1 = self._calculate_d1(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility)
        d2 = self._calculate_d2(d1, volatility, time_to_expiry)
        
        # Calculate option price
        call_price = (
            spot_price * self._cumulative_normal_distribution(d1) -
            strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._cumulative_normal_distribution(d2)
        )
        
        return max(0, call_price)  # Option price cannot be negative
    
    def calculate_put_price(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float
    ) -> float:
        """
        Calculate Black-Scholes put option price.
        
        Args:
            spot_price: Current stock price
            strike_price: Option strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate (annual)
            volatility: Implied volatility (annual)
            
        Returns:
            Theoretical put option price
        """
        if time_to_expiry <= 0:
            # At expiry, option value is intrinsic value
            return max(0, strike_price - spot_price)
        
        # Calculate d1 and d2
        d1 = self._calculate_d1(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility)
        d2 = self._calculate_d2(d1, volatility, time_to_expiry)
        
        # Calculate option price using put-call parity
        call_price = self.calculate_call_price(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility)
        put_price = call_price - spot_price + strike_price * math.exp(-risk_free_rate * time_to_expiry)
        
        return max(0, put_price)  # Option price cannot be negative
    
    def calculate_greeks(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str
    ) -> Dict[str, float]:
        """
        Calculate option Greeks (Delta, Gamma, Theta, Vega).
        
        Args:
            spot_price: Current stock price
            strike_price: Option strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate (annual)
            volatility: Implied volatility (annual)
            option_type: 'call' or 'put'
            
        Returns:
            Dictionary with Greeks values
        """
        if time_to_expiry <= 0:
            return {
                'delta': 1.0 if option_type == 'call' and spot_price > strike_price else 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0
            }
        
        # Calculate d1 and d2
        d1 = self._calculate_d1(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility)
        d2 = self._calculate_d2(d1, volatility, time_to_expiry)
        
        # Calculate standard normal probability density
        pdf_d1 = self._normal_probability_density(d1)
        
        # Delta
        if option_type.lower() == 'call':
            delta = self._cumulative_normal_distribution(d1)
        else:  # put
            delta = self._cumulative_normal_distribution(d1) - 1
        
        # Gamma (same for calls and puts)
        gamma = pdf_d1 / (spot_price * volatility * math.sqrt(time_to_expiry))
        
        # Theta
        theta_part1 = -(spot_price * pdf_d1 * volatility) / (2 * math.sqrt(time_to_expiry))
        if option_type.lower() == 'call':
            theta_part2 = -risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._cumulative_normal_distribution(d2)
        else:  # put
            theta_part2 = risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * self._cumulative_normal_distribution(-d2)
        
        theta = theta_part1 + theta_part2
        
        # Vega (same for calls and puts)
        vega = spot_price * pdf_d1 * math.sqrt(time_to_expiry) / 100  # Divide by 100 for percentage change
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega
        }
    
    def _calculate_d1(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float
    ) -> float:
        """Calculate d1 parameter for Black-Scholes model."""
        numerator = (
            math.log(spot_price / strike_price) +
            (risk_free_rate + 0.5 * volatility * volatility) * time_to_expiry
        )
        denominator = volatility * math.sqrt(time_to_expiry)
        return numerator / denominator
    
    def _calculate_d2(self, d1: float, volatility: float, time_to_expiry: float) -> float:
        """Calculate d2 parameter for Black-Scholes model."""
        return d1 - volatility * math.sqrt(time_to_expiry)
    
    def _cumulative_normal_distribution(self, x: float) -> float:
        """
        Approximate cumulative normal distribution using the error function.
        
        This is a simplified approximation. For production use, consider using
        scipy.stats.norm.cdf for higher accuracy.
        """
        # Using Abramowitz and Stegun approximation
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _normal_probability_density(self, x: float) -> float:
        """Calculate normal probability density function."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


# Example usage and testing
if __name__ == "__main__":
    calculator = BlackScholesCalculator()
    
    # Example parameters
    spot_price = 600.0
    strike_price = 600.0
    time_to_expiry = 1.0 / 365  # 1 day
    risk_free_rate = 0.05  # 5%
    volatility = 0.20  # 20%
    
    # Calculate prices
    call_price = calculator.calculate_call_price(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility)
    put_price = calculator.calculate_put_price(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility)
    
    # Calculate Greeks for call
    call_greeks = calculator.calculate_greeks(spot_price, strike_price, time_to_expiry, risk_free_rate, volatility, 'call')
    
    print(f"Call Price: ${call_price:.2f}")
    print(f"Put Price: ${put_price:.2f}")
    print(f"Call Greeks: {call_greeks}")
