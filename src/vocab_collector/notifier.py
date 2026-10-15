"""Windows toast notifications for word recognition feedback."""

from __future__ import annotations

import logging

_LOG = logging.getLogger(__name__)


def notify_word_recognized(word: str) -> None:
    """Show a Windows toast notification for a successfully recognised word.

    Failures are logged and swallowed so that notification issues never
    break the capture pipeline.
    """
    try:
        from windows_toasts import Toast, WindowsToaster

        toaster = WindowsToaster("VocabularyCollector")
        toast = Toast()
        toast.text_fields = ["\u5df2\u8bc6\u522b\u5355\u8bcd", word]
        toaster.show_toast(toast)
    except Exception:
        _LOG.warning("failed to show toast notification", exc_info=True)
