# Lambda Token Issue Resolution

## Problem Identified

From Lambda CloudWatch logs (2025-10-16 14:00-14:16):

### Key Observations

1. **✅ Lambda is running** - EventBridge triggering every minute
2. **✅ Token refresh succeeding** - Updates to Secrets Manager working
3. **❌ API calls failing** - `InvalidTokenError` after token refresh
4. **⚠️ Token missing expiration** - Warning on every invocation

### Root Cause

**The OAuth token in Secrets Manager lacks proper API permissions.**

Even though Lambda successfully:
- Retrieves token from `schwab-api-token-prod`
- Attempts token refresh
- Updates Secrets Manager with "refreshed" token
- Authenticates successfully

The refreshed token **still fails** when making actual API calls to `get_price_history()`.

This indicates the original OAuth consent/authorization is incomplete or revoked.

## Log Analysis

```
✅ token_retrieved_successfully
⚠️  token_missing_expiration  <-- Missing expiration timestamp
✅ refreshing_expired_token
✅ token_refresh_successful
✅ schwab_authentication_successful
❌ token_invalid: InvalidTokenError  <-- Fails on actual API call
```

**Pattern**: Token operations succeed, but actual Schwab API data fetch fails.

## Solution: Re-authorize OAuth Token

The token in AWS Secrets Manager needs to be replaced with a freshly authorized token.

### Step 1: Generate New Token Locally

```bash
cd /Users/makaminski1337/Developer/alpha-kite-max/backend

# Remove old token
rm -f config/schwab_token.json

# Run any script that authenticates (will trigger OAuth flow)
python test_paper_trading.py
```

**This will**:
1. Detect no token exists
2. Print OAuth authorization URL
3. Open browser for you to authorize
4. Save new token to `config/schwab_token.json`

### Step 2: Upload Token to AWS Secrets Manager

```bash
# Read the token file
cat config/schwab_token.json

# Update AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1
```

**Verify**:
```bash
aws secretsmanager get-secret-value \
  --secret-id schwab-api-token-prod \
  --query SecretString \
  --output text | jq .
```

### Step 3: Test Lambda Function

```bash
# Manually invoke Lambda to test
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --region us-east-1 \
  --payload '{"source":"manual-test"}' \
  response.json

# Check response
cat response.json

# Check if data appeared in Supabase
cd backend
python check_data_status.py
```

## Why This Happens

### OAuth Token Lifecycle

1. **Initial Authorization**: User grants app access to Schwab account
2. **Access Token**: Short-lived (30 min - 1 hour)
3. **Refresh Token**: Long-lived (7-90 days)
4. **Token Refresh**: Uses refresh token to get new access token

### The Problem

**Schwab requires periodic re-authorization** when:
- Refresh token expires (typically 7 days for Schwab)
- API scopes change
- Account permissions modified
- Security policy updates

The Lambda token manager can refresh the *access token* but cannot re-authorize the *refresh token* without user interaction.

## Automated Fix (Future Enhancement)

### Option 1: Increase Token Lifetime

- Configure Schwab app for maximum refresh token lifetime
- Typically 90 days max
- Still requires periodic re-auth

### Option 2: Add Manual Re-Auth Endpoint

Create a Lambda endpoint that triggers OAuth flow:

```python
# lambda/reauth_endpoint.py
def lambda_handler(event, context):
    """
    Generates OAuth URL for manual re-authorization.
    User clicks URL, authorizes, token auto-updates.
    """
    auth_url = generate_oauth_url()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Click URL to re-authorize',
            'auth_url': auth_url
        })
    }
```

### Option 3: CloudWatch Alarm + SNS

Set up alert when Lambda fails:

```hcl
# infrastructure/cloudwatch_alarms.tf
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "alpha-kite-lambda-token-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Lambda has token errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    FunctionName = "alpha-kite-real-time-streamer"
  }
}
```

## Verification Checklist

After updating the token:

- [ ] Lambda logs show `price_history_fetched` (not `token_invalid`)
- [ ] Supabase `equity_data` table has new rows for today
- [ ] Frontend displays current day data
- [ ] No `InvalidTokenError` in CloudWatch
- [ ] Token has proper expiration timestamp
- [ ] Data updates every minute during market hours

## Expected Lambda Success Log

```json
{"event": "lambda_invoked"}
{"event": "market_hours_check", "is_open": true}
{"event": "token_retrieved_successfully"}
{"event": "schwab_authentication_successful"}
{"event": "downloading_minute_data", "ticker": "QQQ"}
{"event": "price_history_fetched", "candles_count": 390}  <-- THIS
{"event": "calculating_indicators"}
{"event": "equity_data_inserted", "count": 1}
{"event": "indicators_inserted", "count": 1}
{"event": "lambda_completed_successfully"}
```

## Quick Fix Commands

```bash
# 1. Generate new token locally
cd backend
rm config/schwab_token.json
python test_paper_trading.py  # Follow OAuth flow

# 2. Upload to AWS
aws secretsmanager update-secret \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1

# 3. Test Lambda
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --payload '{}' \
  response.json

# 4. Check data
python check_data_status.py
```

## Success Criteria

✅ **Lambda executes without errors**
✅ **Data appears in Supabase for current day**
✅ **Frontend displays real-time data**
✅ **No InvalidTokenError in logs**
✅ **Continuous data flow every minute**

---

**Estimated Time to Fix**: 10-15 minutes
**Priority**: 🔴 CRITICAL (no data for 7 days)
**Owner**: DevOps/Backend

