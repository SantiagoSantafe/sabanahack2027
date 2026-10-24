"""Pruebas del núcleo de control (d1/controller.py) con MockRobot y un reloj falso."""

import time

import pytest

from d1.controller import ControlCore
from d1.sdk import MockRobot, StallGuard

DT = 0.05  # 20 Hz

CONTRACT_TELEMETRY_KEYS = {"type", "t", "x", "y", "yaw", "vx", "vy", "wz", "state", "sdk_ok",
                           "battery", "last_cmd_age_ms"}


def make(clock):
    robot = MockRobot(clock=clock)
    robot.connect()
    core = ControlCore(robot, clock=clock, log=lambda m: None)
    return robot, core


def run(core, clock, seconds, feed=None):
    events = []
    for _ in range(int(round(seconds / DT))):
        now = clock.advance(DT)
        if feed:
            feed(now)
        core.tick(now)
        events += core.pop_events()
    return events


def stand(core, clock):
    assert core.request_stand()
    ev = run(core, clock, 2.1)
    assert ("stood_up" in [e[0] for e in ev])
    assert core.standing


def test_no_move_before_stand(clock):
    robot, core = make(clock)
    run(core, clock, 0.5, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    assert len(robot.moves) == 0          # el SDK exige standUp antes de move: no mandamos nada
    assert core.display_state() == "lying"


def test_teleop_fresh_moves_robot(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 1.0, feed=lambda now: core.set_teleop("sim", 1, 0, 0.5))
    assert core.applied[0] == pytest.approx(0.4)
    assert core.applied[2] == pytest.approx(0.3)
    assert robot.cmd == pytest.approx((0.4, 0.0, 0.3))
    assert core.display_state() == "moving"
    assert robot.x > 0.1


def test_teleop_expires_after_0_3_s_and_zero_is_sent_continuously(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 1.0, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    t_last = clock.t
    n_before = len(robot.moves)
    # Ya no llegan teleops. A los 0,3 s el objetivo es cero y se manda cero ya (sin rampa).
    ev = run(core, clock, 0.25)
    assert core.applied[0] > 0              # todavía vigente (< 0,3 s)
    ev += run(core, clock, 0.4)
    assert clock.t - t_last >= 0.6
    assert core.applied == (0.0, 0.0, 0.0)
    assert [e[0] for e in ev].count("watchdog_zero") == 1
    ev = run(core, clock, 1.0)
    assert [e[0] for e in ev].count("watchdog_zero") == 0   # sin repetir el evento
    new_moves = list(robot.moves)[n_before:]
    assert len(new_moves) >= 30             # siguió mandando move() cada tick
    assert new_moves[-1][1:] == (0.0, 0.0, 0.0)
    assert core.display_state() == "standing"


def test_estop_immediate_zero_blocks_teleop_until_resume(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 1.0, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    core.estop("sim", "prueba")
    feed = lambda now: core.set_teleop("sim", 1, 1, 1)  # noqa: E731
    run(core, clock, DT, feed=feed)
    assert core.applied == (0.0, 0.0, 0.0)            # sin rampa: cero inmediato
    run(core, clock, 1.0, feed=feed)
    assert core.applied == (0.0, 0.0, 0.0)
    assert core.display_state() == "estop"
    assert robot.moves[-1][1:] == (0.0, 0.0, 0.0)     # cero continuo, NO passive
    assert all(name != "passive" for _, name in robot.calls)
    assert core.resume("sim")
    run(core, clock, 0.5, feed=feed)
    assert core.applied == (0.0, 0.0, 0.0)            # Reanudar no arranca solo: hay que soltar
    run(core, clock, DT, feed=lambda now: core.set_teleop("sim", 0, 0, 0))
    run(core, clock, 1.0, feed=feed)
    assert core.applied[0] == pytest.approx(0.4)


def test_local_estop_wins_over_sim_resume(clock):
    robot, core = make(clock)
    stand(core, clock)
    core.estop("local", "Espacio")
    assert not core.resume("sim")
    run(core, clock, 0.5, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    assert core.applied == (0.0, 0.0, 0.0)
    assert core.resume("local")


def test_detection_stop_holds_for_hold_s_and_ignores_teleop(clock):
    robot, core = make(clock)
    stand(core, clock)
    feed = lambda now: core.set_teleop("sim", 1, 0, 0)  # noqa: E731
    run(core, clock, 1.0, feed=feed)
    core.detection_stop(1.0, "oidio", 0.93)
    ev = run(core, clock, 0.9, feed=feed)
    assert core.applied[0] == 0.0
    assert core.display_state() == "detection_hold"
    assert "detection_hold_start" in [e[0] for e in ev]
    ev = run(core, clock, 0.6, feed=feed)
    assert "detection_hold_end" in [e[0] for e in ev]
    assert core.applied[0] > 0


def test_lie_waits_for_zero_then_calls_lieDown(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 1.0, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    assert core.request_lie()
    ev = run(core, clock, 0.2, feed=lambda now: core.set_teleop("sim", 1, 0, 0))
    assert not any(n == "lieDown" for _, n in robot.calls)     # todavía frenando
    ev += run(core, clock, 3.0)
    lie_calls = [t for t, n in robot.calls if n == "lieDown"]
    assert len(lie_calls) == 1
    # Antes de lieDown, el último move fue cero (no se acuesta caminando).
    before = [m for m in robot.moves if m[0] <= lie_calls[0]]
    assert before[-1][1:] == (0.0, 0.0, 0.0)
    assert not [m for m in robot.moves if m[0] > lie_calls[0]]  # acostado: no más move()
    assert "lay_down" in [e[0] for e in ev]
    assert core.display_state() == "lying"


def test_local_keyboard_overrides_sim_only_when_moving(clock):
    robot, core = make(clock)
    stand(core, clock)

    def feed(now):
        core.set_teleop("sim", 1, 0, 0)
        core.set_teleop("local", 0, 0, 0)

    run(core, clock, 1.0, feed=feed)
    assert core.active_source == "sim" and core.applied[0] == pytest.approx(0.4)

    def feed2(now):
        core.set_teleop("sim", 1, 0, 0)
        core.set_teleop("local", -1, 0, 0, scale=0.5)

    run(core, clock, 1.5, feed=feed2)
    assert core.active_source == "local" and core.applied[0] == pytest.approx(-0.2)


def test_stale_seq_is_dropped(clock):
    _, core = make(clock)
    assert core.set_teleop("sim", 1, 0, 0, seq=10)
    assert not core.set_teleop("sim", 0, 0, 0, seq=9)
    assert core.set_teleop("sim", 0, 0, 0, seq=11)
    assert not core.set_teleop("sim", 0, 0, 0, seq=1)      # misma conexión: viejo
    assert core.set_teleop("sim", 0, 0, 0, seq=5000)
    assert core.set_teleop("sim", 0, 0, 0, seq=2)          # salto atrás enorme = la sim reinició
    core.clear_teleop("sim")                               # reconexión del WebSocket
    assert core.set_teleop("sim", 0, 0, 0, seq=1)


def test_telemetry_has_exactly_contract_fields(clock):
    _, core = make(clock)
    stand(core, clock)
    tel = core.telemetry()
    assert set(tel) == CONTRACT_TELEMETRY_KEYS
    assert tel["type"] == "telemetry" and tel["state"] in (
        "standing", "moving", "lying", "passive", "estop", "detection_hold", "sdk_error")
    assert tel["sdk_ok"] is True and 0 <= tel["battery"] <= 100


def test_stand_refused_during_estop(clock):
    robot, core = make(clock)
    core.estop("sim")
    assert not core.request_stand()
    assert not any(n == "standUp" for _, n in robot.calls)


def test_shutdown_zero_then_lie(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 0.5, feed=lambda now: core.set_teleop("sim", 1, 0, 0))

    def fake_sleep(dt):
        clock.advance(dt)

    core.shutdown(lie=True, sleep=fake_sleep)
    names = [n for _, n in robot.calls]
    assert names[-1] == "lieDown"
    assert robot.state == "lying"
    assert robot.moves[-1][1:] == (0.0, 0.0, 0.0)


def test_stall_guard_sends_zero_when_loop_freezes():
    robot = MockRobot()
    robot.connect()
    robot.stand_up()
    robot.move(0.4, 0, 0)
    guard = StallGuard(robot, stall_s=0.2, period_s=0.05, log=lambda m: None).start()
    try:
        guard.beat(armed=True)
        time.sleep(0.5)                     # el "lazo" no late
        assert guard.trips == 1
        assert robot.cmd == (0.0, 0.0, 0.0)
    finally:
        guard.stop()


# --------------------------------------------------------------------------
# Revisión de integración (oct-2026)
# --------------------------------------------------------------------------
def test_full_stop_is_immediate_even_at_fast_speed(clock):
    """Soltar las teclas (objetivo cero) = cero en el siguiente tick, también a 0,8 m/s.

    Con la rampa de frenado (1,6 m/s²) tardaba ~0,5 s desde 0,8 m/s y la cadena
    navegador -> sim-core -> puente ya gasta ~0,1 s: no cumplía "cero en <= 0,3 s".
    """
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 1.5, feed=lambda now: core.set_teleop("sim", 1, 0, 0.5, fast=True))
    assert core.applied[0] == pytest.approx(0.8)
    run(core, clock, DT, feed=lambda now: core.set_teleop("sim", 0, 0, 0))
    assert core.applied == (0.0, 0.0, 0.0)
    assert robot.cmd == (0.0, 0.0, 0.0)


def test_teleop_expiry_at_fast_speed_zero_right_after_ttl(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 1.5, feed=lambda now: core.set_teleop("sim", 1, 0, 0, fast=True))
    t_last = clock.t
    run(core, clock, 0.35)                    # ya no llegan teleops (pestaña congelada, red caída)
    assert clock.t - t_last <= 0.35 + 1e-9
    assert core.applied == (0.0, 0.0, 0.0)


def test_resume_with_keys_held_needs_neutral_first(clock):
    """Reanudar no arranca el robot por sí solo (ISO 13850): con W apretada hay que soltar y volver a pulsar."""
    robot, core = make(clock)
    stand(core, clock)
    hold_w = lambda now: core.set_teleop("sim", 1, 0, 0)  # noqa: E731
    run(core, clock, 1.0, feed=hold_w)
    core.estop("sim", "prueba")
    run(core, clock, 0.5, feed=hold_w)
    assert core.resume("sim")
    run(core, clock, 1.0, feed=hold_w)        # W sigue apretada desde antes de Reanudar
    assert core.applied == (0.0, 0.0, 0.0)
    assert len(robot.moves) and robot.moves[-1][1:] == (0.0, 0.0, 0.0)   # sigue mandando ceros
    run(core, clock, DT, feed=lambda now: core.set_teleop("sim", 0, 0, 0))   # suelta
    run(core, clock, 1.0, feed=hold_w)        # vuelve a pulsar: ahora sí
    assert core.applied[0] == pytest.approx(0.4)


def test_stand_with_keys_held_needs_neutral_first(clock):
    """Teleop antes de stand: no se manda move(); y al terminar de pararse no sale andando con W apretada."""
    robot, core = make(clock)
    hold_w = lambda now: core.set_teleop("sim", 1, 0, 0)  # noqa: E731
    run(core, clock, 0.5, feed=hold_w)
    assert len(robot.moves) == 0 and core.display_state() == "lying"
    assert core.request_stand()
    ev = run(core, clock, 2.1, feed=hold_w)
    assert "stood_up" in [e[0] for e in ev]
    run(core, clock, 1.0, feed=hold_w)
    assert core.applied == (0.0, 0.0, 0.0)
    run(core, clock, DT, feed=lambda now: core.set_teleop("sim", 0, 0, 0))
    run(core, clock, 1.0, feed=hold_w)
    assert core.applied[0] == pytest.approx(0.4)


def test_neutral_also_counts_when_the_teleop_expired_or_local_keys_released(clock):
    robot, core = make(clock)
    stand(core, clock)
    run(core, clock, 0.5, feed=lambda now: core.set_teleop("local", 1, 0, 0))
    core.estop("local", "Espacio")
    assert core.resume("local")
    core.clear_teleop("local")                # el teclado local suelta = sin entrada
    run(core, clock, DT)
    run(core, clock, 1.0, feed=lambda now: core.set_teleop("local", 1, 0, 0))
    assert core.applied[0] == pytest.approx(0.4)


def test_link_restored_with_keys_held_needs_neutral_first(clock):
    """Se cae el WebSocket con W apretada y vuelve: el robot no arranca solo al reconectar."""
    robot, core = make(clock)
    stand(core, clock)
    hold_w = lambda now: core.set_teleop("sim", 1, 0, 0)  # noqa: E731
    run(core, clock, 1.0, feed=hold_w)
    core.clear_teleop("sim")                  # el puente pierde la conexión...
    core.require_neutral("sim")               # ...y la recupera: lo que llegue debe pasar por neutro
    run(core, clock, 0.5)
    run(core, clock, 1.0, feed=hold_w)        # la primera orden tras reconectar ya es W
    assert core.applied == (0.0, 0.0, 0.0)
    run(core, clock, DT, feed=lambda now: core.set_teleop("sim", 0, 0, 0))
    run(core, clock, 1.0, feed=hold_w)
    assert core.applied[0] == pytest.approx(0.4)
