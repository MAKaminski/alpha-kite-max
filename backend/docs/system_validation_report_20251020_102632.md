# System Validation Test Report
Generated: 2025-10-20T10:26:32.510854

## Summary
- **Total Tests**: 7
- **Passed**: 6
- **Failed**: 1
- **Success Rate**: 85.7%

## Test Results

### Data Model Validation
- **Status**: ✅ PASS
- **Duration**: 0.00s
- **Timestamp**: 2025-10-20T10:26:32.085200
- **Details**:
  - has_required_fields: True
  - price_valid: True
  - volume_valid: True

### Trading Calculations
- **Status**: ✅ PASS
- **Duration**: 0.00s
- **Timestamp**: 2025-10-20T10:26:32.085279
- **Details**:
  - pnl_calculation: True
  - position_sizing: True
  - commission_calculation: True

### SMA9/VWAP Cross Detection
- **Status**: ✅ PASS
- **Duration**: 0.43s
- **Timestamp**: 2025-10-20T10:26:32.510367
- **Details**:
  - cross_detection: True
  - has_both_types: True
  - data_processing: True
  - total_crosses: 2

### Risk Management Logic
- **Status**: ❌ FAIL
- **Duration**: 0.00s
- **Timestamp**: 2025-10-20T10:26:32.510551
- **Details**:
  - position_limits: True
  - daily_loss_limits: True
  - stop_loss: False
  - margin_requirements: True

### Paper Trading Simulation
- **Status**: ✅ PASS
- **Duration**: 0.00s
- **Timestamp**: 2025-10-20T10:26:32.510616
- **Details**:
  - balance_tracking: True
  - position_tracking: True
  - pnl_calculation: True

### API Endpoint Validation
- **Status**: ✅ PASS
- **Duration**: 0.00s
- **Timestamp**: 2025-10-20T10:26:32.510670
- **Details**:
  - valid_endpoints: True
  - request_structure: True
  - total_endpoints: 5

### System Configuration
- **Status**: ✅ PASS
- **Duration**: 0.00s
- **Timestamp**: 2025-10-20T10:26:32.510723
- **Details**:
  - config_structure: True
  - position_size_valid: True
  - loss_limit_valid: True
  - risk_valid: True
