#!/usr/bin/env python3
"""
Comprehensive OAuth debugging script.
This will test every step of the OAuth flow and provide detailed error information.
"""

import sys
import os
import urllib.parse
import requests
import base64
import json
from pathlib import Path

def test_oauth_url_generation():
    """Test OAuth URL generation."""
    print("🔧 TESTING OAUTH URL GENERATION")
    print("=" * 50)
    
    client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
    redirect_uri = "https://127.0.0.1:8182"
    
    # Test different URL formats
    urls = [
        {
            "name": "Basic OAuth",
            "url": f"https://api.schwabapi.com/v1/oauth/authorize?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code"
        },
        {
            "name": "With state",
            "url": f"https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&state=test123"
        }
    ]
    
    for test in urls:
        print(f"\n📋 {test['name']}:")
        print(f"   URL: {test['url']}")
        
        try:
            response = requests.get(test['url'], allow_redirects=True, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                if 'login' in response.text.lower():
                    print("   Result: ❌ Login page (not authorization)")
                elif 'authorize' in response.text.lower() or 'consent' in response.text.lower():
                    print("   Result: ✅ Authorization page")
                else:
                    print("   Result: ❓ Unknown response")
            elif response.status_code == 403:
                print("   Result: ❌ Forbidden (app not approved)")
            else:
                print(f"   Result: ❓ Status {response.status_code}")
                
        except Exception as e:
            print(f"   Result: ❌ Error: {e}")

def test_callback_server():
    """Test if callback server is working."""
    print("\n🔧 TESTING CALLBACK SERVER")
    print("=" * 50)
    
    try:
        response = requests.get("http://127.0.0.1:8182", timeout=5)
        print(f"✅ Callback server responding: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Callback server not responding")
        return False
    except Exception as e:
        print(f"❌ Callback server error: {e}")
        return False

def test_token_exchange():
    """Test token exchange with a dummy code."""
    print("\n🔧 TESTING TOKEN EXCHANGE")
    print("=" * 50)
    
    client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
    client_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
    redirect_uri = "https://127.0.0.1:8182"
    
    token_url = "https://api.schwabapi.com/v1/oauth/token"
    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Test with dummy code (will fail but shows if endpoint is accessible)
    data = {
        "grant_type": "authorization_code",
        "code": "dummy_code_123",
        "redirect_uri": redirect_uri
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        print(f"Token endpoint status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 400:
            print("✅ Token endpoint accessible (400 expected for dummy code)")
        elif response.status_code == 403:
            print("❌ Token endpoint forbidden (app not approved)")
        else:
            print(f"❓ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Token exchange error: {e}")

def test_environment():
    """Test environment configuration."""
    print("\n🔧 TESTING ENVIRONMENT")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        print("✅ .env file exists")
        
        # Read and check key values
        with open(env_file, 'r') as f:
            content = f.read()
            
        if 'SCHWAB_APP_KEY' in content:
            print("✅ SCHWAB_APP_KEY found in .env")
        else:
            print("❌ SCHWAB_APP_KEY missing from .env")
            
        if 'SCHWAB_APP_SECRET' in content:
            print("✅ SCHWAB_APP_SECRET found in .env")
        else:
            print("❌ SCHWAB_APP_SECRET missing from .env")
            
        if 'SCHWAB_BASE_URL=https://api.schwabapi.com' in content:
            print("✅ SCHWAB_BASE_URL correct")
        else:
            print("❌ SCHWAB_BASE_URL incorrect")
            
        if 'SCHWAB_CALLBACK_URL=https://127.0.0.1:8182' in content:
            print("✅ SCHWAB_CALLBACK_URL correct (no trailing slash)")
        else:
            print("❌ SCHWAB_CALLBACK_URL incorrect")
    else:
        print("❌ .env file not found")

def test_network_connectivity():
    """Test network connectivity to Schwab API."""
    print("\n🔧 TESTING NETWORK CONNECTIVITY")
    print("=" * 50)
    
    endpoints = [
        "https://api.schwabapi.com",
        "https://api.schwabapi.com/v1/oauth/authorize",
        "https://api.schwabapi.com/v1/oauth/token"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"✅ {endpoint}: {response.status_code}")
        except requests.exceptions.SSLError as e:
            print(f"❌ {endpoint}: SSL Error - {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ {endpoint}: Connection Error - {e}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def main():
    """Run all diagnostic tests."""
    print("🔍 COMPREHENSIVE OAUTH DEBUGGING")
    print("=" * 70)
    print()
    
    # Run all tests
    test_environment()
    test_network_connectivity()
    test_oauth_url_generation()
    test_callback_server()
    test_token_exchange()
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    print()
    print("If you see 403 Forbidden errors:")
    print("1. ❌ App not approved for OAuth access")
    print("2. ❌ Contact Schwab Developer Support")
    print("3. ❌ Check for additional approval requirements")
    print()
    print("If you see connection errors:")
    print("1. ❌ Network/firewall issues")
    print("2. ❌ DNS resolution problems")
    print("3. ❌ SSL certificate issues")
    print()
    print("If callback server not responding:")
    print("1. ❌ Port 8182 in use by another process")
    print("2. ❌ Firewall blocking local connections")
    print("3. ❌ Python script crashed")

if __name__ == "__main__":
    main()
