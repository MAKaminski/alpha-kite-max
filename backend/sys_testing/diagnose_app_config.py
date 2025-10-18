#!/usr/bin/env python3
"""
Diagnose Schwab app configuration issues.
This will help identify why the OAuth flow is failing.
"""

import requests
import urllib.parse
import json

def test_oauth_endpoint():
    """Test the OAuth endpoint with different configurations."""
    
    client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
    redirect_uri = "https://127.0.0.1:8182"
    
    print("🔍 DIAGNOSING SCHWAB APP CONFIGURATION")
    print("=" * 70)
    print()
    
    # Test different OAuth URL formats
    test_cases = [
        {
            "name": "Basic OAuth (no state)",
            "url": f"https://api.schwabapi.com/v1/oauth/authorize?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code"
        },
        {
            "name": "With state parameter",
            "url": f"https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&state=test123"
        },
        {
            "name": "With scope parameter",
            "url": f"https://api.schwabapi.com/v1/oauth/authorize?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope=api"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test_case['name']}")
        print(f"   URL: {test_case['url']}")
        
        try:
            response = requests.get(test_case['url'], allow_redirects=True, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                # Check if it's an HTML page (login/authorization)
                if '<html' in response.text.lower() or '<title>' in response.text.lower():
                    if 'login' in response.text.lower():
                        print("   Result: ❌ Login page (not authorization page)")
                    elif 'authorize' in response.text.lower() or 'consent' in response.text.lower():
                        print("   Result: ✅ Authorization page")
                    else:
                        print("   Result: ❓ Unknown HTML page")
                else:
                    print("   Result: ❓ Non-HTML response")
            elif response.status_code == 400:
                print("   Result: ❌ Bad Request (check parameters)")
            elif response.status_code == 401:
                print("   Result: ❌ Unauthorized (check client credentials)")
            elif response.status_code == 403:
                print("   Result: ❌ Forbidden (app not approved)")
            elif response.status_code == 500:
                print("   Result: ❌ Server Error")
            else:
                print(f"   Result: ❓ Unexpected status {response.status_code}")
                
            # Show first 200 characters of response
            content_preview = response.text[:200].replace('\n', ' ').strip()
            print(f"   Preview: {content_preview}...")
            
        except Exception as e:
            print(f"   Result: ❌ Error: {e}")
        
        print()
    
    print("=" * 70)
    print("🔍 DIAGNOSTIC SUMMARY:")
    print("=" * 70)
    print()
    print("If all tests show 'Login page' instead of 'Authorization page':")
    print("1. ❌ App may not be properly approved for production")
    print("2. ❌ Missing required API product subscriptions")
    print("3. ❌ App configuration issue in Developer Portal")
    print("4. ❌ Account restrictions or additional approval needed")
    print()
    print("If you see 'Access Denied' or 'Forbidden':")
    print("1. ❌ App definitely not approved for production use")
    print("2. ❌ Need to contact Schwab support")
    print("3. ❌ May need to re-apply for production access")
    print()
    print("NEXT STEPS:")
    print("1. Check your Developer Portal dashboard")
    print("2. Verify app status is 'Ready For Use'")
    print("3. Confirm you have 'Accounts and Trading Production' API")
    print("4. Contact Schwab support if app appears approved but OAuth fails")

def check_app_requirements():
    """Check if the app meets all requirements."""
    
    print("📋 SCHWAB APP REQUIREMENTS CHECKLIST:")
    print("=" * 70)
    print()
    
    requirements = [
        "✅ App registered in Developer Portal",
        "✅ Client ID: Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU",
        "✅ Callback URL: https://127.0.0.1:8182 (no trailing slash)",
        "❓ App status: 'Ready For Use' (verify in portal)",
        "❓ Environment: Production (not Sandbox)",
        "❓ API Products: 'Accounts and Trading Production' + 'Market Data Production'",
        "❓ App approval: Fully approved by Schwab",
        "❓ Account verification: Account verified for API access"
    ]
    
    for req in requirements:
        print(f"   {req}")
    
    print()
    print("🔍 VERIFICATION STEPS:")
    print("1. Go to https://developer.schwab.com/dashboard")
    print("2. Check your 'kite-trader' app details")
    print("3. Verify ALL requirements above are met")
    print("4. If any are missing, contact Schwab support")

if __name__ == "__main__":
    test_oauth_endpoint()
    print()
    check_app_requirements()
