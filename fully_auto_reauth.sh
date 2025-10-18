#!/bin/bash
# Fully Automated Schwab OAuth Re-Authorization
# Usage: ./fully_auto_reauth.sh

echo "🤖 Fully Automated Schwab OAuth Re-Authorization"
echo "   NO manual login, clicking, or interaction required!"
echo ""

cd backend/sys_testing
python3 fully_automated_oauth.py
