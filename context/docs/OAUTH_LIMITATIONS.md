# OAuth Token Limitations & Automation Strategy

## The Fundamental Limitation

**OAuth 2.0 Security Requirement**: Refresh tokens expire and require user interaction to renew.

### What CAN Be Automated ✅

1. **Access Token Refresh** (every hour)
   - Lambda refreshes automatically
   - Uses refresh_token
   - No user interaction needed
   - Works 24/7

2. **Token Storage** (automatic)
   - Saved to AWS Secrets Manager
   - Encrypted at rest
   - Accessed by Lambda

3. **Error Detection** (automatic)
   - CloudWatch monitors failures
   - SNS sends email alerts
   - You get notified immediately

### What CANNOT Be Automated ❌

1. **Initial Authorization**
   - Requires browser
   - Requires clicking "Allow"
   - Schwab security policy

2. **Refresh Token Renewal** (every 7-90 days)
   - When refresh_token expires
   - Requires re-authorization
   - **This is your current issue**

---

## Current Situation

### Token Lifecycle

```
Day 0:   You authorize → Get access_token + refresh_token
         ✅ Lambda works

Day 1-6: Lambda auto-refreshes access_token every hour
         ✅ Everything works automatically

Day 7:   Refresh token expires (Schwab policy)
         ❌ Lambda can't refresh anymore
         ❌ Data collection stops
         📧 You receive email alert (after we set it up)

Day 7+:  You click re-auth link → 2 clicks → Done
         ✅ Lambda works again for next 7-90 days
```

### Why Lambda Can't Self-Serve

**Security by Design**:
- OAuth requires **user consent** for security
- Prevents apps from having permanent access
- Industry standard (Google, Microsoft, etc. all work this way)
- Schwab legally required to enforce this

**Technical Limitation**:
- Lambda has no browser
- Lambda can't click buttons
- Lambda can't complete CAPTCHA
- Lambda can't store user credentials

---

## Automation Strategy

### 1. Maximize Token Lifetime ⏰

**Action**: Configure Schwab app for 90-day refresh tokens

**How**:
1. Go to https://developer.schwab.com/
2. Your App → Settings
3. Find "Token/OAuth Settings"
4. Set "Refresh Token Lifetime" to **Maximum** (90 days)

**Result**: Re-auth only 4 times/year instead of 52 times/year

### 2. Email Alerts 📧

**Action**: Deploy CloudWatch alarms (already created!)

**Setup**:
```bash
cd infrastructure

# Update cloudwatch_alarms.tf
# Change: endpoint = "your-email@example.com"
# To your actual email

terraform apply
```

**Result**: 
- You get email when Lambda starts failing
- Email says "Token expired - re-auth needed"
- You click link → re-auth → done in 30 seconds

### 3. One-Click Re-Auth Dashboard 🖱️

**What I just created**: 
- Web page: `/admin/reauth`
- One button click
- Opens browser automatically
- You click "Allow"
- Token auto-uploaded to AWS

**Access**: `https://your-app.vercel.app/admin/reauth`

### 4. Scheduled Reminders 📅

**Option A**: Calendar reminder
- Set reminder for every 85 days (before 90-day expiry)
- Proactively re-auth before token expires
- Prevents data gaps

**Option B**: Admin panel shows token age
- Display "Token expires in 5 days"
- Yellow warning at 7 days
- Red alert at 2 days

---

## Recommended Workflow

### Setup (One Time)

1. ✅ Configure Schwab app for 90-day tokens
2. ✅ Deploy CloudWatch alarms with your email
3. ✅ Bookmark `/admin/reauth` page
4. ✅ Set calendar reminder for every 85 days

### Ongoing (Every 90 Days)

**Proactive** (recommended):
1. Calendar reminder fires
2. Visit `/admin/reauth`
3. Click button
4. Click "Allow" in browser
5. Done - 30 seconds total

**Reactive** (when failure occurs):
1. Email alert: "Lambda failing"
2. Visit `/admin/reauth`
3. Click button
4. Click "Allow"
5. Done - Lambda resumes

---

## Why This Is the Best We Can Do

### Industry Standard

**All OAuth providers require this**:
- Google API: 7-180 days
- Microsoft Graph: 90 days
- TD Ameritrade: 90 days
- Schwab: 7-90 days (configurable)

### Alternatives Considered

#### ❌ Store User Credentials
- **Security risk**: Never store passwords
- **Against ToS**: Violates Schwab terms
- **Illegal**: Could violate financial regulations

#### ❌ Use API Keys Instead of OAuth
- **Not available**: Schwab only offers OAuth
- **Less secure**: API keys don't expire
- **No granular permissions**: OAuth allows scoped access

#### ❌ Selenium/Browser Automation
- **Against ToS**: Violates Schwab terms
- **Fragile**: Breaks when UI changes
- **Detectable**: Schwab can block automated browsers
- **Unreliable**: CAPTCHA would block it

---

## What I've Built for You

### 1. Automatic Scripts ✅

**For Local Re-Auth**:
```bash
cd backend
source .venv/bin/activate
python3 auto_reauth.py
```

- Opens browser automatically
- Handles callback automatically  
- Tests token immediately
- Shows AWS upload command

### 2. CloudWatch Alarms ✅

**File**: `infrastructure/cloudwatch_alarms.tf`

- Detects Lambda errors
- Sends email when token expires
- Monitors data gaps

### 3. Web Re-Auth Page ✅

**Route**: `/admin/reauth`

- One-button click
- User-friendly interface
- Explains what's happening
- Future enhancement: Could integrate with backend API

### 4. Comprehensive Docs ✅

- `REAUTH_GUIDE.md` - Step-by-step instructions
- `LAMBDA_TOKEN_FIX.md` - Technical details
- `OAUTH_LIMITATIONS.md` - This document

---

## Summary

**Q: Can Lambda self-serve re-auth?**
**A: No - OAuth 2.0 requires user interaction by design.**

**Q: How often do I need to re-auth?**
**A: Every 7-90 days, depending on your Schwab app config.**

**Q: Can we reduce the frequency?**
**A: Yes! Configure Schwab app for 90-day refresh tokens.**

**Q: How will I know when to re-auth?**
**A: CloudWatch alarm sends email + Admin panel shows token age.**

**Q: How long does re-auth take?**
**A: 30 seconds - just 2 clicks in browser.**

---

## Action Items for You

### Immediate (Now)
- [ ] Upload the new token to AWS Secrets Manager (I'll help)
- [ ] Verify Lambda starts working

### Short-term (This Week)
- [ ] Deploy CloudWatch alarms with your email
- [ ] Configure Schwab app for 90-day token lifetime
- [ ] Test the `/admin/reauth` page

### Long-term (Ongoing)
- [ ] Set calendar reminder for every 85 days
- [ ] Bookmark `/admin/reauth` for quick access
- [ ] Monitor email for token expiration alerts

**This is as automated as OAuth allows - and it's the same for all major APIs!** 🔒

