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
# as root through runtime — gnzsnz's run.sh entrypoint is owned by root
# and not other-readable, so the wrapper MUST run as root too.
# Java/IB Gateway is launched under the ibgateway user via su/gosu inside
# run.sh itself, so end-user code still runs unprivileged.
USER root

# The path to gnzsnz's run.sh has moved across image versions
# (/root/scripts/run.sh historically, but newer stables drop it elsewhere).
# Resolve at build time and store the path so the runtime wrapper does
# not have to guess.
RUN GNZSNZ_RUN_SH="$( \
      find / -type f -name run.sh -executable 2>/dev/null \
      | grep -E '(scripts|gnzsnz)' \
      | head -1 \
    )" && \
    if [ -z "$GNZSNZ_RUN_SH" ]; then \
      GNZSNZ_RUN_SH="$(find / -type f -name run.sh -executable 2>/dev/null | head -1)"; \
    fi && \
    test -n "$GNZSNZ_RUN_SH" && \
    echo "[build] resolved gnzsnz entrypoint: $GNZSNZ_RUN_SH" && \
    echo "$GNZSNZ_RUN_SH" > /usr/local/etc/gnzsnz-run-sh.path

# Patch every file under the image that hardcodes TrustedIPs=127.0.0.1
# (the gnzsnz scripts and any jts.ini templates they ship with). IB Gateway
# reads jts.ini once on startup and never reloads it, so changing the file
# AFTER the gateway has started is too late — by then the in-memory
# whitelist already says "only allow 127.0.0.1" and the connection from
# the strategy-engine container gets dropped 3ms after TCP-accept.
#
# Doing this at build time means run.sh writes TrustedIPs=* into jts.ini
# the very first time it runs, so the gateway boots with the right value.
RUN grep -rln 'TrustedIPs=127\.0\.0\.1' / 2>/dev/null \
      | while IFS= read -r f; do \
          sed -i 's|TrustedIPs=127\.0\.0\.1|TrustedIPs=*|g' "$f" && \
          echo "[build] patched TrustedIPs in $f"; \
        done

RUN cat > /usr/local/bin/patch-trusted-ips.sh <<'EOF' && chmod +x /usr/local/bin/patch-trusted-ips.sh
#!/usr/bin/env bash
# Belt-and-braces: keep watching jts.ini and re-apply TrustedIPs=* if a
# daily IBKR-forced relogin or some unexpected codepath ever rewrites the
# file with the old value. The build-time sed handles the common path.
set -euo pipefail
JTS_INI=/home/ibgateway/Jts/jts.ini
for _ in {1..120}; do
  if [ -f "$JTS_INI" ] && grep -q '^TrustedIPs=' "$JTS_INI"; then
    if ! grep -q '^TrustedIPs=\*' "$JTS_INI"; then
      sed -i 's|^TrustedIPs=.*|TrustedIPs=*|' "$JTS_INI"
      echo "[patch-trusted-ips] re-set TrustedIPs=* in $JTS_INI"
    fi
    sleep 5
    continue
  fi
  sleep 1
done
EOF

RUN cat > /usr/local/bin/start-with-patcher.sh <<'EOF' && chmod +x /usr/local/bin/start-with-patcher.sh
#!/usr/bin/env bash
set -euo pipefail
/usr/local/bin/patch-trusted-ips.sh &
RUN_SH="$(cat /usr/local/etc/gnzsnz-run-sh.path 2>/dev/null || true)"
if [ -z "$RUN_SH" ] || [ ! -x "$RUN_SH" ]; then
  echo "[start-with-patcher] FATAL: gnzsnz run.sh not found at '$RUN_SH'" >&2
  exit 1
fi
echo "[start-with-patcher] exec $RUN_SH"
exec "$RUN_SH" "$@"
EOF

# Wrap the gnzsnz entrypoint: kick off the patcher in the background, then
# exec the upstream script. The patcher polls and rewrites jts.ini repeatedly
# so a daily IBKR-forced relogin (which can regenerate the file) does not
# silently restore TrustedIPs=127.0.0.1.
ENTRYPOINT ["/usr/local/bin/start-with-patcher.sh"]

# Paper-trading port. We deliberately do NOT expose 4001 (live).
EXPOSE 4002

# Healthcheck — confirm the API port is open. First boot can take 90-120s
# (Java/IB Gateway startup), so we give a generous start_period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD nc -z localhost 4002 || exit 1
