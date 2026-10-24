"""Barreras de seguridad añadidas para la integración con el gemelo digital (ver GEMELO_DIGITAL.md).

- Tope global de velocidad (--speed-cap / limits.speed_cap).
- Batería: < 25 % no se para; < 15 % de pie => cero y acostarse.
- Hombre muerto (TTL 0,3 s) y cero al perder el WS: ya cubiertos en test_bridge.py
  (test_teleop_valid_then_expires_at_0_3s, test_ws_drop_gives_continuous_zero_and_reconnects);
  aquí se repite el caso del TTL con reloj falso.
"""

import argparse

import pytest

from d1.config import add_common_args, build_config
from d1.controller import ControlCore
from d1.sdk import MockRobot

DT = 0.05


def make(clock, battery=87, **kw):
    robot = MockRobot(clock=clock, battery=battery)
    robot.connect()
    core = ControlCore(robot, clock=clock, log=lambda m: None, battery_period_s=0.0, **kw)
    return robot, core


def run(core, clock, seconds, feed=None):
    ev = []
    for _ in range(int(round(seconds / DT))):
        now = clock.advance(DT)
        if feed:
            feed(now)
        core.tick(now)
        ev += core.pop_events()
    return ev


def parse(argv):
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    return build_config(ap.parse_args(argv))


def test_speed_cap_clips_all_linear_limits():
    cfg = parse(["--speed-cap", "0.3"])
    lim = cfg.limits
    assert (lim.vx_max, lim.vx_fast, lim.vy_max) == (0.3, 0.3, 0.25)
    assert lim.wz_max == 0.6


def test_no_speed_cap_by_default():
    lim = parse([]).limits
    assert (lim.vx_max, lim.vx_fast) == (0.4, 0.8)


def test_speed_cap_holds_even_with_fast_and_full_stick(clock):
    cfg = parse(["--speed-cap", "0.3"])
    robot = MockRobot(clock=clock)
    robot.connect()
    core = ControlCore(robot, cfg.limits, cfg.accel, clock=clock, log=lambda m: None)
    assert core.request_stand()
    run(core, clock, 2.1)
    run(core, clock, 1.5, feed=lambda now: core.set_teleop("sim", 1, 1, 1, fast=True))
    assert max(abs(m[1]) for m in robot.moves) <= 0.3 + 1e-9
    assert max(abs(m[2]) for m in robot.moves) <= 0.25 + 1e-9


def test_deadman_teleop_expires_in_0_3_s(clock):
    robot, core = make(clock)
    assert core.request_stand()
    run(core, clock, 2.1)
    core.set_teleop("sim", 1, 0, 0)
    for _ in range(4):                       # 0,2 s: vigente
        core.tick(clock.advance(DT))
    assert core.applied[0] > 0
    run(core, clock, 0.4)                    # nadie más manda: caduca
    assert core.applied == (0.0, 0.0, 0.0)
    assert robot.moves[-1][1:] == (0.0, 0.0, 0.0)


def test_battery_below_25_refuses_stand(clock):
    robot, core = make(clock, battery=20)
    core._poll_status(clock())
    assert core.battery == 20
    assert core.request_stand() is False
    assert not core.standing
    assert ("battery_low" in [e[0] for e in core.pop_events()])
    assert all(c[1] != "standUp" for c in robot.calls)


def test_battery_25_or_more_allows_stand(clock):
    robot, core = make(clock, battery=40)
    core._poll_status(clock())
    assert core.request_stand() is True


def test_battery_reading_without_sdk_is_ignored(clock):
    robot, core = make(clock, battery=60)
    assert core.request_stand()
    run(core, clock, 2.1)
    robot._battery = 0.0
    core._next_status = 0.0
    robot.connected = False                  # el SDK dejó de responder: lecturas en 0 no son fiables
    run(core, clock, 0.6)
    assert not core.lie_pending and core.body == "standing"


def test_battery_below_15_lies_down_zero_first(clock):
    robot, core = make(clock, battery=60)
    assert core.request_stand()
    run(core, clock, 2.1)
    run(core, clock, 0.5, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    assert core.applied[0] > 0               # camina
    robot._battery = 12.0                    # cae de golpe
    ev = run(core, clock, 0.3, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    names = [e[0] for e in ev]
    assert "battery_critical" in names
    assert core.applied == (0.0, 0.0, 0.0)   # aunque la sim siga mandando W: cero
    ev = run(core, clock, 3.0)
    assert robot.state == "lying"
    lie_t = [t for t, n in robot.calls if n == "lieDown"]
    assert lie_t, "debió llamar lieDown"
    # cero sostenido ANTES de lieDown (lie_zero_s = 0,4 s)
    before = [m for m in robot.moves if m[0] <= lie_t[0]][-6:]
    assert all(m[1:] == (0.0, 0.0, 0.0) for m in before)
    assert core.request_stand() is False     # y no deja pararse de nuevo
