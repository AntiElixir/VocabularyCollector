import sys
import types

import pytest

from vocab_collector import clipboard


def _fake_pyperclip(paste):
    module = types.ModuleType("pyperclip")

    class PyperclipException(Exception):
        pass

    module.PyperclipException = PyperclipException
    module.paste = paste
    return module


@pytest.mark.parametrize(
    "text,expected",
    [
        ("  heterogeneous  ", "heterogeneous"),
        ("a   b", "a b"),
        ("\thello\t", "hello"),
        ("heterogeneous", "heterogeneous"),
    ],
)
def test_sanitize_normalizes(text, expected):
    assert clipboard.sanitize(text, 64) == expected


def test_sanitize_accepts_exactly_max_length():
    word = "a" * 64
    assert clipboard.sanitize(word, 64) == word


@pytest.mark.parametrize("text", ["", "   ", "a\nb", "a\r\nb", "a" * 65, "1234", None])
def test_sanitize_rejects(text):
    assert clipboard.sanitize(text, 64) is None


def test_wait_for_change_returns_true_when_sequence_changes(monkeypatch):
    sequence = iter([7, 7, 8])
    monkeypatch.setattr(clipboard, "get_sequence_number", lambda: next(sequence))
    monkeypatch.setattr(clipboard.time, "sleep", lambda _seconds: None)

    assert clipboard.wait_for_change(7, timeout_ms=100) is True


def test_wait_for_change_returns_false_on_timeout(monkeypatch):
    monkeypatch.setattr(clipboard, "get_sequence_number", lambda: 7)
    counter = {"n": 0}

    def fake_monotonic():
        counter["n"] += 1
        return 0.0 if counter["n"] <= 2 else 999.0

    monkeypatch.setattr(clipboard.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(clipboard.time, "sleep", lambda _seconds: None)

    assert clipboard.wait_for_change(7, timeout_ms=10) is False


def test_read_text_retries_then_raises(monkeypatch):
    attempts = {"n": 0}
    module = _fake_pyperclip(None)

    def paste():
        attempts["n"] += 1
        raise module.PyperclipException("clipboard busy")

    module.paste = paste
    monkeypatch.setitem(sys.modules, "pyperclip", module)
    monkeypatch.setattr(clipboard.time, "sleep", lambda _seconds: None)

    with pytest.raises(clipboard.ClipboardError):
        clipboard.read_text(retries=3, delay_ms=1)
    assert attempts["n"] == 3


def test_read_text_returns_on_success(monkeypatch):
    module = _fake_pyperclip(lambda: "selected word")
    monkeypatch.setitem(sys.modules, "pyperclip", module)

    assert clipboard.read_text() == "selected word"