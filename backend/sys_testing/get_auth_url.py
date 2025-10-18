#!/usr/bin/env python3
"""
Get the Schwab authorization URL without running the full flow.
You can click this URL in your browser manually.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schwab_integration.config import SchwabConfig
import urllib.parse

def main():
    config = SchwabConfig()
    
    # Build the authorization URL manually
    params = {
        'response_type': 'code',
        'client_id': config.app_key,
        'redirect_uri': config.callback_url,
    }
    
    base_url = "https://api.schwabapi.com/v1/oauth/authorize"
    auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    print("\n" + "="*70)
    print("SCHWAB AUTHORIZATION URL")
    print("="*70)
    print()
    print("👉 Click this URL (or copy/paste into your browser):")
    print()
    print(auth_url)
    print()
    print("="*70)
    print()
    print("What will happen:")
    print("  1. Browser opens Schwab authorization page")
    print("  2. If logged in: Just click 'Allow'")
    print("  3. If not logged in: Log in first, then click 'Allow'")
    print("  4. Browser redirects to callback URL")
    print()
    print("The callback URL will look like:")
    print("  https://127.0.0.1:8182/?code=ABC123...&session=XYZ789...")
    print()
    print("📋 Once you have the callback URL, run:")
    print("  python3 process_callback.py '<paste-full-url-here>'")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

