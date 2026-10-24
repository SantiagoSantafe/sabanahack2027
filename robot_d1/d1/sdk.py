"""Adaptador del SDK del D1 EDU con la misma interfaz para el robot real y uno simulado.

Fuentes (tratadas como datos):
- Guía "AGIQUAD D1 Edu & Ultra SDK Development Guide" V0.2.7, secciones 3.7–3.9, 4.1, 5.4, 6.
- Repo AgibotTech/agibot_D1_Edu-Ultra: include/zsl-1/highlevel.h, docs/api_zsl-1.md,
  demo/zsl-1/python/examples/highlevel_demo_Interactive.py.
- Cadenas del binario lib/zsl-1/x86_64/mc_sdk_zsl_1_py.cpython-310-x86_64-linux-gnu.so.

El D1 EDU usa el modelo "zsl-1" (módulo Python `mc_sdk_zsl_1_py`, clase `HighLevel`).
"zsl-1w" es el Ultra-W con ruedas: no es el nuestro.

Discrepancias encontradas entre la guía y el binario (por eso se prueba con getattr):
- La guía dice `checkConnection()`; el .so y highlevel.h exponen `checkConnect()`.
- La guía dice `getCurrentCtrlMode()`; el .so expone `getCurrentCtrlmode()` (m minúscula).
- El .so trae una máquina de estados del lado del cliente: "Cannot transition to 'move' state:
  must transition to 'standUp' first." => hay que llamar standUp() en esta sesión antes de move().

Uso rápido para diagnosticar la instalación del SDK en la VM:
    python3.10 -m d1.sdk --sdk-path ~/agibot_D1_Edu-Ultra
"""

from __future__ import annotations

import importlib
import math
import os
import platform
import socket
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

SDK_MODULE = "mc_sdk_zsl_1_py"
SDK_MODEL_DIR = "zsl-1"
DEFAULT_ROBOT_IP = "192.168.234.1"   # AP Wi-Fi del D1 (guía 3.3)
WIRED_ROBOT_IP = "192.168.168.168"   # puerto Ethernet del D1 (guía 3.3)
DEFAULT_LOCAL_PORT = 43988           # target_port de sdk_config.yaml (guía 3.7: "no modificar")

# Códigos de retorno de standUp/lieDown/passive/move (guía 4.1.3–4.1.6).
RETURN_CODES = {
    0: "ok",
    0x3007: "falló el cambio de estado de la máquina de estados",
    0x3009: "ángulo de motor fuera de límite",
    0x3010: "motor deshabilitado",
    0x3011: "falla de motor",
    0x3012: "se perdieron los datos de los motores",
    0x3013: "comando de velocidad demasiado grande",
}

# getCurrentCtrlmode (guía 4.1.22).
CTRL_MODES = {
    0: "amortiguado (damping)",
    1: "de pie / saludo",
    10: "acostado, motores libres",
    18: "moviéndose",
    21: "acción (actitud, salto, dos patas)",
    51: "acostado",
}


def describe_code(code) -> str:
    if code is None:
        return "sin código"
    try:
        c = int(code)
    except (TypeError, ValueError):
        return f"código raro {code!r}"
    return f"0x{c:04X} {RETURN_CODES.get(c, 'código desconocido')}"


@dataclass
class Pose:
    x: float
    y: float
    yaw: float


# --------------------------------------------------------------------------
# Red
# --------------------------------------------------------------------------
def detect_local_ip(robot_ip: str, port: int = DEFAULT_LOCAL_PORT) -> Optional[str]:
    """IP de la interfaz local con ruta hacia el robot (truco UDP: connect() no envía nada)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((robot_ip, port))
        ip = s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()
    if not ip or ip.startswith("127.") or ip == "0.0.0.0":
        return None
    return ip


def same_subnet_24(a: str, b: str) -> bool:
    try:
        return a.split(".")[:3] == b.split(".")[:3]
    except AttributeError:
        return False


def network_warnings(local_ip: str, robot_ip: str) -> list:
    """Avisos humanos sobre la IP local (NAT de VM, subred distinta)."""
    msgs = []
    nat_prefixes = {
        "10.0.2.": "VirtualBox en NAT",
        "192.168.122.": "libvirt/KVM en NAT",
        "172.17.": "Docker",
        "192.168.56.": "VirtualBox 'Host-only'",
    }
    for pref, what in nat_prefixes.items():
        if local_ip.startswith(pref):
            msgs.append(f"La IP local {local_ip} parece {what}. El SDK necesita la VM en modo PUENTE "
                        f"(bridged): el robot devuelve UDP a local_ip:puerto y con NAT no llega.")
    if local_ip.startswith("172.") and not any(m for m in msgs):
        msgs.append(f"La IP local {local_ip} puede ser el 'Default Switch' (NAT) de Hyper-V. "
                    "Usa un conmutador externo (puente) o VirtualBox/VMware en modo puente.")
    if not same_subnet_24(local_ip, robot_ip):
        msgs.append(f"La IP local {local_ip} no está en la misma subred /24 que el robot {robot_ip}.")
    return msgs


# --------------------------------------------------------------------------
# Carga del módulo del SDK
# --------------------------------------------------------------------------
def machine_arch() -> str:
    """Igual que el ejemplo oficial: amd64 -> x86_64, arm64 -> aarch64."""
    return platform.machine().lower().replace("amd64", "x86_64").replace("arm64", "aarch64")


def candidate_sdk_paths(explicit: Optional[str]) -> list:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("D1_SDK_PATH"):
        cands.append(os.environ["D1_SDK_PATH"])
    cands += [
        os.path.join(here, "third_party", "agibot_D1_Edu-Ultra"),
        os.path.expanduser("~/agibot_D1_Edu-Ultra"),
        os.path.expanduser("~/agibot_D1_Edu-Ultra-main"),
        "/opt/agibot_D1_Edu-Ultra",
    ]
    return [os.path.expanduser(c) for c in cands]


def find_sdk_lib_dir(sdk_path: Optional[str]) -> str:
    arch = machine_arch()
    tried = []
    for base in candidate_sdk_paths(sdk_path):
        # Se acepta la raíz del repo o directamente la carpeta lib/zsl-1/<arch>.
        for d in (os.path.join(base, "lib", SDK_MODEL_DIR, arch), base):
            tried.append(d)
            if os.path.isdir(d) and any(f.startswith(SDK_MODULE) and f.endswith(".so")
                                        for f in os.listdir(d)):
                return d
    raise FileNotFoundError(
        f"No encontré {SDK_MODULE}*.so para la arquitectura {arch}. Probé:\n  "
        + "\n  ".join(tried)
        + "\nClona el SDK (git clone https://github.com/AgibotTech/agibot_D1_Edu-Ultra.git) "
          "y pasa --sdk-path o define D1_SDK_PATH."
    )


def load_sdk_module(sdk_path: Optional[str] = None):
    if sys.platform != "linux":
        raise RuntimeError(f"El SDK del D1 solo corre en Linux (estás en {sys.platform}). "
                           "En el Mac usa --mock.")
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError(
            f"El módulo del SDK está compilado para CPython 3.10 (cp310) y esto es Python "
            f"{sys.version_info[0]}.{sys.version_info[1]}. Usa python3.10 / el venv de "
            "scripts/setup_vm_ubuntu.sh (guía 6.4).")
    lib_dir = find_sdk_lib_dir(sdk_path)
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    return importlib.import_module(SDK_MODULE), lib_dir


def _vec(value, n: int) -> Optional[list]:
    """Convierte la respuesta del SDK (std::vector<float> -> lista) a n floats finitos, o None."""
    if value is None:
        return None
    try:
        seq = list(value)
    except TypeError:
        return None
    if len(seq) < n:
        return None
    out = []
    for v in seq[:n]:
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(f):
            return None
        out.append(f)
    return out


# --------------------------------------------------------------------------
# Interfaz común
# --------------------------------------------------------------------------
class RobotBase:
    """Interfaz que usan el núcleo de control, la teleop y el puente."""

    is_mock = False
    name = "D1 EDU"

    def connect(self) -> None: ...
    def check_connection(self) -> bool: return False
    def stand_up(self) -> Optional[int]: return None
    def lie_down(self) -> Optional[int]: return None
    def passive(self) -> Optional[int]: return None
    def move(self, vx: float, vy: float, wz: float) -> Optional[int]: return None
    def get_pose(self) -> Optional[Pose]: return None
    def get_battery(self) -> Optional[int]: return None
    def get_ctrl_mode(self) -> Optional[int]: return None
    def close(self) -> None: ...


class RealRobot(RobotBase):
    """D1 EDU real a través de mc_sdk_zsl_1_py.HighLevel (solo Linux + Python 3.10)."""

    def __init__(self, robot_ip: str = DEFAULT_ROBOT_IP, local_ip: Optional[str] = None,
                 local_port: int = DEFAULT_LOCAL_PORT, sdk_path: Optional[str] = None):
        self.robot_ip = robot_ip
        self.local_ip = local_ip
        self.local_port = int(local_port)
        self.sdk_path = sdk_path
        self.module = None
        self.lib_dir = None
        self._app = None
        self._check_fn: Optional[Callable] = None
        self._mode_fn: Optional[Callable] = None

    def connect(self) -> None:
        self.module, self.lib_dir = load_sdk_module(self.sdk_path)
        if not self.local_ip:
            self.local_ip = detect_local_ip(self.robot_ip, self.local_port)
            if not self.local_ip:
                raise RuntimeError(f"No hay ruta hacia el robot {self.robot_ip}. ¿Wi-Fi del D1 "
                                   "conectado y VM en modo puente? Pasa --local-ip si hace falta.")
        self._app = self.module.HighLevel()
        # initRobot(local_ip, local_port, dog_ip) -> None (guía 4.1.1). Si falla, el SDK
        # imprime en la terminal (p. ej. "connect time out", guía 6.1).
        self._app.initRobot(self.local_ip, self.local_port, self.robot_ip)
        app = self._app
        self._check_fn = getattr(app, "checkConnect", None) or getattr(app, "checkConnection", None)
        self._mode_fn = (getattr(app, "getCurrentCtrlmode", None)
                         or getattr(app, "getCurrentCtrlMode", None))

    # --- comandos (devuelven el uint32 del SDK; -1 si lanzó excepción) ---
    def _call(self, name: str, *args) -> Optional[int]:
        if self._app is None:
            return -1
        try:
            r = getattr(self._app, name)(*args)
        except Exception as exc:  # pybind11 convierte excepciones C++ en RuntimeError
            print(f"[sdk] {name}{args} lanzó {type(exc).__name__}: {exc}", flush=True)
            return -1
        try:
            return int(r) if r is not None else 0
        except (TypeError, ValueError):
            return 0

    def stand_up(self) -> Optional[int]:
        return self._call("standUp")

    def lie_down(self) -> Optional[int]:
        return self._call("lieDown")

    def passive(self) -> Optional[int]:
        # Amortiguado: el robot se deja caer (suave). NO es una parada; no se usa en el lazo.
        return self._call("passive")

    def move(self, vx: float, vy: float, wz: float) -> Optional[int]:
        return self._call("move", float(vx), float(vy), float(wz))

    # --- lecturas (todas defensivas) ---
    def check_connection(self) -> bool:
        if self._check_fn is None:
            return False
        try:
            return bool(self._check_fn())
        except Exception:
            return False

    def get_pose(self) -> Optional[Pose]:
        # NO VERIFICADO con el robot real: getPosition() da [x, y, z] en el marco de origen al
        # encender (guía 4.1.18) y getRPY() da [roll, pitch, yaw] en rad (guía 4.1.15). No sabemos
        # cuánto deriva ni si en modo HighLevel la posición se actualiza al caminar.
        if self._app is None:
            return None
        try:
            pos = _vec(self._app.getPosition(), 3)
            rpy = _vec(self._app.getRPY(), 3)
        except Exception:
            return None
        if pos is None or rpy is None:
            return None
        return Pose(pos[0], pos[1], rpy[2])

    def get_battery(self) -> Optional[int]:
        # getBatteryPower() -> uint32 0..100 (guía 4.1.21). NO VERIFICADO con el robot real.
        if self._app is None:
            return None
        try:
            b = int(self._app.getBatteryPower())
        except Exception:
            return None
        return b if 0 <= b <= 100 else None

    def get_ctrl_mode(self) -> Optional[int]:
        # Ojo (guía 4.1.22): devuelve el ÚLTIMO estado ejecutado; tras una acción sin move()
        # puede seguir diciendo "acción". Solo se usa como pista. NO VERIFICADO con el robot real.
        if self._mode_fn is None:
            return None
        try:
            return int(self._mode_fn())
        except Exception:
            return None


class MockRobot(RobotBase):
    """Robot simulado para probar en el Mac: integra la pose con el comando aplicado.

    Imita las reglas que conocemos del SDK real:
    - move() antes de standUp() se rechaza (máquina de estados del cliente) -> 0x3007.
    - standUp()/lieDown() con el robot en movimiento se rechazan -> 0x3007.
    - Si pasan `watchdog_s` sin move() estando de pie, se acuesta en amortiguado (FAQ 6.9).
    """

    is_mock = True
    name = "D1 EDU (mock)"

    def __init__(self, clock: Callable[[], float] = time.monotonic, watchdog_s: float = 3.0,
                 battery: int = 87, record: int = 4000):
        self.clock = clock
        self.watchdog_s = watchdog_s
        self._lock = threading.Lock()
        self.state = "lying"         # lying | standing | passive
        self.cmd = (0.0, 0.0, 0.0)
        self.x = self.y = self.yaw = 0.0
        self._last_t = None
        self._last_move_t = None
        self._battery = float(battery)
        self.moves = deque(maxlen=record)   # (t, vx, vy, wz) para las pruebas
        self.calls = deque(maxlen=record)   # (t, nombre)
        self.connected = False

    def connect(self) -> None:
        self.connected = True
        self._last_t = self.clock()

    def _integrate(self) -> None:
        now = self.clock()
        if self._last_t is None:
            self._last_t = now
            return
        dt = max(0.0, min(now - self._last_t, 0.5))
        self._last_t = now
        if self.state == "standing":
            if self._last_move_t is not None and now - self._last_move_t > self.watchdog_s:
                self.state = "passive"   # watchdog del robot: se acuesta en amortiguado
                self.cmd = (0.0, 0.0, 0.0)
            vx, vy, wz = self.cmd
            c, s = math.cos(self.yaw), math.sin(self.yaw)
            self.x += (vx * c - vy * s) * dt
            self.y += (vx * s + vy * c) * dt
            self.yaw = math.atan2(math.sin(self.yaw + wz * dt), math.cos(self.yaw + wz * dt))
        self._battery = max(0.0, self._battery - dt * 0.002)

    def stand_up(self) -> Optional[int]:
        with self._lock:
            self._integrate()
            self.calls.append((self.clock(), "standUp"))
            if self.state == "standing" and any(abs(c) > 1e-9 for c in self.cmd):
                return 0x3007
            self.state = "standing"
            self.cmd = (0.0, 0.0, 0.0)
            self._last_move_t = self.clock()
            return 0

    def lie_down(self) -> Optional[int]:
        with self._lock:
            self._integrate()
            self.calls.append((self.clock(), "lieDown"))
            if any(abs(c) > 1e-9 for c in self.cmd):
                return 0x3007
            self.state = "lying"
            return 0

    def passive(self) -> Optional[int]:
        with self._lock:
            self._integrate()
            self.calls.append((self.clock(), "passive"))
            self.state = "passive"
            self.cmd = (0.0, 0.0, 0.0)
            return 0

    def move(self, vx: float, vy: float, wz: float) -> Optional[int]:
        with self._lock:
            self._integrate()
            now = self.clock()
            self.moves.append((now, float(vx), float(vy), float(wz)))
            if self.state != "standing":
                return 0x3007
            self.cmd = (float(vx), float(vy), float(wz))
            self._last_move_t = now
            return 0

    def check_connection(self) -> bool:
        return self.connected

    def get_pose(self) -> Optional[Pose]:
        with self._lock:
            self._integrate()
            return Pose(self.x, self.y, self.yaw)

    def get_battery(self) -> Optional[int]:
        with self._lock:
            self._integrate()
            return int(round(self._battery))

    def get_ctrl_mode(self) -> Optional[int]:
        with self._lock:
            self._integrate()
            if self.state == "standing":
                return 18 if any(abs(c) > 1e-9 for c in self.cmd) else 1
            return {"lying": 51, "passive": 0}.get(self.state)

    def last_move(self):
        with self._lock:
            return self.moves[-1] if self.moves else None


# --------------------------------------------------------------------------
# Guardia de atasco: si el lazo de control se congela, manda ceros desde otro hilo
# --------------------------------------------------------------------------
class StallGuard:
    """Hilo vigilante independiente del lazo de control.

    Motivo: el demo oficial deja el robot de pie esperando input() varios segundos sin mandar
    nada y no se acuesta, lo que sugiere que la librería sigue enviando por UDP el ÚLTIMO comando
    por su cuenta (NO VERIFICADO con el robot real). Si fuera así y nuestro lazo se congelara con
    una velocidad distinta de cero, el robot seguiría caminando. Este hilo manda move(0,0,0)
    si el lazo no late en `stall_s` segundos (el SDK es thread-safe según la FAQ 6.8).
    """

    def __init__(self, robot: RobotBase, stall_s: float = 0.5, period_s: float = 0.1,
                 log: Callable[[str], None] = print):
        self.robot = robot
        self.stall_s = stall_s
        self.period_s = period_s
        self.log = log
        self._last_beat = time.monotonic()
        self._armed = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="d1-stall-guard", daemon=True)
        self.trips = 0

    def start(self) -> "StallGuard":
        self._thread.start()
        return self

    def beat(self, armed: bool) -> None:
        """Llamar en cada tick. armed=True cuando el robot está de pie (move() es válido)."""
        self._last_beat = time.monotonic()
        self._armed = armed

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        stalled = False
        while not self._stop.wait(self.period_s):
            late = time.monotonic() - self._last_beat
            if self._armed and late > self.stall_s:
                if not stalled:
                    self.trips += 1
                    self.log(f"[guardia] el lazo de control no late hace {late:.2f} s: "
                             "mando move(0,0,0) desde el hilo vigilante")
                stalled = True
                try:
                    self.robot.move(0.0, 0.0, 0.0)
                except Exception:
                    pass
            elif stalled and late <= self.stall_s:
                stalled = False
                self.log("[guardia] el lazo volvió a latir")


def connect_with_timeout(robot: RobotBase, timeout_s: float = 15.0) -> None:
    """robot.connect() en un hilo; si no vuelve a tiempo, error claro (no se puede matar el hilo)."""
    box = {}

    def target():
        try:
            robot.connect()
            box["ok"] = True
        except BaseException as exc:  # noqa: BLE001 - se re-lanza abajo
            box["err"] = exc

    t = threading.Thread(target=target, name="d1-connect", daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        raise TimeoutError(
            f"initRobot no respondió en {timeout_s:.0f} s. Revisa: sdk_config.yaml del robot con "
            "target_ip = IP de esta máquina, VM en modo puente, firewall UDP (guía 6.1 y 6.19).")
    if "err" in box:
        raise box["err"]


# --------------------------------------------------------------------------
# Diagnóstico: python3.10 -m d1.sdk --sdk-path ~/agibot_D1_Edu-Ultra
# --------------------------------------------------------------------------
def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Verifica que el SDK del D1 se puede importar.")
    ap.add_argument("--sdk-path", default=None)
    ap.add_argument("--robot-ip", default=DEFAULT_ROBOT_IP)
    args = ap.parse_args(argv)
    print(f"Python {sys.version.split()[0]} en {sys.platform}/{machine_arch()}")
    ip = detect_local_ip(args.robot_ip)
    print(f"IP local con ruta a {args.robot_ip}: {ip or 'NINGUNA'}")
    if ip:
        for w in network_warnings(ip, args.robot_ip):
            print("  AVISO:", w)
    try:
        mod, lib_dir = load_sdk_module(args.sdk_path)
    except Exception as exc:
        print(f"ERROR importando {SDK_MODULE}: {exc}")
        return 1
    hl = getattr(mod, "HighLevel", None)
    print(f"OK: {SDK_MODULE} importado desde {lib_dir}")
    if hl is not None:
        names = [n for n in ("initRobot", "checkConnect", "checkConnection", "standUp", "lieDown",
                             "passive", "move", "getPosition", "getRPY", "getBatteryPower",
                             "getCurrentCtrlmode", "getCurrentCtrlMode") if hasattr(hl, n)]
        print("Métodos de HighLevel encontrados:", ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
