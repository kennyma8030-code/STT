#!/usr/bin/env bash
# One-time setup (macOS/Linux): creates the Python venv, installs Python + Node
# deps, and seeds a .env file. Re-running it is safe.
set -e
cd "$(dirname "$0")"

echo "============================================"
echo " 1/4  System audio dependency (PortAudio)"
echo "============================================"
if [[ "$OSTYPE" == darwin* ]]; then
  if command -v brew >/dev/null 2>&1; then
    if ! brew list portaudio >/dev/null 2>&1; then
      echo "Installing portaudio (required by PyAudio)..."
      brew install portaudio
    else
      echo "portaudio already installed."
    fi
  else
    echo "Homebrew not found. Install it (https://brew.sh) then: brew install portaudio"
    exit 1
  fi
else
  echo "Non-macOS: ensure PortAudio dev headers are installed (e.g. 'sudo apt install portaudio19-dev')."
fi

echo
echo "============================================"
echo " 2/4  Creating Python virtual environment"
echo "============================================"
if [ ! -d venv ]; then
  python3 -m venv venv
else
  echo "venv already exists, skipping."
fi

echo
echo "============================================"
echo " 3/4  Installing dependencies"
echo "============================================"
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt
( cd frontend && npm install )

echo
echo "============================================"
echo " 4/4  Setting up .env"
echo "============================================"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env -- edit it and paste your Discord webhook URL."
else
  echo ".env already exists, leaving it alone."
fi

echo
echo "Done! Edit .env if you haven't, then run ./start.sh"
echo "macOS: also grant your terminal Accessibility access (System Settings ->"
echo "Privacy & Security -> Accessibility) so the global hotkey works."
