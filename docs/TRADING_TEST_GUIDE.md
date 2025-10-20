# Trading Test Guide

## Overview
This guide outlines the comprehensive testing strategy for autonomous trading on the paper account.

## Test Categories

### 1. Data Quality Tests
- **Real-time Data Validation**
  - Verify Schwab API data accuracy
  - Check data timestamps are within market hours
  - Validate price and volume data ranges
  - Test data feed continuity

- **Options Data Validation**
  - Verify option chain completeness
  - Check strike price accuracy
  - Validate Greeks calculations
  - Test expiration date handling

### 2. Trading Strategy Tests
- **SMA9/VWAP Cross Detection**
  - Test cross detection accuracy
  - Verify signal timing
  - Test false positive filtering
  - Validate cross strength calculation

- **Position Management**
  - Test position opening logic
  - Verify position sizing
  - Test stop-loss implementation
  - Validate profit-taking logic

### 3. Risk Management Tests
- **Position Limits**
  - Test maximum position size
  - Verify daily loss limits
  - Test exposure limits
  - Validate margin requirements

- **Order Management**
  - Test order placement accuracy
  - Verify order cancellation
  - Test partial fills
  - Validate order status tracking

### 4. Paper Trading Tests
- **Account Simulation**
  - Test paper account balance tracking
  - Verify P&L calculations
  - Test margin calculations
  - Validate position tracking

- **Order Execution Simulation**
  - Test market order simulation
  - Verify limit order simulation
  - Test stop order simulation
  - Validate order matching logic

## Test Execution

### Automated Tests
```bash
# Run all trading tests
npm run test:trading

# Run specific test categories
npm run test:data-quality
npm run test:strategy
npm run test:risk-management
npm run test:paper-trading
```

### Manual Tests
1. **Start Mock Streaming**
   - Enable mock data streaming
   - Verify data feed continuity
   - Test UI responsiveness

2. **Start Real Streaming**
   - Enable real Schwab data streaming
   - Verify data accuracy
   - Test error handling

3. **Trading Simulation**
   - Enable paper trading mode
   - Monitor position management
   - Verify order execution

## Test Data Requirements

### Historical Data
- 30 days of minute-level QQQ data
- Corresponding options data
- Market hours validation
- Holiday handling

### Real-time Data
- Live Schwab API connection
- Options chain updates
- Price and volume feeds
- Error handling

## Success Criteria

### Data Quality
- ✅ 99.9% data accuracy
- ✅ <1 second latency
- ✅ 99.5% uptime
- ✅ Zero data gaps

### Trading Strategy
- ✅ 95% cross detection accuracy
- ✅ <100ms signal processing
- ✅ Zero false positives
- ✅ Consistent position sizing

### Risk Management
- ✅ Zero position limit violations
- ✅ Accurate P&L tracking
- ✅ Proper margin calculations
- ✅ Complete audit trail

### Paper Trading
- ✅ 100% order simulation accuracy
- ✅ Real-time balance updates
- ✅ Complete transaction history
- ✅ Accurate performance metrics

## Monitoring and Alerts

### Real-time Monitoring
- Data feed health
- Trading signal accuracy
- Position risk metrics
- System performance

### Alert Conditions
- Data feed interruption
- Trading signal anomalies
- Risk limit breaches
- System errors

## Test Environment Setup

### Prerequisites
- Schwab API credentials
- Paper trading account
- Test data sets
- Monitoring tools

### Configuration
```env
# Trading Test Configuration
TRADING_MODE=paper
RISK_LIMITS_ENABLED=true
MAX_POSITION_SIZE=1000
DAILY_LOSS_LIMIT=500
AUTO_TRADING_ENABLED=false
```

## Test Execution Timeline

### Phase 1: Data Validation (Day 1)
- [ ] Mock data streaming tests
- [ ] Real data streaming tests
- [ ] Data quality validation
- [ ] Error handling tests

### Phase 2: Strategy Testing (Day 2)
- [ ] Cross detection tests
- [ ] Signal accuracy tests
- [ ] Position management tests
- [ ] Risk management tests

### Phase 3: Paper Trading (Day 3)
- [ ] Account simulation tests
- [ ] Order execution tests
- [ ] P&L tracking tests
- [ ] Performance validation

### Phase 4: Live Trading (Day 4+)
- [ ] Real account integration
- [ ] Live order execution
- [ ] Performance monitoring
- [ ] Risk management validation

## Troubleshooting

### Common Issues
1. **Data Feed Interruption**
   - Check API credentials
   - Verify network connectivity
   - Review error logs

2. **Trading Signal Errors**
   - Validate data quality
   - Check calculation logic
   - Review timing issues

3. **Order Execution Failures**
   - Verify account status
   - Check order parameters
   - Review market conditions

### Support Contacts
- Technical Issues: [Your contact]
- Trading Questions: [Your contact]
- Account Issues: Schwab Support

## Documentation Updates
- Update test results daily
- Document any issues found
- Track performance metrics
- Maintain test logs
