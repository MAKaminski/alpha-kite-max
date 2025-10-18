#!/usr/bin/env python3
"""
OAuth flow following ChatGPT's guidance exactly.
This should work if the schwab-py library's URL worked.
"""

import base64
import urllib.parse
import requests
import json
import os
from pathlib import Path

# Load config from environment or use defaults
CLIENT_ID = os.getenv('SCHWAB_APP_KEY', 'Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU')
CLIENT_SECRET = os.getenv('SCHWAB_APP_SECRET', 'm5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK')
REDIRECT_URI = os.getenv('SCHWAB_CALLBACK_URL', 'https://127.0.0.1:8182/')

print("=" * 70)
print("SCHWAB OAUTH - CHATGPT GUIDED FLOW")
print("=" * 70)
print()
print(f"Client ID: {CLIENT_ID}")
print(f"Redirect URI: {REDIRECT_URI}")
print()

# Step 1: Build authorization URL (following ChatGPT's format)
auth_url = (
    f"https://api.schwabapi.com/v1/oauth/authorize"
    f"?client_id={urllib.parse.quote(CLIENT_ID)}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&response_type=code"
)

print("🔗 AUTHORIZATION URL:")
print()
print(auth_url)
print()
print("=" * 70)
print("📋 INSTRUCTIONS:")
print("=" * 70)
print("1. Copy the URL above")
print("2. Open it in your browser (while logged into Schwab.com)")
print("3. You should see an authorization/consent page")
print("4. Click 'Allow' or 'Authorize'")
print("5. You'll be redirected to https://127.0.0.1:8182/?code=XXX")
print("6. Your browser will show a connection error (that's OK)")
print("7. Copy the ENTIRE URL from your browser's address bar")
print("8. Paste it below")
print()
print("=" * 70)
print()

# Wait for user to paste the redirected URL
redirected_url = input("📥 Paste the full redirected URL here: ").strip()

# Parse the authorization code
try:
    parsed = urllib.parse.urlparse(redirected_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    if 'code' not in query_params:
        print()
        print("❌ ERROR: No 'code' parameter found in URL")
        print(f"   URL: {redirected_url}")
        print(f"   Params: {query_params}")
        exit(1)
    
    code = query_params['code'][0]
    print()
    print(f"✅ Authorization code extracted: {code[:20]}...")
    print()
    
except Exception as e:
    print()
    print(f"❌ ERROR parsing URL: {e}")
    exit(1)

# Step 2: Exchange code for tokens
print("🔄 Exchanging authorization code for tokens...")
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
    resp.raise_for_status()
    tokens = resp.json()
    
    print("✅ TOKENS RECEIVED!")
    print()
    print(f"Access Token: {tokens['access_token'][:30]}...")
    print(f"Refresh Token: {tokens['refresh_token'][:30]}...")
    print(f"Expires In: {tokens.get('expires_in', 'N/A')} seconds")
    print()
    
    # Save tokens to file
    token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
    token_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"💾 Tokens saved to: {token_file}")
    print()
    
    # Step 3: Test the access token with a simple API call
    print("🧪 Testing access token with API call...")
    print()
    
    api_url = "https://api.schwabapi.com/trader/v1/accounts"
    api_headers = {
        "Authorization": f"Bearer {tokens['access_token']}"
    }
    
    api_resp = requests.get(api_url, headers=api_headers)
    
    if api_resp.status_code == 200:
        print("✅ API call successful!")
        print(f"   Response: {api_resp.json()}")
    else:
        print(f"⚠️  API call returned status {api_resp.status_code}")
        print(f"   Response: {api_resp.text}")
    
    print()
    print("=" * 70)
    print("🎉 SUCCESS! OAuth flow completed!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Upload tokens to AWS Secrets Manager")
    print("2. Test Lambda function")
    print("3. Verify data streaming")
    
except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP ERROR: {e}")
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.text}")
    exit(1)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    exit(1)

