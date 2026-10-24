"""Ruta real: el D1 real recorre solo la ruta del modo Auto (pasillos rectos + vueltas en U), siguiendo al gemelo.

Módulo puro (sin E/S, sin relojes): `plan_relativa` arma la ruta Auto escalada en el marco del robot
(adelante, izquierda) respecto al punto de partida; `Seguidor` genera (v, wz) tipo pure-pursuit sobre esa
polilínea ya en el marco de la odometría del D1. `RobotLink` (robot_link.py) lo conecta con el teleop y las barreras.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

Pt = tuple[float, float]


@dataclass
class RutaParams:
    escala: float = 1.0          # 1 = ruta del invernadero; 0,3 = versión reducida para una sala pequeña
    largo_max_m: float = 0.0     # 0 = sin límite; si no, se corta la ruta (ya escalada) a este largo
    v_recta: float = 0.2         # m/s en recta (tope duro)
    v_arco: float = 0.1          # m/s en los arcos de las vueltas
    wz_giro: float = 0.3         # rad/s máximo (giro lento, también en el sitio)
    lookahead_m: float = 0.5
    deriva_max_m: float = 0.4    # si el robot se aparta tanto del camino previsto, se detiene
    radio_arco_m: float = 0.0    # 0 = v_arco / wz_giro (el mínimo que el giro lento permite), con 20 % de holgura
    escaneos: int = 2            # paradas por pasillo para mirar a izquierda y derecha (0 = no mira a los lados)
    angulo_scan_deg: float = 60  # cuánto gira a cada lado en cada parada
    pausa_scan_s: float = 2.0    # tiempo mirando cada lado (la cámara del panel necesita ~2 s para una predicción estable)
    wz_scan: float = 0.5         # rad/s al girar para mirar (más rápido que en la ruta: es un giro en el sitio)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RutaParams":
        p = cls()
        for k in ("escala", "largo_max_m", "deriva_max_m", "escaneos", "angulo_scan_deg", "pausa_scan_s"):
            try:
                v = float(d.get(k, getattr(p, k)))
            except (TypeError, ValueError):
                continue
            if math.isfinite(v) and v >= 0:
                setattr(p, k, v)
        p.escala = min(max(p.escala, 0.002), 1.0)  # 0,005 ≈ 3,4 m reales para todo el bloque: cabe en una sala
        if p.escala < 0.02:  # ruta de sala: más lento para que el gemelo no cruce el pasillo de un salto
            p.v_recta, p.v_arco = 0.1, 0.06
        p.escaneos = int(min(p.escaneos, 6))
        p.angulo_scan_deg = min(max(p.angulo_scan_deg, 20.0), 90.0)
        p.pausa_scan_s = min(max(p.pausa_scan_s, 0.5), 10.0)
        p.deriva_max_m = max(p.deriva_max_m, 0.05)
        return p

    @property
    def radio(self) -> float:
        return self.radio_arco_m or 1.2 * self.v_arco / self.wz_giro


def _simplify(pts: list[Pt]) -> list[Pt]:
    out: list[Pt] = []
    for p in pts:
        if out and math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) < 1e-6:
            continue
        out.append(p)
    i = 1
    while i < len(out) - 1:  # quita vértices colineales
        a, b, c = out[i - 1], out[i], out[i + 1]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        dot = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])
        if abs(cross) < 1e-6 and dot > 0:
            out.pop(i)
        else:
            i += 1
    return out


def plan_relativa(fm: Any, p: RutaParams, aisles: list[int] | None = None) -> list[Pt]:
    """Vértices de la ruta Auto en el marco del robot al partir: (adelante, izquierda) en metros, ya escalados.

    Parte de la entrada del primer pasillo mirando a lo largo de las camas; recorre los pasillos en serpentina
    (misma lógica que `RobotController._plan`: recto y vuelta por la cabecera) y termina al salir del último.
    """
    ids = list(range(len(fm.aisles))) if aisles is None else aisles
    if not ids:
        return [(0.0, 0.0)]
    a0 = fm.aisles[ids[0]]
    at_south = True
    raw: list[Pt] = []
    cur: Pt | None = None
    for ai in ids:
        a = fm.aisles[ai]
        enter_z = fm.head_s if at_south else fm.head_n
        exit_z = fm.head_n if at_south else fm.head_s
        if cur is not None:
            raw += fm.route(cur, (a.x, enter_z))[:-1]
        raw += [(a.x, enter_z), (a.x, exit_z)]
        cur = (a.x, exit_z)
        at_south = not at_south
    ox, oz = a0.x, fm.head_s
    rel = [((z - oz) * p.escala, (x - ox) * p.escala) for x, z in raw]  # (adelante = +z, izquierda = +x)
    rel = _simplify(rel)
    if p.largo_max_m > 0:
        out = [rel[0]]
        left = p.largo_max_m
        for q in rel[1:]:
            d = math.hypot(q[0] - out[-1][0], q[1] - out[-1][1])
            if d >= left:
                f = left / d
                out.append((out[-1][0] + (q[0] - out[-1][0]) * f, out[-1][1] + (q[1] - out[-1][1]) * f))
                break
            out.append(q)
            left -= d
        rel = _simplify(out)
    return rel


def length(pts: list[Pt]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def rel_to_scene(rel: list[Pt], x0: float, z0: float, heading: float) -> list[Pt]:
    """(adelante, izquierda) → escena (x, z); mismo mapeo que web/src/robot/twin.ts."""
    sh, ch = math.sin(heading), math.cos(heading)
    return [(x0 + f * sh + l * ch, z0 + f * ch - l * sh) for f, l in rel]


def rel_to_odom(rel: list[Pt], ox: float, oy: float, yaw: float) -> list[Pt]:
    c, s = math.cos(yaw), math.sin(yaw)
    return [(ox + f * c - l * s, oy + f * s + l * c) for f, l in rel]


@dataclass
class _P:
    x: float
    y: float
    leg: int
    arc: bool = False
    spin: bool = False  # vértice donde hay que girar en el sitio (la vuelta no cabe con el radio mínimo)


def _wrap(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


def build_polyline(vertices: list[Pt], p: RutaParams) -> list[_P]:
    """Vértices → polilínea con arcos (filete) en las esquinas que caben y giro en el sitio en las que no."""
    n = len(vertices)
    out: list[_P] = [_P(vertices[0][0], vertices[0][1], 0)]
    for i in range(1, n - 1):
        a, b, c = vertices[i - 1], vertices[i], vertices[i + 1]
        l1, l2 = math.hypot(b[0] - a[0], b[1] - a[1]), math.hypot(c[0] - b[0], c[1] - b[1])
        d1 = ((b[0] - a[0]) / l1, (b[1] - a[1]) / l1)
        d2 = ((c[0] - b[0]) / l2, (c[1] - b[1]) / l2)
        th = abs(_wrap(math.atan2(d2[1], d2[0]) - math.atan2(d1[1], d1[0])))
        if th < math.radians(8):
            out.append(_P(b[0], b[1], i - 1))
            continue
        t = p.radio * math.tan(th / 2.0)
        if th > math.radians(150) or t > 0.5 * min(l1, l2):
            out.append(_P(b[0], b[1], i - 1, spin=True))  # no cabe: gira en el sitio, wz lento
            continue
        sgn = 1.0 if (d1[0] * d2[1] - d1[1] * d2[0]) > 0 else -1.0
        start = (b[0] - d1[0] * t, b[1] - d1[1] * t)
        cx, cy = start[0] - sgn * d1[1] * p.radio, start[1] + sgn * d1[0] * p.radio  # centro del arco
        a0 = math.atan2(start[1] - cy, start[0] - cx)
        steps = max(3, int(math.degrees(th) / 15))
        for k in range(steps + 1):
            ang = a0 + sgn * th * k / steps
            out.append(_P(cx + p.radio * math.cos(ang), cy + p.radio * math.sin(ang), i - 1 if k < steps / 2 else i, arc=True))
    out.append(_P(vertices[-1][0], vertices[-1][1], n - 2))
    return out


@dataclass
class Orden:
    v: float = 0.0
    wz: float = 0.0
    estado: str = "en_marcha"  # en_marcha | terminada | deriva
    tramo: int = 1
    restante_m: float = 0.0
    deriva_m: float = 0.0


@dataclass
class Seguidor:
    """Pure-pursuit sobre la polilínea: recto a ≤ v_recta, arcos a v_arco, giro en el sitio con wz ≤ wz_giro."""

    vertices: list[Pt]
    p: RutaParams
    pts: list[_P] = field(init=False)
    seg: int = field(default=0, init=False)
    spinning: bool = field(default=False, init=False)
    s_here: float = field(default=0.0, init=False)   # avance sobre la ruta (m reales), para el gemelo y los escaneos
    yaw_ruta: float = field(default=0.0, init=False)  # rumbo del tramo actual en el marco de la odometría

    def __post_init__(self) -> None:
        self.pts = build_polyline(self.vertices, self.p) if len(self.vertices) > 1 else [_P(*self.vertices[0], 0)] * 2
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + math.hypot(b.x - a.x, b.y - a.y))
        self.total = self.cum[-1]
        self.tramos = max(1, len(self.vertices) - 1)

    def _proj(self, i: int, x: float, y: float) -> tuple[float, float]:
        """(parámetro 0..1 sobre el segmento i, distancia al segmento)."""
        a, b = self.pts[i], self.pts[i + 1]
        dx, dy = b.x - a.x, b.y - a.y
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((x - a.x) * dx + (y - a.y) * dy) / l2))
        return t, math.hypot(x - (a.x + t * dx), y - (a.y + t * dy))

    def _point_at(self, s: float) -> tuple[float, float, int]:
        s = min(max(s, 0.0), self.total)
        for i in range(len(self.pts) - 1):
            if s <= self.cum[i + 1] + 1e-9:
                seg = self.cum[i + 1] - self.cum[i]
                f = 0.0 if seg < 1e-9 else (s - self.cum[i]) / seg
                a, b = self.pts[i], self.pts[i + 1]
                return a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, i
        return self.pts[-1].x, self.pts[-1].y, len(self.pts) - 2

    def step(self, x: float, y: float, yaw: float) -> Orden:
        p = self.p
        last = len(self.pts) - 2
        # avanzar de segmento cuando se pasó su final
        while self.seg < last:
            t, _ = self._proj(self.seg, x, y)
            nxt = self.pts[self.seg + 1]
            # a turn-in-place vertex counts as reached only when the robot is really on it (else it would hunt)
            if math.hypot(x - nxt.x, y - nxt.y) < 0.15 or (t >= 1.0 - 1e-9 and not nxt.spin):
                self.seg += 1
            else:
                break
        t, xt = self._proj(self.seg, x, y)
        s_here = self.cum[self.seg] + t * (self.cum[self.seg + 1] - self.cum[self.seg])
        self.s_here = s_here
        a, b = self.pts[self.seg], self.pts[self.seg + 1]
        if math.hypot(b.x - a.x, b.y - a.y) > 1e-9:
            self.yaw_ruta = math.atan2(b.y - a.y, b.x - a.x)
        rest = max(0.0, self.total - s_here)
        fin = self.pts[-1]
        d_fin = math.hypot(x - fin.x, y - fin.y)
        tramo = min(self.pts[min(self.seg + 1, len(self.pts) - 1)].leg + 1, self.tramos)
        o = Orden(tramo=tramo, restante_m=rest, deriva_m=xt)
        if xt > p.deriva_max_m:
            o.estado = "deriva"
            return o
        if self.seg >= last and d_fin < 0.10:
            o.estado, o.restante_m = "terminada", 0.0
            return o
        # objetivo: punto a `lookahead` por delante, sin pasar de un vértice de giro en el sitio ni del final
        s_t = min(s_here + p.lookahead_m, self.total)
        for i in range(self.seg + 1, len(self.pts)):
            if self.pts[i].spin and self.cum[i] < s_t:
                s_t = max(self.cum[i], s_here)
                break
        tx, ty, _ = self._point_at(s_t)
        if math.hypot(tx - x, ty - y) < 0.05:  # sobre el vértice de giro: mirar al tramo siguiente
            tx, ty, _ = self._point_at(min(s_t + 0.3, self.total))
        e = _wrap(math.atan2(ty - y, tx - x) - yaw)
        if self.spinning and abs(e) < 0.15:
            self.spinning = False
        elif not self.spinning and abs(e) > 0.6:
            self.spinning = True
        if self.spinning:
            o.wz = math.copysign(max(0.08, min(p.wz_giro, 1.2 * abs(e))), e)
            return o
        in_arc = self.pts[self.seg].arc or self.pts[min(self.seg + 1, len(self.pts) - 1)].arc
        v = p.v_arco if in_arc else p.v_recta
        v *= max(0.0, 1.0 - abs(e) / 0.6)
        stop_d = d_fin
        for i in range(self.seg + 1, len(self.pts)):
            if self.pts[i].spin:
                stop_d = min(stop_d, math.hypot(x - self.pts[i].x, y - self.pts[i].y))
                break
        v = min(v, 0.5 * stop_d + 0.05)
        v = min(v, p.v_recta)
        ld = max(0.2, math.hypot(tx - x, ty - y))
        o.v = max(0.0, v)
        o.wz = max(-p.wz_giro, min(p.wz_giro, o.v * 2.0 * math.sin(e) / ld + 0.6 * e))
        return o


def estaciones_scan(vertices: list[Pt], p: RutaParams) -> list[float]:
    """Distancias (m reales sobre la ruta) donde parar a mirar a los lados: `escaneos` paradas repartidas en cada
    pasillo (los tramos largos; las cabeceras cortas entre pasillos no cuentan)."""
    if p.escaneos <= 0 or len(vertices) < 2:
        return []
    legs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(vertices, vertices[1:])]
    largo = max(legs)
    out, acc = [], 0.0
    for L in legs:
        if L >= 0.6 * largo:
            out += [acc + L * (k + 1) / (p.escaneos + 1) for k in range(p.escaneos)]
        acc += L
    return out


def punto_en(pts: list[Pt], s: float) -> tuple[float, float, float]:
    """Punto a la distancia `s` de una polilínea de escena (x, z) y su rumbo de escena (adelante = (sin h, cos h))."""
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-9:
            continue
        h = math.atan2(b[0] - a[0], b[1] - a[1])
        if s <= acc + L:
            f = (s - acc) / L
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, h
        acc += L
    if len(pts) >= 2:
        a, b = pts[-2], pts[-1]
        return b[0], b[1], math.atan2(b[0] - a[0], b[1] - a[1])
    return (pts[0][0], pts[0][1], 0.0) if pts else (0.0, 0.0, 0.0)
