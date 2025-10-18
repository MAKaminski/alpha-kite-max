#!/usr/bin/env python3
"""
Fixed OAuth flow based on schwab-py documentation analysis.
This addresses the key issues identified in our authentication attempts.
"""

import urllib.parse
import secrets
import requests
import base64
import json
from pathlib import Path

class FixedSchwabOAuth:
    def __init__(self):
        self.client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
        self.client_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
        self.redirect_uri = "https://127.0.0.1:8182"  # No trailing slash - matches registered URL
        self.base_url = "https://api.schwabapi.com/v1/oauth"
    
    def get_authorization_url(self):
        """
        Generate authorization URL using the exact format from schwab-py documentation.
        Key fixes:
        1. Parameter order: response_type first
        2. State parameter for CSRF protection
        3. Exact callback URL match (no trailing slash)
        """
        state = secrets.token_urlsafe(32)
        
        # Use the exact parameter order from schwab-py
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state
        }
        
        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.base_url}/authorize?{query_string}"
        
        print("🔧 FIXED OAUTH URL (based on schwab-py documentation):")
        print("=" * 70)
        print()
        print(auth_url)
        print()
        print("=" * 70)
        print("📋 KEY FIXES APPLIED:")
        print("   1. ✅ Parameter order: response_type first (like schwab-py)")
        print("   2. ✅ State parameter added (required for CSRF protection)")
        print("   3. ✅ Exact callback URL match (no trailing slash)")
        print("   4. ✅ Correct base URL (api.schwabapi.com)")
        print()
        print("🎯 This should now work!")
        print()
        print("📋 NEXT STEPS:")
        print("   1. Make sure you're logged into Schwab.com in your browser")
        print("   2. Open the URL above")
        print("   3. You should see an authorization/consent page")
        print("   4. Click 'Allow' or 'Authorize'")
        print("   5. Copy the full callback URL from your browser")
        print("   6. Run: python3 process_fixed_callback.py '<CALLBACK_URL>'")
        
        return auth_url, state
    
    def exchange_code_for_tokens(self, code):
        """Exchange authorization code for tokens."""
        token_url = f"{self.base_url}/token"
        
        # Basic authentication (as per documentation)
        basic_auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        print("🔄 Exchanging authorization code for tokens...")
        print(f"   Token URL: {token_url}")
        print(f"   Code: {code[:20]}...")
        print()
        
        try:
            response = requests.post(token_url, headers=headers, data=data)
            
            print(f"   Response Status: {response.status_code}")
            
            if response.status_code == 200:
                tokens = response.json()
                print("✅ TOKENS RECEIVED!")
                print()
                print(f"   Access Token: {tokens['access_token'][:30]}...")
                print(f"   Refresh Token: {tokens['refresh_token'][:30]}...")
                print(f"   Expires In: {tokens.get('expires_in', 'N/A')} seconds")
                print(f"   Token Type: {tokens.get('token_type', 'N/A')}")
                print()
                
                # Save tokens
                self.save_tokens(tokens)
                
                # Test the token
                self.test_access_token(tokens['access_token'])
                
                return tokens
            else:
                print(f"❌ ERROR: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            return None
    
    def save_tokens(self, tokens):
        """Save tokens to file."""
        token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
        token_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(token_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        print(f"💾 Tokens saved to: {token_file}")
        print()
    
    def test_access_token(self, access_token):
        """Test the access token with a simple API call."""
        print("🧪 Testing access token...")
        
        # Test with accounts endpoint
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
    oauth = FixedSchwabOAuth()
    auth_url, state = oauth.get_authorization_url()
    
    print()
    print("=" * 70)
    print("🔍 DIAGNOSTIC INFORMATION:")
    print("=" * 70)
    print(f"Client ID: {oauth.client_id}")
    print(f"Redirect URI: {oauth.redirect_uri}")
    print(f"State: {state}")
    print(f"Base URL: {oauth.base_url}")
    print()
    print("If this still doesn't work, the issue might be:")
    print("1. App not properly approved in Developer Portal")
    print("2. Additional approval steps required")
    print("3. Session/cookie issues (try incognito mode)")
    print("4. Network/firewall issues")

if __name__ == "__main__":
    main()
