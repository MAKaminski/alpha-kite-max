---
name: Period Selector Not Adjusting Data
about: Hour period selection not properly aggregating/displaying data
title: '[BUG] Period selector hour view not updating chart data'
labels: bug, frontend, data-visualization
assignees: ''
---

## Bug Description

When switching the period selector from "minute" to "hour", the chart data does not properly aggregate or display hourly data. The UI updates but the data visualization remains unchanged or incorrect.

## Steps to Reproduce

1. Navigate to the trading dashboard
2. Enable the `period-selector` feature flag in the admin panel
3. Observe the period dropdown appears next to the ticker input
4. Change period from "Minute" to "Hour"
5. Observe chart does not update to show hourly aggregated data

## Expected Behavior

- Chart should re-fetch or aggregate existing minute data into hourly buckets
- X-axis should show hourly intervals
- Data points should represent OHLC or volume-weighted averages for each hour
- Chart title should display "(Hour Data)"

## Actual Behavior

- Chart does not update or shows incorrect aggregation
- Data points remain at minute-level granularity
- Visual representation unchanged

## Technical Details

**Component**: `frontend/src/components/Dashboard.tsx`

**Affected Function**: `aggregateToHourly()`

**Related Code**:
```typescript
// Dashboard.tsx lines 47-102
const aggregateToHourly = (data: ChartDataPoint[]): ChartDataPoint[] => {
  // Groups data by hour and aggregates
  // Uses volume-weighted averaging for SMA9/VWAP
}
```

**Data Flow**:
1. `fetchData()` retrieves minute-level data from Supabase
2. `useEffect` with `period` dependency should trigger re-aggregation
3. `aggregateToHourly()` should process `mergedData`
4. `setAllData()` with processed data
5. Chart re-renders with hourly data

## Diagnostic Plan

### Phase 1: Verify Data Fetching
```typescript
// Add logging in fetchData()
console.log('[DEBUG] Fetching data for period:', period);
console.log('[DEBUG] Merged data length:', mergedData.length);
console.log('[DEBUG] Processed data length:', processedData.length);
```

### Phase 2: Test Aggregation Function
```typescript
// Add logging in aggregateToHourly()
console.log('[DEBUG] Input data length:', data.length);
console.log('[DEBUG] Hourly groups:', Object.keys(hourlyGroups).length);
console.log('[DEBUG] Sample aggregated data:', hourlyData.slice(0, 3));
```

### Phase 3: Verify State Updates
```typescript
// Add logging in useEffect for period changes
useEffect(() => {
  console.log('[DEBUG] Period changed to:', period);
  console.log('[DEBUG] Refetching data...');
  fetchData();
}, [ticker, period]);
```

### Phase 4: Check Chart Props
```typescript
// Verify EquityChart receives correct data
<EquityChart 
  data={displayData}  // Check if this updates
  period={period}     // Check if prop is passed
/>
```

## Potential Root Causes

1. **State Not Updating**: `period` state change not triggering `useEffect`
2. **Aggregation Logic**: `aggregateToHourly()` function has bugs
3. **Data Filtering**: `displayData` filter overriding aggregated data
4. **Chart Not Re-rendering**: EquityChart not responding to prop changes
5. **Timezone Issues**: Hour grouping using wrong timezone (UTC vs EST)

## Testing Checklist

- [ ] Add console.log debugging statements to `fetchData()`
- [ ] Test `aggregateToHourly()` with sample data in isolation
- [ ] Verify `useEffect` dependencies include `period`
- [ ] Check React DevTools for state updates
- [ ] Inspect network tab for duplicate API calls
- [ ] Test with different date ranges
- [ ] Verify hour grouping uses EST timezone
- [ ] Check if `displayData` correctly filters hourly data

## Acceptance Criteria

- [ ] Period dropdown changes from "Minute" to "Hour"
- [ ] Chart immediately shows hourly aggregated data
- [ ] X-axis labels show hourly intervals (e.g., "10:00 AM", "11:00 AM")
- [ ] Data points represent correct aggregations (VWAP, SMA9, volume)
- [ ] Chart title displays "(Hour Data)"
- [ ] Switching back to "Minute" restores minute-level data
- [ ] No console errors during period switching
- [ ] Performance remains acceptable (< 500ms update time)

## Environment

- **Frontend**: Next.js 15.5.5
- **Component**: Dashboard.tsx, EquityChart.tsx
- **Data Source**: Supabase `equity_data` and `indicators` tables
- **Browser**: All modern browsers
- **Feature Flag**: `period-selector` (currently default OFF)

## Priority

**Medium** - Feature is functional when feature flag is OFF (default state). Not blocking critical functionality.

## Labels

- `bug`
- `frontend`
- `data-visualization`
- `feature-flag-related`
- `needs-debugging`

---

**Created**: Auto-generated bug report
**Last Updated**: 2025-10-16

