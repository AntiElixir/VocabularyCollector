"""Clipboard freshness gate, retrying read, and selection sanitization."""

from __future__ import annotations

import ctypes
import logging
import re
import time

_LOG = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")
_HAS_LETTER_RE = re.compile(r"[A-Za-z]")


class ClipboardError(Exception):
    """Raised when the clipboard cannot be read after all retries."""


def get_sequence_number() -> int:
    """Current Windows clipboard change counter (changes on every copy)."""
    return int(ctypes.windll.user32.GetClipboardSequenceNumber())


def wait_for_change(prev_seq: int, timeout_ms: int, poll_ms: int = 20) -> bool:
    """Block until the clipboard sequence differs from ``prev_seq``.

    Returns False if it does not change within ``timeout_ms`` (caller must then
    abort rather than read a possibly stale clipboard).
    """
    deadline = time.monotonic() + timeout_ms / 1000.0
    while get_sequence_number() == prev_seq:
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_ms / 1000.0)
    return True


def read_text(retries: int = 5, delay_ms: int = 50) -> str:
    """Read plain text from the clipboard, retrying while it is busy."""
    import pyperclip

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return pyperclip.paste()
        except pyperclip.PyperclipException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay_ms / 1000.0)
    raise ClipboardError(f"clipboard unavailable after {retries} attempts: {last_error}")


def sanitize(text: str | None, max_chars: int) -> str | None:
    """Normalize a captured selection, or return None if it is unusable.

    Rejects: empty, multi-line, longer than ``max_chars``, or containing no
    ASCII letter.
    """
    if text is None:
        return None
    if "\n" in text or "\r" in text:
        return None
    collapsed = _WHITESPACE_RE.sub(" ", text).strip()
    if not collapsed:
        return None
    if len(collapsed) > max_chars:
        return None
    if not _HAS_LETTER_RE.search(collapsed):
        return None
    return collapsed