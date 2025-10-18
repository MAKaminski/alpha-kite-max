#!/usr/bin/env python3
"""
Get current Schwab token status from AWS Secrets Manager.
This provides real-time token information for the frontend.
"""

import json
import boto3
from datetime import datetime, timezone
import sys
from pathlib import Path

def get_token_from_aws():
    """Get token from AWS Secrets Manager."""
    try:
        client = boto3.client('secretsmanager', region_name='us-east-1')
        response = client.get_secret_value(SecretId='schwab-api-token-prod')
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Error fetching from AWS: {e}")
        return None

def get_token_from_local():
    """Get token from local file (for development)."""
    token_file = Path(__file__).parent.parent / 'config' / 'schwab_token.json'
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading local token: {e}")
    return None

def calculate_token_status(token_data):
    """Calculate token status and timing information."""
    if not token_data:
        return {
            "error": "No token data available",
            "is_valid": False
        }
    
    now = datetime.now(timezone.utc)
    
    # Parse expiration time
    try:
        if 'expires_at' in token_data:
            expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        elif 'expires_in' in token_data:
            # Calculate from expires_in seconds
            expires_at = now + timedelta(seconds=token_data['expires_in'])
        else:
            expires_at = now  # Assume expired if no expiration info
        
        expires_in_seconds = int((expires_at - now).total_seconds())
        is_valid = expires_in_seconds > 0
        
    except Exception as e:
        print(f"Error parsing expiration: {e}")
        expires_in_seconds = 0
        is_valid = False
        expires_at = now
    
    # Calculate refresh token status (assume 90 days from last refresh)
    last_refresh = token_data.get('last_refresh', token_data.get('created_at', now.isoformat()))
    try:
        if isinstance(last_refresh, str):
            refresh_time = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
        else:
            refresh_time = now
    except:
        refresh_time = now
    
    refresh_expires_at = refresh_time + timedelta(days=90)
    refresh_in_seconds = int((refresh_expires_at - now).total_seconds())
    refresh_valid = refresh_in_seconds > 0
    
    return {
        "access_token": token_data.get('access_token', ''),
        "refresh_token": token_data.get('refresh_token', ''),
        "expires_at": expires_at.isoformat(),
        "token_type": token_data.get('token_type', 'Bearer'),
        "scope": token_data.get('scope', 'api'),
        "last_refresh": last_refresh,
        "refresh_count": token_data.get('refresh_count', 0),
        "is_valid": is_valid,
        "expires_in_seconds": max(0, expires_in_seconds),
        "refresh_in_seconds": max(0, refresh_in_seconds),
        "refresh_valid": refresh_valid
    }

def main():
    """Get and display token status."""
    print("🔍 SCHWAB TOKEN STATUS")
    print("=" * 50)
    
    # Try AWS first, then local
    token_data = get_token_from_aws()
    if not token_data:
        print("AWS not available, trying local file...")
        token_data = get_token_from_local()
    
    if not token_data:
        print("❌ No token data found")
        print("   - Check AWS Secrets Manager")
        print("   - Check local config/schwab_token.json")
        print("   - Run OAuth flow to get new token")
        sys.exit(1)
    
    status = calculate_token_status(token_data)
    
    if 'error' in status:
        print(f"❌ Error: {status['error']}")
        sys.exit(1)
    
    print(f"✅ Token Status: {'VALID' if status['is_valid'] else 'EXPIRED'}")
    print(f"   Expires in: {status['expires_in_seconds']} seconds")
    print(f"   Refresh token: {'VALID' if status['refresh_valid'] else 'EXPIRED'}")
    print(f"   Last refresh: {status['last_refresh']}")
    print(f"   Refresh count: {status['refresh_count']}")
    
    # Output JSON for API consumption
    print("\n" + "=" * 50)
    print("JSON OUTPUT (for API):")
    print("=" * 50)
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    from datetime import timedelta
    main()
