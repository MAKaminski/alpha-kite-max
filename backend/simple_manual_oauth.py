#!/usr/bin/env python3
"""
Simple Manual OAuth - No Browser Required
Just paste the callback URL after you authorize manually
"""

import json
import time
import requests
import base64
import urllib.parse

# Your app credentials
APP_KEY = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
APP_SECRET = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
CALLBACK_URL = "https://127.0.0.1:8182"

def generate_auth_url():
    """Generate the authorization URL"""
    params = {
        'client_id': APP_KEY,
        'redirect_uri': CALLBACK_URL,
        'response_type': 'code',
        'scope': 'api'
    }
    
    auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?{urllib.parse.urlencode(params)}"
    return auth_url

def exchange_code_for_tokens(auth_code):
    """Exchange authorization code for tokens"""
    # Prepare Basic Auth header
    credentials = f"{APP_KEY}:{APP_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Make token request
    token_url = "https://api.schwabapi.com/v1/oauth/token"
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': CALLBACK_URL
    }
    
    print(f"📡 Making token request...")
    response = requests.post(token_url, headers=headers, data=data)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        tokens = response.json()
        print("✅ Token exchange successful!")
        print(f"   Access token: {tokens.get('access_token', 'N/A')[:20]}...")
        print(f"   Refresh token: {tokens.get('refresh_token', 'N/A')[:20]}...")
        print(f"   Expires in: {tokens.get('expires_in', 'N/A')} seconds")
        return tokens
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def save_tokens(tokens):
    """Save tokens in our expected format"""
    current_time = int(time.time())
    token_data = {
        "creation_timestamp": current_time,
        "token": {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "expires_in": str(tokens['expires_in']),
            "token_type": tokens['token_type'],
            "scope": tokens.get('scope', 'api'),
            "expires_at": current_time + tokens['expires_in']
        }
    }
    
    # Save to file
    with open('config/schwab_token.json', 'w') as f:
        json.dump(token_data, f, indent=2)
    
    print("✅ Tokens saved to config/schwab_token.json")
    return token_data

def main():
    print("🔐 SIMPLE MANUAL OAUTH")
    print("=" * 40)
    print()
    
    # Step 1: Generate auth URL
    auth_url = generate_auth_url()
    print("🌐 Step 1: Go to this URL in your browser:")
    print(f"   {auth_url}")
    print()
    print("📋 Step 2: After logging in, you'll be redirected to a 404 page")
    print("   Copy the FULL URL from your browser's address bar")
    print("   It should look like: https://127.0.0.1:8182/?code=ABC123...")
    print()
    
    # Step 2: Get callback URL from user
    callback_url = input("📝 Paste the callback URL here: ").strip()
    
    if not callback_url or 'code=' not in callback_url:
        print("❌ Invalid callback URL. Must contain 'code=' parameter")
        return
    
    # Extract authorization code
    try:
        parsed_url = urllib.parse.urlparse(callback_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        auth_code = query_params['code'][0]
        print(f"✅ Extracted code: {auth_code[:20]}...")
    except Exception as e:
        print(f"❌ Error extracting code: {e}")
        return
    
    # Step 3: Exchange code for tokens
    print("\n🔄 Step 3: Exchanging code for tokens...")
    tokens = exchange_code_for_tokens(auth_code)
    
    if not tokens:
        return
    
    # Check if refresh token is present
    if 'refresh_token' not in tokens:
        print("❌ CRITICAL: No refresh token in response!")
        print("Full response:", json.dumps(tokens, indent=2))
        return
    
    # Step 4: Save tokens
    print("\n💾 Step 4: Saving tokens...")
    save_tokens(tokens)
    
    print("\n🎉 SUCCESS!")
    print("✅ Refresh token obtained and saved")
    print("✅ Ready to upload to AWS Secrets Manager")
    print()
    print("Next steps:")
    print("1. Upload to AWS: aws secretsmanager update-secret --secret-id schwab-api-token-prod --secret-string file://config/schwab_token.json --region us-east-1")
    print("2. Test Lambda: aws lambda invoke --function-name alpha-kite-real-time-streamer --region us-east-1 --payload '{}' response.json")

if __name__ == "__main__":
    main()
