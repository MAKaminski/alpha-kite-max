#!/usr/bin/env python3
"""
Process the callback URL and exchange it for tokens.
Usage: python3 process_callback.py '<full-callback-url>'
"""

import sys
from pathlib import Path
import json
import urllib.parse

sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.config import SchwabConfig
from schwab import auth

def main():
    if len(sys.argv) < 2:
        print("\n❌ Error: No callback URL provided")
        print()
        print("Usage:")
        print("  python3 process_callback.py '<full-callback-url>'")
        print()
        print("Example:")
        print("  python3 process_callback.py 'https://127.0.0.1:8182/?code=ABC123&session=XYZ789'")
        print()
        return 1
    
    callback_url = sys.argv[1]
    
    print("\n" + "="*70)
    print("PROCESSING SCHWAB CALLBACK")
    print("="*70)
    print()
    print(f"📥 Callback URL received: {callback_url[:50]}...")
    print()
    
    # Parse the callback URL to extract the code
    try:
        parsed = urllib.parse.urlparse(callback_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'code' not in params:
            print("❌ Error: No 'code' parameter found in URL")
            print()
            print("Make sure you copied the ENTIRE callback URL including all parameters.")
            return 1
        
        code = params['code'][0]
        print(f"✅ Authorization code extracted: {code[:20]}...")
        print()
        
    except Exception as e:
        print(f"❌ Error parsing URL: {e}")
        return 1
    
    config = SchwabConfig()
    token_path = Path(config.token_path)
    
    # Delete old token if exists
    if token_path.exists():
        print(f"🗑️  Deleting old token: {config.token_path}")
        token_path.unlink()
        print("   ✅ Deleted")
        print()
    
    try:
        print("🔄 Exchanging authorization code for tokens...")
        print()
        
        # Use the auth library to exchange code for tokens
        # We'll simulate what client_from_manual_flow does but with the code we already have
        import httpx
        from schwab.client import Client
        
        # Token exchange
        token_url = "https://api.schwabapi.com/v1/oauth/token"
        
        auth_header = httpx.BasicAuth(config.app_key, config.app_secret)
        
        response = httpx.post(
            token_url,
            auth=auth_header,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': config.callback_url,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return 1
        
        token_data = response.json()
        
        # Save token
        import time
        token_dict = {
            'creation_timestamp': int(time.time()),
            'token': token_data
        }
        
        with open(config.token_path, 'w') as f:
            json.dump(token_dict, f, indent=2)
        
        print("="*70)
        print("✅ TOKEN EXCHANGE SUCCESSFUL!")
        print("="*70)
        print()
        
        # Verify token
        print("📄 New token verified:")
        has_access = 'access_token' in token_data
        has_refresh = 'refresh_token' in token_data
        
        print(f"   {'✅' if has_access else '❌'} Has access_token: {has_access}")
        print(f"   {'✅' if has_refresh else '❌'} Has refresh_token: {has_refresh}")
        print(f"   ✅ Token type: {token_data.get('token_type')}")
        print(f"   ✅ Expires in: {token_data.get('expires_in')} seconds")
        print(f"   ✅ Scope: {token_data.get('scope')}")
        print()
        
        if not has_refresh:
            print("⚠️  WARNING: Token missing refresh_token!")
            print("   This suggests an OAuth configuration issue.")
            return 1
        
        print(f"💾 Token saved to: {config.token_path}")
        print()
        print("="*70)
        print("NEXT STEPS")
        print("="*70)
        print()
        print("1. Test locally:")
        print("   python3 test_paper_trading.py")
        print()
        print("2. Upload to AWS Secrets Manager:")
        print("   aws secretsmanager update-secret \\")
        print("     --secret-id schwab-api-token-prod \\")
        print("     --secret-string file://config/schwab_token.json \\")
        print("     --region us-east-1")
        print()
        print("3. Test Lambda:")
        print("   aws lambda invoke \\")
        print("     --function-name alpha-kite-real-time-streamer \\")
        print("     --payload '{}' response.json && cat response.json")
        print()
        print("4. Check data:")
        print("   python3 check_data_status.py")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

