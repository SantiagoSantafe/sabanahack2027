"""Puente asyncio entre el servidor de la simulación (Mac) y el D1 (contrato v1, PROTOCOLO.md).

- Cliente WebSocket a ws://<IP_MAC>:8000/ws/robot con reconexión automática.
- Lazo de control a 20 Hz SIEMPRE activo (aunque no haya WebSocket): manda move() con lo que
  diga el núcleo (ControlCore). Sin teleop vigente => move(0,0,0) continuo.
- Telemetría a 10 Hz y eventos mientras haya conexión.
- Si se cae el WebSocket: se borra el teleop de la simulación (velocidad cero) y se reintenta.
"""

from __future__ import annotations

import asyncio
import json

from collections import deque
from typing import Callable, Optional

from . import PROTOCOL_VERSION
from .controller import ControlCore
from .keyboard import KeyboardDriver
from .sdk import RobotBase, StallGuard

try:  # websockets >= 13 (implementación asyncio nueva)
    from websockets.asyncio.client import connect as _ws_connect
except ImportError:  # pragma: no cover - versiones viejas
    from websockets import connect as _ws_connect  # type: ignore


def ws_connect(url: str, **kw):
    """connect() sin proxy del entorno (websockets>=15 lo usa por defecto) y sin compresión."""
    base = dict(open_timeout=3, ping_interval=2, ping_timeout=3, close_timeout=1,
                compression=None, max_size=2 ** 20)
    base.update(kw)
    try:
        return _ws_connect(url, proxy=None, **base)
    except TypeError:  # websockets < 15 no acepta proxy=
        return _ws_connect(url, **base)


def _int_or_none(v) -> Optional[int]:
    if isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class Bridge:
    def __init__(self, core: ControlCore, robot: RobotBase, url: str, hz: float = 20.0,
                 telemetry_hz: float = 10.0, keyboard: Optional[KeyboardDriver] = None,
                 guard: Optional[StallGuard] = None, log: Callable[[str], None] = print,
                 status: Optional[Callable[[str], None]] = None):
        self.core = core
        self.robot = robot
        self.url = url
        self.period = 1.0 / hz
        self.tel_period = 1.0 / telemetry_hz
        self.keyboard = keyboard
        self.guard = guard
        self.log = log
        self.status = status
        self.connected = False
        self.ws = None
        self.ws_latency_ms: Optional[float] = None
        self.reconnects = 0
        self.rx_count = 0
        self.tx_telemetry = 0
        self._outbox: deque = deque(maxlen=200)
        self._stop: Optional[asyncio.Event] = None
        self._unknown_types: set = set()
        self._last_conn_err = ""
        self.slow_ticks = 0

    # ------------------------------------------------------------------ mensajes
    def hello(self) -> dict:
        lim = self.core.limits
        return {
            "type": "hello",
            "robot": "D1 EDU",
            "mock": bool(self.robot.is_mock),
            "version": PROTOCOL_VERSION,
            "limits": {"vx_max": lim.vx_max, "vy_max": lim.vy_max, "wz_max": lim.wz_max},
        }

    def handle_message(self, raw) -> None:
        try:
            msg = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(msg, dict):
            return
        self.rx_count += 1
        kind = msg.get("type")
        core = self.core
        if kind == "teleop":
            core.set_teleop("sim", msg.get("fwd", 0.0), msg.get("strafe", 0.0), msg.get("turn", 0.0),
                            msg.get("fast") is True, seq=_int_or_none(msg.get("seq")))
        elif kind == "action":
            name = msg.get("name")
            if name == "stand":
                core.request_stand()
            elif name == "lie":
                core.request_lie()
            elif name == "estop":
                core.estop("sim", "botón de la simulación")
            elif name == "resume":
                core.resume("sim")
            else:
                self.log(f"[ws] acción desconocida: {name!r}")
        elif kind == "detection_stop":
            core.detection_stop(msg.get("hold_s"), msg.get("label"), msg.get("conf"))
            self.log(f"[ws] detection_stop label={msg.get('label')} conf={msg.get('conf')} "
                     f"hold_s={msg.get('hold_s')}")
        elif kind not in self._unknown_types:
            self._unknown_types.add(kind)
            self.log(f"[ws] tipo de mensaje desconocido (se ignora): {kind!r}")

    # ------------------------------------------------------------------ tareas
    async def control_loop(self) -> None:
        loop = asyncio.get_running_loop()
        next_t = loop.time()
        while not self._stop.is_set():
            t0 = loop.time()
            now = self.core.clock()
            if self.keyboard is not None:
                self.keyboard.push(now)
                if self.keyboard.quit_requested:
                    self.log("[teclado] salida pedida")
                    self._stop.set()
                    break
            self.core.tick(now)
            if self.guard is not None:
                self.guard.beat(armed=self.core.standing)
            for name, detail in self.core.pop_events():
                self.log(f"[evento] {name}: {detail}")
                if self.connected:
                    self._outbox.append({"type": "event", "name": name, "detail": detail})
            if self.status is not None:
                self.status(self.status_line())
            elapsed = loop.time() - t0
            if elapsed > 0.1:
                self.slow_ticks += 1
                self.log(f"[control] tick lento: {elapsed * 1000:.0f} ms (¿llamada del SDK bloqueante?)")
            next_t += self.period
            delay = next_t - loop.time()
            if delay < -self.period:      # nos atrasamos: no intentar recuperar ticks perdidos
                next_t = loop.time()
                delay = 0
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=max(0.0, delay))
            except asyncio.TimeoutError:
                pass

    async def _telemetry_loop(self, ws) -> None:
        loop = asyncio.get_running_loop()
        next_t = loop.time()
        while True:
            while self._outbox:
                await ws.send(json.dumps(self._outbox.popleft()))
            await ws.send(json.dumps(self.core.telemetry()))
            self.tx_telemetry += 1
            lat = getattr(ws, "latency", None)
            if isinstance(lat, (int, float)) and lat > 0:
                self.ws_latency_ms = lat * 1000.0
            next_t += self.tel_period
            await asyncio.sleep(max(0.0, next_t - loop.time()))

    async def ws_loop(self) -> None:
        backoff = 0.5
        while not self._stop.is_set():
            try:
                async with ws_connect(self.url) as ws:
                    self.ws = ws
                    self.connected = True
                    self._outbox.clear()
                    self.core.clear_teleop("sim")      # seq nuevo para esta conexión
                    self.core.require_neutral("sim")   # volver el enlace no arranca el robot solo
                    backoff = 0.5
                    self._last_conn_err = ""
                    await ws.send(json.dumps(self.hello()))
                    self.log(f"[ws] conectado a {self.url}")
                    tel = asyncio.ensure_future(self._telemetry_loop(ws))
                    try:
                        async for raw in ws:
                            self.handle_message(raw)
                            if tel.done():
                                break
                    finally:
                        tel.cancel()
                        try:
                            await tel
                        except BaseException:
                            pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - cualquier fallo de red => reintentar
                err = f"{type(exc).__name__}: {exc}"
                if err != self._last_conn_err:
                    self.log(f"[ws] sin conexión con {self.url} ({err}); reintento automático")
                    self._last_conn_err = err
            finally:
                if self.connected:
                    self.log("[ws] conexión caída: velocidad a cero, el robot queda de pie; reconectando")
                    self.reconnects += 1
                self.connected = False
                self.ws = None
                self.ws_latency_ms = None
                self.core.clear_teleop("sim")
            if self._stop.is_set():
                break
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 3.0)

    # ------------------------------------------------------------------ ciclo de vida
    def status_line(self) -> str:
        if self.connected:
            lat = "" if self.ws_latency_ms is None else f" {self.ws_latency_ms:.0f}ms"
            ws = f"[WS ok{lat}]"
        else:
            ws = "[WS --]"
        return f"{ws} {self.core.status_line()}"

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    async def run(self) -> None:
        self._stop = asyncio.Event()
        tasks = [asyncio.ensure_future(self.control_loop()), asyncio.ensure_future(self.ws_loop())]
        stop_task = asyncio.ensure_future(self._stop.wait())
        try:
            done, _ = await asyncio.wait([stop_task, *tasks], return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                if t is not stop_task and not t.cancelled() and t.exception() is not None:
                    self.log(f"[puente] una tarea murió: {t.exception()!r}. Salida segura.")
        finally:
            stop_task.cancel()
            self._stop.set()
            ws = self.ws
            if ws is not None:
                try:
                    await asyncio.wait_for(ws.close(), timeout=1.0)
                except BaseException:
                    pass
            for t in tasks:
                t.cancel()
            for t in tasks:
                try:
                    await t
                except BaseException:
                    pass
