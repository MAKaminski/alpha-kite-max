# System Testing & Ad-hoc Scripts

This folder contains utility scripts for debugging, testing, and maintenance tasks.

## 🔧 OAuth & Authentication Scripts

### `auto_reauth.py`
- **Purpose**: Automated Schwab OAuth re-authentication
- **Usage**: `python auto_reauth.py`
- **Note**: Handles the complete OAuth flow automatically

### `reauth_schwab.py`
- **Purpose**: Manual Schwab re-authentication flow
- **Usage**: `python reauth_schwab.py`
- **Note**: Interactive re-authentication with manual steps

### `reauth_schwab_auto.py`
- **Purpose**: Semi-automated Schwab re-authentication
- **Usage**: `python reauth_schwab_auto.py`
- **Note**: Hybrid approach with some automation

### `refresh_schwab_auth.py`
- **Purpose**: Refresh existing Schwab tokens
- **Usage**: `python refresh_schwab_auth.py`
- **Note**: Uses existing refresh tokens

### `get_auth_url.py`
- **Purpose**: Generate Schwab OAuth authorization URL
- **Usage**: `python get_auth_url.py`
- **Note**: Outputs URL for manual authorization

### `process_callback.py`
- **Purpose**: Process OAuth callback and save tokens
- **Usage**: `python process_callback.py <callback_url>`
- **Note**: Handles the callback from OAuth flow

## 🔍 Diagnostic Scripts

### `token_diagnostics.py`
- **Purpose**: Analyze Schwab token status and validity
- **Usage**: `python token_diagnostics.py`
- **Note**: Comprehensive token health check

### `check_data_status.py`
- **Purpose**: Check data availability and gaps in Supabase
- **Usage**: `python check_data_status.py`
- **Note**: Data integrity verification

### `download_missing_data.py`
- **Purpose**: Backfill missing historical data
- **Usage**: `python download_missing_data.py`
- **Note**: Downloads gaps in historical data

### `fortified_token_manager.py`
- **Purpose**: Advanced token management with rate limiting
- **Usage**: `python fortified_token_manager.py`
- **Note**: Production-ready token handling

## 🚀 Quick Reference

**For OAuth Issues:**
1. Run `token_diagnostics.py` to check token status
2. If expired, use `auto_reauth.py` for automatic flow
3. If that fails, use `get_auth_url.py` + `process_callback.py`

**For Data Issues:**
1. Run `check_data_status.py` to identify gaps
2. Use `download_missing_data.py` to backfill

**For Token Management:**
1. Use `fortified_token_manager.py` for production token handling
2. Includes rate limiting and error handling
