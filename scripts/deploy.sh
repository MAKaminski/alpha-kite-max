#!/usr/bin/env bash
# alpha-kite-v2 deploy script.
#
# Provisions Vercel + Railway + applies the Supabase migration from your
# local shell. The Claude Code sandbox where this script was authored
# cannot reach api.vercel.com / backboard.railway.app / Supabase, so the
# script must be run from a network with outbound access.
#
# Usage:
#   export VERCEL_TOKEN=...
#   export RAILWAY_TOKEN=...
#   export SUPABASE_URL=https://<ref>.supabase.co
#   export SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
#   export SUPABASE_DB_URL='postgres://postgres.<ref>:<pw>@<host>:5432/postgres?sslmode=require'
#   bash scripts/deploy.sh
#
# Idempotent except for `vercel --prod` (always deploys a new build) and
# `railway up` (always deploys a new revision).

set -euo pipefail

# ──────────── REQUIRED env vars ──────────────────────────────────────────
: "${VERCEL_TOKEN:?Generate at https://vercel.com/account/tokens}"
: "${RAILWAY_TOKEN:?Generate at https://railway.app/account/tokens}"
: "${SUPABASE_URL:?From Project Settings → API}"
: "${SUPABASE_PUBLISHABLE_KEY:?The 'publishable' (anon) key}"
SUPABASE_DB_URL="${SUPABASE_DB_URL:-}"  # optional: skip migration if unset

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
echo "==> repo root: $REPO_ROOT"

if [[ "${SKIP_PRECHECK:-0}" != "1" ]] && python -m pytest --version >/dev/null 2>&1; then
  echo "==> precheck: pytest + backtest (offline)"
  python -m pytest -q -m "not live and not supabase" >/dev/null
  python scripts/backtest.py >/dev/null
  echo "    OK"
else
  echo "==> precheck: SKIPPED (pytest not installed locally; CI already validates)"
fi

# ──────────── Supabase migration FIRST (so services have tables ready) ───
if [[ -n "$SUPABASE_DB_URL" ]]; then
  echo "==> Supabase: apply infra/supabase/migrations/0001_initial.sql"
  command -v psql >/dev/null || {
    echo "psql not found — install postgresql-client (e.g. brew install libpq)"; exit 1;
  }
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
    -f "$REPO_ROOT/infra/supabase/migrations/0001_initial.sql"
  echo "    tables created"
else
  echo "==> Supabase: SUPABASE_DB_URL not set — skipping SQL migration"
fi

# ──────────── Vercel ─────────────────────────────────────────────────────
echo "==> Vercel: install/upgrade CLI"
command -v vercel >/dev/null || npm i -g vercel >/dev/null

cd "$REPO_ROOT/apps/web"

echo "==> Vercel: link project (creates if missing)"
# --yes accepts defaults; --project pins the slug. If a project with this
# slug already exists in your scope, Vercel links to it.
vercel link --yes --project alpha-kite-max --token "$VERCEL_TOKEN"

PROJECT_ID=$(jq -r .projectId .vercel/project.json)
ORG_ID=$(jq -r .orgId .vercel/project.json)

echo "==> Vercel: PATCH rootDirectory=apps/web (CLI lacks a flag for this)"
curl -sS -X PATCH \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rootDirectory":"apps/web","framework":"nextjs"}' \
  "https://api.vercel.com/v9/projects/$PROJECT_ID?teamId=$ORG_ID" >/dev/null
echo "    rootDirectory patched"

echo "==> Vercel: set env vars (production + preview + development)"
for env in production preview development; do
  for var in NEXT_PUBLIC_SUPABASE_URL NEXT_PUBLIC_SUPABASE_ANON_KEY; do
    vercel env remove "$var" "$env" --yes --token "$VERCEL_TOKEN" 2>/dev/null || true
  done
  printf "%s" "$SUPABASE_URL"             | vercel env add NEXT_PUBLIC_SUPABASE_URL      "$env" --token "$VERCEL_TOKEN"
  printf "%s" "$SUPABASE_PUBLISHABLE_KEY" | vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY "$env" --token "$VERCEL_TOKEN"
done

echo "==> Vercel: deploy --prod (root is apps/web after link)"
vercel --prod --yes --token "$VERCEL_TOKEN"

cd "$REPO_ROOT"

# ──────────── Railway ────────────────────────────────────────────────────
echo "==> Railway: install/upgrade CLI"
command -v railway >/dev/null || npm i -g @railway/cli >/dev/null

export RAILWAY_TOKEN  # consumed by the CLI

if ! railway status 2>/dev/null | grep -qi 'project'; then
  echo "==> Railway: init project alpha-kite-v2"
  railway init --name alpha-kite-v2
fi

deploy_service() {
  local svc="$1"
  local dockerfile="$2"

  echo "==> Railway: ensure service '$svc' exists"
  if ! railway service list 2>/dev/null | grep -q "$svc"; then
    railway add --service "$svc"
  fi

  echo "==> Railway: link to '$svc'"
  railway service link "$svc"

  echo "==> Railway: set env vars on '$svc'"
  railway variable set "STRATEGY_CONFIG=./config/strategy.yaml" --service "$svc"
  railway variable set "SUPABASE_URL=$SUPABASE_URL"             --service "$svc"
  if [[ -n "$SUPABASE_DB_URL" ]]; then
    railway variable set "SUPABASE_DB_URL=$SUPABASE_DB_URL"     --service "$svc"
  fi
  railway variable set "IBKR_HOST=ibkr-gateway"                  --service "$svc"
  railway variable set "IBKR_PORT=7497"                          --service "$svc"
  railway variable set "IBKR_CLIENT_ID=17"                       --service "$svc"
  railway variable set "IBKR_TRADING_MODE=paper"                 --service "$svc"
  railway variable set "LOG_LEVEL=INFO"                          --service "$svc"
  railway variable set "RAILWAY_DOCKERFILE_PATH=$dockerfile"     --service "$svc"

  echo "==> Railway: deploy '$svc'"
  railway up --detach --service "$svc"
}

deploy_service strategy-engine     services/strategy-engine/Dockerfile
deploy_service market-data-stream  services/market-data-stream/Dockerfile

echo
echo "──── done ────"
echo "Vercel:   production URL printed above"
echo "Railway:  https://railway.app/dashboard → alpha-kite-v2"
echo "Logs:     railway logs --service strategy-engine"
echo
echo "broker.dry_run is still TRUE (default). No orders are placed until you"
echo "edit config/strategy.yaml AND have a DU* paper account validated."
