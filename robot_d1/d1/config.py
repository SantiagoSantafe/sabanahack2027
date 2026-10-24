"""Configuración: valores por defecto sensatos, YAML opcional (--config) y argumentos CLI.

Prioridad: argumentos CLI > archivo YAML > valores por defecto de aquí.
"""

from __future__ import annotations

import argparse
import copy
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .safety import Accel, Limits

DEFAULTS: Dict[str, Any] = {
    "robot": {
        "ip": "192.168.234.1",      # Wi-Fi (AP del D1). Cable: 192.168.168.168
        "local_ip": None,           # None = autodetectar la interfaz con ruta al robot
        "local_port": 43988,        # = target_port de /opt/export/config/sdk_config.yaml
        "sdk_path": None,           # raíz del repo agibot_D1_Edu-Ultra (o D1_SDK_PATH)
    },
    "sim": {
        "mac_ip": None,             # IP del Mac con sim-core (FastAPI :8000)
        "port": 8000,
        "path": "/ws/robot",
    },
    "limits": {                     # contrato v1, interiores
        "vx_max": 0.4,
        "vx_fast": 0.8,
        "vy_max": 0.25,
        "wz_max": 0.6,
        "speed_cap": None,          # tope global de velocidad lineal (m/s), p. ej. 0.3 en la demo; None = sin tope
    },
    "accel": {
        "ax": 0.8,
        "ay": 0.6,
        "aw": 1.5,
        "decel_factor": 2.0,
    },
    "control": {
        "hz": 50.0,                  # medido: el D1 se mantiene estable con move() a 50 Hz
        "telemetry_hz": 10.0,
        "teleop_ttl_s": 0.3,
        "stand_settle_s": 1.5,      # tras standUp se manda velocidad cero continua (el robot llega al modo 18 en ~1 s)
        "lie_settle_s": 2.0,
        "lie_zero_s": 0.4,          # antes de lieDown, tiempo con velocidad aplicada = 0
        "stall_guard_s": 0.5,
        "detection_hold_default_s": 4.0,
        "battery_stand_min": 25,    # % — por debajo no se permite pararse (0 = apagado)
        "battery_lie_below": 15,    # % — por debajo, de pie => cero y acostarse (0 = apagado)
    },
    "keyboard": {
        "initial_hold_s": 0.6,      # cubre la demora inicial de autorrepetición (~0,5 s)
        "repeat_hold_s": 0.15,      # con la tecla repitiendo, soltar detiene en <= 0,15 s
        "release_grace_s": 0.08,    # modo pynput: tolera pares soltar/pulsar de la autorrepetición
        "speed_levels": [0.4, 0.6, 0.8, 1.0],
        "speed_level": 1,           # índice: 0.6 de los límites al arrancar
    },
}


def deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_yaml(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        import yaml  # pyyaml, opcional
    except ImportError as exc:
        raise SystemExit("Para usar --config instala pyyaml (pip install pyyaml).") from exc
    with open(os.path.expanduser(path), "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: el YAML debe ser un diccionario.")
    return data


@dataclass
class Config:
    raw: Dict[str, Any] = field(default_factory=lambda: copy.deepcopy(DEFAULTS))

    # Accesos cómodos
    @property
    def robot_ip(self) -> str:
        return str(self.raw["robot"]["ip"])

    @property
    def local_ip(self) -> Optional[str]:
        return self.raw["robot"].get("local_ip")

    @property
    def local_port(self) -> int:
        return int(self.raw["robot"]["local_port"])

    @property
    def sdk_path(self) -> Optional[str]:
        return self.raw["robot"].get("sdk_path")

    @property
    def limits(self) -> Limits:
        l = self.raw["limits"]
        vx, vxf, vy, wz = float(l["vx_max"]), float(l["vx_fast"]), float(l["vy_max"]), float(l["wz_max"])
        cap = l.get("speed_cap")
        if cap is not None and float(cap) > 0:      # tope global de la demo: recorta TODAS las velocidades lineales
            c = float(cap)
            vx, vxf, vy = min(vx, c), min(vxf, c), min(vy, c)
        return Limits(vx, vxf, vy, wz)

    @property
    def accel(self) -> Accel:
        a = self.raw["accel"]
        return Accel(float(a["ax"]), float(a["ay"]), float(a["aw"]), float(a["decel_factor"]))

    def control(self, key: str) -> float:
        return float(self.raw["control"][key])

    def keyboard(self, key: str):
        return self.raw["keyboard"][key]

    @property
    def speed_levels(self) -> List[float]:
        lv = [float(x) for x in self.raw["keyboard"]["speed_levels"]]
        return [min(1.0, max(0.05, x)) for x in lv] or [0.6]

    def ws_url(self) -> Optional[str]:
        s = self.raw["sim"]
        if not s.get("mac_ip"):
            return None
        return f"ws://{s['mac_ip']}:{int(s['port'])}{s['path']}"


def add_common_args(ap: argparse.ArgumentParser) -> None:
    g = ap.add_argument_group("robot")
    g.add_argument("--config", help="archivo YAML (ver config.example.yaml)")
    g.add_argument("--robot-ip", help="IP del D1 (Wi-Fi 192.168.234.1, cable 192.168.168.168)")
    g.add_argument("--local-ip", help="IP de esta máquina hacia el robot (por defecto: autodetectar)")
    g.add_argument("--local-port", type=int, help="puerto local UDP (por defecto 43988)")
    g.add_argument("--sdk-path", help="carpeta del repo agibot_D1_Edu-Ultra")
    g.add_argument("--mock", action="store_true", help="robot simulado (sin SDK ni robot)")
    l = ap.add_argument_group("límites (m/s, rad/s)")
    l.add_argument("--vx-max", type=float)
    l.add_argument("--vx-fast", type=float)
    l.add_argument("--vy-max", type=float)
    l.add_argument("--wz-max", type=float)
    l.add_argument("--speed-cap", type=float,
                   help="tope global de velocidad lineal en m/s (demo: 0.3); recorta vx, vx-fast y vy")


def build_config(args: argparse.Namespace) -> Config:
    raw = deep_merge(DEFAULTS, load_yaml(getattr(args, "config", None)))
    r, lim, sim = raw["robot"], raw["limits"], raw["sim"]
    for attr, (sect, key) in {
        "robot_ip": (r, "ip"), "local_ip": (r, "local_ip"), "local_port": (r, "local_port"),
        "sdk_path": (r, "sdk_path"), "vx_max": (lim, "vx_max"), "vx_fast": (lim, "vx_fast"),
        "vy_max": (lim, "vy_max"), "wz_max": (lim, "wz_max"), "speed_cap": (lim, "speed_cap"), "mac_ip": (sim, "mac_ip"),
        "ws_port": (sim, "port"),
    }.items():
        val = getattr(args, attr, None)
        if val is not None:
            sect[key] = val
    if os.environ.get("MAC_IP") and not sim.get("mac_ip"):
        sim["mac_ip"] = os.environ["MAC_IP"]
    return Config(raw)
