# Lightsail Streaming Service - Complete Index

> **Minimal AWS Lightsail deployment for perpetual Equity/Options streaming to Supabase**  
> Cost: ~$3.50/month | Setup time: ~10 minutes | Uptime: 99.9%+

## 📁 Files in This Directory

### 📘 Documentation

| File | Purpose | Start Here? |
|------|---------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | **5-minute setup guide** | ✅ **START HERE** |
| [README.md](README.md) | Complete documentation | After quickstart |
| [SCHEMA.md](SCHEMA.md) | Database schema reference | For database work |
| [INDEX.md](INDEX.md) | This file - overview | You are here |

### 🚀 Deployment Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `deploy.sh` | Main deployment (Docker) | `./deploy.sh` |
| `deploy-systemd.sh` | Alternative deployment (systemd) | `./deploy-systemd.sh` |

### 🐍 Python Code

| File | Purpose | Run Directly? |
|------|---------|---------------|
| `streaming_service.py` | Main streaming service | ✅ `python streaming_service.py` |
| `health_check.py` | Health monitoring script | ✅ `python health_check.py` |

### 🐳 Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container definition for streaming service |
| `docker-compose.yml` | Docker Compose configuration |

### ⚙️ Configuration Files

| File | Purpose | Required? |
|------|---------|-----------|
| `env.template` | Environment variables template | Copy to `.env` |
| `.env` | Your actual credentials | ✅ Create this |
| `requirements.txt` | Python dependencies | Auto-used |
| `systemd-service.service` | Systemd service definition | For systemd deployment |

### 📊 Database Migrations

| File | Purpose |
|------|---------|
| `../../supabase/migrations/20251015151016_create_equity_and_indicators_tables.sql` | Creates equity & indicator tables |
| `../../supabase/migrations/20251019000000_create_option_prices_table.sql` | Creates options table |
| `../../supabase/migrations/20251021000000_streaming_optimizations.sql` | Adds streaming optimizations |

## 🎯 Quick Navigation

### I want to...

**...get started quickly**
→ Read [QUICKSTART.md](QUICKSTART.md)

**...understand the database schema**
→ Read [SCHEMA.md](SCHEMA.md)

**...deploy to Lightsail**
→ Run `./deploy.sh`

**...check if the service is healthy**
→ Run `python health_check.py`

**...see all configuration options**
→ Read [README.md](README.md)

**...troubleshoot issues**
→ See [README.md - Troubleshooting](README.md#-troubleshooting)

**...modify the streaming logic**
→ Edit `streaming_service.py`

**...change what's being streamed**
→ Edit `.env` (change `STREAM_TICKER`)

**...understand the architecture**
→ See [README.md - Architecture](README.md#%EF%B8%8F-architecture)

## 📊 Database Schema Summary

The streaming service writes to these Supabase tables:

### Primary Tables

1. **equity_data** - Real-time equity prices
   - ticker, timestamp, price, volume
   - ~1 row per second during market hours
   - 90-day retention recommended

2. **indicators** - Calculated indicators
   - ticker, timestamp, sma9, vwap
   - Same frequency as equity_data
   - 90-day retention recommended

3. **option_prices** - Options data (0DTE)
   - ticker, timestamp, option_type, strike_price, expiration_date
   - bid, ask, volume, greeks (delta, gamma, theta, vega)
   - 30-day retention recommended

4. **streaming_metrics** - Service health
   - timestamp, records_processed, error_count, service_status
   - Used for monitoring and alerting
   - 30-day retention recommended

### Helper Views & Functions

- `equity_data_stats` - Materialized view for daily stats
- `get_streaming_health()` - Function to check service health
- `cleanup_old_equity_data()` - Function to remove old data

See [SCHEMA.md](SCHEMA.md) for complete schema documentation.

## 🏗️ Architecture Overview

```
                    ┌─────────────────────┐
                    │  Schwab WebSocket   │
                    │  (Real-time data)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Streaming Service   │
┌──────────────────►│ - Buffers data      │
│                   │ - Calculates SMA9   │
│   Auto-restart    │ - Calculates VWAP   │
│   on failure      │ - Batches writes    │
│                   └──────────┬──────────┘
│                              │
│                              ▼
│                   ┌─────────────────────┐
│                   │   Supabase DB       │
│                   │ - equity_data       │
│                   │ - indicators        │
│                   │ - option_prices     │
│                   │ - streaming_metrics │
│                   └─────────────────────┘
│                              │
│                              ▼
│                   ┌─────────────────────┐
│                   │   Frontend/API      │
│                   │ (Dashboard, charts) │
│                   └─────────────────────┘
│
└─── AWS Lightsail Instance ($3.50/month)
```

## 📋 Deployment Checklist

- [ ] **Prerequisites**
  - [ ] AWS CLI installed and configured
  - [ ] Schwab API credentials obtained
  - [ ] Supabase project created
  - [ ] Service role key from Supabase

- [ ] **Configuration**
  - [ ] Copy `env.template` to `.env`
  - [ ] Fill in all required environment variables
  - [ ] Choose ticker to stream (default: QQQ)

- [ ] **Database Setup**
  - [ ] Apply migration: `create_equity_and_indicators_tables.sql`
  - [ ] Apply migration: `create_option_prices_table.sql`
  - [ ] Apply migration: `streaming_optimizations.sql`
  - [ ] Verify tables exist in Supabase

- [ ] **Deployment**
  - [ ] Run `chmod +x deploy.sh`
  - [ ] Run `./deploy.sh`
  - [ ] Wait for deployment to complete (~5 min)
  - [ ] Note the instance IP address

- [ ] **Verification**
  - [ ] SSH into instance and check logs
  - [ ] Run health check: `python health_check.py`
  - [ ] Query Supabase to verify data
  - [ ] Check streaming metrics

- [ ] **Optional**
  - [ ] Set up monitoring/alerts
  - [ ] Configure data retention
  - [ ] Set up automatic backups
  - [ ] Configure firewall rules

## 🔍 Monitoring & Maintenance

### Daily Checks

```bash
# Quick health check
python health_check.py

# View recent logs
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'sudo docker-compose logs --tail=50'
```

### Weekly Checks

```sql
-- In Supabase SQL Editor

-- Check data volume
SELECT 
    COUNT(*) as total_records,
    MIN(timestamp) as oldest,
    MAX(timestamp) as newest
FROM equity_data
WHERE ticker = 'QQQ';

-- Check streaming health
SELECT * FROM get_streaming_health('QQQ');

-- Check database size
SELECT pg_size_pretty(pg_database_size('postgres'));
```

### Monthly Maintenance

```bash
# Update system packages
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'sudo yum update -y'

# Check disk usage
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'df -h'

# Verify data retention cleanup is working
# (Run cleanup function if needed)
```

## 💰 Cost Breakdown

| Service | Tier | Monthly Cost |
|---------|------|--------------|
| AWS Lightsail | Nano (512MB) | $3.50 |
| Supabase | Free | $0.00 |
| **Total** | | **$3.50** |

### Cost Optimization

**To reduce costs further:**
- Increase `BATCH_SIZE` (fewer writes to Supabase)
- Increase `BATCH_INTERVAL` (less frequent writes)
- Reduce data retention period

**To handle more load:**
- Upgrade to Lightsail Small ($5/month)
- Upgrade Supabase to Pro ($25/month for more storage)

## 🔒 Security Best Practices

1. **Environment Variables**
   - Never commit `.env` to git
   - Use service role key (not anon key)
   - Rotate keys periodically

2. **SSH Access**
   - Keep SSH key secure (`~/.ssh/LightsailDefaultKey-*.pem`)
   - Change default SSH port (optional)
   - Use firewall rules to restrict access

3. **Database**
   - Enable Row Level Security (RLS)
   - Use service role only for backend
   - Regular backups via Supabase

4. **Monitoring**
   - Set up alerts for service downtime
   - Monitor error rates
   - Track data freshness

## 📚 Additional Resources

### Internal Documentation
- [Architecture Overview](../../ARCHITECTURE.md)
- [Schwab OAuth Setup](../../docs/guides/QUICKSTART_OAUTH.md)
- [Testing Guide](../../docs/TESTING_GUIDE.md)
- [Frontend Dashboard](../../frontend/README.md)

### External Resources
- [AWS Lightsail Documentation](https://aws.amazon.com/lightsail/)
- [Supabase Documentation](https://supabase.com/docs)
- [Schwab Developer Portal](https://developer.schwab.com/)

## 🐛 Common Issues & Solutions

### Issue: Service won't start

**Solution:**
```bash
# Check logs for specific error
sudo docker-compose logs

# Verify environment variables
cat .env

# Rebuild container
sudo docker-compose down
sudo docker-compose up -d --build
```

### Issue: No data appearing in Supabase

**Checklist:**
- [ ] Verify Supabase URL and key in `.env`
- [ ] Check that migrations were applied
- [ ] Verify service is running: `sudo docker-compose ps`
- [ ] Check logs for connection errors
- [ ] Test connection: `python health_check.py`

### Issue: High error rate

**Checklist:**
- [ ] Check Schwab token expiration
- [ ] Verify market hours (if not running 24/7)
- [ ] Check Supabase quota/limits
- [ ] Review logs for specific errors

See [README.md - Troubleshooting](README.md#-troubleshooting) for more details.

## 🎓 Learning Path

**Beginner:**
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Deploy using `./deploy.sh`
3. Verify data in Supabase
4. Explore database schema

**Intermediate:**
1. Customize streaming parameters
2. Add monitoring/alerts
3. Modify streaming logic
4. Set up data retention

**Advanced:**
1. Stream multiple tickers
2. Add options streaming
3. Implement custom indicators
4. Build trading strategies

## 📞 Support & Contributing

- **Issues**: Check [README.md - Troubleshooting](README.md#-troubleshooting)
- **Questions**: Review documentation in this directory
- **Enhancements**: Modify `streaming_service.py` and redeploy

---

## Version Information

- **Created**: October 2025
- **Minimum Schema Version**: 20251021000000
- **Python Version**: 3.10+
- **Lightsail Blueprint**: Amazon Linux 2
- **Supabase Version**: Any (uses standard PostgreSQL)

---

**Last Updated**: October 21, 2025  
**Maintainer**: Alpha Kite Max Team  
**License**: See [LICENSE](../../LICENSE)

