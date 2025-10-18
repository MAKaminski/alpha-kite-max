#!/usr/bin/env python3
"""
Script to refresh Schwab API authentication.
Run this when you get InvalidTokenError.
"""

import sys
from pathlib import Path
import os

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.config import SchwabConfig
from schwab import auth, client
import structlog

logger = structlog.get_logger()


def refresh_authentication():
    """Refresh Schwab API authentication."""
    
    print("=" * 80)
    print("SCHWAB API AUTHENTICATION REFRESH")
    print("=" * 80)
    
    # Load config
    config = SchwabConfig()
    
    print(f"\n📋 Configuration:")
    print(f"   App Key: {config.app_key[:10]}...")
    print(f"   Callback URL: {config.callback_url}")
    print(f"   Token Path: {config.token_path}")
    
    # Check if token file exists
    token_file = Path(config.token_path)
    if token_file.exists():
        print(f"\n⚠️  Existing token file found: {token_file}")
        response = input("   Delete and re-authenticate? (y/n): ")
        if response.lower() == 'y':
            token_file.unlink()
            print("   ✅ Old token deleted")
        else:
            print("   Keeping existing token")
            return
    
    print("\n🔐 Starting OAuth authentication flow...")
    print("\nIMPORTANT STEPS:")
    print("1. A browser window will open")
    print("2. Log in to your Schwab account")
    print("3. Authorize the application")
    print("4. You will be redirected to a URL")
    print("5. Copy the ENTIRE URL from your browser")
    print("6. Paste it here when prompted")
    
    input("\nPress Enter when ready to continue...")
    
    try:
        # Create token directory if it doesn't exist
        token_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Start OAuth flow
        schwab_client = auth.client_from_login_flow(
            api_key=config.app_key,
            app_secret=config.app_secret,
            callback_url=config.callback_url,
            token_path=str(token_file),
            asyncio=False
        )
        
        if schwab_client:
            print("\n✅ Authentication successful!")
            print(f"   Token saved to: {token_file}")
            
            # Test the connection
            print("\n🧪 Testing connection...")
            response = schwab_client.get_quote("QQQ")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Connection test successful!")
                print(f"   QQQ Price: ${data.get('QQQ', {}).get('quote', {}).get('lastPrice', 'N/A')}")
            else:
                print(f"   ⚠️  Connection test returned status {response.status_code}")
            
            print("\n" + "=" * 80)
            print("✅ AUTHENTICATION COMPLETE")
            print("=" * 80)
            print("\nYou can now run:")
            print("  python test_current_day.py")
            print("  python main.py --ticker QQQ --days 1")
            
        else:
            print("\n❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = refresh_authentication()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Authentication cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

