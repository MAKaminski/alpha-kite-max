#!/usr/bin/env python3
"""
Process the callback URL from the fixed OAuth flow.
Usage: python3 process_fixed_callback.py "https://127.0.0.1:8182/?code=XXX&state=YYY"
"""

import sys
import urllib.parse
from fixed_oauth_flow import FixedSchwabOAuth

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 process_fixed_callback.py \"<CALLBACK_URL>\"")
        print("Example: python3 process_fixed_callback.py \"https://127.0.0.1:8182/?code=ABC123&state=XYZ789\"")
        sys.exit(1)
    
    callback_url = sys.argv[1]
    
    print("=" * 70)
    print("🔄 PROCESSING FIXED OAUTH CALLBACK")
    print("=" * 70)
    print()
    print(f"Callback URL: {callback_url}")
    print()
    
    # Parse the callback URL
    try:
        parsed = urllib.parse.urlparse(callback_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        print("📋 Parsed Parameters:")
        for key, value in query_params.items():
            print(f"   {key}: {value[0] if value else 'None'}")
        print()
        
        if 'code' not in query_params:
            print("❌ ERROR: No 'code' parameter found in URL")
            if 'error' in query_params:
                print(f"   Error: {query_params['error'][0]}")
                if 'error_description' in query_params:
                    print(f"   Description: {query_params['error_description'][0]}")
            sys.exit(1)
        
        code = query_params['code'][0]
        state = query_params.get('state', [''])[0]
        
        print(f"✅ Authorization code: {code[:20]}...")
        if state:
            print(f"✅ State: {state[:20]}...")
        print()
        
        # Exchange code for tokens
        oauth = FixedSchwabOAuth()
        tokens = oauth.exchange_code_for_tokens(code)
        
        if tokens:
            print()
            print("=" * 70)
            print("🎉 SUCCESS! OAuth flow completed!")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Upload tokens to AWS Secrets Manager:")
            print("   aws secretsmanager put-secret-value \\")
            print("     --secret-id schwab-api-token-prod \\")
            print("     --secret-string file://config/schwab_token.json")
            print()
            print("2. Test Lambda function")
            print("3. Verify data streaming")
        else:
            print("❌ Failed to exchange code for tokens")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
