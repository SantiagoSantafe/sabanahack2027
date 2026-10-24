#!/usr/bin/env python3
"""Puente entre la simulación del Mac (sim-core :8000) y el D1 EDU (contrato v1, PROTOCOLO.md).

Ejemplos:
    python3.10 d1_bridge.py --mac-ip 192.168.234.23                 # robot real por Wi-Fi
    python3.10 d1_bridge.py --mac-ip 192.168.234.23 --local-keys    # + teclado de la VM
    python3 d1_bridge.py --mac-ip 127.0.0.1 --mock                  # sin robot (para probar)

El puente es CLIENTE: se conecta a ws://<IP_MAC>:8000/ws/robot y reconecta solo.
Sin teleop vigente (0,3 s) manda move(0,0,0) continuo. Ctrl-C = salida segura (cero y acostarse).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from d1.bridge import Bridge  # noqa: E402
from d1.config import add_common_args, build_config  # noqa: E402
from d1.console import Console  # noqa: E402
from d1.controller import ControlCore  # noqa: E402
from d1.keyboard import HELP_TEXT, HoldTracker, KeyboardDriver, TerminalKeys  # noqa: E402
from d1.sdk import (MockRobot, RealRobot, StallGuard, connect_with_timeout,  # noqa: E402
                    network_warnings)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Puente WebSocket simulación <-> D1 EDU (contrato v1).")
    add_common_args(ap)
    s = ap.add_argument_group("simulación")
    s.add_argument("--mac-ip", help="IP del Mac con sim-core (o variable MAC_IP)")
    s.add_argument("--ws-port", type=int, help="puerto de sim-core (por defecto 8000)")
    s.add_argument("--url", help="URL WebSocket completa (sustituye a --mac-ip/--ws-port)")
    ap.add_argument("--local-keys", action="store_true",
                    help="el teclado de esta terminal también manda (Espacio = estop local, siempre gana)")
    ap.add_argument("--auto-stand", action="store_true", help="pararse al arrancar (por defecto: botón stand o U)")
    ap.add_argument("--mock-battery", type=int, default=87,
                    help="batería inicial del robot simulado (para probar las barreras de batería)")
    ap.add_argument("--no-lie-on-exit", action="store_true", help="no acostarse al salir")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    cfg = build_config(args)
    con = Console()
    url = args.url or cfg.ws_url()
    if not url:
        con.log("Falta la IP del Mac: usa --mac-ip <IP> (o MAC_IP=<IP>), p. ej. --mac-ip 192.168.234.23")
        return 2

    if args.mock:
        robot = MockRobot(battery=args.mock_battery)
        robot.connect()
        con.log("Robot SIMULADO (--mock): el puente funciona igual pero nada se mueve de verdad.")
    else:
        robot = RealRobot(cfg.robot_ip, cfg.local_ip, cfg.local_port, cfg.sdk_path)
        con.log(f"Conectando al D1 en {cfg.robot_ip} (puerto local {cfg.local_port})...")
        try:
            connect_with_timeout(robot, timeout_s=15.0)
        except Exception as exc:
            con.log(f"ERROR al conectar con el robot: {exc}")
            return 1
        con.log(f"SDK cargado desde {robot.lib_dir}; IP local {robot.local_ip}")
        for w in network_warnings(robot.local_ip, cfg.robot_ip):
            con.log("AVISO: " + w)
        con.log(f"Recuerda: en el robot, /opt/export/config/sdk_config.yaml debe tener "
                f"target_ip: \"{robot.local_ip}\" (guía 3.7).")

    core = ControlCore(robot, cfg.limits, cfg.accel,
                       teleop_ttl_s=cfg.control("teleop_ttl_s"),
                       stand_settle_s=cfg.control("stand_settle_s"),
                       lie_settle_s=cfg.control("lie_settle_s"),
                       lie_zero_s=cfg.control("lie_zero_s"), log=con.log,
                       battery_stand_min=cfg.control("battery_stand_min"),
                       battery_lie_below=cfg.control("battery_lie_below"))
    guard = StallGuard(robot, stall_s=cfg.control("stall_guard_s"), log=con.log).start()

    driver = None
    term = None
    if args.local_keys:
        if not sys.stdin.isatty():
            con.log("--local-keys necesita una terminal interactiva; sigo sin teclado local.")
        else:
            term = TerminalKeys(HoldTracker(float(cfg.keyboard("initial_hold_s")),
                                            float(cfg.keyboard("repeat_hold_s"))))
            driver = KeyboardDriver(core, cfg.speed_levels, int(cfg.keyboard("speed_level")), log=con.log)
            driver.backend = term
            con.log(HELP_TEXT)

    bridge = Bridge(core, robot, url, hz=cfg.control("hz"), telemetry_hz=cfg.control("telemetry_hz"),
                    keyboard=driver, guard=guard, log=con.log, status=con.status)
    con.log(f"Puente activo -> {url}  (Ctrl-C para salir)")
    if args.auto_stand:
        core.request_stand()

    async def runner():
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, bridge.stop)
            except (NotImplementedError, RuntimeError):
                pass
        if term is not None and term.enabled:
            def on_key():
                driver.handle_events(term.read_available(core.clock()))
                if driver.quit_requested:
                    bridge.stop()
            loop.add_reader(term.fd, on_key)
        try:
            await bridge.run()
        finally:
            if term is not None and term.enabled:
                loop.remove_reader(term.fd)

    exit_code = 0
    try:
        if term is not None:
            term.__enter__()
        asyncio.run(runner())
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001
        con.log(f"ERROR en el puente: {exc!r}")
        exit_code = 1
    finally:
        if term is not None:
            term.restore()
        con.end()
        con.log("Salida segura: velocidad cero" + ("" if args.no_lie_on_exit else " y acostarse"))
        guard.stop()   # el lazo ya paró; la secuencia de salida manda los ceros ella misma
        core.shutdown(lie=not args.no_lie_on_exit)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
