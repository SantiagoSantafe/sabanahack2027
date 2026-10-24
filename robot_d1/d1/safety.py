"""Funciones puras de seguridad para mandar el D1 EDU.

Todo aquí es determinista y sin E/S: recibe números y tiempos, devuelve números.
Así se puede probar con pytest sin robot ni red.

Rangos válidos de move() según la guía del SDK (sección 4.1.6) y docs/api_zsl-1.md:
    vx:       0.05 .. 3.0  m/s   (en valor absoluto)
    vy:       0.10 .. 1.0  m/s
    yaw_rate: 0.02 .. 3.0  rad/s
Por debajo del mínimo el SDK no garantiza nada, así que lo mandamos como 0 (zona muerta).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

# --------------------------------------------------------------------------
# Rangos del SDK (guía 4.1.6). No cambiar sin revisar la guía.
# --------------------------------------------------------------------------
SDK_VX_RANGE = (0.05, 3.0)
SDK_VY_RANGE = (0.10, 1.0)
SDK_WZ_RANGE = (0.02, 3.0)

# Tolerancia para comparaciones en el borde de la zona muerta (0.25*0.4 = 0.1 en coma flotante).
_EPS = 1e-9

Velocity = Tuple[float, float, float]
ZERO: Velocity = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class Limits:
    """Límites de demo (interiores) del contrato v1. Siempre por debajo de los del SDK."""

    vx_max: float = 0.4      # m/s sin "fast"
    vx_fast: float = 0.8     # m/s con "fast"
    vy_max: float = 0.25     # m/s
    wz_max: float = 0.6      # rad/s

    def capped_to_sdk(self) -> "Limits":
        """Devuelve los mismos límites, recortados a los máximos del SDK (por si alguien exagera)."""
        return Limits(
            vx_max=min(abs(self.vx_max), SDK_VX_RANGE[1]),
            vx_fast=min(abs(self.vx_fast), SDK_VX_RANGE[1]),
            vy_max=min(abs(self.vy_max), SDK_VY_RANGE[1]),
            wz_max=min(abs(self.wz_max), SDK_WZ_RANGE[1]),
        )


@dataclass(frozen=True)
class Accel:
    """Límites de aceleración (rampa). Frenar se permite más rápido que acelerar."""

    ax: float = 0.8     # m/s² al acelerar en x
    ay: float = 0.6     # m/s² en y
    aw: float = 1.5     # rad/s² en giro
    decel_factor: float = 2.0  # frenar = factor × acelerar


# --------------------------------------------------------------------------
# Entradas: ejes normalizados -> velocidades
# --------------------------------------------------------------------------
def clamp_unit(value) -> float:
    """Convierte a float en [-1, 1]. Cualquier cosa rara (None, texto, bool, NaN, inf) -> 0."""
    if isinstance(value, bool) or value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return max(-1.0, min(1.0, v))


def scale_axes(fwd, strafe, turn, fast: bool, limits: Limits, scale: float = 1.0) -> Velocity:
    """Ejes (-1..1) -> velocidades objetivo (m/s, m/s, rad/s) con los límites de demo.

    - fwd > 0 = adelante, strafe > 0 = izquierda, turn > 0 = girar a la izquierda
      (marco del robot: X adelante, Y izquierda, Z arriba; guía 3.10.2).
    - fast solo afecta a vx (contrato v1).
    - scale (0..1) es el nivel de velocidad del teclado; la simulación usa 1.0.
    """
    lim = limits.capped_to_sdk()
    s = max(0.0, min(1.0, float(scale)))
    vx_cap = lim.vx_fast if fast is True else lim.vx_max
    return (
        clamp_unit(fwd) * vx_cap * s,
        clamp_unit(strafe) * lim.vy_max * s,
        clamp_unit(turn) * lim.wz_max * s,
    )


# --------------------------------------------------------------------------
# Recorte a los rangos del SDK con zona muerta
# --------------------------------------------------------------------------
def sdk_clip(value: float, vmin: float, vmax: float) -> float:
    """Debajo del mínimo -> 0; encima del máximo -> máximo; conserva el signo."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    a = abs(v)
    if a < vmin - _EPS:
        return 0.0
    return math.copysign(min(a, vmax), v)


def clip_to_sdk(vx: float, vy: float, wz: float) -> Velocity:
    """Aplica sdk_clip a las tres componentes con los rangos de la guía 4.1.6."""
    return (
        sdk_clip(vx, *SDK_VX_RANGE),
        sdk_clip(vy, *SDK_VY_RANGE),
        sdk_clip(wz, *SDK_WZ_RANGE),
    )


def is_zero(v: Velocity) -> bool:
    return all(abs(c) < _EPS for c in v)


# --------------------------------------------------------------------------
# Limitador de aceleración (rampa)
# --------------------------------------------------------------------------
def rate_limit(current: float, target: float, dt: float, accel: float, decel: float) -> float:
    """Mueve `current` hacia `target` sin superar la aceleración permitida en `dt` segundos.

    Si el objetivo acerca a cero (frenar) usa `decel`; si aleja de cero usa `accel`.
    Al cambiar de signo, primero frena hasta 0 (con `decel`) y se detiene ahí en este paso.
    """
    if dt <= 0:
        return current
    if current * target < 0:  # cambio de sentido: primero frenar a cero
        step = decel * dt
        if abs(current) <= step:
            return 0.0
        return current - math.copysign(step, current)
    braking = abs(target) < abs(current)
    step = (decel if braking else accel) * dt
    delta = target - current
    if abs(delta) <= step:
        return target
    return current + math.copysign(step, delta)


class RateLimiter3:
    """Rampa para (vx, vy, wz). Guarda el estado interno entre ticks."""

    def __init__(self, accel: Accel):
        self.accel = accel
        self.value: Velocity = ZERO

    def reset(self, value: Velocity = ZERO) -> None:
        self.value = tuple(float(c) for c in value)  # type: ignore[assignment]

    def step(self, target: Velocity, dt: float) -> Velocity:
        a = self.accel
        f = max(1.0, a.decel_factor)
        vx = rate_limit(self.value[0], target[0], dt, a.ax, a.ax * f)
        vy = rate_limit(self.value[1], target[1], dt, a.ay, a.ay * f)
        wz = rate_limit(self.value[2], target[2], dt, a.aw, a.aw * f)
        self.value = (vx, vy, wz)
        return self.value


# --------------------------------------------------------------------------
# Vigencia de comandos
# --------------------------------------------------------------------------
TELEOP_TTL_S = 0.3  # contrato v1: un teleop vale 0,3 s


def is_fresh(cmd_time: Optional[float], now: float, ttl: float = TELEOP_TTL_S) -> bool:
    """True si el comando llegó hace menos de `ttl` segundos (y no viene del futuro raro)."""
    if cmd_time is None:
        return False
    age = now - cmd_time
    return -0.05 <= age < ttl


# --------------------------------------------------------------------------
# Estados de parada: estop y detección
# --------------------------------------------------------------------------
DETECTION_HOLD_DEFAULT_S = 4.0
DETECTION_HOLD_MAX_S = 30.0


def sanitize_hold(hold_s, default: float = DETECTION_HOLD_DEFAULT_S,
                  max_s: float = DETECTION_HOLD_MAX_S) -> float:
    """hold_s inválido o <= 0 -> default; demasiado grande -> max_s."""
    if isinstance(hold_s, bool) or hold_s is None:
        return default
    try:
        h = float(hold_s)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(h) or h <= 0:
        return default
    return min(h, max_s)


class StopState:
    """Estop (bloqueante hasta resume) y retención por detección (temporal).

    - El estop puede venir de varias fuentes ("local" = teclado de la VM, "sim" = simulación).
      Regla: el estop local siempre gana; un resume de la simulación NO lo levanta.
    - La retención por detección dura hold_s; otra detección la prolonga.
    Cada método devuelve una lista de eventos (nombre, detalle) del contrato v1.
    """

    def __init__(self) -> None:
        self.estop_sources: Set[str] = set()
        self.hold_until: Optional[float] = None
        self._hold_reported = False
        self.last_detection: Dict[str, object] = {}

    # --- estop ---
    @property
    def estopped(self) -> bool:
        return bool(self.estop_sources)

    def estop(self, source: str, reason: str = "") -> list:
        was = self.estopped
        self.estop_sources.add(source)
        if was:
            return []
        detail = f"parada de emergencia ({source})" + (f": {reason}" if reason else "")
        return [("estop", detail)]

    def resume(self, source: str) -> Tuple[bool, list]:
        """Devuelve (aceptado, eventos)."""
        if not self.estopped:
            return True, []
        if source != "local" and "local" in self.estop_sources:
            return False, []
        self.estop_sources.clear()
        return True, [("resume", f"movimiento reanudado ({source})")]

    # --- detección ---
    def detection_stop(self, now: float, hold_s, label=None, conf=None) -> list:
        h = sanitize_hold(hold_s)
        new_until = now + h
        active = self.detection_active(now)
        self.hold_until = new_until if not active else max(self.hold_until or 0.0, new_until)
        self.last_detection = {"label": label, "conf": conf, "hold_s": h}
        if active:
            return []
        self._hold_reported = True
        conf_txt = ""
        try:
            conf_txt = f" ({float(conf):.2f})" if conf is not None else ""
        except (TypeError, ValueError):
            conf_txt = ""
        return [("detection_hold_start", f"detección {label or '?'}{conf_txt}: quieto {h:.1f} s")]

    def detection_active(self, now: float) -> bool:
        return self.hold_until is not None and now < self.hold_until

    def update(self, now: float) -> list:
        """Llamar en cada tick: emite detection_hold_end cuando vence la retención."""
        if self.hold_until is not None and now >= self.hold_until:
            self.hold_until = None
            if self._hold_reported:
                self._hold_reported = False
                return [("detection_hold_end", "fin de la retención por detección")]
        return []
