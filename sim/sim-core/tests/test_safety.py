"""Barreras de seguridad del D1 real: geocerca, batería, enlace, video, tope de velocidad, navegador caído."""
from __future__ import annotations

import time
from typing import Any

import pytest
from starlette.testclient import TestClient

import server
from robot import FieldMap
from robot_link import RobotLink
from safety import SafetyConfig, geofence_check
from test_robot_link import HELLO, _single_state, _telemetry, recv, recv_until, wait_for  # noqa: F401

FM = FieldMap(server.CFG["field"], server.CFG["robot"])
AISLE_X = FM.aisles[0].x
MID_Z = 0.0


def make_link(**cfg: Any) -> RobotLink:
    """A link that looks connected to a bridge (no sockets): what the bridge would receive is in `sent`."""
    link = RobotLink(hold_s=4.0, safety=SafetyConfig(speed_cap_mps=cfg.pop("speed_cap_mps", 0.0), **cfg))
    link.connected = True
    link.connected_at = time.time()
    link.on_message({**HELLO})
    link.on_message(_telemetry())
    return link


def sent(link: RobotLink) -> list[dict[str, Any]]:
    out = list(link._outbox)
    link._outbox.clear()
    return out


def log_text(link: RobotLink) -> str:
    return " | ".join(e["text"] for e in link.log)


def drive(link: RobotLink, fwd: float = 1.0, key: int = 1) -> dict[str, Any] | None:
    link.set_manual(key, True)
    link._need_release.discard(key)
    link.set_teleop({"fwd": fwd}, key)
    return link.teleop_tick()


# ---------- (a) geocerca ----------
def test_geofence_geometry() -> None:
    assert geofence_check(FM, AISLE_X, MID_Z) is None  # centro del pasillo
    assert geofence_check(FM, AISLE_X + 0.5, MID_Z) is None  # a 0,33 m de la cama: vale
    assert geofence_check(FM, FM.base[0], FM.base[1]) is None  # base, en el pasillo principal
    kind, text = geofence_check(FM, FM.bed_centers_x[0], MID_Z)  # encima de una cama
    assert kind == "cama" and "pasillo" in text
    edge = FM.bed_centers_x[1] - FM.bed_w / 2 - 0.2  # a 0,20 m del borde: < 0,25
    assert geofence_check(FM, edge, MID_Z)[0] == "cama"
    wall = FM.x0 + FM.nave_w  # corredor de pared entre naves: no es un pasillo
    assert geofence_check(FM, wall, MID_Z) is not None
    assert geofence_check(FM, FM.x0 - 30, FM.base[1]) is not None  # lejos del bloque
    assert geofence_check(FM, AISLE_X, FM.bed_z1 + FM.north_w + 3) is not None  # pasado el límite norte
    assert geofence_check(FM, float("nan"), 0.0) is not None


def test_geofence_trips_estop_with_visible_event() -> None:
    link = make_link()
    link.set_manual(1, True)
    link.update_pose(1, AISLE_X, MID_Z, FM)
    link.guard_tick()
    assert link.geo_violation is None and not sent(link)
    link.update_pose(1, FM.bed_centers_x[0], MID_Z, FM)  # el gemelo se mete en una cama
    link.guard_tick()
    assert any(m == {"type": "action", "name": "estop"} for m in sent(link))
    assert link.estop and link.trips["geofence"] == 1
    assert "fuera del pasillo" in log_text(link).lower()
    assert any(e["level"] == "danger" and "pasillo" in e["text"].lower() for e in link.log)  # => toast en la web
    link.guard_tick()
    assert not sent(link), "el disparo es por flanco: no repite el estop"


def test_geofence_blocks_driving_until_back_inside() -> None:
    link = make_link()
    link.update_pose(1, FM.bed_centers_x[0], MID_Z, FM)
    msg = drive(link)
    link.guard_tick()
    msg = drive(link)
    assert msg and msg["fwd"] == 0.0  # fuera del pasillo: ceros aunque haya tecla
    link.action("resume")
    link.guard_tick()
    assert drive(link)["fwd"] == 0.0, "Reanudar no basta mientras el gemelo siga fuera: Re-centrar"
    link.update_pose(1, AISLE_X, MID_Z, FM)  # Re-centrar el gemelo
    link.guard_tick()
    link.set_teleop({"fwd": 0.0}, 1)  # suelta las teclas
    link.set_teleop({"fwd": 1.0}, 1)
    assert drive(link)["fwd"] == 1.0


def test_geofence_ignores_stale_pose_and_can_be_disabled() -> None:
    link = make_link()
    link.set_manual(1, True)
    link.update_pose(1, FM.bed_centers_x[0], MID_Z, FM)
    link._pose[1] = (*link._pose[1][:2], time.monotonic() - 5.0, FM)  # pose vieja: no se juzga
    link.guard_tick()
    assert link.geo_violation is None
    link2 = make_link(geofence=False)
    link2.set_manual(1, True)
    link2.update_pose(1, FM.bed_centers_x[0], MID_Z, FM)
    link2.guard_tick()
    assert link2.geo_violation is None and not link2.estop


# ---------- (b) batería ----------
def test_battery_below_25_refuses_stand() -> None:
    link = make_link()
    link.on_message(_telemetry(battery=22))
    assert link.action("stand") is False
    assert not sent(link)
    assert "batería 22 %" in log_text(link).lower() or "batería 22" in log_text(link).lower()
    link.on_message(_telemetry(battery=60))
    assert link.action("stand") is True
    assert sent(link)[-1] == {"type": "action", "name": "stand"}


def test_battery_below_15_lies_down_once_and_zeroes_teleop() -> None:
    link = make_link()
    link.on_message(_telemetry(battery=12, state="moving"))
    link.guard_tick()
    link.guard_tick()
    assert sent(link) == [{"type": "action", "name": "lie"}]  # una sola orden, el puente pone cero primero
    assert "crítica" in log_text(link).lower()
    assert drive(link)["fwd"] == 0.0
    link.on_message(_telemetry(battery=40))
    link.guard_tick()
    assert drive(link)["fwd"] == 1.0


# ---------- (c) pérdida de enlace ----------
def test_stale_telemetry_stops_teleop_and_alerts() -> None:
    link = make_link()
    link.set_manual(1, True)
    assert drive(link)["fwd"] == 1.0
    link.telemetry_at = time.time() - 1.5  # el puente calló
    link.guard_tick()
    assert link._link_stale and link.status()["safety"]["link_stale"]
    assert link.teleop_tick() is None, "con telemetría vieja el sim deja de mandar teleop"
    assert "telemetría" in log_text(link).lower()
    assert link.trips["link"] == 1
    link.on_message(_telemetry())  # vuelve
    link.guard_tick()
    assert not link._link_stale
    link.set_teleop({"fwd": 1.0}, 1)
    assert link.teleop_tick()["fwd"] == 0.0, "al volver hay que soltar y pulsar de nuevo"


def test_stale_without_any_telemetry_after_connect() -> None:
    link = RobotLink(safety=SafetyConfig(speed_cap_mps=0.0))
    link.connected = True
    link.connected_at = time.time() - 2.0
    link.guard_tick()
    assert link._link_stale


# ---------- (d) pérdida de video ----------
def test_video_loss_holds_robot_after_3s_in_manual() -> None:
    link = make_link()
    link.panel_update({"cam_ok": True})
    link.guard_tick()
    assert drive(link)["fwd"] == 1.0
    link.panel_update({"cam_ok": False})
    link.guard_tick()
    assert drive(link)["fwd"] == 1.0, "antes de 3 s todavía se puede"
    link._video_lost_since = time.monotonic() - 3.5
    link.guard_tick()
    assert link._video_block
    assert drive(link)["fwd"] == 0.0
    assert "sin video: robot detenido" in log_text(link).lower()
    assert link.trips["video"] == 1
    link.panel_update({"cam_ok": True})
    link.guard_tick()
    assert not link._video_block
    link.set_teleop({"fwd": 1.0}, 1)  # sigue con W apretada (sin pasar por neutro)
    assert link.teleop_tick()["fwd"] == 0.0, "con el video de vuelta hay que soltar y pulsar de nuevo"


def test_video_guard_inactive_until_panel_is_seen_or_forced() -> None:
    link = make_link()
    link.guard_tick()
    assert not link.video_guard_active() and drive(link)["fwd"] == 1.0
    forced = make_link(video_guard="on")
    forced.set_manual(1, True)
    forced.guard_tick()
    forced._video_lost_since = time.monotonic() - 4
    forced.guard_tick()
    assert drive(forced)["fwd"] == 0.0
    off = make_link(video_guard="off")
    off.panel_update({"cam_ok": False})
    off._video_lost_since = time.monotonic() - 10
    off.guard_tick()
    assert drive(off)["fwd"] == 1.0


def test_panel_that_stops_reporting_counts_as_video_lost() -> None:
    link = make_link()
    link.set_manual(1, True)
    link.panel_update({"cam_ok": True})
    link.panel_at = time.monotonic() - 2.0  # el panel murió
    assert not link.video_ok()
    link.guard_tick()
    link._video_lost_since = time.monotonic() - 4
    link.guard_tick()
    assert link._video_block


# ---------- (e) tope de velocidad ----------
def test_speed_cap_scales_axes_and_forbids_fast() -> None:
    link = make_link(speed_cap_mps=0.3)  # el puente declara vx_max 0,4 en HELLO
    link.set_manual(1, True)
    link.set_teleop({"fwd": 1, "strafe": 1, "turn": 0.5, "fast": True}, 1)
    m = link.teleop_tick()
    assert m["fwd"] == pytest.approx(0.75)  # 0,75 x 0,4 m/s = 0,3 m/s
    assert m["strafe"] == pytest.approx(1.0)  # vy_max 0,25 < 0,3
    assert m["fast"] is False and m["turn"] == 0.5
    link.set_teleop({"fwd": -1}, 1)
    assert link.teleop_tick()["fwd"] == pytest.approx(-0.75)


def test_speed_cap_noop_when_bridge_is_already_slower_and_configurable() -> None:
    link = make_link(speed_cap_mps=0.3)
    link.on_message({**HELLO, "limits": {"vx_max": 0.3, "vy_max": 0.25, "wz_max": 0.6}})
    link.set_manual(1, True)
    link.set_teleop({"fwd": 1}, 1)
    assert link.teleop_tick()["fwd"] == pytest.approx(1.0)
    link.safety.update({"speed_cap_mps": 0.2})
    assert link.teleop_tick()["fwd"] == pytest.approx(0.2 / 0.3)
    link.safety.update({"speed_cap_mps": -5, "bogus": 1})  # inválidos se ignoran
    assert link.safety.speed_cap_mps == 0.2


# ---------- (f) navegador caído ----------
def test_viewer_closed_sends_explicit_zeros() -> None:
    link = make_link()
    drive(link)
    link.viewer_closed(1)
    link.set_manual(1, False)
    msgs = [link.teleop_tick() for _ in range(3)]
    assert all(m and m["fwd"] == 0.0 for m in msgs)
    assert "navegador" in log_text(link).lower()
    link._zero_until = 0.0
    link._was_driving = False
    assert link.teleop_tick() is None


def test_browser_ws_drop_sends_zero_to_bridge_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "LINK", RobotLink(hold_s=4.0, notify=server._notify, safety=SafetyConfig(speed_cap_mps=0.0)))
    with TestClient(server.app) as c, c.websocket_connect("/ws/robot") as bridge:
        bridge.send_json(HELLO)
        with c.websocket_connect("/ws") as web:
            recv_until(web, _single_state)
            web.send_json({"cmd": "manual", "value": True})
            t0 = time.monotonic()
            while time.monotonic() - t0 < 0.5:
                web.send_json({"cmd": "teleop", "fwd": 1})
                bridge.send_json(_telemetry())
                recv(bridge, 0.5)
        # el navegador murió con W apretada: el puente debe recibir ceros, no más W
        end = time.monotonic() + 1.0
        zeros = 0
        while time.monotonic() < end and zeros < 5:
            bridge.send_json(_telemetry())
            m = recv(bridge, 0.5)
            if m["type"] == "teleop":
                zeros = zeros + 1 if m["fwd"] == 0.0 else 0
        assert zeros >= 5


# ---------- por HTTP / WebSocket ----------
def test_pose_out_of_aisle_over_ws_stops_the_real_robot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "LINK", RobotLink(hold_s=4.0, notify=server._notify, safety=SafetyConfig(speed_cap_mps=0.0)))
    with TestClient(server.app) as c, c.websocket_connect("/ws/robot") as bridge, c.websocket_connect("/ws") as web:
        bridge.send_json(HELLO)
        recv_until(web, _single_state)
        web.send_json({"cmd": "manual", "value": True})
        web.send_json({"cmd": "pose", "x": FM.bed_centers_x[0], "z": 0.0, "heading": 0.0, "speed": 0.0})
        got = []

        def saw_estop() -> bool:
            bridge.send_json(_telemetry())
            m = recv(bridge, 0.5)
            got.append(m)
            return m == {"type": "action", "name": "estop"}

        wait_for(saw_estop, 3.0)
        toast = recv_until(web, lambda m: any(e.get("type") == "real_alert" and "pasillo" in e.get("text", "") for e in m.get("events", [])), timeout=3.0)
        assert toast
        assert c.get("/api/robot").json()["estop"] is True


def test_panel_heartbeat_and_safety_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "LINK", RobotLink(hold_s=4.0, notify=server._notify, safety=SafetyConfig()))
    with TestClient(server.app) as c:
        assert c.get("/api/robot").json()["safety"]["panel"] is None
        assert c.post("/api/panel", json={"cam_ok": False, "clase": "sin_hoja"}).json() == {"ok": True}
        st = c.get("/api/robot").json()["safety"]
        assert st["panel"]["cam_ok"] is False and st["video_guard_active"] is True and st["video_ok"] is False
        assert c.post("/api/safety", json={"speed_cap_mps": 0.25, "video_guard": "off"}).json()["config"]["speed_cap_mps"] == 0.25
        assert c.get("/api/safety").json()["video_guard_active"] is False


def test_panel_detection_creates_incident_and_stops_the_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "LINK", RobotLink(hold_s=4.0, notify=server._notify, safety=SafetyConfig(speed_cap_mps=0.0)))
    with TestClient(server.app) as c, c.websocket_connect("/ws/robot") as bridge, c.websocket_connect("/ws") as web:
        bridge.send_json(HELLO)
        recv_until(web, _single_state)
        r = c.post("/api/detection", json={"label": "oidio", "conf": 0.93, "p_enfermedad": 0.96, "sospecha": True,
                                           "umbral": 0.737, "truth_label": "oidio", "source": "rtsp"}).json()
        assert r["ok"] and r["forwarded_to_robot"] is True
        stop = recv_until(bridge, lambda m: m["type"] == "detection_stop", 2.0)
        assert stop["label"] == "oidio"
        st = c.get("/api/robot").json()
        assert st["incidents"] == 1 and st["last_detection"]["incident_no"] == 1


def test_battery_zero_with_sdk_down_is_not_a_reading() -> None:
    link = make_link()
    link.on_message(_telemetry(battery=0, sdk_ok=False, state="sdk_error"))
    assert link._battery() is None
    assert link.action("stand") is True  # no se bloquea por una lectura falsa
