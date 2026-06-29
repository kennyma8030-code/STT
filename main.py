"""FastAPI backend for the STT control panel.

Endpoints
  GET  /models   -> available models + detected device
  GET  /status   -> current session state
  POST /start    {model, ptt_key, quit_key} -> load model, start global PTT listener
  POST /stop     -> stop the listener / end the session
  GET  /stream   -> SSE: status / ready / recording / text / warn events

Each transcription is sent to BOTH:
  - Discord, via bot.send_message() (webhook HTTP POST), and
  - the frontend, via the SSE /stream channel.

Run (no --reload; RealtimeSTT uses multiprocessing):
    uvicorn main:app
  or
    python main.py
"""

import asyncio
import json
import multiprocessing
import os
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pynput import keyboard

from bot import send_message

# ── Device auto-detect: CUDA if an NVIDIA GPU is visible, else CPU ──────────
try:
    import ctranslate2
    _HAS_CUDA = ctranslate2.get_cuda_device_count() > 0
except Exception:
    _HAS_CUDA = False

DEVICE = "cuda" if _HAS_CUDA else "cpu"
COMPUTE_TYPE = "float16" if _HAS_CUDA else "int8"

AVAILABLE_MODELS = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3"]

# ── Shared state between the pynput thread and the asyncio event loop ───────
_loop: Optional[asyncio.AbstractEventLoop] = None
_events: "asyncio.Queue[dict]" = asyncio.Queue()
_recorder = None
_listener: Optional[keyboard.Listener] = None
_worker: Optional[threading.Thread] = None
_recording = False
_state = {"status": "idle", "model": None, "device": DEVICE}
_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop
    _loop = asyncio.get_running_loop()  # the listener thread hands events to this loop
    yield


app = FastAPI(title="STT Control Panel", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    model: str = "small.en"
    ptt_key: str = "f9"
    quit_key: str = "esc"


def _emit(event: str, **data) -> None:
    """Push an SSE event onto the asyncio queue from ANY thread, safely."""
    if _loop is None:
        return
    _loop.call_soon_threadsafe(_events.put_nowait, {"event": event, **data})


def _parse_key(name: str):
    """Map 'f9' / 'esc' / 'space' / 'a' to a pynput key object."""
    name = (name or "").strip().lower()
    if hasattr(keyboard.Key, name):          # special keys: f9, esc, space, ...
        return getattr(keyboard.Key, name)
    if len(name) == 1:                        # printable single character
        return keyboard.KeyCode.from_char(name)
    raise ValueError(f"Unrecognized key: {name!r}")


def _run_session(model: str, ptt_key: str, quit_key: str) -> None:
    """Background thread: load the model, then listen for the PTT key globally."""
    global _recorder, _listener, _recording
    from RealtimeSTT import AudioToTextRecorder

    _state.update(status="loading", model=model, device=DEVICE)
    _emit("status", status="loading", model=model, device=DEVICE)

    try:
        ptt = _parse_key(ptt_key)
        quit_key_obj = _parse_key(quit_key)
    except ValueError as e:
        _state.update(status="error")
        _emit("warn", message=str(e))
        _emit("status", status="idle")
        _state.update(status="idle")
        return

    try:
        _recorder = AudioToTextRecorder(
            model=model,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            use_microphone=True,
            spinner=False,
            enable_realtime_transcription=False,
        )
    except Exception as e:
        _state.update(status="idle", model=None)
        _emit("warn", message=f"Failed to load model: {e}")
        _emit("status", status="idle")
        return

    _state.update(status="ready")
    _emit("ready", model=model, ptt_key=ptt_key, quit_key=quit_key)

    def on_press(key):
        global _recording
        if key == ptt and not _recording:
            _recording = True
            _emit("recording", recording=True)
            _recorder.start()

    def on_release(key):
        global _recording
        if key == ptt and _recording:
            _recording = False
            _emit("recording", recording=False)
            _recorder.stop()
            text = _recorder.text()
            if text:
                try:
                    send_message(text)            # ─► Discord (webhook POST)
                except Exception as e:
                    _emit("warn", message=f"Discord send failed: {e}")
                _emit("text", text=text)          # ─► frontend (SSE)
        elif key == quit_key_obj:
            return False                           # stops the listener

    _listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    _listener.start()
    _listener.join()  # blocks until the quit key is pressed or stop() is called

    try:
        _recorder.shutdown()
    except Exception:
        pass
    _recorder = None
    _recording = False
    _state.update(status="idle", model=None)
    _emit("status", status="idle")


@app.get("/models")
async def models():
    return {"models": AVAILABLE_MODELS, "device": DEVICE}


@app.get("/status")
async def status():
    return {**_state, "recording": _recording}


@app.post("/start")
async def start(req: StartRequest):
    global _worker
    with _lock:
        if _state["status"] in ("loading", "ready"):
            return {"status": _state["status"], "detail": "session already active"}
        if req.model not in AVAILABLE_MODELS:
            return {"status": "error", "detail": f"unknown model {req.model}"}
        _worker = threading.Thread(
            target=_run_session,
            args=(req.model, req.ptt_key, req.quit_key),
            daemon=True,
        )
        _worker.start()
    return {"status": "starting", "model": req.model, "device": DEVICE}


@app.post("/stop")
async def stop():
    if _listener is not None:
        _listener.stop()  # makes join() return -> triggers cleanup
    return {"status": "stopping"}


@app.post("/shutdown")
async def shutdown():
    """End the whole stack: clean up, then exit the process. Because the dev
    launcher runs both servers under `concurrently -k`, exiting the backend
    also takes the Vite frontend down with it."""

    def _die():
        try:
            if _listener is not None:
                _listener.stop()
        except Exception:
            pass
        try:
            if _recorder is not None:
                _recorder.shutdown()
        except Exception:
            pass
        os._exit(0)

    threading.Timer(0.4, _die).start()  # let the HTTP response flush first
    return {"status": "shutting down"}


def _sse(obj: dict) -> str:
    event = obj.get("event", "message")
    return f"event: {event}\ndata: {json.dumps(obj)}\n\n"


@app.get("/stream")
async def stream():
    async def event_gen():
        # greet a freshly connected client with the current state
        yield _sse({"event": "status", **_state, "recording": _recording})
        while True:
            try:
                item = await asyncio.wait_for(_events.get(), timeout=15)
                yield _sse(item)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # keep-alive comment so proxies don't drop us

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# Only auto-launch the embedded dev server when this file is run directly
# (`python main.py`) in the MAIN process. A real server importing the app
# (`uvicorn main:app`, gunicorn, ...) has __name__ != "__main__", and spawned
# multiprocessing workers have a parent process — both skip this block.
if __name__ == "__main__" and multiprocessing.parent_process() is None:
    multiprocessing.freeze_support()
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
