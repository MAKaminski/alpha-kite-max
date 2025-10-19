# Schwab OAuth Quick Start

**FULLY AUTOMATED** - No manual copying, pasting, or terminal commands!

---

## ⚡ One-Command OAuth

### Option 1: Super Simple (Recommended)

```bash
./reauth_schwab.sh
```

**That's it!** The script will:
1. ✅ Open browser to Schwab OAuth
2. ✅ Wait for you to click "Allow"
3. ✅ Automatically capture callback
4. ✅ Exchange code for tokens
5. ✅ Upload to AWS Secrets Manager
6. ✅ Test API access

**No manual copying or pasting required!**

---

### Option 2: Direct Python

```bash
cd backend/sys_testing
python3 auto_reauth.py
```

---

### Option 3: Manual (Legacy)

```bash
cd backend/sys_testing

# Step 1: Open this URL in browser
open "https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id=Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU&redirect_uri=https%3A//127.0.0.1%3A8182&state=reauth_$(date +%s)000"

# Step 2: After clicking "Allow", IMMEDIATELY run:
python3 simple_callback_processor.py "PASTE_CALLBACK_URL_HERE"
```

⚠️ **Manual method requires 30-second timing!**

---

## 🎯 What Happens Automatically

1. ✅ Authorization code exchanged for tokens
2. ✅ Tokens saved to `backend/config/schwab_token.json`
3. ✅ API access tested
4. ✅ Tokens uploaded to AWS Secrets Manager
5. ✅ Lambda function ready to use tokens

---

## 🔍 Verify Deployment

### Check Local Token

```bash
cat backend/config/schwab_token.json | jq '.'
```

### Check AWS Secret

```bash
aws secretsmanager get-secret-value \
  --secret-id schwab-api-token-prod \
  --region us-east-1 \
  --query SecretString --output text | jq '.'
```

### Check Admin Panel

Visit: https://your-app.vercel.app
- Open Admin Panel
- Check token status (should be green ✅)

---

## 🚨 Common Issues

### "Authorization code expired"
- **Problem**: Took too long to paste URL
- **Solution**: Be faster! Have terminal ready

### "AWS upload failed"
- **Problem**: AWS credentials not configured
- **Solution**: Run `aws configure`

### "403 Forbidden"
- **Problem**: App not approved for OAuth
- **Solution**: Contact developer@schwab.com

---

## 📖 Full Documentation

- **Deployment Guide**: `context/docs/SCHWAB_TOKEN_DEPLOYMENT.md`
- **Authentication**: `context/docs/SCHWAB_AUTH_DOCUMENTATION.md`
- **Token Management**: `context/docs/TOKEN_MANAGEMENT_DEPLOYMENT.md`

---

**Need help?** See full documentation or contact support.

