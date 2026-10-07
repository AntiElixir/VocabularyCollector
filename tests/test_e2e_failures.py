"""Hermetic Windows E2E: failure paths must never write a partial row."""

import socket
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.windows_e2e

pytest.importorskip("pynput")

if sys.platform != "win32":
    pytest.skip("Windows only", allow_module_level=True)

from pynput.keyboard import Controller, Key  # noqa: E402

import e2e_support as support  # noqa: E402
from vocab_collector import db  # noqa: E402


@pytest.fixture
def app_env():
    backup = support.CONFIG.read_bytes() if support.CONFIG.exists() else None
    support.clean_runtime_files()
    yield
    support.remove_config()
    if backup is not None:
        support.CONFIG.write_bytes(backup)


def _rows():
    if not support.DB_FILE.exists():
        return []
    conn = db.connect(support.DB_FILE)
    try:
        return db.list_all(conn)
    finally:
        conn.close()


def _dead_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _copy_twice(keyboard):
    with keyboard.pressed(Key.ctrl):
        keyboard.press("c")
        keyboard.release("c")
        time.sleep(0.08)
        keyboard.press("c")
        keyboard.release("c")


def _capture_word_in_notepad(word: str) -> subprocess.Popen:
    notepad = subprocess.Popen(["notepad.exe"])
    time.sleep(2.0)
    keyboard = Controller()
    keyboard.type(word)
    time.sleep(0.3)
    with keyboard.pressed(Key.ctrl):
        keyboard.press("a")
        keyboard.release("a")
    time.sleep(0.2)
    _copy_twice(keyboard)
    return notepad


def test_stub_500_logs_error_keeps_db_empty_and_process_alive(app_env):
    state = support.StubState()
    state.status = 500
    stub = support.StubServer(state).start()
    support.write_config(stub.base_url)
    process = support.launch_app()
    notepad = None
    try:
        time.sleep(2.0)
        notepad = _capture_word_in_notepad("heterogeneous")

        assert support.wait_for(
            lambda: "heterogeneous" in support.read_log() and "ERROR" in support.read_log()
        ), support.read_log()

        assert _rows() == []
        assert process.poll() is None
    finally:
        support.kill(notepad)
        support.kill(process)
        stub.stop()


def test_dead_port_logs_timeout_and_keeps_db_empty(app_env):
    support.write_config(f"http://127.0.0.1:{_dead_port()}/v1")
    process = support.launch_app()
    notepad = None
    try:
        time.sleep(2.0)
        notepad = _capture_word_in_notepad("connectionless")

        assert support.wait_for(
            lambda: "connectionless" in support.read_log() and "ERROR" in support.read_log()
        ), support.read_log()

        assert _rows() == []
        assert process.poll() is None
    finally:
        support.kill(notepad)
        support.kill(process)


def test_missing_config_exits_1_and_names_the_path():
    support.remove_config()
    support.clean_runtime_files()

    process = support.launch_app()
    try:
        assert process.wait(timeout=20) == 1
    finally:
        support.kill(process)

    assert str(support.CONFIG) in support.read_log()


def test_stale_clipboard_is_rejected_without_a_row(app_env):
    stub = support.StubServer().start()
    support.write_config(stub.base_url)
    process = support.launch_app()
    notepad = None
    try:
        time.sleep(2.0)
        # Focus Notepad with nothing selected: Ctrl+C changes no clipboard content.
        notepad = subprocess.Popen(["notepad.exe"])
        time.sleep(2.0)
        _copy_twice(Controller())

        assert support.wait_for(lambda: "rejected timeout" in support.read_log()), support.read_log()
        assert _rows() == []
    finally:
        support.kill(notepad)
        support.kill(process)
        stub.stop()