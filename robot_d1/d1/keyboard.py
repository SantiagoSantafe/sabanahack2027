"""Teclado para teleoperar: modo terminal (sin dependencias) y modo pynput (sabe cuándo se suelta).

Problema: una terminal no avisa cuando se SUELTA una tecla; solo manda caracteres, y al mantener
una tecla manda la primera, espera la demora de autorrepetición (~0,25–0,66 s según el sistema)
y luego repite cada ~30–40 ms.

Solución del modo terminal (retención por tiempo en dos etapas):
- Primera pulsación: la tecla se considera pulsada `initial_hold_s` (0,6 s) para cubrir la demora.
- Si llegan repeticiones: se considera pulsada `repeat_hold_s` (0,15 s) desde la última repetición.
=> Al soltar una tecla que ya repetía, el robot frena en <= 0,15 s. Un toque corto mueve ~0,6 s.
Limitación: la terminal solo repite la ÚLTIMA tecla pulsada, así que no se combinan W+A.
Para combinar teclas usa el modo pynput (necesita sesión gráfica X11).
"""

from __future__ import annotations

import os
import select
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

MOVE_KEYS = {
    # tecla: (fwd, strafe, turn)
    "w": (1.0, 0.0, 0.0),
    "s": (-1.0, 0.0, 0.0),
    "a": (0.0, 0.0, 1.0),    # girar a la izquierda (turn > 0 = izquierda)
    "d": (0.0, 0.0, -1.0),
    "q": (0.0, 1.0, 0.0),    # lateral izquierda (strafe > 0 = izquierda)
    "e": (0.0, -1.0, 0.0),
}

# Flechas del teclado (secuencias ESC [ A..D) se mapean a W/S/A/D.
ARROWS = {"A": "w", "B": "s", "C": "d", "D": "a"}

ACTION_KEYS = {
    " ": "estop",
    "r": "resume",
    "u": "stand",
    "l": "lie",
    "h": "help",
    "?": "help",
    "+": "faster",
    "=": "faster",
    "-": "slower",
    "_": "slower",
    "\x1b": "quit",   # Esc solo
    "\x03": "quit",   # Ctrl-C si la terminal está en modo crudo
}

HELP_TEXT = """\
Teclas:  W/S adelante/atrás   A/D girar   Q/E lateral   (flechas = W/S/A/D)
         Shift+W = rápido (solo adelante/atrás)   +/- nivel de velocidad
         ESPACIO = PARADA DE EMERGENCIA (cero continuo, bloqueado hasta R)
         R = reanudar   U = pararse   L = acostarse   H = esta ayuda
         Ctrl-C o Esc = salida segura (cero y luego acostarse)"""


@dataclass
class KeyEvent:
    kind: str           # "move" | "action"
    key: str            # tecla normalizada (minúscula) o nombre de acción
    shift: bool = False


def parse_bytes(data: str) -> Tuple[List[KeyEvent], str]:
    """Convierte caracteres de la terminal en eventos. Devuelve (eventos, resto_incompleto).

    Un ESC al final sin más bytes se devuelve como resto: puede ser el inicio de una flecha.
    Quien llama decide si, pasado un instante sin más datos, lo trata como Esc solo.
    """
    events: List[KeyEvent] = []
    i = 0
    n = len(data)
    while i < n:
        ch = data[i]
        if ch == "\x1b":
            if i + 1 >= n:
                return events, data[i:]
            nxt = data[i + 1]
            if nxt in "[O":
                if i + 2 >= n:
                    return events, data[i:]
                code = data[i + 2]
                if code in ARROWS:
                    events.append(KeyEvent("move", ARROWS[code]))
                    i += 3
                    continue
                # Otra secuencia (F1, Supr...): saltarla hasta su letra final.
                j = i + 2
                while j < n and not data[j].isalpha() and data[j] != "~":
                    j += 1
                i = j + 1
                continue
            events.append(KeyEvent("action", "quit"))
            i += 1
            continue
        low = ch.lower()
        if low in MOVE_KEYS:
            events.append(KeyEvent("move", low, shift=ch.isupper()))
        elif ch in ACTION_KEYS:
            events.append(KeyEvent("action", ACTION_KEYS[ch]))
        elif low in ACTION_KEYS:
            events.append(KeyEvent("action", ACTION_KEYS[low]))
        i += 1
    return events, ""


class HoldTracker:
    """Retención por tiempo en dos etapas (modo terminal). Función pura del tiempo que se le pasa."""

    def __init__(self, initial_hold_s: float = 0.6, repeat_hold_s: float = 0.15):
        self.initial_hold_s = initial_hold_s
        self.repeat_hold_s = repeat_hold_s
        self._until: Dict[str, float] = {}
        self._shift: Dict[str, bool] = {}

    def press(self, key: str, now: float, shift: bool = False) -> None:
        # Si ya estaba retenida, esto es una repetición: ventana corta. Si no, ventana inicial.
        held = self.is_held(key, now)
        self._until[key] = now + (self.repeat_hold_s if held else self.initial_hold_s)
        self._shift[key] = shift

    def release_all(self) -> None:
        self._until.clear()
        self._shift.clear()

    def is_held(self, key: str, now: float) -> bool:
        return now < self._until.get(key, -1.0)

    def held(self, now: float) -> List[str]:
        return [k for k in self._until if self.is_held(k, now)]

    def shift_held(self, now: float) -> bool:
        return any(self._shift.get(k) for k in self.held(now))


def axes_from_keys(keys, fast: bool = False) -> Tuple[float, float, float, bool]:
    fwd = strafe = turn = 0.0
    for k in keys:
        f, s, t = MOVE_KEYS.get(k, (0.0, 0.0, 0.0))
        fwd += f
        strafe += s
        turn += t
    clamp = lambda v: max(-1.0, min(1.0, v))  # noqa: E731
    return clamp(fwd), clamp(strafe), clamp(turn), fast


class TerminalKeys:
    """Lee la terminal en modo cbreak (Ctrl-C sigue generando SIGINT). Sin dependencias."""

    def __init__(self, hold: HoldTracker, stream=None):
        self.hold = hold
        self.stream = stream or sys.stdin
        self.fd = self.stream.fileno()
        self._old = None
        self._pending = ""
        self._pending_since: Optional[float] = None
        self.enabled = os.isatty(self.fd)

    def __enter__(self) -> "TerminalKeys":
        if self.enabled:
            import termios
            import tty
            self._old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *exc) -> None:
        self.restore()

    def restore(self) -> None:
        if self._old is not None:
            import termios
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self._old)
            except Exception:
                pass
            self._old = None

    def wait_readable(self, timeout: float) -> bool:
        if not self.enabled:
            return False
        try:
            r, _, _ = select.select([self.fd], [], [], max(0.0, timeout))
        except (OSError, ValueError):
            return False
        return bool(r)

    def read_available(self, now: float) -> List[KeyEvent]:
        """Lee lo que haya (no bloquea) y devuelve eventos. Aplica las pulsaciones al HoldTracker."""
        data = ""
        if self.enabled:
            while True:
                try:
                    r, _, _ = select.select([self.fd], [], [], 0)
                except (OSError, ValueError):
                    break
                if not r:
                    break
                chunk = os.read(self.fd, 1024)
                if not chunk:
                    break
                data += chunk.decode("utf-8", errors="ignore")
        return self.feed(data, now)

    def feed(self, data: str, now: float) -> List[KeyEvent]:
        buf = self._pending + data
        events, rest = parse_bytes(buf)
        if rest:
            if self._pending_since is None:
                self._pending_since = now
            elif now - self._pending_since > 0.05:
                # ESC solo (nadie completó la secuencia en 50 ms) = salir
                events.append(KeyEvent("action", "quit"))
                rest = ""
        if not rest:
            self._pending_since = None
        self._pending = rest
        for ev in events:
            if ev.kind == "move":
                self.hold.press(ev.key, now, ev.shift)
            elif ev.key == "estop":
                self.hold.release_all()
        return events

    def release_all(self) -> None:
        self.hold.release_all()

    def axes(self, now: float) -> Tuple[float, float, float, bool]:
        return axes_from_keys(self.hold.held(now), fast=self.hold.shift_held(now))


class PynputKeys:
    """Teclado con pynput: sabe cuándo se suelta cada tecla (permite W+A).

    Requisitos: `pip install pynput` y una sesión gráfica X11 (DISPLAY definido). En Ubuntu 22.04
    con Wayland elige "Ubuntu on Xorg" al iniciar sesión. OJO: pynput escucha el teclado de TODO
    el escritorio, no solo esta terminal: no escribas en otra ventana mientras manejas.
    """

    def __init__(self, release_grace_s: float = 0.08, clock: Callable[[], float] = None,
                 on_action: Callable[[str], None] = None):
        import time as _time
        from pynput import keyboard as kb  # noqa: F401 - falla aquí si no está instalado

        self._kb = kb
        self.clock = clock or _time.monotonic
        self.release_grace_s = release_grace_s
        self.on_action = on_action or (lambda name: None)
        self._down: Dict[str, bool] = {}
        self._released_at: Dict[str, float] = {}
        self._shift = False
        self._listener = None

    def _name(self, key) -> Optional[str]:
        kb = self._kb
        if key == kb.Key.space:
            return " "
        if key == kb.Key.esc:
            return "\x1b"
        if key in (kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r):
            return "shift"
        arrows = {kb.Key.up: "w", kb.Key.down: "s", kb.Key.left: "a", kb.Key.right: "d"}
        if key in arrows:
            return arrows[key]
        ch = getattr(key, "char", None)
        return ch.lower() if ch else None

    def _on_press(self, key) -> None:
        name = self._name(key)
        if name is None:
            return
        if name == "shift":
            self._shift = True
            return
        if name in MOVE_KEYS:
            self._down[name] = True
            self._released_at.pop(name, None)
            return
        if not self._down.get(name):          # acciones: solo en la transición (sin autorrepetición)
            self._down[name] = True
            action = ACTION_KEYS.get(name)
            if action:
                self.on_action(action)

    def _on_release(self, key) -> None:
        name = self._name(key)
        if name is None:
            return
        if name == "shift":
            self._shift = False
            return
        self._down[name] = False
        if name in MOVE_KEYS:
            self._released_at[name] = self.clock()

    def start(self) -> "PynputKeys":
        self._listener = self._kb.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()
        return self

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def held(self, now: float) -> List[str]:
        out = []
        for k in MOVE_KEYS:
            if self._down.get(k):
                out.append(k)
            elif k in self._released_at and now - self._released_at[k] < self.release_grace_s:
                out.append(k)
        return out

    def release_all(self) -> None:
        self._down = {k: False for k in self._down}
        self._released_at.clear()

    def axes(self, now: float) -> Tuple[float, float, float, bool]:
        return axes_from_keys(self.held(now), fast=self._shift)


def pynput_available() -> Tuple[bool, str]:
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return False, "no hay DISPLAY (sin sesión gráfica X11; ¿estás por SSH o en Wayland puro?)"
    try:
        import pynput  # noqa: F401
    except Exception as exc:  # ImportError o error del backend X
        return False, f"pynput no disponible: {exc}"
    return True, ""


class KeyboardDriver:
    """Conecta un teclado (terminal o pynput) con el núcleo de control (ControlCore).

    - Teclas de movimiento -> core.set_teleop("local", ...) con el nivel de velocidad.
    - Espacio -> core.estop("local") (siempre gana; solo R local lo levanta).
    - U/L/R/H/+/- -> acciones. Esc/Ctrl-C -> `quit_requested = True`.
    Es seguro llamar handle_action desde el hilo de pynput (ControlCore usa un RLock).
    """

    def __init__(self, core, levels: List[float], level_idx: int = 1,
                 log: Callable[[str], None] = print, source: str = "local"):
        self.core = core
        self.levels = levels or [0.6]
        self.level_idx = max(0, min(int(level_idx), len(self.levels) - 1))
        self.log = log
        self.source = source
        self.quit_requested = False
        self.backend = None   # TerminalKeys o PynputKeys

    @property
    def level(self) -> float:
        return self.levels[self.level_idx]

    def handle_events(self, events: List[KeyEvent]) -> None:
        for ev in events:
            if ev.kind == "action":
                self.handle_action(ev.key)

    def handle_action(self, name: str) -> None:
        if name == "estop":
            if self.backend is not None:
                self.backend.release_all()
            self.core.estop(self.source, "tecla Espacio")
        elif name == "resume":
            self.core.resume(self.source)
        elif name == "stand":
            self.core.request_stand()
        elif name == "lie":
            self.core.request_lie()
        elif name == "help":
            self.log(HELP_TEXT)
        elif name == "faster":
            self.level_idx = min(self.level_idx + 1, len(self.levels) - 1)
            self.log(f"[teclado] nivel de velocidad {self.level_idx + 1}/{len(self.levels)} "
                     f"({self.level:.0%} de los límites)")
        elif name == "slower":
            self.level_idx = max(self.level_idx - 1, 0)
            self.log(f"[teclado] nivel de velocidad {self.level_idx + 1}/{len(self.levels)} "
                     f"({self.level:.0%} de los límites)")
        elif name == "quit":
            self.quit_requested = True

    def push(self, now: float) -> None:
        """Llamar en cada tick: pasa los ejes del teclado al núcleo."""
        if self.backend is None:
            return
        # Un Esc suelto queda pendiente 50 ms (podría ser una flecha); resolverlo aquí.
        if getattr(self.backend, "_pending", ""):
            self.handle_events(self.backend.feed("", now))
        fwd, strafe, turn, fast = self.backend.axes(now)
        if fwd or strafe or turn:
            self.core.set_teleop(self.source, fwd, strafe, turn, fast, scale=self.level, now=now)
        else:
            self.core.clear_teleop(self.source)
