"""Co-simulación: RobotLink (sim-core) + ControlCore/MockRobot reales del puente, con reloj falso.

Recorre una ruta con vuelta en U de punta a punta (teleop 20 Hz, telemetría 10 Hz, rampa y zona muerta del
puente) y comprueba que llega, sin pasarse de 0,2 m/s, y que PARADA la cancela. Se salta si no está robot_d1 2.
"""
from __future__ import annotations

import math
import os
import sys
import time
import types

import pytest

import robot_link
from ruta_real import RutaParams
from safety import SafetyConfig

BRIDGE = os.path.expanduser("~/Downloads/robot_d1 2")
pytestmark = pytest.mark.skipif(not os.path.isdir(BRIDGE), reason="falta robot_d1 2")


class Rig:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sys.path.insert(0, BRIDGE)
        from d1.controller import ControlCore
        from d1.safety import Limits
        from d1.sdk import MockRobot

        self.t = 1000.0
        clock = lambda: self.t  # noqa: E731
        self.mr = MockRobot(clock=clock)
        self.mr.connect()
        self.core = ControlCore(self.mr, Limits(0.3, 0.3, 0.25, 0.6), clock=clock, log=lambda m: None, stand_settle_s=1.5)
        self.core.request_stand()
        for _ in range(100):
            self.t += 0.02
            self.core.tick(self.t)
        self.T = 0.0
        monkeypatch.setattr(robot_link, "time", types.SimpleNamespace(
            time=lambda: 1.7e9 + self.T, monotonic=lambda: self.T, perf_counter=lambda: self.T, sleep=time.sleep))
        self.link = robot_link.RobotLink(safety=SafetyConfig(speed_cap_mps=0.3))
        self.link.connected = True
        self.link.connected_at = 1.7e9
        self.link.on_message({"type": "hello", "robot": "D1", "mock": True, "version": 1,
                              "limits": {"vx_max": 0.3, "vy_max": 0.25, "wz_max": 0.6}})
        self.link.set_manual(1, True)
        self.k = 0
        self.vmax = 0.0
        self.tel()

    def tel(self) -> None:
        d = self.core.telemetry(wall_time=1.7e9 + self.T)
        self.link.on_message(d)

    def step(self) -> None:
        self.t += 0.02
        self.T += 0.02
        self.k += 1
        if self.k % 5 == 0:
            self.tel()
        if self.k % 2 == 0:
            self.link.guard_tick()
            m = self.link.teleop_tick()
            if m:
                self.core.set_teleop("sim", m["fwd"], m["strafe"], m["turn"], m["fast"], seq=m["seq"])
        self.core.tick(self.t)
        self.vmax = max(self.vmax, abs(self.core.applied[0]))

    def run(self, seconds: float, until=None) -> None:
        for _ in range(int(seconds / 0.02)):
            self.step()
            if until and until():
                return


def test_route_with_u_turn_completes_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    r = Rig(monkeypatch)
    verts = [(0.0, 0.0), (6.0, 0.0), (6.0, 0.34), (2.0, 0.34)]  # recta, U que no cabe (gira en el sitio), recta de vuelta
    assert r.link.ruta_start(verts, RutaParams(), (0.0, 0.0, 0.0))
    r.run(240, until=lambda: r.link._ruta_estado != "en_marcha")
    assert r.link._ruta_estado == "terminada", r.link._ruta_motivo
    assert r.vmax <= 0.2 + 1e-6
    assert math.hypot(r.mr.x - 2.0, r.mr.y - 0.34) < 0.25
    assert abs(abs(r.mr.yaw) - math.pi) < 0.4  # termina mirando de vuelta


def test_estop_mid_route_stops_zero_and_needs_new_press(monkeypatch: pytest.MonkeyPatch) -> None:
    r = Rig(monkeypatch)
    assert r.link.ruta_start([(0.0, 0.0), (20.0, 0.0)], RutaParams(), (0.0, 0.0, 0.0))
    r.run(10)
    assert r.mr.x > 0.5
    r.link.action("estop")
    r.core.estop("sim", "test")
    r.run(1.0)
    x = r.mr.x
    r.run(3.0)
    assert r.core.applied == (0.0, 0.0, 0.0) and abs(r.mr.x - x) < 0.02
    assert r.link._ruta_estado == "cancelada"
    r.link.action("resume")
    r.core.resume("sim")
    r.run(3.0)
    assert abs(r.mr.x - x) < 0.02, "Reanudar no reanuda la ruta"


def test_ruta_sala_mira_a_los_lados_y_se_dibuja_1_a_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escala 0,005 (bloque en ~3 m de sala): para a mirar izquierda y derecha y la ruta de la escena mide lo mismo
    que la real (el gemelo copia la odometría 1:1)."""
    from tests.test_ruta_real import FM
    from ruta_real import plan_relativa

    r = Rig(monkeypatch)
    p = RutaParams.from_dict({"escala": 0.005, "escaneos": 1, "pausa_scan_s": 1.0})
    assert p.escala == 0.005
    rel = plan_relativa(FM, p, FM.block_aisles(1))[:4]
    assert r.link.ruta_start(rel, p, (0.0, 0.0, 0.0))
    lados = set()
    def seguir() -> bool:
        if r.link.scan_lado():
            lados.add(r.link.scan_lado())
        return r.link._ruta_estado != "en_marcha"
    r.run(240, until=seguir)
    assert r.link._ruta_estado == "terminada", r.link._ruta_motivo
    assert lados == {"izquierda", "derecha"}
    largo_escena = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(r.link._ruta_scene, r.link._ruta_scene[1:]))
    assert abs(largo_escena - sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(rel, rel[1:]))) < 1e-6
