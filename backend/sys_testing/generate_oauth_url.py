#!/usr/bin/env python3
"""
Generate Schwab OAuth authorization URL
"""

import sys
import urllib.parse
from pathlib import Path

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
from schwab_integration.config import SchwabConfig

def generate_oauth_url():
    """Generate the OAuth authorization URL"""
    
    config = SchwabConfig()
    
    # OAuth parameters
    params = {
        'client_id': config.app_key,
        'redirect_uri': 'https://127.0.0.1:8182',
        'response_type': 'code',
        'scope': 'api'
    }
    
    # Build the URL
    auth_url = f"{config.base_url}/v1/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    print("🚀 SCHWAB OAUTH FLOW")
    print("=" * 50)
    print()
    print("1️⃣  START CALLBACK SERVER:")
    print("   python oauth_callback_server.py")
    print()
    print("2️⃣  CLICK THIS URL (while logged into Schwab.com):")
    print(f"   {auth_url}")
    print()
    print("3️⃣  AFTER AUTHORIZATION, PROCESS THE CALLBACK:")
    print("   python process_oauth_callback.py")
    print()
    print("💡 Make sure you're logged into schwab.com first!")

if __name__ == "__main__":
    generate_oauth_url()
