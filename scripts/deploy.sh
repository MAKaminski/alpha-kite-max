#!/usr/bin/env bash
# alpha-kite-v2 deploy script.
#
# Provisions Vercel + Railway + applies every Supabase migration from your
# local shell. The Claude Code sandbox where this script was authored
# cannot reach api.vercel.com / backboard.railway.app / Supabase, so the
# script must be run from a network with outbound access.
#
# Usage (one shot, all four env vars exported):
#   export VERCEL_TOKEN=...                   # https://vercel.com/account/tokens
#   export RAILWAY_TOKEN=...                  # https://railway.com (project token)
#   export SUPABASE_URL=https://<ref>.supabase.co
#   export SUPABASE_PUBLISHABLE_KEY=sb_publishable_...   # the "anon" key
#   export SUPABASE_DB_URL='postgres://postgres.<ref>:<pw>@<host>:5432/postgres?sslmode=require'
#   export SUPABASE_SERVICE_ROLE_KEY=...      # secret service-role key (for /live-enable writes)
#   bash scripts/deploy.sh
#
# Optional toggles:
#   RUN_BACKFILL=1     also run scripts/backfill_bars.py for QQQ (slow:
#                      yfinance pulls 1m/5m/1h/1d at each tier's free-cap)
#   BACKFILL_SYMBOLS="QQQ SPY"  defaults to "QQQ" when RUN_BACKFILL=1
#   SKIP_PRECHECK=1    skip the local pytest+backtest sanity run
#
# Idempotent except for `vercel --prod` (always deploys a new build) and
# `railway up` (always deploys a new revision).

set -euo pipefail

# ──────────── REQUIRED env vars ──────────────────────────────────────────
: "${VERCEL_TOKEN:?Generate at https://vercel.com/account/tokens}"

# Railway accepts two token types:
#   RAILWAY_API_TOKEN  → account-scoped; can run `railway init` to create projects
#   RAILWAY_TOKEN      → project-scoped; only works against an existing project
# This script supports either: with API token we'll create the project; with
# project token we assume the project already exists and skip init.
if [[ -z "${RAILWAY_API_TOKEN:-}" && -z "${RAILWAY_TOKEN:-}" ]]; then
  echo "ERROR: set RAILWAY_API_TOKEN (account token) or RAILWAY_TOKEN (project token)"
  echo "       generate at https://railway.com (Account or Project Settings → Tokens)"
  exit 1
fi
: "${SUPABASE_URL:?From Project Settings → API}"
: "${SUPABASE_PUBLISHABLE_KEY:?The 'publishable' (anon) key}"
SUPABASE_DB_URL="${SUPABASE_DB_URL:-}"  # optional: skip migrations if unset
SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-}"  # optional: needed for /live-enable
RUN_BACKFILL="${RUN_BACKFILL:-0}"
BACKFILL_SYMBOLS="${BACKFILL_SYMBOLS:-QQQ}"

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

# ──────────── Supabase migrations FIRST (so services have tables ready) ──
if [[ -n "$SUPABASE_DB_URL" ]]; then
  command -v psql >/dev/null || {
    echo "psql not found — install postgresql-client (e.g. brew install libpq)"; exit 1;
  }
  for sql in "$REPO_ROOT"/infra/supabase/migrations/*.sql; do
    echo "==> Supabase: apply $(basename "$sql")"
    psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$sql"
  done
  echo "    all migrations applied"
else
  echo "==> Supabase: SUPABASE_DB_URL not set — skipping SQL migrations"
fi

# ──────────── (optional) historical bar backfill ─────────────────────────
if [[ "$RUN_BACKFILL" == "1" && -n "$SUPABASE_DB_URL" ]]; then
  for sym in $BACKFILL_SYMBOLS; do
    echo "==> Backfill: $sym (1m/7d, 5m/60d, 1h/730d, 1d/5y)"
    SUPABASE_DB_URL="$SUPABASE_DB_URL" \
      python -m scripts.backfill_bars --symbol "$sym"
  done
fi

# ──────────── Railway ────────────────────────────────────────────────────
# We run Railway BEFORE Vercel so that the backtest-api service gets a
# public domain we can set on Vercel (BACKTEST_API_URL) before the
# Vercel build picks it up.
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

if [[ -n "${RAILWAY_API_TOKEN:-}" ]]; then
  echo "==> Railway: account token detected (will create project if needed)"
  export RAILWAY_API_TOKEN
  railway whoami || {
    echo "ERROR: RAILWAY_API_TOKEN rejected. Generate an account token at"
    echo "       https://railway.com (top-right avatar → Account Settings → Tokens)"
    exit 1
  }
  if ! railway status 2>/dev/null | grep -qi 'project'; then
    echo "==> Railway: init project alpha-kite-v2"
    railway init --name alpha-kite-v2
  fi
else
  echo "==> Railway: project token detected (project must already exist)"
  export RAILWAY_TOKEN
  # Verify the token resolves to a project by listing its services. We use
  # `service list` instead of `status` because `status` crashes (Abort trap)
  # when its stderr is piped on macOS (Railway CLI bug as of 4.56).
  if ! railway service list >/dev/null 2>&1; then
    echo "ERROR: RAILWAY_TOKEN does not point at an accessible project."
    echo "       Open https://railway.com → choose your project → Settings"
    echo "       → Tokens → Create Token, then re-export RAILWAY_TOKEN."
    exit 1
  fi
fi

deploy_service() {
  local svc="$1"
  local dockerfile="$2"
  local expose="${3:-private}"   # pass "public" to generate a *.up.railway.app domain

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

  if [[ "$expose" == "public" ]]; then
    echo "==> Railway: ensure '$svc' has a public domain"
    # `railway domain` with no args either prints the existing domain or
    # generates a new *.up.railway.app one.
    railway domain --service "$svc" 2>/dev/null || railway domain
  fi
}

deploy_service strategy-engine     services/strategy-engine/Dockerfile
deploy_service market-data-stream  services/market-data-stream/Dockerfile
deploy_service backtest-api        services/backtest-api/Dockerfile  public

# After deploy_service backtest-api, capture the public URL so we can
# wire it onto Vercel as BACKTEST_API_URL.
echo "==> Railway: capture backtest-api domain"
railway service link backtest-api >/dev/null 2>&1 || true
BACKTEST_API_DOMAIN="$(railway domain --service backtest-api 2>/dev/null \
  | grep -oE '[a-z0-9.-]+\.up\.railway\.app' | head -1 || true)"
if [[ -z "$BACKTEST_API_DOMAIN" ]]; then
  # Fallback: parse `railway service` info.
  BACKTEST_API_DOMAIN="$(railway service backtest-api 2>/dev/null \
    | grep -oE '[a-z0-9.-]+\.up\.railway\.app' | head -1 || true)"
fi
if [[ -n "$BACKTEST_API_DOMAIN" ]]; then
  BACKTEST_API_URL="https://${BACKTEST_API_DOMAIN}"
  echo "    backtest-api URL = $BACKTEST_API_URL"
else
  BACKTEST_API_URL=""
  echo "    WARNING: could not auto-detect backtest-api domain."
  echo "    Find it under Railway → backtest-api → Settings → Networking,"
  echo "    then set BACKTEST_API_URL on Vercel manually."
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
set_vercel_env() {
  local var="$1" value="$2" env="$3"
  [[ -z "$value" ]] && return 0
  vercel env remove "$var" "$env" --yes --token "$VERCEL_TOKEN" 2>/dev/null || true
  printf "%s\n" "$value" | vercel env add "$var" "$env" --token "$VERCEL_TOKEN"
}

for env in production preview development; do
  set_vercel_env NEXT_PUBLIC_SUPABASE_URL      "$SUPABASE_URL"             "$env"
  set_vercel_env NEXT_PUBLIC_SUPABASE_ANON_KEY "$SUPABASE_PUBLISHABLE_KEY" "$env"
  # New env vars (streams I + E):
  set_vercel_env BACKTEST_API_URL              "$BACKTEST_API_URL"         "$env"
  set_vercel_env SUPABASE_SERVICE_ROLE_KEY     "$SUPABASE_SERVICE_ROLE_KEY" "$env"
done

echo "==> Vercel: deploy --prod (cwd=repo root, rootDirectory=apps/web)"
vercel --prod --yes --token "$VERCEL_TOKEN"

echo
echo "──── done ────"
echo "Vercel:        production URL printed above"
echo "Railway:       https://railway.app/dashboard → alpha-kite-v2"
echo "Logs:          railway logs --service strategy-engine"
[[ -n "$BACKTEST_API_URL" ]] && \
  echo "Backtest API:  $BACKTEST_API_URL/healthz   (should return {\"ok\":true})"
echo
echo "broker.dry_run is still TRUE (default). Use /live-enable in the dashboard"
echo "(or edit config/strategy.yaml + restart strategy-engine) to flip it."
