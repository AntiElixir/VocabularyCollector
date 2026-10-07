import logging
import sys
import threading

from vocab_collector import logging_setup


def _flush(logger):
    for handler in logger.handlers:
        handler.flush()


def test_record_reaches_the_file(tmp_path):
    log_file = tmp_path / "collector.log"
    logger = logging_setup.setup_logging(log_file, "INFO")

    logging.getLogger("test").info("hello world")
    _flush(logger)

    assert log_file.exists()
    assert "hello world" in log_file.read_text(encoding="utf-8")


def test_stderr_none_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stderr", None)
    log_file = tmp_path / "collector.log"

    logger = logging_setup.setup_logging(log_file, "INFO")
    assert len(logger.handlers) == 1

    logging.getLogger("test").warning("still written")
    _flush(logger)
    assert "still written" in log_file.read_text(encoding="utf-8")


def test_excepthook_logs_a_traceback(tmp_path):
    log_file = tmp_path / "collector.log"
    logger = logging_setup.setup_logging(log_file, "INFO")

    original_main = sys.excepthook
    original_thread = threading.excepthook
    try:
        logging_setup.install_excepthooks(logger)
        try:
            raise ValueError("boom")
        except ValueError:
            sys.excepthook(*sys.exc_info())
        _flush(logger)
    finally:
        sys.excepthook = original_main
        threading.excepthook = original_thread

    text = log_file.read_text(encoding="utf-8")
    assert "boom" in text
    assert "Traceback" in text


def test_redact_secret():
    assert logging_setup.redact_secret("key=sk-abc here", "sk-abc") == "key=*** here"
    assert logging_setup.redact_secret("nothing", None) == "nothing"