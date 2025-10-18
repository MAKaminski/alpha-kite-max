#!/usr/bin/env python3
"""
Test script to verify the callback URL is working
"""

import requests
import json

def test_callback_server():
    """Test if the callback server is responding"""
    
    print("🧪 Testing OAuth Callback Server")
    print("=" * 50)
    
    # Test if server is running
    try:
        response = requests.get("http://127.0.0.1:8182", timeout=5)
        print(f"✅ Server is responding: {response.status_code}")
        print(f"📄 Response: {response.text[:200]}...")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running on port 8182")
        print("💡 Start the server with: python callback_8182_server.py")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_oauth_url():
    """Test the OAuth URL (this will open browser)"""
    
    print("\n🌐 Testing OAuth URL")
    print("=" * 50)
    
    oauth_url = "https://api.schwabapi.com/v1/oauth/authorize?client_id=Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU&redirect_uri=https%3A%2F%2F127.0.0.1%3A8182&response_type=code&scope=api"
    
    print(f"🔗 OAuth URL: {oauth_url}")
    print("\n📋 Instructions:")
    print("1. Make sure callback server is running")
    print("2. Click the OAuth URL above")
    print("3. You should see an authorization page (not login)")
    print("4. Click 'Allow' or 'Authorize'")
    print("5. You'll be redirected to http://127.0.0.1:8182")
    print("6. Check the callback server console for the authorization code")
    
    # Try to open in browser (optional)
    try:
        import webbrowser
        webbrowser.open(oauth_url)
        print("\n🚀 Opened OAuth URL in your default browser")
    except:
        print("\n💡 Copy and paste the OAuth URL into your browser")

if __name__ == "__main__":
    # Test server first
    server_running = test_callback_server()
    
    if server_running:
        # Test OAuth URL
        test_oauth_url()
    else:
        print("\n❌ Cannot test OAuth URL - callback server is not running")
        print("🚀 Start the server first, then run this test again")
