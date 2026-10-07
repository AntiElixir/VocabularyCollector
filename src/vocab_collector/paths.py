"""Portable path resolution: works both from source and from a frozen exe.

The built application is a PyInstaller onedir bundle. Its config/ and data/
folders live next to the executable, so the whole folder is portable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory that owns config/ and data/.

    Frozen: the folder containing the executable (never sys._MEIPASS).
    Source checkout: the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable))
    return Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    return app_dir() / "config"


def data_dir() -> Path:
    return app_dir() / "data"


def config_path() -> Path:
    return config_dir() / "config.toml"


def example_config_path() -> Path:
    return config_dir() / "config.example.toml"


def db_path() -> Path:
    return data_dir() / "vocabulary.db"


def log_path() -> Path:
    return data_dir() / "collector.log"


def html_path() -> Path:
    return data_dir() / "vocabulary.html"


def templates_dir() -> Path:
    """Directory containing web UI templates."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "templates"
    return Path(__file__).resolve().parent / "templates"


def ensure_dirs() -> None:
    """Create config/ and data/ next to the app if they are missing."""
    config_dir().mkdir(parents=True, exist_ok=True)
    data_dir().mkdir(parents=True, exist_ok=True)