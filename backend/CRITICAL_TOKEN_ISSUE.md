# CRITICAL: Schwab Token Missing Refresh Token

## The Problem

**Every token we generate is missing `refresh_token` field!**

Current token structure:
```json
{
  "token": {
    "access_token": "...",
    "expires_in": "3600",
    "expires_at": 1234567890
    // ❌ MISSING: "refresh_token": "..."
  }
}
```

This causes:
- Token works for 1 hour only
- Cannot be refreshed automatically
- Lambda fails after 1 hour
- Must re-auth every hour (not viable!)

## Root Cause

The schwab-py library's `client_from_manual_flow()` is not requesting the `offline_access` scope or using the correct OAuth grant type to receive a refresh token.

## Potential Solutions

### Solution 1: Check Schwab App Configuration

The Schwab Developer Portal app might not be configured for refresh tokens.

**Action Required** (YOU must do this):
1. Go to https://developer.schwab.com/
2. Click "My Apps"
3. Select your app (Os3C2znH...)
4. Check settings:
   - ✅ "Refresh Token" enabled?
   - ✅ Grant type includes "authorization_code"?
   - ✅ Token lifetime set to maximum?
5. If not enabled, enable and save
6. Re-run auth flow

### Solution 2: Use Different Auth Method

The schwab-py library might have a bug or limitation. Try using the raw OAuth flow:

**File**: `backend/manual_oauth.py` (needs to be created)

```python
import requests
import urllib.parse

# Step 1: Generate auth URL with offline_access scope
params = {
    'response_type': 'code',
    'client_id': 'YOUR_APP_KEY',
    'redirect_uri': 'https://127.0.0.1:8182/',
    'scope': 'api offline_access',  # Request offline access for refresh token
}

auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?{urllib.parse.urlencode(params)}"
print("Go to:", auth_url)

# Step 2: After you authorize, paste callback URL
callback = input("Paste callback URL: ")
code = urllib.parse.parse_qs(urllib.parse.urlparse(callback).query)['code'][0]

# Step 3: Exchange code for tokens
token_response = requests.post(
    'https://api.schwabapi.com/v1/oauth/token',
    auth=(APP_KEY, APP_SECRET),
    data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'https://127.0.0.1:8182/',
    }
)

tokens = token_response.json()
print("Tokens:", tokens)
# Check if 'refresh_token' is present!
```

### Solution 3: Contact Schwab Support

If refresh tokens still aren't returned:

**Email**: developer.support@schwab.com

**Subject**: "Refresh token not returned in OAuth flow"

**Body**:
```
Hello,

I'm using the Schwab API with App Key Os3C2znH... and the schwab-py Python library.

When completing the OAuth authorization flow, I receive an access_token
but NO refresh_token in the response.

Current token response:
{
  "access_token": "...",
  "expires_in": "3600",
  "token_type": "Bearer",
  "scope": "api"
}

Expected:
{
  "access_token": "...",
  "refresh_token": "...",  <-- MISSING
  "expires_in": "3600"
}

Questions:
1. Does my app need specific configuration to receive refresh tokens?
2. Is there a required scope I'm missing?
3. Are refresh tokens available for my account type?

Thank you!
```

## Immediate Workaround

### Option A: Re-auth Every Hour
**Not recommended** - extremely impractical

### Option B: Use Different API
**Check if Schwab offers**:
- API keys (instead of OAuth)
- Service account tokens
- Longer-lived credentials

### Option C: Manual Data Collection
Until token issue is fixed:
```bash
# Set up hourly cron job on your local machine
0 * * * * cd /path/to/backend && python3 main.py --ticker QQQ --days 1
```

This downloads data locally (not ideal but works)

## What YOU Need to Do

**CRITICAL**: Check your Schwab Developer Portal app settings NOW

1. Go to: https://developer.schwab.com/
2. My Apps → Your App
3. Look for:
   - "Refresh Token" setting
   - "Token Configuration"
   - "OAuth Grant Types"
4. Enable "Refresh Token" if it's off
5. Screenshot the settings and share

**If refresh tokens aren't available for your app type**, we need to contact Schwab support or find an alternative approach.

---

**This is blocking everything. The token structure is fundamentally incomplete.**

