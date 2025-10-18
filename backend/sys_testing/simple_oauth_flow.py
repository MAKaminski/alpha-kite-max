#!/usr/bin/env python3
"""
Simple OAuth flow for Schwab API
"""

import urllib.parse

# Your Schwab app credentials from .env
APP_KEY = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
CALLBACK_URL = "https://127.0.0.1:8182"

def generate_oauth_url():
    """Generate the OAuth authorization URL"""
    
    # OAuth parameters
    params = {
        'client_id': APP_KEY,
        'redirect_uri': CALLBACK_URL,
        'response_type': 'code',
        'scope': 'api'
    }
    
    # Build the URL
    auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    print("🚀 SCHWAB OAUTH FLOW")
    print("=" * 60)
    print()
    print("✅ You are logged into Schwab.com")
    print("🔧 Now we need to catch the OAuth callback")
    print()
    print("1️⃣  FIRST: Start the callback server in another terminal:")
    print("   cd backend/sys_testing")
    print("   python oauth_callback_server.py")
    print()
    print("2️⃣  THEN: Click this OAuth URL:")
    print(f"   {auth_url}")
    print()
    print("3️⃣  FINALLY: After authorization, process the callback:")
    print("   python process_oauth_callback.py")
    print()
    print("💡 The callback server will catch the authorization code")
    print("   and save it for processing!")

if __name__ == "__main__":
    generate_oauth_url()
