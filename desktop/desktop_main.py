"""
Desktop entry point. Starts the existing FastAPI backend in a background thread,
then opens a native OS window pointed at it using pywebview.

This file does not duplicate any backend logic — it imports and runs the exact
same `app` object that `uvicorn app.main:app` runs for the web app.
"""

import logging
import os
import socket
import sys
import threading
import time

import uvicorn
import webview

# Configure logging for desktop application debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("desktop_main")

if not getattr(sys, "frozen", False):
    _BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
    if os.path.isdir(_BACKEND_DIR):
        sys.path.insert(0, _BACKEND_DIR)

from app.main import app  # noqa: E402  (import after sys.path change is intentional)


def show_error_dialog(title: str, message: str) -> None:
    """Show a native GUI error popup on Windows if startup fails."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # 0x10 = MB_ICONERROR
    except Exception:
        print(f"[{title}] {message}", file=sys.stderr)


def find_available_port(default_port: int = 8000) -> int:
    """Try default port 8000 first; if occupied, ask OS for any free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", default_port))
            return default_port
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(server: uvicorn.Server):
    """Runs the FastAPI app. This function blocks, so it must run on its own thread."""
    try:
        server.run()
    except Exception as exc:
        logger.error("Backend server crashed: %s", exc, exc_info=True)
        show_error_dialog("Job Aggregator Server Error", f"Backend server crashed:\n\n{exc}")


def _wait_for_server(server: uvicorn.Server, server_thread: threading.Thread, port: int) -> None:
    """Wait until Uvicorn has completed startup before loading the desktop window."""
    deadline = time.monotonic() + 15
    while not server.started and server_thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)

    if not server.started:
        raise RuntimeError(f"Job Aggregator backend failed to bind/start on http://127.0.0.1:{port}")


def main():
    try:
        port = find_available_port(8000)
        logger.info("Starting backend server on http://127.0.0.1:%d", port)

        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        )
        server_thread = threading.Thread(target=_start_server, args=(server,), daemon=True)
        server_thread.start()
        _wait_for_server(server, server_thread, port)

        logger.info("Backend server successfully started on http://127.0.0.1:%d", port)

        window = webview.create_window(
            title="Job Aggregator (Desktop Debug)",
            url=f"http://127.0.0.1:{port}",
            width=1280,
            height=800,
            min_size=(1024, 700),
        )

        logger.info("Starting PyWebview window with debug=True...")
        try:
            # debug=True enables F12 / Right-click Developer Tools / Inspect Element
            webview.start(debug=True)
        finally:
            server.should_exit = True
    except Exception as exc:
        logger.error("Could not start Job Aggregator: %s", exc, exc_info=True)
        show_error_dialog("Job Aggregator Launch Error", f"Could not start Job Aggregator:\n\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
