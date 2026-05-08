# syntax=docker/dockerfile:1.6
# IBKR Gateway sidecar — paper trading only.
#
# Uses gnzsnz/ib-gateway:stable as the base. That image bundles IB Gateway,
# IBC, and Xvfb headless display, all pre-configured. We add a paper-only
# guard on top.
#
# Required env vars at runtime:
#   TWS_USERID     — IBKR login (e.g. kaminski1337)
#   TWS_PASSWORD   — IBKR password
#   TRADING_MODE   — must be exactly "paper" (the entrypoint refuses anything else)
#
# Default ports exposed by gnzsnz/ib-gateway:
#   4001 — live trading (we never expose this)
#   4002 — paper trading (this is what the engine connects to)
#
# IMPORTANT: by building/running this image you accept Interactive Brokers'
# software license terms (https://www.interactivebrokers.com/en/index.php?f=14099).

FROM gnzsnz/ib-gateway:stable

# Paper-trading port. We deliberately do NOT expose 4001 (live).
EXPOSE 4002

# Hard guard on top of gnzsnz's own check: refuse to start if TRADING_MODE
# is anything other than "paper". The base image also enforces this but a
# belt-and-braces check costs nothing.
USER root
RUN cat <<'EOF' > /etc/cont-init.d/00-paper-guard.sh
#!/usr/bin/env bash
set -euo pipefail
mode_lc="$(printf '%s' "${TRADING_MODE:-}" | tr '[:upper:]' '[:lower:]')"
if [[ "$mode_lc" != "paper" ]]; then
  echo "FATAL: TRADING_MODE must be 'paper'; got '${TRADING_MODE:-<empty>}'" >&2
  exit 65
fi
echo "paper-mode guard: OK"
EOF
RUN chmod +x /etc/cont-init.d/00-paper-guard.sh

# Healthcheck — confirm the API port is open. First boot can take 90-120s
# (Java/IB Gateway startup), so we give a generous start_period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD nc -z localhost 4002 || exit 1
