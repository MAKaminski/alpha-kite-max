# 🔐 Environment Variables Guide

## 📋 Overview

Alpha Kite Max uses **TWO separate `.env` files** - one for backend, one for frontend. This separation is intentional and follows best practices.

---

## 🗂️ Environment File Structure

```
alpha-kite-max/
├── backend/
│   ├── .env                    ← Backend environment variables (YOU CREATE THIS)
│   └── env.template            ← Template for backend .env
├── frontend/
│   └── .env.local              ← Frontend environment variables (YOU CREATE THIS)
├── env.example                 ← Template for frontend .env.local
└── context/
    └── .env                    ← IGNORE THIS (context docs only, not used)
```

---

## 🎯 Which Files to Use

### ✅ **Active Environment Files (YOU NEED THESE)**

| File | Purpose | Create From | Required For |
|------|---------|-------------|--------------|
| `backend/.env` | Backend Python app credentials | `backend/env.template` | Data download, trading, API calls |
| `frontend/.env.local` | Frontend Next.js app credentials | `env.example` | Dashboard display, chart rendering |

### ❌ **Files to Ignore**

| File | Status | Action |
|------|--------|--------|
| `context/.env` | Not used by code | Ignore - just context docs |

---

## 🚀 Setup Instructions

### 1️⃣ **Backend Setup** (Required for all backend operations)

```bash
# Copy template
cd backend
cp env.template .env

# Edit .env and fill in:
nano .env  # or use your favorite editor
```

**Required Variables:**
```bash
# Schwab API (REQUIRED)
SCHWAB_CLIENT_ID=your_actual_client_id
SCHWAB_CLIENT_SECRET=your_actual_client_secret
SCHWAB_API_USERNAME=your_schwab_username
SCHWAB_API_ACCOUNT_PASS=your_schwab_password

# Supabase (REQUIRED)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_actual_service_role_key

# Polygon.io (OPTIONAL - for stock data only)
POLYGON_API=your_polygon_api_key
POLYGON_ACCESS_KEY_ID=your_polygon_access_key
POLYGON_SECRET_ACCESS_KEY=your_polygon_secret_key
POLYGON_S3_ENDPOINT=https://files.polygon.io
POLYGON_BUCKET=flatfiles

# Application Config (OPTIONAL - defaults provided)
LOG_LEVEL=INFO
DEFAULT_TICKER=QQQ
LOOKBACK_DAYS=5
```

### 2️⃣ **Frontend Setup** (Required for dashboard)

```bash
# Copy template
cp env.example frontend/.env.local

# Edit .env.local and fill in:
nano frontend/.env.local  # or use your favorite editor
```

**Required Variables:**
```bash
# Supabase (REQUIRED)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_actual_anon_key
```

**Note:** Vercel auto-populates deployment variables. Don't manually set `VERCEL_URL`, `VERCEL_ENV`, etc.

---

## 🔒 Security Best Practices

### ✅ DO
- ✅ Keep `.env` files in `.gitignore` (already done)
- ✅ Use different keys for frontend (anon) vs backend (service role)
- ✅ Store real credentials only in actual `.env` files
- ✅ Use templates (env.template, env.example) for documentation

### ❌ DON'T
- ❌ Commit `.env` files to git
- ❌ Share service role keys publicly
- ❌ Use production credentials in development
- ❌ Copy real credentials into templates

---

## 🎯 Why Two Separate Files?

### **Backend (.env)**
- **Location**: `backend/.env`
- **Purpose**: Server-side operations
- **Access Level**: Full admin access (service role key)
- **Used By**: Python scripts, data downloaders, trading bots
- **Contains**: Sensitive credentials for APIs

### **Frontend (.env.local)**
- **Location**: `frontend/.env.local`
- **Purpose**: Client-side operations
- **Access Level**: Public access (anon key with RLS)
- **Used By**: Next.js app, browser-side code
- **Contains**: Only public-safe credentials

### **Why Not One Global File?**
1. **Security**: Frontend credentials are exposed to browsers, backend ones are not
2. **Separation**: Different deployment targets (Vercel vs local/AWS)
3. **Best Practice**: Next.js convention uses `.env.local` for frontend
4. **Clarity**: Clear separation of concerns

---

## 🔍 Variable Reference

### **Backend Variables**

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `SCHWAB_CLIENT_ID` | ✅ Yes | Schwab OAuth client ID | `abc123...` |
| `SCHWAB_CLIENT_SECRET` | ✅ Yes | Schwab OAuth secret | `xyz789...` |
| `SCHWAB_API_USERNAME` | ✅ Yes | Schwab account username | `myusername` |
| `SCHWAB_API_ACCOUNT_PASS` | ✅ Yes | Schwab account password | `mypassword` |
| `SUPABASE_URL` | ✅ Yes | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ Yes | Supabase admin key | `eyJ...` |
| `POLYGON_API` | ⚠️ Optional | Polygon API key | `abc123...` |
| `LOG_LEVEL` | ⚠️ Optional | Logging level | `INFO` |
| `DEFAULT_TICKER` | ⚠️ Optional | Default stock ticker | `QQQ` |

### **Frontend Variables**

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ Yes | Supabase project URL | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ Yes | Supabase public key | `eyJ...` |

---

## 🐛 Troubleshooting

### "Cannot find module 'dotenv'"
```bash
cd backend
uv pip install python-dotenv
```

### "SUPABASE_URL is not defined"
- Check you created the `.env` file in the correct location
- Verify variable names match exactly (case-sensitive)
- Ensure no spaces around `=` sign

### "Permission denied" errors
- Backend: Check you're using `SUPABASE_SERVICE_ROLE_KEY`
- Frontend: Check you're using `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### "Environment variables not loading"
- Backend: Ensure `.env` is in `backend/` directory
- Frontend: Ensure `.env.local` is in `frontend/` directory
- Restart development servers after changing .env files

---

## ✅ Verification

### Check Backend Config
```bash
cd backend
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ SCHWAB_CLIENT_ID:', 'SET' if os.getenv('SCHWAB_CLIENT_ID') else '❌ NOT SET')"
```

### Check Frontend Config
```bash
cd frontend
npm run dev
# Visit http://localhost:3000
# Open browser console, check for Supabase initialization messages
```

---

## 📝 Summary

| File | Location | Purpose | Create From |
|------|----------|---------|-------------|
| ✅ `backend/.env` | `backend/.env` | Backend credentials | `backend/env.template` |
| ✅ `frontend/.env.local` | `frontend/.env.local` | Frontend credentials | `env.example` |
| ❌ `context/.env` | `context/.env` | Not used | N/A - ignore |

**Remember**: 
- Backend = `backend/.env` (service role key)
- Frontend = `frontend/.env.local` (anon key)
- Two files = Better security + proper separation

---

*Last Updated: October 19, 2025*

