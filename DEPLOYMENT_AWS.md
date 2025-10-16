# AWS Lambda Real-Time Streaming Deployment Guide

Complete guide for deploying real-time equity data streaming using AWS Lambda + EventBridge.

## Overview

This deployment sets up automated real-time data streaming that:
- Runs every minute during market hours (9:30 AM - 4:00 PM ET)
- Fetches latest equity data from Schwab API
- Calculates SMA9 and VWAP indicators
- Uploads to Supabase automatically
- Costs ~$0.50/month (within AWS free tier)

## Prerequisites Checklist

- [ ] AWS Account created
- [ ] AWS CLI installed and configured
- [ ] Terraform installed (v1.0+)
- [ ] Schwab API credentials (App Key, Secret)
- [ ] Supabase project set up
- [ ] Schwab token authenticated locally

## Step-by-Step Deployment

### Step 1: AWS Account Setup

1. **Create AWS Account**: https://aws.amazon.com/free/
2. **Create IAM User** (recommended over root account):
   - Go to IAM Console
   - Click "Users" → "Add User"
   - Username: `alpha-kite-deployer`
   - Access type: Programmatic access
   - Attach policy: `AdministratorAccess` (or custom policy)
   - Save Access Key ID and Secret Access Key

3. **Configure AWS CLI**:
```bash
aws configure
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region: us-east-1
# Default output format: json
```

4. **Verify configuration**:
```bash
aws sts get-caller-identity
```

### Step 2: Install Terraform

**macOS:**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Linux:**
```bash
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

**Verify:**
```bash
terraform version
```

### Step 3: Authenticate with Schwab

Run authentication locally to generate token:

```bash
cd backend
source venv/bin/activate
python refresh_schwab_auth.py
```

This creates `backend/config/schwab_token.json` which we'll upload to AWS later.

### Step 4: Configure Terraform Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your credentials:

```hcl
aws_region     = "us-east-1"
environment    = "prod"
default_ticker = "QQQ"

# From Supabase Dashboard → Settings → API
supabase_url = "https://xwcauibwyxhsifnotnzz.supabase.co"
supabase_key = "your-service-role-key-here"

# From Schwab Developer Portal
schwab_app_key = "your-app-key-here"
schwab_secret  = "your-app-secret-here"
```

### Step 5: Deploy Infrastructure

```bash
cd backend
./deploy_lambda.sh --plan-only  # Review changes first
```

Review the Terraform plan. If everything looks good:

```bash
./deploy_lambda.sh  # Deploy to AWS
```

This will:
1. Package Lambda function with dependencies (~50MB)
2. Create Lambda function
3. Set up EventBridge scheduler (every minute during market hours)
4. Create IAM roles and policies
5. Set up CloudWatch logging
6. Create Secrets Manager secret for Schwab token

### Step 6: Upload Schwab Token to AWS

```bash
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://backend/config/schwab_token.json \
  --region us-east-1
```

Verify:
```bash
aws secretsmanager describe-secret \
  --secret-id schwab-api-token-prod \
  --region us-east-1
```

### Step 7: Test Lambda Function

Manually invoke Lambda to test:

```bash
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --payload '{}' \
  --region us-east-1 \
  response.json

cat response.json
```

Expected response:
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Data fetched and uploaded successfully\", \"ticker\": \"QQQ\", \"equity_rows\": 1, \"indicator_rows\": 1}"
}
```

### Step 8: Monitor CloudWatch Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow --region us-east-1

# Or view last 10 minutes
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 10m --region us-east-1
```

### Step 9: Verify Data in Supabase

Check your Supabase dashboard:
1. Go to Table Editor
2. Open `equity_data` table
3. Filter by today's date
4. Verify rows are being added every minute

Or query via SQL:
```sql
SELECT COUNT(*), MAX(timestamp) as latest
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp::date = CURRENT_DATE;
```

### Step 10: Verify Frontend Display

1. Open your Vercel dashboard: https://your-app.vercel.app
2. Select today's date
3. Verify chart shows minute-by-minute data
4. Check that latest data point is recent (< 2 minutes old)

## Monitoring & Maintenance

### CloudWatch Metrics

View metrics in AWS Console:
- Navigate to: CloudWatch → Metrics → AlphaKiteMax/RealTimeStreaming

Available metrics:
- `DataPointsFetched`: Number of data points per minute
- `SupabaseUploadSuccess`: Upload success rate
- `LatencyMilliseconds`: Execution time
- `TokenRefreshEvents`: Token refresh count

### Set Up Alarms

Create alarm for no data:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name alpha-kite-no-data-alert \
  --alarm-description "Alert when no data fetched for 15 minutes" \
  --metric-name DataPointsFetched \
  --namespace AlphaKiteMax/RealTimeStreaming \
  --statistic Sum \
  --period 900 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --region us-east-1
```

### Token Refresh

Schwab tokens expire periodically. Lambda automatically refreshes them, but if you see authentication errors:

```bash
# Re-authenticate locally
cd backend
python refresh_schwab_auth.py

# Upload new token
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1
```

## Troubleshooting

### Lambda Not Executing

**Check EventBridge rules:**
```bash
aws events list-rules --name-prefix alpha-kite --region us-east-1
```

**Verify Lambda has permission:**
```bash
aws lambda get-policy --function-name alpha-kite-real-time-streamer --region us-east-1
```

### Authentication Errors

**Check token in Secrets Manager:**
```bash
aws secretsmanager get-secret-value --secret-id schwab-api-token-prod --region us-east-1
```

**Refresh token:**
```bash
python backend/refresh_schwab_auth.py
aws secretsmanager put-secret-value --secret-id schwab-api-token-prod --secret-string file://backend/config/schwab_token.json --region us-east-1
```

### No Data in Supabase

**Check Lambda logs:**
```bash
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 1h --region us-east-1 | grep ERROR
```

**Test Lambda manually:**
```bash
aws lambda invoke --function-name alpha-kite-real-time-streamer --log-type Tail --payload '{}' response.json --region us-east-1
cat response.json | jq .
```

**Verify Supabase credentials:**
```bash
aws lambda get-function-configuration --function-name alpha-kite-real-time-streamer --region us-east-1 | jq .Environment
```

### High Latency

**Check Lambda memory:**
```bash
aws lambda get-function-configuration --function-name alpha-kite-real-time-streamer --region us-east-1 | jq .MemorySize
```

**Increase if needed:**
```bash
aws lambda update-function-configuration --function-name alpha-kite-real-time-streamer --memory-size 512 --region us-east-1
```

## Cost Optimization

Current setup is optimized for minimal cost:

| Resource | Monthly Cost |
|----------|--------------|
| Lambda (8,580 invocations) | $0 (free tier) |
| Secrets Manager | $0.40 |
| CloudWatch Logs (14-day retention) | ~$0.10 |
| **Total** | **~$0.50/month** |

To reduce costs further:
1. Reduce log retention: 7 days instead of 14
2. Use Parameter Store instead of Secrets Manager (free, but less secure)
3. Batch uploads: Every 5 minutes instead of 1 minute

## Updating Lambda Code

After making changes to Lambda code:

```bash
cd backend
./deploy_lambda.sh
```

Terraform will detect changes and update Lambda function automatically.

## Cleanup

To remove all AWS resources:

```bash
cd infrastructure
terraform destroy --auto-approve
```

This removes:
- Lambda function
- IAM roles and policies
- EventBridge rules
- CloudWatch log groups
- Secrets Manager secrets (after 7-day recovery)

## Production Checklist

Before going live:

- [ ] Test Lambda for full trading day
- [ ] Verify data accuracy in Supabase
- [ ] Check frontend displays data correctly
- [ ] Set up CloudWatch alarms
- [ ] Configure SNS notifications (optional)
- [ ] Document runbooks for common issues
- [ ] Set up backup/recovery plan
- [ ] Review IAM permissions (least privilege)
- [ ] Enable CloudTrail for audit logging
- [ ] Tag all resources appropriately

## Support & Resources

- **AWS Lambda Docs**: https://docs.aws.amazon.com/lambda/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/
- **Schwab API Docs**: https://developer.schwab.com
- **Supabase Docs**: https://supabase.com/docs

## Next Steps

After successful deployment:

1. **Monitor First Hour**: Watch CloudWatch logs for first 60 minutes
2. **Verify Data Quality**: Check Supabase for accurate timestamps and values
3. **Test Frontend**: Ensure dashboard displays real-time data
4. **Set Up Alerts**: Configure CloudWatch alarms for monitoring
5. **Document Issues**: Keep runbook of any problems encountered
6. **Optimize**: Fine-tune memory/timeout settings based on performance

Congratulations! Your real-time data streaming is now live! 🚀

