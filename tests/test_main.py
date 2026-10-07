import sys
import threading
import types

import pytest

from vocab_collector import __main__ as app_main


@pytest.fixture(autouse=True)
def _restore_excepthooks():
    original_main = sys.excepthook
    original_thread = threading.excepthook
    yield
    sys.excepthook = original_main
    threading.excepthook = original_thread


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(app_main.paths, "ensure_dirs", lambda: None)
    monkeypatch.setattr(app_main.paths, "log_path", lambda: tmp_path / "collector.log")
    monkeypatch.setattr(app_main.paths, "config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setattr(app_main.paths, "db_path", lambda: tmp_path / "vocabulary.db")
    monkeypatch.setattr(app_main.paths, "html_path", lambda: tmp_path / "vocabulary.html")


def test_missing_config_exits_1_and_logs_the_path(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)

    with pytest.raises(SystemExit) as exc:
        app_main.main()

    assert exc.value.code == 1
    log_text = (tmp_path / "collector.log").read_text(encoding="utf-8")
    assert str(tmp_path / "config.toml") in log_text


def test_happy_path_starts_listener_and_regenerates_html(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    (tmp_path / "config.toml").write_text(
        '[llm]\nbase_url="https://x/api/v1"\napi_key="sk-real"\nmodel="m"\n',
        encoding="utf-8",
    )

    calls = {}

    class FakeListener:
        def __init__(self, on_trigger, window_ms):
            calls["window_ms"] = window_ms
            calls["on_trigger"] = on_trigger
            calls["constructed"] = True

        def start(self):
            calls["started"] = True

        def join(self):
            pass

        def stop(self):
            calls["stopped"] = True

    monkeypatch.setattr(app_main, "hotkey", types.SimpleNamespace(Listener=FakeListener))
    monkeypatch.setattr(app_main, "LLMClient", lambda config: object())

    assert app_main.main() == 0
    assert calls.get("constructed") is True
    assert calls.get("started") is True
    assert calls.get("stopped") is True
    assert (tmp_path / "vocabulary.html").exists()