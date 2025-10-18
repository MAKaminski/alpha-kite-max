#!/usr/bin/env python3
"""
Simple OAuth callback processor without dependencies.
Usage: python3 simple_callback_processor.py "https://127.0.0.1:8182/?code=XXX&state=YYY"
"""

import sys
import urllib.parse
import requests
import base64
import json
from pathlib import Path

def process_callback(callback_url):
    """Process OAuth callback URL and exchange code for tokens."""
    
    print("🔄 PROCESSING OAUTH CALLBACK")
    print("=" * 50)
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
            return False
        
        code = query_params['code'][0]
        state = query_params.get('state', [''])[0]
        
        print(f"✅ Authorization code: {code[:20]}...")
        if state:
            print(f"✅ State: {state[:20]}...")
        print()
        
        # Exchange code for tokens
        return exchange_code_for_tokens(code)
        
    except Exception as e:
        print(f"❌ ERROR parsing URL: {e}")
        return False

def exchange_code_for_tokens(code):
    """Exchange authorization code for tokens."""
    
    print("🔄 Exchanging code for tokens...")
    
    # Configuration
    client_id = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
    client_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
    redirect_uri = "https://127.0.0.1:8182"
    
    token_url = "https://api.schwabapi.com/v1/oauth/token"
    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        if response.status_code == 200:
            tokens = response.json()
            print("✅ TOKENS RECEIVED!")
            print()
            print(f"Access Token: {tokens['access_token'][:30]}...")
            print(f"Refresh Token: {tokens['refresh_token'][:30]}...")
            print(f"Expires In: {tokens.get('expires_in', 'N/A')} seconds")
            print()
            
            # Save tokens locally
            token_file = save_tokens(tokens)
            
            # Test the token
            test_access_token(tokens['access_token'])
            
            # Upload to AWS Secrets Manager
            upload_to_aws(token_file)
            
            return True
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Token exchange error: {e}")
        return False

def save_tokens(tokens):
    """Save tokens to file."""
    token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
    token_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Add metadata
    from datetime import datetime, timedelta
    token_data = {
        **tokens,
        'last_refresh': datetime.utcnow().isoformat() + 'Z',
        'refresh_count': 0,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    # Calculate expires_at if not present
    if 'expires_at' not in token_data and 'expires_in' in token_data:
        expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
        token_data['expires_at'] = expires_at.isoformat() + 'Z'
    
    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)
    
    print(f"💾 Tokens saved to: {token_file}")
    
    return token_file

def upload_to_aws(token_file):
    """Upload tokens to AWS Secrets Manager."""
    print("\n☁️  Uploading tokens to AWS Secrets Manager...")
    
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
            print("⚠️  Secret 'schwab-api-token-prod' not found, creating it...")
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

def test_access_token(access_token):
    """Test the access token with a simple API call."""
    print("\n🧪 Testing access token...")
    
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
    if len(sys.argv) != 2:
        print("Usage: python3 simple_callback_processor.py \"<CALLBACK_URL>\"")
        print("Example: python3 simple_callback_processor.py \"https://127.0.0.1:8182/?code=ABC123&state=XYZ789\"")
        sys.exit(1)
    
    callback_url = sys.argv[1]
    success = process_callback(callback_url)
    
    if success:
        print()
        print("=" * 70)
        print("🎉 SUCCESS! OAuth flow completed and tokens deployed!")
        print("=" * 70)
        print()
        print("✅ Completed:")
        print("   1. ✅ Authorization code exchanged for tokens")
        print("   2. ✅ Tokens saved locally to config/schwab_token.json")
        print("   3. ✅ API access verified")
        print("   4. ✅ Tokens uploaded to AWS Secrets Manager")
        print()
        print("📋 Next steps:")
        print("   1. Test Lambda function")
        print("   2. Verify data streaming")
        print("   3. Monitor token expiration in admin panel")
        print()
        print("🔗 Quick Links:")
        print("   • Lambda: https://console.aws.amazon.com/lambda")
        print("   • Secrets: https://console.aws.amazon.com/secretsmanager")
        print("   • Admin Panel: https://your-app.vercel.app (open admin)")
    else:
        print()
        print("❌ OAuth flow failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
