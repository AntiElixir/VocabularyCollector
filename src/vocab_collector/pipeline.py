"""Capture pipeline: one worker thread, isolated stages, HTML refresh."""

from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime, timezone

from . import clipboard, db, html_export
from .llm import LLMError

_LOG = logging.getLogger(__name__)

_POLL_TIMEOUT_S = 0.2


class Collector:
    """Serialise captures through a single worker thread.

    ``enqueue`` is the listener callback and must stay non-blocking; all slow
    work happens on the worker thread.
    """

    def __init__(self, config, db_conn, llm, paths) -> None:
        self._config = config
        self._conn = db_conn
        self._llm = llm
        self._paths = paths
        self._queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Collector":
        self._thread = threading.Thread(target=self._run, name="collector-worker", daemon=True)
        self._thread.start()
        return self

    def enqueue(self, seq0: int) -> None:
        self._queue.put(seq0)

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=_POLL_TIMEOUT_S)
            except queue.Empty:
                continue
            try:
                self._process(item)
            except Exception:
                _LOG.exception("unexpected error while handling a capture")
            finally:
                self._queue.task_done()

    def _process(self, seq0: int) -> None:
        if not clipboard.wait_for_change(seq0, self._config.app.clipboard_wait_ms):
            _LOG.warning("rejected timeout")
            return

        try:
            raw = clipboard.read_text()
        except Exception as exc:
            _LOG.warning("rejected clipboard unavailable: %s", exc)
            return

        word = clipboard.sanitize(raw, self._config.app.max_selection_chars)
        if word is None:
            _LOG.warning("rejected invalid selection")
            return

        try:
            result = self._llm.collect(word)
        except LLMError as exc:
            _LOG.error("error %s %s", word, exc)
            return

        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        inserted = db.insert_word(
            self._conn, result.english, result.chinese, result.domain, created_at
        )
        if not inserted:
            _LOG.info("duplicate %s", word)
            return

        _LOG.info("inserted %s", word)
        html_export.write_atomic(
            self._paths.html_path(), html_export.render(db.list_all(self._conn))
        )