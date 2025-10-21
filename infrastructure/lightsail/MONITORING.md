# Monitoring & Observability - Lightsail Streaming Service

## 📊 Overview

This guide shows you how to monitor the Lightsail streaming service in action.

---

## 🖥️ AWS Lightsail Monitoring

### Access Lightsail Console

1. **Go to AWS Lightsail Console**
   ```
   https://lightsail.aws.amazon.com/
   ```

2. **Select your region** (e.g., us-east-1)

3. **Find your instance**: `equity-options-streamer`

### Instance Dashboard

**Metrics Available:**
- ✅ CPU utilization
- ✅ Network in/out
- ✅ Status checks
- ✅ Instance state

**Screenshot locations:**
```
Lightsail Console → Instances → equity-options-streamer → Metrics tab
```

**What to look for:**
- CPU should be low (5-15% for nano instance)
- Network out should show steady traffic (writes to Supabase)
- Status checks should be green
- Instance state should be "Running"

---

## 🔍 Real-Time Monitoring Options

### Option 1: SSH + Docker Logs (Recommended)

```bash
# SSH into your instance
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP>

# View streaming logs in real-time
cd /opt/streaming-service
sudo docker-compose logs -f

# Filter for specific events
sudo docker-compose logs -f | grep "equity_data_flushed"

# View last 100 lines
sudo docker-compose logs --tail=100

# View service status
sudo docker-compose ps
```

**What you'll see:**
```json
{
  "event": "streaming_service_starting",
  "ticker": "QQQ",
  "batch_size": 1,
  "batch_interval": 1,
  "timestamp": "2025-10-21T14:30:00Z"
}
{
  "event": "streaming_connection_established",
  "timestamp": "2025-10-21T14:30:05Z"
}
{
  "event": "equity_data_flushed",
  "rows": 1,
  "timestamp": "2025-10-21T14:30:06Z"
}
```

### Option 2: Health Check Script

```bash
# From your local machine (while connected via SSH or locally if you have dependencies)
cd infrastructure/lightsail
python health_check.py
```

**Output:**
```
╔══════════════════════════════════════════════════════════════════╗
║            🏥 STREAMING SERVICE HEALTH CHECK                     ║
╚══════════════════════════════════════════════════════════════════╝
Timestamp: 2025-10-21T14:30:00Z
Ticker: QQQ
Overall Status: ✅ healthy

✅ Database Connection
   Status: HEALTHY
   Database connection successful

✅ Recent Data
   Status: HEALTHY
   Found 60 records in last 5 minutes
   latest_timestamp: 2025-10-21T14:29:55Z
   age_seconds: 5.2
   latest_price: 389.45

✅ Data Freshness
   Status: HEALTHY
   Latest data is 0.1 minutes old
```

### Option 3: Supabase Real-Time Monitoring

**SQL Editor Queries:**

```sql
-- See data streaming in (run repeatedly)
SELECT 
    timestamp,
    price,
    volume,
    AGE(NOW(), timestamp) as age
FROM equity_data 
WHERE ticker = 'QQQ' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check streaming health
SELECT * FROM get_streaming_health('QQQ');

-- View metrics for last hour
SELECT 
    timestamp,
    records_processed,
    error_count,
    service_status
FROM streaming_metrics
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Count records per minute (should be ~1)
SELECT 
    DATE_TRUNC('minute', timestamp) AS minute,
    COUNT(*) AS records
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', timestamp)
ORDER BY minute DESC
LIMIT 10;
```

### Option 4: AWS CloudWatch (Lightsail Metrics)

**Navigate to:**
```
AWS Console → Lightsail → Instances → equity-options-streamer → Metrics
```

**Available Metrics:**
1. **CPU Utilization**
   - Should be: 5-15% (normal operation)
   - Alert if: >80% sustained

2. **Network Out**
   - Should show: Steady outbound traffic
   - Pattern: Regular writes every second
   - Alert if: Drops to 0 during market hours

3. **Network In**
   - Should show: Inbound traffic from Schwab WebSocket
   - Pattern: Constant during market hours

4. **Status Check Failures**
   - Should be: 0 (green)
   - Alert if: Any failures

**Set up CloudWatch Alarms:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lightsail-high-cpu \
  --alarm-description "Alert if CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/Lightsail \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## 📈 What to Expect

### During Market Hours (9:30 AM - 4:00 PM ET)

**Docker Logs:**
- New log entry every second
- `equity_data_flushed` event every second
- `indicator_data_flushed` event every second
- No errors

**Supabase:**
- New row in `equity_data` table every second
- New row in `indicators` table every second
- Records should be ~1 second old (max)

**AWS Lightsail:**
- CPU: 5-15%
- Network Out: Steady (writing to Supabase)
- Status: Running (green)

### Outside Market Hours

**Docker Logs:**
- Service still running
- Logs showing "market_closed" checks
- No data writes

**Supabase:**
- No new data (as expected)
- Latest timestamp from market close

---

## 🚨 Alerts & Monitoring Setup

### Create CloudWatch Dashboard

```bash
# Create a custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name EquityStreamingDashboard \
  --dashboard-body file://dashboard-config.json
```

**dashboard-config.json:**
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/Lightsail", "CPUUtilization", { "stat": "Average" } ],
          [ ".", "NetworkIn", { "stat": "Sum" } ],
          [ ".", "NetworkOut", { "stat": "Sum" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lightsail Instance Metrics"
      }
    }
  ]
}
```

### Set Up SNS Alerts (Optional)

```bash
# Create SNS topic
aws sns create-topic --name equity-streaming-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:equity-streaming-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create alarm
aws cloudwatch put-metric-alarm \
  --alarm-name streaming-service-down \
  --alarm-description "Alert if no network activity" \
  --metric-name NetworkOut \
  --namespace AWS/Lightsail \
  --statistic Sum \
  --period 300 \
  --threshold 1000 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:equity-streaming-alerts
```

---

## 🔧 Troubleshooting Dashboard

### Quick Diagnostic Commands

```bash
# SSH into instance
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP>

# Check if service is running
sudo docker-compose ps

# Check recent logs
sudo docker-compose logs --tail=50

# Check container resource usage
sudo docker stats

# Check disk space
df -h

# Check memory usage
free -h

# Restart service if needed
sudo docker-compose restart

# Rebuild and restart (if code updated)
sudo docker-compose down
sudo docker-compose up -d --build
```

### Common Issues & Solutions

**Issue: No logs showing**
```bash
# Check if container is running
sudo docker-compose ps

# If not running, check why
sudo docker-compose logs

# Restart
sudo docker-compose up -d
```

**Issue: Data not appearing in Supabase**
```bash
# Check logs for Supabase errors
sudo docker-compose logs | grep -i supabase

# Verify environment variables
cat .env | grep SUPABASE

# Test connection manually
python health_check.py
```

**Issue: High CPU usage**
```bash
# Check what's consuming CPU
sudo docker stats

# Check if multiple instances running
ps aux | grep streaming

# Restart with resource limits
sudo docker-compose down
sudo docker-compose up -d
```

---

## 📊 Performance Baselines

### Normal Operation

| Metric | Expected Value | Alert Threshold |
|--------|----------------|-----------------|
| CPU Usage | 5-15% | >80% |
| Memory Usage | 100-200 MB | >400 MB |
| Network Out | 5-10 KB/s | <1 KB/s during market hours |
| Disk Usage | <5 GB | >15 GB |
| Records/minute | ~60 | <1 during market hours |
| Latency | <1 second | >5 seconds |

### Health Check Results

```bash
# Good health check
Overall Status: ✅ healthy
Database connection: healthy
Recent data: Found 60 records
Data freshness: 0.1 minutes old
Streaming metrics: healthy

# Warning state
Overall Status: ⚠️ warning
Recent data: Found 10 records (low)
Data freshness: 5.2 minutes old (stale)

# Error state
Overall Status: ❌ error
Database connection: error
Recent data: No data found
Data freshness: 20 minutes old
```

---

## 📱 Monitoring from Mobile

### AWS Console Mobile App

1. Download "AWS Console" app (iOS/Android)
2. Login to your AWS account
3. Navigate to: Lightsail → Instances
4. View real-time metrics

### Email Alerts

Set up SNS email alerts (see above) to get notifications on your phone.

---

## 🎯 Quick Monitoring Checklist

Daily checks:
- [ ] Instance status is "Running" (green)
- [ ] CPU < 20%
- [ ] Recent data in Supabase (< 1 minute old)
- [ ] No errors in logs

Weekly checks:
- [ ] Review `streaming_metrics` table for errors
- [ ] Check disk usage (< 10 GB)
- [ ] Verify token expiration date

Monthly checks:
- [ ] Review CloudWatch metrics history
- [ ] Check Supabase storage usage
- [ ] Update dependencies if needed

---

## 📚 Additional Resources

- [AWS Lightsail Metrics](https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-viewing-instance-health-metrics)
- [Docker Compose Logs](https://docs.docker.com/compose/reference/logs/)
- [Supabase Monitoring](https://supabase.com/docs/guides/platform/performance)

---

*Last Updated: October 21, 2025*

