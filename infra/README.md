# Infrastructure guide

This directory holds everything you need to deploy alpha-kite-v2 outside of a
laptop: Railway service definitions, an IBKR Gateway image, Supabase
migrations, and the local `docker-compose.yml` smoke stack at the repo root.

```
infra/
├── ibkr/        # Headless IBKR Gateway image (paper-only)
├── railway/     # Railway service.json files (one per service)
├── supabase/    # SQL migrations applied to the Supabase Postgres
└── README.md    # ← you are here
```

## Local smoke test

```bash
cp .env.example .env
$EDITOR .env                 # set IBKR_USERNAME / IBKR_PASSWORD / Supabase keys
docker compose up --build
```

Five containers come up on the `alpha-kite` bridge network: `ibkr-gateway`,
`supabase-db`, `strategy-engine`, `market-data-stream`, `web`. The web UI is
at <http://localhost:3000>; the gateway listens on `localhost:7497`; Postgres
on `localhost:54322`.

## Deploying to Railway

Railway builds each service from its own Dockerfile via the JSON specs in
`infra/railway/`.

```bash
# One-time
railway login
railway link

# Per-service (link the file, then deploy)
railway service create strategy-engine
railway service create market-data-stream

# Push from the repo root
railway up --service strategy-engine
railway up --service market-data-stream
```

Both services need these envs set in Railway's dashboard:

- `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`
- `IBKR_USERNAME`, `IBKR_PASSWORD`, `IBKR_TRADING_MODE=paper`
- `STRATEGY_CONFIG=/app/config/strategy.yaml`

The IBKR gateway itself is **not** suited to Railway (it needs a long-lived
TCP port and a stateful filesystem). Run it on a dedicated VM (Fly.io, Hetzner,
your own laptop) and point Railway services at it via `IBKR_HOST`.

## Deploying the frontend

```bash
cd apps/web
vercel              # first deploy → set NEXT_PUBLIC_SUPABASE_* envs
vercel --prod       # subsequent deploys
```

## Safety guards (how they interact)

Three independent safety layers must all agree before an order goes out:

1. **`TRADING_MODE=paper`** — enforced both in the IBKR container's entrypoint
   and inside `ibc-config.ini.template`. See `infra/ibkr/README.md` for
   details.
2. **Strategy-side config gates** — owned by Tracks A/B/D; not configured
   here.
3. **Kill-switch sentinel file** — see below.

### Flipping the kill switch

To stop the engine from placing any further orders without taking containers
down:

```bash
touch KILL          # at the repo root
```

The strategy engine polls for a file named `KILL` at the project root every
loop iteration; if it exists, all order-placement paths short-circuit to a
no-op. To re-enable trading:

```bash
rm KILL
```

The sentinel is also listed in `.gitignore` and `.dockerignore` so it can
never be committed or accidentally baked into an image.

## Updating Supabase migrations

```bash
# Add a new migration file (numbered)
$EDITOR infra/supabase/migrations/0002_add_orders_index.sql

# Apply remotely
supabase db push

# Or, locally via docker compose:
docker compose down supabase-db -v   # drop the volume to re-run init scripts
docker compose up   supabase-db
```
