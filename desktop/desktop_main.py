"""
Desktop entry point. Starts the existing FastAPI backend in a background thread,
then opens a native OS window pointed at it using pywebview.

This file does not duplicate any backend logic — it imports and runs the exact
same `app` object that `uvicorn app.main:app` runs for the web app.
"""

import os
import sys
import threading

import uvicorn
import webview

# Make backend/app importable regardless of the current working directory this
# script is launched from.
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, _BACKEND_DIR)

from app.main import app  # noqa: E402  (import after sys.path change is intentional)


def _start_server():
    """Runs the FastAPI app. This function blocks, so it must run on its own thread,
    not on the main thread (the main thread is needed for the webview window)."""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    window = webview.create_window(
        title="Job Aggregator",
        url="http://127.0.0.1:8000",
        width=1280,
        height=800,
        min_size=(1024, 700),
    )
    webview.start()  # blocks the main thread until the window is closed


if __name__ == "__main__":
    main()
