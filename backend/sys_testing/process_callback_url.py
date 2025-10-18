#!/usr/bin/env python3
"""
Process the callback URL to exchange the authorization code for tokens.
Usage: python3 process_callback_url.py "https://127.0.0.1:8182/?code=XXX"
"""

import sys
import base64
import urllib.parse
import requests
import json
import os
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python3 process_callback_url.py \"<CALLBACK_URL>\"")
    print("Example: python3 process_callback_url.py \"https://127.0.0.1:8182/?code=ABC123\"")
    sys.exit(1)

CLIENT_ID = os.getenv('SCHWAB_APP_KEY', 'Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU')
CLIENT_SECRET = os.getenv('SCHWAB_APP_SECRET', 'm5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK')
REDIRECT_URI = os.getenv('SCHWAB_CALLBACK_URL', 'https://127.0.0.1:8182/')

redirected_url = sys.argv[1]

print("=" * 70)
print("🔄 PROCESSING CALLBACK URL")
print("=" * 70)
print()

# Parse the authorization code
try:
    parsed = urllib.parse.urlparse(redirected_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    print(f"Parsed URL: {parsed.scheme}://{parsed.netloc}{parsed.path}")
    print(f"Query params: {query_params}")
    print()
    
    if 'code' not in query_params:
        print("❌ ERROR: No 'code' parameter found in URL")
        print()
        if 'error' in query_params:
            print(f"   Error: {query_params['error'][0]}")
            if 'error_description' in query_params:
                print(f"   Description: {query_params['error_description'][0]}")
        sys.exit(1)
    
    code = query_params['code'][0]
    print(f"✅ Authorization code: {code[:20]}...")
    print()
    
except Exception as e:
    print(f"❌ ERROR parsing URL: {e}")
    sys.exit(1)

# Exchange code for tokens
print("🔄 Exchanging code for tokens...")
print()

token_url = "https://api.schwabapi.com/v1/oauth/token"
basic_auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

headers = {
    "Authorization": f"Basic {basic_auth}",
    "Content-Type": "application/x-www-form-urlencoded"
}

payload = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI
}

try:
    resp = requests.post(token_url, headers=headers, data=payload)
    
    print(f"Response status: {resp.status_code}")
    print()
    
    if resp.status_code != 200:
        print(f"❌ ERROR: {resp.text}")
        sys.exit(1)
    
    tokens = resp.json()
    
    print("✅ TOKENS RECEIVED!")
    print()
    print(f"Access Token: {tokens['access_token'][:30]}...")
    print(f"Refresh Token: {tokens['refresh_token'][:30]}...")
    print(f"Expires In: {tokens.get('expires_in', 'N/A')} seconds")
    print()
    
    # Save tokens
    token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
    token_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"💾 Tokens saved to: {token_file}")
    print()
    
    # Test the token
    print("🧪 Testing access token...")
    api_url = "https://api.schwabapi.com/trader/v1/accounts"
    api_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    api_resp = requests.get(api_url, headers=api_headers)
    
    if api_resp.status_code == 200:
        print("✅ API call successful!")
        accounts = api_resp.json()
        print(f"   Found {len(accounts)} account(s)")
    else:
        print(f"⚠️  API call status: {api_resp.status_code}")
        print(f"   Response: {api_resp.text}")
    
    print()
    print("=" * 70)
    print("🎉 SUCCESS!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Upload tokens to AWS Secrets Manager:")
    print(f"   aws secretsmanager put-secret-value \\")
    print(f"     --secret-id schwab-api-token-prod \\")
    print(f"     --secret-string file://{token_file}")
    print()
    print("2. Test Lambda function")
    print("3. Verify data streaming")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

