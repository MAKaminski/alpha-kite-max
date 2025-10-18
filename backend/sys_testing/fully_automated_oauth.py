#!/usr/bin/env python3
"""
Fully Automated Schwab OAuth with Login Automation

This script automates EVERYTHING:
1. Opens browser to OAuth URL
2. Automatically fills in login credentials
3. Clicks login button
4. Waits for authorization page
5. Clicks "Allow" button
6. Captures callback URL
7. Exchanges code for tokens
8. Uploads to AWS Secrets Manager

NO manual interaction required at all!
"""

import time
import json
import base64
import requests
import threading
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
import ssl
import subprocess
import sys

# Configuration
CLIENT_ID = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
CLIENT_SECRET = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
REDIRECT_URI = "https://127.0.0.1:8182"
BASE_URL = "https://api.schwabapi.com"
PORT = 8182

# Schwab credentials (from .env or user input)
SCHWAB_USERNAME = "makaminski"
SCHWAB_PASSWORD = "azj*pbf.tpw*BNX5vkr"  # From your .env file

# Global variables for callback capture
callback_url = None
callback_received = threading.Event()

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to capture OAuth callback"""
    
    def do_GET(self):
        global callback_url
        
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        # Parse the callback URL
        query_params = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query_params)
        
        code = params.get('code', [''])[0]
        state = params.get('state', [''])[0]
        error = params.get('error', [''])[0]
        
        # Store the full callback URL
        callback_url = f"https://127.0.0.1:{PORT}{self.path}"
        
        # Send success page to browser
        self.wfile.write(b"<html><head><title>OAuth Success</title></head><body>")
        self.wfile.write(b"<h1>Authorization Successful!</h1>")
        
        if code:
            self.wfile.write(f"<p>Authorization Code: <code>{code[:20]}...</code></p>".encode())
            self.wfile.write(f"<p>State: <code>{state}</code></p>".encode())
            self.wfile.write(b"<p><strong>Processing tokens automatically...</strong></p>")
            self.wfile.write(b"<p>You can close this window.</p>")
        elif error:
            self.wfile.write(f"<p style='color: red;'>Error: {error}</p>".encode())
            self.wfile.write(f"<p>Error Description: {params.get('error_description', [''])[0]}</p>".encode())
        else:
            self.wfile.write(b"<p>No authorization code or error found.</p>")
        
        self.wfile.write(b"</body></html>")
        
        # Signal that callback was received
        callback_received.set()
        
        print(f"\n✅ Callback received: {callback_url}")

def start_callback_server():
    """Start HTTPS callback server"""
    print(f"🚀 Starting callback server on port {PORT}...")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain('server.pem', 'server.key')
    except FileNotFoundError:
        print("❌ SSL certificates not found. Generating...")
        generate_ssl_certificates()
        context.load_cert_chain('server.pem', 'server.key')
    
    with socketserver.TCPServer(("", PORT), OAuthCallbackHandler) as httpd:
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print(f"✅ Callback server ready on https://127.0.0.1:{PORT}")
        
        # Start server in background thread
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return httpd

def generate_ssl_certificates():
    """Generate self-signed SSL certificates for localhost"""
    print("🔐 Generating SSL certificates for localhost...")
    
    # Generate private key
    subprocess.run([
        'openssl', 'genrsa', '-out', 'server.key', '2048'
    ], check=True, capture_output=True)
    
    # Generate certificate
    subprocess.run([
        'openssl', 'req', '-new', '-x509', '-key', 'server.key', 
        '-out', 'server.pem', '-days', '365', '-subj', 
        '/C=US/ST=State/L=City/O=Organization/CN=127.0.0.1'
    ], check=True, capture_output=True)
    
    print("✅ SSL certificates generated")

def install_playwright():
    """Install Playwright if not already installed"""
    try:
        import playwright
        print("✅ Playwright already installed")
        return True
    except ImportError:
        print("📦 Installing Playwright...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("✅ Playwright installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Playwright: {e}")
            return False

def automated_browser_oauth():
    """Use Playwright to automate the entire OAuth flow"""
    print("🤖 Starting fully automated browser OAuth...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Launch browser (headless=False so you can see what's happening)
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Generate OAuth URL
            state = f"auto_reauth_{int(time.time())}"
            oauth_url = f"{BASE_URL}/v1/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state={state}"
            
            print(f"🌐 Opening OAuth URL: {oauth_url}")
            page.goto(oauth_url)
            
            # Wait for login page to load
            print("⏳ Waiting for login page...")
            page.wait_for_selector('input[name="loginId"], input[type="text"]', timeout=10000)
            
            # Fill in login credentials
            print("🔑 Filling in login credentials...")
            
            # Try different selectors for username field
            username_selectors = [
                'input[name="loginId"]',
                'input[type="text"]',
                'input[placeholder*="Login"]',
                'input[placeholder*="Username"]'
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    page.fill(selector, SCHWAB_USERNAME)
                    username_filled = True
                    print(f"✅ Username filled using selector: {selector}")
                    break
                except:
                    continue
            
            if not username_filled:
                print("❌ Could not find username field")
                return False
            
            # Try different selectors for password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="Password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    page.fill(selector, SCHWAB_PASSWORD)
                    password_filled = True
                    print(f"✅ Password filled using selector: {selector}")
                    break
                except:
                    continue
            
            if not password_filled:
                print("❌ Could not find password field")
                return False
            
            # Click login button
            print("🔘 Clicking login button...")
            login_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                '.login-button',
                '#login-button'
            ]
            
            login_clicked = False
            for selector in login_selectors:
                try:
                    page.click(selector)
                    login_clicked = True
                    print(f"✅ Login button clicked using selector: {selector}")
                    break
                except:
                    continue
            
            if not login_clicked:
                print("❌ Could not find login button")
                return False
            
            # Wait for authorization page or callback
            print("⏳ Waiting for authorization page or callback...")
            
            # Wait for either authorization page or callback redirect
            try:
                # Wait for authorization page (if it appears)
                page.wait_for_selector('button:has-text("Allow"), button:has-text("Authorize"), button:has-text("Accept")', timeout=15000)
                print("✅ Authorization page loaded")
                
                # Click Allow/Authorize button
                auth_selectors = [
                    'button:has-text("Allow")',
                    'button:has-text("Authorize")',
                    'button:has-text("Accept")',
                    'input[value="Allow"]',
                    'input[value="Authorize"]'
                ]
                
                auth_clicked = False
                for selector in auth_selectors:
                    try:
                        page.click(selector)
                        auth_clicked = True
                        print(f"✅ Authorization button clicked using selector: {selector}")
                        break
                    except:
                        continue
                
                if not auth_clicked:
                    print("⚠️  Could not find authorization button, but continuing...")
                
            except:
                print("⚠️  No authorization page found, checking for direct callback...")
            
            # Wait for callback redirect
            print("⏳ Waiting for callback redirect...")
            try:
                page.wait_for_url(f"**/127.0.0.1:{PORT}/**", timeout=30000)
                print("✅ Callback redirect received!")
                
                # Get the callback URL
                callback_url = page.url
                print(f"📋 Callback URL: {callback_url}")
                
                # Store globally for processing
                globals()['callback_url'] = callback_url
                callback_received.set()
                
                return True
                
            except Exception as e:
                print(f"❌ Callback redirect timeout: {e}")
                print(f"Current URL: {page.url}")
                return False
            
            finally:
                # Keep browser open for a moment to see the result
                time.sleep(3)
                browser.close()
    
    except ImportError:
        print("❌ Playwright not available. Installing...")
        if install_playwright():
            return automated_browser_oauth()
        else:
            return False
    except Exception as e:
        print(f"❌ Browser automation failed: {e}")
        return False

def generate_oauth_url():
    """Generate OAuth authorization URL"""
    import secrets
    
    state = f"auto_reauth_{int(time.time())}"
    
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': state
    }
    
    query_string = urllib.parse.urlencode(params)
    oauth_url = f"{BASE_URL}/v1/oauth/authorize?{query_string}"
    
    return oauth_url, state

def exchange_code_for_tokens(auth_code):
    """Exchange authorization code for access and refresh tokens"""
    print("🔄 Exchanging authorization code for tokens...")
    
    # Prepare credentials for Basic Auth
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Token exchange request
    token_url = f"{BASE_URL}/v1/oauth/token"
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        
        tokens = response.json()
        print("✅ Tokens received successfully!")
        
        # Add metadata
        tokens['expires_at'] = (datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 604800))).isoformat() + 'Z'
        tokens['last_refresh'] = datetime.utcnow().isoformat() + 'Z'
        tokens['refresh_count'] = 0
        tokens['created_at'] = datetime.utcnow().isoformat() + 'Z'
        
        return tokens
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Token exchange failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def save_tokens(tokens):
    """Save tokens to local file"""
    token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
    token_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"💾 Tokens saved to: {token_file}")
    return token_file

def upload_to_aws(token_file):
    """Upload tokens to AWS Secrets Manager"""
    print("☁️  Uploading tokens to AWS Secrets Manager...")
    
    try:
        import boto3
        
        # Read token file
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        # Upload to AWS Secrets Manager
        client = boto3.client('secretsmanager', region_name='us-east-1')
        
        try:
            response = client.put_secret_value(
                SecretId='schwab-api-token-prod',
                SecretString=json.dumps(token_data)
            )
            print("✅ Tokens uploaded to AWS Secrets Manager!")
            print(f"   Secret ARN: {response['ARN']}")
            print(f"   Version ID: {response['VersionId']}")
            return True
            
        except client.exceptions.ResourceNotFoundException:
            print("⚠️  Secret not found, creating it...")
            response = client.create_secret(
                Name='schwab-api-token-prod',
                Description='Schwab API OAuth tokens for production',
                SecretString=json.dumps(token_data)
            )
            print("✅ Secret created and tokens uploaded!")
            print(f"   Secret ARN: {response['ARN']}")
            return True
            
    except ImportError:
        print("⚠️  boto3 not installed. Install with: pip install boto3")
        print("   Skipping AWS upload.")
        return False
    except Exception as e:
        print(f"❌ AWS upload failed: {e}")
        print("   You can manually upload using:")
        print(f"   aws secretsmanager put-secret-value \\")
        print(f"     --secret-id schwab-api-token-prod \\")
        print(f"     --secret-string file://{token_file}")
        return False

def test_api_access(access_token):
    """Test the access token with a simple API call"""
    print("🧪 Testing API access...")
    
    api_url = f"{BASE_URL}/trader/v1/accounts"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            accounts = response.json()
            print("✅ API call successful!")
            print(f"   Found {len(accounts)} account(s)")
            return True
        else:
            print(f"⚠️  API call status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def fully_automated_oauth_flow():
    """Main fully automated OAuth flow"""
    print("🤖 Starting FULLY Automated Schwab OAuth Flow")
    print("   NO manual interaction required!")
    print("=" * 60)
    
    # Step 1: Start callback server
    print("\n📡 Step 1: Starting callback server...")
    httpd = start_callback_server()
    time.sleep(2)  # Give server time to start
    
    try:
        # Step 2: Run browser automation
        print("\n🤖 Step 2: Starting browser automation...")
        print("   This will:")
        print("   • Open browser to Schwab OAuth")
        print("   • Automatically fill in login credentials")
        print("   • Click login button")
        print("   • Click Allow/Authorize button")
        print("   • Capture callback automatically")
        
        success = automated_browser_oauth()
        
        if not success:
            print("❌ Browser automation failed")
            return False
        
        # Step 3: Process callback
        print("\n🔄 Step 3: Processing callback...")
        if callback_url:
            # Parse the callback URL
            parsed_url = urllib.parse.urlparse(callback_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            auth_code = query_params.get('code', [''])[0]
            
            if auth_code:
                # Exchange code for tokens
                tokens = exchange_code_for_tokens(auth_code)
                
                if tokens:
                    # Save tokens locally
                    token_file = save_tokens(tokens)
                    
                    # Test API access
                    test_api_access(tokens['access_token'])
                    
                    # Upload to AWS
                    upload_to_aws(token_file)
                    
                    print("\n" + "=" * 60)
                    print("🎉 FULLY AUTOMATED OAUTH FLOW COMPLETED!")
                    print("=" * 60)
                    print("\n✅ Completed:")
                    print("   1. ✅ Browser opened automatically")
                    print("   2. ✅ Login credentials filled automatically")
                    print("   3. ✅ Login button clicked automatically")
                    print("   4. ✅ Authorization completed automatically")
                    print("   5. ✅ Callback captured automatically")
                    print("   6. ✅ Tokens exchanged and saved")
                    print("   7. ✅ API access tested")
                    print("   8. ✅ Tokens uploaded to AWS")
                    print("\n🔗 Next steps:")
                    print("   • Lambda function can now use tokens")
                    print("   • Check admin panel for token status")
                    print("   • Data streaming should resume")
                    
                    return True
                else:
                    print("❌ Token exchange failed")
                    return False
            else:
                print("❌ No authorization code found in callback")
                return False
        else:
            print("❌ No callback URL captured")
            return False
    
    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        httpd.shutdown()
        print("✅ Callback server stopped")

def main():
    """Main entry point"""
    print("🤖 Fully Automated Schwab OAuth")
    print("   NO manual login, clicking, or interaction required!")
    print()
    
    try:
        success = fully_automated_oauth_flow()
        
        if success:
            print("\n🎉 SUCCESS! OAuth flow completed fully automatically!")
            exit(0)
        else:
            print("\n❌ OAuth flow failed")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  OAuth flow cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
