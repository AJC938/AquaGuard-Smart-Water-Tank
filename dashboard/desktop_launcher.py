"""Launch the Streamlit dashboard inside a standalone Windows app window."""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

import webview


PROJECT_DIR = Path(__file__).resolve().parent


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until_ready(process: subprocess.Popen, url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"AquaGuard dashboard server stopped early (exit code {process.returncode}).")
        try:
            with urlopen(f"{url}/_stcore/health", timeout=1.0) as response:
                if response.status == 200 and response.read().strip() == b"ok":
                    return
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError("AquaGuard did not finish starting within 45 seconds.")


def main() -> int:
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    log_path = Path(tempfile.gettempdir()) / "AquaGuard_Dashboard.log"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("a", encoding="utf-8") as log_file:
        server = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", str(PROJECT_DIR / "app.py"),
                "--server.headless=true", "--server.address=127.0.0.1", f"--server.port={port}",
                "--browser.gatherUsageStats=false",
            ],
            cwd=PROJECT_DIR,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        try:
            wait_until_ready(server, url)
            webview.create_window(
                "AquaGuard · Smart Water Tank Monitoring", url, width=1440, height=940,
                min_size=(1000, 700), background_color="#0b1117",
            )
            webview.start(gui="edgechromium", debug=False)
            return 0
        except Exception as exc:
            print(f"Could not open the AquaGuard desktop window: {exc}")
            print(f"Startup log: {log_path}")
            return 1
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
