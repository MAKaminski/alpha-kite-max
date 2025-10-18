#!/usr/bin/env python3
"""
Test different OAuth URL formats to find the working one
"""

import urllib.parse

# Your credentials
APP_KEY = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"

def test_oauth_urls():
    """Test different OAuth URL formats"""
    
    print("🧪 TESTING DIFFERENT OAUTH URL FORMATS")
    print("=" * 60)
    
    # Different base URLs to try
    base_urls = [
        "https://api.schwabapi.com",
        "https://api.schwab.com", 
        "https://api.schwab.com/v1",
        "https://api.schwabapi.com/v1"
    ]
    
    # Different callback URLs to try
    callback_urls = [
        "https://127.0.0.1:8182",
        "https://127.0.0.1:8182/",
        "https://localhost:8182",
        "https://localhost:8182/"
    ]
    
    # Different scopes to try
    scopes = [
        "api",
        "readonly",
        "readwrite", 
        ""
    ]
    
    print("🔍 Testing combinations...")
    print()
    
    for base_url in base_urls:
        for callback_url in callback_urls:
            for scope in scopes:
                # Build parameters
                params = {
                    'client_id': APP_KEY,
                    'redirect_uri': callback_url,
                    'response_type': 'code'
                }
                
                if scope:
                    params['scope'] = scope
                
                # Build URL
                auth_url = f"{base_url}/oauth/authorize?{urllib.parse.urlencode(params)}"
                
                print(f"🌐 Base: {base_url}")
                print(f"📞 Callback: {callback_url}")
                print(f"🔑 Scope: '{scope}' (empty means no scope)")
                print(f"🔗 URL: {auth_url}")
                print("-" * 60)
                
                # Only show a few combinations to avoid spam
                if base_url == "https://api.schwabapi.com" and callback_url == "https://127.0.0.1:8182/" and scope == "api":
                    print("⭐ THIS IS THE MOST LIKELY TO WORK - TRY THIS ONE FIRST!")
                    print()
                    break
            if base_url == "https://api.schwabapi.com":
                break
    
    print("💡 RECOMMENDED TESTING ORDER:")
    print("1. Try the ⭐ marked URL above")
    print("2. If that fails, try without scope")
    print("3. If still failing, check your Schwab app settings")
    print("4. Make sure callback URL matches exactly in Schwab Developer Portal")

if __name__ == "__main__":
    test_oauth_urls()
