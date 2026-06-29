// Cross-platform launcher for the FastAPI backend.
// Picks the right venv Python for the OS and runs main.py from the project root.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url)); // .../frontend
const root = join(here, ".."); // project root (where main.py + venv live)

const python =
  process.platform === "win32"
    ? join(root, "venv", "Scripts", "python.exe")
    : join(root, "venv", "bin", "python");

const child = spawn(python, [join(root, "main.py")], {
  cwd: root,
  stdio: "inherit",
});

// Make sure the Python process dies with us (e.g. when concurrently -k fires).
const forward = (sig) => {
  if (!child.killed) child.kill(sig);
};
process.on("SIGTERM", () => forward("SIGTERM"));
process.on("SIGINT", () => forward("SIGINT"));

child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (err) => {
  console.error(`Failed to start backend Python at ${python}\n${err.message}`);
  process.exit(1);
});
