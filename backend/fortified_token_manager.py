#!/usr/bin/env python3
"""
Fortified Token Manager with Rate Limiting and Retry Logic
Prevents token refresh issues and provides robust error handling
"""

import json
import time
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path
import structlog
from typing import Optional, Tuple, Dict, Any

# Configure structured logging
logger = structlog.get_logger()

class FortifiedTokenManager:
    def __init__(self):
        self.token_file = Path("config/schwab_token.json")
        self.app_key = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
        self.app_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
        self.base_url = "https://api.schwabapi.com"
        
        # Rate limiting protection
        self.last_refresh_attempt = 0
        self.min_refresh_interval = 60  # 1 minute minimum between attempts
        self.max_retries = 3
        self.retry_delays = [5, 15, 30]  # Exponential backoff in seconds
        
        # Token cache
        self._cached_token = None
        self._cache_timestamp = 0
        self._cache_duration = 1500  # 25 minutes (tokens expire in 30)
    
    def load_token(self) -> Tuple[Optional[Dict], Optional[str]]:
        """Load token with error handling"""
        try:
            if not self.token_file.exists():
                return None, "Token file does not exist"
            
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            return token_data, None
        except Exception as e:
            return None, f"Error loading token: {e}"
    
    def save_token(self, token_data: Dict) -> bool:
        """Save token with error handling"""
        try:
            # Ensure directory exists
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info("token_saved", file=str(self.token_file))
            return True
        except Exception as e:
            logger.error("token_save_failed", error=str(e))
            return False
    
    def is_token_valid(self, token_data: Dict) -> Tuple[bool, str]:
        """Check if token is valid and not expired"""
        if not token_data or "token" not in token_data:
            return False, "No token data"
        
        token = token_data["token"]
        
        # Check if access token exists
        if "access_token" not in token or not token["access_token"]:
            return False, "No access token"
        
        # Check expiration
        if "expires_at" in token:
            expires_at = token["expires_at"]
            current_time = int(time.time())
            
            if expires_at <= current_time:
                return False, f"Token expired {current_time - expires_at} seconds ago"
            
            # Check if token expires soon (less than 5 minutes)
            if expires_at - current_time < 300:
                return True, f"Token expires in {expires_at - current_time} seconds"
        
        return True, "Token is valid"
    
    def can_refresh_token(self) -> Tuple[bool, str]:
        """Check if we can attempt a token refresh (rate limiting)"""
        current_time = time.time()
        time_since_last_attempt = current_time - self.last_refresh_attempt
        
        if time_since_last_attempt < self.min_refresh_interval:
            wait_time = self.min_refresh_interval - time_since_last_attempt
            return False, f"Rate limited - wait {wait_time:.0f} seconds"
        
        return True, "Can attempt refresh"
    
    def refresh_token_with_retry(self, refresh_token: str) -> Tuple[bool, str, Optional[Dict]]:
        """Refresh token with exponential backoff retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info("refresh_attempt", attempt=attempt + 1, max_attempts=self.max_retries)
                
                # Check rate limiting
                can_refresh, rate_limit_msg = self.can_refresh_token()
                if not can_refresh:
                    logger.warning("rate_limited", message=rate_limit_msg)
                    return False, rate_limit_msg, None
                
                # Update last attempt time
                self.last_refresh_attempt = time.time()
                
                # Prepare request
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
                
                # Make request
                response = requests.post(
                    f"{self.base_url}/v1/oauth/token",
                    headers=headers,
                    data=data,
                    timeout=10
                )
                
                logger.info("refresh_response", 
                           status_code=response.status_code,
                           attempt=attempt + 1)
                
                if response.status_code == 200:
                    new_tokens = response.json()
                    logger.info("refresh_success", 
                               has_access_token='access_token' in new_tokens,
                               has_refresh_token='refresh_token' in new_tokens)
                    return True, "Refresh successful", new_tokens
                
                elif response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get('error', 'Unknown error')
                    logger.error("refresh_failed_400", error=error_msg, attempt=attempt + 1)
                    
                    # Don't retry on 400 errors (invalid refresh token)
                    if "invalid_grant" in error_msg.lower():
                        return False, f"Invalid refresh token: {error_msg}", None
                    return False, f"Refresh failed: {error_msg}", None
                
                elif response.status_code == 429:
                    logger.warning("rate_limited_429", attempt=attempt + 1)
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        logger.info("retrying_after_delay", delay=delay)
                        time.sleep(delay)
                        continue
                    return False, "Rate limited - max retries exceeded", None
                
                else:
                    logger.error("refresh_failed_unexpected", 
                                status_code=response.status_code,
                                response=response.text[:200],
                                attempt=attempt + 1)
                    
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        logger.info("retrying_after_delay", delay=delay)
                        time.sleep(delay)
                        continue
                    return False, f"Refresh failed: {response.status_code}", None
                
            except requests.exceptions.Timeout:
                logger.error("refresh_timeout", attempt=attempt + 1)
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info("retrying_after_delay", delay=delay)
                    time.sleep(delay)
                    continue
                return False, "Request timeout", None
                
            except Exception as e:
                logger.error("refresh_exception", error=str(e), attempt=attempt + 1)
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info("retrying_after_delay", delay=delay)
                    time.sleep(delay)
                    continue
                return False, f"Refresh error: {e}", None
        
        return False, "Max retries exceeded", None
    
    def get_valid_token(self) -> Tuple[bool, str, Optional[Dict]]:
        """Get a valid token, refreshing if necessary"""
        # Load current token
        token_data, load_error = self.load_token()
        if load_error:
            return False, f"Token load error: {load_error}", None
        
        if not token_data:
            return False, "No token data", None
        
        # Check if token is valid
        is_valid, validity_msg = self.is_token_valid(token_data)
        logger.info("token_validity_check", is_valid=is_valid, message=validity_msg)
        
        if is_valid:
            return True, "Token is valid", token_data
        
        # Token is invalid, try to refresh
        if "token" not in token_data or "refresh_token" not in token_data["token"]:
            return False, "No refresh token available - need to re-authenticate", None
        
        refresh_token = token_data["token"]["refresh_token"]
        logger.info("attempting_token_refresh")
        
        success, message, new_tokens = self.refresh_token_with_retry(refresh_token)
        
        if success and new_tokens:
            # Convert new tokens to our format
            current_time = int(time.time())
            new_token_data = {
                "creation_timestamp": current_time,
                "token": {
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens.get("refresh_token", refresh_token),  # Keep old if not provided
                    "expires_in": str(new_tokens["expires_in"]),
                    "token_type": new_tokens["token_type"],
                    "scope": new_tokens.get("scope", "api"),
                    "expires_at": current_time + new_tokens["expires_in"]
                }
            }
            
            # Save new token
            if self.save_token(new_token_data):
                logger.info("token_refreshed_and_saved")
                return True, "Token refreshed successfully", new_token_data
            else:
                return False, "Token refreshed but failed to save", new_token_data
        else:
            return False, f"Token refresh failed: {message}", None
    
    def test_api_connection(self, access_token: str) -> Tuple[bool, str]:
        """Test API connection with current token"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/v1/accounts",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "API connection successful"
            elif response.status_code == 401:
                return False, "Token invalid/expired"
            elif response.status_code == 429:
                return False, "Rate limited"
            else:
                return False, f"API error: {response.status_code} - {response.text[:200]}"
                
        except Exception as e:
            return False, f"Connection error: {e}"

def main():
    """Test the fortified token manager"""
    print("🛡️  FORTIFIED TOKEN MANAGER TEST")
    print("=" * 50)
    
    manager = FortifiedTokenManager()
    
    # Get valid token
    success, message, token_data = manager.get_valid_token()
    
    if success:
        print(f"✅ {message}")
        
        # Test API connection
        access_token = token_data["token"]["access_token"]
        api_success, api_message = manager.test_api_connection(access_token)
        
        if api_success:
            print(f"✅ {api_message}")
        else:
            print(f"❌ {api_message}")
    else:
        print(f"❌ {message}")
        print("\n💡 Next steps:")
        print("1. Run: python3 fix_oauth.py (to get refresh token)")
        print("2. Or: python3 reauth_schwab_auto.py (for automatic re-auth)")

if __name__ == "__main__":
    main()
