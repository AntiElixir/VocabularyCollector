"""Windows smoke test: the real pynput listener reacts to synthetic Ctrl+C+C."""

import sys
import time

import pytest

pytestmark = pytest.mark.windows_e2e

pytest.importorskip("pynput")

if sys.platform != "win32":
    pytest.skip("Windows only", allow_module_level=True)

from pynput.keyboard import Controller, Key  # noqa: E402

from vocab_collector.hotkey import Listener  # noqa: E402


def _wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_synthetic_double_tap_fires_exactly_one_callback():
    triggered = []
    listener = Listener(triggered.append, window_ms=500, sequence_provider=lambda: 1)
    listener.start()
    time.sleep(0.3)
    try:
        keyboard = Controller()
        with keyboard.pressed(Key.ctrl):
            keyboard.press("c")
            keyboard.release("c")
            time.sleep(0.08)
            keyboard.press("c")
            keyboard.release("c")
        assert _wait_for(lambda: len(triggered) == 1), triggered
    finally:
        listener.stop()

    assert len(triggered) == 1


def test_single_synthetic_copy_fires_nothing():
    triggered = []
    listener = Listener(triggered.append, window_ms=500, sequence_provider=lambda: 1)
    listener.start()
    time.sleep(0.3)
    try:
        keyboard = Controller()
        with keyboard.pressed(Key.ctrl):
            keyboard.press("c")
            keyboard.release("c")
        time.sleep(0.8)
    finally:
        listener.stop()

    assert triggered == []