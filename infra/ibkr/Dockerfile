# syntax=docker/dockerfile:1.6
# IBKR Gateway + IBC (IB Controller) — paper trading only.
#
# The simplest path is to inherit from the community ibcalpha/ibc image, which
# already bundles the gateway and IBC. If that image is not available in your
# registry mirror, comment out the FROM line and uncomment the openjdk-based
# fallback further down — and accept IBKR's terms manually before building.
#
# IMPORTANT: by building/running this image you accept Interactive Brokers'
# software license terms (https://www.interactivebrokers.com/en/index.php?f=14099).

ARG IBC_BASE=ibcalpha/ibc:latest
FROM ${IBC_BASE} AS ibc-base

# ---------------------------------------------------------------------------
# Fallback build (uncomment if ibcalpha/ibc is not reachable):
#
# FROM openjdk:17-slim AS ibc-base
# ENV IBC_VERSION=3.20.0 \
#     TWS_MAJOR=1030 \
#     IBC_HOME=/opt/ibc \
#     TWS_HOME=/opt/tws
# RUN apt-get update \
#  && apt-get install -y --no-install-recommends curl unzip xvfb libxtst6 libxrender1 socat netcat-openbsd \
#  && rm -rf /var/lib/apt/lists/* \
#  && mkdir -p ${IBC_HOME} ${TWS_HOME}
# # The user must download the gateway installer + IBC zip themselves and place
# # them under infra/ibkr/vendor/ before building. See infra/ibkr/README.md.
# COPY vendor/ibgateway-stable.sh /tmp/ibgateway.sh
# COPY vendor/IBCLinux.zip       /tmp/IBCLinux.zip
# RUN bash /tmp/ibgateway.sh -q -dir ${TWS_HOME} \
#  && unzip -d ${IBC_HOME} /tmp/IBCLinux.zip \
#  && rm /tmp/ibgateway.sh /tmp/IBCLinux.zip
# ---------------------------------------------------------------------------

# Install netcat for healthcheck (busybox `nc` is already in many bases but we
# pin it explicitly for the slim variant).
USER root
RUN (command -v nc >/dev/null 2>&1) \
 || (apt-get update \
     && apt-get install -y --no-install-recommends netcat-openbsd \
     && rm -rf /var/lib/apt/lists/*)

# Paper-trading port. We deliberately do NOT expose 7496 (live).
EXPOSE 7497

# Required envs (the entrypoint script refuses to start otherwise).
ENV TWS_USERID="" \
    TWS_PASSWORD="" \
    TRADING_MODE="paper"

# Templates filled in at runtime by the entrypoint.
COPY infra/ibkr/jts.ini.template       /opt/ibc-templates/jts.ini.template
COPY infra/ibkr/ibc-config.ini.template /opt/ibc-templates/ibc-config.ini.template

# Hard guard against running against a live account. We grep TRADING_MODE
# for the literal string "live" and refuse to start if found. The grep is
# deliberately permissive ("live", "Live", "LIVE") so a typo never reaches IBKR.
COPY <<'EOF' /opt/ibc-templates/entrypoint.sh
#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TWS_USERID:-}" || -z "${TWS_PASSWORD:-}" ]]; then
  echo "FATAL: TWS_USERID and TWS_PASSWORD must be set in the environment" >&2
  exit 64
fi

mode_lc="$(printf '%s' "${TRADING_MODE:-}" | tr '[:upper:]' '[:lower:]')"
if [[ "$mode_lc" != "paper" ]]; then
  echo "FATAL: TRADING_MODE must be exactly 'paper'; got '${TRADING_MODE:-<empty>}'" >&2
  echo "       This image refuses to launch against a live IBKR account." >&2
  exit 65
fi
if printf '%s' "$mode_lc" | grep -qi 'live'; then
  echo "FATAL: TRADING_MODE contains 'live' — refusing to start" >&2
  exit 65
fi

# Render templates with envsubst-style substitution (bash only).
render() {
  local src="$1" dst="$2"
  python3 - "$src" "$dst" <<'PY'
import os, sys, string
src, dst = sys.argv[1], sys.argv[2]
with open(src) as fh:
    rendered = string.Template(fh.read()).safe_substitute(os.environ)
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w") as fh:
    fh.write(rendered)
PY
}

mkdir -p /root/Jts /root/ibc
render /opt/ibc-templates/jts.ini.template        /root/Jts/jts.ini
render /opt/ibc-templates/ibc-config.ini.template /root/ibc/config.ini

# Defer to the upstream IBC entrypoint if present, otherwise fall back to
# whatever the base image's CMD was.
if [[ -x /opt/ibc/scripts/ibcstart.sh ]]; then
  exec /opt/ibc/scripts/ibcstart.sh
elif [[ -x /usr/local/bin/start.sh ]]; then
  exec /usr/local/bin/start.sh
else
  echo "FATAL: no IBC entrypoint found in the base image" >&2
  exit 70
fi
EOF
RUN chmod +x /opt/ibc-templates/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD nc -z localhost 7497 || exit 1

ENTRYPOINT ["/opt/ibc-templates/entrypoint.sh"]
