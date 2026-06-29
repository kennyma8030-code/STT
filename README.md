# stt-bot

Push-to-talk speech-to-text. Hold a key to talk, release to transcribe, and the
text is sent to a Discord channel (via webhook) and shown in a small web control
panel.

- **Backend** — FastAPI (`main.py`), runs Whisper locally via RealtimeSTT.
- **Frontend** — a Vite web UI (`frontend/`) to pick the model and start/stop a session.

## Prerequisites

Install these once, system-wide:

- [Python 3](https://www.python.org/downloads/) (3.10+), with "Add to PATH" checked
- [Node.js](https://nodejs.org/) (18+)

## Setup (one time)

Double-click **`setup.bat`**, or from a terminal:

```bat
setup.bat
```

This creates the Python virtual environment, installs the Python and frontend
dependencies, and creates a `.env` file. Then open `.env` and paste your Discord
webhook URL:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

(In Discord: **Server Settings → Integrations → Webhooks → New Webhook → Copy URL**.)

## Running

Double-click **`start.bat`**.

That starts the backend and the web UI together and opens the browser at
http://localhost:5173. Pick a model, click start, then hold **F9** to talk and
press **Esc** to quit the session.

> Under the hood `start.bat` just runs `npm run dev` inside `frontend/`, which
> uses `concurrently` to launch both `main.py` (backend) and Vite (frontend).

### Other ways to run

- **Terminal:** `cd frontend && npm run dev`
- **No web UI (CLI only):** `venv\Scripts\python.exe cli.py` — push-to-talk
  straight to Discord, no browser. Pass a model name, e.g. `cli.py small.en`.

## First run note

The first time you start a session with a given model, RealtimeSTT downloads the
Whisper model, so it takes a bit longer. After that it's cached.
