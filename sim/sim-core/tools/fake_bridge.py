"""Fake D1 bridge: speaks contract v1 (robot_d1/PROTOCOLO.md) so the link can be tested without the VM.

Connects to /ws/robot as the real d1_bridge.py would, sends `hello`, integrates the `teleop`
commands as a kinematic robot (same limits and SDK clipping as the contract) and sends telemetry
at 10 Hz. Honors `action` (stand, lie, estop, resume) and `detection_stop`, and reconnects on its
own if the server goes away.

    cd sim-core
    .venv/bin/python tools/fake_bridge.py                      # ws://localhost:8000/ws/robot
    .venv/bin/python tools/fake_bridge.py --url ws://192.168.234.20:8000/ws/robot --no-odom

Detection without the camera (another terminal):

    curl -s -X POST http://localhost:8000/api/detection -H 'Content-Type: application/json' \\
      -d '{"ts": 1792780000.5, "label": "oidio", "conf": 0.93, "p_enfermedad": 0.96, "sospecha": true,
           "umbral": 0.737, "cama": 2, "truth_label": "oidio", "frame": null, "source": "dryrun"}'
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from typing import Any

try:
    from websockets.asyncio.client import connect
except ImportError:  # websockets < 13
    from websockets import connect  # type: ignore[no-redef]

TELEOP_TTL_S = 0.3
SDK_MIN = {"vx": 0.05, "vy": 0.1, "wz": 0.02}
SDK_MAX = {"vx": 3.0, "vy": 1.0, "wz": 3.0}


def sdk_clip(v: float, axis: str) -> float:
    """Contract: below the SDK minimum the command is 0, above the maximum it is clipped."""
    a = abs(v)
    if a < SDK_MIN[axis]:
        return 0.0
    return math.copysign(min(a, SDK_MAX[axis]), v)


class FakeD1:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.x = self.y = self.yaw = 0.0
        self.vx = self.vy = self.wz = 0.0
        self.state = "standing"
        self.estop = False
        self.hold_until = 0.0
        self.battery = 92.0
        self.cmd: dict[str, Any] | None = None
        self.cmd_at = -1e9
        self.counts = {"teleop": 0, "action": 0, "detection_stop": 0}
        self.last_seq = 0
        self.watchdog_sent = True

    def limits(self) -> dict[str, float]:
        return {"vx_max": self.args.vx, "vy_max": self.args.vy, "wz_max": self.args.wz}

    def on_message(self, msg: dict[str, Any], events: list[tuple[str, str]]) -> None:
        kind = msg.get("type")
        if kind == "teleop":
            self.counts["teleop"] += 1
            self.last_seq = int(msg.get("seq", 0))
            self.cmd = msg
            self.cmd_at = time.monotonic()
            if self.args.verbose:
                print(f"teleop seq={self.last_seq} fwd={msg.get('fwd')} turn={msg.get('turn')} fast={msg.get('fast')}", flush=True)
        elif kind == "action":
            self.counts["action"] += 1
            name = msg.get("name")
            print(f"action {name}", flush=True)
            if name == "estop":
                self.estop = True
                self.state = "estop"
                events.append(("estop", "botón Parar D1"))
            elif name == "resume":
                self.estop = False
                self.state = "standing"
                events.append(("resume", ""))
            elif name == "stand" and not self.estop:
                self.state = "standing"
                events.append(("stood_up", ""))
            elif name == "lie" and not self.estop:
                self.state = "lying"
                events.append(("lay_down", ""))
        elif kind == "detection_stop":
            self.counts["detection_stop"] += 1
            hold = float(msg.get("hold_s", 4.0))
            print(f"detection_stop hold_s={hold} label={msg.get('label')} conf={msg.get('conf')}", flush=True)
            self.hold_until = time.monotonic() + hold
            events.append(("detection_hold_start", f"{msg.get('label')} {msg.get('conf')}"))

    def step(self, dt: float, events: list[tuple[str, str]]) -> None:
        now = time.monotonic()
        held = now < self.hold_until
        if not held and self.state == "detection_hold":
            self.state = "standing"
            events.append(("detection_hold_end", ""))
        fresh = self.cmd is not None and now - self.cmd_at <= TELEOP_TTL_S
        if fresh:
            self.watchdog_sent = False
        elif not self.watchdog_sent:
            self.watchdog_sent = True
            events.append(("watchdog_zero", "sin teleop en 0,3 s"))
        vx = vy = wz = 0.0
        if fresh and not self.estop and not held and self.state not in ("lying", "passive") and self.cmd:
            fast = bool(self.cmd.get("fast"))
            vx = sdk_clip(float(self.cmd.get("fwd", 0)) * self.args.vx * (2.0 if fast else 1.0), "vx")
            vy = sdk_clip(float(self.cmd.get("strafe", 0) or 0) * self.args.vy, "vy")
            wz = sdk_clip(float(self.cmd.get("turn", 0)) * self.args.wz, "wz")
        self.vx, self.vy, self.wz = vx, vy, wz
        if self.estop:
            self.state = "estop"
        elif held:
            self.state = "detection_hold"
        elif self.state in ("standing", "moving"):
            self.state = "moving" if (vx or vy or wz) else "standing"
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        self.x += (vx * c - vy * s) * dt
        self.y += (vx * s + vy * c) * dt
        self.yaw = math.atan2(math.sin(self.yaw + wz * dt), math.cos(self.yaw + wz * dt))
        self.battery = max(5.0, self.battery - dt * (0.004 if (vx or vy or wz) else 0.001))

    def telemetry(self) -> dict[str, Any]:
        odom = not self.args.no_odom
        age = (time.monotonic() - self.cmd_at) * 1000.0 if self.cmd is not None else None
        return {
            "type": "telemetry", "t": time.time(),
            "x": round(self.x, 4) if odom else None,
            "y": round(self.y, 4) if odom else None,
            "yaw": round(self.yaw, 4) if odom else None,
            "vx": self.vx, "vy": self.vy, "wz": self.wz,
            "state": self.state, "sdk_ok": True, "battery": round(self.battery, 1),
            "last_cmd_age_ms": round(age) if age is not None else None,
        }


async def run_once(robot: FakeD1) -> None:
    args = robot.args
    async with connect(args.url) as ws:
        print(f"conectado a {args.url}", flush=True)
        await ws.send(json.dumps({"type": "hello", "robot": "D1 EDU", "mock": True, "version": 1, "limits": robot.limits()}))
        events: list[tuple[str, str]] = []

        async def reader() -> None:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(msg, dict):
                    robot.on_message(msg, events)

        rtask = asyncio.create_task(reader())
        dt = 1.0 / 50.0
        tel_every = 1.0 / args.hz
        next_tel = time.monotonic()
        next_report = time.monotonic() + 2.0
        try:
            while not rtask.done():
                robot.step(dt, events)
                while events:
                    name, detail = events.pop(0)
                    await ws.send(json.dumps({"type": "event", "name": name, "detail": detail}))
                now = time.monotonic()
                if now >= next_tel:
                    next_tel += tel_every
                    await ws.send(json.dumps(robot.telemetry()))
                if now >= next_report:
                    next_report = now + 2.0
                    c = robot.counts
                    print(
                        f"recibidos: teleop={c['teleop']} (seq {robot.last_seq}) action={c['action']} "
                        f"detection_stop={c['detection_stop']} · odom x={robot.x:.2f} y={robot.y:.2f} "
                        f"yaw={math.degrees(robot.yaw):.0f}° estado={robot.state}",
                        flush=True,
                    )
                await asyncio.sleep(dt)
        finally:
            rtask.cancel()


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--url", default="ws://localhost:8000/ws/robot")
    p.add_argument("--hz", type=float, default=10.0, help="telemetría por segundo")
    p.add_argument("--vx", type=float, default=0.4, help="m/s con fwd=1 (el doble con fast)")
    p.add_argument("--vy", type=float, default=0.25)
    p.add_argument("--wz", type=float, default=0.6, help="rad/s con turn=1")
    p.add_argument("--no-odom", action="store_true", help="x, y, yaw = null (como si el SDK no diera odometría)")
    p.add_argument("--verbose", action="store_true", help="imprime cada teleop")
    args = p.parse_args()
    robot = FakeD1(args)
    while True:
        try:
            await run_once(robot)
        except (OSError, ConnectionError) as e:
            print(f"sin servidor ({e.__class__.__name__}); reintento en 1 s", flush=True)
        except Exception as e:  # noqa: BLE001 — websockets.ConnectionClosed and friends: keep reconnecting
            print(f"conexión cerrada ({e.__class__.__name__}); reintento en 1 s", flush=True)
        robot.cmd = None  # like the real bridge: zero velocity while disconnected
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
