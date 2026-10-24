"""
risk.py -- Modelos de riesgo ambiental de enfermedades del arandano (Sabana Hack, reto "Berry Good Idea").

Que hace
--------
1. Detecta periodos de mojadura foliar a partir de datos HORARIOS (proxy: HR >= umbral, lluvia,
   probabilidad de mojadura LWP de Open-Meteo opcional, o riego por aspersion), permitiendo
   interrupciones secas cortas configurables.
2. Calcula, por periodo, la duracion de mojadura (LWD, horas mojadas) y la temperatura media
   SOLO de las horas mojadas.
3. Calcula un indice de infeccion 0-1 por enfermedad con la ecuacion publicada cuando existe:
     - Antracnosis (Colletotrichum): Wilson, Madden & Ellis 1990 (fresa), que es la ecuacion del
       Strawberry Advisory System y del Blueberry Advisory System (UF/IFAS, validado en arandano por
       Gama et al. 2021). Se complementa con una APROXIMACION calibrada en arandano (Gillett &
       Schilder 2009) y se usa la envolvente (maximo) para favorecer la sensibilidad.
     - Botrytis: Bulger, Ellis & Madden 1987 (flores de fresa, proxy).
     - Roya (Thekopsora minima): APROXIMACION con el modelo generico de Magarey et al. 2005 (GIM)
       y temperaturas cardinales de Pfister et al. 2004.
     - Oidio: indice de Gubler-Thomas (UC Davis, VID). NO VALIDADO en arandano.
4. Clasifica bajo/medio/alto con umbrales documentados y aplica un multiplicador de fenologia
   (SUPUESTO).

Cada coeficiente lleva su cita en el comentario. Ver riesgo/README.md para formulas, fuentes y limites.
Las etiquetas usadas en este archivo:
    PUBLICADO      coeficiente copiado de la fuente indicada (abierta en esta sesion).
    APROXIMACION   regla o curva construida por nosotros a partir de datos publicados.
    SUPUESTO       valor elegido por el equipo sin fuente directa.
    NO VERIFICADO  dato visto solo en un resumen secundario (no se pudo abrir la fuente original).

Dependencias: solo libreria estandar en el nucleo. pandas es opcional (lectura de CSV / DataFrame).
Compatible con Python 3.9+ (se ejecuta con el venv del proyecto: .venv/bin/python -I).

Uso rapido
----------
    from risk import horas_desde_csv, resumen_diario, ConfigMojadura
    horas = horas_desde_csv("clima/derivados/hoja_mojada_horaria_chia.csv")
    dias = resumen_diario(horas, ConfigMojadura(umbral_hr=90), etapa="floracion")

CLI
---
    python -I riesgo/risk.py evaluar --csv clima/derivados/hoja_mojada_horaria_chia.csv --punto chia
    python -I riesgo/risk.py actual                # riesgo 72 h con el ultimo pronostico en cache
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_DATOS = os.path.dirname(AQUI)

ENFERMEDADES = ("antracnosis", "botrytis", "roya", "oidio")
ETAPAS = ("vegetativo", "floracion", "fruto_verde", "maduracion")
CLASES = ("bajo", "medio", "alto")


def _es_nan(x) -> bool:
    if x is None:
        return True
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return True


def _logistica(z: float) -> float:
    # e^z / (1 + e^z), estable numericamente
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


# =====================================================================================
# 1. Deteccion de periodos de mojadura
# =====================================================================================

@dataclass
class ConfigMojadura:
    """Criterio de "hora mojada" y de union de horas en un periodo.

    umbral_hr: HR (%) a partir de la cual la hora se considera mojada. 90 % es el proxy simple mas
        usado (SUPUESTO por defecto). Sentelhas et al. 2008 (Agric. For. Meteorol. 148:392-400)
        concluyen que el umbral de HR debe calibrarse por sitio (resumen secundario, NO VERIFICADO).
    umbral_lluvia_mm: lluvia horaria (mm) que marca la hora como mojada. 0.5 mm/h por defecto, segun la
        comparacion IDEAM vs Open-Meteo 2025 del equipo (reportes/clima-open-meteo.md): Open-Meteo marca
        1.7-4.5 veces mas horas con lluvia que el pluviometro, y con "lluvia > 0" el 55-74 % de las horas
        del anio saldrian mojadas. Escenario central del equipo de clima: HR >= 90 o lluvia >= 0.5;
        escenario de alerta (sensibilidad ~0.9 frente a HR_IDEAM >= 90): HR >= 85 o lluvia >= 0.5.
    usar_lwp / umbral_lwp: usar la probabilidad de mojadura foliar de Open-Meteo (producto de modelo,
        no observacion) como criterio adicional.
    max_interrupcion_h: maximo de horas secas seguidas que NO cortan el periodo. NCSU IPM: "an
        infection risk period is terminated by a minimum dry period of four hours" -> 3 h secas se
        toleran, 4 h cortan (PUBLICADO, pagina NCSU citada en README).
    min_horas_mojadas: periodos con menos horas mojadas se descartan.
    """
    umbral_hr: float = 90.0
    umbral_lluvia_mm: float = 0.5
    usar_hr: bool = True
    usar_lwp: bool = False
    umbral_lwp: float = 50.0
    max_interrupcion_h: int = 3
    min_horas_mojadas: int = 1


@dataclass
class Hora:
    """Un registro horario. time = inicio de la hora (hora local)."""
    time: datetime
    T: float
    HR: float
    lluvia: float = 0.0
    lwp: Optional[float] = None
    riego: bool = False


@dataclass
class PeriodoMojadura:
    inicio: datetime
    fin: datetime                       # ultima hora mojada
    horas_mojadas: int                  # LWD que entra a los modelos
    duracion_total_h: int               # de inicio a fin, incluidas interrupciones
    t_media: float                      # media de T solo en horas mojadas (NCSU)
    t_min: float
    t_max: float
    hr_media: float
    lluvia_mm: float
    n_interrupciones: int
    abierto: bool = False               # la serie termino antes de ver un corte seco completo
    detalle: List[Tuple[datetime, float]] = field(default_factory=list, repr=False)


def hora_mojada(h: Hora, cfg: ConfigMojadura) -> bool:
    if h.riego:
        return True
    if cfg.usar_hr and not _es_nan(h.HR) and float(h.HR) >= cfg.umbral_hr:
        return True
    if not _es_nan(h.lluvia) and float(h.lluvia) >= cfg.umbral_lluvia_mm:
        return True
    if cfg.usar_lwp and not _es_nan(h.lwp) and float(h.lwp) >= cfg.umbral_lwp:
        return True
    return False


def _horas_entre(a: datetime, b: datetime) -> int:
    return int(round((b - a).total_seconds() / 3600.0))


def _cerrar(actual: dict, ultimo_t: datetime, cfg: ConfigMojadura) -> Optional[PeriodoMojadura]:
    det = actual["detalle"]
    if len(det) < cfg.min_horas_mojadas:
        return None
    ts = [t for _, t in det if not _es_nan(t)]
    hrs = [x for x in actual["hr"] if not _es_nan(x)]
    inicio, fin = det[0][0], det[-1][0]
    secas_al_final = _horas_entre(fin, ultimo_t)
    return PeriodoMojadura(
        inicio=inicio, fin=fin, horas_mojadas=len(det),
        duracion_total_h=_horas_entre(inicio, fin) + 1,
        t_media=(sum(ts) / len(ts)) if ts else float("nan"),
        t_min=min(ts) if ts else float("nan"), t_max=max(ts) if ts else float("nan"),
        hr_media=(sum(hrs) / len(hrs)) if hrs else float("nan"),
        lluvia_mm=actual["lluvia"], n_interrupciones=actual["interrupciones"],
        abierto=secas_al_final <= cfg.max_interrupcion_h,
        detalle=list(det),
    )


def detectar_periodos(horas: Sequence[Hora], cfg: Optional[ConfigMojadura] = None) -> List[PeriodoMojadura]:
    """Une horas mojadas en periodos. Las horas faltantes en la serie cuentan como secas.

    Un hueco seco de <= cfg.max_interrupcion_h horas NO corta el periodo (se cuenta como
    interrupcion); las horas secas del hueco NO se suman a la LWD.
    """
    cfg = cfg or ConfigMojadura()
    hs = sorted(horas, key=lambda h: h.time)
    periodos: List[PeriodoMojadura] = []
    actual: Optional[dict] = None
    ultimo_mojado: Optional[datetime] = None
    for h in hs:
        if not hora_mojada(h, cfg):
            continue
        if actual is not None and ultimo_mojado is not None:
            secas = _horas_entre(ultimo_mojado, h.time) - 1
            if secas > cfg.max_interrupcion_h:
                p = _cerrar(actual, h.time, cfg)
                if p:
                    periodos.append(p)
                actual = None
            elif secas > 0:
                actual["interrupciones"] += 1
        if actual is None:
            actual = {"detalle": [], "hr": [], "lluvia": 0.0, "interrupciones": 0}
        actual["detalle"].append((h.time, float("nan") if _es_nan(h.T) else float(h.T)))
        actual["hr"].append(float("nan") if _es_nan(h.HR) else float(h.HR))
        if not _es_nan(h.lluvia):
            actual["lluvia"] += float(h.lluvia)
        ultimo_mojado = h.time
    if actual is not None and hs:
        p = _cerrar(actual, hs[-1].time, cfg)
        if p:
            periodos.append(p)
    return periodos


# =====================================================================================
# 2. Modelos de infeccion por evento (LWD en horas, T media en C)
# =====================================================================================

# ---- 2.1 Antracnosis: Wilson, Madden & Ellis 1990, Phytopathology 80:111-116 -----------------
# PUBLICADO. Coeficientes tal como los publica NC State IPM ("FLSAS Models", imagen
# "anthracnose fruit rot FLSAS formula", pagina actualizada 23-jul-2025):
#   f(LWD,T) = -3.7 + 0.33*LWD - 0.069*LWD*T + 0.005*LWD*T^2 - 9.3e-5*LWD*T^3
#   infNdx = e^f / (1 + e^f)
# Verificado: con estos coeficientes se reproducen los puntos de la grafica NCSU a 26.6 C
# (indice 0.15 a 7.0 h y 0.50 a 13.1 h). Es la ecuacion del Strawberry Advisory System
# (MacKenzie & Peres 2012, Plant Dis. 96:522) y del Blueberry Advisory System
# (Gama et al. 2022, EDIS PP366; validado en campo en arandano por Gama et al. 2021, Plant Dis. 105:1806).
WILSON_C0 = -3.7
WILSON_C1 = 0.33
WILSON_C2 = -0.069
WILSON_C3 = 0.005
WILSON_C4 = -9.3e-5


def _wilson_g(t: float) -> float:
    """Pendiente del logit respecto a LWD: g(T) = c1 + c2*T + c3*T^2 + c4*T^3."""
    return WILSON_C1 + WILSON_C2 * t + WILSON_C3 * t ** 2 + WILSON_C4 * t ** 3


def _raices_wilson() -> Tuple[float, float]:
    # g'(T) = c2 + 2*c3*T + 3*c4*T^2 = 0
    a, b, c = 3 * WILSON_C4, 2 * WILSON_C3, WILSON_C2
    d = math.sqrt(b * b - 4 * a * c)
    r1, r2 = (-b + d) / (2 * a), (-b - d) / (2 * a)
    return min(r1, r2), max(r1, r2)


# T_GMIN ~ 9.33 C (minimo local de g) y T_OPT ~ 26.5 C (maximo; NCSU reporta 26.6 C "optimal").
WILSON_T_GMIN, WILSON_T_OPT = _raices_wilson()


def indice_antracnosis_wilson(lwd: float, t: float) -> float:
    """Indice 0-1 de Wilson et al. 1990. Sin mojadura (lwd <= 0) -> 0.

    IMPLEMENTACION: para T < 9.33 C se usa g(9.33). El polinomio cubico extrapolado haria subir el
    riesgo hacia 0 C (g(0) = 0.33, igual que a 26 C), lo que contradice la biologia (Miles et al.
    2013: crecimiento escaso o nulo a 5 C) y la curva publicada por NCSU, que es plana y baja entre
    0 y ~10 C (grafica "Strawberry Fruit Anthracnose temp graph"). Con el recorte se reproduce esa
    curva (p. ej. 20.9 h a 0 C -> 0.06).
    """
    if lwd is None or _es_nan(lwd) or lwd <= 0 or _es_nan(t):
        return 0.0
    te = max(float(t), WILSON_T_GMIN)
    return _logistica(WILSON_C0 + float(lwd) * _wilson_g(te))


# ---- 2.2 Antracnosis, APROXIMACION calibrada en arandano -----------------------------------
# Fuente de calibracion (PUBLICADO, resumen abierto): Gillett, J.M. & Schilder, A.C. 2009.
# "Environmental requirements for infection of blueberry fruit by Colletotrichum acutatum".
# Acta Hortic. 810:355-360, doi:10.17660/ActaHortic.2009.810.46 (mismo grupo de Miles et al. 2013).
#   "la infeccion aumento considerablemente despues de 12-18 h de mojadura a 20-25 C, 18-24 h a 30 C,
#    24 h a 15 C y 36-48 h a 10 C"; optimo 25 C; "bajos niveles a 6 h en todos los casos".
# APROXIMACION: se toma el punto medio de cada rango como la LWD a la que el indice llega a 0.5
# (W50) y se usa la misma forma logistica de Wilson con el mismo intercepto (-3.7):
#   g_arandano(T) = 3.7 / W50(T),   indice = logistica(-3.7 + LWD * g_arandano(T)).
# Justificacion del anclaje en 0.5: a 20-25 C la ecuacion de Wilson llega a 0.5 entre 13.4 y 18 h,
# dentro del rango 12-18 h observado en arandano, asi que "aumento considerable" ~ W50 es coherente.
# Extremos: 0 a 5 C y a 35 C (Miles et al. 2013, resumen Crossref: poco o ningun crecimiento
# micelial a 5 y 35 C). Entre anclas: interpolacion lineal de g.
ANCLAS_ARANDANO_W50 = (  # (T en C, W50 en h) -- puntos medios de Gillett & Schilder 2009
    (10.0, 42.0),   # 36-48 h
    (15.0, 24.0),   # 24 h
    (20.0, 15.0),   # 12-18 h
    (25.0, 15.0),   # 12-18 h
    (30.0, 21.0),   # 18-24 h
)
_TABLA_G_ARANDANO = [(5.0, 0.0)] + [(t, -WILSON_C0 / w) for t, w in ANCLAS_ARANDANO_W50] + [(35.0, 0.0)]


def _interp(x: float, tabla: Sequence[Tuple[float, float]]) -> float:
    """Interpolacion lineal; fuera de la tabla devuelve el valor del extremo."""
    if x <= tabla[0][0]:
        return tabla[0][1]
    if x >= tabla[-1][0]:
        return tabla[-1][1]
    for (x0, y0), (x1, y1) in zip(tabla[:-1], tabla[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return 0.0


def g_arandano_aprox(t: float) -> float:
    return _interp(float(t), _TABLA_G_ARANDANO)


def indice_antracnosis_arandano_aprox(lwd: float, t: float) -> float:
    """APROXIMACION (ver arriba). Sin mojadura -> 0."""
    if lwd is None or _es_nan(lwd) or lwd <= 0 or _es_nan(t):
        return 0.0
    return _logistica(WILSON_C0 + float(lwd) * g_arandano_aprox(t))


def indice_antracnosis(lwd: float, t: float, modelo: str = "envolvente") -> float:
    """modelo: 'wilson' | 'arandano_aprox' | 'envolvente' (max de ambos, orientado a sensibilidad) | 'gim'."""
    if modelo == "wilson":
        return indice_antracnosis_wilson(lwd, t)
    if modelo == "arandano_aprox":
        return indice_antracnosis_arandano_aprox(lwd, t)
    if modelo == "gim":
        return indice_gim(lwd, t, PARAMS_GIM["antracnosis"])
    if modelo == "envolvente":
        return max(indice_antracnosis_wilson(lwd, t), indice_antracnosis_arandano_aprox(lwd, t))
    raise ValueError("modelo de antracnosis desconocido: %s" % modelo)


# ---- 2.3 Botrytis: Bulger, Ellis & Madden 1987, Phytopathology 77:1225-1230 ------------------
# PUBLICADO. Coeficientes tal como los publica NC State IPM (imagen "FLSAS Botrytis formula"):
#   f(LWD,T) = -4.268 - 0.0901*LWD + 0.0294*LWD*T - 2.35e-5*LWD*T^3 ;  infNdx = e^f/(1+e^f)
# Verificado: reproduce la grafica NCSU a 20.5 C (0.50 a 13.8 h; 0.70 a 16.5 h). Respuesta: infeccion
# de FLORES de fresa (proxy para arandano). Umbral de accion 0.50 validado en campo por MacKenzie &
# Peres 2012, Plant Dis. 96:529-536 (resumen Crossref).
# Rango experimental 5-30 C y hasta 32 h de mojadura (resumen del abstract APS hecho por el buscador;
# la pagina APS respondio 403 -> NO VERIFICADO directamente).
BULGER_C0 = -4.268
BULGER_C1 = -0.0901
BULGER_C2 = 0.0294
BULGER_C4 = -2.35e-5
BULGER_RANGO_T = (5.0, 30.0)     # NO VERIFICADO directamente
BULGER_LWD_MAX = 32.0            # NO VERIFICADO directamente
BULGER_T_OPT = math.sqrt(BULGER_C2 / (-3 * BULGER_C4))   # ~20.4 C (NCSU: 20.5 C)


def _fuera_rango_bulger(lwd: float, t: float) -> bool:
    """True si el evento sale del rango experimental de Bulger 1987 (extrapolacion)."""
    if _es_nan(t):
        return True
    return bool(lwd > BULGER_LWD_MAX or not (BULGER_RANGO_T[0] <= t <= BULGER_RANGO_T[1]))


def indice_botrytis_bulger(lwd: float, t: float) -> float:
    """Indice 0-1 de Bulger et al. 1987. Sin mojadura -> 0."""
    if lwd is None or _es_nan(lwd) or lwd <= 0 or _es_nan(t):
        return 0.0
    w, tt = float(lwd), float(t)
    return _logistica(BULGER_C0 + BULGER_C1 * w + BULGER_C2 * w * tt + BULGER_C4 * w * tt ** 3)


# ---- 2.4 Modelo generico de infeccion (GIM): Magarey, Sutton & Thayer 2005, Phytopathology 95:92 --
# Forma tal como la publica NC State IPM (imagen "GIM formula2"):
#   alfa = ln2 / ln[(Tmax-Tmin)/(Topt-Tmin)]
#   f_T  = [2 (T-Tmin)^a (Topt-Tmin)^a - (T-Tmin)^(2a)] / (Topt-Tmin)^(2a)   si Tmin <= T <= Tmax; 0 fuera
#   I    = LWD * f_T / LWDmin          ("1 ciclo ~ 20 % de incidencia a LWDmin")
#   infNdx = 0.15 ^ (3.5 * 0.15 ^ (0.75 * I))
# Uso de LWDmax: si la mojadura requerida LWDmin/f_T supera LWDmax no hay infeccion (I = 0).
# Esto es nuestra lectura de Magarey 2005 (el resumen solo define Wmin) -> NO VERIFICADO.
@dataclass(frozen=True)
class ParamsGIM:
    t_min: float
    t_opt: float
    t_max: float
    lwd_min: float
    lwd_max: float
    fuente: str


PARAMS_GIM: Dict[str, ParamsGIM] = {
    # PUBLICADO (NCSU IPM, "GIM Models", en evaluacion por NCSU): C. acutatum en fresa.
    "antracnosis": ParamsGIM(7.0, 27.5, 35.0, 6.0, 36.0, "NCSU IPM GIM C. acutatum"),
    # PUBLICADO (NCSU IPM, "GIM Models"): B. cinerea en fresa.
    "botrytis": ParamsGIM(6.0, 20.5, 40.0, 8.0, 18.0, "NCSU IPM GIM B. cinerea"),
    # APROXIMACION para roya del arandano (Thekopsora minima):
    #   t_opt 21.5 C: optimo de germinacion de urediniosporas, Pfister, Halik & Bergdahl 2004,
    #       Plant Dis. 88:359-362 (resumen Europe PMC). Griffin & Anderson 2026, J. Fungi 12:133: 19-23 C favorable.
    #   t_min 8 C: SUPUESTO. Pfister 2004: germinacion "muy reducida" bajo 15 C, pero ocurre a 10 C
    #       (menor temperatura ensayada); se extrapola un poco por debajo.
    #   t_max 32 C: SUPUESTO. Pfister 2004: a 30 C la produccion de uredinios cae 6 veces (no es cero);
    #       Agriculture Victoria: infecciones poco probables sobre 30 C (resumen del buscador, NO VERIFICADO).
    #   lwd_min 8 h: SUPUESTO. Para otras royas, 4-8 h de mojadura continua dan la maxima germinacion
    #       (Griffin & Anderson 2026, discusion, citando estudios en Uromyces).
    #   lwd_max 48 h: evaluacion EPPO resumida por DEFRA (2021): 15-25 C y "periodo de mojadura de 48 h".
    "roya": ParamsGIM(8.0, 21.5, 32.0, 8.0, 48.0, "APROXIMACION GIM con Pfister 2004 / EPPO-DEFRA 2021"),
}


def f_temperatura_gim(t: float, p: ParamsGIM) -> float:
    if _es_nan(t) or t < p.t_min or t > p.t_max:
        return 0.0
    a = math.log(2.0) / math.log((p.t_max - p.t_min) / (p.t_opt - p.t_min))
    x = (float(t) - p.t_min)
    xo = (p.t_opt - p.t_min)
    val = (2.0 * x ** a * xo ** a - x ** (2 * a)) / xo ** (2 * a)
    return max(0.0, min(1.0, val))


def ciclos_gim(lwd: float, t: float, p: ParamsGIM) -> float:
    if lwd is None or _es_nan(lwd) or lwd <= 0:
        return 0.0
    ft = f_temperatura_gim(t, p)
    if ft <= 0 or p.lwd_min / ft > p.lwd_max:
        return 0.0
    return float(lwd) * ft / p.lwd_min


def indice_gim_desde_ciclos(i: float) -> float:
    if i <= 0:
        return 0.0
    return 0.15 ** (3.5 * 0.15 ** (0.75 * i))


def indice_gim(lwd: float, t: float, p: ParamsGIM) -> float:
    """Indice GIM 0-1. Sin mojadura -> 0."""
    return indice_gim_desde_ciclos(ciclos_gim(lwd, t, p))


def indice_roya(lwd: float, t: float) -> float:
    """APROXIMACION: GIM con parametros de Thekopsora minima (ver PARAMS_GIM['roya'])."""
    return indice_gim(lwd, t, PARAMS_GIM["roya"])


# ---- 2.5 Oidio: indice de Gubler-Thomas (UC Davis), oidio de la VID ----------------------------
# PUBLICADO para vid (UC IPM, modelo "Powdery mildew of grape", Thomas, Gubler & Leavitt 1994,
# Phytopathology 84:1070 abstr.). NO VALIDADO EN ARANDANO.
#   - Arranque: 3 dias consecutivos con >= 6 h seguidas entre 70 y 85 F (21.1-29.4 C): +20 cada dia.
#   - Despues: +20 por dia con >= 6 h seguidas en el rango; -10 si no.
#   - -10 si T >= 95 F (35 C) al menos 15 min (con datos horarios: alguna hora >= 35 C).
#   - Limites 0-100; cambio diario entre -10 y +20. Tras aplicar fungicida el indice vuelve a 0.
#   - Lectura: <= 30 intervalo largo; 40-50 intermedio; 60-100 presion alta.
# Con datos horarios la regla "salir del rango > 45 min corta la racha" se aplica como: cualquier
# hora fuera del rango corta la racha.
GT_T_MIN_C = (70.0 - 32.0) * 5.0 / 9.0     # 21.11 C
GT_T_MAX_C = (85.0 - 32.0) * 5.0 / 9.0     # 29.44 C
GT_T_ALTA_C = (95.0 - 32.0) * 5.0 / 9.0    # 35.0 C
GT_HORAS = 6


@dataclass
class DiaOidio:
    fecha: date
    indice: int            # 0-100
    racha_max_h: int
    caliente: bool
    activado: bool


def _racha_maxima(horas_dia: Sequence[Hora], t_min: float, t_max: float) -> int:
    mejor = actual = 0
    prev: Optional[datetime] = None
    for h in sorted(horas_dia, key=lambda x: x.time):
        ok = (not _es_nan(h.T)) and t_min <= float(h.T) <= t_max
        consecutiva = prev is not None and _horas_entre(prev, h.time) == 1
        if ok:
            actual = actual + 1 if (consecutiva and actual > 0) else 1
        else:
            actual = 0
        mejor = max(mejor, actual)
        prev = h.time
    return mejor


def indice_oidio_gubler_thomas(horas: Sequence[Hora], t_min_c: float = GT_T_MIN_C,
                               t_max_c: float = GT_T_MAX_C, t_alta_c: float = GT_T_ALTA_C,
                               horas_requeridas: int = GT_HORAS,
                               fechas_aplicacion: Iterable[date] = ()) -> List[DiaOidio]:
    por_dia: Dict[date, List[Hora]] = {}
    for h in horas:
        por_dia.setdefault(h.time.date(), []).append(h)
    aplic = set(fechas_aplicacion)
    out: List[DiaOidio] = []
    indice, activado, racha_dias = 0, False, 0
    for d in sorted(por_dia):
        hd = por_dia[d]
        racha = _racha_maxima(hd, t_min_c, t_max_c)
        caliente = any((not _es_nan(h.T)) and float(h.T) >= t_alta_c for h in hd)
        favorable = racha >= horas_requeridas
        if not activado:
            racha_dias = racha_dias + 1 if favorable else 0
            if racha_dias >= 3:
                activado, indice = True, 60
        else:
            delta = (20 if favorable else -10) + (-10 if caliente else 0)
            delta = max(-10, min(20, delta))
            indice = max(0, min(100, indice + delta))
        if d in aplic:
            indice = 0
        out.append(DiaOidio(d, indice, racha, caliente, activado))
    return out


# =====================================================================================
# 3. Clasificacion, fenologia y evaluacion
# =====================================================================================

# Umbrales (medio, alto): indice < medio -> bajo; medio <= indice < alto -> medio; >= alto -> alto.
UMBRALES: Dict[str, Tuple[float, float]] = {
    # PUBLICADO: NCSU IPM FLSAS (bajo < 0.15 <= medio < 0.50 <= alto); MacKenzie & Peres 2012a:
    # captan si INF > 0.15, piraclostrobina si INF > 0.5.
    "antracnosis": (0.15, 0.50),
    # PUBLICADO: NCSU IPM FLSAS (bajo < 0.50 <= medio < 0.70 <= alto); MacKenzie & Peres 2012b: INF >= 0.50.
    "botrytis": (0.50, 0.70),
    # SUPUESTO: 0.20 = 1 ciclo GIM (~20 % de incidencia segun NCSU/Magarey); 0.50 por analogia con antracnosis.
    "roya": (0.20, 0.50),
    # PUBLICADO para vid (UC IPM): indice/100; 40-50 intermedio, >= 60 alto.
    "oidio": (0.40, 0.60),
}

# Multiplicador de fenologia: SUPUESTO en todos los valores (no hay fuente que lo cuantifique).
# Rango [0, 1]: 1.0 = etapa mas susceptible (deja intacto el indice publicado).
FENOLOGIA: Dict[str, Dict[str, float]] = {
    # Fruto verde y maduro se infectan (Gillett & Schilder 2009; infeccion latente en fruto verde,
    # MSU E3039). Floracion: inicio de aplicaciones en BAS/MSU. Vegetativo: solo ramillas/hojas.
    "antracnosis": {"vegetativo": 0.2, "floracion": 0.6, "fruto_verde": 1.0, "maduracion": 1.0},
    # Bulger 1987 modela infeccion de flores; CAES (Connecticut): petalos senescentes y brotes tiernos.
    "botrytis": {"vegetativo": 0.3, "floracion": 1.0, "fruto_verde": 0.5, "maduracion": 0.7},
    # Enfermedad de hoja; en el tropico el arandano no pierde hojas (PNW Handbook: sin hospedero
    # alterno en plantas que no defolian) -> sin reduccion.
    "roya": {"vegetativo": 1.0, "floracion": 1.0, "fruto_verde": 1.0, "maduracion": 1.0},
    # Cornell (fast fact): los conidios infectan tejido emergente.
    "oidio": {"vegetativo": 1.0, "floracion": 0.8, "fruto_verde": 0.8, "maduracion": 0.6},
}


def multiplicador_fenologia(enfermedad: str, etapa: Optional[str]) -> float:
    if etapa is None:
        return 1.0
    if etapa not in ETAPAS:
        raise ValueError("etapa desconocida: %s (use %s)" % (etapa, ", ".join(ETAPAS)))
    return FENOLOGIA[enfermedad][etapa]


def clasificar(indice: float, enfermedad: str, umbrales: Optional[Dict[str, Tuple[float, float]]] = None) -> str:
    medio, alto = (umbrales or UMBRALES)[enfermedad]
    if _es_nan(indice) or indice < medio:
        return "bajo"
    if indice < alto:
        return "medio"
    return "alto"


def _nivel(clase: str) -> int:
    return CLASES.index(clase)


def indices_evento(lwd: float, t: float, modelo_antracnosis: str = "envolvente") -> Dict[str, float]:
    """Indices publicados/aproximados (sin fenologia) para un periodo de mojadura."""
    return {
        "antracnosis": indice_antracnosis(lwd, t, modelo_antracnosis),
        "antracnosis_wilson": indice_antracnosis_wilson(lwd, t),
        "antracnosis_arandano_aprox": indice_antracnosis_arandano_aprox(lwd, t),
        "antracnosis_gim": indice_gim(lwd, t, PARAMS_GIM["antracnosis"]),
        "botrytis": indice_botrytis_bulger(lwd, t),
        "botrytis_gim": indice_gim(lwd, t, PARAMS_GIM["botrytis"]),
        "roya": indice_roya(lwd, t),
    }


FUENTE_CORTA = {
    "antracnosis": "Wilson et al. 1990 (SAS/BAS) + aprox. arandano Gillett & Schilder 2009",
    "botrytis": "Bulger et al. 1987 (flor de fresa, proxy)",
    "roya": "APROXIMACION GIM (Magarey 2005) con Pfister 2004 / EPPO",
    "oidio": "Gubler-Thomas (vid, UC IPM) - NO VALIDADO en arandano",
}


def evaluar_eventos(horas: Sequence[Hora], cfg: Optional[ConfigMojadura] = None, etapa: Optional[str] = None,
                    modelo_antracnosis: str = "envolvente") -> List[dict]:
    """Una fila por periodo de mojadura con indices, indices ajustados por fenologia y clases."""
    cfg = cfg or ConfigMojadura()
    filas = []
    for p in detectar_periodos(horas, cfg):
        ind = indices_evento(p.horas_mojadas, p.t_media, modelo_antracnosis)
        fila = {
            "inicio": p.inicio, "fin": p.fin, "horas_mojadas": p.horas_mojadas,
            "duracion_total_h": p.duracion_total_h, "n_interrupciones": p.n_interrupciones,
            "t_media_mojada": round(p.t_media, 2) if not _es_nan(p.t_media) else None,
            "hr_media": round(p.hr_media, 1) if not _es_nan(p.hr_media) else None,
            "lluvia_mm": round(p.lluvia_mm, 1), "abierto": p.abierto,
            "botrytis_fuera_de_rango": _fuera_rango_bulger(p.horas_mojadas, p.t_media),
        }
        for k, v in ind.items():
            fila["idx_" + k] = round(v, 4)
        for enf in ("antracnosis", "botrytis", "roya"):
            aj = min(1.0, ind[enf] * multiplicador_fenologia(enf, etapa))
            fila["idx_aj_" + enf] = round(aj, 4)
            fila["clase_" + enf] = clasificar(aj, enf)
        filas.append(fila)
    return filas


def _instantaneas_por_dia(p: PeriodoMojadura) -> Dict[date, Tuple[int, float]]:
    """LWD acumulada y T media acumulada al cierre de cada dia calendario que toca el periodo."""
    out: Dict[date, Tuple[int, float]] = {}
    n, suma, nt = 0, 0.0, 0
    for t, temp in p.detalle:
        n += 1
        if not _es_nan(temp):
            suma += temp
            nt += 1
        out[t.date()] = (n, (suma / nt) if nt else float("nan"))
    return out


def resumen_diario(horas: Sequence[Hora], cfg: Optional[ConfigMojadura] = None, etapa: Optional[str] = None,
                   modelo_antracnosis: str = "envolvente", fechas_aplicacion: Iterable[date] = (),
                   ventana_roya_dias: int = 14) -> List[dict]:
    """Una fila por dia: indice maximo (ajustado por fenologia) de cada enfermedad y su clase.

    Para cada dia D se evalua cada periodo de mojadura que toca D con la LWD acumulada hasta el
    final de D (un periodo de 3 dias sube el riesgo dia a dia). El oidio se calcula con la serie
    horaria completa. 'roya_presion_14d' = 1 - prod(1 - indice_evento) de los periodos que terminan
    en los ultimos 14 dias (SUPUESTO: eventos independientes; ciclo de 10-14 d: latencia ~10 d a
    20 C segun PNW Handbook y 10-10.7 d a 20-25 C segun Pfister 2004).
    """
    cfg = cfg or ConfigMojadura()
    hs = sorted(horas, key=lambda h: h.time)
    if not hs:
        return []
    dias = sorted({h.time.date() for h in hs})
    base = {d: {"fecha": d, "horas_mojadas_dia": 0, "t_media_dia": None} for d in dias}
    tsum: Dict[date, List[float]] = {}
    for h in hs:
        if hora_mojada(h, cfg):
            base[h.time.date()]["horas_mojadas_dia"] += 1
        if not _es_nan(h.T):
            tsum.setdefault(h.time.date(), []).append(float(h.T))
    for d, v in tsum.items():
        base[d]["t_media_dia"] = round(sum(v) / len(v), 2)

    mejor: Dict[date, Dict[str, Tuple[float, dict]]] = {d: {} for d in dias}
    roya_finales: List[Tuple[date, float]] = []
    for p in detectar_periodos(hs, cfg):
        for d, (lwd, tm) in _instantaneas_por_dia(p).items():
            ind = indices_evento(lwd, tm, modelo_antracnosis)
            for enf in ("antracnosis", "botrytis", "roya"):
                aj = min(1.0, ind[enf] * multiplicador_fenologia(enf, etapa))
                if enf not in mejor[d] or aj > mejor[d][enf][0]:
                    mejor[d][enf] = (aj, {"inicio": p.inicio, "lwd": lwd, "t": tm, "bruto": ind[enf],
                                          "abierto": p.abierto})
        roya_finales.append((p.fin.date(), indice_roya(p.horas_mojadas, p.t_media)))

    oidio = {x.fecha: x for x in indice_oidio_gubler_thomas(hs, fechas_aplicacion=fechas_aplicacion)}
    filas = []
    for d in dias:
        fila = dict(base[d])
        peor = "bajo"
        motivos = []
        for enf in ("antracnosis", "botrytis", "roya"):
            aj, info = mejor[d].get(enf, (0.0, None))
            clase = clasificar(aj, enf)
            fila["idx_" + enf] = round(aj, 4)
            fila["clase_" + enf] = clase
            if info:
                fila[enf + "_lwd_h"] = info["lwd"]
                fila[enf + "_t_media"] = round(info["t"], 2) if not _es_nan(info["t"]) else None
                fila[enf + "_idx_sin_fenologia"] = round(info["bruto"], 4)
            if clase != "bajo" and info:
                motivos.append("%s %s: %d h de mojadura a %.1f C (indice %.2f; umbrales %.2f/%.2f; %s)" % (
                    enf, clase.upper(), info["lwd"], info["t"], aj, UMBRALES[enf][0], UMBRALES[enf][1],
                    FUENTE_CORTA[enf]))
            if _nivel(clase) > _nivel(peor):
                peor = clase
        o = oidio.get(d)
        oi = (o.indice / 100.0) if o else 0.0
        oi_aj = min(1.0, oi * multiplicador_fenologia("oidio", etapa))
        fila["oidio_gt_indice_0_100"] = o.indice if o else 0
        fila["oidio_racha_h"] = o.racha_max_h if o else 0
        fila["idx_oidio"] = round(oi_aj, 4)
        fila["clase_oidio"] = clasificar(oi_aj, "oidio")
        if fila["clase_oidio"] != "bajo":
            motivos.append("oidio %s: indice Gubler-Thomas %d (%s)" % (
                fila["clase_oidio"].upper(), o.indice, FUENTE_CORTA["oidio"]))
        if _nivel(fila["clase_oidio"]) > _nivel(peor):
            peor = fila["clase_oidio"]
        ini = d - timedelta(days=ventana_roya_dias - 1)
        prod = 1.0
        for dfin, r in roya_finales:
            if ini <= dfin <= d:
                prod *= (1.0 - r)
        fila["roya_presion_14d"] = round(1.0 - prod, 4)
        fila["riesgo_global"] = peor
        fila["motivo"] = " | ".join(motivos)
        filas.append(fila)
    return filas


def riesgo_ventana_72h(filas_diarias: Sequence[dict], fecha: date) -> dict:
    """Riesgo por enfermedad = maximo de ayer, hoy y manana (como el mapa de NCSU IPM:
    "highest risk index ... for the 72-hr time period from midnight yesterday through midnight tomorrow")."""
    sel = [f for f in filas_diarias if fecha - timedelta(days=1) <= f["fecha"] <= fecha + timedelta(days=1)]
    out = {"fecha": fecha.isoformat(), "dias_usados": [f["fecha"].isoformat() for f in sel], "enfermedades": {}}
    # [verificacion-riesgo-clima, 2026-10-23] Antes, una fecha fuera del pronostico (p. ej. cache vencida el dia
    # de la demo) devolvia riesgo_global="bajo" sin ningun dia evaluado: un falso "sin riesgo" silencioso.
    # Ahora se marca "sin_datos" con un "error" (el CLI ya imprime r["error"]) y se avisa si la ventana esta incompleta.
    if not sel:
        rango = ("%s a %s" % (min(f["fecha"] for f in filas_diarias).isoformat(),
                              max(f["fecha"] for f in filas_diarias).isoformat())) if filas_diarias else "ninguno"
        out["riesgo_global"] = "sin_datos"
        out["motivos"] = []
        out["error"] = "la ventana de 72 h de %s no tiene datos (dias disponibles: %s); actualizar el pronostico" % (
            fecha.isoformat(), rango)
        return out
    if len(sel) < 3:
        out["advertencia"] = "ventana incompleta: solo %d de 3 dias con datos" % len(sel)
    peor = "bajo"
    for enf in ENFERMEDADES:
        if not sel:
            continue
        top = max(sel, key=lambda f: f["idx_" + enf])
        clase = clasificar(top["idx_" + enf], enf)
        out["enfermedades"][enf] = {
            "indice": top["idx_" + enf], "clase": clase, "dia_pico": top["fecha"].isoformat(),
            "umbrales_medio_alto": list(UMBRALES[enf]), "modelo": FUENTE_CORTA[enf],
        }
        if _nivel(clase) > _nivel(peor):
            peor = clase
    out["riesgo_global"] = peor
    out["motivos"] = [f["motivo"] for f in sel if f.get("motivo")]
    return out


# =====================================================================================
# 4. Lectura de datos
# =====================================================================================

_ALIAS = {
    "time": ("time", "fecha_hora", "datetime"),
    "T": ("T", "temperature_2m", "temp", "t"),
    "HR": ("HR", "relative_humidity_2m", "rh", "hr"),
    "lluvia": ("lluvia", "precipitation", "precip", "rain"),
    "lwp": ("LWP", "leaf_wetness_probability", "lwp"),
    "riego": ("riego",),
}


def _col(nombres: Sequence[str], alias: Sequence[str]) -> Optional[str]:
    for a in alias:
        if a in nombres:
            return a
    return None


def _parse_time(s: str) -> datetime:
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError("fecha no reconocida: %r" % s)


def _num(x) -> float:
    if x is None or (isinstance(x, str) and x.strip() == ""):
        return float("nan")
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def horas_desde_csv(ruta: str, filtro: Optional[Dict[str, str]] = None) -> List[Hora]:
    """Lee un CSV horario (formato clima/derivados/hoja_mojada_horaria_*.csv o crudo de Open-Meteo).

    filtro: p. ej. {"modelo": "best_match"} para quedarse con un modelo en los CSV de cache.
    Si hay timestamps repetidos se conserva el primero.
    """
    with open(ruta, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        c = {k: _col(cols, v) for k, v in _ALIAS.items()}
        if not c["time"] or not c["T"] or not c["HR"]:
            raise ValueError("CSV sin columnas time/T/HR reconocibles: %s" % cols)
        vistos = set()
        out = []
        for r in rd:
            if filtro and any(r.get(k) != v for k, v in filtro.items()):
                continue
            t = _parse_time(r[c["time"]])
            if t in vistos:
                continue
            vistos.add(t)
            lluvia = _num(r[c["lluvia"]]) if c["lluvia"] else 0.0
            out.append(Hora(
                time=t, T=_num(r[c["T"]]), HR=_num(r[c["HR"]]),
                lluvia=0.0 if _es_nan(lluvia) else lluvia,
                lwp=_num(r[c["lwp"]]) if c["lwp"] else None,
                riego=bool(int(float(r[c["riego"]]))) if c["riego"] and r[c["riego"]] not in ("", None) else False,
            ))
    out.sort(key=lambda h: h.time)
    return out


def horas_desde_df(df) -> List[Hora]:
    """Convierte un pandas.DataFrame (mismas columnas que horas_desde_csv) en lista de Hora."""
    cols = list(df.columns)
    c = {k: _col(cols, v) for k, v in _ALIAS.items()}
    if not c["T"] or not c["HR"]:
        raise ValueError("DataFrame sin columnas T/HR reconocibles: %s" % cols)
    tiempos = df[c["time"]] if c["time"] else df.index
    out = []
    for i, t in enumerate(tiempos):
        tt = t.to_pydatetime() if hasattr(t, "to_pydatetime") else (t if isinstance(t, datetime) else _parse_time(str(t)))
        fila = df.iloc[i]
        ll = _num(fila[c["lluvia"]]) if c["lluvia"] else 0.0
        out.append(Hora(tt, _num(fila[c["T"]]), _num(fila[c["HR"]]), 0.0 if _es_nan(ll) else ll,
                        _num(fila[c["lwp"]]) if c["lwp"] else None,
                        bool(fila[c["riego"]]) if c["riego"] else False))
    out.sort(key=lambda h: h.time)
    return out


def escribir_csv(filas: Sequence[dict], ruta: str) -> None:
    if not filas:
        open(ruta, "w").close()
        return
    claves: List[str] = []
    for f in filas:
        for k in f:
            if k not in claves:
                claves.append(k)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=claves)
        w.writeheader()
        for f in filas:
            w.writerow({k: (v.isoformat(sep=" ") if isinstance(v, datetime) else
                            v.isoformat() if isinstance(v, date) else v) for k, v in f.items()})


# =====================================================================================
# 5. CLI
# =====================================================================================

def _ultimo_pronostico(punto: str) -> Optional[str]:
    rutas = sorted(glob.glob(os.path.join(RAIZ_DATOS, "clima", "cache", "pronostico_%s_*.csv" % punto)))
    return rutas[-1] if rutas else None


def _cmd_evaluar(a) -> int:
    cfg = ConfigMojadura(umbral_hr=a.umbral_hr, umbral_lluvia_mm=a.umbral_lluvia,
                         usar_lwp=a.usar_lwp, max_interrupcion_h=a.max_interrupcion)
    filtro = {"modelo": a.modelo_clima} if a.modelo_clima else None
    horas = horas_desde_csv(a.csv, filtro)
    eventos = evaluar_eventos(horas, cfg, a.etapa)
    dias = resumen_diario(horas, cfg, a.etapa)
    os.makedirs(a.salida_dir, exist_ok=True)
    pref = os.path.join(a.salida_dir, "%s_%s" % (a.prefijo, a.punto))
    escribir_csv(eventos, pref + "_eventos.csv")
    escribir_csv(dias, pref + "_diario.csv")
    conteo = {enf: {c: sum(1 for d in dias if d["clase_" + enf] == c) for c in CLASES} for enf in ENFERMEDADES}
    print(json.dumps({"punto": a.punto, "horas": len(horas), "eventos": len(eventos), "dias": len(dias),
                      "dias_por_clase": conteo, "salidas": [pref + "_eventos.csv", pref + "_diario.csv"]},
                     ensure_ascii=False, indent=1))
    return 0


def _cmd_actual(a) -> int:
    cfg = ConfigMojadura(umbral_hr=a.umbral_hr)
    puntos = a.puntos.split(",")
    hoy = datetime.strptime(a.fecha, "%Y-%m-%d").date() if a.fecha else date.today()
    res = {"generado": datetime.now().isoformat(timespec="seconds"), "etapa": a.etapa,
           "criterio_mojadura": asdict(cfg), "puntos": {}}
    for p in puntos:
        ruta = _ultimo_pronostico(p)
        if not ruta:
            res["puntos"][p] = {"error": "sin pronostico en clima/cache"}
            continue
        horas = horas_desde_csv(ruta)
        dias = resumen_diario(horas, cfg, a.etapa)
        r = riesgo_ventana_72h(dias, hoy)
        r["fuente_clima"] = os.path.relpath(ruta, RAIZ_DATOS)
        res["puntos"][p] = r
    os.makedirs(a.salida_dir, exist_ok=True)
    salida = os.path.join(a.salida_dir, "riesgo_actual.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    for p, r in res["puntos"].items():
        if "error" in r:
            print(p, r["error"])
            continue
        print("%-10s global=%-5s " % (p, r["riesgo_global"]) + "  ".join(
            "%s=%s(%.2f)" % (e, v["clase"], v["indice"]) for e, v in r["enfermedades"].items()))
    print("->", salida)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Modelos de riesgo de enfermedad del arandano")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluar", help="eventos y resumen diario de un CSV horario")
    e.add_argument("--csv", required=True)
    e.add_argument("--punto", default="punto")
    e.add_argument("--prefijo", default="riesgo")
    e.add_argument("--etapa", choices=ETAPAS, default=None)
    e.add_argument("--umbral-hr", type=float, default=90.0)
    e.add_argument("--umbral-lluvia", type=float, default=0.5)
    e.add_argument("--usar-lwp", action="store_true")
    e.add_argument("--max-interrupcion", type=int, default=3)
    e.add_argument("--modelo-clima", default=None, help="filtra la columna 'modelo' (p. ej. best_match)")
    e.add_argument("--salida-dir", default=os.path.join(AQUI, "salidas"))
    e.set_defaults(func=_cmd_evaluar)
    c = sub.add_parser("actual", help="riesgo 72 h con el ultimo pronostico en clima/cache")
    c.add_argument("--puntos", default="chia,guasca,sotaquira,tausa")
    c.add_argument("--fecha", default=None, help="YYYY-MM-DD (por defecto hoy)")
    c.add_argument("--etapa", choices=ETAPAS, default=None)
    c.add_argument("--umbral-hr", type=float, default=90.0)
    c.add_argument("--salida-dir", default=os.path.join(AQUI, "salidas"))
    c.set_defaults(func=_cmd_actual)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
