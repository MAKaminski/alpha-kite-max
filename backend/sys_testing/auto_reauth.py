#!/usr/bin/env python3
"""
Fully automatic Schwab re-authentication using browser automation.
This will automatically open your browser and guide you through the OAuth flow.
"""

import sys
from pathlib import Path
import json
import time
import webbrowser

sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.config import SchwabConfig
from schwab import auth

def main():
    print("\n" + "="*70)
    print("AUTOMATIC SCHWAB RE-AUTHENTICATION")
    print("="*70)
    print()
    
    config = SchwabConfig()
    token_path = Path(config.token_path)
    
    # Delete old token
    if token_path.exists():
        print(f"🗑️  Deleting old token: {config.token_path}")
        with open(token_path) as f:
            old_token = json.load(f)
            has_refresh = 'refresh_token' in old_token.get('token', {})
            print(f"   Old token has refresh_token: {'YES' if has_refresh else 'NO ❌'}")
        token_path.unlink()
        print("   ✅ Deleted")
        print()
    
    print("🚀 Starting automatic OAuth flow...")
    print()
    print("📱 Your browser will automatically open.")
    print("   → If already logged into Schwab: Just click 'Allow'")
    print("   → If not logged in: Log in, then click 'Allow'")
    print()
    print("⏳ Waiting for authorization...")
    print()
    
    try:
        # Use easy_client which handles the browser flow automatically
        from schwab import auth
        
        print("🌐 Opening browser for authorization...")
        print()
        
        # This will automatically:
        # 1. Generate auth URL
        # 2. Open browser
        # 3. Start local server on callback URL
        # 4. Wait for authorization
        # 5. Exchange code for tokens
        # 6. Save tokens to file
        client = auth.easy_client(
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
        
        # Verify token
        if token_path.exists():
            with open(token_path) as f:
                new_token = json.load(f)
                print("📄 New token verified:")
                if 'token' in new_token:
                    token_data = new_token['token']
                    has_access = 'access_token' in token_data
                    has_refresh = 'refresh_token' in token_data
                    
                    print(f"   {'✅' if has_access else '❌'} Has access_token: {has_access}")
                    print(f"   {'✅' if has_refresh else '❌'} Has refresh_token: {has_refresh}")
                    print(f"   ✅ Token type: {token_data.get('token_type')}")
                    print(f"   ✅ Expires in: {token_data.get('expires_in')} seconds")
                    print(f"   ✅ Scope: {token_data.get('scope')}")
                    
                    if not has_refresh:
                        print()
                        print("⚠️  WARNING: Token missing refresh_token!")
                        return 1
                print()
        
        print(f"💾 Token saved to: {config.token_path}")
        print()
        
        # Test the token immediately
        print("🧪 Testing token with Schwab API...")
        try:
            response = client.get_account_numbers()
            if response.status_code == 200:
                accounts = response.json()
                print(f"   ✅ Token works! Found {len(accounts)} account(s)")
                if accounts:
                    print(f"   📋 Account: {accounts[0].get('accountNumber', 'N/A')}")
            else:
                print(f"   ⚠️  API returned status: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Test failed: {e}")
        
        print()
        print("="*70)
        print("NEXT: UPLOAD TO AWS")
        print("="*70)
        print()
        print("Run this command:")
        print()
        print("  aws secretsmanager update-secret \\")
        print("    --secret-id schwab-api-token-prod \\")
        print("    --secret-string file://config/schwab_token.json \\")
        print("    --region us-east-1")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("💡 If browser didn't open automatically, the URL was printed above.")
        print("   Copy it manually and authorize in your browser.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

