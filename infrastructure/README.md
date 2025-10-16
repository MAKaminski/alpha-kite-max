# AWS Lambda Real-Time Streaming Infrastructure

This directory contains Terraform configuration for deploying real-time equity data streaming using AWS Lambda + EventBridge.

## Architecture

```
┌─────────────────────┐
│  EventBridge Rules  │ ──► Trigger every minute during market hours
└─────────────────────┘     (9:30 AM - 4:00 PM ET, weekdays)
           │
           ▼
┌─────────────────────┐
│  Lambda Function    │ ──► Fetch latest minute of data
│  (Python 3.10)      │     Calculate SMA9 & VWAP
└─────────────────────┘     Upload to Supabase
           │
           ├──► Schwab API (via schwab-py)
           ├──► Supabase (data storage)
           └──► AWS Secrets Manager (token storage)
```

## Prerequisites

1. **AWS Account**: Sign up at [aws.amazon.com](https://aws.amazon.com)
2. **AWS CLI**: Install and configure with your credentials
3. **Terraform**: Install from [terraform.io](https://www.terraform.io/downloads)
4. **Schwab API Credentials**: App Key and Secret from Schwab Developer Portal
5. **Supabase Project**: URL and Service Role Key

## Quick Start

### 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### 2. Create Terraform Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your credentials
```

**terraform.tfvars:**
```hcl
aws_region     = "us-east-1"
environment    = "prod"
default_ticker = "QQQ"

# Supabase
supabase_url = "https://your-project.supabase.co"
supabase_key = "your-service-role-key"

# Schwab API
schwab_app_key = "your-app-key"
schwab_secret  = "your-app-secret"
```

### 3. Deploy Infrastructure

```bash
cd backend
./deploy_lambda.sh --plan-only  # Preview changes
./deploy_lambda.sh              # Deploy
```

This script:
- Packages Lambda function with dependencies
- Creates deployment zip file
- Runs Terraform to provision AWS resources
- Outputs next steps for configuration

### 4. Upload Schwab Token

After initial Schwab authentication:

```bash
# Run authentication locally first
cd backend
python refresh_schwab_auth.py

# Upload token to AWS Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1
```

### 5. Test Lambda Function

```bash
# Manually invoke Lambda
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --payload '{}' \
  response.json

# View response
cat response.json
```

### 6. Monitor Execution

```bash
# Tail CloudWatch logs
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow

# View metrics in CloudWatch console
# Navigate to: CloudWatch > Metrics > AlphaKiteMax/RealTimeStreaming
```

## Resources Created

### Lambda Function
- **Name**: `alpha-kite-real-time-streamer`
- **Runtime**: Python 3.10
- **Memory**: 256 MB
- **Timeout**: 60 seconds
- **Handler**: `real_time_streamer.lambda_handler`

### EventBridge Rules
- **Market Open** (9:30-9:59 AM ET): Triggers every minute
- **Market Hours** (10:00 AM-3:59 PM ET): Triggers every minute
- **Market Close** (4:00 PM ET): Final trigger

### IAM Role & Policies
- **Role**: `alpha-kite-real-time-streamer-role`
- **Permissions**:
  - CloudWatch Logs (write)
  - Secrets Manager (read/write for token)
  - CloudWatch Metrics (write)

### Secrets Manager
- **Secret**: `schwab-api-token-prod`
- **Description**: OAuth token for Schwab API
- **Auto-refresh**: Lambda updates when token expires

### CloudWatch Log Group
- **Name**: `/aws/lambda/alpha-kite-real-time-streamer`
- **Retention**: 14 days

## Cost Estimate

Based on 390 executions/day during market hours:

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 8,580 invocations/month | **$0** (free tier) |
| Lambda | After 1M invocations | $0.20/month |
| Secrets Manager | 1 secret | $0.40/month |
| CloudWatch Logs | 14-day retention | ~$0.10/month |
| EventBridge | Rules and triggers | **$0** (free) |
| **Total** | | **~$0.50-0.70/month** |

## Monitoring & Alerts

### CloudWatch Metrics

Available in namespace `AlphaKiteMax/RealTimeStreaming`:

- `DataPointsFetched`: Number of data points per execution
- `SupabaseUploadSuccess`: Upload success/failure (1/0)
- `LatencyMilliseconds`: Execution latency
- `TokenRefreshEvents`: Token refresh occurrences
- `Errors`: Error count by type

### CloudWatch Alarms

Create alarms for monitoring:

```bash
# Alert when no data fetched (market issue)
aws cloudwatch put-metric-alarm \
  --alarm-name alpha-kite-no-data \
  --metric-name DataPointsFetched \
  --namespace AlphaKiteMax/RealTimeStreaming \
  --statistic Average \
  --period 300 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 3

# Alert on upload failures
aws cloudwatch put-metric-alarm \
  --alarm-name alpha-kite-upload-failures \
  --metric-name SupabaseUploadSuccess \
  --namespace AlphaKiteMax/RealTimeStreaming \
  --statistic Average \
  --period 300 \
  --threshold 0.8 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2
```

## Troubleshooting

### Lambda Function Not Triggering

Check EventBridge rules:
```bash
aws events list-rules --name-prefix alpha-kite
aws events list-targets-by-rule --rule alpha-kite-market-hours-every-minute
```

### Authentication Errors

Update Schwab token in Secrets Manager:
```bash
python backend/refresh_schwab_auth.py
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://backend/config/schwab_token.json
```

### No Data in Supabase

Check Lambda logs:
```bash
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 1h
```

Test Lambda manually:
```bash
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --log-type Tail \
  --payload '{}' \
  response.json | jq -r '.LogResult' | base64 -d
```

### High Costs

Lambda is well within free tier (1M requests/month). If costs increase:
1. Check execution count in CloudWatch
2. Verify EventBridge rules aren't over-triggering
3. Review Lambda memory/timeout settings

## Updating Lambda Code

After making changes to Lambda code:

```bash
cd backend
./deploy_lambda.sh
```

This repackages and redeploys the Lambda function.

## Cleanup

To destroy all resources:

```bash
cd infrastructure
terraform destroy
```

This removes:
- Lambda function
- IAM roles and policies
- EventBridge rules
- CloudWatch log groups
- Secrets Manager secrets (after 7-day recovery period)

## Security Best Practices

1. **Secrets Manager**: Never commit tokens to Git
2. **IAM Roles**: Use least-privilege permissions
3. **VPC**: Consider deploying Lambda in VPC for additional security
4. **Encryption**: Secrets Manager encrypts at rest by default
5. **Access Logs**: CloudWatch logs all invocations

## Support

For issues:
1. Check CloudWatch logs first
2. Review Terraform state: `terraform show`
3. Test Lambda locally: Use AWS SAM CLI
4. Verify Schwab API status
5. Check Supabase connectivity

## Next Steps

After deployment:
1. Monitor first hour of execution
2. Verify data appears in Supabase
3. Check frontend displays real-time data
4. Set up CloudWatch alarms
5. Configure SNS notifications (optional)

## Lambda Package Optimization

### Using uv for Faster Builds

This project uses `uv` (ultra-fast Python package manager) for significantly faster package installation and deployment:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Build optimized Lambda package
cd backend/lambda
./deploy_uv.sh
```

### Package Size Optimization

The deployment script automatically:
- Uses `uv` for faster package installation (10x faster than pip)
- Excludes heavy packages (pandas, numpy) not needed for Lambda
- Removes test files and unnecessary metadata
- Targets package size under 5MB for optimal Lambda performance
- Only includes essential runtime dependencies

### Benefits of uv

- **Speed**: 10-100x faster than pip for package resolution
- **Reliability**: Better dependency resolution and conflict detection
- **Size**: More efficient package management reduces Lambda package size
- **Compatibility**: Drop-in replacement for pip with better performance

