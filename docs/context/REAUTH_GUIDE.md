# Schwab Re-Authentication Guide

## The Problem

Your current token is **missing the `refresh_token` field**. This is why:
- Token refresh appears to succeed in Lambda
- But API calls immediately fail with `InvalidTokenError`
- The token can't actually be refreshed without a refresh_token

## Current Token (Invalid)
```json
{
  "token": {
    "access_token": "D3rXH98xv5AJ53inX1ZdjyQ5l86e",
    "expires_in": "3600",
    "expires_at": 1760562700,
    // ❌ MISSING: "refresh_token": "..."
  }
}
```

## Required Token (Valid)
```json
{
  "token": {
    "access_token": "...",
    "refresh_token": "...",  // ✅ NEEDED
    "expires_in": "3600",
    "expires_at": 1760562700
  }
}
```

---

## Re-Authentication Steps

### Option 1: Interactive Script (Recommended)

**I'll run commands, you execute manual steps:**

#### Step 1: Run the re-auth script
```bash
cd /Users/makaminski1337/Developer/alpha-kite-max/backend
python reauth_schwab_auto.py
```

#### Step 2: You'll see output like:
```
🔐 Starting OAuth flow...

Go to this URL in your browser:
https://api.schwab.com/v1/oauth/authorize?client_id=Os3C2znH...

After authorizing, paste the full callback URL here:
```

#### Step 3: Click the URL
- Browser will open Schwab login
- Enter your Schwab credentials
- Click "Allow" to authorize

#### Step 4: Copy the callback URL
After clicking Allow, you'll be redirected to something like:
```
https://127.0.0.1:8182/?code=ABC123...&session=XYZ789...
```

**Copy the ENTIRE URL** (including `https://` and all parameters)

#### Step 5: Paste it back in the terminal
The script will:
- Exchange the code for tokens
- Save to `config/schwab_token.json`
- Verify it has `refresh_token`
- Show you the AWS command to upload it

### Option 2: Manual OAuth Flow

If the script doesn't work, here's the manual process:

#### 1. Delete old token
```bash
cd backend
rm config/schwab_token.json
```

#### 2. Run any Schwab client script
```bash
python test_paper_trading.py
```

#### 3. Follow the OAuth flow
The library will print a URL - click it and authorize

#### 4. Verify token has refresh_token
```bash
cat config/schwab_token.json | jq .token.refresh_token
```

Should show a long string, not `null`

---

## After Getting Valid Token

### 1. Test It Locally

```bash
cd backend
python test_paper_trading.py
```

**Expected output**:
```
✓ Account found!
✓ Option chains retrieved successfully
```

### 2. Upload to AWS Secrets Manager

```bash
aws secretsmanager update-secret \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1
```

**Expected output**:
```json
{
    "ARN": "arn:aws:secretsmanager:us-east-1:...:secret:schwab-api-token-prod-...",
    "Name": "schwab-api-token-prod",
    "VersionId": "..."
}
```

### 3. Verify Upload

```bash
aws secretsmanager get-secret-value \
  --secret-id schwab-api-token-prod \
  --query SecretString \
  --output text | jq .token.refresh_token
```

Should show the refresh_token string

### 4. Test Lambda

```bash
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --region us-east-1 \
  --payload '{}' \
  response.json

cat response.json
```

**Expected output** (in response.json):
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Data updated\", \"ticker\": \"QQQ\", \"data_points\": 390}"
}
```

### 5. Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 5m
```

**Look for**:
```json
{"event": "price_history_fetched", "candles_count": 390}  // ✅ SUCCESS
{"event": "equity_data_inserted", "count": 390}
{"event": "indicators_inserted", "count": 390}
```

**Should NOT see**:
```json
{"event": "token_invalid"}  // ❌ OLD ERROR
```

### 6. Verify Data in Supabase

```bash
python check_data_status.py
```

**Expected output**:
```
✅ Found data for 1 day(s):

  📅 2025-10-16:
     • Data points: 390
     • Time range: 09:30:00 to 16:00:00
```

---

## Troubleshooting

### Issue: "No module named 'schwab'"

**Fix**:
```bash
cd backend
pip install -r requirements.txt
# OR with uv
uv pip install -r requirements.txt
```

### Issue: "Browser doesn't open"

**Manual steps**:
1. Copy the URL from the console
2. Open it manually in your browser
3. Continue with authorization

### Issue: "Invalid callback URL"

**Check Schwab Developer Portal**:
1. Go to https://developer.schwab.com/
2. Click "My Apps"
3. Select your app
4. Verify callback URL matches: `https://127.0.0.1:8182/`

### Issue: "Still no refresh_token after auth"

**Possible causes**:
1. App not fully approved in Schwab portal
2. API scopes not properly configured
3. Using wrong app credentials

**Solution**:
- Create a new app in Schwab developer portal
- Ensure all scopes are selected
- Use the new App Key and Secret

---

## What We're Going to Do Together

1. **You run**: `python reauth_schwab_auto.py`
2. **Script shows**: Authorization URL
3. **You click**: The URL and authorize in browser
4. **You copy**: The callback URL from browser
5. **You paste**: Callback URL into terminal
6. **Script saves**: New token with refresh_token
7. **I'll help**: Upload to AWS and verify

**Ready? Run this command when you're ready:**

```bash
cd /Users/makaminski1337/Developer/alpha-kite-max/backend
python reauth_schwab_auto.py
```

Then paste the output here and I'll guide you through each step! 🚀

