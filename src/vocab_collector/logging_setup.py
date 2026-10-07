"""Rotating file logging that survives a windowed (--noconsole) build."""

from __future__ import annotations

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 3


def _coerce_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    return logging.getLevelNamesMapping().get(str(level).upper(), logging.INFO)


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass


def setup_logging(log_path: Path | str, level: str | int = "INFO") -> logging.Logger:
    """Configure the root logger with a rotating UTF-8 file handler."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(_coerce_level(level))
    _clear_handlers(logger)

    formatter = logging.Formatter(_FORMAT)
    file_handler = RotatingFileHandler(
        str(path), maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Under PyInstaller --noconsole, sys.stderr is None; never add a stream there.
    if sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def redact_secret(text: str, secret: str | None) -> str:
    """Replace an API key with *** so it can never reach a log sink."""
    if secret and secret in text:
        return text.replace(secret, "***")
    return text


def install_excepthooks(logger: logging.Logger) -> None:
    """Route uncaught exceptions (main thread and threads) to the log."""

    def _main_hook(exc_type, exc_value, exc_tb) -> None:
        logger.critical("uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    def _thread_hook(args) -> None:
        name = args.thread.name if args.thread is not None else "?"
        logger.critical(
            "uncaught exception in thread %s",
            name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _main_hook
    threading.excepthook = _thread_hook