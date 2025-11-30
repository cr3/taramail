#!/bin/sh
set -e

# Substitute environment variables in the config template
TEMPLATE=/etc/blackbox_exporter/config.yml.template
if [ -e "${TEMPLATE}" ]; then
  envsubst < ${TEMPLATE} > /etc/blackbox_exporter/config.yml
fi

# Start blackbox exporter with the processed config
exec /bin/blackbox_exporter "$@"
