# Vercel Deployment Guide

## Automated Deployment Checking

This project includes several tools to help ensure successful Vercel deployments and catch errors before they reach production.

## 1. GitHub Actions Integration

**File**: `.github/workflows/check-vercel-deployment.yml`

This workflow automatically:
- ✅ Monitors Vercel deployments after each push to `main`
- ✅ Waits for deployment to complete (up to 5 minutes)
- ✅ Reports success/failure in GitHub Actions
- ✅ Provides deployment URL when successful

### View Deployment Status

After pushing to GitHub:
1. Go to your repository on GitHub
2. Click **Actions** tab
3. See the latest "Check Vercel Deployment" workflow
4. Green checkmark = successful deployment
5. Red X = deployment failed

## 2. Pre-Push Lint Check (Recommended)

**File**: `scripts/pre-push-lint-check.sh`

Prevents pushing code with linting errors that would fail in Vercel.

### Setup Git Hook

```bash
# Install the pre-push hook
ln -sf ../../scripts/pre-push-lint-check.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Now every `git push` will:
1. Run `npm run lint` in the frontend
2. Block the push if linting fails
3. Show you the errors to fix

### Bypass Hook (Emergency Only)

```bash
git push --no-verify
```

⚠️ **Warning**: Only use this if you're certain the linting errors are false positives.

## 3. Manual Deployment Check

**File**: `scripts/check-vercel-deployment.sh`

Check deployment status from the command line.

### Setup

```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Login to Vercel
vercel login

# Check deployment status
./scripts/check-vercel-deployment.sh
```

### What It Does

- Fetches latest deployment info
- Monitors build progress
- Shows build logs if deployment fails
- Provides live deployment URL

## 4. Local Build Test

Before pushing, test the build locally:

```bash
cd frontend
npm run build
```

This runs the same build process that Vercel uses.

## Common Linting Errors

### Missing Imports

**Error**: `Cannot find name 'useEffect'`

**Fix**:
```typescript
import { useState, useEffect } from 'react';
```

### Unused Variables

**Error**: `'variableName' is defined but never used`

**Fix**: Remove the unused variable or use it

### TypeScript `any` Type

**Error**: `Unexpected any. Specify a different type`

**Fix**:
```typescript
// Bad
onClick={() => setTab(tab.id as any)}

// Good
onClick={() => setTab(tab.id as 'status' | 'pipeline')}
```

### Unescaped Entities

**Error**: `' can be escaped with &apos;`

**Fix**:
```typescript
// Bad
<span>Today's Data</span>

// Good
<span>Today&apos;s Data</span>
```

## Vercel Dashboard

### Access Deployment Logs

1. Go to https://vercel.com/makaminski1337/alpha-kite-max
2. Click on the latest deployment
3. View **Build Logs** tab
4. See detailed error messages

### Deployment Settings

**Root Directory**: `frontend/`
**Build Command**: `npm run build`
**Output Directory**: `.next`
**Install Command**: `npm install`

### Environment Variables

Set in Vercel Dashboard → Settings → Environment Variables:

```
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Troubleshooting

### Build Fails with Linting Errors

**Solution**:
1. Run `cd frontend && npm run lint` locally
2. Fix all errors
3. Test with `npm run build`
4. Commit and push

### Build Succeeds Locally but Fails on Vercel

**Check**:
- Environment variables are set in Vercel
- Dependencies in `package.json` are up to date
- No references to local files outside `frontend/`
- All imports use relative paths or aliases

### Deployment Timeout

**Solution**:
1. Check Vercel dashboard for errors
2. Large builds may need optimization
3. Consider reducing dependencies

### TypeScript Errors in Production

**Solution**:
1. Set `"strict": true` in `tsconfig.json` locally
2. Fix all type errors
3. Test build: `npm run build`

## Best Practices

### Before Committing

1. ✅ Run `npm run lint` in `frontend/`
2. ✅ Run `npm run build` to test build
3. ✅ Fix all errors before committing

### After Pushing

1. ✅ Check GitHub Actions for deployment status
2. ✅ Visit live site to verify changes
3. ✅ Monitor Vercel dashboard for errors

### Continuous Integration

The GitHub Actions workflow ensures:
- Every push is validated
- Deployment status is tracked
- Failures are caught immediately
- Team is notified of issues

## Quick Reference

```bash
# Check local linting
cd frontend && npm run lint

# Test local build
cd frontend && npm run build

# Setup pre-push hook
ln -sf ../../scripts/pre-push-lint-check.sh .git/hooks/pre-push

# Check Vercel deployment
./scripts/check-vercel-deployment.sh

# View deployment logs
vercel logs
```

## Future Enhancements

Potential MCP integration options:
1. **Vercel MCP Server** (when available)
   - Direct API access to deployments
   - Real-time build logs
   - Automated error detection

2. **Custom GitHub Actions Reporter**
   - Slack/Discord notifications
   - Detailed error reports
   - Performance metrics

3. **Pre-commit Hooks**
   - Auto-format code
   - Run type checking
   - Prevent bad commits

---

**Your deployments should now be smooth and error-free!** 🚀

