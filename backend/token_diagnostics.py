#!/usr/bin/env python3
"""
Comprehensive Token Diagnostics System
Identifies token issues, rate limiting, and provides solutions
"""

import json
import time
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path
import structlog

# Configure structured logging
logger = structlog.get_logger()

class TokenDiagnostics:
    def __init__(self):
        self.token_file = Path("config/schwab_token.json")
        self.app_key = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
        self.app_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
        self.base_url = "https://api.schwabapi.com"
        
    def load_token(self):
        """Load token from file with error handling"""
        try:
            if not self.token_file.exists():
                return None, "Token file does not exist"
            
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            return token_data, None
        except Exception as e:
            return None, f"Error loading token: {e}"
    
    def analyze_token_structure(self, token_data):
        """Analyze token structure and identify issues"""
        issues = []
        warnings = []
        
        if not token_data:
            issues.append("No token data")
            return issues, warnings
        
        # Check for required fields
        if "token" not in token_data:
            issues.append("Missing 'token' field in token data")
            return issues, warnings
        
        token = token_data["token"]
        
        # Check access token
        if "access_token" not in token:
            issues.append("Missing 'access_token'")
        elif not token["access_token"]:
            issues.append("Empty 'access_token'")
        
        # Check refresh token
        if "refresh_token" not in token:
            issues.append("Missing 'refresh_token' - CRITICAL")
        elif not token["refresh_token"]:
            issues.append("Empty 'refresh_token' - CRITICAL")
        
        # Check expiration
        if "expires_at" in token:
            expires_at = token["expires_at"]
            current_time = int(time.time())
            
            if expires_at <= current_time:
                issues.append(f"Token expired {current_time - expires_at} seconds ago")
            elif expires_at - current_time < 300:  # Less than 5 minutes
                warnings.append(f"Token expires in {expires_at - current_time} seconds")
        else:
            warnings.append("No 'expires_at' field")
        
        # Check token type
        if token.get("token_type") != "Bearer":
            warnings.append(f"Unexpected token_type: {token.get('token_type')}")
        
        # Check scope
        if "scope" not in token:
            warnings.append("No 'scope' field")
        elif token["scope"] != "api":
            warnings.append(f"Unexpected scope: {token['scope']}")
        
        return issues, warnings
    
    def test_token_validity(self, access_token):
        """Test if token is valid by making a simple API call"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Test with a simple endpoint
            response = requests.get(
                f"{self.base_url}/v1/accounts",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Token is valid"
            elif response.status_code == 401:
                return False, "Token is invalid/expired"
            elif response.status_code == 429:
                return False, "Rate limited - too many requests"
            else:
                return False, f"Unexpected response: {response.status_code} - {response.text[:200]}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, f"Request error: {e}"
    
    def test_refresh_token(self, refresh_token):
        """Test if refresh token works"""
        try:
            credentials = f"{self.app_key}:{self.app_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            response = requests.post(
                f"{self.base_url}/v1/oauth/token",
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                new_tokens = response.json()
                return True, "Refresh token works", new_tokens
            elif response.status_code == 400:
                error_data = response.json()
                return False, f"Refresh failed: {error_data.get('error', 'Unknown error')}", None
            elif response.status_code == 429:
                return False, "Rate limited on refresh", None
            else:
                return False, f"Refresh failed: {response.status_code} - {response.text[:200]}", None
                
        except Exception as e:
            return False, f"Refresh error: {e}", None
    
    def check_rate_limits(self):
        """Check if we're hitting rate limits"""
        # This would require tracking API calls over time
        # For now, we'll check recent token refresh attempts
        return "Rate limit checking not implemented yet"
    
    def generate_diagnostic_report(self):
        """Generate comprehensive diagnostic report"""
        print("🔍 SCHWAB TOKEN DIAGNOSTICS")
        print("=" * 60)
        
        # Load token
        token_data, load_error = self.load_token()
        if load_error:
            print(f"❌ Token Load Error: {load_error}")
            return
        
        print(f"📁 Token file: {self.token_file}")
        print(f"📅 Loaded at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Analyze structure
        issues, warnings = self.analyze_token_structure(token_data)
        
        print("🔍 TOKEN STRUCTURE ANALYSIS")
        print("-" * 40)
        
        if issues:
            for issue in issues:
                print(f"❌ {issue}")
        else:
            print("✅ Token structure looks good")
        
        if warnings:
            for warning in warnings:
                print(f"⚠️  {warning}")
        
        print()
        
        # Test token validity
        if token_data and "token" in token_data and "access_token" in token_data["token"]:
            access_token = token_data["token"]["access_token"]
            
            print("🧪 TOKEN VALIDITY TEST")
            print("-" * 40)
            
            is_valid, message = self.test_token_validity(access_token)
            if is_valid:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
            
            print()
            
            # Test refresh token
            if "refresh_token" in token_data["token"]:
                refresh_token = token_data["token"]["refresh_token"]
                
                print("🔄 REFRESH TOKEN TEST")
                print("-" * 40)
                
                refresh_works, refresh_message, new_tokens = self.test_refresh_token(refresh_token)
                if refresh_works:
                    print(f"✅ {refresh_message}")
                    if new_tokens:
                        print(f"   New access token: {new_tokens.get('access_token', 'N/A')[:20]}...")
                        print(f"   New refresh token: {new_tokens.get('refresh_token', 'N/A')[:20]}...")
                else:
                    print(f"❌ {refresh_message}")
            else:
                print("❌ No refresh token to test")
        
        print()
        print("💡 RECOMMENDATIONS")
        print("-" * 40)
        
        if issues:
            if "Missing 'refresh_token'" in issues or "Empty 'refresh_token'" in issues:
                print("🔴 CRITICAL: Need to re-authenticate to get refresh token")
                print("   Run: python3 fix_oauth.py")
            elif "Token expired" in issues:
                print("🟡 Token expired - try refreshing first")
                print("   Run: python3 refresh_schwab_auth.py")
            else:
                print("🟡 Fix token structure issues first")
        else:
            print("✅ Token appears healthy")
        
        print()
        print("🛡️  RATE LIMITING PROTECTION")
        print("-" * 40)
        print("• Wait at least 1 minute between token refresh attempts")
        print("• Implement exponential backoff for retries")
        print("• Cache successful tokens for 25+ minutes")
        print("• Monitor API response codes for 429 (rate limited)")

def main():
    diagnostics = TokenDiagnostics()
    diagnostics.generate_diagnostic_report()

if __name__ == "__main__":
    main()
