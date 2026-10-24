"""Pruebas del teclado en modo terminal: retención por tiempo y lectura de bytes."""

from d1.controller import ControlCore
from d1.keyboard import HoldTracker, KeyboardDriver, TerminalKeys, axes_from_keys, parse_bytes
from d1.sdk import MockRobot


class _NoTTY:
    def fileno(self):
        return -1


def make_term():
    t = TerminalKeys.__new__(TerminalKeys)       # sin tocar la terminal real
    t.hold = HoldTracker(0.6, 0.15)
    t.stream = _NoTTY()
    t.fd = -1
    t._old = None
    t._pending = ""
    t._pending_since = None
    t.enabled = False
    return t


def test_first_press_survives_autorepeat_delay():
    h = HoldTracker(initial_hold_s=0.6, repeat_hold_s=0.15)
    h.press("w", 0.0)
    assert h.is_held("w", 0.55)          # demora típica de autorrepetición ~0,5 s
    h.press("w", 0.5)                    # primera repetición
    for i in range(1, 16):               # repeticiones cada 33 ms
        h.press("w", 0.5 + i * 0.033)
    last = 0.5 + 15 * 0.033
    assert h.is_held("w", last + 0.14)
    assert not h.is_held("w", last + 0.151)   # al soltar, para en <= 0,15 s


def test_single_tap_stops_after_initial_window():
    h = HoldTracker(0.6, 0.15)
    h.press("w", 0.0)
    assert h.is_held("w", 0.59)
    assert not h.is_held("w", 0.61)


def test_parse_bytes_keys_arrows_and_esc():
    ev, rest = parse_bytes("wW \x1b[A")
    assert [(e.kind, e.key, e.shift) for e in ev] == [
        ("move", "w", False), ("move", "w", True), ("action", "estop", False), ("move", "w", False)]
    assert rest == ""
    ev, rest = parse_bytes("u\x1b")
    assert ev[0].key == "stand" and rest == "\x1b"     # Esc al final: esperar por si es flecha
    ev, _ = parse_bytes("\x1bx")
    assert ev[0].key == "quit"


def test_lone_esc_becomes_quit_after_50ms():
    t = make_term()
    assert t.feed("\x1b", 10.0) == []
    ev = t.feed("", 10.1)
    assert [e.key for e in ev] == ["quit"]


def test_arrow_split_across_reads_is_not_quit():
    t = make_term()
    assert t.feed("\x1b", 10.0) == []
    ev = t.feed("[B", 10.01)
    assert [(e.kind, e.key) for e in ev] == [("move", "s")]


def test_axes_and_space_releases_keys():
    t = make_term()
    t.feed("w", 0.0)
    assert t.axes(0.1) == (1.0, 0.0, 0.0, False)
    t.feed(" ", 0.2)
    assert t.axes(0.25) == (0.0, 0.0, 0.0, False)
    assert axes_from_keys(["w", "a", "q"]) == (1.0, 1.0, 1.0, False)


def test_driver_actions_and_levels(clock):
    robot = MockRobot(clock=clock)
    robot.connect()
    core = ControlCore(robot, clock=clock, log=lambda m: None)
    d = KeyboardDriver(core, [0.4, 0.6, 0.8, 1.0], 1, log=lambda m: None)
    d.backend = make_term()
    d.handle_events(parse_bytes("+++")[0])
    assert d.level == 1.0
    d.handle_events(parse_bytes("----")[0])
    assert d.level == 0.4
    d.handle_events(parse_bytes(" ")[0])
    assert core.stops.estopped and "local" in core.stops.estop_sources
    d.handle_events(parse_bytes("r")[0])
    assert not core.stops.estopped
    d.handle_events(parse_bytes("u")[0])
    assert any(n == "standUp" for _, n in robot.calls)
    d.handle_events(parse_bytes("\x03")[0])
    assert d.quit_requested
