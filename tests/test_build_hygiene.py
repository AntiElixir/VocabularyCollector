"""Prove the built dist/ tree carries no secret and no real config."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def scan_for_secret(tree: Path, needle: str) -> list[Path]:
    hits = []
    for path in tree.rglob("*"):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if needle.encode("utf-8") in data:
            hits.append(path)
    return hits


def _real_key() -> str | None:
    config_file = ROOT / "config" / "config.toml"
    if not config_file.exists():
        return None
    from vocab_collector.config import load_config

    try:
        return load_config(config_file).llm.api_key
    except Exception:
        return None


def test_scanner_finds_a_planted_secret(tmp_path):
    """Self-test: the checker actually detects a secret when one is present."""
    (tmp_path / "blob.bin").write_bytes(b"prefix sk-planted-secret suffix")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "clean.txt").write_text("nothing here", encoding="utf-8")

    assert [p.name for p in scan_for_secret(tmp_path, "sk-planted-secret")] == ["blob.bin"]
    assert scan_for_secret(tmp_path, "sk-a-different-secret") == []


def test_dist_has_no_real_key_and_no_real_config():
    if not DIST.is_dir():
        pytest.skip("dist/ not built yet; run scripts/build.ps1 first")

    key = _real_key()
    if key:
        assert scan_for_secret(DIST, key) == [], "the real API key leaked into dist/"

    assert list(DIST.rglob("config.toml")) == []
    assert (DIST / "VocabularyCollector" / "config" / "config.example.toml").is_file()


def test_gitignore_covers_runtime_and_secret_files():
    if not (ROOT / ".git").exists():
        pytest.skip("not a git repository")

    for target in ("config/config.toml", "data/"):
        result = subprocess.run(
            ["git", "check-ignore", "-q", target], cwd=str(ROOT), check=False
        )
        assert result.returncode == 0, f"{target} is not gitignored"