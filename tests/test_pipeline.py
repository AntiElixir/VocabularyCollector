import time

from vocab_collector import db, pipeline
from vocab_collector.config import AppConfig
from vocab_collector.llm import LLMError
from vocab_collector.models import VocabResult


class FakeConfig:
    app = AppConfig(
        max_selection_chars=64,
        double_tap_window_ms=400,
        clipboard_wait_ms=50,
        log_level="INFO",
    )


class Paths:
    def __init__(self, tmp_path):
        self._tmp = tmp_path

    def html_path(self):
        return self._tmp / "vocabulary.html"


class FakeLLM:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.words = []

    def collect(self, word):
        self.words.append(word)
        if self._error is not None:
            raise self._error
        return self._result


def _conn(tmp_path):
    conn = db.connect(tmp_path / "vocabulary.db")
    db.init_schema(conn)
    return conn


def _clipboard(monkeypatch, *, changed=True, text="heterogeneous"):
    monkeypatch.setattr(pipeline.clipboard, "wait_for_change", lambda seq0, ms: changed)
    reads = []
    monkeypatch.setattr(pipeline.clipboard, "read_text", lambda: reads.append(text) or text)
    return reads


def test_successful_capture_inserts_and_writes_html(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    _clipboard(monkeypatch, text="  heterogeneous  ")
    llm = FakeLLM(VocabResult(english="heterogeneous", chinese="异质的", domain="AI"))
    collector = pipeline.Collector(FakeConfig(), conn, llm, Paths(tmp_path))

    collector._process(1)

    rows = db.list_all(conn)
    assert len(rows) == 1
    assert rows[0][0] == "heterogeneous"
    assert "heterogeneous" in (tmp_path / "vocabulary.html").read_text(encoding="utf-8")


def test_llm_error_writes_nothing_and_logs_the_word(tmp_path, monkeypatch, caplog):
    conn = _conn(tmp_path)
    _clipboard(monkeypatch)
    llm = FakeLLM(error=LLMError("boom"))
    collector = pipeline.Collector(FakeConfig(), conn, llm, Paths(tmp_path))

    with caplog.at_level("ERROR"):
        collector._process(1)

    assert db.list_all(conn) == []
    assert any("heterogeneous" in record.getMessage() for record in caplog.records)


def test_timeout_aborts_without_reading(tmp_path, monkeypatch, caplog):
    conn = _conn(tmp_path)
    reads = _clipboard(monkeypatch, changed=False)
    llm = FakeLLM(VocabResult(english="x", chinese="y", domain="AI"))
    collector = pipeline.Collector(FakeConfig(), conn, llm, Paths(tmp_path))

    with caplog.at_level("WARNING"):
        collector._process(1)

    assert reads == []
    assert db.list_all(conn) == []
    assert "rejected timeout" in caplog.text


def test_duplicate_logs_and_does_not_rewrite_html(tmp_path, monkeypatch, caplog):
    conn = _conn(tmp_path)
    db.insert_word(conn, "heterogeneous", "异质的", "AI", "2026-01-01T00:00:00+00:00")
    sentinel = tmp_path / "vocabulary.html"
    sentinel.write_text("SENTINEL", encoding="utf-8")
    _clipboard(monkeypatch)
    llm = FakeLLM(VocabResult(english="heterogeneous", chinese="x", domain="y"))
    collector = pipeline.Collector(FakeConfig(), conn, llm, Paths(tmp_path))

    with caplog.at_level("INFO"):
        collector._process(1)

    assert sentinel.read_text(encoding="utf-8") == "SENTINEL"
    assert len(db.list_all(conn)) == 1


def test_invalid_selection_is_rejected(tmp_path, monkeypatch, caplog):
    conn = _conn(tmp_path)
    _clipboard(monkeypatch, text="1234")
    llm = FakeLLM(VocabResult(english="x", chinese="y", domain="AI"))
    collector = pipeline.Collector(FakeConfig(), conn, llm, Paths(tmp_path))

    with caplog.at_level("WARNING"):
        collector._process(1)

    assert llm.words == []
    assert db.list_all(conn) == []


def test_worker_survives_a_stage_exception(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    monkeypatch.setattr(pipeline.clipboard, "wait_for_change", lambda seq0, ms: True)
    monkeypatch.setattr(pipeline.clipboard, "read_text", lambda: "good")

    class ExplodingThenFine:
        def __init__(self):
            self.calls = 0

        def collect(self, word):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("kaboom")
            return VocabResult(english=word, chinese="好", domain="AI")

    collector = pipeline.Collector(FakeConfig(), conn, ExplodingThenFine(), Paths(tmp_path)).start()
    try:
        collector.enqueue(1)
        collector.enqueue(2)
        deadline = time.time() + 5
        while not db.list_all(conn) and time.time() < deadline:
            time.sleep(0.02)
    finally:
        collector.stop()

    rows = db.list_all(conn)
    assert len(rows) == 1
    assert rows[0][0] == "good"