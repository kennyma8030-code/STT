#!/usr/bin/env bash
# Launch the STT app (backend + frontend together) on macOS/Linux.
# Runs `npm run dev` in frontend/, which starts main.py (backend) + Vite (frontend).
set -e
cd "$(dirname "$0")/frontend"

if [ ! -d node_modules ]; then
  echo "node_modules not found. Run ./setup.sh first."
  exit 1
fi

npm run dev
