#!/bin/sh

until ping taramail-sogo -c1 > /dev/null; do
  echo "Waiting for SOGo..."
  sleep 1
done
until ping taramail-rspamd -c1 > /dev/null; do
  echo "Waiting for Rspamd..."
  sleep 1
done

python3 /bootstrap.py

exec "$@"
