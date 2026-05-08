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
# Railway: account tokens use RAILWAY_API_TOKEN; older project tokens use
# RAILWAY_TOKEN. We accept either but normalize to RAILWAY_API_TOKEN since
# this script needs account-level commands (railway init, whoami, etc).
if [[ -z "${RAILWAY_API_TOKEN:-}" && -n "${RAILWAY_TOKEN:-}" ]]; then
  echo "==> NOTE: copying RAILWAY_TOKEN → RAILWAY_API_TOKEN (account token)"
  export RAILWAY_API_TOKEN="$RAILWAY_TOKEN"
fi
: "${RAILWAY_API_TOKEN:?Generate an account token at https://railway.com/account/tokens (NOT a project token)}"
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

# Run all Vercel ops from REPO ROOT, not from apps/web. After the
# rootDirectory PATCH below, Vercel resolves deploy source as
# cwd + rootDirectory; if cwd is already apps/web, you get apps/web/apps/web
# (404). The project link file ends up at $REPO_ROOT/.vercel/project.json.
cd "$REPO_ROOT"

# Clean any stale link from a prior attempt (e.g. apps/web/.vercel from v1
# of this script).
rm -rf "$REPO_ROOT/apps/web/.vercel"

echo "==> Vercel: link project at repo root (creates if missing)"
vercel link --yes --project alpha-kite-max --token "$VERCEL_TOKEN"

PROJECT_ID=$(jq -r .projectId "$REPO_ROOT/.vercel/project.json")
ORG_ID=$(jq -r .orgId "$REPO_ROOT/.vercel/project.json")

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
  # Trailing newline keeps the optional "Git branch?" prompt happy on preview env.
  printf "%s\n" "$SUPABASE_URL"             | vercel env add NEXT_PUBLIC_SUPABASE_URL      "$env" --token "$VERCEL_TOKEN"
  printf "%s\n" "$SUPABASE_PUBLISHABLE_KEY" | vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY "$env" --token "$VERCEL_TOKEN"
done

echo "==> Vercel: deploy --prod (cwd=repo root, rootDirectory=apps/web)"
vercel --prod --yes --token "$VERCEL_TOKEN"

# ──────────── Railway ────────────────────────────────────────────────────
echo "==> Railway: ensure CLI is installed"
if ! command -v railway >/dev/null; then
  if command -v brew >/dev/null; then
    brew install railway
  elif command -v npm >/dev/null; then
    npm i -g @railway/cli || {
      echo "ERROR: 'npm i -g @railway/cli' failed (likely macOS permissions"
      echo "       on the global npm prefix). Install via Homebrew instead:"
      echo "         brew install railway"
      echo "       or use the upstream installer:"
      echo "         curl -fsSL https://railway.app/install.sh | sh"
      exit 1
    }
  else
    echo "ERROR: neither brew nor npm available; install Railway CLI manually"
    echo "       https://docs.railway.app/guides/cli"
    exit 1
  fi
fi
command -v railway >/dev/null || {
  echo "ERROR: railway CLI installed but not on PATH; restart your shell and re-run"
  exit 1
}
echo "    $(railway --version)"

# Railway CLI reads RAILWAY_API_TOKEN for account-scoped ops
export RAILWAY_API_TOKEN
# Pre-flight: confirm the token actually authenticates before we try ops
railway whoami || {
  echo "ERROR: railway whoami failed. Generate an ACCOUNT token at"
  echo "       https://railway.com/account/tokens (not a project token)"
  exit 1
}

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
