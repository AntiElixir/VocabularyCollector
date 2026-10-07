import types

from vocab_collector import hotkey
from vocab_collector.hotkey import Event, TapStateMachine, VK_C, VK_LCONTROL, VK_RCONTROL


def _press(machine, vk, t):
    return machine.feed(vk, True, t)


def _release(machine, vk, t):
    return machine.feed(vk, False, t)


def test_double_tap_with_release_triggers_once():
    machine = TapStateMachine(400)
    _press(machine, VK_LCONTROL, 0.0)
    assert _press(machine, VK_C, 0.00) is Event.FIRST_TAP
    assert _release(machine, VK_C, 0.05) is Event.NONE
    assert _press(machine, VK_C, 0.10) is Event.TRIGGER


def test_single_tap_does_not_trigger():
    machine = TapStateMachine(400)
    _press(machine, VK_LCONTROL, 0.0)
    assert _press(machine, VK_C, 0.0) is Event.FIRST_TAP
    assert _release(machine, VK_C, 0.05) is Event.NONE


def test_triple_tap_triggers_exactly_once():
    machine = TapStateMachine(400)
    _press(machine, VK_LCONTROL, 0.0)
    events = []
    t = 0.0
    for _ in range(3):
        events.append(_press(machine, VK_C, t))
        t += 0.05
        events.append(_release(machine, VK_C, t))
        t += 0.05
    assert events.count(Event.TRIGGER) == 1


def test_auto_repeat_down_only_never_triggers():
    machine = TapStateMachine(400)
    _press(machine, VK_LCONTROL, 0.0)
    assert _press(machine, VK_C, 0.00) is Event.FIRST_TAP
    assert _press(machine, VK_C, 0.03) is Event.NONE
    assert _press(machine, VK_C, 0.06) is Event.NONE
    assert _press(machine, VK_C, 0.09) is Event.NONE


def test_other_key_between_taps_resets():
    machine = TapStateMachine(400)
    _press(machine, VK_LCONTROL, 0.0)
    _press(machine, VK_C, 0.00)
    _release(machine, VK_C, 0.05)
    _press(machine, 0x41, 0.06)  # the letter A
    assert _press(machine, VK_C, 0.10) is Event.FIRST_TAP
    _release(machine, VK_C, 0.12)
    assert _press(machine, VK_C, 0.15) is Event.TRIGGER


def test_ctrl_release_between_taps_resets():
    machine = TapStateMachine(400)
    _press(machine, VK_LCONTROL, 0.0)
    _press(machine, VK_C, 0.00)
    _release(machine, VK_C, 0.05)
    _release(machine, VK_LCONTROL, 0.06)
    assert _press(machine, VK_C, 0.10) is Event.NONE
    _press(machine, VK_LCONTROL, 0.11)
    assert _press(machine, VK_C, 0.15) is Event.FIRST_TAP


def test_c_without_ctrl_is_ignored():
    machine = TapStateMachine(400)
    assert _press(machine, VK_C, 0.0) is Event.NONE


def test_window_boundary_399_triggers_and_401_does_not():
    inside = TapStateMachine(400)
    _press(inside, VK_LCONTROL, 0.0)
    _press(inside, VK_C, 0.0)
    _release(inside, VK_C, 0.01)
    assert _press(inside, VK_C, 0.399) is Event.TRIGGER

    outside = TapStateMachine(400)
    _press(outside, VK_LCONTROL, 0.0)
    _press(outside, VK_C, 0.0)
    _release(outside, VK_C, 0.01)
    assert _press(outside, VK_C, 0.401) is not Event.TRIGGER


def test_right_control_works():
    machine = TapStateMachine(400)
    _press(machine, VK_RCONTROL, 0.0)
    assert _press(machine, VK_C, 0.0) is Event.FIRST_TAP
    _release(machine, VK_C, 0.05)
    assert _press(machine, VK_C, 0.1) is Event.TRIGGER


def test_listener_records_sequence_and_enqueues(monkeypatch):
    clock = {"t": 0.0}

    def fake_monotonic():
        clock["t"] += 0.05
        return clock["t"]

    monkeypatch.setattr(hotkey.time, "monotonic", fake_monotonic)

    triggered = []
    listener = hotkey.Listener(triggered.append, window_ms=400, sequence_provider=lambda: 42)

    ctrl = types.SimpleNamespace(vk=VK_LCONTROL)
    c = types.SimpleNamespace(vk=VK_C)

    listener.on_press(ctrl)
    listener.on_press(c)
    listener.on_release(c)
    listener.on_press(c)

    assert triggered == [42]


def test_listener_ignores_keys_without_vk(monkeypatch):
    triggered = []
    listener = hotkey.Listener(triggered.append, window_ms=400, sequence_provider=lambda: 42)
    listener.on_press(types.SimpleNamespace(vk=None))
    assert triggered == []