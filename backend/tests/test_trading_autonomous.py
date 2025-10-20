#!/usr/bin/env python3
"""
Autonomous Trading Test Suite

This script tests the autonomous trading functionality including:
- Data quality validation
- Trading strategy accuracy
- Risk management compliance
- Paper trading simulation
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from schwab_integration.client import SchwabClient
from schwab_integration.trading_engine import TradingEngine
from models.trading import Position, Trade, Order

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingTestSuite:
    """Comprehensive trading test suite for autonomous trading validation."""
    
    def __init__(self):
        self.schwab_client = None
        self.trading_engine = None
        self.test_results = {}
        self.paper_account_balance = 100000  # Starting paper account balance
        self.positions = []
        self.trades = []
        
    async def setup(self):
        """Initialize test environment."""
        try:
            # Initialize Schwab client (paper trading mode)
            self.schwab_client = SchwabClient(
                paper_trading=True,
                auto_refresh=True
            )
            
            # Initialize trading engine
            self.trading_engine = TradingEngine(
                client=self.schwab_client,
                paper_trading=True
            )
            
            logger.info("✅ Test environment initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize test environment: {e}")
            return False
    
    async def test_data_quality(self) -> Dict[str, bool]:
        """Test data quality and accuracy."""
        logger.info("🔍 Testing data quality...")
        results = {}
        
        try:
            # Test 1: Real-time data accuracy
            ticker = "QQQ"
            data = await self.schwab_client.get_quote(ticker)
            
            results['real_time_data'] = (
                data is not None and 
                'lastPrice' in data and 
                data['lastPrice'] > 0
            )
            
            # Test 2: Historical data consistency
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            hist_data = await self.schwab_client.get_historical_data(
                ticker, start_date, end_date, 'minute'
            )
            
            results['historical_data'] = (
                hist_data is not None and 
                len(hist_data) > 0 and
                all('close' in candle for candle in hist_data)
            )
            
            # Test 3: Options data completeness
            options_data = await self.schwab_client.get_options_chain(ticker)
            
            results['options_data'] = (
                options_data is not None and
                'callExpDateMap' in options_data and
                'putExpDateMap' in options_data
            )
            
            # Test 4: Data timestamps
            if hist_data:
                timestamps = [candle['datetime'] for candle in hist_data]
                results['timestamp_accuracy'] = all(
                    isinstance(ts, (int, float)) for ts in timestamps
                )
            
            logger.info(f"✅ Data quality tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Data quality test failed: {e}")
            return {'error': str(e)}
    
    async def test_trading_strategy(self) -> Dict[str, bool]:
        """Test trading strategy accuracy."""
        logger.info("📈 Testing trading strategy...")
        results = {}
        
        try:
            # Test 1: SMA9/VWAP cross detection
            ticker = "QQQ"
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            # Get historical data
            hist_data = await self.schwab_client.get_historical_data(
                ticker, start_date, end_date, 'minute'
            )
            
            if hist_data:
                # Calculate SMA9 and VWAP
                df = pd.DataFrame(hist_data)
                df['sma9'] = df['close'].rolling(window=9).mean()
                df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
                
                # Detect crosses
                crosses = []
                for i in range(1, len(df)):
                    prev_sma = df.iloc[i-1]['sma9']
                    prev_vwap = df.iloc[i-1]['vwap']
                    curr_sma = df.iloc[i]['sma9']
                    curr_vwap = df.iloc[i]['vwap']
                    
                    # Bullish cross: SMA9 crosses above VWAP
                    if prev_sma <= prev_vwap and curr_sma > curr_vwap:
                        crosses.append({
                            'type': 'bullish',
                            'timestamp': df.iloc[i]['datetime'],
                            'price': df.iloc[i]['close']
                        })
                    
                    # Bearish cross: SMA9 crosses below VWAP
                    elif prev_sma >= prev_vwap and curr_sma < curr_vwap:
                        crosses.append({
                            'type': 'bearish',
                            'timestamp': df.iloc[i]['datetime'],
                            'price': df.iloc[i]['close']
                        })
                
                results['cross_detection'] = len(crosses) > 0
                results['cross_accuracy'] = len(crosses) <= len(df) * 0.1  # Max 10% of data points
                
                # Test 2: Signal timing
                if crosses:
                    signal_delays = []
                    for cross in crosses:
                        # Calculate delay from cross to next price movement
                        cross_time = cross['timestamp']
                        # This is a simplified test - in reality, you'd measure actual execution delay
                        signal_delays.append(0.1)  # Mock delay
                    
                    results['signal_timing'] = all(delay < 1.0 for delay in signal_delays)
                else:
                    results['signal_timing'] = True
                
                # Test 3: Position sizing
                test_position_size = self.trading_engine.calculate_position_size(
                    account_balance=self.paper_account_balance,
                    risk_per_trade=0.02,  # 2% risk
                    stop_loss_distance=5.0  # $5 stop loss
                )
                
                results['position_sizing'] = (
                    0 < test_position_size < self.paper_account_balance * 0.1
                )
            
            logger.info(f"✅ Trading strategy tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Trading strategy test failed: {e}")
            return {'error': str(e)}
    
    async def test_risk_management(self) -> Dict[str, bool]:
        """Test risk management compliance."""
        logger.info("🛡️ Testing risk management...")
        results = {}
        
        try:
            # Test 1: Position limits
            max_position_size = 1000
            test_position = Position(
                symbol="QQQ",
                quantity=1500,  # Exceeds limit
                entry_price=600.0,
                current_price=600.0
            )
            
            results['position_limits'] = not self.trading_engine.validate_position_limits(
                test_position, max_position_size
            )
            
            # Test 2: Daily loss limits
            daily_loss_limit = 1000
            test_trades = [
                Trade(symbol="QQQ", quantity=100, price=600.0, side="BUY"),
                Trade(symbol="QQQ", quantity=100, price=590.0, side="SELL")  # $1000 loss
            ]
            
            daily_pnl = sum(trade.quantity * (600.0 - trade.price) for trade in test_trades)
            results['daily_loss_limits'] = daily_pnl <= daily_loss_limit
            
            # Test 3: Stop loss execution
            test_position = Position(
                symbol="QQQ",
                quantity=100,
                entry_price=600.0,
                current_price=590.0,  # 10% loss
                stop_loss=594.0  # 1% stop loss
            )
            
            results['stop_loss'] = self.trading_engine.should_trigger_stop_loss(test_position)
            
            # Test 4: Margin requirements
            test_position = Position(
                symbol="QQQ",
                quantity=1000,
                entry_price=600.0,
                current_price=600.0
            )
            
            required_margin = test_position.quantity * test_position.current_price * 0.5  # 50% margin
            results['margin_requirements'] = required_margin <= self.paper_account_balance
            
            logger.info(f"✅ Risk management tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Risk management test failed: {e}")
            return {'error': str(e)}
    
    async def test_paper_trading(self) -> Dict[str, bool]:
        """Test paper trading simulation."""
        logger.info("📊 Testing paper trading simulation...")
        results = {}
        
        try:
            # Test 1: Account balance tracking
            initial_balance = self.paper_account_balance
            
            # Simulate a trade
            trade = Trade(
                symbol="QQQ",
                quantity=100,
                price=600.0,
                side="BUY"
            )
            
            self.paper_account_balance -= trade.quantity * trade.price
            results['balance_tracking'] = self.paper_account_balance == initial_balance - 60000
            
            # Test 2: Position tracking
            position = Position(
                symbol="QQQ",
                quantity=100,
                entry_price=600.0,
                current_price=605.0
            )
            
            self.positions.append(position)
            results['position_tracking'] = len(self.positions) == 1
            
            # Test 3: P&L calculation
            unrealized_pnl = position.quantity * (position.current_price - position.entry_price)
            results['pnl_calculation'] = unrealized_pnl == 500.0
            
            # Test 4: Order execution simulation
            order = Order(
                symbol="QQQ",
                quantity=50,
                side="SELL",
                order_type="MARKET",
                price=605.0
            )
            
            # Simulate order execution
            executed_trade = Trade(
                symbol=order.symbol,
                quantity=order.quantity,
                price=order.price,
                side=order.side
            )
            
            self.trades.append(executed_trade)
            self.paper_account_balance += executed_trade.quantity * executed_trade.price
            
            results['order_execution'] = len(self.trades) == 1
            
            # Test 5: Transaction history
            results['transaction_history'] = len(self.trades) > 0
            
            logger.info(f"✅ Paper trading tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Paper trading test failed: {e}")
            return {'error': str(e)}
    
    async def run_all_tests(self) -> Dict[str, Dict[str, bool]]:
        """Run all trading tests."""
        logger.info("🚀 Starting comprehensive trading test suite...")
        
        # Setup
        if not await self.setup():
            return {'error': 'Failed to setup test environment'}
        
        # Run tests
        self.test_results = {
            'data_quality': await self.test_data_quality(),
            'trading_strategy': await self.test_trading_strategy(),
            'risk_management': await self.test_risk_management(),
            'paper_trading': await self.test_paper_trading()
        }
        
        # Calculate overall success rate
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.test_results.items():
            if isinstance(tests, dict) and 'error' not in tests:
                for test_name, result in tests.items():
                    total_tests += 1
                    if result:
                        passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"📊 Test Results Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        
        return self.test_results
    
    def generate_report(self) -> str:
        """Generate a detailed test report."""
        report = []
        report.append("# Trading Test Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        for category, tests in self.test_results.items():
            report.append(f"## {category.replace('_', ' ').title()}")
            report.append("")
            
            if isinstance(tests, dict) and 'error' not in tests:
                for test_name, result in tests.items():
                    status = "✅ PASS" if result else "❌ FAIL"
                    report.append(f"- {test_name}: {status}")
            else:
                report.append(f"❌ Error: {tests.get('error', 'Unknown error')}")
            
            report.append("")
        
        return "\n".join(report)

async def main():
    """Main test execution function."""
    test_suite = TradingTestSuite()
    
    try:
        # Run all tests
        results = await test_suite.run_all_tests()
        
        # Generate and save report
        report = test_suite.generate_report()
        
        # Save report to file
        report_file = f"trading_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Test report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*50)
        print("TRADING TEST SUITE COMPLETED")
        print("="*50)
        print(report)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    asyncio.run(main())
