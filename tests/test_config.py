from pathlib import Path

import pytest

from vocab_collector import paths
from vocab_collector.config import ConfigError, PLACEHOLDER_API_KEY, load_config

GOOD = """
[llm]
base_url = "https://example.test/api/v1"
api_key = "sk-real-secret"
model = "deepseek-chat"
timeout_seconds = 12
max_retries = 3
rate_limit_retry_wait = 30

[app]
max_selection_chars = 32
double_tap_window_ms = 250
clipboard_wait_ms = 300
log_level = "DEBUG"
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_file_loads(tmp_path):
    cfg = load_config(_write(tmp_path, GOOD))
    assert cfg.llm.base_url == "https://example.test/api/v1"
    assert cfg.llm.api_key == "sk-real-secret"
    assert cfg.llm.model == "deepseek-chat"
    assert cfg.llm.timeout_seconds == 12
    assert cfg.llm.max_retries == 3
    assert cfg.llm.rate_limit_retry_wait == 30
    assert cfg.app.max_selection_chars == 32
    assert cfg.app.double_tap_window_ms == 250
    assert cfg.app.clipboard_wait_ms == 300
    assert cfg.app.log_level == "DEBUG"


def test_defaults_applied_when_app_section_absent(tmp_path):
    text = '[llm]\nbase_url="https://x/api/v1"\napi_key="sk-real"\nmodel="m"\n'
    cfg = load_config(_write(tmp_path, text))
    assert cfg.app.max_selection_chars == 64
    assert cfg.app.double_tap_window_ms == 400
    assert cfg.app.clipboard_wait_ms == 800
    assert cfg.app.log_level == "INFO"
    assert cfg.llm.timeout_seconds == 30
    assert cfg.llm.max_retries == 0
    assert cfg.llm.rate_limit_retry_wait == 60


def test_missing_file_names_the_path(tmp_path):
    missing = tmp_path / "nope.toml"
    with pytest.raises(ConfigError) as exc:
        load_config(missing)
    assert str(missing) in str(exc.value)


def test_missing_api_key_rejected(tmp_path):
    text = '[llm]\nbase_url="https://x/api/v1"\nmodel="m"\n'
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, text))


def test_placeholder_key_rejected(tmp_path):
    text = f'[llm]\nbase_url="https://x/api/v1"\napi_key="{PLACEHOLDER_API_KEY}"\nmodel="m"\n'
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, text))
    assert "placeholder" in str(exc.value)


def test_redacted_summary_never_contains_the_key(tmp_path):
    cfg = load_config(_write(tmp_path, GOOD))
    summary = cfg.redacted_summary()
    assert "sk-real-secret" not in summary
    assert "***" in summary


def test_example_config_loads_once_key_is_filled(tmp_path):
    example = paths.example_config_path().read_text(encoding="utf-8")
    filled = example.replace(PLACEHOLDER_API_KEY, "sk-real")
    cfg = load_config(_write(tmp_path, filled))
    assert cfg.llm.base_url == "https://models.sjtu.edu.cn/api/v1"
    assert cfg.llm.model == "deepseek-chat"
    assert cfg.app.max_selection_chars == 64