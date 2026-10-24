"""Núcleo de control compartido por la teleop (d1_teleop.py) y el puente (d1_bridge.py).

Se llama a `tick()` a 20 Hz. En cada tick:
1. Elige la entrada vigente (teclado local o simulación; un teleop vale 0,3 s).
2. Aplica estop / retención por detección / acostarse pendiente (todas fuerzan cero).
3. Escala a los límites de demo, pasa por la rampa y recorta a los rangos del SDK.
4. Si el robot está de pie, llama SIEMPRE a robot.move(vx, vy, wz) (ceros incluidos).

El reloj es inyectable (`clock`) para poder probarlo con un reloj falso.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .safety import (ZERO, Accel, Limits, RateLimiter3, StopState, Velocity, clamp_unit,
                     clip_to_sdk, is_fresh, is_zero, scale_axes)
from .sdk import CTRL_MODES, RobotBase, describe_code

# Estados del cuerpo según lo que NOSOTROS mandamos (el SDK exige standUp() antes de move()).
BODY_LYING = "lying"
BODY_STANDING_UP = "standing_up"
BODY_STANDING = "standing"
BODY_LYING_DOWN = "lying_down"
BODY_PASSIVE = "passive"

MOVE_OK_BODIES = (BODY_STANDING,)


@dataclass
class TeleopInput:
    fwd: float = 0.0
    strafe: float = 0.0
    turn: float = 0.0
    fast: bool = False
    scale: float = 1.0
    t: Optional[float] = None
    seq: Optional[int] = None


@dataclass
class TickResult:
    sent: bool
    cmd: Velocity
    state: str
    source: Optional[str]


class ControlCore:
    def __init__(self, robot: RobotBase, limits: Limits = Limits(), accel: Accel = Accel(),
                 teleop_ttl_s: float = 0.3, stand_settle_s: float = 2.0,
                 lie_settle_s: float = 2.0, lie_zero_s: float = 0.4,
                 clock: Callable[[], float] = time.monotonic,
                 log: Callable[[str], None] = print,
                 status_period_s: float = 0.5, battery_period_s: float = 2.0,
                 battery_stand_min: float = 25.0, battery_lie_below: float = 15.0):
        self.robot = robot
        self.limits = limits
        self.teleop_ttl_s = teleop_ttl_s
        self.stand_settle_s = stand_settle_s
        self.lie_settle_s = lie_settle_s
        self.lie_zero_s = lie_zero_s
        self.clock = clock
        self.log = log
        self.status_period_s = status_period_s
        self.battery_period_s = battery_period_s
        # Barrera de batería (integración con el gemelo): < stand_min no se permite pararse;
        # < lie_below se acuesta solo, con cero primero (request_lie). Apagar con 0.
        self.battery_stand_min = battery_stand_min
        self.battery_lie_below = battery_lie_below
        self._battery_crit_reported = False

        self.lock = threading.RLock()
        self.limiter = RateLimiter3(accel)
        self.stops = StopState()
        self.inputs: Dict[str, TeleopInput] = {}
        self.body = BODY_LYING
        self.body_until: Optional[float] = None
        self.lie_pending = False
        self.zero_since: Optional[float] = None
        self.applied: Velocity = ZERO
        self.active_source: Optional[str] = None
        self.last_tick: Optional[float] = None
        self.last_teleop_t: Optional[float] = None
        self._expired_nonzero: Dict[str, bool] = {}
        # Fuentes que deben pasar por neutro antes de mover: rearmar no arranca el robot por sí
        # solo (ISO 13850). Valor False = vale soltar las teclas o que el teleop caduque (tras
        # Reanudar o pararse); True = estricto, solo un teleop en cero (tras reconectar el enlace).
        self._need_neutral: Dict[str, bool] = {}
        self._events: List[Tuple[str, str]] = []

        # Estado leído del SDK (cacheado; se refresca a menor frecuencia que el lazo)
        self.sdk_ok = False
        self.battery: Optional[int] = None
        self.ctrl_mode: Optional[int] = None
        self.pose = None
        self._next_status = 0.0
        self._next_battery = 0.0
        self._last_sdk_error_t: Optional[float] = None
        self._last_err_report: Dict[str, float] = {}
        self._battery_warned = 101
        self.move_count = 0

    # ------------------------------------------------------------------ eventos
    def _emit(self, events) -> None:
        for name, detail in events:
            self._events.append((name, detail))

    def pop_events(self) -> List[Tuple[str, str]]:
        with self.lock:
            ev, self._events = self._events, []
            return ev

    def _sdk_error(self, key: str, detail: str, now: float, every_s: float = 2.0) -> None:
        self._last_sdk_error_t = now
        last = self._last_err_report.get(key)
        if last is None or now - last >= every_s:
            self._last_err_report[key] = now
            self._emit([("sdk_error", detail)])

    # ------------------------------------------------------------------ entradas
    def set_teleop(self, source: str, fwd, strafe, turn, fast=False, scale: float = 1.0,
                   seq: Optional[int] = None, now: Optional[float] = None) -> bool:
        """Registra un comando de teleop. Devuelve False si se descartó (seq viejo)."""
        with self.lock:
            now = self.clock() if now is None else now
            prev = self.inputs.get(source)
            if (seq is not None and prev is not None and prev.seq is not None
                    and seq <= prev.seq and prev.seq - seq < 1000):
                return False  # duplicado o fuera de orden (un salto grande = la sim reinició)
            self.inputs[source] = TeleopInput(fwd, strafe, turn, fast is True, scale, now, seq)
            self.last_teleop_t = now
            if not _nonzero(fwd, strafe, turn):
                self._need_neutral.pop(source, None)
            return True

    def _require_neutral(self) -> None:
        """Tras Reanudar / pararse: las fuentes con teclas apretadas deben soltarlas antes de mover."""
        for s in self.inputs:
            self._need_neutral.setdefault(s, False)

    def require_neutral(self, source: str) -> None:
        """Tras (re)conectar el enlace de `source`: no mover hasta recibir de él un teleop en cero."""
        with self.lock:
            self._need_neutral[source] = True

    def clear_teleop(self, source: str) -> None:
        with self.lock:
            self.inputs.pop(source, None)

    def estop(self, source: str, reason: str = "") -> None:
        with self.lock:
            ev = self.stops.estop(source, reason)
            # Parada inmediata: sin rampa.
            self.limiter.reset(ZERO)
            self._emit(ev)

    def resume(self, source: str) -> bool:
        with self.lock:
            ok, ev = self.stops.resume(source)
            if not ok:
                self.log("[control] resume ignorado: el estop LOCAL está activo; pulsa R en la VM")
            if ev:  # de verdad estaba en estop
                self._require_neutral()
            self._emit(ev)
            return ok

    def detection_stop(self, hold_s=None, label=None, conf=None, now: Optional[float] = None) -> None:
        with self.lock:
            now = self.clock() if now is None else now
            self._emit(self.stops.detection_stop(now, hold_s, label, conf))

    def request_stand(self, now: Optional[float] = None) -> bool:
        with self.lock:
            now = self.clock() if now is None else now
            if self.stops.estopped:
                self.log("[control] no me paro: estop activo (R para reanudar)")
                return False
            if self.body in (BODY_STANDING, BODY_STANDING_UP):
                self.log("[control] ya está de pie")
                return False
            if (self.battery_stand_min and self.battery is not None and self.sdk_ok
                    and self.battery < self.battery_stand_min):
                msg = (f"batería {self.battery}% < {self.battery_stand_min:.0f}%: no me paro "
                       "(cargar el robot antes)")
                self.log(f"[control] {msg}")
                self._emit([("battery_low", msg)])
                return False
            if self.body == BODY_LYING_DOWN:
                self.log("[control] espera a que termine de acostarse")
                return False
            self.lie_pending = False
            code = self.robot.stand_up()
            if code not in (0, None):
                self._sdk_error("stand", f"standUp falló: {describe_code(code)}", now, every_s=0)
                return False
            self.body = BODY_STANDING_UP
            self.body_until = now + self.stand_settle_s
            self.limiter.reset(ZERO)
            self.log(f"[control] parándose ({self.stand_settle_s:.1f} s mandando velocidad cero)")
            return True

    def request_lie(self, now: Optional[float] = None) -> bool:
        """Acostarse: primero velocidad cero sostenida, luego lieDown() (guía 4.1.4)."""
        with self.lock:
            if self.body in (BODY_LYING, BODY_PASSIVE, BODY_LYING_DOWN):
                self.log("[control] ya está acostado")
                return False
            if self.body == BODY_STANDING_UP:
                self.log("[control] espera a que termine de pararse")
                return False
            self.lie_pending = True
            self.log("[control] acostarse: frenando primero")
            return True

    # ------------------------------------------------------------------ lazo
    def _select_input(self, now: float) -> Tuple[Optional[str], Optional[TeleopInput]]:
        fresh = {s: i for s, i in self.inputs.items() if is_fresh(i.t, now, self.teleop_ttl_s)}
        # Eventos de caducidad: solo si lo último que llegó pedía movimiento.
        for s, i in self.inputs.items():
            nonzero = any(abs(v) > 1e-6 for v in (_num(i.fwd), _num(i.strafe), _num(i.turn)))
            if s not in fresh and nonzero and not self._expired_nonzero.get(s):
                self._expired_nonzero[s] = True
                self._emit([("watchdog_zero",
                             f"teleop de '{s}' caducó (>{self.teleop_ttl_s:.1f} s): velocidad a cero")])
            elif s in fresh:
                self._expired_nonzero[s] = False
        local = fresh.get("local")
        if local is not None and any(abs(_num(v)) > 1e-6 for v in (local.fwd, local.strafe, local.turn)):
            return "local", local
        if "sim" in fresh:
            return "sim", fresh["sim"]
        if local is not None:
            return "local", local
        for s, i in fresh.items():
            return s, i
        return None, None

    def tick(self, now: Optional[float] = None) -> TickResult:
        with self.lock:
            now = self.clock() if now is None else now
            dt = 0.05 if self.last_tick is None else max(0.0, min(now - self.last_tick, 0.25))
            self.last_tick = now

            self._emit(self.stops.update(now))
            self._poll_status(now)
            self._advance_body(now)

            source, inp = self._select_input(now)
            self.active_source = source
            # Una fuente sin entrada vigente (soltó las teclas o caducó) ya pasó por neutro.
            for s, strict in list(self._need_neutral.items()):
                i = self.inputs.get(s)
                if not strict and (i is None or not is_fresh(i.t, now, self.teleop_ttl_s)):
                    del self._need_neutral[s]
            hold = self.stops.detection_active(now)
            rearm = source is not None and source in self._need_neutral
            blocked = (self.stops.estopped or hold or self.lie_pending or self.body != BODY_STANDING
                       or rearm)

            if blocked or inp is None:
                target = ZERO
            else:
                target = scale_axes(inp.fwd, inp.strafe, inp.turn, inp.fast, self.limits, inp.scale)
            if self.stops.estopped or self.body != BODY_STANDING or is_zero(target):
                # Parar = cero YA (como el estop): sin rampa de frenado. Con la rampa, desde 0,8 m/s
                # tardaba ~0,5 s en llegar a cero. La rampa queda solo para acelerar y para cambios
                # entre velocidades distintas de cero.
                self.limiter.reset(ZERO)
                ramped = ZERO
            else:
                ramped = self.limiter.step(target, dt)
            cmd = clip_to_sdk(*ramped)
            self.applied = cmd

            sent = False
            if self.body in MOVE_OK_BODIES:
                code = self.robot.move(*cmd)
                sent = True
                self.move_count += 1
                if code not in (0, None):
                    self._sdk_error(f"move:{code}", f"move{_fmt(cmd)} devolvió {describe_code(code)}", now)
            elif self.body == BODY_STANDING_UP:
                # Medido en el D1 EDU (firmware 0.5.1): tras standUp() el robot espera move(0,0,0) continuo;
                # si no llega, se vuelve a acostar. Los rechazos 0x3007 del primer segundo son normales.
                self.robot.move(*ZERO)
                sent = True

            # Acostarse pendiente: cuando la velocidad aplicada lleva lie_zero_s en cero.
            if is_zero(cmd):
                self.zero_since = now if self.zero_since is None else self.zero_since
            else:
                self.zero_since = None
            if (self.lie_pending and self.body == BODY_STANDING and self.zero_since is not None
                    and now - self.zero_since >= self.lie_zero_s):
                self._do_lie(now)

            return TickResult(sent, cmd, self.display_state(now), source)

    def _do_lie(self, now: float) -> None:
        self.lie_pending = False
        code = self.robot.lie_down()
        if code not in (0, None):
            self._sdk_error("lie", f"lieDown falló: {describe_code(code)}", now, every_s=0)
            return
        self.body = BODY_LYING_DOWN
        self.body_until = now + self.lie_settle_s
        self.limiter.reset(ZERO)

    def _advance_body(self, now: float) -> None:
        if self.body_until is not None and now >= self.body_until:
            if self.body == BODY_STANDING_UP:
                self.body = BODY_STANDING
                self._require_neutral()
                self._emit([("stood_up", "el robot está de pie y recibe move()")])
            elif self.body == BODY_LYING_DOWN:
                self.body = BODY_LYING
                self._emit([("lay_down", "el robot se acostó")])
            self.body_until = None

    def _poll_status(self, now: float) -> None:
        if now >= self._next_status:
            self._next_status = now + self.status_period_s
            ok = bool(self.robot.check_connection())
            if self.sdk_ok and not ok:
                self._sdk_error("conn", "checkConnect = false: se perdió la comunicación con el SDK", now)
            self.sdk_ok = ok
            self.pose = self.robot.get_pose()
            mode = self.robot.get_ctrl_mode()
            self.ctrl_mode = mode
            # Pista: si el robot dice "amortiguado" (0) estando nosotros de pie, se acostó solo
            # (batería baja, mando, watchdog). NO VERIFICADO con el robot real.
            if mode == 0 and self.body == BODY_STANDING:
                self.body = BODY_PASSIVE
                self.lie_pending = False
                self.limiter.reset(ZERO)
                self._emit([("lay_down", "el robot pasó a amortiguado por su cuenta (modo 0): "
                                         "¿batería baja, mando o watchdog de 3 s? Pulsa U/stand")])
        if now >= self._next_battery:
            self._next_battery = now + self.battery_period_s
            b = self.robot.get_battery()
            self.battery = b
            if b is not None:
                if self.sdk_ok:      # sin SDK la lectura (0 %) no es fiable: no acostar por eso
                    self._battery_guard(b)
                for thr in (30, 20, 10):
                    if b < thr <= self._battery_warned:
                        self._battery_warned = thr
                        self.log(f"[batería] {b}% (< {thr}%). Bajo 20% el D1 no acepta control por SDK "
                                 "y puede apagarse de golpe (guía 5.2.1, FAQ del repo).")

    def _battery_guard(self, b: float) -> None:
        """Batería crítica estando de pie: acostarse con cero primero (request_lie, no corta de golpe)."""
        lim = self.battery_lie_below
        if not lim or b >= lim + 3:      # histéresis de 3 puntos para volver a avisar
            self._battery_crit_reported = False
            return
        if b < lim and self.body == BODY_STANDING and not self.lie_pending:
            if not self._battery_crit_reported:
                self._battery_crit_reported = True
                self._emit([("battery_critical", f"batería {b}% < {lim:.0f}%: velocidad cero y acostarse")])
            self.lie_pending = True
            self.log(f"[batería] {b}% < {lim:.0f}%: acostándome (cero primero)")

    # ------------------------------------------------------------------ salida
    def display_state(self, now: Optional[float] = None) -> str:
        now = self.clock() if now is None else now
        err_recent = self._last_sdk_error_t is not None and now - self._last_sdk_error_t < 1.0
        if not self.sdk_ok or err_recent:
            return "sdk_error"
        if self.stops.estopped:
            return "estop"
        if self.stops.detection_active(now):
            return "detection_hold"
        if self.body == BODY_PASSIVE:
            return "passive"
        if self.body in (BODY_LYING, BODY_LYING_DOWN):
            return "lying"
        if not is_zero(self.applied):
            return "moving"
        return "standing"

    @property
    def standing(self) -> bool:
        return self.body in MOVE_OK_BODIES

    def last_cmd_age_ms(self, now: Optional[float] = None) -> Optional[int]:
        now = self.clock() if now is None else now
        if self.last_teleop_t is None:
            return None
        return int(round(max(0.0, now - self.last_teleop_t) * 1000))

    def telemetry(self, wall_time: Optional[float] = None, now: Optional[float] = None) -> dict:
        """Mensaje `telemetry` del contrato v1."""
        with self.lock:
            now = self.clock() if now is None else now
            pose = self.pose
            return {
                "type": "telemetry",
                "t": time.time() if wall_time is None else wall_time,
                "x": None if pose is None else round(pose.x, 4),
                "y": None if pose is None else round(pose.y, 4),
                "yaw": None if pose is None else round(pose.yaw, 4),
                "vx": round(self.applied[0], 4),
                "vy": round(self.applied[1], 4),
                "wz": round(self.applied[2], 4),
                "state": self.display_state(now),
                "sdk_ok": bool(self.sdk_ok),
                "battery": self.battery,
                "last_cmd_age_ms": self.last_cmd_age_ms(now),
            }

    def status_line(self, now: Optional[float] = None) -> str:
        now = self.clock() if now is None else now
        vx, vy, wz = self.applied
        age = self.last_cmd_age_ms(now)
        pose = self.pose
        pose_txt = "—" if pose is None else f"({pose.x:+.2f},{pose.y:+.2f},{pose.yaw*57.2958:+.0f}°)"
        bat = "—" if self.battery is None else f"{self.battery}%"
        mode = "" if self.ctrl_mode is None else f" modo={self.ctrl_mode}"
        src = self.active_source or "-"
        extra = ""
        if self.stops.estopped:
            extra = " [ESTOP: R reanuda]"
        elif self.stops.detection_active(now):
            extra = f" [DETECCIÓN {max(0.0, (self.stops.hold_until or now) - now):.1f}s]"
        elif self.body != BODY_STANDING:
            extra = {BODY_LYING: " [acostado: U para pararse]", BODY_PASSIVE: " [amortiguado: U]",
                     BODY_STANDING_UP: " [parándose...]", BODY_LYING_DOWN: " [acostándose...]"}.get(self.body, "")
        elif self.lie_pending:
            extra = " [frenando para acostarse]"
        return (f"{self.display_state(now):<14} vx={vx:+.2f} vy={vy:+.2f} wz={wz:+.2f} "
                f"src={src} edad={'—' if age is None else str(age) + 'ms'} sdk={'ok' if self.sdk_ok else 'NO'}"
                f" bat={bat}{mode} pose={pose_txt}{extra}")

    def describe_mode(self) -> str:
        return CTRL_MODES.get(self.ctrl_mode, "?") if self.ctrl_mode is not None else "?"

    # ------------------------------------------------------------------ apagado seguro
    def shutdown(self, lie: bool = True, sleep: Callable[[float], None] = time.sleep,
                 period_s: float = 0.05) -> None:
        """Salida segura: cero inmediato y sostenido; luego acostarse si estaba de pie."""
        with self.lock:
            self.inputs.clear()
            self.limiter.reset(ZERO)
            self.applied = ZERO
            was_standing = self.body in (BODY_STANDING, BODY_STANDING_UP)
        if not was_standing:
            return
        for _ in range(int(0.5 / period_s)):
            self.robot.move(0.0, 0.0, 0.0)
            sleep(period_s)
        if lie:
            code = self.robot.lie_down()
            self.log(f"[salida] lieDown -> {describe_code(code)}; espero {self.lie_settle_s:.1f} s")
            with self.lock:
                self.body = BODY_LYING_DOWN
            sleep(self.lie_settle_s)
            with self.lock:
                self.body = BODY_LYING
        else:
            self.log("[salida] el robot queda de pie: sin comandos se acostará solo a los 3 s (FAQ 6.9)")


def _num(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if f == f else 0.0


def _nonzero(*axes) -> bool:
    """Igual criterio que scale_axes: lo que clamp_unit deja distinto de cero."""
    return any(clamp_unit(a) != 0.0 for a in axes)


def _fmt(v: Velocity) -> str:
    return "(" + ", ".join(f"{c:+.2f}" for c in v) + ")"
