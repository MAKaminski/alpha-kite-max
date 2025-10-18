#!/usr/bin/env python3
"""Test paper trading connectivity with Schwab API."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import structlog
from schwab_integration.client import SchwabClient
from schwab_integration.config import SchwabConfig

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def main():
    """Test paper trading account access."""
    print("\n🔍 Testing Schwab Paper Trading Account Access\n")
    
    try:
        # Initialize Schwab client
        config = SchwabConfig()
        client = SchwabClient(config)
        
        # Test 1: Get account information
        print("1. Fetching account information...")
        account_info = client.get_account_info()
        
        if account_info:
            print(f"   ✓ Account found!")
            print(f"   Account ID: {account_info.get('accountNumber', 'N/A')}")
            print(f"   Account Type: {account_info.get('type', 'N/A')}")
            print(f"   Is Paper Trading: {config.paper}")
        else:
            print("   ✗ No account information retrieved")
            return 1
        
        # Test 2: Get option chains (to verify we can access options data)
        print("\n2. Testing option chain access for QQQ...")
        option_chains = client.get_option_chains("QQQ", "PUT")
        
        if option_chains:
            print("   ✓ Option chains retrieved successfully")
            exp_dates = list(option_chains.get('putExpDateMap', {}).keys())
            if exp_dates:
                print(f"   Available expiration dates: {len(exp_dates)}")
                print(f"   First expiration: {exp_dates[0] if exp_dates else 'N/A'}")
        else:
            print("   ✗ Failed to retrieve option chains")
        
        print("\n✅ Paper trading connectivity test completed!")
        print("\n📋 Configuration:")
        print(f"   Paper Mode: {config.paper}")
        print(f"   Account ID: {config.account_id or account_info.get('accountNumber', 'Not set')}")
        print(f"   Base URL: {config.base_url}")
        
        print("\n💡 To place paper trades:")
        print("   1. Ensure SCHWAB_PAPER=true in .env")
        print("   2. Set SCHWAB_ACCOUNT_ID to your paper account number")
        print("   3. Use the trading engine to execute strategy trades")
        
        return 0
        
    except Exception as e:
        logger.error("paper_trading_test_failed", error=str(e))
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

