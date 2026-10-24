"""Índices de riesgo de enfermedad (0-1) portados de la capa verificada del equipo.

Origen: BerryGoodIdea_handoff/datos/riesgo/risk.py (136 pruebas). Aquí se copian SOLO las funciones que
usa la simulación, para que sim-core sea autocontenido (no se importa nada de datos/). Los casos de libro
de esas pruebas se repiten en tests/test_risk.py.

Modelos (entrada: LWD = horas de hoja mojada, T = °C media de las horas mojadas):

- Antracnosis (Colletotrichum): envolvente = máx(a, b), orientada a la sensibilidad.
    a) Wilson, Madden y Ellis 1990, Phytopathology 80:111-116 (fruto de fresa). PUBLICADO, coeficientes de
       NC State IPM; es la ecuación del Strawberry Advisory System y del Blueberry Advisory System
       (UF/IFAS; Gama et al. 2022, EDIS PP366; validada en arándano por Gama et al. 2021, Plant Dis.
       105:1806). Recorte frío: bajo el mínimo local del polinomio (~9,33 °C) se usa la pendiente de ese
       punto (implementación del equipo; reproduce la curva plana de NCSU entre 0 y 10 °C).
    b) APROXIMACIÓN calibrada en arándano con Gillett y Schilder 2009, Acta Hortic. 810:355-360: misma forma
       logística, con la LWD a la que el índice vale 0,5 (W50) en el punto medio de cada rango publicado.
  NO se usa Miles et al. 2013 (Plant Pathol. 62:1238): sus coeficientes nunca se obtuvieron (artículo cerrado).
- Botrytis: Bulger, Ellis y Madden 1987, Phytopathology 77:1225-1230. PUBLICADO (coeficientes de NC State
  IPM). Modela infección de FLORES de fresa: proxy para arándano. Rango experimental 5-30 °C y <= 32 h
  (NO VERIFICADO directamente: APS respondió 403); fuera de ese rango es extrapolación.
- Roya (Thekopsora minima): APROXIMACIÓN con el modelo genérico de infección (GIM) de Magarey, Sutton y
  Thayer 2005 (Phytopathology 95:92-100) y temperaturas cardinales con Pfister et al. 2004 (rododendro);
  Tmin, Tmax y LWDmin son SUPUESTOS. Se usa como regla de vigilancia, no como modelo validado.

Sin mojadura (LWD <= 0) todos los índices valen 0. Los coeficientes viven en config/risk.yaml con su cita;
los valores por defecto de este módulo son los publicados y las pruebas fijan que coincidan.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

DISEASE_KEYS = ("anthracnose", "botrytis", "rust")

# --- valores publicados por defecto (los mismos que datos/riesgo/risk.py) --------------------------------
# Wilson et al. 1990 (NC State IPM, imagen "anthracnose fruit rot FLSAS formula"):
#   f = c0 + c1*LWD + c2*LWD*T + c3*LWD*T^2 + c4*LWD*T^3
WILSON_1990 = {"c0": -3.7, "c1": 0.33, "c2": -0.069, "c3": 0.005, "c4": -9.3e-5}
# Gillett y Schilder 2009 (resumen abierto): "aumento considerable" tras 36-48 h a 10 °C, 24 h a 15 °C,
# 12-18 h a 20-25 °C y 18-24 h a 30 °C -> W50 = punto medio (APROXIMACIÓN). g = 0 a 5 y 35 °C
# (Miles et al. 2013, resumen Crossref: crecimiento escaso o nulo a 5 y 35 °C).
GILLETT_SCHILDER_2009_W50 = ((10.0, 42.0), (15.0, 24.0), (20.0, 15.0), (25.0, 15.0), (30.0, 21.0))
GILLETT_SCHILDER_ZERO_T = (5.0, 35.0)
# Bulger et al. 1987 (NC State IPM, imagen "FLSAS Botrytis formula"):
#   f = c0 + c_lwd*LWD + c_lwd_t*LWD*T + c_lwd_t3*LWD*T^3
BULGER_1987 = {"c0": -4.268, "c_lwd": -0.0901, "c_lwd_t": 0.0294, "c_lwd_t3": -2.35e-5}
BULGER_RANGE_T = (5.0, 30.0)   # NO VERIFICADO directamente
BULGER_LWD_MAX_H = 32.0        # NO VERIFICADO directamente
# GIM para roya: Topt 21,5 °C (Pfister 2004), Tmin 8 y Tmax 32 °C (SUPUESTO), LWDmin 8 h (SUPUESTO),
# LWDmax 48 h (EPPO resumido por DEFRA 2021).
GIM_RUST = {"t_min_c": 8.0, "t_opt_c": 21.5, "t_max_c": 32.0, "lwd_min_h": 8.0, "lwd_max_h": 48.0}
# Umbrales (medio, alto) publicados: NCSU FLSAS y MacKenzie y Peres 2012a/b; roya = SUPUESTO.
DEFAULT_THRESHOLDS = {"anthracnose": (0.15, 0.50), "botrytis": (0.50, 0.70), "rust": (0.20, 0.50)}


def _is_nan(x: Any) -> bool:
    if x is None:
        return True
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return True


def _logistic(z: float) -> float:
    """e^z / (1 + e^z), numéricamente estable."""
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _no_wetness(lwd: Any, t: Any) -> bool:
    return lwd is None or _is_nan(lwd) or float(lwd) <= 0 or _is_nan(t)


# ---------------------------------------------------------------------------------------------------------
# Antracnosis
# ---------------------------------------------------------------------------------------------------------
def _wilson_slope(t: float, c: dict[str, float]) -> float:
    """Pendiente del logit respecto a LWD: g(T) = c1 + c2*T + c3*T^2 + c4*T^3."""
    return float(c["c1"]) + float(c["c2"]) * t + float(c["c3"]) * t**2 + float(c["c4"]) * t**3


def wilson_critical_temps(coeffs: dict[str, float] | None = None) -> tuple[float, float]:
    """(T del mínimo local de g, T del máximo de g). Con los coeficientes publicados: ~9,33 y ~26,5 °C."""
    c = coeffs or WILSON_1990
    a, b, cc = 3 * float(c["c4"]), 2 * float(c["c3"]), float(c["c2"])
    d = math.sqrt(b * b - 4 * a * cc)
    r1, r2 = (-b + d) / (2 * a), (-b - d) / (2 * a)
    return min(r1, r2), max(r1, r2)


def wilson1990_anthracnose(lwd: float, temp_c: float, coeffs: dict[str, float] | None = None) -> float:
    """Índice 0-1 de Wilson et al. 1990 con recorte frío bajo el mínimo local de g (implementación del equipo)."""
    if _no_wetness(lwd, temp_c):
        return 0.0
    c = coeffs or WILSON_1990
    t_gmin, _ = wilson_critical_temps(c)
    t = max(float(temp_c), t_gmin)
    return _logistic(float(c["c0"]) + float(lwd) * _wilson_slope(t, c))


def _interp(x: float, table: Sequence[tuple[float, float]]) -> float:
    """Interpolación lineal; fuera de la tabla devuelve el valor del extremo."""
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table[:-1], table[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return 0.0


def gillett_schilder_slope_table(
    anchors: Sequence[Sequence[float]] | None = None,
    zero_t: Sequence[float] | None = None,
    c0: float = WILSON_1990["c0"],
) -> list[tuple[float, float]]:
    """Tabla (T, g) con g = -c0 / W50 en cada ancla y g = 0 en los extremos térmicos."""
    anc = anchors or GILLETT_SCHILDER_2009_W50
    z = zero_t or GILLETT_SCHILDER_ZERO_T
    return [(float(z[0]), 0.0)] + [(float(t), -float(c0) / float(w)) for t, w in anc] + [(float(z[1]), 0.0)]


def gillett_schilder2009_approx(lwd: float, temp_c: float, cfg: dict[str, Any] | None = None) -> float:
    """APROXIMACIÓN en arándano: logística(c0 + LWD * g(T)), g interpolada desde los W50 de Gillett y Schilder."""
    if _no_wetness(lwd, temp_c):
        return 0.0
    cfg = cfg or {}
    c0 = float(cfg.get("intercept", WILSON_1990["c0"]))
    table = gillett_schilder_slope_table(cfg.get("w50_anchors"), cfg.get("zero_slope_temps_c"), c0)
    return _logistic(c0 + float(lwd) * _interp(float(temp_c), table))


def anthracnose_index(lwd: float, temp_c: float, cfg: dict[str, Any] | None = None) -> float:
    """model: envelope (máx de ambos, por defecto) | wilson1990 | gillett_schilder2009."""
    cfg = cfg or {}
    model = str(cfg.get("model", "envelope"))
    a = wilson1990_anthracnose(lwd, temp_c, cfg.get("wilson1990"))
    if model == "wilson1990":
        return a
    b = gillett_schilder2009_approx(lwd, temp_c, cfg.get("gillett_schilder2009"))
    if model == "gillett_schilder2009":
        return b
    if model == "envelope":
        return max(a, b)
    raise ValueError(f"modelo de antracnosis desconocido: {model}")


# ---------------------------------------------------------------------------------------------------------
# Botrytis
# ---------------------------------------------------------------------------------------------------------
def bulger1987_logit(wetness_h: float, temp_c: float, coeffs: dict[str, float] | None = None) -> float:
    """Índice 0-1 de Bulger et al. 1987 (flor de fresa, proxy). Sin mojadura -> 0."""
    if _no_wetness(wetness_h, temp_c):
        return 0.0
    c = coeffs or BULGER_1987
    w, t = float(wetness_h), float(temp_c)
    z = float(c["c0"]) + float(c["c_lwd"]) * w + float(c["c_lwd_t"]) * w * t + float(c["c_lwd_t3"]) * w * t**3
    return _logistic(z)


def bulger_optimum_temp(coeffs: dict[str, float] | None = None) -> float:
    """T óptima analítica sqrt(c_lwd_t / (-3 c_lwd_t3)); con los coeficientes publicados ~20,4 °C (NCSU: 20,5)."""
    c = coeffs or BULGER_1987
    b3 = float(c["c_lwd_t3"])
    if b3 >= 0:
        return float("nan")
    return math.sqrt(float(c["c_lwd_t"]) / (-3.0 * b3))


def bulger_out_of_range(wetness_h: float, temp_c: float, cfg: dict[str, Any] | None = None) -> bool:
    """True si el evento sale del rango experimental de Bulger 1987 (extrapolación)."""
    cfg = cfg or {}
    t_lo, t_hi = cfg.get("valid_temp_c", BULGER_RANGE_T)
    lwd_max = float(cfg.get("valid_max_wetness_h", BULGER_LWD_MAX_H))
    if _is_nan(temp_c):
        return True
    return bool(float(wetness_h) > lwd_max or not (float(t_lo) <= float(temp_c) <= float(t_hi)))


# ---------------------------------------------------------------------------------------------------------
# Roya (GIM)
# ---------------------------------------------------------------------------------------------------------
def gim_temperature_factor(temp_c: float, p: dict[str, float] | None = None) -> float:
    """f_T del GIM (Magarey et al. 2005, forma publicada por NCSU); 0 fuera de [Tmin, Tmax]."""
    p = p or GIM_RUST
    t_min, t_opt, t_max = float(p["t_min_c"]), float(p["t_opt_c"]), float(p["t_max_c"])
    if _is_nan(temp_c) or temp_c < t_min or temp_c > t_max:
        return 0.0
    a = math.log(2.0) / math.log((t_max - t_min) / (t_opt - t_min))
    x, xo = float(temp_c) - t_min, t_opt - t_min
    val = (2.0 * x**a * xo**a - x ** (2 * a)) / xo ** (2 * a)
    return max(0.0, min(1.0, val))


def gim_cycles(lwd: float, temp_c: float, p: dict[str, float] | None = None) -> float:
    """I = LWD * f_T / LWDmin; I = 0 si LWDmin / f_T > LWDmax (lectura del equipo, NO VERIFICADO)."""
    p = p or GIM_RUST
    if lwd is None or _is_nan(lwd) or lwd <= 0:
        return 0.0
    ft = gim_temperature_factor(temp_c, p)
    if ft <= 0 or float(p["lwd_min_h"]) / ft > float(p["lwd_max_h"]):
        return 0.0
    return float(lwd) * ft / float(p["lwd_min_h"])


def gim_index_from_cycles(i: float) -> float:
    """0,15^(3,5 * 0,15^(0,75 I)): I = 1 -> ~0,20; I = 2 -> ~0,68 (nota y curva de NCSU)."""
    if i <= 0:
        return 0.0
    return 0.15 ** (3.5 * 0.15 ** (0.75 * i))


def rust_gim_index(lwd: float, temp_c: float, p: dict[str, float] | None = None) -> float:
    """APROXIMACIÓN para roya del arándano (regla de vigilancia). Sin mojadura -> 0."""
    return gim_index_from_cycles(gim_cycles(lwd, temp_c, p))


# ---------------------------------------------------------------------------------------------------------
# Interfaz que usan engine.py y batch.py (nombres y firmas estables)
# ---------------------------------------------------------------------------------------------------------
def daily_risks(
    wetness_h: float,
    mean_temp_during_wet_c: float,
    mean_temp_c: float,
    risk_cfg: dict[str, Any],
) -> dict[str, float]:
    """Índice 0-1 por enfermedad para un periodo de mojadura (LWD, T media de las horas mojadas).

    mean_temp_c se conserva por compatibilidad: con LWD = 0 todos los índices valen 0, así que no se usa.
    """
    del mean_temp_c  # los tres modelos usan solo la T de las horas mojadas (NCSU)
    lwd, t = float(wetness_h), float(mean_temp_during_wet_c)
    anth_cfg = risk_cfg.get("anthracnose", {}) or {}
    bot_cfg = risk_cfg.get("botrytis", {}) or {}
    rust_cfg = risk_cfg.get("rust", {}) or {}
    return {
        "anthracnose": anthracnose_index(lwd, t, anth_cfg),
        "botrytis": bulger1987_logit(lwd, t, bot_cfg.get("coefficients")),
        "rust": rust_gim_index(lwd, t, rust_cfg.get("gim")),
    }


def combined_risk(risks: dict[str, float], how: str = "max") -> float:
    """Presión combinada sobre las tres enfermedades (máx por defecto, orientada a la sensibilidad)."""
    vals = [float(v) for k, v in risks.items() if k in DISEASE_KEYS]
    if not vals:
        return 0.0
    if how == "mean":
        return float(sum(vals) / len(vals))
    return float(max(vals))


def classify(index: float, disease: str, risk_cfg: dict[str, Any] | None = None) -> str:
    """bajo / medio / alto con los umbrales (medio, alto) de risk.yaml o los publicados por defecto."""
    thr = DEFAULT_THRESHOLDS[disease]
    if risk_cfg:
        cfg_thr = (risk_cfg.get(disease, {}) or {}).get("thresholds")
        if cfg_thr:
            thr = (float(cfg_thr[0]), float(cfg_thr[1]))
    if _is_nan(index) or index < thr[0]:
        return "bajo"
    return "medio" if index < thr[1] else "alto"
