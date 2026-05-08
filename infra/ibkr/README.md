# IBKR Gateway container

Headless Interactive Brokers Gateway, driven by IBC, locked to **paper trading
only**. The container refuses to start unless `TRADING_MODE=paper`.

## One-time setup

1. Create a paper trading account at IBKR if you don't have one:
   <https://www.interactivebrokers.com/en/index.php?f=1286>.
2. Accept IBKR's software licence terms — they govern the gateway binary that
   ships inside the container:
   <https://www.interactivebrokers.com/en/index.php?f=14099>.
3. Note your **paper** username and password. Do not reuse the live credentials.

## Configuration

The container reads three environment variables. All three are required.

| Variable        | Required | Notes                                                |
|-----------------|----------|------------------------------------------------------|
| `TWS_USERID`    | yes      | Paper account username.                              |
| `TWS_PASSWORD`  | yes      | Paper account password. Pass via secret store only.  |
| `TRADING_MODE`  | yes      | Must be the literal string `paper`.                  |

Set them in `.env` next to the repo root, or inject via Railway / docker
secrets / Kubernetes secrets. **Never** bake them into the image.

```bash
export TWS_USERID=...
export TWS_PASSWORD=...
export TRADING_MODE=paper
docker compose up ibkr-gateway
```

## Why `TRADING_MODE=paper` is enforced

The entrypoint script normalises `TRADING_MODE` to lower-case and exits with a
non-zero status if the value is anything other than `paper`. It also greps the
value for the substring `live` as belt-and-braces — so a typo such as
`Paper-Live` is rejected too.

This guard is duplicated in `ibc-config.ini.template`, which hard-codes
`TradingMode=paper`. To talk to a live account you would need to bypass *both*
checks and edit a templated file at runtime; the goal is that no single
copy-paste mistake can route real money through the system.

## Daily session reset

IBKR forces a server-side restart at **23:50 America/New_York** every day. IBC
handles the relogin transparently in most cases, but the API port can briefly
disappear during the reset. We rely on two layers:

1. **IBC's own auto-relogin**, configured via `ReloginAfterSecondFactor=yes`
   in `ibc-config.ini.template`.
2. **Docker healthcheck**: `nc -z localhost 7497` runs every 30 seconds. If
   the port stays closed past the retry budget, the orchestrator (Docker /
   Railway) restarts the container and IBC logs back in from scratch.

If you see the engine emit `IBKR_CONNECTION_LOST` errors right around 23:50
ET, that is expected — the engine should self-heal within ~2 minutes.

## Files in this directory

- `Dockerfile` — image definition. Inherits from `ibcalpha/ibc:latest` by
  default; an `openjdk:17-slim` fallback is documented inline for environments
  that cannot pull from Docker Hub.
- `jts.ini.template` — minimal Gateway settings, env-substituted at start.
- `ibc-config.ini.template` — IBC behaviour settings, env-substituted at start.
- `README.md` — this file.

## Troubleshooting

- **Container exits immediately with status 64**: `TWS_USERID` or
  `TWS_PASSWORD` is unset.
- **Container exits with status 65**: `TRADING_MODE` is not `paper`. Fix the
  env var; do not patch the entrypoint.
- **Healthcheck flapping**: port 7497 is taking longer than the start-period
  to come up. Increase `--start-period` if your host is slow to boot Java.
