# 🚀 Lightsail Streaming Service - Quick Start

Deploy a perpetual equity/options data streaming service to AWS Lightsail in under 10 minutes.

## Prerequisites

- ✅ AWS CLI installed and configured
- ✅ Schwab API credentials (app key + secret)
- ✅ Supabase project with service role key
- ✅ ~$3.50/month budget for Lightsail

## 5-Minute Setup

### 1️⃣ Configure Environment (2 minutes)

```bash
cd infrastructure/lightsail
cp env.template .env
nano .env  # or use your favorite editor
```

**Required values:**
```bash
STREAM_TICKER=QQQ                              # Ticker to stream
SCHWAB_APP_KEY=your_key_here                   # From Schwab developer portal
SCHWAB_APP_SECRET=your_secret_here             # From Schwab developer portal
SUPABASE_URL=https://xxx.supabase.co           # From Supabase project settings
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...            # From Supabase → Settings → API
```

### 2️⃣ Apply Database Schema (1 minute)

In Supabase Dashboard → SQL Editor:

```sql
-- Run these migrations in order:
-- 1. supabase/migrations/20251015151016_create_equity_and_indicators_tables.sql
-- 2. supabase/migrations/20251019000000_create_option_prices_table.sql
-- 3. supabase/migrations/20251021000000_streaming_optimizations.sql
```

Or use the Supabase CLI:
```bash
cd ../../supabase
supabase db push
```

### 3️⃣ Deploy to Lightsail (5 minutes)

```bash
cd ../infrastructure/lightsail
chmod +x deploy.sh
./deploy.sh
```

**That's it!** The script will:
- ✅ Create a Lightsail instance
- ✅ Install Docker and dependencies
- ✅ Deploy the streaming service
- ✅ Start streaming data to Supabase

## Verify It's Working

### Check Service Logs

```bash
# Get instance IP from deploy script output
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP> \
  'cd /opt/streaming-service && sudo docker-compose logs -f'
```

You should see logs like:
```json
{"event": "streaming_service_starting", "ticker": "QQQ", "timestamp": "2025-10-21T14:30:00Z"}
{"event": "streaming_connection_established", "timestamp": "2025-10-21T14:30:05Z"}
{"event": "equity_data_flushed", "rows": 10, "timestamp": "2025-10-21T14:31:00Z"}
```

### Check Supabase

In Supabase → Table Editor:

```sql
-- Check equity data
SELECT * FROM equity_data 
WHERE ticker = 'QQQ' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check indicators
SELECT * FROM indicators 
WHERE ticker = 'QQQ' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check streaming health
SELECT * FROM get_streaming_health('QQQ');
```

## Common Issues

### ❌ No data in Supabase

**Fix:**
```bash
# Check service logs for errors
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'sudo docker-compose logs | grep error'

# Verify credentials
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'cat /opt/streaming-service/.env'

# Restart service
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'cd /opt/streaming-service && sudo docker-compose restart'
```

### ❌ Schwab authentication failed

**Fix:**
1. Verify credentials in `.env`
2. Ensure Schwab tokens are valid
3. See [QUICKSTART_OAUTH.md](../../docs/guides/QUICKSTART_OAUTH.md) for token setup

### ❌ Service keeps restarting

**Fix:**
```bash
# Check why it's failing
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'sudo docker-compose logs --tail=100'

# Common issues:
# - Missing env variables → check .env file
# - Invalid Supabase URL/key → verify in Supabase dashboard
# - Network issues → check Lightsail firewall rules
```

## Customization

### Change Ticker

```bash
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP>

# Edit .env
sudo nano /opt/streaming-service/.env
# Change: STREAM_TICKER=SPY

# Restart
cd /opt/streaming-service
sudo docker-compose restart
```

### Adjust Batch Size (Performance Tuning)

```bash
# For more frequent updates (lower latency):
BATCH_SIZE=5
BATCH_INTERVAL=30

# For fewer database writes (cost savings):
BATCH_SIZE=50
BATCH_INTERVAL=300
```

### Stream Multiple Tickers

Currently supports one ticker per instance. To stream multiple tickers:

**Option 1:** Deploy multiple instances
```bash
LIGHTSAIL_INSTANCE_NAME=streamer-qqq STREAM_TICKER=QQQ ./deploy.sh
LIGHTSAIL_INSTANCE_NAME=streamer-spy STREAM_TICKER=SPY ./deploy.sh
```

**Option 2:** Modify `streaming_service.py` to handle multiple tickers (advanced)

## Cost Breakdown

| Service | Plan | Cost/Month |
|---------|------|------------|
| AWS Lightsail | Nano (512MB RAM) | $3.50 |
| Supabase | Free tier | $0 |
| **Total** | | **$3.50** |

### Scaling Up

Need more performance? Upgrade the Lightsail instance:

```bash
# Small instance (1GB RAM, 1 vCPU) - $5/month
aws lightsail update-instance-bundle \
  --instance-name equity-options-streamer \
  --bundle-id small_2_0

# Medium instance (2GB RAM, 1 vCPU) - $10/month
aws lightsail update-instance-bundle \
  --instance-name equity-options-streamer \
  --bundle-id medium_2_0
```

## Maintenance

### View Logs
```bash
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'sudo journalctl -u docker -f'
```

### Restart Service
```bash
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'cd /opt/streaming-service && sudo docker-compose restart'
```

### Update Service Code
```bash
cd infrastructure/lightsail
# Make your changes to streaming_service.py
./deploy.sh  # Re-deploys with new code
```

### Stop Service (Pause Streaming)
```bash
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'cd /opt/streaming-service && sudo docker-compose down'
```

### Delete Everything (Stop Billing)
```bash
aws lightsail delete-instance \
  --instance-name equity-options-streamer \
  --region us-east-1
```

## Monitoring

### Service Health Dashboard

```sql
-- In Supabase SQL Editor

-- Overall health
SELECT * FROM get_streaming_health();

-- Records per hour
SELECT 
    DATE_TRUNC('hour', timestamp) AS hour,
    COUNT(*) AS records
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Latest data
SELECT 
    ticker,
    MAX(timestamp) AS last_update,
    AGE(NOW(), MAX(timestamp)) AS time_ago
FROM equity_data
GROUP BY ticker;
```

### Set Up Alerts

Add to `streaming_service.py` or use Supabase Edge Functions:

```python
# Alert if no data for 5 minutes
last_update = max(equity_buffer, key=lambda x: x['timestamp'])
if datetime.now() - last_update > timedelta(minutes=5):
    # Send alert (email, SMS, Slack, etc.)
    logger.error("no_data_received", minutes=5)
```

## Next Steps

1. ✅ **Set up monitoring**: Add alerts for service health
2. ✅ **Build a dashboard**: Use the frontend to visualize streaming data
3. ✅ **Add more data sources**: Stream options data, multiple tickers
4. ✅ **Implement trading logic**: Use streamed data for automated trading

## Resources

- [Full Documentation](README.md)
- [Database Schema](SCHEMA.md)
- [Schwab OAuth Setup](../../docs/guides/QUICKSTART_OAUTH.md)
- [Troubleshooting Guide](README.md#-troubleshooting)

## Support

If you run into issues:

1. Check the logs (see "Verify It's Working" above)
2. Review [README.md](README.md) for detailed troubleshooting
3. Verify schema is applied correctly in Supabase
4. Ensure all environment variables are set correctly

---

**Time to first data**: ~10 minutes  
**Monthly cost**: ~$3.50  
**Data retention**: 90 days (configurable)  
**Uptime**: 99.9%+ (with auto-restart)

