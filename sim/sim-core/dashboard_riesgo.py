"""Riesgo próximo (24-72 h) por cama y enfermedad, avisos preventivos por regla y cobertura del robot.

El motor solo calcula el riesgo del día en curso. Para 24-72 h se proyecta con el clima horario del
escenario (misma serie que usará el motor los días siguientes) y las mismas reglas de microclima del túnel,
SIN azar (ventilación siempre a tiempo, alero cerrado): por eso todo lo futuro se rotula ESTIMADO.
Las recomendaciones son reglas orientativas: validar con el agrónomo.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from risk import daily_risks

ENF = {"botrytis": "Botrytis", "anthracnose": "antracnosis", "rust": "roya"}
ACCIONES = {
    "botrytis": "ventilar y mantener los aleros cerrados si llueve, revisar flores y fruta antes de las 6 a. m., retirar tejido enfermo",
    "anthracnose": "evitar mojar el follaje, retirar fruta madura o dañada, revisar frutos antes de la próxima mojadura",
    "rust": "revisar el envés de las hojas, retirar hojas afectadas y vigilar la mojadura nocturna",
}
NOTA = "Recomendación orientativa por regla; validar con el agrónomo."


def nivel_de(v: float, medio: float, alto: float) -> str:
    return "alto" if v >= alto else "medio" if v >= medio else "bajo"


def _umbrales(sim: Any, d: str) -> tuple[float, float]:
    th = (sim.risk_cfg.get(d, {}) or {}).get("thresholds")
    if th:
        return float(th[0]), float(th[1])
    return {"anthracnose": (0.15, 0.5), "botrytis": (0.5, 0.7), "rust": (0.2, 0.5)}[d]


ORDEN = {"bajo": 0, "medio": 1, "alto": 2}


def evaluar(sim: Any, r: dict[str, float]) -> tuple[str, str]:
    """(nivel, enfermedad dominante): cada enfermedad se juzga con SUS umbrales (risk.yaml); manda la de mayor nivel
    y, a igual nivel, la más cercana a su umbral alto. Un solo par de umbrales escondería la antracnosis y la roya."""
    mejor, key = "botrytis", (-1, -1.0)
    for d, v in r.items():
        m, a = _umbrales(sim, d)
        k = (ORDEN[nivel_de(v, m, a)], v / a)
        if k > key:
            mejor, key = d, k
    return nivel_de(r[mejor], *_umbrales(sim, mejor)), mejor


def _dia(sim: Any, day_index: int) -> tuple[np.ndarray, np.ndarray]:
    """T interior (24,) y HR por cama (n_beds, 24) proyectadas para un día, sin azar."""
    day = sim.hourly.day_slice(day_index % max(sim.hourly.n_days, 1))
    T = np.array(day.temperature_2m or [15.0] * 24, dtype=float)
    RH = np.array(day.relative_humidity_2m or [70.0] * 24, dtype=float)
    h = np.arange(len(T))
    c = sim.climate
    if c.get("enabled", True):
        d0, d1 = c.get("day_hours", [6, 18])
        is_day = (h >= d0) & (h < d1)
        T_in = T + np.where(is_day, float(c.get("day_temp_offset_c", 0)), float(c.get("night_temp_offset_c", 0)))
        RH_in = RH + np.where(is_day, 0.0, float(c.get("night_rh_offset_pct", 0)))
        vent = c.get("ventilation", {})
        if vent.get("mode", "auto") == "auto":
            v0, v1 = vent.get("hours", [6, 18])
            on = (h >= v0) & (h < v1) & (RH_in > float(vent.get("rh_setpoint_pct", 85)))
            RH_in = RH_in - on * float(vent.get("rh_reduction_pct", 0))
            T_in = T_in - on * float(vent.get("temp_reduction_c", 0))
    else:
        T_in, RH_in = T, RH
    rh_bed = np.clip(RH_in[None, :] + sim._bed_gradient()[:, None], 0, 100)
    return T_in, rh_bed


def proyectar(sim: Any, cfg: dict[str, Any]) -> dict[str, Any]:
    rc = cfg["riesgo"]
    hr_alta = float(rc["hr_alta_pct"])
    thr = float(sim.weather_cfg.get("rh_wetness_threshold_pct", 90))
    lv = sim.weather_cfg.get("risk_levels", {"medium": 0.05, "high": 0.15})
    medio_c, alto_c = float(lv.get("medium", 0.05)), float(lv.get("high", 0.15))
    now_h = int(sim._hour())
    base = sim._day_index()
    n_days = 4
    Ts, RHs = zip(*[_dia(sim, base + k) for k in range(n_days)])
    T = np.concatenate(Ts)                    # (96,)
    RH = np.concatenate(RHs, axis=1)          # (n_beds, 96)
    wet = RH >= thr
    nb = sim.n_beds
    bpn = sim.map.bpn
    camas: list[dict[str, Any]] = []
    for b in range(nb):
        ahora_pd = {d: 0.0 for d in ENF}
        ventanas = []
        for hz in rc["ventanas_h"]:
            lo, hi = now_h + (hz - 24 if hz > 24 else 0), now_h + hz
            w = wet[b, lo:hi]
            wet_h = float(w.sum())
            t_wet = float(T[lo:hi][w].mean()) if wet_h > 0 else float(T[lo:hi].mean())
            r = daily_risks(wet_h, t_wet, float(T[lo:hi].mean()), sim.risk_cfg)
            nivel_v, dom = evaluar(sim, r)
            comb = max(r.values())
            noche = bool(w[: 24].size and any(((lo + k) % 24 >= 18 or (lo + k) % 24 < 6) for k in np.where(w)[0]))
            ventanas.append({
                "horas": f"{hz - 24 if hz > 24 else 0}-{hz} h", "riesgo": round(comb, 3), "nivel": nivel_v,
                "enfermedad": dom, "enfermedad_nombre": ENF[dom], "nivel_enfermedad": nivel_v,
                "por_enfermedad": {k: round(v, 3) for k, v in r.items()},
                "horas_mojadas": int(wet_h), "horas_hr_alta": int((RH[b, lo:hi] >= hr_alta).sum()),
                "temp_mojada_c": round(t_wet, 1), "noche": noche, "estimado": True,
            })
        cur = float(sim.bed_risks[b])
        wet_today = sim.wet_bh[b]
        wh = float(wet_today.sum())
        r0 = daily_risks(wh, float(sim.T_in[wet_today].mean()) if wh > 0 else float(sim.T_in.mean()), float(sim.T_in.mean()), sim.risk_cfg)
        nivel0, _ = evaluar(sim, r0)
        camas.append({
            "bed": b, "nave": b // bpn + 1, "cama": b % bpn + 1,
            "ahora": {"riesgo": round(cur, 3), "nivel": nivel0, "estimado": False},
            "ventanas": ventanas,
            "max_riesgo": round(max([cur] + [v["riesgo"] for v in ventanas]), 3),
        })
        camas[-1]["nivel"] = max([nivel0] + [v["nivel"] for v in ventanas], key=lambda n: ORDEN[n])
    return {"camas": camas, "niveles": {"medio": medio_c, "alto": alto_c},
            "umbrales": {d: list(_umbrales(sim, d)) for d in ENF}, "hora_actual": now_h,
            "pd_ahora": {d: round(float(sim.risks.get(d, 0.0)), 3) for d in ENF}}


def avisos(proy: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Avisos preventivos por (nave, enfermedad, ventana): camas medio/alto, orientativos."""
    grupos: dict[tuple[int, str, str], dict[str, Any]] = {}
    for c in proy["camas"]:
        for v in c["ventanas"]:
            if v["nivel"] == "bajo":
                continue
            k = (c["nave"], v["enfermedad"], v["horas"])
            g = grupos.setdefault(k, {"camas": [], "nivel": "medio", "noche": False, "riesgo": 0.0, "mojadas": 0})
            g["camas"].append(c["cama"])
            g["nivel"] = "alto" if v["nivel"] == "alto" or g["nivel"] == "alto" else "medio"
            g["noche"] = g["noche"] or v["noche"]
            g["riesgo"] = max(g["riesgo"], v["riesgo"])
            g["mojadas"] = max(g["mojadas"], v["horas_mojadas"])
    out = []
    for (nave, d, hz), g in grupos.items():
        camas = sorted(g["camas"])
        donde = f"N{nave}" + (f" (camas {', '.join(f'C{c}' for c in camas)})" if len(camas) <= 4 else f" ({len(camas)} camas)")
        cuando = "esta noche" if hz.startswith("0-") and g["noche"] else f"en las próximas {hz.split('-')[1]}"
        out.append({
            "id": f"N{nave}-{d}-{hz}", "nivel": g["nivel"], "nave": nave, "camas": camas, "enfermedad": d,
            "enfermedad_nombre": ENF[d], "ventana": hz, "riesgo": g["riesgo"], "horas_mojadas": g["mojadas"],
            "texto": f"Riesgo {g['nivel']} de {ENF[d]} en {donde} {cuando}: {ACCIONES[d]}.",
            "nota": NOTA, "estimado": True,
        })
    out.sort(key=lambda a: (a["nivel"] != "alto", a["ventana"], -a["riesgo"]))
    return out[: int(cfg["riesgo"]["max_avisos"])]


def cobertura(sim: Any, cfg: dict[str, Any]) -> dict[str, Any]:
    ciego = float(cfg["cobertura"]["ciego_h"])
    now_h = sim.t / 3600.0
    bpn = sim.map.bpn
    camas = []
    for b in range(sim.n_beds):
        t = sim.bed_last_t.get(b)
        horas = None if t is None else round(now_h - t / 3600.0, 1)
        camas.append({
            "nave": b // bpn + 1, "cama": b % bpn + 1,
            "ultima_dia": None if t is None else int(t // 86400),
            "ultima_hora": None if t is None else f"{int((t % 86400) // 3600):02d}:{int((t % 3600) // 60):02d}",
            "horas_sin_revisar": horas,
            "ciego": (now_h > ciego) if horas is None else horas > ciego,
        })
    return {"ciego_h": ciego, "camas": camas, "puntos_ciegos": [c for c in camas if c["ciego"]],
            "ahora_h": round(now_h, 1), "nota": "Horas del escenario simulado."}
