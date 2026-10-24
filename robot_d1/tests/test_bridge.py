"""Pruebas del puente (d1/bridge.py) con MockRobot y un servidor WebSocket falso en el mismo proceso.

Se usa tiempo real (no reloj falso) porque aquí lo que se prueba es la red y el asyncio.
"""

import asyncio
import json
import time

import pytest_asyncio
from websockets.asyncio.server import serve

from d1.bridge import Bridge
from d1.controller import ControlCore
from d1.sdk import MockRobot

TELEMETRY_KEYS = {"type", "t", "x", "y", "yaw", "vx", "vy", "wz", "state", "sdk_ok", "battery",
                  "last_cmd_age_ms"}


class SimServer:
    """Imita a sim-core: guarda lo que manda el puente y le envía teleop/acciones."""

    def __init__(self):
        self.ws = None
        self.msgs = []
        self.hellos = 0
        self.server = None
        self.port = None
        self.teleop = None          # (fwd, strafe, turn) mientras se envía a 20 Hz
        self.seq = 0
        self._sender = None

    async def handler(self, ws):
        self.ws = ws
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.msgs.append(msg)
                if msg.get("type") == "hello":
                    self.hellos += 1
        except Exception:
            pass
        finally:
            if self.ws is ws:
                self.ws = None

    async def start(self, port=0):
        self.server = await serve(self.handler, "127.0.0.1", port, compression=None)
        self.port = self.server.sockets[0].getsockname()[1]
        self._sender = asyncio.ensure_future(self._send_loop())

    async def stop(self):
        if self._sender:
            self._sender.cancel()
        self.server.close()
        await self.server.wait_closed()
        self.ws = None

    async def send(self, msg):
        if self.ws is not None:
            await self.ws.send(json.dumps(msg))

    async def _send_loop(self):
        while True:
            if self.teleop is not None and self.ws is not None:
                self.seq += 1
                f, s, t = self.teleop
                try:
                    await self.send({"type": "teleop", "fwd": f, "strafe": s, "turn": t,
                                     "fast": False, "seq": self.seq})
                except Exception:
                    pass
            await asyncio.sleep(0.05)

    def of_type(self, kind):
        return [m for m in self.msgs if m.get("type") == kind]

    def events(self):
        return [m["name"] for m in self.of_type("event")]


async def wait_until(cond, timeout=3.0, step=0.02):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        await asyncio.sleep(step)
    return cond()


@pytest_asyncio.fixture
async def setup():
    sim = SimServer()
    await sim.start()
    robot = MockRobot()
    robot.connect()
    core = ControlCore(robot, stand_settle_s=0.3, lie_settle_s=0.3, log=lambda m: None)
    bridge = Bridge(core, robot, f"ws://127.0.0.1:{sim.port}/ws/robot", log=lambda m: None)
    task = asyncio.ensure_future(bridge.run())
    assert await wait_until(lambda: sim.hellos >= 1, 5.0), "el puente no se conectó"
    # Como sim-core con un visor en Manual sin teclas: ceros a 20 Hz. Tras conectar, el puente
    # exige un teleop en cero antes de mover (volver el enlace no arranca el robot solo).
    sim.teleop = (0.0, 0.0, 0.0)
    try:
        yield sim, robot, core, bridge
    finally:
        bridge.stop()
        await asyncio.wait_for(task, 5.0)
        await sim.stop()


async def stand_up(sim, robot):
    await sim.send({"type": "action", "name": "stand"})
    assert await wait_until(lambda: "stood_up" in sim.events(), 3.0)
    assert robot.state == "standing"


async def test_hello_and_telemetry_at_10hz(setup):
    sim, robot, core, bridge = setup
    hello = sim.of_type("hello")[0]
    assert hello == {"type": "hello", "robot": "D1 EDU", "mock": True, "version": 1,
                     "limits": {"vx_max": 0.4, "vy_max": 0.25, "wz_max": 0.6}}
    n0 = len(sim.of_type("telemetry"))
    await asyncio.sleep(1.0)
    n = len(sim.of_type("telemetry")) - n0
    assert 7 <= n <= 13, f"telemetría a {n} Hz"
    tel = sim.of_type("telemetry")[-1]
    assert set(tel) == TELEMETRY_KEYS
    assert tel["state"] == "lying" and tel["sdk_ok"] is True


async def test_teleop_valid_then_expires_at_0_3s(setup):
    sim, robot, core, bridge = setup
    await stand_up(sim, robot)
    sim.teleop = (1.0, 0.0, 0.0)
    assert await wait_until(lambda: abs(robot.cmd[0] - 0.4) < 1e-6, 2.0), robot.cmd
    sim.teleop = None                      # la sim deja de mandar (p. ej. modo Manual apagado)
    t_stop = time.monotonic()
    await asyncio.sleep(0.2)
    assert robot.cmd[0] > 0                # todavía vigente (< 0,3 s)
    assert await wait_until(lambda: robot.cmd == (0.0, 0.0, 0.0), 1.0)
    assert time.monotonic() - t_stop < 0.9
    n = len(robot.moves)
    await asyncio.sleep(0.5)
    assert len(robot.moves) - n >= 8       # sigue mandando move(0,0,0) a ~20 Hz
    assert robot.moves[-1][1:] == (0.0, 0.0, 0.0)
    assert await wait_until(lambda: "watchdog_zero" in sim.events(), 1.0)
    assert await wait_until(lambda: sim.of_type("telemetry")[-1]["state"] == "standing", 1.0)


async def test_estop_blocks_until_resume(setup):
    sim, robot, core, bridge = setup
    await stand_up(sim, robot)
    sim.teleop = (1.0, 0.0, 0.5)
    assert await wait_until(lambda: robot.cmd[0] > 0.3, 2.0)
    await sim.send({"type": "action", "name": "estop"})
    assert await wait_until(lambda: robot.cmd == (0.0, 0.0, 0.0), 0.3)   # inmediato, sin rampa
    await asyncio.sleep(0.6)                                             # teleop sigue llegando
    assert robot.cmd == (0.0, 0.0, 0.0)
    assert robot.state == "standing"                                     # no passive: no se cae
    assert sim.of_type("telemetry")[-1]["state"] == "estop"
    assert "estop" in sim.events()
    await sim.send({"type": "action", "name": "resume"})
    await asyncio.sleep(0.5)                                             # teclas aún apretadas
    assert robot.cmd == (0.0, 0.0, 0.0)                                  # Reanudar no arranca solo
    sim.teleop = (0.0, 0.0, 0.0)                                         # suelta...
    await asyncio.sleep(0.15)
    sim.teleop = (1.0, 0.0, 0.5)                                         # ...y vuelve a pulsar
    assert await wait_until(lambda: robot.cmd[0] > 0.3, 2.0)
    assert "resume" in sim.events()


async def test_detection_stop_holds_then_releases(setup):
    sim, robot, core, bridge = setup
    await stand_up(sim, robot)
    sim.teleop = (1.0, 0.0, 0.0)
    assert await wait_until(lambda: robot.cmd[0] > 0.3, 2.0)
    await sim.send({"type": "detection_stop", "hold_s": 0.8, "label": "oidio", "conf": 0.93})
    assert await wait_until(lambda: robot.cmd == (0.0, 0.0, 0.0), 0.5)
    await asyncio.sleep(0.4)
    assert robot.cmd == (0.0, 0.0, 0.0)                     # ignora el teleop mientras dura
    assert await wait_until(lambda: sim.of_type("telemetry")[-1]["state"] == "detection_hold", 0.5)
    assert await wait_until(lambda: robot.cmd[0] > 0.3, 2.0)
    assert "detection_hold_start" in sim.events()
    assert await wait_until(lambda: "detection_hold_end" in sim.events(), 1.0)


async def test_ws_drop_gives_continuous_zero_and_reconnects(setup):
    sim, robot, core, bridge = setup
    await stand_up(sim, robot)
    sim.teleop = (1.0, 0.0, 0.0)
    assert await wait_until(lambda: robot.cmd[0] > 0.3, 2.0)
    # Se cae el servidor entero (Mac dormido, Wi-Fi caído...).
    await sim.stop()
    assert await wait_until(lambda: robot.cmd == (0.0, 0.0, 0.0), 0.8)
    n = len(robot.moves)
    await asyncio.sleep(1.0)
    assert len(robot.moves) - n >= 15                       # cero continuo, el robot queda de pie
    assert robot.state == "standing"
    assert all(m[1:] == (0.0, 0.0, 0.0) for m in list(robot.moves)[n:])
    assert not bridge.connected
    # Vuelve el servidor en el mismo puerto: el puente reconecta solo y manda hello otra vez.
    port = sim.port
    sim2 = SimServer()
    await sim2.start(port)
    try:
        assert await wait_until(lambda: sim2.hellos >= 1, 5.0), "no reconectó"
        sim2.teleop = (1.0, 0.0, 0.0)          # el operador seguía con W apretada
        await asyncio.sleep(0.6)
        assert robot.cmd == (0.0, 0.0, 0.0)    # reconectar no arranca el robot por sí solo
        sim2.teleop = (0.0, 0.0, 0.0)          # suelta...
        await asyncio.sleep(0.15)
        sim2.teleop = (1.0, 0.0, 0.0)          # ...y vuelve a pulsar
        assert await wait_until(lambda: robot.cmd[0] > 0.3, 2.0)
    finally:
        sim2.teleop = None
        await sim2.stop()
        sim.server = sim2.server   # para que el fixture no falle al cerrar


async def test_garbage_messages_are_ignored(setup):
    sim, robot, core, bridge = setup
    await stand_up(sim, robot)
    for raw in ["no json", "[]", '{"type": "teleop", "fwd": "NaN", "turn": null}',
                '{"type": "teleop", "fwd": 99, "turn": true}', '{"type": "zzz"}']:
        await sim.ws.send(raw)
    await asyncio.sleep(0.2)
    assert bridge.connected
    assert abs(robot.cmd[0]) <= 0.4 + 1e-9 and robot.cmd[2] == 0.0     # 99 se recorta; true -> 0
