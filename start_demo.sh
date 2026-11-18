#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$DIR/data"
mkdir -p "$DATA_DIR"

PYTHON="${PYTHON:-python3}"

PORTS=(3000 5200 5300)
for port in "${PORTS[@]}"; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port $port is already in use. Run ./stop_demo.sh first."
    exit 1
  fi
done

echo "Starting Sentinel DB demo services..."
nohup $PYTHON -u "$DIR/app.py" --port 3000 --role sentinel > "$DATA_DIR/service-3000.log" 2> "$DATA_DIR/service-3000.err" &
nohup $PYTHON -u "$DIR/app.py" --port 5200 --role storefront > "$DATA_DIR/service-5200.log" 2> "$DATA_DIR/service-5200.err" &
nohup $PYTHON -u "$DIR/app.py" --port 5300 --role honeypot > "$DATA_DIR/service-5300.log" 2> "$DATA_DIR/service-5300.err" &

echo "Waiting for services to become healthy..."
DEADLINE=$((SECONDS + 30))
ALL_READY=0

while [ $SECONDS -lt $DEADLINE ]; do
  READY_COUNT=0
  for port in "${PORTS[@]}"; do
    if curl -s -f "http://127.0.0.1:$port/api/health" >/dev/null 2>&1; then
      READY_COUNT=$((READY_COUNT + 1))
    fi
  done
  if [ $READY_COUNT -eq 3 ]; then
    ALL_READY=1
    break
  fi
  sleep 0.5
done

if [ $ALL_READY -ne 1 ]; then
  echo "Failed to start one or more demo services. Check logs in $DATA_DIR."
  exit 1
fi

echo "All three demo services passed their health checks!"
echo "Sentinel analyst dashboard: http://127.0.0.1:3000/"
echo "Normal storefront:           http://127.0.0.1:5200/"
echo "Honeypot decoy:              http://127.0.0.1:5300/"

