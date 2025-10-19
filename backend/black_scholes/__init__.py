"""
Black-Scholes Options Pricing Calculator

Provides synthetic options data generation using Black-Scholes model
for backtesting and development when real options data is unavailable.
"""

from .calculator import BlackScholesCalculator
from .synthetic_generator import SyntheticOptionsGenerator

__all__ = ['BlackScholesCalculator', 'SyntheticOptionsGenerator']
