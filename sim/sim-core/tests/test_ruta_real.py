"""Seguidor de la Ruta real: recta, vuelta en U (arco y giro en el sitio), deriva, escala/largo y barreras."""
from __future__ import annotations

import math
import time
from typing import Any

import pytest

import server
from robot import FieldMap
from ruta_real import RutaParams, Seguidor, length, plan_relativa, rel_to_odom, rel_to_scene
from safety import SafetyConfig
from test_robot_link import HELLO, _telemetry
from robot_link import RobotLink

FM = FieldMap(server.CFG["field"], server.CFG["robot"])
DT = 0.05


def simular(verts, p=None, pose=(0.0, 0.0, 0.0), push=None, max_s=900.0, tau=0.3):
    """Monociclo con retardo de primer orden. Devuelve (órdenes, trayectoria, último estado)."""
    p = p or RutaParams()
    seg = Seguidor(verts, p)
    x, y, yaw = pose
    v = wz = 0.0
    traj, ords = [], []
    t = 0.0
    while t < max_s:
        o = seg.step(x, y, yaw)
        ords.append(o)
        if o.estado != "en_marcha":
            break
        v += (o.v - v) * DT / tau
        wz += (o.wz - wz) * DT / tau
        yaw = math.atan2(math.sin(yaw + wz * DT), math.cos(yaw + wz * DT))
        x += v * math.cos(yaw) * DT
        y += v * math.sin(yaw) * DT
        if push:
            x, y = push(t, x, y)
        traj.append((x, y))
        t += DT
    return ords, traj, ords[-1]


def test_straight_reaches_end_slowly_and_on_the_line() -> None:
    ords, traj, last = simular([(0, 0), (4, 0)])
    assert last.estado == "terminada"
    assert max(o.v for o in ords) <= 0.2 + 1e-9
    assert max(abs(y) for _, y in traj) < 0.05
    assert traj[-1][0] == pytest.approx(4.0, abs=0.15)
    assert ords[0].restante_m == pytest.approx(4.0, abs=0.01)


def test_u_turn_that_fits_uses_a_slow_arc() -> None:
    # aisle 4 m, headland 2,27 m between aisles: radio 0,4 cabe -> arcos, nunca gira en el sitio
    verts = [(0, 0), (4, 0), (4, 2.27), (0, 2.27)]
    seg = Seguidor(verts, RutaParams())
    assert not any(q.spin for q in seg.pts) and any(q.arc for q in seg.pts)
    ords, traj, last = simular(verts)
    assert last.estado == "terminada"
    assert max(o.wz for o in ords) <= 0.3 + 1e-9 and min(o.wz for o in ords) >= -0.3 - 1e-9
    assert max(o.v for o in ords) <= 0.2 + 1e-9
    assert max(o.deriva_m for o in ords) < 0.2
    assert traj[-1][1] == pytest.approx(2.27, abs=0.15)


def test_u_turn_that_does_not_fit_spins_in_place_with_low_wz() -> None:
    verts = [(0, 0), (1.0, 0), (1.0, 0.68), (0, 0.68)]  # escala 0,3: no cabe el radio
    seg = Seguidor(verts, RutaParams())
    assert sum(q.spin for q in seg.pts) == 2
    ords, traj, last = simular(verts)
    assert last.estado == "terminada"
    spins = [o for o in ords if o.v == 0.0 and abs(o.wz) > 0]
    assert spins, "debe girar en el sitio"
    assert max(abs(o.wz) for o in ords) <= 0.3 + 1e-9
    assert max(o.deriva_m for o in ords) < 0.25


def test_tramo_progress_and_remaining_distance_decrease() -> None:
    verts = [(0, 0), (3, 0), (3, 1.5), (0, 1.5)]
    ords, _, last = simular(verts)
    rest = [o.restante_m for o in ords]
    assert all(b <= a + 0.05 for a, b in zip(rest, rest[1:]))
    assert ords[0].tramo == 1 and max(o.tramo for o in ords) == 3
    assert last.restante_m == 0.0


def test_drift_beyond_limit_stops_with_deriva() -> None:
    def push(t, x, y):  # un empujón lateral de 0,7 m a los 5 s
        return (x, y + 0.7) if 5.0 <= t < 5.0 + DT else (x, y)

    ords, _, last = simular([(0, 0), (6, 0)], RutaParams(deriva_max_m=0.4), push=push)
    assert last.estado == "deriva" and last.deriva_m > 0.4
    assert last.v == 0.0 and last.wz == 0.0  # cero al declararse la deriva


def test_pure_pursuit_corrects_small_offsets() -> None:
    ords, traj, last = simular([(0, 0), (6, 0)], pose=(0.0, 0.25, 0.0))
    assert last.estado == "terminada"
    assert abs(traj[-1][1]) < 0.08


def test_plan_scale_and_max_length() -> None:
    full = plan_relativa(FM, RutaParams(escala=1.0))
    small = plan_relativa(FM, RutaParams(escala=0.3))
    assert length(small) == pytest.approx(0.3 * length(full), rel=1e-6)
    assert full[0] == (0.0, 0.0) and full[1][0] == pytest.approx(FM.head_n - FM.head_s, abs=1e-6)
    cut = plan_relativa(FM, RutaParams(escala=0.3, largo_max_m=10.0))
    assert length(cut) == pytest.approx(10.0, abs=1e-6)
    assert plan_relativa(FM, RutaParams(escala=1.0), aisles=[0])[-1][1] == 0.0  # un pasillo: recto


def test_scene_and_odom_mappings_are_consistent() -> None:
    rel = [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0)]
    sc = rel_to_scene(rel, 5.0, 7.0, math.pi / 2)  # mirando a +x
    assert sc[1] == pytest.approx((7.0, 7.0), abs=1e-9)  # adelante = +x
    assert sc[2] == pytest.approx((7.0, 6.0), abs=1e-9)  # izquierda = -z cuando mira a +x
    od = rel_to_odom(rel, 1.0, 1.0, math.pi / 2)  # odometría: yaw +90° = mira a +y
    assert od[1] == pytest.approx((1.0, 3.0), abs=1e-9)
    assert od[2] == pytest.approx((0.0, 3.0), abs=1e-9)


# ---------- integración con RobotLink (barreras) ----------
def make_link() -> RobotLink:
    link = RobotLink(hold_s=4.0, safety=SafetyConfig(speed_cap_mps=0.3))
    link.connected = True
    link.connected_at = time.time()
    link.on_message({**HELLO, "limits": {"vx_max": 0.3, "vy_max": 0.25, "wz_max": 0.6}})
    link.on_message(_telemetry(state="standing", x=1.0, y=2.0, yaw=0.5))
    link.set_manual(1, True)
    return link


def start(link: RobotLink, **kw: Any) -> bool:
    rel = plan_relativa(FM, RutaParams.from_dict({"escala": 0.3, "largo_max_m": 8.0, **kw}))
    ok = link.ruta_start(rel, RutaParams.from_dict({"escala": 0.3, "largo_max_m": 8.0, **kw}), (FM.base[0], FM.base[1], 0.0))
    link._ruta_arranque = 0.0  # skip the 0,6 s neutral that follows pressing the button
    return ok


def estado(link: RobotLink) -> str:
    return link.status()["ruta"]["estado"]


def test_link_route_generates_teleop_at_most_0_2() -> None:
    link = make_link()
    assert start(link)
    assert estado(link) == "en_marcha"
    m = link.teleop_tick()
    assert m["type"] == "teleop" and m["strafe"] == 0.0 and m["fast"] is False
    assert 0.0 < m["fwd"] * 0.3 <= 0.2 + 1e-9  # 0,3 m/s del hello x fwd
    assert abs(m["turn"] * 0.6) <= 0.3 + 1e-9


def test_link_estop_cancels_and_requires_pressing_again() -> None:
    link = make_link()
    assert start(link)
    link.action("estop")
    assert estado(link) == "cancelada"
    assert link.teleop_tick()["fwd"] == 0.0
    link.action("resume")
    link.guard_tick()
    assert estado(link) == "cancelada", "Reanudar no reanuda la ruta"
    assert link.teleop_tick()["fwd"] == 0.0


@pytest.mark.parametrize("what", ["link", "geofence", "battery", "manual", "keys"])
def test_link_barriers_cancel_route(what: str) -> None:
    link = make_link()
    link.panel_update({"cam_ok": True})
    assert start(link, escala=1.0 if what == "geofence" else 0.3)
    if what == "link":
        link.telemetry_at = time.time() - 2
    elif what == "video":
        link.panel_update({"cam_ok": False})
        link._video_lost_since = time.monotonic() - 5
    elif what == "geofence":
        link.update_pose(1, FM.bed_centers_x[0], 0.0, FM)  # escala 1: la geocerca de la escena sigue activa
    elif what == "battery":
        link.on_message(_telemetry(state="standing", battery=10))
    elif what == "manual":
        link.set_manual(1, False)
    elif what == "keys":
        link.set_teleop({"fwd": 1.0}, 1)
    link.guard_tick()
    m = link.teleop_tick()
    assert estado(link) == "cancelada", what
    if m is not None:
        assert m["fwd"] == 0.0 and m["turn"] == 0.0


def test_video_loss_pauses_route_and_cancels_only_after_12_s() -> None:
    link = make_link()
    link.panel_update({"cam_ok": True})
    assert start(link, escala=0.3)
    link.panel_update({"cam_ok": False})
    link._video_lost_since = time.monotonic() - 5
    link.guard_tick()
    m = link.teleop_tick()
    assert estado(link) == "pausa" and m["fwd"] == 0.0 and m["turn"] == 0.0
    link._sin_video_desde = time.monotonic() - 13
    link.guard_tick()
    assert estado(link) == "cancelada"


def test_link_detection_hold_pauses_then_resumes_by_itself() -> None:
    link = make_link()
    assert start(link)
    assert link.teleop_tick()["fwd"] > 0
    link.on_detection({"label": "oidio", "conf": 0.9, "sospecha": True})
    m = link.teleop_tick()
    assert m["fwd"] == 0.0 and m["turn"] == 0.0
    assert estado(link) == "pausa"
    link.hold_until = time.monotonic() - 0.1  # termina el detection_stop
    assert link.teleop_tick()["fwd"] > 0
    assert estado(link) == "en_marcha"


def test_link_drift_stops_and_warns() -> None:
    link = make_link()
    assert start(link)
    link.on_message(_telemetry(state="standing", x=1.0 + 5.0, y=2.0 + 5.0, yaw=0.5))  # lejos del camino
    m = link.teleop_tick()
    assert m["fwd"] == 0.0 and m["turn"] == 0.0
    assert estado(link) == "cancelada"
    assert "deriv" in " ".join(e["text"].lower() for e in link.log)


def test_link_refuses_to_start_when_not_ready() -> None:
    link = make_link()
    link.on_message(_telemetry(state="lying", x=0.0, y=0.0, yaw=0.0))
    assert start(link) is False and "pararse" in link.log[-1]["text"].lower()
    link = make_link()
    link.on_message(_telemetry(state="standing", x=None, y=None, yaw=None))
    assert start(link) is False and "odometr" in link.log[-1]["text"].lower()
    link = make_link()
    link.action("estop")
    assert start(link) is False


def test_dryrun_draws_without_moving_and_scaled_route_suspends_geofence() -> None:
    link = make_link()
    p = RutaParams.from_dict({"escala": 0.3, "largo_max_m": 8.0})
    link.ruta_dryrun(plan_relativa(FM, p), p, (FM.base[0], FM.base[1], 0.0))
    st = link.status()["ruta"]
    assert st["estado"] == "simulacion" and len(st["puntos"]) >= 2 and st["total_m"] == pytest.approx(8.0, abs=0.01)
    assert link.teleop_tick()["fwd"] == 0.0  # solo dibuja
    assert start(link)
    link.update_pose(1, FM.bed_centers_x[0], 0.0, FM)  # el gemelo "dentro de una cama" de la escena
    link.guard_tick()
    assert link.geo_violation is None, "con ruta reducida la geocerca de la escena se suspende (manda la deriva)"


def test_bloques_y_camino_central() -> None:
    """Bloque 1 = naves 1–2, Bloque 2 = naves 3–4, separados por el camino central; cada uno con su inicio."""
    assert FM.n_blocks == 2
    cx0, cx1 = FM.central_x()
    assert abs((cx1 - cx0) - 5.0) < 1e-9
    assert FM.nave_x0[1] + FM.nave_w <= cx0 + 1e-9 and FM.nave_x0[2] >= cx1 - 1e-9
    b1, b2 = FM.block_aisles(1), FM.block_aisles(2)
    assert b1 and b2 and not set(b1) & set(b2)
    assert all(FM.aisles[a].x < cx0 for a in b1) and all(FM.aisles[a].x > cx1 for a in b2)
    for b in (1, 2):
        x, z, h = FM.block_start(b)
        assert x == FM.aisles[FM.block_aisles(b)[0]].x and z == FM.head_s and h == 0.0
    assert cx0 <= FM.base[0] <= cx1  # la base queda al pie del camino central
