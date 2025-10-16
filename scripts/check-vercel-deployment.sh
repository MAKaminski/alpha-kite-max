#!/bin/bash

# Vercel Deployment Checker
# This script checks the latest Vercel deployment status after a git push

set -e

VERCEL_PROJECT="alpha-kite-max"
VERCEL_TEAM="makaminski1337"  # Your Vercel team/username

echo "🚀 Checking Vercel deployment status..."
echo ""

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Get latest deployment
echo "📡 Fetching latest deployment..."
DEPLOYMENT_INFO=$(vercel ls --team $VERCEL_TEAM $VERCEL_PROJECT -t 1 2>&1 || echo "error")

if [[ "$DEPLOYMENT_INFO" == *"error"* ]] || [[ -z "$DEPLOYMENT_INFO" ]]; then
    echo "⚠️  Could not fetch deployment info. You may need to login:"
    echo "   Run: vercel login"
    exit 1
fi

echo "$DEPLOYMENT_INFO"
echo ""

# Wait for build to complete (check every 10 seconds for up to 5 minutes)
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Get deployment status
    STATUS_OUTPUT=$(vercel ls --team $VERCEL_TEAM $VERCEL_PROJECT -t 1 2>&1 || echo "")
    
    if [[ "$STATUS_OUTPUT" == *"Ready"* ]]; then
        echo "✅ Deployment successful!"
        echo ""
        echo "🌐 Your site is live at:"
        echo "   https://alpha-kite-max-git-main-makaminski1337.vercel.app"
        exit 0
    elif [[ "$STATUS_OUTPUT" == *"Error"* ]] || [[ "$STATUS_OUTPUT" == *"Failed"* ]]; then
        echo "❌ Deployment failed!"
        echo ""
        echo "📋 Fetching build logs..."
        echo ""
        
        # Try to get logs
        vercel logs --team $VERCEL_TEAM $VERCEL_PROJECT || echo "Could not fetch logs"
        
        echo ""
        echo "🔗 Check details at: https://vercel.com/$VERCEL_TEAM/$VERCEL_PROJECT"
        exit 1
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "⏳ Build in progress... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    sleep 10
done

echo "⏱️  Timeout waiting for deployment. Check manually:"
echo "   https://vercel.com/$VERCEL_TEAM/$VERCEL_PROJECT"
exit 1

