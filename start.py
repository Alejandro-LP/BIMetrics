"""Start Flask and Vite together from the BIMetrics project root."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend-bimetrics"
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
POLL_SECONDS = 0.25
SHUTDOWN_TIMEOUT_SECONDS = 8


def find_npm() -> str:
    """Find npm on PATH, including the Windows command shim."""
    candidates = ("npm.cmd", "npm") if os.name == "nt" else ("npm",)
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise FileNotFoundError("npm was not found on PATH. Install Node.js first.")


def process_options() -> dict:
    """Put each server in its own process group for clean shutdown."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def start_process(name: str, command: list[str], cwd: Path) -> subprocess.Popen:
    """Start a server in its project directory without blocking this script."""
    print(f"Starting {name} in {cwd}", flush=True)
    use_shell = os.name == "nt" and command[0].lower().endswith((".cmd", ".bat"))
    return subprocess.Popen(
        command,
        cwd=cwd,
        shell=use_shell,
        **process_options(),
    )


def stop_process(name: str, process: subprocess.Popen) -> None:
    """Stop the server and any child processes it started."""
    if process.poll() is not None:
        return

    print(f"Stopping {name}...", flush=True)
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=SHUTDOWN_TIMEOUT_SECONDS,
            )
        else:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, subprocess.TimeoutExpired):

        pass
    except OSError as error:
        print(f"Could not stop {name}: {error}", file=sys.stderr, flush=True)

    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main() -> int:
    """Validate the project, run both servers, and clean them up on exit."""
    if not (BACKEND_DIR / "run.py").is_file():
        print(f"Backend entry point not found: {BACKEND_DIR / 'run.py'}", file=sys.stderr)
        return 1
    if not (FRONTEND_DIR / "package.json").is_file():
        print(f"Frontend package.json not found: {FRONTEND_DIR / 'package.json'}", file=sys.stderr)
        return 1

    try:
        npm = find_npm()
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1

    processes: list[tuple[str, subprocess.Popen]] = []

    python_executable = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable
    try:
        processes.append((
            "Flask API",
            start_process("Flask API", [python_executable, "run.py"], BACKEND_DIR),
        ))
        processes.append((
            "Vite frontend",
            start_process("Vite frontend", [npm, "run", "dev"], FRONTEND_DIR),
        ))

        print(
            "\nBIMetrics servers are starting:\n"
            "  API:      http://127.0.0.1:5000\n"
            "  Frontend: http://localhost:5173\n"
            "Press Ctrl+C to stop both.\n",
            flush=True,
        )

        while True:
            for name, process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    print(
                        f"{name} exited with code {exit_code}; stopping the other server.",
                        file=sys.stderr,
                        flush=True,
                    )
                    return exit_code or 1
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopping BIMetrics servers...", flush=True)
        return 0
    except OSError as error:
        print(f"Could not start BIMetrics: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        for name, process in reversed(processes):
            stop_process(name, process)


if __name__ == "__main__":
    raise SystemExit(main())
