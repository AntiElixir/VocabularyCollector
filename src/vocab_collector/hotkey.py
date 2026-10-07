"""Global Ctrl+C+C gesture detection.

Detection is split in two: ``TapStateMachine`` is pure and fully testable,
while ``Listener`` is the thin pynput glue that feeds real keyboard events in.
Keys are matched by virtual-key code, so the gesture is Dvorak/IME safe.
"""

from __future__ import annotations

import logging
import time
from enum import Enum

from . import clipboard

_LOG = logging.getLogger(__name__)

VK_C = 0x43
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3

#: Generic control is what pynput synthesises for ``Key.ctrl``; the left/right
#: variants are what the low-level hook reports for physical presses.
_CONTROL_VKS = (VK_CONTROL, VK_LCONTROL, VK_RCONTROL)


def _vk_of(key) -> int | None:
    """Extract a virtual-key code from a pynput key event.

    Plain keys arrive as :class:`pynput.keyboard.KeyCode`, which exposes ``vk``
    directly. Special keys (``Key.ctrl``, ...) arrive as :class:`Key` enum
    members, whose ``vk`` is ``None``; the code lives on ``key.value.vk``.
    """
    vk = getattr(key, "vk", None)
    if vk is not None:
        return vk
    value = getattr(key, "value", None)
    if isinstance(value, int):
        return value
    return getattr(value, "vk", None)


class Event(Enum):
    NONE = "none"
    FIRST_TAP = "first_tap"
    TRIGGER = "trigger"


class TapStateMachine:
    """Recognise Ctrl held + C tapped twice within a time window."""

    def __init__(self, window_ms: int) -> None:
        self._window_s = window_ms / 1000.0
        self._ctrl_down = False
        self._c_down = False
        self._first_press_at: float | None = None
        self._first_released = False
        self._armed = False
        self._cooldown_until = 0.0

    def _reset(self) -> None:
        self._c_down = False
        self._first_press_at = None
        self._first_released = False
        self._armed = False
        self._cooldown_until = 0.0

    def feed(self, vk: int, is_press: bool, now_monotonic: float) -> Event:
        if vk in _CONTROL_VKS:
            if is_press:
                self._ctrl_down = True
            else:
                self._ctrl_down = False
                self._reset()
            return Event.NONE

        if vk != VK_C:
            if is_press:
                self._reset()
            return Event.NONE

        if not self._ctrl_down:
            if is_press:
                self._reset()
            return Event.NONE

        if not is_press:
            if self._c_down:
                self._c_down = False
                if self._first_press_at is not None:
                    self._first_released = True
            return Event.NONE

        # Press of C while Ctrl is held.
        if self._c_down:
            # Auto-repeat: ignore.
            return Event.NONE
        self._c_down = True

        if self._armed and now_monotonic > self._cooldown_until:
            self._armed = False
            self._first_press_at = None
            self._first_released = False

        if self._first_press_at is not None and (now_monotonic - self._first_press_at) > self._window_s:
            self._reset()
            self._c_down = True

        if self._armed:
            return Event.NONE

        if self._first_press_at is None:
            self._first_press_at = now_monotonic
            self._first_released = False
            return Event.FIRST_TAP

        if not self._first_released:
            self._reset()
            self._c_down = True
            return Event.NONE

        self._armed = True
        self._cooldown_until = now_monotonic + self._window_s
        return Event.TRIGGER


class Listener:
    """pynput keyboard listener that only feeds the state machine and enqueues."""

    def __init__(self, on_trigger, window_ms: int, sequence_provider=clipboard.get_sequence_number) -> None:
        self._machine = TapStateMachine(window_ms)
        self._on_trigger = on_trigger
        self._sequence_provider = sequence_provider
        self._seq0: int | None = None
        self._listener = None

    def _handle(self, vk: int | None, is_press: bool) -> None:
        if vk is None:
            return
        event = self._machine.feed(vk, is_press, time.monotonic())
        if event is Event.FIRST_TAP:
            try:
                self._seq0 = self._sequence_provider()
            except Exception:
                self._seq0 = None
                _LOG.exception("failed to read clipboard sequence number")
        elif event is Event.TRIGGER:
            if self._seq0 is None:
                _LOG.warning("trigger without a recorded clipboard sequence, ignoring")
                return
            self._on_trigger(self._seq0)

    def on_press(self, key) -> None:
        self._handle(_vk_of(key), True)

    def on_release(self, key) -> None:
        self._handle(_vk_of(key), False)

    def start(self) -> "Listener":
        from pynput import keyboard

        self._listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self._listener.start()
        _LOG.info("hotkey listener started")
        return self

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        _LOG.info("hotkey listener stopped")

    def join(self) -> None:
        if self._listener is not None:
            self._listener.join()