"""Barreras de seguridad del D1 real (decisión en el servidor, nunca solo en la web).

Las reglas puras viven aquí (geocerca, configuración); `robot_link.RobotLink` las aplica sobre el flujo
de teleop/telemetría y genera los eventos visibles. Ver datos/robot/GEMELO_DIGITAL.md.
"""
from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SafetyConfig:
    speed_cap_mps: float = 0.3          # tope global de la demo (0 = sin tope)
    geofence: bool = True
    bed_margin_m: float = 0.25          # distancia mínima del centro del gemelo al borde de una cama
    battery_stand_min: float = 25.0     # % — por debajo no se permite 'stand'
    battery_lie_below: float = 15.0     # % — por debajo, 'lie' seguro (cero primero)
    telemetry_stale_s: float = 1.0      # telemetría más vieja => se dejan de mandar órdenes
    video_loss_s: float = 3.0           # sin cámara más de esto en Manual => cero
    video_guard: str = "auto"           # auto: activa desde que el panel avisa una vez | on | off
    panel_fresh_s: float = 1.5          # el latido del panel (cada 0,5 s) vale este tiempo
    pose_fresh_s: float = 1.0           # la pose del gemelo vale este tiempo para la geocerca
    zero_after_viewer_s: float = 1.0    # ceros explícitos tras caerse el WS del navegador

    @classmethod
    def from_env(cls) -> "SafetyConfig":
        c = cls()
        if os.environ.get("BERRY_SPEED_CAP"):
            c.speed_cap_mps = max(0.0, float(os.environ["BERRY_SPEED_CAP"]))
        if os.environ.get("BERRY_VIDEO_GUARD") in ("auto", "on", "off"):
            c.video_guard = os.environ["BERRY_VIDEO_GUARD"]
        if os.environ.get("BERRY_GEOFENCE") in ("0", "off", "false"):
            c.geofence = False
        return c

    def update(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cambios en caliente (POST /api/safety). Valores inválidos se ignoran."""
        for k, v in data.items():
            if k not in self.__dataclass_fields__:
                continue
            cur = getattr(self, k)
            try:
                if isinstance(cur, bool):
                    setattr(self, k, bool(v))
                elif isinstance(cur, float):
                    f = float(v)
                    if math.isfinite(f) and f >= 0:
                        setattr(self, k, f)
                elif k == "video_guard" and v in ("auto", "on", "off"):
                    setattr(self, k, v)
            except (TypeError, ValueError):
                pass
        return asdict(self)


def geofence_check(fm: Any, x: float, z: float, margin: float = 0.25) -> tuple[str, str] | None:
    """None si (x, z) está en el área permitida; si no, (tipo, texto en español).

    Área permitida (marco de la escena, el mismo de `layout`): los pasillos entre camas, el pasillo
    principal del frente (5 m) y la cabecera norte. Dentro de las hileras solo valen los pasillos, a
    más de `margin` m del borde de una cama.
    """
    if not (math.isfinite(x) and math.isfinite(z)):
        return ("area", "fuera del pasillo: posición inválida")
    x1 = fm.x0 + fm.width
    if z < fm.bed_z0 - fm.main_path_w or z > fm.bed_z1 + fm.north_w:
        return ("area", "fuera del pasillo: salió del área del bloque")
    in_tunnel = z > fm.bed_z0 - 0.4
    xlo, xhi = (fm.x0, x1) if in_tunnel else (fm.x0 - 4.0, x1 + 4.0)
    if not (xlo <= x <= xhi):
        return ("area", "fuera del pasillo: salió del área del bloque")
    if fm.bed_z0 <= z <= fm.bed_z1:
        half = fm.bed_w / 2.0
        near = min(abs(x - cx) - half for cx in fm.bed_centers_x)  # distancia al borde de la cama más cercana
        if near < margin:
            return ("cama", f"fuera del pasillo: a {max(near, 0.0):.2f} m de una cama (mínimo {margin:.2f} m)")
        if not any(abs(x - a.x) <= fm.pitch / 2.0 - half - margin for a in fm.aisles):
            return ("area", "fuera del pasillo: no está en un pasillo entre camas")
    return None
