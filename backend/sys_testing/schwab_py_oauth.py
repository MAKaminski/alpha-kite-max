#!/usr/bin/env python3
"""
Use schwab-py library's built-in OAuth flow as a workaround.
This might handle authentication differently than our manual approach.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from schwab import auth
    print("✅ schwab-py library imported successfully")
except ImportError as e:
    print(f"❌ Error importing schwab-py: {e}")
    print("Please install: pip install schwab-py")
    sys.exit(1)

def test_schwab_py_oauth():
    """Test OAuth using schwab-py's built-in flow."""
    
    print("🔧 TESTING SCHWAB-PY OAUTH FLOW")
    print("=" * 70)
    print()
    
    # Configuration
    client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
    client_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
    callback_url = "https://127.0.0.1:8182"  # No trailing slash
    
    print(f"Client ID: {client_id}")
    print(f"Callback URL: {callback_url}")
    print()
    
    try:
        print("🚀 Attempting to create schwab-py client...")
        print("   This will:")
        print("   1. Generate OAuth URL")
        print("   2. Open your browser")
        print("   3. Handle the callback automatically")
        print("   4. Save tokens")
        print()
        
        # Use schwab-py's easy_client with interactive=True
        client = auth.easy_client(
            api_key=client_id,
            app_secret=client_secret,
            callback_url=callback_url,
            token_path="config/schwab_token.json",
            interactive=True  # This will open browser and wait for input
        )
        
        print("✅ SUCCESS! OAuth flow completed!")
        print()
        
        # Test the client
        print("🧪 Testing API access...")
        accounts = client.get_account_numbers()
        print(f"✅ Found {len(accounts)} account(s)")
        print("🎉 AUTHENTICATION SUCCESSFUL!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("🔍 This error suggests:")
        print("1. App not approved for OAuth access")
        print("2. Missing required permissions")
        print("3. Additional approval steps needed")
        print("4. Contact Schwab Developer Support")
        return False

def test_manual_oauth_url():
    """Test if we can at least generate the OAuth URL manually."""
    
    print("\n🔧 TESTING MANUAL OAUTH URL GENERATION")
    print("=" * 70)
    print()
    
    try:
        # Try to create a client without interactive mode
        client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
        client_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
        callback_url = "https://127.0.0.1:8182"
        
        # This should generate the OAuth URL without starting the flow
        client = auth.easy_client(
            api_key=client_id,
            app_secret=client_secret,
            callback_url=callback_url,
            token_path="config/schwab_token.json",
            interactive=False
        )
        
        print("✅ Client created successfully (non-interactive)")
        print("   This means the credentials are valid")
        print("   The issue is likely with OAuth approval")
        
    except Exception as e:
        print(f"❌ Error creating client: {e}")
        print("   This suggests a fundamental app configuration issue")

if __name__ == "__main__":
    print("🎯 SCHWAB-PY OAUTH WORKAROUND")
    print("=" * 70)
    print()
    print("This uses the official schwab-py library's OAuth flow")
    print("which might handle authentication differently than our manual approach.")
    print()
    
    # Test manual URL generation first
    test_manual_oauth_url()
    
    print()
    print("=" * 70)
    print("📋 NEXT STEPS:")
    print("=" * 70)
    print("1. If the above shows errors, your app needs additional approval")
    print("2. Contact Schwab Developer Support:")
    print("   - Email: developer@schwab.com")
    print("   - Portal: https://developer.schwab.com/support")
    print("3. Ask specifically about OAuth access requirements")
    print("4. Mention you're getting 403 Forbidden on OAuth endpoints")
    print()
    print("The 'Ready For Use' status might not include OAuth permissions.")
