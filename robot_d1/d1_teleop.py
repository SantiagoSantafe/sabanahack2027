#!/usr/bin/env python3
"""Teleoperación local del D1 EDU con el teclado de la VM (respaldo sin simulación).

Ejemplos:
    python3.10 d1_teleop.py                      # robot real por Wi-Fi (192.168.234.1)
    python3.10 d1_teleop.py --robot-ip 192.168.168.168   # por cable
    python3 d1_teleop.py --mock                  # sin robot (Mac o VM), para practicar
    python3.10 d1_teleop.py --keys pynput        # sabe cuándo sueltas la tecla (X11)

Teclas: W/S adelante/atrás, A/D girar, Q/E lateral, +/- nivel, ESPACIO = parada de emergencia,
R = reanudar, U = pararse, L = acostarse, H = ayuda, Ctrl-C/Esc = salida segura.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from d1.config import add_common_args, build_config  # noqa: E402
from d1.console import Console  # noqa: E402
from d1.controller import ControlCore  # noqa: E402
from d1.keyboard import (HELP_TEXT, HoldTracker, KeyboardDriver, PynputKeys,  # noqa: E402
                         TerminalKeys, pynput_available)
from d1.sdk import (MockRobot, RealRobot, StallGuard, connect_with_timeout,  # noqa: E402
                    network_warnings)


def make_robot(cfg, mock: bool, con: Console):
    if mock:
        return MockRobot()
    robot = RealRobot(cfg.robot_ip, cfg.local_ip, cfg.local_port, cfg.sdk_path)
    con.log(f"Conectando al D1 en {cfg.robot_ip} (puerto local {cfg.local_port})...")
    connect_with_timeout(robot, timeout_s=15.0)
    con.log(f"SDK cargado desde {robot.lib_dir}; IP local {robot.local_ip}")
    for w in network_warnings(robot.local_ip, cfg.robot_ip):
        con.log("AVISO: " + w)
    con.log(f"Recuerda: en el robot, /opt/export/config/sdk_config.yaml debe tener "
            f"target_ip: \"{robot.local_ip}\" (guía 3.7). Si no, no llega nada (FAQ 6.1).")
    return robot


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Teleoperación del D1 EDU por teclado (terminal o pynput).")
    add_common_args(ap)
    ap.add_argument("--keys", choices=["auto", "terminal", "pynput"], default="terminal",
                    help="terminal (sin dependencias, por defecto), pynput (sabe cuándo se suelta) "
                         "o auto (pynput si se puede)")
    ap.add_argument("--auto-stand", action="store_true", help="pararse al arrancar (por defecto: pulsa U)")
    ap.add_argument("--no-lie-on-exit", action="store_true", help="no acostarse al salir")
    ap.add_argument("--initial-hold", type=float, help="retención de la 1ª pulsación (s), por defecto 0.6")
    ap.add_argument("--repeat-hold", type=float, help="retención con autorrepetición (s), por defecto 0.15")
    args = ap.parse_args(argv)
    cfg = build_config(args)
    con = Console()

    if not sys.stdin.isatty():
        print("d1_teleop.py necesita una terminal interactiva (stdin no es una TTY).")
        return 2

    try:
        robot = make_robot(cfg, args.mock, con)
    except Exception as exc:
        con.log(f"ERROR al conectar con el robot: {exc}")
        return 1
    if args.mock:
        robot.connect()
        con.log("Robot SIMULADO (--mock): nada se mueve de verdad.")

    core = ControlCore(robot, cfg.limits, cfg.accel,
                       teleop_ttl_s=cfg.control("teleop_ttl_s"),
                       stand_settle_s=cfg.control("stand_settle_s"),
                       lie_settle_s=cfg.control("lie_settle_s"),
                       lie_zero_s=cfg.control("lie_zero_s"), log=con.log)
    guard = StallGuard(robot, stall_s=cfg.control("stall_guard_s"), log=con.log).start()
    driver = KeyboardDriver(core, cfg.speed_levels, int(cfg.keyboard("speed_level")), log=con.log)

    hold = HoldTracker(args.initial_hold or float(cfg.keyboard("initial_hold_s")),
                       args.repeat_hold or float(cfg.keyboard("repeat_hold_s")))
    term = TerminalKeys(hold)
    pyn = None
    mode = args.keys
    if mode in ("auto", "pynput"):
        ok, why = pynput_available()
        if ok:
            try:
                pyn = PynputKeys(float(cfg.keyboard("release_grace_s")), on_action=driver.handle_action).start()
            except Exception as exc:
                ok, why = False, str(exc)
        if not ok:
            if mode == "pynput":
                con.log(f"pynput no se puede usar ({why}). Usa --keys terminal.")
                guard.stop()
                return 2
            con.log(f"pynput no disponible ({why}); uso el modo terminal.")
    driver.backend = pyn or term
    con.log(f"Teclado: {'pynput (sabe cuándo sueltas)' if pyn else 'terminal (retención por tiempo)'}")
    con.log(HELP_TEXT)

    # SIGTERM también hace salida segura.
    signal.signal(signal.SIGTERM, lambda *_: setattr(driver, "quit_requested", True))

    period = 1.0 / cfg.control("hz")
    exit_code = 0
    with term:
        if args.auto_stand:
            core.request_stand()
        next_t = time.monotonic()
        try:
            while not driver.quit_requested:
                # 1) Teclas: se atienden apenas llegan (Espacio para al instante, sin esperar al tick).
                events = term.read_available(time.monotonic())
                if pyn is not None:
                    # Con pynput, la terminal solo sirve para Espacio/Esc (lo demás lo ve pynput).
                    events = [e for e in events if e.kind == "action" and e.key in ("estop", "quit")]
                driver.handle_events(events)
                if driver.quit_requested:
                    break
                # 2) Tick de control a 20 Hz: siempre llama a move() si el robot está de pie.
                now = time.monotonic()
                if now >= next_t:
                    driver.push(now)
                    core.tick(now)
                    guard.beat(armed=core.standing)
                    for name, detail in core.pop_events():
                        con.log(f"[evento] {name}: {detail}")
                    con.status(core.status_line() + f" nivel={driver.level:.0%}")
                    next_t += period
                    if next_t < now - period:      # atrasados: no recuperar ticks perdidos
                        next_t = now + period
                # 3) Esperar hasta el próximo tick o hasta que llegue una tecla.
                timeout = max(0.0, next_t - time.monotonic())
                if not term.wait_readable(timeout) and not term.enabled:
                    time.sleep(timeout)
        except KeyboardInterrupt:
            pass
        except Exception as exc:  # noqa: BLE001 - salir de forma segura ante cualquier fallo
            con.log(f"ERROR en el lazo: {exc!r}")
            exit_code = 1
        finally:
            con.end()
            con.log("Salida segura: velocidad cero" + ("" if args.no_lie_on_exit else " y acostarse"))
            guard.stop()   # el lazo ya paró; la secuencia de salida manda los ceros ella misma
            if pyn is not None:
                pyn.stop()
            core.shutdown(lie=not args.no_lie_on_exit)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
