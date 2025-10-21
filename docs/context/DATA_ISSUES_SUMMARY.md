# Data Issues Summary - 2025-10-16

## Diagnostic Results

Ran `backend/check_data_status.py` on 2025-10-16 at 2:15 PM EST

### Findings

#### ❌ Issue #1: No Data for 10/15/2025
- **Date**: 2025-10-15 (Tuesday - Weekday)
- **Status**: **NO DATA** in Supabase
- **Expected**: Minute-level data during market hours (9:30 AM - 4:00 PM EST)
- **Actual**: Zero rows in `equity_data` table

#### ❌ Issue #2: No Real-Time Data for 10/16/2025  
- **Date**: 2025-10-16 (Wednesday - TODAY)
- **Status**: **NO DATA** in Supabase
- **Expected**: Real-time data streaming via Lambda (every minute during market hours)
- **Actual**: Zero rows in `equity_data` table

#### ✅ Historical Data Exists
- **Date**: 2025-10-09 (Last data available)
- **Data Points**: 1,000 rows
- **Time Range**: 00:00:00 to 18:07:00
- **Average Price**: $610.97
- **Total Volume**: 21,982,410
- **Indicators**: 1,000 rows (SMA9, VWAP)

### Data Gap Analysis

**Missing Days** (all weekdays):
- 2025-10-10 (Thursday) - ❌ NO DATA
- 2025-10-13 (Monday) - ❌ NO DATA  
- 2025-10-14 (Tuesday) - ❌ NO DATA
- 2025-10-15 (Wednesday) - ❌ NO DATA
- 2025-10-16 (Thursday - TODAY) - ❌ NO DATA

**Last Successful Data**: 2025-10-09 (7 days ago)

## Root Cause Analysis

### Potential Causes

1. **Lambda Function Not Running**
   - EventBridge rule might be disabled
   - Lambda function may have errors
   - Execution role permissions issue

2. **Schwab API Token Expired**
   - Token in Secrets Manager is invalid
   - Token refresh logic failing
   - Authentication errors preventing data fetch

3. **Lambda Not Deployed**
   - Latest code not deployed to AWS
   - Deployment package missing dependencies
   - Function configuration incorrect

4. **EventBridge Schedule Disabled**
   - Cron schedule not triggering
   - Rule in disabled state
   - Target Lambda not configured

5. **Supabase Connection Issues**
   - Service role key invalid
   - Network connectivity problems
   - Table permissions incorrect

## Diagnostic Steps

### 1. Check Lambda Function Status

```bash
# Via AWS CLI
aws lambda get-function --function-name alpha-kite-real-time-streamer

# Check recent invocations
aws logs tail /aws/lambda/alpha-kite-real-time-streamer --since 1h --follow
```

### 2. Check EventBridge Rule

```bash
# Check if rule is enabled
aws events describe-rule --name alpha-kite-minute-trigger

# List targets
aws events list-targets-for-rule --rule alpha-kite-minute-trigger
```

### 3. Test Lambda Manually

```bash
# Invoke Lambda function
aws lambda invoke \
  --function-name alpha-kite-real-time-streamer \
  --payload '{"source":"manual-test"}' \
  response.json

# Check output
cat response.json
```

### 4. Check Schwab Token

```bash
# Get token from Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id schwab-api-token \
  --query SecretString \
  --output text
```

### 5. Check Supabase Tables

```sql
-- Check if tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('equity_data', 'indicators');

-- Check row counts
SELECT COUNT(*) FROM equity_data;
SELECT COUNT(*) FROM indicators;
```

## Action Items

### Immediate (Priority 1)

- [ ] **Check Lambda CloudWatch Logs** for errors in last 7 days
- [ ] **Verify EventBridge Rule** is enabled and triggering
- [ ] **Check Schwab Token** expiration in Secrets Manager
- [ ] **Test Lambda Invocation** manually to verify it works
- [ ] **Review Lambda IAM Role** permissions

### Short-term (Priority 2)

- [ ] **Redeploy Lambda** with latest code if needed
- [ ] **Refresh Schwab Token** if expired
- [ ] **Enable CloudWatch Alarms** for Lambda failures
- [ ] **Add SNS Notifications** for Lambda errors
- [ ] **Backfill Missing Data** for 10/10 - 10/16

### Long-term (Priority 3)

- [ ] **Implement Token Auto-Refresh** in Lambda
- [ ] **Add Health Check Endpoint** to monitor data freshness
- [ ] **Create Dashboard Alert** for missing data
- [ ] **Set up Dead Letter Queue** for failed Lambda invocations
- [ ] **Add Monitoring Dashboard** for data pipeline

## Testing Commands

### Run Data Status Check
```bash
cd backend
python check_data_status.py
```

### Test Schwab Connection
```bash
cd backend
python main.py --test-connections
```

### Download Data Manually
```bash
cd backend
python main.py --ticker QQQ --days 1
```

## Expected Behavior

**Lambda Function** should:
1. ✅ Run every minute during market hours (9:30 AM - 4:00 PM EST)
2. ✅ Fetch latest QQQ data from Schwab API
3. ✅ Calculate SMA9 and VWAP indicators
4. ✅ Upsert data to Supabase `equity_data` and `indicators` tables
5. ✅ Log success/failure to CloudWatch

**Data Flow**:
```
EventBridge (every minute)
  → Lambda Function
    → Schwab API (price data)
      → Calculate Indicators
        → Supabase (store data)
          → Frontend (display)
```

## Resolution Timeline

**Target**: Restore real-time data within 2 hours
- Hour 1: Diagnose Lambda/EventBridge/Token issues
- Hour 2: Fix issues and verify data streaming
- Post-fix: Backfill missing data for 10/10 - 10/16

## Success Criteria

- [ ] Real-time data flowing for current day (10/16)
- [ ] Lambda logs show successful executions
- [ ] Supabase contains data for 10/16
- [ ] Frontend displays current day data
- [ ] No errors in CloudWatch logs
- [ ] EventBridge triggering every minute

---

**Status**: 🔴 **CRITICAL** - No data for 7 days
**Owner**: DevOps / Backend Team
**Created**: 2025-10-16 14:15 EST
**Last Updated**: 2025-10-16 14:15 EST

