# Quick Start: AWS Lambda Real-Time Streaming

Get your real-time data streaming up and running in 15 minutes.

## TL;DR

```bash
# 1. Configure AWS
aws configure

# 2. Set up credentials
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your credentials

# 3. Authenticate with Schwab
cd ../backend
python refresh_schwab_auth.py

# 4. Deploy to AWS
./deploy_lambda.sh

# 5. Upload token
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json

# 6. Test
aws lambda invoke --function-name alpha-kite-real-time-streamer --payload '{}' response.json
cat response.json
```

## Detailed Steps

### 1. AWS Setup (5 minutes)

Create AWS account if you don't have one: https://aws.amazon.com/free/

Install AWS CLI:
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Configure credentials:
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, region (us-east-1), format (json)
```

### 2. Credentials (3 minutes)

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
supabase_url = "https://xwcauibwyxhsifnotnzz.supabase.co"  # Your Supabase URL
supabase_key = "your-service-role-key"                      # From Supabase Settings
schwab_app_key = "your-app-key"                             # From Schwab Developer
schwab_secret = "your-app-secret"                           # From Schwab Developer
```

### 3. Schwab Authentication (2 minutes)

```bash
cd ../backend
source venv/bin/activate  # If using venv
python refresh_schwab_auth.py
```

Follow prompts to authenticate. This creates `config/schwab_token.json`.

### 4. Deploy (5 minutes)

```bash
./deploy_lambda.sh
```

This packages and deploys everything to AWS. Takes ~5 minutes.

### 5. Upload Token (30 seconds)

```bash
aws secretsmanager put-secret-value \
  --secret-id schwab-api-token-prod \
  --secret-string file://config/schwab_token.json \
  --region us-east-1
```

### 6. Verify (1 minute)

Test Lambda:
```bash
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --payload '{}' \
  --region us-east-1 \
  response.json

cat response.json
```

Expected: `{"statusCode": 200, "body": "{\"message\": \"Data fetched...\"}"}`

Monitor logs:
```bash
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow
```

Check Supabase:
```sql
SELECT COUNT(*), MAX(timestamp) FROM equity_data WHERE ticker = 'QQQ' AND timestamp::date = CURRENT_DATE;
```

## What Happens Next?

1. **Every Minute**: Lambda runs during market hours (9:30 AM - 4:00 PM ET)
2. **Fetches Data**: Gets latest equity data from Schwab API
3. **Calculates**: SMA9 and VWAP indicators
4. **Uploads**: Data to Supabase automatically
5. **Frontend**: Your dashboard shows real-time data

## Monitoring

```bash
# Watch logs live
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --follow

# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace AlphaKiteMax/RealTimeStreaming \
  --metric-name DataPointsFetched \
  --dimensions Name=Ticker,Value=QQQ \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300
```

## Troubleshooting

### Lambda Not Running
```bash
aws events list-rules --name-prefix alpha-kite
# Should show 3 rules for market hours
```

### Authentication Errors
```bash
# Refresh token
python backend/refresh_schwab_auth.py
aws secretsmanager put-secret-value --secret-id schwab-api-token-prod --secret-string file://backend/config/schwab_token.json
```

### No Data in Supabase
```bash
# Check Lambda logs
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 1h | grep ERROR

# Test manually
aws lambda invoke --function-name alpha-kite-real-time-streamer --payload '{}' response.json
```

## Cost

- **Lambda**: $0/month (free tier)
- **Secrets Manager**: $0.40/month
- **CloudWatch**: ~$0.10/month
- **Total**: ~$0.50/month

## Cleanup

To remove everything:
```bash
cd infrastructure
terraform destroy
```

## Next Steps

1. ✅ Deploy Lambda
2. ✅ Verify data streaming
3. ⏭️ Set up CloudWatch alarms
4. ⏭️ Monitor for full trading day
5. ⏭️ Optimize based on performance

## Support

- Full guide: See `DEPLOYMENT_AWS.md`
- Infrastructure docs: See `infrastructure/README.md`
- Test locally: `python backend/lambda/test_local.py`

Questions? Check CloudWatch logs first:
```bash
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 10m
```

