#!/usr/bin/env bash
# alpha-kite-v2 deploy script.
#
# Provisions Vercel + Railway from your local shell. Apply the Supabase
# migration manually via the dashboard SQL editor (one paste of
# infra/supabase/migrations/0001_initial.sql) — Supabase has no token-based
# DDL endpoint that's worth automating for a single migration.
#
# Usage:
#   1. ROTATE the tokens you pasted into the previous Claude session.
#      Generate fresh ones now.
#   2. Fill the four variables below.
#   3. bash deploy-alpha-kite.sh
#
# This script is idempotent except for `vercel --prod` which always deploys
# a new build.

set -euo pipefail

# ──────────── REQUIRED — fill these in before running ────────────────────
export VERCEL_TOKEN="${VERCEL_TOKEN:?Generate at https://vercel.com/account/tokens}"
export RAILWAY_TOKEN="${RAILWAY_TOKEN:?Generate at https://railway.app/account/tokens}"
export SUPABASE_URL="${SUPABASE_URL:?From Project Settings → API}"
export SUPABASE_PUBLISHABLE_KEY="${SUPABASE_PUBLISHABLE_KEY:?The 'publishable' (anon) key}"

# Optional — only needed if you want this script to also run the SQL migration
SUPABASE_DB_URL="${SUPABASE_DB_URL:-}"

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ -d "$REPO_ROOT/apps/web" ]] || REPO_ROOT="$HOME/alpha-kite-max"
cd "$REPO_ROOT"

echo "==> repo root: $REPO_ROOT"
echo "==> precheck: pytest + backtest"
python -m pytest -q -m "not live and not supabase" >/dev/null
python scripts/backtest.py >/dev/null
echo "    OK"

# ──────────── Vercel ─────────────────────────────────────────────────────
echo "==> Vercel: install/upgrade CLI"
command -v vercel >/dev/null || npm i -g vercel >/dev/null

cd "$REPO_ROOT/apps/web"

echo "==> Vercel: link project"
# `vercel link` writes .vercel/project.json. Use --yes to auto-link if a
# project name matches; otherwise it prompts. We pass --project to be explicit.
vercel link --yes --project alpha-kite-max --token "$VERCEL_TOKEN" || \
  vercel link --yes --token "$VERCEL_TOKEN"

echo "==> Vercel: set env vars"
# `vercel env add` reads from stdin; we pipe the value in. Idempotent via rm-then-add.
for env in production preview development; do
  for var in NEXT_PUBLIC_SUPABASE_URL NEXT_PUBLIC_SUPABASE_ANON_KEY; do
    vercel env rm "$var" "$env" --yes --token "$VERCEL_TOKEN" 2>/dev/null || true
  done
  echo "$SUPABASE_URL"             | vercel env add NEXT_PUBLIC_SUPABASE_URL       "$env" --token "$VERCEL_TOKEN"
  echo "$SUPABASE_PUBLISHABLE_KEY" | vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY  "$env" --token "$VERCEL_TOKEN"
done

# Root directory: the Vercel CLI does NOT expose this as a flag. The way to
# fix it without the dashboard is the Projects API:
echo "==> Vercel: PATCH project root directory to apps/web"
PROJECT_ID=$(jq -r .projectId "$REPO_ROOT/apps/web/.vercel/project.json")
ORG_ID=$(jq -r .orgId "$REPO_ROOT/apps/web/.vercel/project.json")
curl -sS -X PATCH \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rootDirectory":"apps/web","framework":"nextjs"}' \
  "https://api.vercel.com/v9/projects/$PROJECT_ID?teamId=$ORG_ID" >/dev/null

echo "==> Vercel: deploy --prod"
vercel --prod --yes --token "$VERCEL_TOKEN"

cd "$REPO_ROOT"

# ──────────── Railway ────────────────────────────────────────────────────
echo "==> Railway: install/upgrade CLI"
command -v railway >/dev/null || npm i -g @railway/cli >/dev/null

# Railway CLI auth: pass via env var
export RAILWAY_TOKEN

if ! railway status 2>/dev/null | grep -q 'Project:'; then
  echo "==> Railway: init project alpha-kite-v2"
  railway init --name alpha-kite-v2
fi

echo "==> Railway: deploy strategy-engine"
railway service create strategy-engine 2>/dev/null || true
railway service connect strategy-engine
railway variables \
  --set STRATEGY_CONFIG=./config/strategy.yaml \
  --set SUPABASE_URL="$SUPABASE_URL" \
  --set SUPABASE_DB_URL="${SUPABASE_DB_URL:-unset_set_after_phase1}" \
  --set IBKR_HOST=ibkr-gateway \
  --set IBKR_PORT=7497 \
  --set IBKR_CLIENT_ID=17 \
  --set IBKR_TRADING_MODE=paper \
  --set LOG_LEVEL=INFO

# Override the Dockerfile path: Railway needs the path inside the repo
railway variables --set "RAILWAY_DOCKERFILE_PATH=services/strategy-engine/Dockerfile"
railway up --detach

echo "==> Railway: deploy market-data-stream"
railway service create market-data-stream 2>/dev/null || true
railway service connect market-data-stream
railway variables \
  --set STRATEGY_CONFIG=./config/strategy.yaml \
  --set SUPABASE_URL="$SUPABASE_URL" \
  --set SUPABASE_DB_URL="${SUPABASE_DB_URL:-unset_set_after_phase1}" \
  --set IBKR_HOST=ibkr-gateway \
  --set IBKR_PORT=7497 \
  --set LOG_LEVEL=INFO
railway variables --set "RAILWAY_DOCKERFILE_PATH=services/market-data-stream/Dockerfile"
railway up --detach

# ──────────── Supabase migration (optional, only if SUPABASE_DB_URL set) ─
if [[ -n "$SUPABASE_DB_URL" ]]; then
  echo "==> Supabase: apply 0001_initial.sql"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
    -f "$REPO_ROOT/infra/supabase/migrations/0001_initial.sql"
else
  echo "==> Supabase: SUPABASE_DB_URL not set — skipping SQL migration."
  echo "    Apply manually in the Supabase dashboard SQL editor:"
  echo "      $REPO_ROOT/infra/supabase/migrations/0001_initial.sql"
fi

echo
echo "──── done ────"
echo "Vercel:   open the URL printed above"
echo "Railway:  https://railway.app/dashboard → alpha-kite-v2"
echo "Logs:     railway logs --service strategy-engine"
echo
echo "broker.dry_run is still TRUE (default). No orders will be placed until"
echo "you flip it in config/strategy.yaml AND have validated the paper-account"
echo "guard with a real DU* account id."
