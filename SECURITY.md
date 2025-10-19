# Security Policy

## Table of Contents

1. [Reporting Security Vulnerabilities](#reporting-security-vulnerabilities)
2. [Credential Management](#credential-management)
3. [API Keys &amp; Secrets](#api-keys--secrets)
4. [Token Security](#token-security)
5. [Environment Variables](#environment-variables)
6. [AWS Security](#aws-security)
7. [Supabase Security](#supabase-security)
8. [Development Security](#development-security)
9. [Production Security](#production-security)
10. [Security Checklist](#security-checklist)

---

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please **DO NOT** open a public issue.

**Instead:**

- Email: MKaminski1337@Gmail.com
- Include: Detailed description, steps to reproduce, potential impact
- Response time: We aim to respond within 48 hours

---

## Credential Management

### ⚠️ NEVER Commit Credentials

**Never commit the following to Git:**

- API keys (Schwab App Key, App Secret)
- OAuth tokens (access tokens, refresh tokens)
- Database credentials (Supabase Service Role Key)
- AWS credentials (Access Key, Secret Access Key)
- Environment files (`.env`, `.env.local`, `.env.production`)
- Token files (`.schwab_tokens.json`, `schwab_token.json`)
- Private keys or certificates

### Git Protection

The `.gitignore` is configured to exclude:

```gitignore
# Environment variables
.env
.env.*
!.env.example

# Schwab tokens
.schwab_tokens.json
**/schwab_token.json
backend/config/schwab_token.json

# AWS credentials
.aws/

# IDE files with credentials
.vscode/settings.json (if contains secrets)
```

### Pre-commit Hooks

Consider using [ggshield](https://github.com/GitGuardian/ggshield) to detect secrets:

```bash
# Install
pip install ggshield

# Scan repository
ggshield secret scan repo .
```

**Note:** This project already has `.cache_ggshield` configured.

---

## API Keys & Secrets

### Schwab API Credentials

**Storage Locations:**

| Environment                 | Storage Method             | File/Service              |
| --------------------------- | -------------------------- | ------------------------- |
| **Local Development** | `.env` file (gitignored) | `backend/.env`          |
| **AWS Lambda**        | Environment variables      | Lambda configuration      |
| **Production Tokens** | AWS Secrets Manager        | `schwab-api-token-prod` |

**Required Credentials:**

- `SCHWAB_APP_KEY`: Application key from Schwab Developer Portal
- `SCHWAB_APP_SECRET`: Application secret (treat as password)
- OAuth tokens: Access token, refresh token (generated via OAuth flow)

**Security Best Practices:**

1. **Rotate regularly**: Change App Secret every 90 days
2. **Limit scope**: Only request necessary OAuth scopes
3. **Monitor usage**: Check Schwab Developer Portal for unusual activity
4. **Separate environments**: Use different App Keys for dev/prod

### Supabase Credentials

**Types of Keys:**

| Key Type                   | Use Case                | Security Level   | Where to Use     |
| -------------------------- | ----------------------- | ---------------- | ---------------- |
| **Anon Key**         | Frontend, public access | Public (safe)    | Client-side code |
| **Service Role Key** | Backend, admin access   | **SECRET** | Server-side only |

**Storage:**

- Frontend: `NEXT_PUBLIC_SUPABASE_ANON_KEY` (safe to expose)
- Backend: `SUPABASE_SERVICE_ROLE_KEY` (never expose)

**Row-Level Security (RLS):**

- All tables MUST have RLS enabled
- Anon key users can only read public data
- Service role bypasses RLS (use carefully)

**Service Role Key Security:**

```bash
# ❌ NEVER do this
console.log(process.env.SUPABASE_SERVICE_ROLE_KEY)

# ✅ Always use securely
const supabase = createClient(url, serviceRoleKey, { 
  auth: { persistSession: false } 
})
```

---

## Token Security

### OAuth Token Lifecycle

**Schwab OAuth Tokens:**

- **Access Token**: Valid for 7 days
- **Refresh Token**: Valid for 90 days
- **Auto-refresh**: Lambda function refreshes before expiration

### Token Storage

**Local Development:**

```bash
# Stored in backend/config/schwab_token.json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2t...",
  "expires_at": "2024-10-23T12:00:00Z",
  "token_type": "Bearer"
}

# File permissions (Unix/Mac)
chmod 600 backend/config/schwab_token.json
```

**AWS Production:**

- Stored in AWS Secrets Manager (`schwab-api-token-prod`)
- Encrypted at rest (AWS KMS)
- Access controlled via IAM policies
- Automatic rotation via Lambda

### Token Refresh Flow

```
1. Lambda checks token expiration
2. If < 24 hours remaining → refresh
3. Call Schwab API with refresh_token
4. Get new access_token + refresh_token
5. Update AWS Secrets Manager
6. Continue execution
```

### Manual Token Refresh

```bash
cd backend

# Option 1: Automated
python sys_testing/auto_reauth.py

# Option 2: Manual
python sys_testing/get_auth_url.py
# Click URL, authorize, copy callback URL
python sys_testing/process_callback.py <callback_url>

# Upload to AWS
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1
```

---

## Environment Variables

### Frontend (Next.js)

**File:** `frontend/.env.local`

```bash
# Public variables (prefixed with NEXT_PUBLIC_)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# These are SAFE to expose in client-side code
```

**Vercel Deployment:**

1. Add variables in Vercel dashboard
2. Never commit `.env.local` to Git
3. Use Vercel environment variables for production

### Backend (Python)

**File:** `backend/.env`

```bash
# Schwab API (SECRET)
SCHWAB_APP_KEY=your-app-key
SCHWAB_APP_SECRET=your-app-secret

# Supabase (SECRET - Service Role)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Application
LOG_LEVEL=INFO
DEFAULT_TICKER=QQQ
```

**Lambda Environment Variables:**

- Configured via Terraform (`infrastructure/lambda.tf`)
- Encrypted in transit and at rest
- Never logged to CloudWatch

### Environment Variable Validation

Use Pydantic for validation:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    schwab_app_key: str
    schwab_app_secret: str
    supabase_url: str
    supabase_service_role_key: str
  
    class Config:
        env_file = ".env"
        case_sensitive = False

# Raises validation error if missing
settings = Settings()
```

---

## AWS Security

### IAM Best Practices

**Lambda Execution Role:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:schwab-api-token-*"
    }
  ]
}
```

**Principle of Least Privilege:**

- Only grant permissions required for operation
- Use resource-level restrictions (e.g., specific secret ARN)
- Avoid wildcard permissions (`*`) when possible

### AWS Secrets Manager

**Features:**

- Encryption at rest (AWS KMS)
- Automatic rotation support
- Audit logging via CloudTrail
- Fine-grained access control

**Cost:** $0.40/month per secret + $0.05 per 10,000 API calls

**Access Pattern:**

```python
import boto3
import json

def get_schwab_token():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='schwab-api-token-prod')
    return json.loads(response['SecretString'])
```

### CloudWatch Logs

**Log Filtering:**

- Never log credentials in plain text
- Redact sensitive fields (tokens, keys)
- Use structured logging with `structlog`

```python
import structlog

logger = structlog.get_logger()

# ✅ Safe logging
logger.info("token_refreshed", expires_at="2024-10-23T12:00:00Z")

# ❌ NEVER do this
logger.info(f"New token: {access_token}")
```

**Log Retention:**

- Default: 14 days (configurable)
- Reduce retention to minimize exposure
- Delete logs after debugging

---

## Supabase Security

### Row-Level Security (RLS)

**All tables MUST have RLS enabled:**

```sql
-- Enable RLS
ALTER TABLE equity_data ENABLE ROW LEVEL SECURITY;

-- Public read access (safe with Anon Key)
CREATE POLICY "Public read access" ON equity_data
  FOR SELECT USING (true);

-- Insert only with Service Role (enforced by RLS bypass)
-- No policy needed - Service Role bypasses RLS
```

### Database Credentials

**PostgreSQL Connection String:**

- Never expose in client-side code
- Use Supabase client libraries (handle auth automatically)
- Connection string includes password (treat as secret)

**Supabase API Keys:**

| Key              | Security         | Client-Side? | Purpose                        |
| ---------------- | ---------------- | ------------ | ------------------------------ |
| Anon Key         | Public           | ✅ Yes       | Read-only access, RLS enforced |
| Service Role Key | **SECRET** | ❌ No        | Full access, bypasses RLS      |

### API Rate Limiting

**Supabase Free Tier Limits:**

- 500 MB database storage
- 5 GB egress bandwidth/month
- Unlimited API requests (soft limit ~1,000/min)

**Protection Against Abuse:**

- RLS limits data access
- API Gateway rate limiting (Supabase managed)
- Monitor usage in Supabase dashboard

---

## Development Security

### Local Development

**Setup Checklist:**

- [ ] Copy `env.example` to `.env` (never commit `.env`)
- [ ] Set file permissions: `chmod 600 .env`
- [ ] Use `.gitignore` to exclude secrets
- [ ] Run `ggshield` to scan for leaked secrets
- [ ] Use virtual environments (Python `venv`, Node `node_modules`)

### Code Review

**Security Review:**

- [ ] No hardcoded credentials
- [ ] No `console.log()` of sensitive data
- [ ] Environment variables properly loaded
- [ ] Secrets not in error messages
- [ ] RLS policies tested
- [ ] Input validation implemented

### Testing

**Never use production credentials in tests:**

```python
# ✅ Good - use test fixtures
@pytest.fixture
def mock_schwab_token():
    return {"access_token": "test_token_12345"}

# ❌ Bad - uses real credentials
def test_api():
    token = os.getenv("SCHWAB_TOKEN")  # Real token!
```

---

## Production Security

### Deployment Checklist

**Before deploying:**

- [ ] All secrets in environment variables (not code)
- [ ] Terraform variables in `terraform.tfvars` (gitignored)
- [ ] AWS credentials configured via `aws configure` (not in code)
- [ ] Vercel environment variables set
- [ ] Supabase RLS policies enabled and tested
- [ ] CloudWatch log retention set to minimum required
- [ ] Lambda execution role follows least privilege
- [ ] Secrets Manager configured for token rotation

### Monitoring & Alerts

**Security Monitoring:**

1. **AWS CloudTrail**: Log all API calls
2. **CloudWatch Alarms**: Alert on unusual activity
3. **Supabase Logs**: Monitor database access
4. **Schwab Developer Portal**: Check API usage

**Alert Triggers:**

- Repeated authentication failures
- Unusual API call volume
- Token refresh failures
- Database access outside normal hours

### Incident Response

**If credentials are compromised:**

1. **Immediate Actions:**

   - Rotate compromised credentials immediately
   - Revoke Schwab App Key/Secret
   - Reset Supabase Service Role Key
   - Rotate AWS IAM keys
   - Check CloudWatch logs for unauthorized access
2. **Investigation:**

   - Review Git history for exposed secrets
   - Check Supabase logs for data access
   - Review AWS CloudTrail for API calls
   - Identify scope of exposure
3. **Remediation:**

   - Remove secrets from Git history (`git filter-branch` or BFG Repo-Cleaner)
   - Force push cleaned history
   - Notify affected parties (if data breach)
   - Document incident and prevention steps

---

## Security Checklist

### Initial Setup

- [ ] Copy `env.example` to `.env` and fill in credentials
- [ ] Verify `.env` is in `.gitignore`
- [ ] Set file permissions: `chmod 600 .env backend/config/schwab_token.json`
- [ ] Install `ggshield` for secret scanning
- [ ] Configure AWS credentials via `aws configure` (not in code)
- [ ] Enable RLS on all Supabase tables

### Development Workflow

- [ ] Never commit `.env`, `.env.local`, or token files
- [ ] Use `git status` before committing to check for secrets
- [ ] Run `ggshield secret scan repo .` before pushing
- [ ] Review diffs carefully before pushing to remote
- [ ] Use environment variables for all credentials
- [ ] Redact secrets in logs and error messages

### Deployment

- [ ] Terraform variables in `terraform.tfvars` (gitignored)
- [ ] AWS Secrets Manager configured for OAuth tokens
- [ ] Lambda environment variables encrypted
- [ ] Vercel environment variables set via dashboard
- [ ] CloudWatch log retention set appropriately
- [ ] RLS policies tested and enabled

### Ongoing Maintenance

- [ ] Rotate Schwab App Secret every 90 days
- [ ] Monitor token expiration (auto-refresh via Lambda)
- [ ] Review IAM policies quarterly
- [ ] Check Supabase audit logs monthly
- [ ] Update dependencies for security patches
- [ ] Review CloudWatch logs for anomalies

### Code Review

- [ ] No hardcoded credentials
- [ ] Environment variables properly validated
- [ ] Secrets not logged or exposed in errors
- [ ] RLS policies enforce access control
- [ ] Input validation prevents injection attacks
- [ ] Error messages don't leak sensitive info

---

## Additional Resources

### Tools

- **ggshield**: Secret detection in Git - https://github.com/GitGuardian/ggshield
- **git-secrets**: Prevent committing secrets - https://github.com/awslabs/git-secrets
- **truffleHog**: Find secrets in Git history - https://github.com/trufflesecurity/truffleHog

### Documentation

- **AWS Security Best Practices**: https://aws.amazon.com/security/best-practices/
- **Supabase Security**: https://supabase.com/docs/guides/platform/security
- **OAuth 2.0 Security**: https://tools.ietf.org/html/rfc6749#section-10

### Contact

For security concerns, contact the maintainers privately.

---

**Last Updated:** October 18, 2024
**Review Cycle:** Quarterly

