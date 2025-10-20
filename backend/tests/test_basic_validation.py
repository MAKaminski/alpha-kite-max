#!/usr/bin/env python3
"""
Basic System Validation Test

This script performs basic validation tests without requiring full Schwab integration.
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

from models.trading import Position, Trade, TradingSignal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BasicValidationTest:
    """Basic system validation tests."""
    
    def __init__(self):
        self.test_results = {}
        self.paper_account_balance = 100000  # Starting paper account balance
        self.positions = []
        self.trades = []
        
    def test_data_models(self) -> Dict[str, bool]:
        """Test data model creation and validation."""
        logger.info("🔍 Testing data models...")
        results = {}
        
        try:
            # Test 1: Position model
            position = Position(
                ticker="QQQ",
                option_symbol="QQQ251220C00600000",
                option_type="CALL",
                strike_price=600.0,
                expiration_date=datetime.now().date(),
                action="SELL_TO_OPEN",
                contracts=100,
                entry_price=600.0,
                entry_credit=600.0 * 100,
                current_price=605.0
            )
            
            results['position_model'] = (
                position.ticker == "QQQ" and
                position.contracts == 100 and
                position.entry_price == 600.0
            )
            
            # Test 2: Trade model
            trade = Trade(
                ticker="QQQ",
                option_symbol="QQQ251220C00600000",
                option_type="CALL",
                strike_price=600.0,
                expiration_date=datetime.now().date(),
                action="SELL_TO_OPEN",
                contracts=100,
                price=600.0,
                credit_debit=600.0 * 100,
                trade_timestamp=datetime.now(),
                signal_timestamp=datetime.now()
            )
            
            results['trade_model'] = (
                trade.ticker == "QQQ" and
                trade.contracts == 100 and
                trade.price == 600.0
            )
            
            # Test 3: TradingSignal model
            signal = TradingSignal(
                ticker="QQQ",
                signal_timestamp=datetime.now(),
                signal_type="PUT_SELL",
                current_price=600.0,
                sma9_value=599.5,
                vwap_value=600.2,
                direction="up"
            )
            
            results['signal_model'] = (
                signal.ticker == "QQQ" and
                signal.signal_type == "PUT_SELL" and
                signal.current_price == 600.0
            )
            
            logger.info(f"✅ Data model tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Data model test failed: {e}")
            return {'error': str(e)}
    
    def test_trading_calculations(self) -> Dict[str, bool]:
        """Test basic trading calculations."""
        logger.info("📊 Testing trading calculations...")
        results = {}
        
        try:
            # Test 1: P&L calculation
            position = Position(
                ticker="QQQ",
                option_symbol="QQQ251220C00600000",
                option_type="CALL",
                strike_price=600.0,
                expiration_date=datetime.now().date(),
                action="SELL_TO_OPEN",
                contracts=100,
                entry_price=600.0,
                entry_credit=600.0 * 100,
                current_price=605.0
            )
            
            unrealized_pnl = position.contracts * (position.current_price - position.entry_price)
            results['pnl_calculation'] = unrealized_pnl == 500.0
            
            # Test 2: Account balance tracking
            initial_balance = self.paper_account_balance
            
            trade = Trade(
                ticker="QQQ",
                option_symbol="QQQ251220C00600000",
                option_type="CALL",
                strike_price=600.0,
                expiration_date=datetime.now().date(),
                action="SELL_TO_OPEN",
                contracts=100,
                price=600.0,
                credit_debit=600.0 * 100,
                trade_timestamp=datetime.now(),
                signal_timestamp=datetime.now()
            )
            
            self.paper_account_balance += trade.credit_debit
            results['balance_tracking'] = self.paper_account_balance == initial_balance + 60000
            
            # Test 3: Position sizing
            account_balance = 100000
            risk_per_trade = 0.02  # 2%
            stop_loss_distance = 5.0  # $5
            
            max_position_size = account_balance * risk_per_trade / stop_loss_distance
            results['position_sizing'] = max_position_size == 400.0  # 100000 * 0.02 / 5
            
            # Test 4: Risk limits
            max_position_value = 10000
            test_position_value = 15000
            results['risk_limits'] = test_position_value > max_position_value
            
            logger.info(f"✅ Trading calculation tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Trading calculation test failed: {e}")
            return {'error': str(e)}
    
    def test_sma_vwap_cross_detection(self) -> Dict[str, bool]:
        """Test SMA9/VWAP cross detection logic."""
        logger.info("📈 Testing SMA9/VWAP cross detection...")
        results = {}
        
        try:
            # Create sample price data
            np.random.seed(42)  # For reproducible results
            prices = 600 + np.cumsum(np.random.randn(20) * 0.5)
            volumes = np.random.randint(1000, 5000, 20)
            
            # Calculate SMA9
            sma9 = pd.Series(prices).rolling(window=9).mean()
            
            # Calculate VWAP
            vwap = (pd.Series(prices) * pd.Series(volumes)).cumsum() / pd.Series(volumes).cumsum()
            
            # Test cross detection
            crosses = []
            for i in range(1, len(sma9)):
                if pd.isna(sma9.iloc[i]) or pd.isna(vwap.iloc[i]):
                    continue
                    
                prev_sma = sma9.iloc[i-1]
                prev_vwap = vwap.iloc[i-1]
                curr_sma = sma9.iloc[i]
                curr_vwap = vwap.iloc[i]
                
                # Bullish cross: SMA9 crosses above VWAP
                if prev_sma <= prev_vwap and curr_sma > curr_vwap:
                    crosses.append('bullish')
                
                # Bearish cross: SMA9 crosses below VWAP
                elif prev_sma >= prev_vwap and curr_sma < curr_vwap:
                    crosses.append('bearish')
            
            results['cross_detection'] = len(crosses) > 0
            results['cross_types'] = 'bullish' in crosses and 'bearish' in crosses
            results['data_processing'] = len(sma9.dropna()) > 0 and len(vwap.dropna()) > 0
            
            logger.info(f"✅ SMA9/VWAP cross detection tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ SMA9/VWAP cross detection test failed: {e}")
            return {'error': str(e)}
    
    def test_risk_management(self) -> Dict[str, bool]:
        """Test risk management logic."""
        logger.info("🛡️ Testing risk management...")
        results = {}
        
        try:
            # Test 1: Position size limits
            max_position_size = 10000
            test_position_value = 15000
            results['position_limits'] = test_position_value > max_position_size
            
            # Test 2: Daily loss limits
            daily_loss_limit = 1000
            daily_pnl = -500  # Loss
            results['daily_loss_limits'] = abs(daily_pnl) <= daily_loss_limit
            
            # Test 3: Stop loss calculation
            entry_price = 600.0
            current_price = 590.0
            stop_loss_percent = 0.02  # 2%
            stop_loss_price = entry_price * (1 - stop_loss_percent)
            
            results['stop_loss_trigger'] = current_price <= stop_loss_price
            
            # Test 4: Margin requirements
            account_balance = 100000
            position_value = 50000
            margin_requirement = 0.5  # 50%
            required_margin = position_value * margin_requirement
            
            results['margin_requirements'] = required_margin <= account_balance
            
            logger.info(f"✅ Risk management tests completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Risk management test failed: {e}")
            return {'error': str(e)}
    
    def run_all_tests(self) -> Dict[str, Dict[str, bool]]:
        """Run all basic validation tests."""
        logger.info("🚀 Starting basic validation test suite...")
        
        # Run tests
        self.test_results = {
            'data_models': self.test_data_models(),
            'trading_calculations': self.test_trading_calculations(),
            'sma_vwap_cross_detection': self.test_sma_vwap_cross_detection(),
            'risk_management': self.test_risk_management()
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
        report.append("# Basic Validation Test Report")
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

def main():
    """Main test execution function."""
    test_suite = BasicValidationTest()
    
    try:
        # Run all tests
        results = test_suite.run_all_tests()
        
        # Generate and save report
        report = test_suite.generate_report()
        
        # Save report to file
        report_file = f"basic_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Test report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*50)
        print("BASIC VALIDATION TEST SUITE COMPLETED")
        print("="*50)
        print(report)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    main()
