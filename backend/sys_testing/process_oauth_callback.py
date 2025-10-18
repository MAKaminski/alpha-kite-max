#!/usr/bin/env python3
"""
Process the OAuth callback code and exchange for tokens
"""

import sys
import json
import httpx
from pathlib import Path

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
from schwab_integration.config import SchwabConfig

def process_oauth_callback():
    """Process the OAuth callback code"""
    
    print("🔄 Processing OAuth Callback...")
    
    # Read the authorization code
    try:
        with open('/tmp/schwab_auth_code.txt', 'r') as f:
            code = f.read().strip()
        print(f"📥 Authorization Code: {code}")
    except FileNotFoundError:
        print("❌ No authorization code found. Make sure you completed the OAuth flow.")
        return 1
    
    # Load config
    config = SchwabConfig()
    
    # Exchange code for tokens
    token_url = f"{config.base_url}/v1/oauth/token"
    
    # Basic auth header
    import base64
    credentials = f"{config.app_key}:{config.app_secret}"
    auth_header = base64.b64encode(credentials.encode()).decode()
    
    print("🔄 Exchanging code for tokens...")
    
    try:
        response = httpx.post(
            token_url,
            headers={
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': 'https://127.0.0.1:8182'
            }
        )
        
        if response.status_code == 200:
            tokens = response.json()
            print("✅ Token exchange successful!")
            
            # Save tokens
            config.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config.token_path, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            print(f"💾 Tokens saved to: {config.token_path}")
            
            # Verify we have a refresh token
            has_refresh = 'refresh_token' in tokens
            print(f"🔄 Has refresh token: {has_refresh}")
            
            if has_refresh:
                print("🎉 SUCCESS! You now have a refresh token for automatic renewals.")
            else:
                print("⚠️  WARNING: No refresh token received!")
            
            return 0
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = process_oauth_callback()
    sys.exit(exit_code)
