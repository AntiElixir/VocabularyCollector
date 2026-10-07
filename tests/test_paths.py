import sys
from pathlib import Path

from vocab_collector import paths


def test_frozen_uses_exe_directory(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\x\VocabularyCollector.exe")

    assert paths.app_dir() == Path(r"C:\x")
    assert paths.db_path() == Path(r"C:\x\data\vocabulary.db")
    assert str(paths.log_path()).endswith(r"data\collector.log")
    assert str(paths.html_path()).endswith(r"data\vocabulary.html")
    assert str(paths.config_path()).endswith(r"config\config.toml")


def test_source_layout_uses_repo_root(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    root = Path(paths.__file__).resolve().parents[2]
    assert paths.app_dir() == root
    assert paths.config_path() == root / "config" / "config.toml"


def test_meipass_is_never_consulted(monkeypatch):
    class BoomSys:
        def __getattr__(self, name):
            if name == "_MEIPASS":
                raise AssertionError("sys._MEIPASS must not be consulted")
            return getattr(sys, name)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\x\app.exe")
    monkeypatch.setattr(paths, "sys", BoomSys())

    assert paths.app_dir() == Path(r"C:\x")


def test_ensure_dirs_creates_config_and_data(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path)
    paths.ensure_dirs()
    assert (tmp_path / "config").is_dir()
    assert (tmp_path / "data").is_dir()