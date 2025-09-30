#!/bin/bash

echo "Removing prior PID file"
rm -f /var/run/monit.pid

env > /opt/monit/scripts/.env

exec "$@"
