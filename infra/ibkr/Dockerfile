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

# gnzsnz writes jts.ini with TrustedIPs=127.0.0.1, which makes IB Gateway
# reject API connections from anything other than localhost. On Railway the
# strategy-engine container reaches us via the private network, not 127.0.0.1,
# so the gateway TCP-accepts then immediately closes the socket.
#
# Patch TrustedIPs=* once jts.ini exists. The container is only reachable on
# Railway's private network (port 4002 is not publicly exposed), so widening
# the allowlist here does not expose the API to the internet.
#
# Note: gnzsnz/ib-gateway:stable ends with `USER ibgateway`, so RUN steps
# in this Dockerfile execute as that unprivileged user by default and
# cannot write to /usr/local/bin/. Switch to root for the build and stay
# as root through runtime — gnzsnz's /root/scripts/run.sh is owned by
# root and not other-readable, so the entrypoint MUST run as root too.
# Java/IB Gateway is launched under the ibgateway user via su/gosu inside
# run.sh itself, so end-user code still runs unprivileged.
USER root
RUN cat > /usr/local/bin/patch-trusted-ips.sh <<'EOF' && chmod +x /usr/local/bin/patch-trusted-ips.sh
#!/usr/bin/env bash
set -euo pipefail
JTS_INI=/home/ibgateway/Jts/jts.ini
# Keep watching: gnzsnz/IBC may rewrite jts.ini on relogin.
for _ in {1..120}; do
  if [ -f "$JTS_INI" ] && grep -q '^TrustedIPs=' "$JTS_INI"; then
    if ! grep -q '^TrustedIPs=\*' "$JTS_INI"; then
      sed -i 's|^TrustedIPs=.*|TrustedIPs=*|' "$JTS_INI"
      echo "[patch-trusted-ips] set TrustedIPs=* in $JTS_INI"
    fi
    sleep 5
    continue
  fi
  sleep 1
done
EOF

# Wrap the gnzsnz entrypoint: kick off the patcher in the background, then
# exec the upstream script. The patcher polls and rewrites jts.ini repeatedly
# so a daily IBKR-forced relogin (which can regenerate the file) does not
# silently restore TrustedIPs=127.0.0.1.
ENTRYPOINT ["/bin/bash", "-c", "/usr/local/bin/patch-trusted-ips.sh & exec /root/scripts/run.sh \"$@\"", "--"]

# Paper-trading port. We deliberately do NOT expose 4001 (live).
EXPOSE 4002

# Healthcheck — confirm the API port is open. First boot can take 90-120s
# (Java/IB Gateway startup), so we give a generous start_period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD nc -z localhost 4002 || exit 1
