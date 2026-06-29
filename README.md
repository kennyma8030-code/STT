# stt-bot

Push-to-talk speech-to-text. Hold a key to talk, release to transcribe, and the
text is sent to a Discord channel (via webhook) and shown in a web control panel.

- **Backend** — FastAPI (`main.py`), runs Whisper locally via RealtimeSTT. Listens
  for the global push-to-talk key, transcribes, posts to Discord, and streams
  results to the UI over SSE. Serves on `http://127.0.0.1:8000`.
- **Frontend** — a Vite web UI (`frontend/`) to pick the model, set the keybinding,
  start/stop a session, and watch the live transcript (dark/light mode). Serves on
  `http://localhost:5173`.

`npm run dev` (in `frontend/`) starts **both** together via `concurrently`; the
launcher `frontend/start-api.mjs` runs the backend with the correct venv Python
for your OS, so the same command works on Windows, macOS, and Linux.

## Prerequisites

Install these once, system-wide:

- [Python 3](https://www.python.org/downloads/) (3.10+), on PATH
- [Node.js](https://nodejs.org/) (18+)
- **macOS only:** [Homebrew](https://brew.sh) (used to install PortAudio for PyAudio)

## Setup (one time)

### Windows

Double-click **`setup.bat`**, or run it from a terminal. It creates the venv,
installs Python + frontend deps, and seeds `.env`.

### macOS / Linux

```bash
bash setup.sh
```

It installs PortAudio (macOS, via Homebrew), creates the venv, installs Python +
frontend deps, and seeds `.env`.

### Then: add your webhook

Open `.env` and paste your Discord webhook URL:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

(In Discord: **Server Settings → Integrations → Webhooks → New Webhook → Copy URL**.)

### macOS extra step — Accessibility

The push-to-talk key uses a system-wide keyboard hook. Grant your terminal app
access under **System Settings → Privacy & Security → Accessibility**, or the key
won't be captured. Also note **F9** may be intercepted by macOS unless "Use F1,
F2, etc. as standard function keys" is on — or just rebind the key in the UI.

## Running

- **Windows:** double-click **`start.bat`**
- **macOS / Linux:** `bash start.sh`
- **Any OS, from a terminal:** `cd frontend && npm run dev`

This starts the backend and web UI together and opens the browser at
http://localhost:5173. Pick a model, click **Start session**, then hold **F9** to
talk and release to transcribe. **Esc** ends the session; **Shut down servers**
stops both servers.

## Notes

- **First run** with a given model downloads the Whisper weights, so it takes
  longer; after that it's cached.
- **Device:** auto-detected — CUDA (`float16`) only if an NVIDIA GPU is present,
  otherwise CPU (`int8`). Macs and AMD GPUs run on CPU (ctranslate2 has no
  Apple-GPU/ROCm support). Smaller models (`tiny.en`) are much faster on CPU.
- **No auto-reload:** the backend runs without `--reload` (RealtimeSTT uses
  multiprocessing). After editing `main.py`, restart. Frontend edits hot-reload.
- **The venv is not portable** across operating systems — run the setup steps on
  each machine.
