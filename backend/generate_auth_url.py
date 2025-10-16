#!/usr/bin/env python3
"""
Generate Schwab OAuth URL for manual authorization
"""

import urllib.parse

# Your app credentials
APP_KEY = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
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

def main():
    print("🔐 SCHWAB OAUTH AUTHORIZATION")
    print("=" * 50)
    print()
    
    auth_url = generate_auth_url()
    
    print("🌐 STEP 1: Click this URL to authorize:")
    print(f"   {auth_url}")
    print()
    print("📋 STEP 2: After logging in, you'll be redirected to a 404 page")
    print("   Copy the FULL URL from your browser's address bar")
    print("   It should look like: https://127.0.0.1:8182/?code=ABC123...")
    print()
    print("📝 STEP 3: Run this command with your callback URL:")
    print("   python3 process_callback.py 'YOUR_CALLBACK_URL_HERE'")
    print()
    print("💡 TIP: The 404 page is normal - just copy the URL!")

if __name__ == "__main__":
    main()
