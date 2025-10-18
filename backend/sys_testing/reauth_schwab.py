#!/usr/bin/env python3
"""
Re-authenticate with Schwab API to get a fresh OAuth token.
This will open a browser for you to authorize the app.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.config import SchwabConfig
from schwab import auth

def main():
    print("\n" + "="*70)
    print("SCHWAB API RE-AUTHENTICATION")
    print("="*70)
    print()
    
    config = SchwabConfig()
    
    print("📋 Configuration:")
    print(f"   App Key: {config.app_key[:8]}...")
    print(f"   Callback URL: {config.callback_url}")
    print(f"   Token Path: {config.token_path}")
    print()
    
    # Check if old token exists
    token_path = Path(config.token_path)
    if token_path.exists():
        print(f"⚠️  Found existing token at: {config.token_path}")
        print(f"   Created: {token_path.stat().st_mtime}")
        
        # Show current token
        with open(token_path) as f:
            old_token = json.load(f)
            if 'token' in old_token:
                has_refresh = 'refresh_token' in old_token['token']
                print(f"   Has refresh_token: {'✅ YES' if has_refresh else '❌ NO (THIS IS THE PROBLEM!)'}")
                if 'expires_at' in old_token['token']:
                    print(f"   Expires at: {old_token['token']['expires_at']}")
        print()
        
        response = input("   Delete old token and create new one? (y/n): ")
        if response.lower() != 'y':
            print("\n❌ Cancelled. Exiting...")
            return 1
        
        print(f"   🗑️  Deleting {config.token_path}...")
        token_path.unlink()
        print("   ✅ Deleted")
        print()
    
    print("🔐 Starting OAuth authorization flow...")
    print()
    print("📝 INSTRUCTIONS:")
    print("   1. A browser window will open (or a URL will be displayed)")
    print("   2. Log in to your Schwab account")
    print("   3. Click 'Allow' to authorize the app")
    print("   4. You'll be redirected to the callback URL")
    print("   5. Copy the ENTIRE callback URL from your browser")
    print("   6. Paste it below when prompted")
    print()
    
    input("Press Enter to continue...")
    print()
    
    try:
        # Create new authenticated client
        print("🌐 Initiating OAuth flow...")
        print()
        
        client = auth.client_from_manual_flow(
            api_key=config.app_key,
            app_secret=config.app_secret,
            callback_url=config.callback_url,
            token_path=config.token_path
        )
        
        print()
        print("="*70)
        print("✅ AUTHENTICATION SUCCESSFUL!")
        print("="*70)
        print()
        
        # Verify token file
        if token_path.exists():
            with open(token_path) as f:
                new_token = json.load(f)
                print("📄 New token details:")
                if 'token' in new_token:
                    token_data = new_token['token']
                    print(f"   ✅ Has access_token: {len(token_data.get('access_token', '')) > 0}")
                    print(f"   ✅ Has refresh_token: {len(token_data.get('refresh_token', '')) > 0}")
                    print(f"   ✅ Expires in: {token_data.get('expires_in')} seconds")
                    print(f"   ✅ Scope: {token_data.get('scope')}")
                    print()
        
        print("📋 Next steps:")
        print()
        print("1. Test the token locally:")
        print("   python test_paper_trading.py")
        print()
        print("2. Upload to AWS Secrets Manager:")
        print("   aws secretsmanager update-secret \\")
        print("     --secret-id schwab-api-token-prod \\")
        print(f"     --secret-string file://{config.token_path} \\")
        print("     --region us-east-1")
        print()
        print("3. Test Lambda:")
        print("   aws lambda invoke \\")
        print("     --function-name alpha-kite-real-time-streamer \\")
        print("     --payload '{}' \\")
        print("     response.json")
        print()
        print("4. Check data:")
        print("   python check_data_status.py")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print()
        print("Common issues:")
        print("  • Incorrect callback URL in Schwab app settings")
        print("  • App not approved in Schwab developer portal")
        print("  • Network/firewall blocking the callback")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())

