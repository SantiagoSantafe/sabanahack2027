"""Link with the real D1 (contract robot_d1/PROTOCOLO.md v1): bridge socket, teleop relay, detections."""
from __future__ import annotations

import json
import time
from typing import Any, Callable

import anyio
import pytest
from starlette.testclient import TestClient

import server
from robot_link import RobotLink, TruthTally
from safety import SafetyConfig

HELLO = {"type": "hello", "robot": "D1 EDU", "mock": True, "version": 1, "limits": {"vx_max": 0.4, "vy_max": 0.25, "wz_max": 0.6}}


def _telemetry(**kw: Any) -> dict[str, Any]:
    base = {"type": "telemetry", "t": time.time(), "x": 0.0, "y": 0.0, "yaw": 0.0, "vx": 0.0, "vy": 0.0, "wz": 0.0,
            "state": "standing", "sdk_ok": True, "battery": 80, "last_cmd_age_ms": 12}
    return {**base, **kw}


def recv(ws: Any, timeout: float = 2.0) -> dict[str, Any]:
    """receive_json with a timeout (the test client's receive blocks forever)."""

    async def _r() -> Any:
        with anyio.fail_after(timeout):
            return await ws._send_rx.receive()

    msg = ws.portal.call(_r)
    if msg["type"] == "websocket.close":
        raise AssertionError(f"socket closed: {msg}")
    return json.loads(msg["text"])


def recv_until(ws: Any, pred: Callable[[dict[str, Any]], bool], timeout: float = 4.0) -> dict[str, Any]:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        msg = recv(ws, max(0.05, end - time.monotonic()))
        if pred(msg):
            return msg
    raise AssertionError("condition not met in time")


def wait_for(cond: Callable[[], bool], timeout: float = 2.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError("condition not met in time")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    # speed_cap_mps=0: these tests check the raw relay; the cap has its own tests in test_safety.py
    monkeypatch.setattr(server, "LINK", RobotLink(hold_s=4.0, notify=server._notify, safety=SafetyConfig(speed_cap_mps=0.0)))
    with TestClient(server.app) as c:
        yield c


def _single_state(msg: dict[str, Any]) -> bool:
    return msg.get("mode") == "single"


def test_bridge_hello_telemetry_and_status(client: TestClient) -> None:
    assert client.get("/api/robot").json()["connected"] is False
    with client.websocket_connect("/ws/robot") as bridge:
        bridge.send_json(HELLO)
        bridge.send_json(_telemetry(x=1.25, y=-0.5, yaw=0.3, battery=77))
        wait_for(lambda: client.get("/api/robot").json()["telemetry"] is not None)
        st = client.get("/api/robot").json()
        assert st["connected"] and st["hello"] and st["mock"] is True
        assert st["limits"]["vx_max"] == 0.4
        assert st["telemetry"]["x"] == 1.25 and st["telemetry"]["battery"] == 77
        assert st["state"] == "standing" and st["estop"] is False
        assert st["latency_ms"] is not None and 0 <= st["latency_ms"] < 1000
        assert any("conectado" in e["text"] for e in st["log"])
    wait_for(lambda: client.get("/api/robot").json()["connected"] is False)


def test_nan_telemetry_stays_valid_json(client: TestClient) -> None:
    with client.websocket_connect("/ws/robot") as bridge:
        bridge.send_text('{"type": "telemetry", "t": NaN, "x": NaN, "y": Infinity, "yaw": null, "state": "moving"}')
        wait_for(lambda: client.get("/api/robot").json()["telemetry"] is not None)
        st = client.get("/api/robot").json()
        json.dumps(st, allow_nan=False)
        assert st["telemetry"]["x"] is None and st["telemetry"]["y"] is None and st["state"] == "moving"


def test_state_payload_carries_real_robot_block(client: TestClient) -> None:
    with client.websocket_connect("/ws") as web:
        msg = recv_until(web, _single_state)
        assert msg["real_robot"]["connected"] is False
        with client.websocket_connect("/ws/robot") as bridge:
            bridge.send_json(HELLO)
            msg = recv_until(web, lambda m: _single_state(m) and m["real_robot"]["hello"])
            assert msg["real_robot"]["mock"] is True
            assert any(e["type"] == "real_link" and "conectado" in e["text"] for e in msg["events"])


def test_teleop_relayed_at_20hz_only_in_manual(client: TestClient) -> None:
    with client.websocket_connect("/ws/robot") as bridge, client.websocket_connect("/ws") as web:
        bridge.send_json(HELLO)
        recv_until(web, _single_state)
        web.send_json({"cmd": "teleop", "fwd": 1, "turn": 0.5, "fast": True})
        with pytest.raises(TimeoutError):
            recv(bridge, 0.4)  # not in Manual: nothing goes to the robot

        web.send_json({"cmd": "manual", "value": True})
        got: list[dict[str, Any]] = []
        t0 = time.monotonic()
        while time.monotonic() - t0 < 1.0:
            web.send_json({"cmd": "teleop", "fwd": 1, "turn": 0.5, "fast": True})
            bridge.send_json(_telemetry())  # a real bridge sends telemetry at 10 Hz (stale > 1 s stops teleop)
            msg = recv(bridge, 0.5)
            assert msg["type"] == "teleop"
            got.append(msg)
        moving = [m for m in got if m["fwd"] == 1.0]
        assert moving, got[:3]
        m = moving[-1]
        assert m["turn"] == 0.5 and m["fast"] is True and m["strafe"] == 0.0
        seqs = [g["seq"] for g in got]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
        assert 12 <= len(got) <= 30, len(got)  # ~20 Hz

        # The viewer stops sending: stale teleop becomes zeros, still at 20 Hz while Manual is on.
        bridge.send_json(_telemetry())
        zero = recv_until(bridge, lambda x: x["type"] == "teleop" and x["fwd"] == 0.0, timeout=1.0)
        assert zero["turn"] == 0.0 and zero["fast"] is False

        web.send_json({"cmd": "manual", "value": False})
        wait_for(lambda: not server.LINK.manual_active(), 1.0)
        tail: list[dict[str, Any]] = []
        for _ in range(20):  # drain what was already sent, then silence
            try:
                tail.append(recv(bridge, 0.3))
            except TimeoutError:
                break
        else:
            raise AssertionError("teleop kept flowing after leaving Manual")
        assert tail and tail[-1]["type"] == "teleop" and tail[-1]["fwd"] == 0.0


def test_actions_and_estop_zero_teleop(client: TestClient) -> None:
    with client.websocket_connect("/ws/robot") as bridge, client.websocket_connect("/ws") as web:
        bridge.send_json(HELLO)
        recv_until(web, _single_state)
        web.send_json({"cmd": "manual", "value": True})
        web.send_json({"cmd": "robot_action", "name": "estop"})
        act = recv_until(bridge, lambda m: m["type"] == "action")
        assert act == {"type": "action", "name": "estop"}
        assert client.get("/api/robot").json()["estop"] is True
        for _ in range(6):
            web.send_json({"cmd": "teleop", "fwd": 1, "turn": 0, "fast": False})
            m = recv_until(bridge, lambda x: x["type"] == "teleop")
            assert m["fwd"] == 0.0  # estop: zeros no matter what the keyboard says
        web.send_json({"cmd": "robot_action", "name": "resume"})
        assert recv_until(bridge, lambda m: m["type"] == "action") == {"type": "action", "name": "resume"}
        for name in ("stand", "lie"):
            assert client.post("/api/robot/action", json={"name": name}).json() == {"ok": True, "sent": True}
            assert recv_until(bridge, lambda m: m["type"] == "action")["name"] == name
        assert client.post("/api/robot/action", json={"name": "passive"}).json()["sent"] is False
        bridge.send_json({"type": "event", "name": "estop", "detail": "botón"})
        msg = recv_until(web, lambda m: _single_state(m) and any(e["type"] == "real_alert" for e in m["events"]))
        alert = [e for e in msg["events"] if e["type"] == "real_alert"][-1]
        assert alert["level"] == "danger" and "parada de emergencia" in alert["text"]


def test_detection_stops_robot_and_files_incident(client: TestClient) -> None:
    det = {"ts": time.time(), "label": "oidio", "conf": 0.93, "p_enfermedad": 0.96, "sospecha": True, "umbral": 0.737,
           "cama": 2, "truth_label": "oidio", "frame": "f_000123.jpg", "source": "rtsp"}
    with client.websocket_connect("/ws/robot") as bridge, client.websocket_connect("/ws") as web:
        bridge.send_json(HELLO)
        recv_until(web, _single_state)
        r = client.post("/api/detection", json=det).json()
        assert r["ok"] and r["forwarded_to_robot"] is True and r["incident_id"] == 1 and r["duplicate"] is False
        stop = recv_until(bridge, lambda m: m["type"] == "detection_stop")
        assert stop["hold_s"] == 4.0 and stop["label"] == "oidio" and stop["conf"] == 0.93

        msg = recv_until(web, lambda m: _single_state(m) and any(i.get("fuente") == "camara_d1" for i in m["incidents"]))
        inc = [i for i in msg["incidents"] if i.get("fuente") == "camara_d1"][-1]
        assert (inc["nave"], inc["cama"], inc["clase"], inc["confianza"]) == (1, 2, "oídio", 0.93)
        assert isinstance(inc["temp_c"], float) and isinstance(inc["rh_pct"], float)
        assert inc["th_fuente"] == "simulado (en producción: sensor a bordo)"
        ev = [e for e in msg["events"] if e["type"] == "real_detection"][-1]
        assert ev["text"].startswith("Cámara del D1: oídio 93 % · Nave 1 · Cama 2 · ")
        assert ev["text"].endswith("% HR (simulado)") and "," in ev["text"].split("·")[-1]
        assert msg["real_robot"]["hold_s_left"] > 0
        assert msg["real_robot"]["truth"]["hits"] == 1

        # Same finding seen again: no second stop, no second incident.
        r2 = client.post("/api/detection", json={**det, "conf": 0.9}).json()
        assert r2["duplicate"] is True and r2["forwarded_to_robot"] is False and r2["incident_id"] == 1
        st = client.get("/api/robot").json()
        assert st["incidents"] == 1 and st["last_detection"]["where"]["cama"] == 2

        # A different disease is a new finding.
        r3 = client.post("/api/detection", json={**det, "label": "alternaria", "truth_label": "alternaria"}).json()
        assert r3["incident_id"] == 2 and r3["forwarded_to_robot"] is True

        # Not suspicious: nothing is sent and no incident.
        r4 = client.post("/api/detection", json={**det, "label": "sana", "sospecha": False, "truth_label": "sana"}).json()
        assert r4["incident_id"] is None and r4["forwarded_to_robot"] is False


def test_detection_without_bridge_or_aruco(client: TestClient) -> None:
    with client.websocket_connect("/ws") as web:
        recv_until(web, _single_state)
        r = client.post("/api/detection", json={"label": "heliothis", "conf": 0.81, "sospecha": True, "cama": None}).json()
        assert r["forwarded_to_robot"] is False and r["incident_id"] == 1
        msg = recv_until(web, lambda m: _single_state(m) and any(e["type"] == "real_detection" for e in m["events"]))
        ev = [e for e in msg["events"] if e["type"] == "real_detection"][-1]
        assert "Heliothis 81 %" in ev["text"]
        robot_x = msg["robot"]["x"]
        bed_x = msg["layout"]["bed_x"]
        nearest = min(range(len(bed_x)), key=lambda b: abs(bed_x[b] - robot_x))
        assert ev["bed"] == nearest
    # No viewer open: still answered, nothing to file.
    r = client.post("/api/detection", json={"label": "oidio", "conf": 0.9, "sospecha": True, "cama": 5}).json()
    assert r["ok"] and r["incident_id"] is None


def test_newest_bridge_replaces_previous(client: TestClient) -> None:
    with client.websocket_connect("/ws/robot") as first:
        first.send_json(HELLO)
        wait_for(lambda: client.get("/api/robot").json()["hello"])
        id1 = client.get("/api/robot").json()["link_id"]
        with client.websocket_connect("/ws/robot") as second:
            second.send_json({**HELLO, "mock": False})
            wait_for(lambda: client.get("/api/robot").json()["mock"] is False)
            st = client.get("/api/robot").json()
            assert st["connected"] and st["link_id"] == id1 + 1


def test_truth_tally_one_verdict_per_leaf() -> None:
    t = TruthTally()
    now = 1000.0
    for k in range(3):  # oidio leaf, flagged on the 2nd frame → hit with the right class
        t.add("oidio", k >= 1, "oidio", now + k * 0.2)
    snap = t.snapshot()
    assert snap is not None and snap["hits"] == 1 and snap["misses"] == 0 and snap["class_match"] == 1
    for k in range(3):  # healthy leaf flagged → false alarm
        t.add("sana", k == 2, "alternaria", now + 2 + k * 0.2)
    for k in range(2):  # alternaria never flagged → miss
        t.add("alternaria", False, "sana", now + 4 + k * 0.2)
    t.add("sana", False, "sana", now + 6)  # healthy, not flagged
    snap = t.snapshot()
    assert snap is not None
    assert (snap["hits"], snap["false_alarms"], snap["misses"], snap["true_negatives"]) == (1, 1, 1, 1)
    assert snap["leaves"] == 4 and snap["frames"] == 9
    t.add("sana", True, "oidio", now + 20)  # after a long gap the same label is a new leaf
    snap = t.snapshot()
    assert snap is not None and snap["leaves"] == 5 and snap["false_alarms"] == 2


def test_teleop_tick_rules() -> None:
    link = RobotLink(hold_s=4.0, safety=SafetyConfig(speed_cap_mps=0.0))
    assert link.teleop_tick() is None  # no bridge
    link.connected = True
    assert link.teleop_tick() is None  # nobody in Manual
    link.set_manual(1, True)
    link.set_teleop({"fwd": 3, "turn": -2, "strafe": "x", "fast": True}, key=1)
    m = link.teleop_tick()
    assert m is not None and (m["fwd"], m["turn"], m["strafe"], m["fast"]) == (1.0, -1.0, 0.0, True)
    cmd, t = link._teleop[1]
    link._teleop[1] = (cmd, t - 1.0)  # stale
    m = link.teleop_tick()
    assert m is not None and m["fwd"] == 0.0
    link.set_manual(1, False)
    last = link.teleop_tick()
    assert last is not None and last["fwd"] == 0.0  # one explicit stop when leaving Manual
    assert link.teleop_tick() is None


# ---------------------------------------------------------------------------
# Revisión de integración con el puente real (oct-2026)
# ---------------------------------------------------------------------------
def _strict_json(text: str) -> Any:
    """Como JSON.parse del navegador: NaN / Infinity no son JSON válido."""

    def bad(c: str) -> Any:
        raise ValueError(c)

    return json.loads(text, parse_constant=bad)


def recv_raw(ws: Any, timeout: float = 2.0) -> str:
    async def _r() -> Any:
        with anyio.fail_after(timeout):
            return await ws._send_rx.receive()

    msg = ws.portal.call(_r)
    if msg["type"] == "websocket.close":
        raise AssertionError(f"socket closed: {msg}")
    return msg["text"]


def test_viewer_outside_manual_cannot_drive(client: TestClient) -> None:
    """Solo los visores en Manual conducen; antes cualquier /ws podía mandar teleop."""
    with client.websocket_connect("/ws/robot") as bridge, client.websocket_connect("/ws") as driver, \
            client.websocket_connect("/ws") as other:
        bridge.send_json(HELLO)
        recv_until(driver, _single_state)
        recv_until(other, _single_state)
        driver.send_json({"cmd": "manual", "value": True})  # en Manual, sin teclas (pestaña quieta)
        wait_for(lambda: server.LINK.manual_active(), 1.0)
        t0 = time.monotonic()
        got: list[dict[str, Any]] = []
        while time.monotonic() - t0 < 0.8:
            other.send_json({"cmd": "teleop", "fwd": 1, "turn": 0, "fast": False})  # NO está en Manual
            got.append(recv_until(bridge, lambda m: m["type"] == "teleop"))
        assert got and all(m["fwd"] == 0.0 for m in got), [m["fwd"] for m in got][-5:]


def test_two_manual_viewers_latest_moving_command_wins() -> None:
    """Dos visores en Manual: el que está quieto (ceros a 20 Hz) no hace tartamudear al que conduce."""
    link = RobotLink(hold_s=4.0, safety=SafetyConfig(speed_cap_mps=0.0))
    link.connected = True
    link.set_manual(1, True)
    link.set_manual(2, True)
    for _ in range(5):
        link.set_teleop({"fwd": 1, "turn": 0}, key=1)
        link.set_teleop({"fwd": 0, "turn": 0}, key=2)
        m = link.teleop_tick()
        assert m is not None and m["fwd"] == 1.0
    link.set_teleop({"fwd": 0, "turn": 0}, key=1)  # el que conducía suelta: todos en cero -> cero
    m = link.teleop_tick()
    assert m is not None and m["fwd"] == 0.0
    link.set_teleop({"fwd": 1}, key=1)
    link.set_manual(1, False)  # sale de Manual: su última orden ya no cuenta
    m = link.teleop_tick()
    assert m is not None and m["fwd"] == 0.0


def test_fast_must_be_a_real_boolean() -> None:
    link = RobotLink(hold_s=4.0, safety=SafetyConfig(speed_cap_mps=0.0))
    link.connected = True
    link.set_manual(1, True)
    for raw, expected in (("false", False), ("true", False), (1, False), (None, False), (True, True)):
        link.set_teleop({"fwd": 1, "fast": raw}, key=1)
        m = link.teleop_tick()
        assert m is not None and m["fast"] is expected, raw


def test_estop_is_resent_to_a_bridge_that_connects_later(client: TestClient) -> None:
    """El estop es pegajoso en el servidor: un puente que (re)conecta lo recibe antes que nada."""
    with client.websocket_connect("/ws/robot") as first:
        first.send_json(HELLO)
        wait_for(lambda: client.get("/api/robot").json()["hello"])
        assert client.post("/api/robot/action", json={"name": "estop"}).json()["sent"] is True
        assert recv_until(first, lambda m: m["type"] == "action") == {"type": "action", "name": "estop"}
    wait_for(lambda: client.get("/api/robot").json()["connected"] is False)
    assert client.get("/api/robot").json()["estop"] is True
    with client.websocket_connect("/ws/robot") as second:
        second.send_json(HELLO)
        assert recv(second) == {"type": "action", "name": "estop"}
        assert client.get("/api/robot").json()["estop"] is True
        assert client.post("/api/robot/action", json={"name": "resume"}).json()["sent"] is True
        assert recv_until(second, lambda m: m["type"] == "action") == {"type": "action", "name": "resume"}
    with client.websocket_connect("/ws/robot") as third:  # tras Reanudar ya no se reenvía
        third.send_json(HELLO)
        with pytest.raises(TimeoutError):
            recv(third, 0.4)


def test_live_bridge_is_not_replaced_by_a_second_one(client: TestClient) -> None:
    """Dos puentes a la vez (p. ej. un --mock olvidado): antes se turnaban cada ~0,5 s y el estop
    podía ir al equivocado. Ahora el vivo se queda y el segundo se rechaza con un aviso."""
    with client.websocket_connect("/ws/robot") as first:
        first.send_json(HELLO)
        first.send_json(_telemetry())
        wait_for(lambda: client.get("/api/robot").json()["telemetry"] is not None)
        id1 = client.get("/api/robot").json()["link_id"]
        with client.websocket_connect("/ws/robot") as second:
            async def _closed() -> Any:
                with anyio.fail_after(2.0):
                    return await second._send_rx.receive()

            msg = second.portal.call(_closed)
            assert msg["type"] == "websocket.close" and msg["code"] == 4001
        st = client.get("/api/robot").json()
        assert st["connected"] and st["link_id"] == id1
        assert any("rechaz" in e["text"] for e in st["log"])
        assert client.post("/api/robot/action", json={"name": "stand"}).json()["sent"] is True
        assert recv_until(first, lambda m: m["type"] == "action")["name"] == "stand"


def test_detection_with_nan_conf_keeps_viewer_json_valid(client: TestClient) -> None:
    """Un conf NaN del detector dejaba TODOS los estados siguientes inválidos para JSON.parse."""
    with client.websocket_connect("/ws") as web:
        recv_until(web, _single_state)
        r = client.post("/api/detection", content=b'{"label": "oidio", "conf": NaN, "sospecha": true, "cama": 3}',
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200 and r.json()["incident_id"] == 1
        for _ in range(5):
            _strict_json(recv_raw(web))


def test_bridge_reconnect_with_keys_held_needs_release_first(client: TestClient) -> None:
    """Se cae el puente con W apretada y vuelve: no arranca hasta que el visor suelte y vuelva a pulsar.

    El visor deja de mandar mientras el enlace está caído y el servidor rellena con ceros por
    caducidad: esos ceros no prueban que el operador soltó la tecla, así que no rearman.
    """
    with client.websocket_connect("/ws") as web:
        recv_until(web, _single_state)
        with client.websocket_connect("/ws/robot") as first:
            first.send_json(HELLO)
            web.send_json({"cmd": "manual", "value": True})
            wait_for(lambda: server.LINK.manual_active(), 1.0)
            web.send_json({"cmd": "teleop", "fwd": 1, "turn": 0, "fast": False})
            assert recv_until(first, lambda m: m["type"] == "teleop" and m["fwd"] == 1.0)["fwd"] == 1.0
        wait_for(lambda: client.get("/api/robot").json()["connected"] is False)
        time.sleep(0.4)  # enlace caído: el visor no manda (teleop.ts exige realRobot.connected)
        with client.websocket_connect("/ws/robot") as second:
            second.send_json(HELLO)
            got: list[float] = []
            t0 = time.monotonic()
            while time.monotonic() - t0 < 0.6:  # el operador sigue con W apretada
                web.send_json({"cmd": "teleop", "fwd": 1, "turn": 0, "fast": False})
                got.append(recv_until(second, lambda m: m["type"] == "teleop")["fwd"])
            assert got and all(f == 0.0 for f in got), got
            web.send_json({"cmd": "teleop", "fwd": 0, "turn": 0, "fast": False})  # suelta
            time.sleep(0.1)
            web.send_json({"cmd": "teleop", "fwd": 1, "turn": 0, "fast": False})  # vuelve a pulsar
            assert recv_until(second, lambda m: m["type"] == "teleop" and m["fwd"] == 1.0)["fwd"] == 1.0
