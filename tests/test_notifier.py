"""Tests for the notifier module."""

from vocab_collector import notifier


def test_notify_word_recognized_does_not_raise(monkeypatch):
    """notify_word_recognized must never propagate exceptions."""

    class FakeToaster:
        def __init__(self, name):
            self.name = name

        def show_toast(self, toast):
            raise RuntimeError("toast system unavailable")

    monkeypatch.setattr("windows_toasts.WindowsToaster", FakeToaster)
    monkeypatch.setattr("windows_toasts.Toast", lambda: _FakeToast())

    notifier.notify_word_recognized("hello")


def test_notify_word_recognized_sets_fields(monkeypatch):
    captured = {}

    class FakeToaster:
        def __init__(self, name):
            captured["app_name"] = name

        def show_toast(self, toast):
            captured["toast"] = toast

    class FakeToast:
        def __init__(self):
            self.text_fields = []

    monkeypatch.setattr("windows_toasts.WindowsToaster", FakeToaster)
    monkeypatch.setattr("windows_toasts.Toast", FakeToast)

    notifier.notify_word_recognized("algorithm")

    assert captured["app_name"] == "VocabularyCollector"
    assert captured["toast"].text_fields == ["\u5df2\u8bc6\u522b\u5355\u8bcd", "algorithm"]
