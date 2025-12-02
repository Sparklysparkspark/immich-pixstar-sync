#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/immich-pixstar.pid"

echo "[stop.sh] Stopping immich-pixstar-sync..."

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "[stop.sh] Sent SIGTERM to PID $PID"
    # Optional: wait a bit, then force kill if still alive
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
      echo "[stop.sh] PID $PID still running, sending SIGKILL..."
      kill -9 "$PID"
    fi
  else
    echo "[stop.sh] No running process found for PID $PID (already stopped?)"
  fi
  rm -f "$PID_FILE"
else
  echo "[stop.sh] No PID file found at $PID_FILE"
  echo "[stop.sh] Trying fallback kill by name..."
  # Fallback: kill any "python main.py" processes if this is the only one
  pkill -f "python main.py" 2>/dev/null || true
fi

echo "[stop.sh] Done."
