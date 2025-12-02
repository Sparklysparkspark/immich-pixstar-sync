#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/immich-pixstar.pid"

echo "[run.sh] Starting immich-pixstar-sync..."

# Activate venv if present
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# Run in background so it survives terminal/SSH close.
# No need to redirect logs – Python handles logging to file.
nohup python main.py >/dev/null 2>&1 &

PID=$!
echo "$PID" > "$PID_FILE"

echo "[run.sh] Started with PID $PID"
echo "[run.sh] You can close this terminal; the process will keep running."
