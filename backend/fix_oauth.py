#!/usr/bin/env python3
"""
Fix Schwab OAuth to get refresh tokens
Uses raw OAuth implementation following Schwab's exact specification
"""

import requests
import urllib.parse
import base64
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

# Your app credentials
APP_KEY = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
APP_SECRET = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
CALLBACK_URL = "https://127.0.0.1:8182"

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/?code='):
            # Extract the authorization code
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                self.server.auth_code = query_params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                response_html = f"""
                <html>
                <body>
                    <h1>✅ Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <p>Code received: {self.server.auth_code}</p>
                </body>
                </html>
                """.encode()
                self.wfile.write(response_html)
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write("❌ No authorization code found".encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("❌ Invalid callback".encode())

def start_callback_server():
    """Start local server to catch OAuth callback"""
    server = HTTPServer(('127.0.0.1', 8182), CallbackHandler)
    server.auth_code = None
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return server

def step1_authorize():
    """Step 1: Generate authorization URL and open browser"""
    print("🔐 Step 1: Authorization")
    print("=" * 50)
    
    # Start callback server
    server = start_callback_server()
    print(f"✅ Callback server started on {CALLBACK_URL}")
    
    # Generate authorization URL
    params = {
        'client_id': APP_KEY,
        'redirect_uri': CALLBACK_URL,
        'response_type': 'code',
        'scope': 'api'  # Schwab uses 'api' scope
    }
    
    auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    print(f"🌐 Opening browser to: {auth_url}")
    webbrowser.open(auth_url)
    
    print("\n⏳ Waiting for authorization...")
    print("   (Complete the login in your browser)")
    
    # Wait for callback
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    while server.auth_code is None:
        if time.time() - start_time > timeout:
            print("❌ Timeout waiting for authorization")
            return None
        time.sleep(1)
    
    print(f"✅ Authorization code received: {server.auth_code[:20]}...")
    return server.auth_code

def step2_exchange_code_for_tokens(auth_code):
    """Step 2: Exchange authorization code for access and refresh tokens"""
    print("\n🔄 Step 2: Exchange Code for Tokens")
    print("=" * 50)
    
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
    
    print(f"📡 Making token request to: {token_url}")
    print(f"   Grant type: {data['grant_type']}")
    print(f"   Code: {auth_code[:20]}...")
    
    response = requests.post(token_url, headers=headers, data=data)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        tokens = response.json()
        print("✅ Token exchange successful!")
        print(f"   Access token: {tokens.get('access_token', 'N/A')[:20]}...")
        print(f"   Refresh token: {tokens.get('refresh_token', 'N/A')[:20]}...")
        print(f"   Expires in: {tokens.get('expires_in', 'N/A')} seconds")
        print(f"   Token type: {tokens.get('token_type', 'N/A')}")
        print(f"   Scope: {tokens.get('scope', 'N/A')}")
        
        # Check if refresh token is present
        if 'refresh_token' in tokens:
            print("🎉 SUCCESS: Refresh token received!")
            return tokens
        else:
            print("❌ FAILURE: No refresh token in response!")
            print("Full response:", json.dumps(tokens, indent=2))
            return None
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def save_tokens(tokens):
    """Save tokens in the format expected by our application"""
    print("\n💾 Step 3: Save Tokens")
    print("=" * 50)
    
    # Convert to our expected format
    token_data = {
        "creation_timestamp": int(time.time()),
        "token": {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "expires_in": str(tokens['expires_in']),
            "token_type": tokens['token_type'],
            "scope": tokens['scope'],
            "expires_at": int(time.time()) + tokens['expires_in']
        }
    }
    
    # Save to file
    with open('config/schwab_token.json', 'w') as f:
        json.dump(token_data, f, indent=2)
    
    print("✅ Tokens saved to config/schwab_token.json")
    print("📋 Token structure:")
    print(json.dumps(token_data, indent=2))
    
    return token_data

def main():
    print("🚀 Schwab OAuth Fix - Get Refresh Tokens")
    print("=" * 60)
    print("This will use raw OAuth implementation to get refresh tokens")
    print()
    
    # Check if credentials are set
    if APP_KEY == "Os3C2znH..." or APP_SECRET == "...":
        print("❌ Please update APP_KEY and APP_SECRET in this script")
        print("   Get them from: https://developer.schwab.com/")
        return
    
    try:
        # Step 1: Get authorization code
        auth_code = step1_authorize()
        if not auth_code:
            return
        
        # Step 2: Exchange for tokens
        tokens = step2_exchange_code_for_tokens(auth_code)
        if not tokens:
            return
        
        # Step 3: Save tokens
        save_tokens(tokens)
        
        print("\n🎉 OAuth Fix Complete!")
        print("✅ Refresh token obtained and saved")
        print("✅ Ready to upload to AWS Secrets Manager")
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
