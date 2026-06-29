import "./style.css";

const API = "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);
const modelSel = $("model");
const startBtn = $("start");
const stopBtn = $("stop");
const pttBtn = $("ptt");
const quitBtn = $("quit");
const dot = $("dot");
const statusText = $("statusText");
const hint = $("hint");
const lines = $("lines");
const empty = $("empty");
const deviceTag = $("device");
const config = $("config");
const shutdownBtn = $("shutdown");
const themeBtn = $("theme");

let recording = false;
let es = null; // the SSE connection, so we can close it on shutdown

// ── Theme (persisted in localStorage; applied pre-paint in index.html) ──
function applyTheme(theme) {
  const light = theme === "light";
  document.documentElement.classList.toggle("light", light);
  themeBtn.textContent = light ? "DARK" : "LIGHT"; // label = the mode you'd switch to
}
applyTheme(localStorage.getItem("theme") || "dark");
themeBtn.addEventListener("click", () => {
  const next = document.documentElement.classList.contains("light") ? "dark" : "light";
  localStorage.setItem("theme", next);
  applyTheme(next);
});

// ── Click-to-rebind a key ───────────────────────────────────────────────────
function keyName(e) {
  if (e.key === "Escape") return "esc";
  if (e.key === " ") return "space";
  if (e.key === "Enter") return "enter";
  if (e.key === "Tab") return "tab";
  if (/^F\d{1,2}$/.test(e.key)) return e.key.toLowerCase(); // F1–F12
  if (e.key.length === 1) return e.key.toLowerCase();
  return null;
}

function bindCapture(btn) {
  btn.addEventListener("click", () => {
    btn.classList.add("listening");
    btn.textContent = "press a key…";
    const handler = (e) => {
      e.preventDefault();
      const name = keyName(e);
      if (name) {
        btn.dataset.key = name;
        btn.textContent = name.toUpperCase();
      } else {
        btn.textContent = btn.dataset.key.toUpperCase();
      }
      btn.classList.remove("listening");
      window.removeEventListener("keydown", handler, true);
    };
    window.addEventListener("keydown", handler, true);
  });
}
bindCapture(pttBtn);
bindCapture(quitBtn);

// ── Status helpers ───────────────────────────────────────────────────────────
const LABELS = {
  idle: "Idle",
  loading: "Loading model…",
  ready: "Ready",
  recording: "Recording",
  stopped: "Stopped",
  error: "Error",
};

function setStatus(state) {
  dot.className = "dot " + state;
  statusText.textContent = LABELS[state] || state;
}

function sessionActive(active) {
  startBtn.hidden = active;
  stopBtn.hidden = !active;
  config.classList.toggle("locked", active);
}

function addLine(text) {
  empty.hidden = true;
  const li = document.createElement("li");
  const t = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const time = document.createElement("time");
  time.textContent = t;
  const span = document.createElement("span");
  span.textContent = text; // textContent = safe, no HTML injection
  li.append(time, span);
  lines.appendChild(li);
  lines.scrollTop = lines.scrollHeight;
}

// ── Load models ──────────────────────────────────────────────────────────────
async function loadModels() {
  try {
    const r = await fetch(`${API}/models`);
    const { models, device } = await r.json();
    modelSel.innerHTML = "";
    for (const m of models) {
      const o = document.createElement("option");
      o.value = m;
      o.textContent = m;
      modelSel.appendChild(o);
    }
    if (models.includes("small.en")) modelSel.value = "small.en"; // default model
    deviceTag.textContent = device.toUpperCase();
    deviceTag.classList.toggle("warn", device === "cpu");
  } catch {
    deviceTag.textContent = "backend offline";
    deviceTag.classList.add("warn");
  }
}

// ── SSE stream ───────────────────────────────────────────────────────────────
function connect() {
  es = new EventSource(`${API}/stream`);

  es.addEventListener("status", (e) => {
    const d = JSON.parse(e.data);
    if (d.status === "ready" || d.status === "recording" || d.status === "loading") {
      setStatus(recording ? "recording" : d.status);
      sessionActive(true);
    } else {
      setStatus(d.status);
      sessionActive(false);
    }
  });

  es.addEventListener("ready", (e) => {
    const d = JSON.parse(e.data);
    setStatus("ready");
    hint.textContent = `Hold ${d.ptt_key.toUpperCase()} to talk · ${d.quit_key.toUpperCase()} to quit`;
    sessionActive(true);
  });

  es.addEventListener("recording", (e) => {
    recording = JSON.parse(e.data).recording;
    setStatus(recording ? "recording" : "ready");
  });

  es.addEventListener("text", (e) => addLine(JSON.parse(e.data).text));

  es.addEventListener("warn", (e) => {
    hint.textContent = "Warning: " + JSON.parse(e.data).message;
  });

  es.onopen = () => loadModels(); // refresh device tag once connected
  es.onerror = () => {
    deviceTag.textContent = "reconnecting…";
    deviceTag.classList.add("warn");
  };
}

// ── Actions ──────────────────────────────────────────────────────────────────
startBtn.addEventListener("click", async () => {
  setStatus("loading");
  hint.textContent = "Loading model… first run downloads it.";
  startBtn.disabled = true;
  try {
    await fetch(`${API}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: modelSel.value,
        ptt_key: pttBtn.dataset.key,
        quit_key: quitBtn.dataset.key,
      }),
    });
  } catch {
    setStatus("error");
    hint.textContent = "Could not reach backend on :8000";
  } finally {
    startBtn.disabled = false;
  }
});

stopBtn.addEventListener("click", () => {
  fetch(`${API}/stop`, { method: "POST" }).catch(() => {});
});

shutdownBtn.addEventListener("click", async () => {
  shutdownBtn.disabled = true;
  shutdownBtn.textContent = "SHUTTING DOWN…";
  try {
    const res = await fetch(`${API}/shutdown`, { method: "POST" });
    if (!res.ok) {
      // server answered but rejected it (e.g. 404 = backend predates /shutdown)
      shutdownBtn.disabled = false;
      shutdownBtn.textContent = "SHUT DOWN SERVERS";
      hint.textContent = `Shutdown failed (HTTP ${res.status}). Restart the backend so it has /shutdown.`;
      return;
    }
  } catch {
    // connection dropped as the server exited — that's the success signal
  }
  if (es) es.close(); // stop SSE auto-reconnect attempts
  setStatus("stopped");
  sessionActive(false);
  startBtn.disabled = true;
  deviceTag.textContent = "offline";
  deviceTag.classList.add("warn");
  hint.textContent = "Servers stopped. Restart with `npm run dev`.";
  shutdownBtn.textContent = "SERVERS STOPPED";
});

loadModels();
connect();
