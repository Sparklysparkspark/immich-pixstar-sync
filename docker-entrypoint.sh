#!/bin/sh
set -e

# Copy config files from /config (mounted volume) into /app
# so the app sees them exactly like the non-Docker version.

if [ -f /config/.env ]; then
  echo "Using /config/.env"
  cp /config/.env /app/.env
fi

if [ -f /config/pixstar_mapping.json ]; then
  echo "Using /config/pixstar_mapping.json"
  cp /config/pixstar_mapping.json /app/pixstar_mapping.json
fi

echo "Starting Immich → Pix-Star sync..."
exec "$@"
