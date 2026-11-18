#!/usr/bin/env bash
PORTS=(3000 5100 5200 5300)

for port in "${PORTS[@]}"; do
  pid=$(lsof -ti :$port 2>/dev/null || true)
  if [ -n "$pid" ]; then
    kill -9 $pid 2>/dev/null || true
    echo "Killed process on port $port (PID: $pid)"
  fi
done

echo "Stopped Sentinel DB demo services on ports 5100, 5200, and 5300."

