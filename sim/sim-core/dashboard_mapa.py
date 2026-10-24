"""Vista cenital del bloque: geometría en metros, campos T/HR interpolados y detecciones ubicadas.

Ejes: x = ancho del bloque (naves de oeste a este), y = largo de las camas (+y = norte), en metros, con
las mismas coordenadas del motor (x, z). Todo es de solo lectura sobre la sesión.
Los campos de T y HR NO son medidos en toda la superficie: se interpolan (kernel gaussiano suavizado hacia
la media) a partir de las lecturas puntuales disponibles y se marca qué celdas contienen una lectura.
"""
from __future__ import annotations

from typing import Any

import numpy as np

SIGMA_M = 6.0          # ancho del kernel gaussiano
W0 = 0.05              # peso de la media global: lejos de toda lectura el valor vuelve a la media
CELDA_MEDIDA_M = 0.75  # una celda a menos de esto de una lectura se marca como medida


def geometria(sim: Any) -> dict[str, Any]:
    m = sim.map
    lay = m.layout()
    x0, x1 = m.x0, m.x0 + m.width
    y0, y1 = m.bed_z0 - m.main_path_w, m.bed_z1 + m.north_w
    camas = []
    for b in range(m.n_beds):
        camas.append({"bed": b, "nave": b // m.bpn + 1, "cama": b % m.bpn + 1, "x": round(m.bed_centers_x[b], 3),
                      "ancho": m.bed_w, "y0": round(m.bed_z0, 3), "y1": round(m.bed_z1, 3)})
    return {
        "unidad": "m", "norte": "+y",
        "bounds": {"x0": round(x0, 3), "x1": round(x1, 3), "y0": round(y0, 3), "y1": round(y1, 3)},
        "naves": [{"nave": k + 1, "x0": round(m.nave_x0[k], 3), "x1": round(m.nave_x0[k] + m.nave_w, 3)} for k in range(m.n_naves)],
        "camas": camas,
        "plantas": {"n": m.n_plants, "espaciado": m.spacing, "y_primera": round(m.z0, 3)},
        "pasillos": [{"x": round(a["x"], 3), "nave": a["nave"] + 1, "y0": round(m.bed_z0, 3), "y1": round(m.bed_z1, 3)} for a in lay["aisles"]],
        # cabecera sur (camino de acceso de lado a lado) y camino central entre el Bloque 1 y el Bloque 2
        "camino_cabecera": {"x0": round(x0, 3), "x1": round(x1, 3), "y0": round(m.bed_z0 - m.main_path_w, 3), "y1": round(m.bed_z0, 3)},
        "camino_central": ({"x0": round(m.central_x()[0], 3), "x1": round(m.central_x()[1], 3), "y0": round(m.bed_z0, 3), "y1": round(m.bed_z1 + m.north_w, 3)}
                           if m.n_blocks > 1 else None),
        "bloques": [{"id": b["id"], "naves": b["naves"], "x0": round(b["x0"], 3), "x1": round(b["x1"], 3),
                     "inicio": [round(v, 3) for v in b["start"]], "inicio_txt": b["start_label"]} for b in lay["blocks"]],
        "bloque_activo": int(getattr(sim, "bloque", 1)),
        "cabecera_norte": {"y0": round(m.bed_z1, 3), "y1": round(m.bed_z1 + m.north_w, 3)},
        "base": {"x": round(m.base[0], 2), "y": round(m.base[1], 2)},
    }


def posicion_planta(sim: Any, bed: int, planta: int | None) -> tuple[float, float]:
    m = sim.map
    p = 0 if planta is None else int(planta) - 1
    return float(m.bed_centers_x[bed]), float(m.plant_z(min(max(p, 0), m.n_plants - 1)))


def _t_h(rec: dict[str, Any]) -> float:
    try:
        h, mi = str(rec.get("clock")).split(":")
        return float(rec.get("day", 0)) * 24 + int(h) + int(mi) / 60.0
    except ValueError:
        return float(rec.get("day", 0)) * 24


def lecturas(sim: Any, horas: float, ahora_h: float) -> list[dict[str, Any]]:
    """Lecturas puntuales de T/HR: sondas del robot e incidencias (últimas `horas`) + red de sensores del bloque."""
    out: list[dict[str, Any]] = []
    for r in sim.records:
        if r.get("temp_c") is None or r.get("rh_pct") is None:
            continue
        t = _t_h(r)
        if t < ahora_h - horas:
            continue
        if r.get("kind") == "incidencia" and r.get("planta") and r.get("cama_global"):
            x, y = posicion_planta(sim, int(r["cama_global"]) - 1, r["planta"])
            tipo = "incidencia"
        else:
            x, y, tipo = float(r.get("x", 0.0)), float(r.get("z", 0.0)), "sonda_robot"
        out.append({"x": round(x, 2), "y": round(y, 2), "t": float(r["temp_c"]), "hr": float(r["rh_pct"]), "tipo": tipo, "t_h": round(t, 2)})
    w = sim._climate_now()
    for b in range(sim.n_beds):
        out.append({"x": round(float(sim.map.bed_centers_x[b]), 2), "y": 0.0, "t": float(w["T_in"]), "hr": float(w["RH_bed"][b]),
                    "tipo": "sensor_bloque", "t_h": round(ahora_h, 2)})
    return out


def rejilla(puntos: list[tuple[float, float, float]], bounds: dict[str, float], celda: float = 1.0,
            sigma: float = SIGMA_M) -> dict[str, Any]:
    """Campo interpolado en una rejilla regular. Devuelve valores por fila (y creciente), índices de celdas medidas y rango."""
    nx = max(1, int(np.ceil((bounds["x1"] - bounds["x0"]) / celda)))
    ny = max(1, int(np.ceil((bounds["y1"] - bounds["y0"]) / celda)))
    cx = bounds["x0"] + (np.arange(nx) + 0.5) * celda
    cy = bounds["y0"] + (np.arange(ny) + 0.5) * celda
    X, Y = np.meshgrid(cx, cy)               # (ny, nx)
    base = {"nx": nx, "ny": ny, "celda": celda, "x0": bounds["x0"], "y0": bounds["y0"], "n_lecturas": len(puntos)}
    if not puntos:
        return {**base, "valores": [], "medido": [], "min": None, "max": None}
    P = np.array(puntos, dtype=float)
    px, py, v = P[:, 0], P[:, 1], P[:, 2]
    mean = float(v.mean())
    num = np.zeros(X.size)
    den = np.zeros(X.size)
    fx, fy = X.ravel(), Y.ravel()
    for i in range(0, len(px), 200):          # por lotes: memoria acotada con muchas lecturas
        d2 = (fx[:, None] - px[None, i:i + 200]) ** 2 + (fy[:, None] - py[None, i:i + 200]) ** 2
        w = np.exp(-d2 / (2 * sigma * sigma))
        num += w @ v[i:i + 200]
        den += w.sum(axis=1)
    val = (num + W0 * mean) / (den + W0)
    medido = np.zeros(X.size, dtype=bool)
    for x, y in zip(px, py):
        medido |= (np.abs(fx - x) <= max(celda, CELDA_MEDIDA_M)) & (np.abs(fy - y) <= max(celda, CELDA_MEDIDA_M))
    return {**base, "valores": [round(float(a), 2) for a in val], "medido": [int(i) for i in np.where(medido)[0]],
            "min": round(float(val.min()), 2), "max": round(float(val.max()), 2)}
