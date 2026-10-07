"""Hermetic Windows E2E: Notepad + stub LLM + real capture -> DB + HTML."""

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
    """Give the app a stub config and a clean data/ dir, restoring afterwards."""
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


def _copy_twice(keyboard):
    with keyboard.pressed(Key.ctrl):
        keyboard.press("c")
        keyboard.release("c")
        time.sleep(0.08)
        keyboard.press("c")
        keyboard.release("c")


def test_full_capture_flow_writes_one_row_and_html(app_env):
    stub = support.StubServer().start()
    support.write_config(stub.base_url)
    process = support.launch_app()
    notepad = None
    try:
        time.sleep(2.0)
        assert process.poll() is None, support.read_log()

        notepad = subprocess.Popen(["notepad.exe"])
        time.sleep(2.0)

        keyboard = Controller()
        keyboard.type("heterogeneous")
        time.sleep(0.3)
        with keyboard.pressed(Key.ctrl):
            keyboard.press("a")
            keyboard.release("a")
        time.sleep(0.2)

        _copy_twice(keyboard)

        assert support.wait_for(lambda: len(_rows()) >= 1), support.read_log()

        rows = _rows()
        assert len(rows) == 1
        assert rows[0][0] == "heterogeneous"
        assert rows[0][1] == "异质的"

        html = support.HTML_FILE.read_text(encoding="utf-8")
        assert "heterogeneous" in html

        # Re-capturing the same selection must not add a second row.
        _copy_twice(keyboard)
        time.sleep(3.0)
        assert len(_rows()) == 1
    finally:
        support.kill(notepad)
        support.kill(process)
        stub.stop()