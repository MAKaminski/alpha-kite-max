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

# IB Gateway reads jts.ini once at boot and never reloads it; patching
# the file AFTER the gateway has started is too late. The previous
# attempt (grep+sed for "TrustedIPs=127.0.0.1") found nothing because
# gnzsnz constructs that line from a variable -- the literal string is
# never on disk pre-startup. Take a different angle: pre-bake jts.ini
# at build time with all the minimal lines IBC requires (per its
# startup log, it ensures these are present and only ADDS missing
# lines, never replaces existing values). When IBC's "ensure minimal
# lines" check runs, every line is already there -- including
# TrustedIPs=* -- so it leaves the file alone and the gateway boots
# with the open whitelist.
RUN mkdir -p /home/ibgateway/Jts && \
    cat > /home/ibgateway/Jts/jts.ini <<'EOF'
[Logon]
s3store=true
Locale=en
displayedproxymsg=1
UseSSL=true

[IBGateway]
ApiOnly=true
TrustedIPs=*
EOF

RUN chown -R ibgateway:ibgateway /home/ibgateway/Jts && \
    chmod 644 /home/ibgateway/Jts/jts.ini && \
    echo "[build] pre-baked /home/ibgateway/Jts/jts.ini:" && \
    cat /home/ibgateway/Jts/jts.ini

RUN cat > /usr/local/bin/patch-trusted-ips.sh <<'EOF' && chmod +x /usr/local/bin/patch-trusted-ips.sh
#!/usr/bin/env bash
# Aggressive background watcher: keep jts.ini and IBC's config.ini set
# to the values we want. Necessary because gnzsnz's run.sh writes both
# files AFTER our pre-startup patch in start-with-patcher.sh and BEFORE
# IBC reads them, silently clobbering our values. We need to repatch
# fast enough to win the race against IBC's startup config-read.
#
# Poll at 50 ms for the first 60 s, then back off to 5 s as a safety net.
set -euo pipefail
JTS_INI=/home/ibgateway/Jts/jts.ini
IBC_INI=/home/ibgateway/ibc/config.ini

_force_jts_trustedips() {
  # IBC validates jts.ini's TrustedIPs and rewrites invalid values to
  # 127.0.0.1. With our TrustedTwsApiClientIPs=0.0.0.0 in config.ini,
  # IBC writes TrustedIPs=127.0.0.1,0.0.0.0 which is a VALID value
  # ("0.0.0.0" is IBC's documented sentinel for allow-all). Earlier
  # this watcher overwrote IBC's good value with `*` -- which IBC then
  # had to rewrite to 127.0.0.1 again, and may have left the file in
  # an invalid state while the gateway was reading it (Java loaded `*`,
  # treated it as no-match, never opened the API socket). Just leave
  # IBC's value alone; no patching needed here.
  return 0
}

_force_ibc_trusted_clients() {
  [ -f "$IBC_INI" ] || return 0
  if grep -q '^TrustedTwsApiClientIPs=' "$IBC_INI"; then
    if ! grep -q '^TrustedTwsApiClientIPs=0\.0\.0\.0' "$IBC_INI"; then
      sed -i 's|^TrustedTwsApiClientIPs=.*|TrustedTwsApiClientIPs=0.0.0.0|' "$IBC_INI"
      echo "[patch-trusted-ips] re-set TrustedTwsApiClientIPs=0.0.0.0 in $IBC_INI"
    fi
  else
    echo 'TrustedTwsApiClientIPs=0.0.0.0' >> "$IBC_INI"
    echo "[patch-trusted-ips] appended TrustedTwsApiClientIPs=0.0.0.0 to $IBC_INI"
  fi
  if grep -q '^AcceptIncomingConnectionAction=' "$IBC_INI"; then
    if ! grep -q '^AcceptIncomingConnectionAction=accept' "$IBC_INI"; then
      sed -i 's|^AcceptIncomingConnectionAction=.*|AcceptIncomingConnectionAction=accept|' "$IBC_INI"
      echo "[patch-trusted-ips] re-set AcceptIncomingConnectionAction=accept in $IBC_INI"
    fi
  else
    echo 'AcceptIncomingConnectionAction=accept' >> "$IBC_INI"
    echo "[patch-trusted-ips] appended AcceptIncomingConnectionAction=accept to $IBC_INI"
  fi
}

# Tight loop for the first 60 s -- this is where the race with IBC's
# startup read happens.
end=$(( $(date +%s) + 60 ))
while [ "$(date +%s)" -lt "$end" ]; do
  _force_jts_trustedips
  _force_ibc_trusted_clients
  sleep 0.05
done

# After IBC is up, slow-poll as a safety net for relogins that
# regenerate the files.
while true; do
  _force_jts_trustedips
  _force_ibc_trusted_clients
  sleep 5
done
EOF

RUN cat > /usr/local/bin/start-with-patcher.sh <<'EOF' && chmod +x /usr/local/bin/start-with-patcher.sh
#!/usr/bin/env bash
set -euo pipefail
# Diagnostic: dump jts.ini state so we can see in the runtime log
# whether the pre-bake survived gnzsnz's startup.
echo "[start-with-patcher] pre-run jts.ini contents:"
cat /home/ibgateway/Jts/jts.ini 2>&1 | sed 's/^/[start-with-patcher]   /' || \
  echo "[start-with-patcher]   (no jts.ini yet)"

# IBC's config.ini controls two things we care about:
#
# 1. AcceptIncomingConnectionAction -- when empty (gnzsnz's default),
#    IB Gateway pops a "Accept incoming connection from X.X.X.X?"
#    dialog for every new API client IP and waits for a human click.
#    In a headless container that blocks. Setting "accept" auto-clicks
#    Yes.
#
# 2. TrustedTwsApiClientIPs -- when empty, IBC defaults the gateway's
#    TrustedIPs to just 127.0.0.1, blocking everything from Railway's
#    private network. IBC's own docs say setting this to "0.0.0.0"
#    allows connections from any IP. The wildcard "*" gets validated
#    and rewritten back to 127.0.0.1; "0.0.0.0" is the documented
#    "allow all" sentinel that survives IBC's validation.
#
# gnzsnz writes config.ini at startup from its own template. We patch
# the file in-place after it appears but before gnzsnz exec's IBC.
IBC_INI=/home/ibgateway/ibc/config.ini
_ibc_force_setting() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$IBC_INI"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$IBC_INI"
  else
    echo "${key}=${val}" >> "$IBC_INI"
  fi
  echo "[start-with-patcher] forced ${key}=${val} in $IBC_INI"
}
for _ in {1..30}; do
  if [ -f "$IBC_INI" ]; then
    _ibc_force_setting AcceptIncomingConnectionAction accept
    _ibc_force_setting TrustedTwsApiClientIPs 0.0.0.0
    break
  fi
  sleep 0.2
done

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
