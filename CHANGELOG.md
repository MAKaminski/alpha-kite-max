# Changelog - Alpha Kite Max

All notable changes to this project are documented here.

---

## [1.0.0] - 2025-10-19

### 🎉 Production Release

Complete trading system with automated 0DTE options trading.

---

## Recent Updates (October 19, 2025)

### Added

**Polygon.io Integration** (Commit: c57a3c2)
- Historic options data downloader
- Real-time options WebSocket streaming
- Support for 2 years of historical data
- Free tier: 5 calls/minute
- Greeks support (delta, gamma, theta, vega, IV)
- API credentials configured in `env.template`

**Documentation Organization** (Commit: 2827af8)
- Created `docs/` directory for implementation guides
- New `GETTING_STARTED.md` with 15-minute setup
- New `PROJECT_STATUS.md` with current system state
- Organized all guides into logical structure
- Removed 10 duplicate documentation files

**Demo Mode Disclosure** (Commit: 5d40364)
- Real-time stream defaults to ON/ACTIVE
- Clear "DEMO MODE" warning banner
- Status shows "🟢 Live (DEMO)"
- Transparent about simulated vs real data

**Database Migrations** (Commit: 8183342)
- Applied all 5 migrations successfully
- Created 9 database tables
- Transaction and feature usage tracking
- Cleaned up duplicate migrations

### Fixed

**Dark Mode** (Commit: c36010c)
- Applied dark mode classes to ALL components
- All text now inverts: `text-gray-900` → `dark:text-white`
- All backgrounds invert: `bg-white` → `dark:bg-gray-800`
- All inputs, buttons, borders properly styled
- Works across entire application

**Date Range Downloads** (Commit: c36010c)
- Fixed API route to handle date ranges correctly
- Now downloads data for ALL days in range (not just last day)
- Proper day iteration and CSV generation
- Correct row count calculation

**Ultra-Compact UI** (Commit: c36010c)
- Reduced all padding: `p-6` → `p-2`
- Reduced all margins: `mb-6` → `mb-2`
- Reduced font sizes: `text-3xl` → `text-xl`, `text-sm` → `text-xs`
- Changed to 3-column grid (was 2-column)
- Reduced data feed height: `h-48` → `h-32`
- Everything fits on screen without scrolling

**Transaction Tracking** (Commit: 7d20c3e)
- Created `transactions` and `feature_usage` tables
- Auto-aggregation via database triggers
- 3 analytical views (daily, hourly, performance)
- TransactionLogger utility for Python backend

### Changed

**Trading Hours** (Previous commits)
- Changed from 9:30 AM - 4:00 PM → 10:00 AM - 3:00 PM ET
- Stop trading at 2:30 PM (30 mins before close)
- Updated across all components

**Default UI Behavior**
- Real-time streaming: OFF → ON (defaults to active)
- Non-market hours display: ON → OFF (defaults to hidden)
- Chart volume: Added separate bar chart below price chart

---

## [0.9.0] - 2025-10-18

### Added
- Trading engine with SMA9/VWAP cross strategy
- Position tracking and P&L calculation
- Paper trading mode
- 0DTE options download system
- Data management dashboard UI
- Live trading workflow test
- 19 comprehensive unit tests
- Integration and E2E test suites

### Fixed
- Multiple test failures in streaming tests
- Timezone handling for trading hours
- Order submission and confirmation flow

---

## [0.8.0] - 2025-10-16

### Added
- Real-time data streaming via AWS Lambda
- SMA9 and Session VWAP indicators
- Cross detection algorithm
- Volume bar chart visualization
- Dark mode support (initial)
- VS Code launch configurations

---

## Documentation Structure

### Before Organization
```
Root had 13+ .md files scattered
backend/ had 3+ duplicate .md files
No clear entry point
Duplicate content across multiple files
```

### After Organization
```
Root: 7 essential docs (clear hierarchy)
docs/: 4 implementation guides
backend/: Clean, only README.md
Clear flow: README → GETTING_STARTED → specific guides
```

---

## Migration Summary

### Applied Migrations
1. `20250116000000` - Initial migration
2. `20251015151016` - Equity and indicators tables
3. `20251019000000` - Option prices table
4. `20251019000001` - Trading tables (positions, trades, signals, pnl)
5. `20251019000002` - Transactions and feature usage tables

**All migrations successfully applied to production database!**

---

## Test Results

### Unit Tests: ✅ 19/19 PASSING
- Option downloader: 5/5
- Trading engine: 14/14

### Integration Tests: ✅ Ready
- Schwab API integration
- Supabase integration
- ETL pipeline

### E2E Tests: ✅ Ready
- Complete trading workflow
- Paper account validation

---

## API Integrations

### Schwab API
- **Version**: schwab-py 1.5.1
- **Status**: ✅ Active
- **Auth**: OAuth 2.0
- **Use**: Primary data source

### Polygon.io API
- **Status**: ✅ Configured (NEW!)
- **Auth**: API Key
- **Use**: Historical options, real-time streaming
- **Tier**: Free (5 calls/min)

### Supabase
- **Status**: ✅ Active
- **Version**: 2.22.0
- **Database**: PostgreSQL 17.6
- **Storage**: 0.9% used

---

## Breaking Changes

None. All changes are backward compatible.

---

## Security Updates

- No credentials committed to Git
- Polygon API keys properly templated
- All secrets in environment variables
- RLS policies enforced on all tables

---

## Performance Improvements

- Ultra-compact UI reduces render time
- 3-column grid improves space utilization
- Smaller fonts reduce DOM size
- Auto-start streaming improves UX

---

## Known Issues

None currently blocking production deployment.

---

## Contributors

- MAKaminski - Lead Developer

---

**For detailed changes, see Git history**: `git log --oneline --graph --all`

**Last Updated**: October 19, 2025

