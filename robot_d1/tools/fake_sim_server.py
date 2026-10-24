#!/usr/bin/env python3
"""Servidor WebSocket mínimo que imita a sim-core (contrato v1) para probar el puente sin la simulación.

Corre en el Mac (o en cualquier máquina):
    python3 tools/fake_sim_server.py                    # teclado del Mac (por defecto si hay terminal)
    python3 tools/fake_sim_server.py --mode pattern     # patrón automático: pararse, adelante, girar...
    python3 tools/fake_sim_server.py --port 8000 --host 0.0.0.0

Expone:
    ws://<host>:8000/ws/robot     el puente (d1_bridge.py) se conecta aquí
    GET http://<host>:8000/api/robot   estado del enlace (lo usa scripts/check_red.sh)

Teclas (modo keys): W/S/A/D/Q/E mover (Shift = rápido), U pararse, L acostarse, ESPACIO estop,
R reanudar, P simular detección (detection_stop 4 s), H ayuda, Ctrl-C o Esc salir.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from d1.console import Console  # noqa: E402
from d1.keyboard import HoldTracker, TerminalKeys  # noqa: E402

try:
    from websockets.asyncio.server import serve
except ImportError:  # pragma: no cover
    sys.exit("Necesitas websockets >= 13:  pip install 'websockets>=13'")

HELP = ("Teclas: W/S/A/D/Q/E mover (Shift=rápido) | U pararse | L acostarse | ESPACIO estop | "
        "R reanudar | P detección | H ayuda | Ctrl-C/Esc salir")

# Patrón: (segundos, fwd, strafe, turn). Se repite. Arranca con action "stand".
PATTERN = [
    (3.0, 0.0, 0.0, 0.0),
    (2.0, 1.0, 0.0, 0.0),
    (1.0, 0.0, 0.0, 0.0),
    (2.0, 0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0, 0.0),
    (2.0, -1.0, 0.0, 0.0),
    (1.0, 0.0, 0.0, 0.0),
    (2.0, 0.0, 0.0, -1.0),
    (1.0, 0.0, 0.0, 0.0),
]


class FakeSim:
    def __init__(self, mode: str, con: Console, pattern_scale: float = 0.6, hz: float = 20.0):
        self.mode = mode
        self.con = con
        self.pattern_scale = pattern_scale
        self.period = 1.0 / hz
        self.ws = None
        self.hello: Optional[dict] = None
        self.last_tel: Optional[dict] = None
        self.last_tel_rx: Optional[float] = None
        self.connected_since: Optional[float] = None
        self.seq = 0
        self.manual = True
        self.hold = HoldTracker(0.6, 0.15)
        self.term = TerminalKeys(self.hold) if mode == "keys" else None
        self.stop_event: Optional[asyncio.Event] = None
        self.pattern_t0: Optional[float] = None

    # ---------------------------------------------------------------- HTTP /api/robot
    def api_robot(self) -> dict:
        lat = None
        if self.ws is not None:
            l = getattr(self.ws, "latency", None)
            lat = round(l * 1000, 1) if isinstance(l, (int, float)) else None
        return {
            "connected": self.ws is not None,
            "mock": None if not self.hello else self.hello.get("mock"),
            "hello": self.hello,
            "last_telemetry": self.last_tel,
            "telemetry_age_ms": None if self.last_tel_rx is None else int((time.time() - self.last_tel_rx) * 1000),
            "latency_ms": lat,
            "server": "fake_sim_server.py",
        }

    def process_request(self, connection, request):
        path = request.path.split("?")[0]
        if path == "/ws/robot":
            return None  # seguir con el handshake WebSocket
        if path == "/api/robot":
            body = json.dumps(self.api_robot(), indent=1)
            try:
                from websockets.datastructures import Headers
                from websockets.http11 import Response
                data = body.encode()
                return Response(200, "OK", Headers([("Content-Type", "application/json"),
                                                    ("Content-Length", str(len(data)))]), data)
            except Exception:
                return connection.respond(200, body + "\n")
        return connection.respond(404, "Solo /ws/robot y /api/robot\n")

    # ---------------------------------------------------------------- WebSocket
    async def handler(self, ws) -> None:
        if self.ws is not None:
            self.con.log("[sim] llegó otro puente; el nuevo reemplaza al anterior")
        self.ws = ws
        self.connected_since = time.time()
        self.pattern_t0 = None
        self.con.log(f"[sim] puente conectado desde {getattr(ws, 'remote_address', '?')}")
        sender = asyncio.ensure_future(self.teleop_sender(ws))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                kind = msg.get("type")
                if kind == "hello":
                    self.hello = msg
                    self.con.log(f"[sim] hello: {json.dumps(msg)}")
                elif kind == "telemetry":
                    self.last_tel = msg
                    self.last_tel_rx = time.time()
                elif kind == "event":
                    self.con.log(f"[sim] evento del puente: {msg.get('name')} — {msg.get('detail')}")
        except Exception as exc:
            self.con.log(f"[sim] conexión terminada: {type(exc).__name__}")
        finally:
            sender.cancel()
            if self.ws is ws:
                self.ws = None
            self.con.log("[sim] puente desconectado")

    async def send(self, msg: dict) -> None:
        ws = self.ws
        if ws is None:
            return
        try:
            await ws.send(json.dumps(msg))
        except Exception:
            pass

    def current_axes(self, now: float):
        if self.mode == "pattern":
            if self.pattern_t0 is None:
                self.pattern_t0 = now
                asyncio.ensure_future(self.send({"type": "action", "name": "stand"}))
                self.con.log("[sim] patrón: action stand")
            total = sum(p[0] for p in PATTERN)
            t = (now - self.pattern_t0) % total
            for dur, f, s, w in PATTERN:
                if t < dur:
                    k = self.pattern_scale
                    return f * k, s * k, w * k, False
                t -= dur
            return 0.0, 0.0, 0.0, False
        if self.term is None:
            return 0.0, 0.0, 0.0, False
        return self.term.axes(now)

    async def teleop_sender(self, ws) -> None:
        loop = asyncio.get_running_loop()
        next_t = loop.time()
        while True:
            now = time.monotonic()
            if self.term is not None and self.term._pending:   # Esc suelto pendiente
                if any(e.key == "quit" for e in self.term.feed("", now)):
                    self.stop_event.set()
            fwd, strafe, turn, fast = self.current_axes(now)
            self.seq += 1
            await ws.send(json.dumps({"type": "teleop", "fwd": fwd, "strafe": strafe, "turn": turn,
                                      "fast": bool(fast), "seq": self.seq}))
            tel = self.last_tel or {}
            self.con.status(
                f"[sim] envío fwd={fwd:+.2f} str={strafe:+.2f} turn={turn:+.2f}{' RÁPIDO' if fast else ''} | "
                f"robot: {tel.get('state', '?')} vx={_f(tel.get('vx'))} vy={_f(tel.get('vy'))} "
                f"wz={_f(tel.get('wz'))} x={_f(tel.get('x'))} y={_f(tel.get('y'))} "
                f"yaw={_f(tel.get('yaw'))} bat={tel.get('battery')} sdk_ok={tel.get('sdk_ok')}")
            next_t += self.period
            await asyncio.sleep(max(0.0, next_t - loop.time()))

    # ---------------------------------------------------------------- teclado del Mac
    def on_key(self) -> None:
        for ev in self.term.read_available(time.monotonic()):
            if ev.kind != "action":
                continue
            name = ev.key
            if name == "quit":
                self.stop_event.set()
            elif name == "help":
                self.con.log(HELP)
            elif name in ("stand", "lie", "estop", "resume"):
                self.con.log(f"[sim] action {name}")
                asyncio.ensure_future(self.send({"type": "action", "name": name}))
        # P = detección simulada (no está en el mapa de teclas del robot)

    def on_raw(self, data: str) -> None:
        if "p" in data.lower():
            self.con.log("[sim] detection_stop simulado (oidio 0.93, 4 s)")
            asyncio.ensure_future(self.send({"type": "detection_stop", "hold_s": 4,
                                             "label": "oidio", "conf": 0.93}))


def _f(v) -> str:
    return "—" if v is None else f"{v:+.2f}"


async def amain(args) -> None:
    con = Console()
    mode = args.mode
    if mode == "keys" and not sys.stdin.isatty():
        con.log("No hay terminal interactiva: uso --mode pattern")
        mode = "pattern"
    sim = FakeSim(mode, con, pattern_scale=args.pattern_scale)
    sim.stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, sim.stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass
    if sim.term is not None:
        sim.term.__enter__()
        orig_feed = sim.term.feed

        def feed_with_p(data, now):  # interceptar la P antes del parser de teclas
            if data:
                sim.on_raw(data)
            return orig_feed(data, now)
        sim.term.feed = feed_with_p
        loop.add_reader(sim.term.fd, sim.on_key)
        con.log(HELP)
    try:
        async with serve(sim.handler, args.host, args.port, process_request=sim.process_request,
                         ping_interval=2, ping_timeout=3, compression=None):
            con.log(f"[sim] escuchando en ws://{args.host}:{args.port}/ws/robot  (modo {mode})")
            con.log(f"[sim] estado: curl http://<esta_IP>:{args.port}/api/robot")
            await sim.stop_event.wait()
    finally:
        if sim.term is not None:
            loop.remove_reader(sim.term.fd)
            sim.term.restore()
        con.end()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Simulación falsa (contrato v1) para probar d1_bridge.py.")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mode", choices=["keys", "pattern"], default="keys")
    ap.add_argument("--pattern-scale", type=float, default=0.6, help="ejes del patrón (0..1)")
    args = ap.parse_args(argv)
    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
