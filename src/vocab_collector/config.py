"""Load and validate config/config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_API_KEY = "sk-REPLACE_ME"


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    max_retries: int = 0
    rate_limit_retry_wait: int = 60


@dataclass(frozen=True)
class AppConfig:
    max_selection_chars: int = 64
    double_tap_window_ms: int = 400
    clipboard_wait_ms: int = 800
    log_level: str = "INFO"


@dataclass(frozen=True)
class WebConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass(frozen=True)
class Config:
    llm: LlmConfig
    app: AppConfig
    web: WebConfig

    def redacted_summary(self) -> str:
        """Human-readable summary that never contains the API key."""
        return (
            f"base_url={self.llm.base_url} model={self.llm.model} "
            f"timeout_seconds={self.llm.timeout_seconds} "
            f"max_retries={self.llm.max_retries} "
            f"rate_limit_retry_wait={self.llm.rate_limit_retry_wait} "
            f"api_key=*** "
            f"max_selection_chars={self.app.max_selection_chars} "
            f"double_tap_window_ms={self.app.double_tap_window_ms} "
            f"clipboard_wait_ms={self.app.clipboard_wait_ms} "
            f"log_level={self.app.log_level} "
            f"web_host={self.web.host} web_port={self.web.port}"
        )


def _required_str(section: dict, key: str, where: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Missing or empty '{key}' in {where}.")
    return value.strip()


def load_config(path: Path | str) -> Config:
    """Parse and validate the TOML config, or raise ConfigError with a fix hint."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(
            f"Config file not found at {path}. Copy config/config.example.toml to "
            f"config/config.toml and paste your API key."
        )

    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Could not parse {path}: {exc}") from exc

    llm_raw = raw.get("llm")
    if not isinstance(llm_raw, dict):
        raise ConfigError(f"Missing [llm] section in {path}.")

    base_url = _required_str(llm_raw, "base_url", "[llm]")
    api_key = _required_str(llm_raw, "api_key", "[llm]")
    model = _required_str(llm_raw, "model", "[llm]")
    if api_key == PLACEHOLDER_API_KEY:
        raise ConfigError(
            "api_key is still the placeholder 'sk-REPLACE_ME'; paste your real key "
            "into config/config.toml."
        )

    try:
        timeout_seconds = float(llm_raw.get("timeout_seconds", 30))
        max_retries = int(llm_raw.get("max_retries", 0))
        rate_limit_retry_wait = int(llm_raw.get("rate_limit_retry_wait", 60))
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid numeric value in [llm]: {exc}") from exc

    app_raw = raw.get("app", {})
    if not isinstance(app_raw, dict):
        raise ConfigError(f"[app] must be a table in {path}.")
    try:
        app = AppConfig(
            max_selection_chars=int(app_raw.get("max_selection_chars", 64)),
            double_tap_window_ms=int(app_raw.get("double_tap_window_ms", 400)),
            clipboard_wait_ms=int(app_raw.get("clipboard_wait_ms", 800)),
            log_level=str(app_raw.get("log_level", "INFO")),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid value in [app]: {exc}") from exc

    web_raw = raw.get("web", {})
    if not isinstance(web_raw, dict):
        raise ConfigError(f"[web] must be a table in {path}.")
    try:
        web = WebConfig(
            host=str(web_raw.get("host", "127.0.0.1")),
            port=int(web_raw.get("port", 8765)),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid value in [web]: {exc}") from exc

    return Config(
        llm=LlmConfig(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            rate_limit_retry_wait=rate_limit_retry_wait,
        ),
        app=app,
        web=web,
    )