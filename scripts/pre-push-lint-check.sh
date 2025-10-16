#!/bin/bash

# Pre-push hook to check for linting errors before pushing
# This helps catch issues before they fail in Vercel

echo "🔍 Running frontend lint check before push..."

cd frontend

# Run Next.js lint
if npm run lint; then
    echo "✅ Lint check passed!"
    exit 0
else
    echo "❌ Lint check failed!"
    echo ""
    echo "Please fix the linting errors before pushing."
    echo "Run 'cd frontend && npm run lint' to see the errors."
    echo ""
    echo "To bypass this check (not recommended), use:"
    echo "  git push --no-verify"
    exit 1
fi

