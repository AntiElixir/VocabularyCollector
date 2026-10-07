"""Shared helpers for the Windows end-to-end tests.

The stub LLM is a local http.server, so the E2E never touches the network or
the real API key.
"""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CONFIG = ROOT / "config" / "config.toml"
DB_FILE = ROOT / "data" / "vocabulary.db"
LOG_FILE = ROOT / "data" / "collector.log"
HTML_FILE = ROOT / "data" / "vocabulary.html"


class StubState:
    def __init__(self):
        self.status = 200
        self.word = "heterogeneous"
        self.chinese = "异质的"
        self.domain = "AI"
        self.requests = 0


def _make_handler(state: StubState):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - stdlib naming
            length = int(self.headers.get("Content-Length", 0) or 0)
            self.rfile.read(length)
            state.requests += 1

            if state.status != 200:
                body = b'{"error":"stub failure"}'
            else:
                content = json.dumps(
                    {
                        "english": state.word,
                        "chinese": state.chinese,
                        "domain": state.domain,
                    }
                )
                body = json.dumps(
                    {
                        "id": "chatcmpl-stub",
                        "object": "chat.completion",
                        "created": 0,
                        "model": "stub",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": content},
                            }
                        ],
                    }
                ).encode()

            self.send_response(state.status if state.status != 200 else 200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Handler


class StubServer:
    def __init__(self, state: StubState | None = None):
        self.state = state or StubState()
        self._httpd = None
        self._thread = None
        self.port = None

    def start(self) -> "StubServer":
        self._httpd = http.server.HTTPServer(("127.0.0.1", 0), _make_handler(self.state))
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def write_config(base_url: str, api_key: str = "sk-e2e-stub") -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(
        "[llm]\n"
        f'base_url = "{base_url}"\n'
        f'api_key = "{api_key}"\n'
        'model = "stub-model"\n'
        "timeout_seconds = 5\n"
        "max_retries = 0\n"
        "\n"
        "[app]\n"
        "max_selection_chars = 64\n"
        "double_tap_window_ms = 400\n"
        "clipboard_wait_ms = 400\n"
        'log_level = "INFO"\n',
        encoding="utf-8",
    )


def remove_config() -> None:
    if CONFIG.exists():
        CONFIG.unlink()


def clean_runtime_files() -> None:
    for path in (DB_FILE, LOG_FILE, HTML_FILE):
        if path.exists():
            path.unlink()


def launch_app() -> subprocess.Popen:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.Popen(
        [sys.executable, "-m", "vocab_collector"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def kill(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def wait_for(predicate, timeout: float = 15.0, interval: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def read_log() -> str:
    if not LOG_FILE.exists():
        return ""
    return LOG_FILE.read_text(encoding="utf-8", errors="replace")