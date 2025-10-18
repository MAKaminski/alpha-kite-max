---
name: Automated OAuth Re-Authorization
about: Implement fully automated OAuth token refresh without manual intervention
title: '[FEATURE] Automated OAuth Re-Authorization Flow'
labels: enhancement, authentication, automation
assignees: ''
---

## Feature Description

Implement a fully automated OAuth re-authorization flow that can refresh tokens without manual browser interaction.

## Current Behavior

**Manual Process Required:**
1. User must manually open OAuth URL in browser
2. User must log in to Schwab.com
3. User must click "Allow" button
4. User must copy callback URL within 30 seconds
5. User must paste URL into terminal command

**Pain Points:**
- Requires manual intervention during business hours
- 30-second authorization code expiration window
- Can't automate for unattended operation
- Tokens expire every 7 days (access) / 90 days (refresh)

## Desired Behavior

**Automated Re-Authorization:**
- System detects token expiration approaching
- Automatically initiates OAuth flow
- Handles authorization without manual intervention
- Updates tokens in AWS Secrets Manager
- Notifies user of completion

## Technical Approach

### Option 1: Browser Automation (Selenium/Playwright)

```python
from playwright.sync_api import sync_playwright

def automated_oauth_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to OAuth URL
        page.goto(oauth_url)
        
        # Fill login form (if not already logged in)
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        
        # Click "Allow" button
        page.click('button[name="allow"]')
        
        # Capture callback URL
        page.wait_for_url('**/127.0.0.1:8182/**')
        callback_url = page.url
        
        # Process callback
        exchange_code_for_tokens(callback_url)
        upload_to_aws()
        
        browser.close()
```

**Pros:**
- Fully automated
- Works with existing OAuth flow
- No Schwab API changes needed

**Cons:**
- Requires storing credentials (security risk)
- Browser automation can be fragile
- Headless browsers may be detected

### Option 2: Refresh Token Rotation

```python
def automatic_token_refresh():
    # Use existing refresh token
    new_tokens = refresh_access_token(current_refresh_token)
    
    # Update AWS Secrets Manager
    update_secrets_manager(new_tokens)
    
    # Lambda continues using new tokens
```

**Pros:**
- No credentials storage needed
- Uses standard OAuth refresh flow
- Secure and recommended approach

**Cons:**
- Only works if refresh token is valid (<90 days)
- Requires manual re-auth if refresh token expires

### Option 3: Hybrid Approach (Recommended)

```python
def smart_token_management():
    if refresh_token_valid():
        # Use refresh token (automated)
        refresh_access_token()
    elif refresh_token_expires_soon():
        # Send email/SMS notification
        notify_user("Re-authorization needed in 7 days")
    else:
        # Fallback to manual re-auth
        initiate_manual_oauth_flow()
```

**Pros:**
- Best of both worlds
- Proactive notifications
- Graceful fallback

**Cons:**
- More complex implementation

## Implementation Plan

### Phase 1: Enhanced Refresh Token Management
- [ ] Implement automatic refresh when access token expires
- [ ] Add CloudWatch alarm for refresh token expiration
- [ ] Send SNS notification when refresh token < 7 days
- [ ] Update Lambda to auto-refresh access tokens

### Phase 2: Proactive Notifications
- [ ] Email notification at 7 days before refresh token expires
- [ ] SMS notification (optional) at 3 days
- [ ] Admin panel warning banner
- [ ] Slack/Discord webhook integration (optional)

### Phase 3: Automated Browser Flow (Optional)
- [ ] Implement Playwright-based automation
- [ ] Secure credential storage (AWS Secrets Manager)
- [ ] Scheduled re-authorization (before expiration)
- [ ] Logging and monitoring

### Phase 4: Self-Service Re-Auth (Alternative)
- [ ] Admin panel "Re-Authorize" button triggers email
- [ ] Email contains time-limited OAuth URL
- [ ] Click URL → Auto-login → Auto-approve → Done
- [ ] Tokens automatically uploaded to AWS

## Security Considerations

### If Using Browser Automation:
1. **Credential Storage**: 
   - Store in AWS Secrets Manager (encrypted)
   - Never commit to Git
   - Rotate regularly

2. **Execution Environment**:
   - Run in isolated Lambda/EC2
   - Use VPC with private subnets
   - Enable CloudTrail logging

3. **Access Control**:
   - Restrict IAM permissions
   - Enable MFA for Schwab account
   - Monitor for unusual activity

### Recommended Approach:
- **Primary**: Use refresh token rotation (no credentials needed)
- **Fallback**: Manual re-auth with proactive notifications
- **Avoid**: Storing account passwords

## Acceptance Criteria

- [ ] Tokens automatically refresh when access token expires
- [ ] User receives notification when refresh token < 7 days
- [ ] Admin panel shows token expiration countdown
- [ ] Failed refresh triggers alert
- [ ] Successful refresh logged in CloudWatch
- [ ] Documentation updated with automation details
- [ ] No credentials stored in code or .env files

## Alternative Solutions

1. **Schwab API Service Account**: Request dedicated service account from Schwab (no user login required)
2. **Long-Lived Tokens**: Request extended token lifetime from Schwab
3. **API Key Authentication**: Request alternative auth method

## Dependencies

- AWS Lambda (token refresh logic)
- AWS Secrets Manager (token storage)
- AWS SNS (notifications)
- AWS EventBridge (scheduling)
- Playwright (if using browser automation)

## Priority

**Medium** - Tokens expire every 90 days, so manual re-auth is manageable but annoying.

## Related Issues

- #XXX - Token expiration monitoring
- #XXX - Admin panel token status
- #XXX - CloudWatch alarms for token issues

## Notes

**Current Workaround:**
- Set calendar reminder for 80 days after token creation
- Run manual OAuth flow before expiration
- Takes 5 minutes with current automated deployment

**Security Best Practice:**
OAuth is designed to NOT require password storage. The current manual flow is the secure approach. Only implement automation if absolutely necessary for business reasons.

---

**Created**: 2025-10-18  
**Status**: Proposed  
**Type**: Enhancement

