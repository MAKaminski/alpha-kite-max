# AWS Lightsail Streaming Service

Minimal deployment for perpetually streaming Equity and Options data to Supabase.

## 📊 What It Does

This service:
- ✅ Streams real-time equity prices (QQQ or any ticker)
- ✅ Calculates indicators (SMA9, VWAP) in real-time
- ✅ Batches data efficiently before writing to Supabase
- ✅ Runs perpetually with automatic restarts
- ✅ Costs ~$3.50/month on AWS Lightsail nano instance

## 🗄️ Database Schema

The service writes to these Supabase tables:

### equity_data
```sql
CREATE TABLE public.equity_data (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, timestamp)
);
```

### indicators
```sql
CREATE TABLE public.indicators (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    sma9 DECIMAL(10, 2),
    vwap DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, timestamp)
);
```

### option_prices (for options data)
```sql
CREATE TABLE public.option_prices (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('CALL', 'PUT')),
    strike_price DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    last_price DECIMAL(10, 4),
    bid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    volume BIGINT,
    open_interest BIGINT,
    implied_volatility DECIMAL(10, 4),
    delta DECIMAL(10, 4),
    gamma DECIMAL(10, 4),
    theta DECIMAL(10, 4),
    vega DECIMAL(10, 4),
    option_symbol VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, timestamp, option_type, strike_price, expiration_date)
);
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd infrastructure/lightsail
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```bash
STREAM_TICKER=QQQ              # Ticker to stream
BATCH_SIZE=10                   # Number of records per batch
BATCH_INTERVAL=60               # Flush interval in seconds

SCHWAB_APP_KEY=xxx
SCHWAB_APP_SECRET=xxx
SCHWAB_REDIRECT_URI=https://localhost:8080

SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx
```

### 2. Apply Supabase Schema

Run the migrations in your Supabase project:

```bash
# From the project root
cd supabase/migrations

# Apply in Supabase SQL Editor or using CLI
supabase db push
```

Or manually in Supabase Dashboard → SQL Editor:

```sql
-- Run each migration file in order:
-- 20251015151016_create_equity_and_indicators_tables.sql
-- 20251019000000_create_option_prices_table.sql
```

### 3. Deploy to Lightsail

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Create a Lightsail instance ($3.50/month)
2. Install Docker and dependencies
3. Deploy the streaming service
4. Start streaming data

### 4. Monitor Service

```bash
# View logs
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP> \
  'cd /opt/streaming-service && sudo docker-compose logs -f'

# Check service status
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP> \
  'cd /opt/streaming-service && sudo docker-compose ps'

# Restart service
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP> \
  'cd /opt/streaming-service && sudo docker-compose restart'
```

## 🏗️ Architecture

```
┌─────────────────────┐
│  Schwab WebSocket   │
│   (Real-time data)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Streaming Service  │
│  - Receives ticks   │
│  - Calculates SMA9  │
│  - Calculates VWAP  │
│  - Batches data     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     Supabase DB     │
│  - equity_data      │
│  - indicators       │
│  - option_prices    │
└─────────────────────┘
```

## 📝 Schema Details

### Indexes

The schema includes optimized indexes for:
- Fast time-series queries: `(ticker, timestamp DESC)`
- Efficient lookups by ticker
- Unique constraints to prevent duplicates

### Row Level Security (RLS)

- **Service role**: Full access (for streaming service)
- **Anonymous**: Read-only access (for dashboard/frontend)
- **Authenticated users**: Read-only access

### Data Retention

By default, data is retained indefinitely. To add automatic cleanup:

```sql
-- Example: Delete equity data older than 90 days
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'cleanup-old-equity-data',
  '0 2 * * *',  -- Run at 2 AM daily
  $$DELETE FROM equity_data WHERE created_at < NOW() - INTERVAL '90 days'$$
);
```

## 🔧 Configuration

### Batch Settings

- `BATCH_SIZE`: Number of records to accumulate before writing (default: 10)
- `BATCH_INTERVAL`: Maximum seconds between writes (default: 60)

Tuning recommendations:
- **High frequency**: Lower batch size (5-10), shorter interval (30-60s)
- **Cost optimization**: Higher batch size (50-100), longer interval (120-300s)
- **Low latency**: BATCH_SIZE=1, BATCH_INTERVAL=10

### Market Hours

The service includes market hours checking (9:30 AM - 4:00 PM ET, weekdays).

To stream 24/7 (for testing or after-hours data):
```bash
SKIP_MARKET_HOURS=true
```

## 💰 Cost Estimate

**AWS Lightsail**: $3.50/month (nano instance)
- 512 MB RAM
- 1 vCPU
- 20 GB SSD
- 1 TB transfer

**Supabase**: Free tier includes:
- 500 MB database
- Unlimited API requests
- 2 GB file storage

**Total**: ~$3.50/month

## 🔒 Security

1. **SSH Access**: Uses AWS Lightsail default key pair
2. **Environment Variables**: Stored in `.env` file (never committed)
3. **Supabase**: Uses service role key (full access, kept secure)
4. **Network**: Lightsail instance has minimal open ports

### Hardening (Recommended)

```bash
# SSH into instance
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<INSTANCE_IP>

# Update system
sudo yum update -y

# Configure firewall (only allow SSH)
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload

# Enable automatic security updates
sudo yum install -y yum-cron
sudo systemctl enable yum-cron
sudo systemctl start yum-cron
```

## 🐛 Troubleshooting

### Service not starting

```bash
# Check logs
sudo docker-compose logs

# Check container status
sudo docker-compose ps

# Rebuild and restart
sudo docker-compose down
sudo docker-compose up -d --build
```

### No data in Supabase

1. Check service logs for errors
2. Verify Supabase credentials in `.env`
3. Test Supabase connection:
   ```bash
   docker-compose exec streaming-service python -c "
   from supabase_client import SupabaseClient
   client = SupabaseClient()
   print('Connection:', client.test_connection())
   "
   ```

### Schwab authentication issues

The service requires Schwab tokens. See [QUICKSTART_OAUTH.md](../../docs/guides/QUICKSTART_OAUTH.md) for authentication setup.

## 📚 Related Documentation

- [Supabase Migrations](../../supabase/migrations/)
- [Schwab Integration](../../backend/schwab_integration/)
- [Architecture Overview](../../ARCHITECTURE.md)

## 🔄 Updating the Service

```bash
# Make changes to code
# Then redeploy
./deploy.sh

# Or manually:
cd infrastructure/lightsail
tar -czf /tmp/update.tar.gz streaming_service.py requirements.txt
scp -i ~/.ssh/LightsailDefaultKey-us-east-1.pem /tmp/update.tar.gz ec2-user@<IP>:/tmp/
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP>
cd /opt/streaming-service
sudo tar -xzf /tmp/update.tar.gz
sudo docker-compose up -d --build
```

## 🛑 Stopping/Removing

```bash
# Stop service (keeps instance)
ssh -i ~/.ssh/LightsailDefaultKey-us-east-1.pem ec2-user@<IP> \
  'cd /opt/streaming-service && sudo docker-compose down'

# Delete Lightsail instance (stops billing)
aws lightsail delete-instance \
  --instance-name equity-options-streamer \
  --region us-east-1
```

