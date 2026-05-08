# syntax=docker/dockerfile:1.6
# IBKR Gateway sidecar — paper trading only.
#
# Uses gnzsnz/ib-gateway:stable as-is. That image bundles IB Gateway,
# IBC, and Xvfb headless display, all pre-configured. Its own entrypoint
# enforces TRADING_MODE — we don't add a redundant guard.
#
# Required env vars at runtime:
#   TWS_USERID     — IBKR login (e.g. kaminski1337)
#   TWS_PASSWORD   — IBKR password
#   TRADING_MODE   — must be "paper" (gnzsnz refuses anything else by default)
#
# Default ports exposed by gnzsnz/ib-gateway:
#   4001 — live trading (NEVER expose this)
#   4002 — paper trading (this is what the engine connects to)
#
# Multi-layer paper-mode safety in this repo:
#   1. config/strategy.yaml schema rejects broker.mode != "paper" at load time
#   2. PaperAccountGuard refuses non-DU paper account ids
#   3. broker.dry_run defaults to true (no orders ever placed)
#   4. gnzsnz's own entrypoint requires TRADING_MODE=paper
#
# IMPORTANT: by building/running this image you accept Interactive Brokers'
# software license terms (https://www.interactivebrokers.com/en/index.php?f=14099).

FROM gnzsnz/ib-gateway:stable

# Paper-trading port. We deliberately do NOT expose 4001 (live).
EXPOSE 4002

# Healthcheck — confirm the API port is open. First boot can take 90-120s
# (Java/IB Gateway startup), so we give a generous start_period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD nc -z localhost 4002 || exit 1
