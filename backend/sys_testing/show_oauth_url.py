#!/usr/bin/env python3
"""
Show the OAuth URL following ChatGPT's guidance.
This is the CORRECT format according to both schwab-py and ChatGPT.
"""

import urllib.parse
import os

CLIENT_ID = os.getenv('SCHWAB_APP_KEY', 'Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU')
REDIRECT_URI = os.getenv('SCHWAB_CALLBACK_URL', 'https://127.0.0.1:8182/')

# Build authorization URL (exactly as ChatGPT and schwab-py showed)
auth_url = (
    f"https://api.schwabapi.com/v1/oauth/authorize"
    f"?client_id={urllib.parse.quote(CLIENT_ID)}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&response_type=code"
)

print("=" * 70)
print("🔗 SCHWAB OAUTH AUTHORIZATION URL")
print("=" * 70)
print()
print(auth_url)
print()
print("=" * 70)
print("📋 WHAT TO DO:")
print("=" * 70)
print("1. ✅ Make sure you're logged into Schwab.com in your browser")
print("2. ✅ Copy the URL above")
print("3. ✅ Open it in your browser")
print("4. ✅ You should see an authorization/consent page (NOT a login page)")
print("5. ✅ Click 'Allow' or 'Authorize'")
print("6. ✅ You'll be redirected to https://127.0.0.1:8182/?code=XXX")
print("7. ✅ Copy the ENTIRE URL from your browser's address bar")
print("8. ✅ Run: python3 process_callback_url.py <PASTE_URL_HERE>")
print()
print("=" * 70)
print()
print("💡 KEY DIFFERENCES FROM BEFORE:")
print("   - NO 'state' parameter (ChatGPT doesn't use it)")
print("   - NO 'scope' parameter (not required)")
print("   - Uses 'response_type=code' explicitly")
print()
print("🔍 DEBUGGING:")
print("   - If this STILL leads to a login page, your Schwab app may not be")
print("     properly configured or approved in the Developer Portal")
print("   - Check: https://developer.schwab.com/dashboard")
print()

