"""Daemon entry point: no window, no arguments."""

from __future__ import annotations

import logging
import sys

from . import db, hotkey, html_export, paths
from .config import ConfigError, load_config
from .llm import LLMClient
from .logging_setup import install_excepthooks, setup_logging
from .pipeline import Collector

_LOG = logging.getLogger(__name__)


def main() -> int:
    paths.ensure_dirs()
    setup_logging(paths.log_path(), "INFO")
    install_excepthooks(logging.getLogger())

    try:
        config = load_config(paths.config_path())
    except ConfigError as exc:
        _LOG.critical("configuration error: %s", exc)
        raise SystemExit(1) from exc

    setup_logging(paths.log_path(), config.app.log_level)
    install_excepthooks(logging.getLogger())
    _LOG.info("starting %s", config.redacted_summary())

    conn = db.connect(paths.db_path())
    db.init_schema(conn)
    html_export.write_atomic(paths.html_path(), html_export.render(db.list_all(conn)))

    llm = LLMClient(config.llm)
    collector = Collector(config, conn, llm, paths).start()

    listener = hotkey.Listener(collector.enqueue, config.app.double_tap_window_ms)
    listener.start()
    _LOG.info("listening")

    try:
        listener.join()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        collector.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())