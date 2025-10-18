#!/usr/bin/env python3
"""
Automatic Schwab re-authentication (non-interactive).
Deletes old token and initiates OAuth flow.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.config import SchwabConfig
from schwab import auth

def main():
    print("\n" + "="*70)
    print("SCHWAB API RE-AUTHENTICATION (AUTO MODE)")
    print("="*70)
    print()
    
    config = SchwabConfig()
    token_path = Path(config.token_path)
    
    # Delete old token
    if token_path.exists():
        print(f"🗑️  Deleting old token: {config.token_path}")
        
        # Show what we're deleting
        with open(token_path) as f:
            old_token = json.load(f)
            has_refresh = 'refresh_token' in old_token.get('token', {})
            print(f"   Old token has refresh_token: {'YES' if has_refresh else 'NO ❌'}")
        
        token_path.unlink()
        print("   ✅ Deleted")
        print()
    
    print("🔐 Starting OAuth flow...")
    print()
    print("="*70)
    print("MANUAL STEPS REQUIRED:")
    print("="*70)
    print()
    print("The schwab-py library will:")
    print("  1. Generate an authorization URL")
    print("  2. Print it to the console")
    print("  3. Wait for you to paste the callback URL")
    print()
    print("YOU NEED TO:")
    print("  1. Copy the authorization URL that appears below")
    print("  2. Open it in your browser")
    print("  3. Log in to Schwab")
    print("  4. Click 'Allow'")
    print("  5. Copy the ENTIRE callback URL from your browser")
    print("  6. Paste it when prompted")
    print()
    print("="*70)
    print()
    
    try:
        # This will print the URL and wait for user input
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
        
        # Verify new token
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
                    print(f"   ✅ Expires in: {token_data.get('expires_in')} seconds")
                    print(f"   ✅ Scope: {token_data.get('scope')}")
                    
                    if not has_refresh:
                        print()
                        print("⚠️  WARNING: Token still missing refresh_token!")
                        print("   This might indicate an issue with the OAuth flow.")
                        print("   The token may work temporarily but will fail to refresh.")
                        return 1
                print()
        
        print("📋 Token saved to: config/schwab_token.json")
        print()
        print("✅ Next: Upload to AWS Secrets Manager")
        print()
        print("Run this command:")
        print()
        print("aws secretsmanager update-secret \\")
        print("  --secret-id schwab-api-token-prod \\")
        print("  --secret-string file://config/schwab_token.json \\")
        print("  --region us-east-1")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

