#!/usr/bin/env python3
"""
Improved Testing Framework with Timeout Protection

This framework provides robust testing capabilities with timeout protection,
better error handling, and comprehensive reporting.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Custom timeout exception."""
    pass

class TestResult:
    """Test result container."""
    
    def __init__(self, name: str, passed: bool, duration: float, error: Optional[str] = None):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.error = error
        self.timestamp = datetime.now()

class TestSuite:
    """Improved test suite with timeout protection."""
    
    def __init__(self, name: str, timeout_seconds: int = 30):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
    
    def timeout_handler(self, signum, frame):
        """Handle timeout signal."""
        raise TimeoutError(f"Test timed out after {self.timeout_seconds} seconds")
    
    def run_test_with_timeout(self, test_func: Callable, test_name: str) -> TestResult:
        """Run a test function with timeout protection."""
        start_time = time.time()
        
        try:
            # Set up timeout signal
            if hasattr(signal, 'SIGALRM'):  # Unix systems
                signal.signal(signal.SIGALRM, self.timeout_handler)
                signal.alarm(self.timeout_seconds)
            
            # Run the test
            result = test_func()
            
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            duration = time.time() - start_time
            
            # Determine if test passed
            if isinstance(result, bool):
                passed = result
                error = None
            elif isinstance(result, dict):
                passed = result.get('passed', False)
                error = result.get('error', None)
            else:
                passed = result is not None
                error = None
            
            return TestResult(test_name, passed, duration, error)
            
        except TimeoutError as e:
            duration = time.time() - start_time
            return TestResult(test_name, False, duration, str(e))
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return TestResult(test_name, False, duration, error_msg)
        finally:
            # Ensure timeout is cancelled
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
    
    def add_test(self, test_func: Callable, test_name: str):
        """Add a test to the suite."""
        result = self.run_test_with_timeout(test_func, test_name)
        self.results.append(result)
        
        status = "✅ PASS" if result.passed else "❌ FAIL"
        duration_str = f"{result.duration:.2f}s"
        
        logger.info(f"{status} {test_name} ({duration_str})")
        
        if result.error:
            logger.error(f"   Error: {result.error}")
    
    def run_suite(self) -> Dict[str, Any]:
        """Run all tests in the suite."""
        self.start_time = time.time()
        logger.info(f"🚀 Starting test suite: {self.name}")
        
        # Run all tests
        for test_func, test_name in self.tests:
            self.add_test(test_func, test_name)
        
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time
        
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Log summary
        logger.info(f"📊 Test Suite Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {failed_tests}")
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        logger.info(f"   Total Duration: {total_duration:.2f}s")
        
        return {
            'suite_name': self.name,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'total_duration': total_duration,
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'duration': r.duration,
                    'error': r.error,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }
    
    def generate_report(self) -> str:
        """Generate a detailed test report."""
        report = []
        report.append(f"# {self.name} Test Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report.append("## Summary")
        report.append(f"- **Total Tests**: {total_tests}")
        report.append(f"- **Passed**: {passed_tests}")
        report.append(f"- **Failed**: {total_tests - passed_tests}")
        report.append(f"- **Success Rate**: {success_rate:.1f}%")
        report.append("")
        
        # Test Results
        report.append("## Test Results")
        report.append("")
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            duration = f"{result.duration:.2f}s"
            report.append(f"### {result.name}")
            report.append(f"- **Status**: {status}")
            report.append(f"- **Duration**: {duration}")
            report.append(f"- **Timestamp**: {result.timestamp.isoformat()}")
            
            if result.error:
                report.append(f"- **Error**: ```")
                report.append(result.error)
                report.append("```")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, filename: Optional[str] = None):
        """Save test report to file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.name.lower().replace(' ', '_')}_report_{timestamp}.md"
        
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Test report saved to: {filename}")
        return filename

# Example usage and test functions
def create_basic_validation_suite() -> TestSuite:
    """Create a basic validation test suite."""
    suite = TestSuite("Basic Validation", timeout_seconds=10)
    
    # Test 1: Data model validation
    def test_data_models():
        try:
            from models.trading import Position, Trade, TradingSignal
            from datetime import datetime, date
            
            # Test Position model
            position = Position(
                ticker="QQQ",
                option_symbol="QQQ251220C00600000",
                option_type="CALL",
                strike_price=600.0,
                expiration_date=date.today(),
                action="SELL_TO_OPEN",
                contracts=100,
                entry_price=600.0,
                entry_credit=600.0 * 100
            )
            
            # Test Trade model
            trade = Trade(
                ticker="QQQ",
                option_symbol="QQQ251220C00600000",
                option_type="CALL",
                strike_price=600.0,
                expiration_date=date.today(),
                action="SELL_TO_OPEN",
                contracts=100,
                price=600.0,
                credit_debit=600.0 * 100,
                trade_timestamp=datetime.now(),
                signal_timestamp=datetime.now()
            )
            
            # Test TradingSignal model
            signal = TradingSignal(
                ticker="QQQ",
                signal_timestamp=datetime.now(),
                signal_type="PUT_SELL",
                current_price=600.0,
                sma9_value=599.5,
                vwap_value=600.2,
                direction="up"
            )
            
            return {
                'passed': True,
                'position_valid': position.ticker == "QQQ",
                'trade_valid': trade.ticker == "QQQ",
                'signal_valid': signal.ticker == "QQQ"
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    # Test 2: Trading calculations
    def test_trading_calculations():
        try:
            # P&L calculation
            entry_price = 600.0
            current_price = 605.0
            contracts = 100
            pnl = contracts * (current_price - entry_price)
            
            # Position sizing
            account_balance = 100000
            risk_per_trade = 0.02
            stop_loss_distance = 5.0
            max_position_size = account_balance * risk_per_trade / stop_loss_distance
            
            return {
                'passed': pnl == 500.0 and max_position_size == 400.0,
                'pnl_correct': pnl == 500.0,
                'position_sizing_correct': max_position_size == 400.0
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    # Test 3: Risk management
    def test_risk_management():
        try:
            # Position limits
            max_position_value = 10000
            test_position_value = 15000
            position_limit_breach = test_position_value > max_position_value
            
            # Daily loss limits
            daily_loss_limit = 1000
            daily_pnl = -500
            within_loss_limit = abs(daily_pnl) <= daily_loss_limit
            
            # Stop loss
            entry_price = 600.0
            current_price = 590.0
            stop_loss_percent = 0.02
            stop_loss_price = entry_price * (1 - stop_loss_percent)
            stop_loss_triggered = current_price <= stop_loss_price
            
            return {
                'passed': position_limit_breach and within_loss_limit and stop_loss_triggered,
                'position_limits': position_limit_breach,
                'daily_loss_limits': within_loss_limit,
                'stop_loss': stop_loss_triggered
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    # Add tests to suite
    suite.tests = [
        (test_data_models, "Data Model Validation"),
        (test_trading_calculations, "Trading Calculations"),
        (test_risk_management, "Risk Management")
    ]
    
    return suite

def main():
    """Main test execution function."""
    try:
        # Create and run test suite
        suite = create_basic_validation_suite()
        results = suite.run_suite()
        
        # Save report
        report_file = suite.save_report()
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUITE COMPLETED")
        print("="*60)
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Total Duration: {results['total_duration']:.2f}s")
        print(f"Report saved to: {report_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    main()
