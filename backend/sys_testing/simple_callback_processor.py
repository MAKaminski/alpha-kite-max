#!/usr/bin/env python3
"""
Simple OAuth callback processor without dependencies.
Usage: python3 simple_callback_processor.py "https://127.0.0.1:8182/?code=XXX&state=YYY"
"""

import sys
import urllib.parse
import requests
import base64
import json
from pathlib import Path

def process_callback(callback_url):
    """Process OAuth callback URL and exchange code for tokens."""
    
    print("🔄 PROCESSING OAUTH CALLBACK")
    print("=" * 50)
    print(f"Callback URL: {callback_url}")
    print()
    
    # Parse the callback URL
    try:
        parsed = urllib.parse.urlparse(callback_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        print("📋 Parsed Parameters:")
        for key, value in query_params.items():
            print(f"   {key}: {value[0] if value else 'None'}")
        print()
        
        if 'code' not in query_params:
            print("❌ ERROR: No 'code' parameter found in URL")
            if 'error' in query_params:
                print(f"   Error: {query_params['error'][0]}")
                if 'error_description' in query_params:
                    print(f"   Description: {query_params['error_description'][0]}")
            return False
        
        code = query_params['code'][0]
        state = query_params.get('state', [''])[0]
        
        print(f"✅ Authorization code: {code[:20]}...")
        if state:
            print(f"✅ State: {state[:20]}...")
        print()
        
        # Exchange code for tokens
        return exchange_code_for_tokens(code)
        
    except Exception as e:
        print(f"❌ ERROR parsing URL: {e}")
        return False

def exchange_code_for_tokens(code):
    """Exchange authorization code for tokens."""
    
    print("🔄 Exchanging code for tokens...")
    
    # Configuration
    client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
    client_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
    redirect_uri = "https://127.0.0.1:8182"
    
    token_url = "https://api.schwabapi.com/v1/oauth/token"
    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        if response.status_code == 200:
            tokens = response.json()
            print("✅ TOKENS RECEIVED!")
            print()
            print(f"Access Token: {tokens['access_token'][:30]}...")
            print(f"Refresh Token: {tokens['refresh_token'][:30]}...")
            print(f"Expires In: {tokens.get('expires_in', 'N/A')} seconds")
            print()
            
            # Save tokens
            save_tokens(tokens)
            
            # Test the token
            test_access_token(tokens['access_token'])
            
            return True
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Token exchange error: {e}")
        return False

def save_tokens(tokens):
    """Save tokens to file."""
    token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
    token_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"💾 Tokens saved to: {token_file}")

def test_access_token(access_token):
    """Test the access token with a simple API call."""
    print("🧪 Testing access token...")
    
    api_url = "https://api.schwabapi.com/trader/v1/accounts"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            accounts = response.json()
            print("✅ API call successful!")
            print(f"   Found {len(accounts)} account(s)")
            print("🎉 AUTHENTICATION SUCCESSFUL!")
        else:
            print(f"⚠️  API call status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 simple_callback_processor.py \"<CALLBACK_URL>\"")
        print("Example: python3 simple_callback_processor.py \"https://127.0.0.1:8182/?code=ABC123&state=XYZ789\"")
        sys.exit(1)
    
    callback_url = sys.argv[1]
    success = process_callback(callback_url)
    
    if success:
        print()
        print("=" * 50)
        print("🎉 SUCCESS! OAuth flow completed!")
        print("=" * 50)
        print()
        print("Next steps:")
        print("1. Upload tokens to AWS Secrets Manager:")
        print("   aws secretsmanager put-secret-value \\")
        print("     --secret-id schwab-api-token-prod \\")
        print("     --secret-string file://config/schwab_token.json")
        print()
        print("2. Test Lambda function")
        print("3. Verify data streaming")
    else:
        print()
        print("❌ OAuth flow failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
