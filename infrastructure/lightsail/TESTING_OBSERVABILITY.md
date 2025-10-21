# Testing & Observability Guide - Lightsail Streaming Service

## 🎯 Complete Guide to Monitoring Your Deployment

This guide shows you **exactly** how to watch your Lightsail streaming service in action.

---

## ✅ Commit Summary

**What Was Done:**
- ✅ Removed Lambda infrastructure (14 files)
- ✅ Created Lightsail microservices architecture
- ✅ Configured every-second streaming to Supabase
- ✅ Updated all documentation
- ✅ **Committed to Git**: `refactor: migrate from Lambda to Lightsail microservices architecture`

**Changes**: 37 files changed, 4734 insertions(+), 1680 deletions(-)

---

## 🔍 How to Observe the Service

### Method 1: AWS Lightsail Console (Primary Dashboard)

**Step 1: Access Lightsail Console**
```
https://lightsail.aws.amazon.com/ls/webapp/home/instances
```

**Step 2: Find Your Instance**
- Look for: `equity-options-streamer`
- Should show status: **Running** (green checkmark)

**Step 3: View Metrics**

Click on instance → **Metrics** tab

**You'll see 4 graphs:**

1. **CPU Utilization**
   - Normal: 5-15%
   - During market hours: Steady CPU usage
   - Alert if: >80% sustained

2. **Network In**
   - Shows: Data coming from Schwab WebSocket
   - Pattern: Constant during market hours
   - Alert if: Drops to 0 during market hours

3. **Network Out**
   - Shows: Data being written to Supabase
   - Pattern: Steady outbound every second
   - Alert if: No outbound traffic during market hours

4. **Status Check Failures**
   - Should be: 0 (all green)
   - Alert if: Any failures

**Screenshots in AWS Console:**
```
Lightsail → Instances → equity-options-streamer → Metrics
```

---

### Method 2: SSH + Real-Time Logs (Most Detailed)

**Step 1: SSH into Instance**
```bash
# Get instance IP from deployment output
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP>
```

**Step 2: Watch Real-Time Logs**
```bash
cd /opt/streaming-service
sudo docker-compose logs -f
```

**What You'll See** (every second during market hours):
```json
{
  "timestamp": "2025-10-21T14:30:01.123Z",
  "level": "info",
  "event": "data_buffered",
  "ticker": "QQQ",
  "equity_buffer_size": 1,
  "indicator_buffer_size": 1
}
{
  "timestamp": "2025-10-21T14:30:01.234Z",
  "level": "info",
  "event": "equity_data_flushed",
  "rows": 1
}
{
  "timestamp": "2025-10-21T14:30:01.345Z",
  "level": "info",
  "event": "indicator_data_flushed",
  "rows": 1
}
```

**Useful Log Commands:**
```bash
# View last 100 lines
sudo docker-compose logs --tail=100

# Filter for errors only
sudo docker-compose logs -f | grep error

# Filter for specific events
sudo docker-compose logs -f | grep "equity_data_flushed"

# Check service status
sudo docker-compose ps
```

---

### Method 3: Supabase Real-Time Monitoring (Verify Data Flow)

**Open Supabase SQL Editor:**
```
https://app.supabase.com/project/YOUR_PROJECT/sql
```

**Run These Queries:**

**1. See Live Data Streaming In** (run every few seconds)
```sql
SELECT 
    timestamp,
    price,
    volume,
    AGE(NOW(), timestamp) as data_age_seconds
FROM equity_data 
WHERE ticker = 'QQQ' 
ORDER BY timestamp DESC 
LIMIT 10;
```

**Expected Result:**
- New rows every ~1 second
- `data_age_seconds` should be < 5 seconds
- Continuous updates during market hours

**2. Check Streaming Health**
```sql
SELECT * FROM get_streaming_health('QQQ');
```

**Expected Output:**
| ticker | last_update | records_last_hour | avg_batch_size | error_rate | status |
|--------|-------------|-------------------|----------------|------------|--------|
| QQQ    | 2025-10-21 14:30:00 | 3600 | 1.00 | 0.00 | healthy |

**3. Count Records Per Minute** (should be ~60)
```sql
SELECT 
    DATE_TRUNC('minute', timestamp) AS minute,
    COUNT(*) AS records_per_minute
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '30 minutes'
GROUP BY DATE_TRUNC('minute', timestamp)
ORDER BY minute DESC;
```

**Expected:**
- ~60 records per minute during market hours
- 0 records outside market hours

---

### Method 4: Health Check Script (Automated)

**From Your Local Machine:**
```bash
cd infrastructure/lightsail
python health_check.py
```

**Sample Output:**
```
╔══════════════════════════════════════════════════════════════╗
║        🏥 STREAMING SERVICE HEALTH CHECK                     ║
╚══════════════════════════════════════════════════════════════╝
Timestamp: 2025-10-21T14:30:00Z
Ticker: QQQ
Overall Status: ✅ healthy
════════════════════════════════════════════════════════════════

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
   latest_timestamp: 2025-10-21T14:29:55Z
   age_minutes: 0.1

ℹ️  Streaming Metrics
   Status: INFO
   Streaming metrics not available (this is OK for new deployments)

════════════════════════════════════════════════════════════════
```

---

### Method 5: AWS CloudWatch (Advanced Monitoring)

**Access CloudWatch:**
```
AWS Console → CloudWatch → Metrics → Lightsail
```

**Available Metrics:**
1. CPUUtilization
2. NetworkIn
3. NetworkOut
4. StatusCheckFailed_Instance
5. StatusCheckFailed_System

**Create Custom Dashboard:**
```bash
# Create a monitoring dashboard
aws cloudwatch put-dashboard \
  --dashboard-name EquityStreamingMonitor \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/Lightsail", "CPUUtilization"],
            [".", "NetworkOut"],
            [".", "NetworkIn"]
          ],
          "period": 60,
          "stat": "Average",
          "region": "us-east-1",
          "title": "Streaming Service Metrics"
        }
      }
    ]
  }'
```

**Set Up Alarms:**
```bash
# Alert if CPU > 80%
aws cloudwatch put-metric-alarm \
  --alarm-name streaming-high-cpu \
  --alarm-description "Alert if CPU usage > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/Lightsail \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Alert if no network activity
aws cloudwatch put-metric-alarm \
  --alarm-name streaming-no-activity \
  --alarm-description "Alert if no network activity" \
  --metric-name NetworkOut \
  --namespace AWS/Lightsail \
  --statistic Sum \
  --period 300 \
  --threshold 1000 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2
```

---

## 🧪 Step-by-Step Testing After Deployment

### Phase 1: Verify Deployment (5 minutes)

**1. Check Instance is Running**
```bash
# Via AWS CLI
aws lightsail get-instance \
  --instance-name equity-options-streamer \
  --query 'instance.state.name' \
  --output text

# Expected: running
```

**2. SSH into Instance**
```bash
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP>
```

**3. Check Service Status**
```bash
cd /opt/streaming-service
sudo docker-compose ps

# Expected output:
# NAME                    STATUS
# equity-options-streamer Up (healthy)
```

### Phase 2: Verify Data Flow (10 minutes)

**1. Watch Logs for Data Writes**
```bash
# On Lightsail instance
sudo docker-compose logs -f | grep "equity_data_flushed"

# You should see new lines every second during market hours
```

**2. Check Supabase for New Data**
```sql
-- Run in Supabase SQL Editor
SELECT COUNT(*) as new_records
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '5 minutes';

-- Should return > 0 during market hours
```

**3. Verify Timestamp Freshness**
```sql
SELECT 
    ticker,
    MAX(timestamp) as latest_data,
    AGE(NOW(), MAX(timestamp)) as age
FROM equity_data
WHERE ticker = 'QQQ'
GROUP BY ticker;

-- age should be < 10 seconds during market hours
```

### Phase 3: Test Health Monitoring (5 minutes)

**1. Run Health Check Script**
```bash
# From your local machine
cd infrastructure/lightsail
python health_check.py

# All checks should pass (green checkmarks)
```

**2. Check Streaming Metrics in Database**
```sql
SELECT 
    timestamp,
    records_processed,
    error_count,
    service_status
FROM streaming_metrics
WHERE ticker = 'QQQ'
ORDER BY timestamp DESC
LIMIT 10;

# error_count should be 0
# service_status should be 'running'
```

### Phase 4: Stress Test (Optional, 15 minutes)

**1. Monitor Resource Usage**
```bash
# On Lightsail instance
sudo docker stats

# Check:
# - CPU < 50%
# - Memory < 400MB
```

**2. Check Data Consistency**
```sql
-- Verify no gaps in data
SELECT 
    DATE_TRUNC('minute', timestamp) AS minute,
    COUNT(*) AS records
FROM equity_data
WHERE ticker = 'QQQ'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', timestamp)
ORDER BY minute DESC;

-- Should have ~60 records per minute (no gaps)
```

---

## 📊 What "Success" Looks Like

### AWS Lightsail Console
- ✅ Instance status: **Running** (green)
- ✅ CPU: 5-15% (steady)
- ✅ Network Out: Consistent traffic
- ✅ Status checks: 0 failures

### Docker Logs
```json
{"event": "equity_data_flushed", "rows": 1, "timestamp": "..."}  // Every second
{"event": "indicator_data_flushed", "rows": 1, "timestamp": "..."}  // Every second
```

### Supabase Database
- ✅ New rows every ~1 second
- ✅ Latest timestamp < 10 seconds old
- ✅ ~60 records per minute
- ✅ No errors in streaming_metrics table

### Health Check Script
```
Overall Status: ✅ healthy
Database connection: healthy
Recent data: Found 60 records
Data freshness: 0.1 minutes old
```

---

## 🚨 What "Problems" Look Like

### ❌ Service Not Running
**AWS Console:** Instance shows "Stopped"
**Fix:**
```bash
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP>
cd /opt/streaming-service
sudo docker-compose up -d
```

### ❌ No Data in Supabase
**Supabase Query:** Returns 0 rows
**Check Logs:**
```bash
sudo docker-compose logs | grep error
```
**Common Causes:**
- Invalid Supabase credentials
- Network connectivity issues
- Schwab token expired

### ❌ High CPU Usage
**AWS Console:** CPU > 80%
**Check:**
```bash
sudo docker stats
# If memory leak, restart:
sudo docker-compose restart
```

### ❌ Stale Data
**Health Check:** "Data freshness: 10 minutes old"
**Investigate:**
```bash
# Check if service is stuck
sudo docker-compose logs --tail=50

# Check if market is open
date  # Verify time

# Restart if needed
sudo docker-compose restart
```

---

## 📱 Mobile Monitoring

### AWS Console Mobile App
1. Download "AWS Console" app (iOS/Android)
2. Login to your AWS account
3. Navigate to: Services → Lightsail
4. View instance metrics on your phone

### Email Alerts (Set Up Once)
```bash
# Create SNS topic
aws sns create-topic --name streaming-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:streaming-alerts \
  --protocol email \
  --notification-endpoint your@email.com

# Confirm subscription via email link
```

---

## 🎯 Quick Monitoring Checklist

**Daily** (30 seconds):
- [ ] AWS Console: Instance status = Running
- [ ] Supabase: Latest data < 1 minute old

**Weekly** (5 minutes):
- [ ] Run health check script
- [ ] Check streaming_metrics for errors
- [ ] Review CloudWatch metrics

**Monthly** (15 minutes):
- [ ] Check disk usage: `df -h`
- [ ] Review error logs
- [ ] Verify token expiration date

---

## 📚 Complete Monitoring Workflow

**1. First 5 Minutes After Deployment:**
```bash
# SSH into instance
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP>

# Watch logs
cd /opt/streaming-service
sudo docker-compose logs -f

# Look for:
# ✅ "streaming_service_starting"
# ✅ "streaming_connection_established"  
# ✅ "equity_data_flushed" (every second)
```

**2. After 10 Minutes:**
```sql
-- In Supabase SQL Editor
SELECT COUNT(*) FROM equity_data WHERE ticker = 'QQQ';
-- Should have ~600 records (10 min × 60 sec/min)
```

**3. After 1 Hour:**
```bash
# Run health check
python health_check.py

# Check AWS metrics
# Visit: https://lightsail.aws.amazon.com/
# View CPU, Network graphs (should be stable)
```

**4. Ongoing:**
- Check AWS Console once daily
- Run health_check.py once weekly
- Query Supabase for data verification

---

## 🔗 Quick Links

**AWS Resources:**
- [Lightsail Console](https://lightsail.aws.amazon.com/)
- [CloudWatch Metrics](https://console.aws.amazon.com/cloudwatch/)
- [CloudWatch Alarms](https://console.aws.amazon.com/cloudwatch/home#alarmsV2:)

**Supabase:**
- [Your Project Dashboard](https://app.supabase.com/project/YOUR_PROJECT)
- [SQL Editor](https://app.supabase.com/project/YOUR_PROJECT/sql)
- [Table Editor](https://app.supabase.com/project/YOUR_PROJECT/editor)

**Documentation:**
- [Lightsail Monitoring](./MONITORING.md)
- [Health Check Script](./health_check.py)
- [Deployment Guide](./README.md)

---

**You now have 5 different ways to observe your streaming service!** 🎉

**Most Important:**
1. AWS Lightsail Console (instance health)
2. Supabase SQL queries (data verification)
3. SSH + Docker logs (real-time troubleshooting)

---

*Last Updated: October 21, 2025*

