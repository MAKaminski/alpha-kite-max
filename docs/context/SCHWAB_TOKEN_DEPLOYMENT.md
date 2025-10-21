# Schwab Token Deployment Workflow

Complete guide for deploying Schwab API tokens to AWS Secrets Manager.

---

## 🎯 Overview

This workflow ensures that Schwab OAuth tokens are properly:
1. Generated via OAuth flow
2. Saved locally for backup
3. Uploaded to AWS Secrets Manager
4. Available to Lambda function
5. Monitored in admin panel

---

## 🚀 Quick Start

### Option 1: Automatic Deployment (Recommended)

```bash
# 1. Get OAuth authorization
cd backend/sys_testing
python3 simple_callback_processor.py "<CALLBACK_URL>"

# Tokens are automatically:
# ✅ Saved to backend/config/schwab_token.json
# ✅ Uploaded to AWS Secrets Manager
# ✅ Ready for Lambda use
```

### Option 2: Manual Deployment

```bash
# 1. Generate tokens via OAuth
cd backend/sys_testing
python3 simple_callback_processor.py "<CALLBACK_URL>"

# 2. Deploy to AWS
cd ../..
./scripts/deploy-schwab-tokens.sh
```

---

## 📋 Complete OAuth Flow

### Step 1: Get Authorization URL

```bash
cd backend/sys_testing

# Generate OAuth URL
python3 -c "
import secrets
state = secrets.token_urlsafe(32)
client_id = 'Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU'
redirect_uri = 'https://127.0.0.1:8182'
print(f'https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&state={state}')
"
```

### Step 2: Authorize

1. **Open the URL** in your browser
2. **Login to Schwab** (if not already logged in)
3. **Click "Allow"** to authorize the app
4. **Copy the callback URL** from your browser address bar
   - Example: `https://127.0.0.1:8182/?code=ABC123...&state=XYZ789`

### Step 3: Exchange Code for Tokens

⚠️ **Important**: You have only 30-60 seconds to complete this step!

```bash
# Run immediately after authorization
python3 simple_callback_processor.py "PASTE_CALLBACK_URL_HERE"
```

**This script automatically:**
- ✅ Exchanges authorization code for tokens
- ✅ Saves tokens to `backend/config/schwab_token.json`
- ✅ Tests API access
- ✅ Uploads tokens to AWS Secrets Manager

---

## 🔧 Manual Deployment Script

If automatic upload fails, use the deployment script:

```bash
./scripts/deploy-schwab-tokens.sh
```

### What It Does:

1. **Validates** token file exists
2. **Checks** AWS credentials
3. **Uploads** tokens to Secrets Manager
4. **Updates** Lambda function
5. **Tests** Lambda invocation
6. **Provides** next steps

---

## 📁 Token File Structure

`backend/config/schwab_token.json`:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2t...",
  "token_type": "Bearer",
  "expires_in": 604800,
  "scope": "api",
  "id_token": "eyJraWQiOiI1N2VkODg4Yi...",
  "expires_at": "2025-10-25T12:00:00Z",
  "last_refresh": "2025-10-18T12:00:00Z",
  "refresh_count": 0,
  "created_at": "2025-10-18T12:00:00Z"
}
```

### Token Metadata:

- `access_token`: Used for API calls (valid 7 days)
- `refresh_token`: Used to get new access tokens (valid 90 days)
- `expires_at`: When access token expires
- `last_refresh`: Last time token was refreshed
- `refresh_count`: Number of times token has been refreshed
- `created_at`: When token was first created

---

## ☁️ AWS Secrets Manager

### Secret Configuration:

| Property | Value |
|----------|-------|
| **Name** | `schwab-api-token-prod` |
| **Region** | `us-east-1` |
| **Description** | Schwab API OAuth tokens for production |
| **Rotation** | Manual (triggered by OAuth flow) |

### Access Permissions:

Lambda execution role has:
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:PutSecretValue"
  ],
  "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:schwab-api-token-*"
}
```

---

## 🔄 Token Refresh Workflow

### Automatic Refresh (Lambda)

Lambda automatically refreshes tokens when:
- Access token expires in < 24 hours
- During normal market hours operation

```python
# Lambda checks token expiration
if token_expires_soon():
    new_tokens = refresh_access_token(refresh_token)
    save_to_secrets_manager(new_tokens)
```

### Manual Refresh

If automatic refresh fails:

1. **Re-run OAuth flow** (gets new tokens)
2. **Deploy to AWS** (upload new tokens)
3. **Verify in admin panel** (check status)

---

## 🧪 Testing Deployment

### 1. Verify Local Token

```bash
cat backend/config/schwab_token.json | jq '.'
```

### 2. Verify AWS Secret

```bash
aws secretsmanager get-secret-value \
  --secret-id schwab-api-token-prod \
  --region us-east-1 \
  --query SecretString \
  --output text | jq '.'
```

### 3. Test Lambda Access

```bash
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --payload '{"test": true}' \
  --region us-east-1 \
  response.json

cat response.json | jq '.'
```

### 4. Check Admin Panel

1. Visit your app: `https://your-app.vercel.app`
2. Open Admin Panel
3. Check token status:
   - Should show ✅ VALID
   - Expiration time displayed
   - Refresh token status

---

## 🚨 Troubleshooting

### Token File Not Found

```bash
# Check if file exists
ls -la backend/config/schwab_token.json

# If missing, re-run OAuth flow
cd backend/sys_testing
python3 simple_callback_processor.py "<CALLBACK_URL>"
```

### AWS Upload Failed

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check AWS region
aws configure get region

# Manually upload
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://backend/config/schwab_token.json \
  --region us-east-1
```

### Lambda Not Updating

```bash
# Check Lambda function exists
aws lambda get-function \
  --function-name alpha-kite-real-time-streamer \
  --region us-east-1

# View Lambda logs
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow
```

### Authorization Code Expired

⚠️ **Error**: "Authorization code has expired"

**Solution**: Authorization codes expire in 30-60 seconds. Be faster!

1. Have terminal ready with command typed
2. Complete OAuth flow
3. Immediately paste URL and run command

```bash
# Pre-type this command:
python3 simple_callback_processor.py "

# Then:
# 1. Complete OAuth
# 2. Paste URL
# 3. Add closing quote
# 4. Press Enter IMMEDIATELY
```

---

## 📊 Deployment Checklist

### Pre-Deployment:
- [ ] Callback server running (`standalone_callback_server.py`)
- [ ] AWS credentials configured (`aws configure`)
- [ ] Terminal ready with processor command
- [ ] Browser ready for OAuth

### During OAuth:
- [ ] OAuth URL opened in browser
- [ ] Schwab login completed
- [ ] Authorization approved
- [ ] Callback URL copied within 30 seconds
- [ ] Processor command executed immediately

### Post-Deployment:
- [ ] Token file created (`backend/config/schwab_token.json`)
- [ ] AWS Secret updated
- [ ] Lambda function tested
- [ ] Admin panel shows valid token
- [ ] Data streaming verified

---

## 🔗 Related Documentation

- [Schwab Authentication](./SCHWAB_AUTH_DOCUMENTATION.md)
- [Token Management UI](./TOKEN_MANAGEMENT_DEPLOYMENT.md)
- [Lambda Deployment](../backend/lambda/README.md)
- [Security Policy](../../SECURITY.md)

---

## 📞 Support

### Common Issues:

1. **403 Forbidden**: App not approved → Contact Schwab Support
2. **Code Expired**: Too slow → Be faster next time
3. **AWS Error**: Credentials → Run `aws configure`
4. **Token Invalid**: Expired → Re-run OAuth flow

### Contact:

- **Schwab Developer Support**: developer@schwab.com
- **AWS Support**: https://console.aws.amazon.com/support

---

**Last Updated**: October 18, 2025  
**Version**: 1.0

