#!/bin/bash
# One-Command Schwab OAuth Re-Authorization
# Usage: ./reauth_schwab.sh

echo "🤖 Schwab OAuth Re-Authorization"
echo "   Fully automated - no manual copying required!"
echo ""

cd backend/sys_testing
python3 auto_reauth.py
