"""
Desktop entry point. Starts the existing FastAPI backend in a background thread,
then opens a native OS window pointed at it using pywebview.

This file does not duplicate any backend logic — it imports and runs the exact
same `app` object that `uvicorn app.main:app` runs for the web app.

SHUTDOWN BEHAVIOR: closing the window is the only "quit" a user has for a
webview-based desktop app, so it must be a guaranteed full stop — not a
best-effort one. main() always routes through _shutdown() on every exit path
(normal close or a startup exception), which signals uvicorn to stop, gives it
a short window to shut down its sockets cleanly, and then calls os._exit() to
force the whole process to terminate immediately regardless of any thread or
handle that didn't clean up in time. Without the os._exit() call, it's
possible for the Python process (and anything it's holding open) to keep
running invisibly in the background after the window disappears.
"""

import logging
import os
import socket
import sys
import threading
import time

import uvicorn
import webview


def is_debug_mode() -> bool:
    """Check if debug mode (DevTools / Console log) is explicitly enabled."""
    if "--debug" in sys.argv or "-d" in sys.argv:
        return True
    if os.environ.get("JOB_AGGREGATOR_DEBUG") == "1":
        return True

    # Check for debug_mode.flag in the installation directory
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    if os.path.exists(os.path.join(exe_dir, "debug_mode.flag")):
        return True
    return False


DEBUG_ENABLED = is_debug_mode()

# Configure logging for desktop application
logging.basicConfig(
    level=logging.DEBUG if DEBUG_ENABLED else logging.INFO,
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


def _shutdown(server: uvicorn.Server | None, server_thread: threading.Thread | None, exit_code: int = 0, timeout: float = 5.0) -> None:
    """
    Best-effort graceful shutdown, followed by an unconditional hard process
    exit, so the app is guaranteed to fully terminate the moment the window
    closes — no lingering backend thread, no leftover process still sitting
    in Task Manager.
    """
    if server is not None:
        logger.info("Signaling backend server to stop...")
        server.should_exit = True

    if server_thread is not None and server_thread.is_alive():
        server_thread.join(timeout=timeout)
        if server_thread.is_alive():
            logger.warning(
                "Backend server did not stop within %.1fs — forcing full exit anyway.", timeout
            )

    logger.info("Job Aggregator shutting down.")
    logging.shutdown()

    # os._exit() terminates this process immediately and unconditionally,
    # including any thread that ignored should_exit or the join timeout
    # above. A normal sys.exit()/return here is not enough to guarantee
    # this — os._exit() is the deliberate, blunt tool that makes "closed
    # the window" actually mean "the app is gone," every time.
    os._exit(exit_code)


def main():
    server: uvicorn.Server | None = None
    server_thread: threading.Thread | None = None
    exit_code = 0

    try:
        port = find_available_port(8000)
        logger.info("Starting backend server on http://127.0.0.1:%d", port)

        log_lvl = "debug" if DEBUG_ENABLED else "info"
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level=log_lvl)
        )
        server_thread = threading.Thread(target=_start_server, args=(server,), daemon=True)
        server_thread.start()
        _wait_for_server(server, server_thread, port)

        logger.info("Backend server successfully started on http://127.0.0.1:%d", port)

        window_title = "Job Aggregator" + (" (Debug Mode)" if DEBUG_ENABLED else "")
        window = webview.create_window(
            title=window_title,
            url=f"http://127.0.0.1:{port}",
            width=1280,
            height=800,
            min_size=(1024, 700),
        )

        # Fires as soon as the user clicks the window's close button, before
        # webview.start() returns — gives an explicit, early signal into the
        # log that a deliberate shutdown (not a crash) is starting.
        window.events.closing += lambda: logger.info("Window closing — shutting down Job Aggregator...")

        logger.info("Starting PyWebview window with debug=%s...", DEBUG_ENABLED)
        # debug=True enables F12 / Right-click Developer Tools / Inspect Element
        webview.start(debug=DEBUG_ENABLED)

    except Exception as exc:
        logger.error("Could not start Job Aggregator: %s", exc, exc_info=True)
        show_error_dialog("Job Aggregator Launch Error", f"Could not start Job Aggregator:\n\n{exc}")
        exit_code = 1
    finally:
        # Runs on every exit path — a clean window close, or a startup
        # exception above. This is what guarantees the process (and the
        # backend thread inside it) never keeps running after this point.
        _shutdown(server, server_thread, exit_code=exit_code)


if __name__ == "__main__":
    main()