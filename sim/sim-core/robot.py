"""Robot pathing inside a macrotunnel block: aisles between pot rows + headlands.

Each nave holds `beds_per_nave` pot rows; the robot walks the interior aisles of every
nave and its camera frames the plants on both sides. Overflowing foliage narrows the
aisle: the robot shifts to the center of the free gap, slows down, brushes leaves when
the gap is narrower than its body, and rigid platforms turn back when they cannot pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


@dataclass
class Waypoint:
    x: float
    z: float
    kind: str  # route | aisle_enter | capture | aisle_exit | blocked | dock
    aisle: int = -1
    plants: tuple[tuple[int, int], ...] = ()
    speed_factor: float = 1.0
    careful: bool = False
    contact: bool = False
    skipped: int = 0


@dataclass
class Aisle:
    index: int
    x: float
    left: int
    right: int
    nave: int


class FieldMap:
    """Block geometry shared by routing, sensing and the client (sent as `layout`)."""

    def __init__(self, field_cfg: dict[str, Any], robot_cfg: dict[str, Any]):
        self.n_naves = int(field_cfg.get("naves", 4))
        self.bpn = int(field_cfg.get("beds_per_nave", 3))
        self.nave_w = float(field_cfg.get("nave_width_m", 6.8))
        self.n_beds = self.n_naves * self.bpn
        self.n_plants = int(field_cfg["plants_per_bed"])
        self.spacing = float(field_cfg["plant_spacing_m"])
        self.bed_w = float(field_cfg.get("bed_width_m", 0.6))
        self.pitch = self.nave_w / self.bpn
        # Bloques: las naves se reparten en `blocks` grupos separados por el camino central (a lo largo de las camas)
        self.n_blocks = max(1, min(int(field_cfg.get("blocks", 1)), self.n_naves))
        self.central_w = float(field_cfg.get("central_path_width_m", 5.0)) if self.n_blocks > 1 else 0.0
        self.npb = -(-self.n_naves // self.n_blocks)  # naves por bloque (redondeo hacia arriba)
        self.width = self.n_naves * self.nave_w + (self.n_blocks - 1) * self.central_w
        self.x0 = -self.width / 2.0
        self.nave_x0 = [self.x0 + k * self.nave_w + (k // self.npb) * self.central_w for k in range(self.n_naves)]
        self.bed_centers_x = [
            self.nave_x0[b // self.bpn] + (b % self.bpn + 0.5) * self.pitch for b in range(self.n_beds)
        ]
        self.aisles: list[Aisle] = []
        for k in range(self.n_naves):
            for j in range(self.bpn - 1):
                left = k * self.bpn + j
                self.aisles.append(Aisle(len(self.aisles), self.nave_x0[k] + (j + 1) * self.pitch, left, left + 1, k))
        self.bed_len = (self.n_plants - 1) * self.spacing
        self.z0 = -self.bed_len / 2.0
        self.z1 = self.bed_len / 2.0
        path = robot_cfg.get("path", {})
        self.bed_pad = float(path.get("bed_end_pad_m", 0.3))
        self.bed_z0 = self.z0 - self.bed_pad
        self.bed_z1 = self.z1 + self.bed_pad
        self.main_path_w = float(field_cfg.get("main_path_width_m", 5.0))
        self.north_w = float(field_cfg.get("north_headland_m", 1.5))
        self.head_s = self.bed_z0 - float(path.get("main_path_walk_m", 1.3))
        self.head_n = self.bed_z1 + self.north_w / 2.0
        base_x = self.central_x()[0] + 1.2 if self.n_blocks > 1 else self.nave_x0[0] + 1.2
        self.base = (base_x, self.bed_z0 - float(path.get("base_offset_m", 3.6)))  # al pie del camino central
        self.margin = float(path.get("collision_margin_m", 0.12))
        n = self.n_beds * self.n_plants
        self.spread_l = np.full(n, 0.45, dtype=np.float32)
        self.spread_r = np.full(n, 0.45, dtype=np.float32)

    def block_of_nave(self, nave: int) -> int:
        """Bloque (1..n) de una nave (índice 0..n-1)."""
        return min(nave // self.npb, self.n_blocks - 1) + 1

    def central_x(self) -> tuple[float, float]:
        """(x0, x1) del camino central entre el bloque 1 y el 2 (vacío si hay un solo bloque)."""
        if self.n_blocks < 2:
            return (self.x0, self.x0)
        x0 = self.nave_x0[self.npb - 1] + self.nave_w
        return (x0, x0 + self.central_w)

    def block_aisles(self, block: int) -> list[int]:
        """Índices de los pasillos del bloque (1..n), de oeste a este."""
        return [a.index for a in self.aisles if self.block_of_nave(a.nave) == block] or [a.index for a in self.aisles]

    def block_start(self, block: int) -> tuple[float, float, float]:
        """Inicio predefinido del bloque: entrada del primer pasillo, en la cabecera sur, mirando al fondo (+z)."""
        a = self.aisles[self.block_aisles(block)[0]]
        return (a.x, self.head_s, 0.0)

    @property
    def area_ha(self) -> float:
        return self.width * (self.bed_len + 2 * self.bed_pad) / 10000.0

    def idx(self, bed: int, plant: int) -> int:
        return bed * self.n_plants + plant

    def plant_z(self, plant: int) -> float:
        return self.z0 + plant * self.spacing

    def nearest_plant(self, z: float) -> int:
        return int(min(max(round((z - self.z0) / self.spacing), 0), self.n_plants - 1))

    def bed_label(self, bed: int) -> str:
        return f"Nave {bed // self.bpn + 1} · Cama {bed % self.bpn + 1}"

    def aisle_label(self, a: Aisle) -> str:
        return f"Nave {a.nave + 1} · Camas {a.left % self.bpn + 1} y {a.right % self.bpn + 1}"

    def in_row(self, x: float, z: float, margin: float) -> bool:
        if z < self.bed_z0 - margin or z > self.bed_z1 + margin:
            return False
        return any(abs(x - cx) <= self.bed_w / 2.0 + margin for cx in self.bed_centers_x)

    def segment_clear(self, p: tuple[float, float], q: tuple[float, float], margin: float | None = None) -> bool:
        m = self.margin if margin is None else margin
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        n = max(2, int(d / 0.1))
        return not any(
            self.in_row(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n, m) for k in range(n + 1)
        )

    def nearest_aisle(self, x: float) -> Aisle:
        return min(self.aisles, key=lambda a: abs(a.x - x))

    def route(self, p: tuple[float, float], q: tuple[float, float]) -> list[tuple[float, float]]:
        """Points from p (excluded) to q (included) using aisles and headlands only."""
        if self.segment_clear(p, q):
            return [q]
        ax_p = self.nearest_aisle(p[0]).x
        ax_q = self.nearest_aisle(q[0]).x
        best: list[tuple[float, float]] = [q]
        best_len = float("inf")
        for hz in (self.head_s, self.head_n):
            pts = [(ax_p, p[1]), (ax_p, hz), (ax_q, hz), (ax_q, q[1]), q]
            clean: list[tuple[float, float]] = []
            prev = p
            length = 0.0
            for pt in pts:
                d = math.hypot(pt[0] - prev[0], pt[1] - prev[1])
                if d > 1e-6:
                    clean.append(pt)
                    length += d
                    prev = pt
            if length < best_len:
                best, best_len = clean, length
        return best

    def gap(self, a: Aisle, plant: int) -> tuple[float, float]:
        """(x of the free-gap center, free width) between the two rows at a plant index."""
        xl = self.bed_centers_x[a.left]
        xr = self.bed_centers_x[a.right]
        sl = float(self.spread_r[self.idx(a.left, plant)])
        sr = float(self.spread_l[self.idx(a.right, plant)])
        free = (xr - xl) - sl - sr
        return xl + sl + free / 2.0, free

    def layout(self) -> dict[str, Any]:
        return {
            "naves": self.n_naves,
            "beds_per_nave": self.bpn,
            "nave_width": self.nave_w,
            "nave_x0": self.nave_x0,
            "bed_x": self.bed_centers_x,
            "bed_w": self.bed_w,
            "aisles": [{"x": a.x, "left": a.left, "right": a.right, "nave": a.nave} for a in self.aisles],
            "n_plants": self.n_plants,
            "spacing": self.spacing,
            "z0": self.z0,
            "bed_z0": self.bed_z0,
            "bed_z1": self.bed_z1,
            "head_s": self.head_s,
            "head_n": self.head_n,
            "main_path_w": self.main_path_w,
            "north_w": self.north_w,
            "base": list(self.base),
            "area_ha": self.area_ha,
            "central": list(self.central_x()) if self.n_blocks > 1 else None,
            "blocks": [
                {
                    "id": b,
                    "naves": [k + 1 for k in range(self.n_naves) if self.block_of_nave(k) == b],
                    "x0": min(self.nave_x0[k] for k in range(self.n_naves) if self.block_of_nave(k) == b),
                    "x1": max(self.nave_x0[k] + self.nave_w for k in range(self.n_naves) if self.block_of_nave(k) == b),
                    "aisles": self.block_aisles(b),
                    "start": list(self.block_start(b)),
                    "start_label": self.aisle_label(self.aisles[self.block_aisles(b)[0]]),
                }
                for b in range(1, self.n_blocks + 1)
            ],
        }


CaptureFn = Callable[[int, int], bool]


class RobotController:
    """Kinematic patrol controller. Time is in simulated seconds."""

    def __init__(
        self,
        field_map: FieldMap,
        robot_cfg: dict[str, Any],
        alt: dict[str, Any],
        rng: np.random.Generator,
    ):
        self.robot_cfg = robot_cfg
        self.alt = alt
        self.rng = rng
        self.map = field_map
        self.platform = str(alt.get("platform", "quadruped"))
        self.active = self.platform != "none"
        mob = alt.get("mobility", {})
        self.base_speed = float(mob.get("speed_mps", robot_cfg.get("inspection_speed_mps", 0.5)))
        self.hours_per_ha = mob.get("hours_per_ha")
        self.speed_mps = self.base_speed
        self.battery_h = float(mob.get("battery_h", robot_cfg.get("battery_hours", 1.5)))
        self.fail_prob = float(mob.get("fail_prob_per_bed", 0.0))
        self.mud_slowdown = max(1.0, float(mob.get("mud_slowdown", 1.0)))
        self.stuck_prob = float(mob.get("stuck_prob", 0.0))
        self.mast = bool(alt.get("mast", False))
        self.width = float(mob.get("width_m", 0.36))
        height = float(mob.get("height_m", 0.42))
        if self.mast:
            height = max(height, float(robot_cfg.get("mast", {}).get("height_m", 1.35)))
        self.height = height
        self.rigid = bool(mob.get("rigid", False))
        self.return_thr = float(robot_cfg.get("battery_return_threshold", 0.2))
        self.charge_h = float(robot_cfg.get("charge_hours", 1.0))
        path = robot_cfg.get("path", {})
        self.lookahead = float(path.get("camera_lookahead_m", 1.2))
        self.rescue_after_s = float(path.get("rescue_after_s", 7200))
        fol = robot_cfg.get("foliage", {})
        self.careful_c = float(fol.get("careful_clearance_m", 0.25))
        self.careful_f = float(fol.get("careful_speed_factor", 0.5))
        self.contact_f = float(fol.get("contact_speed_factor", 0.3))
        self.canopy_low = float(fol.get("canopy_low_m", 0.5))
        self.block_c = float(fol.get("rigid_block_clearance_m", -0.1))

        self.x, self.z = self.map.base
        self.heading = 0.0
        self.speed = 0.0
        self.battery = 1.0
        self.state = "docked"
        self.mode = "auto"
        self.path: list[Waypoint] = []
        self.wp = 0
        self.hold_s = 0.0
        self.down_s = 0.0
        self.odometry_m = 0.0
        self.busy_s = 0.0
        self.current_aisle = -1
        self.bed_label = ""
        self.patrol_active = False
        self.patrol_aisles: list[int] = []
        self.aisles_done: list[int] = []
        self.target: tuple[int, int] | None = None
        self.contacts = 0
        self.careful_passes = 0
        self.plants_skipped = 0
        self.blocked = 0
        self._warned_aisle = -1

    # ----- planning -----
    def is_busy(self) -> bool:
        return self.active and self.state in ("walking", "inspecting", "returning", "manual")

    def start_patrol(self, aisle_order: list[int]) -> None:
        if not self.active or self.mode == "manual" or self.state in ("failed", "stuck"):
            return
        self.patrol_active = True
        self.patrol_aisles = list(aisle_order)
        self.aisles_done = []
        self._plan(self.patrol_aisles)
        if self.hours_per_ha:
            length = self._path_length()
            target_s = self.map.area_ha * float(self.hours_per_ha) * 3600.0
            self.speed_mps = float(np.clip(length / max(target_s, 1.0), 0.1, 1.5))
        self.state = "walking"

    def _path_length(self) -> float:
        total, prev = 0.0, (self.x, self.z)
        for w in self.path:
            total += math.hypot(w.x - prev[0], w.z - prev[1])
            prev = (w.x, w.z)
        return total

    def _foliage(self, a: Aisle, cz: float) -> tuple[float, float, bool, bool, bool]:
        """(x, speed factor, careful, contact, blocked) for the robot standing at cz."""
        m = self.map
        if cz < m.bed_z0 or cz > m.bed_z1:
            return a.x, 1.0, False, False, False
        q = m.nearest_plant(cz)
        gx, free = m.gap(a, q)
        c = (free - self.width) / 2.0
        lo = m.bed_centers_x[a.left] + m.bed_w / 2.0 + self.width / 2.0
        hi = m.bed_centers_x[a.right] - m.bed_w / 2.0 - self.width / 2.0
        x = float(min(max(gx, lo), hi)) if lo < hi else a.x
        if c >= self.careful_c:
            return x, 1.0, False, False, False
        if c > 0:
            return x, self.careful_f, True, False, False
        if self.rigid and c < self.block_c:
            return x, 0.0, True, True, True
        touches = self.height > self.canopy_low
        return x, (self.contact_f if touches else self.careful_f), True, touches, False

    def _plan(self, aisle_ids: list[int]) -> None:
        m = self.map
        wps: list[Waypoint] = []
        cur = (self.x, self.z)
        at_south = abs(cur[1] - m.head_s) <= abs(cur[1] - m.head_n)
        for ai in aisle_ids:
            a = m.aisles[ai]
            enter_z = m.head_s if at_south else m.head_n
            exit_z = m.head_n if at_south else m.head_s
            for pt in m.route(cur, (a.x, enter_z))[:-1]:
                wps.append(Waypoint(pt[0], pt[1], "route"))
            wps.append(Waypoint(a.x, enter_z, "aisle_enter", ai))
            direction = 1.0 if at_south else -1.0
            order = list(range(m.n_plants)) if at_south else list(range(m.n_plants - 1, -1, -1))
            groups: dict[float, list[int]] = {}
            for p in order:
                cz = m.plant_z(p) - direction * self.lookahead
                cz = min(max(cz, min(enter_z, exit_z)), max(enter_z, exit_z))
                groups.setdefault(round(cz, 4), []).append(p)
            blocked_at: int | None = None
            for cz, plants in groups.items():
                x, f, careful, contact, blocked = self._foliage(a, cz)
                if blocked:
                    blocked_at = plants[0]
                    remaining = len(order) - order.index(plants[0])
                    wps.append(Waypoint(wps[-1].x, wps[-1].z, "blocked", ai, skipped=remaining * 2))
                    wps.append(Waypoint(a.x, enter_z, "route"))
                    break
                pairs = tuple(pair for p in plants for pair in ((a.left, p), (a.right, p)))
                wps.append(Waypoint(x, cz, "capture", ai, pairs, f, careful, contact))
            if blocked_at is None:
                wps.append(Waypoint(a.x, exit_z, "aisle_exit", ai))
                cur = (a.x, exit_z)
                at_south = not at_south
            else:
                wps.append(Waypoint(a.x, enter_z, "aisle_exit", ai))
                cur = (a.x, enter_z)
        for pt in m.route(cur, m.base):
            wps.append(Waypoint(pt[0], pt[1], "route"))
        wps[-1] = Waypoint(m.base[0], m.base[1], "dock")
        self.path = wps
        self.wp = 0

    def _plan_to_base(self) -> None:
        pts = self.map.route((self.x, self.z), self.map.base)
        self.path = [Waypoint(p[0], p[1], "route") for p in pts]
        self.path[-1] = Waypoint(self.map.base[0], self.map.base[1], "dock")
        self.wp = 0

    def hold(self, seconds: float) -> None:
        if self.mode == "manual":
            return
        self.state = "inspecting"
        self.hold_s = seconds
        self.speed = 0.0

    # ----- manual -----
    def set_manual(self, on: bool) -> None:
        if not self.active:
            return
        if on:
            self.mode = "manual"
            self.state = "manual"
            self.path = []
            return
        self.mode = "auto"
        remaining = [a for a in self.patrol_aisles if a not in self.aisles_done]
        if self.patrol_active and remaining:
            self._plan(remaining)
        else:
            self.patrol_active = False
            self._plan_to_base()
        self.state = "walking"

    def set_pose(self, x: float, z: float, heading: float, speed: float) -> None:
        if self.mode != "manual" or self.map.in_row(x, z, 0.02):
            return
        self.odometry_m += math.hypot(x - self.x, z - self.z)
        self.x, self.z, self.heading, self.speed = float(x), float(z), float(heading), float(speed)

    # ----- stepping -----
    def _drain(self, dt: float) -> None:
        if self.battery_h > 0:
            self.battery = max(0.0, self.battery - dt / (self.battery_h * 3600.0))

    def step(self, dt: float, muddy: bool, on_capture: CaptureFn) -> list[dict[str, Any]]:
        ev: list[dict[str, Any]] = []
        if not self.active:
            return ev
        st = self.state
        if self.is_busy():
            self.busy_s += dt

        if st == "manual":
            self._drain(dt)
            return ev
        if st in ("docked", "charging"):
            self.speed = 0.0
            self.battery = min(1.0, self.battery + dt / (self.charge_h * 3600.0))
            if st == "charging" and self.battery >= 0.98:
                remaining = [a for a in self.patrol_aisles if a not in self.aisles_done]
                if self.patrol_active and remaining:
                    self._plan(remaining)
                    self.state = "walking"
                    ev.append({"type": "charged"})
                else:
                    self.state = "docked"
            return ev
        if st in ("failed", "stuck"):
            self.speed = 0.0
            self.down_s += dt
            if st == "stuck" and self.rng.random() < 1.0 - math.exp(-dt / 600.0):
                self.state = "walking"
                self.down_s = 0.0
                ev.append({"type": "unstuck"})
            elif self.down_s >= self.rescue_after_s:
                self.x, self.z = self.map.base
                self.state = "docked"
                self.patrol_active = False
                self.down_s = 0.0
                self.current_aisle = -1
                self.bed_label = ""
                ev.append({"type": "rescued"})
            return ev
        if st == "inspecting":
            self._drain(dt)
            self.speed = 0.0
            self.hold_s -= dt
            if self.hold_s <= 0:
                self.state = "walking"
            return ev

        self._drain(dt)
        if st == "walking" and self.battery <= self.return_thr:
            self.state = "returning"
            self._plan_to_base()
            ev.append({"type": "battery_low", "battery": self.battery})

        budget_t = dt
        moved = False
        speed_now = 0.0
        while budget_t > 1e-9 and self.wp < len(self.path):
            w = self.path[self.wp]
            v = self.speed_mps * w.speed_factor / (self.mud_slowdown if muddy else 1.0)
            v = max(v, 0.02)
            dx, dz = w.x - self.x, w.z - self.z
            d = math.hypot(dx, dz)
            if d > 1e-6:
                self.heading = math.atan2(dx, dz)
            reach_t = d / v
            if reach_t > budget_t:
                step = v * budget_t
                self.x += dx / d * step
                self.z += dz / d * step
                self.odometry_m += step
                moved = True
                speed_now = v
                break
            self.x, self.z = w.x, w.z
            self.odometry_m += d
            budget_t -= reach_t
            moved = moved or d > 0
            speed_now = v
            self.wp += 1
            if self._arrive(w, muddy, ev, on_capture):
                break
        self.speed = speed_now if moved and self.state in ("walking", "returning") else 0.0
        self.target = self._next_capture()
        return ev

    def _next_capture(self) -> tuple[int, int] | None:
        for w in self.path[self.wp : self.wp + 3]:
            if w.kind == "capture" and w.plants:
                return (w.aisle, w.plants[0][1])
        return None

    def _arrive(self, w: Waypoint, muddy: bool, ev: list[dict[str, Any]], on_capture: CaptureFn) -> bool:
        if w.kind == "aisle_enter":
            a = self.map.aisles[w.aisle]
            self.current_aisle = w.aisle
            self.bed_label = self.map.aisle_label(a)
            ev.append({"type": "aruco", "aisle": w.aisle, "beds": [a.left, a.right]})
            if self.fail_prob > 0 and self.rng.random() < self.fail_prob:
                self.state = "failed"
                ev.append({"type": "failed", "aisle": w.aisle})
                return True
            if muddy and self.stuck_prob > 0 and self.rng.random() < self.stuck_prob:
                self.state = "stuck"
                ev.append({"type": "stuck", "aisle": w.aisle})
                return True
        elif w.kind == "capture":
            if w.careful:
                self.careful_passes += 1
                if self._warned_aisle != w.aisle:
                    self._warned_aisle = w.aisle
                    ev.append({"type": "careful", "aisle": w.aisle, "contact": w.contact})
            if w.contact:
                self.contacts += 1
            stop = False
            for bed, plant in w.plants:
                stop = on_capture(bed, plant) or stop
            return stop
        elif w.kind == "blocked":
            self.blocked += 1
            self.plants_skipped += w.skipped
            ev.append({"type": "blocked", "aisle": w.aisle, "skipped": w.skipped})
        elif w.kind == "aisle_exit":
            if w.aisle not in self.aisles_done:
                self.aisles_done.append(w.aisle)
            ev.append({"type": "aisle_complete", "aisle": w.aisle})
        elif w.kind == "dock":
            self.current_aisle = -1
            self.bed_label = ""
            self.path = []
            self.wp = 0
            if self.state == "returning" and self.patrol_active:
                self.state = "charging"
                ev.append({"type": "docked_charging"})
            else:
                self.state = "docked"
                if self.patrol_active:
                    self.patrol_active = False
                    ev.append({"type": "patrol_complete"})
            ev.append({"type": "docked"})
            return True
        return False

    def snapshot(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "z": self.z,
            "heading": self.heading,
            "speed": self.speed,
            "state": self.state,
            "mode": self.mode,
            "battery": self.battery,
            "bed_label": self.bed_label,
            "mast": self.mast,
            "current_aisle": self.current_aisle,
            "platform": self.platform,
            "active": self.active,
            "odometry_m": self.odometry_m,
            "busy_s": self.busy_s,
            "target": list(self.target) if self.target else None,
            "patrol_active": self.patrol_active,
            "aisles_done": len(self.aisles_done),
            "aisles_total": len(self.patrol_aisles),
            "base": list(self.map.base),
            "width_m": self.width,
            "height_m": self.height,
            "rigid": self.rigid,
            "contacts": self.contacts,
            "careful_passes": self.careful_passes,
            "plants_skipped": self.plants_skipped,
        }


def prioritize_by_risk(risks: list[float], threshold: float) -> list[int]:
    """High-risk items first (descending), then the rest in spatial order."""
    high = sorted([i for i, r in enumerate(risks) if r >= threshold], key=lambda i: -risks[i])
    return high + [i for i, r in enumerate(risks) if r < threshold]


def build_patrol_path(
    field_cfg: dict[str, Any], robot_cfg: dict[str, Any], alt: dict[str, Any] | None = None, order: list[int] | None = None
) -> tuple[FieldMap, list[Waypoint]]:
    """Convenience for tests: full patrol path from the base with default foliage."""
    fm = FieldMap(field_cfg, robot_cfg)
    ctl = RobotController(fm, robot_cfg, alt or {"platform": "quadruped"}, np.random.default_rng(0))
    ctl._plan(order if order is not None else list(range(len(fm.aisles))))
    return fm, ctl.path
