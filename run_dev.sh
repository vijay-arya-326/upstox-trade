#!/usr/bin/env bash
# Run both backend (Python API, :8000) and frontend (Vite React, :5173).
# Usage:
#   ./run_dev.sh          # dev: backend + vite hot-reload (needs npm deps)
#   ./run_dev.sh --prod   # prod: build frontend bundle, serve via backend only
set -euo pipefail
cd "$(dirname "$0")"

BACKEND_PORT="${WEB_PORT:-8000}"
MODE="${1:-dev}"

if [[ ! -d .venv ]]; then
  echo "error: .venv not found. Run 'uv sync' first." >&2
  exit 1
fi

if [[ "$MODE" == "--prod" ]]; then
  echo "==> building frontend bundle..."
  (cd frontend && npm install --no-audit --no-fund && npm run build)
  echo "==> serving production build at http://127.0.0.1:${BACKEND_PORT}"
  exec .venv/bin/python run_web.py
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "==> installing frontend deps..."
  (cd frontend && npm install --no-audit --no-fund)
fi

echo "==> backend  : http://127.0.0.1:${BACKEND_PORT}  (API + prod bundle)"
echo "==> frontend : http://127.0.0.1:5173  (vite dev, proxies /api)"
echo "    press Ctrl+C to stop both"

.venv/bin/python run_web.py &
BACK_PID=$!
(cd frontend && npm run dev -- --host 127.0.0.1) &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null; wait 2>/dev/null' INT TERM
wait
