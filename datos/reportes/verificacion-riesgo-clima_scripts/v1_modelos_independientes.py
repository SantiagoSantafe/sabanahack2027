"""Verificacion adversaria: reimplementacion INDEPENDIENTE (no importa risk.py) de Wilson 1990,
Bulger 1987 y GIM (Magarey 2005, forma NCSU) para comprobar los puntos publicados por NCSU IPM y
comparar con lo que devuelve riesgo/risk.py.

Uso: .venv/bin/python -I reportes/verificacion-riesgo-clima_scripts/v1_modelos_independientes.py
"""
import math
import sys
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def logit_inv(z):
    return 1.0 / (1.0 + math.exp(-z))


# Coeficientes leidos por mi de las imagenes NCSU (raw/riesgo_ncsu_sas/*formula*.jpg)
def wilson_raw(w, t):
    return logit_inv(-3.7 + 0.33 * w - 0.069 * w * t + 0.005 * w * t ** 2 - 9.3e-5 * w * t ** 3)


def bulger(w, t):
    return logit_inv(-4.268 - 0.0901 * w + 0.0294 * w * t - 2.35e-5 * w * t ** 3)


def gim(w, t, tmin, topt, tmax, wmin):
    if t < tmin or t > tmax:
        return 0.0
    a = math.log(2) / math.log((tmax - tmin) / (topt - tmin))
    ft = (2 * (t - tmin) ** a * (topt - tmin) ** a - (t - tmin) ** (2 * a)) / (topt - tmin) ** (2 * a)
    i = w * ft / wmin
    return 0.15 ** (3.5 * 0.15 ** (0.75 * i)) if i > 0 else 0.0


def w_para(indice, f, t, lo=0.01, hi=300.0):
    """LWD a la que el indice f(w,t) alcanza 'indice' (biseccion; f monotona creciente en w)."""
    if f(hi, t) < indice:
        return float("inf")
    for _ in range(200):
        m = (lo + hi) / 2
        if f(m, t) < indice:
            lo = m
        else:
            hi = m
    return hi


print("== Puntos publicados en las graficas NCSU (raw/riesgo_ncsu_sas/*.png) ==")
print("Wilson 26.6C 7.0h  -> %.3f (grafica 0.15)" % wilson_raw(7.0, 26.6))
print("Wilson 26.6C 13.1h -> %.3f (grafica 0.50)" % wilson_raw(13.1, 26.6))
print("Wilson 26.6C 20.9h -> %.3f (grafica ~0.90)" % wilson_raw(20.9, 26.6))
print("Wilson 0C 20.9h SIN recorte -> %.3f (grafica ~0.06: la curva NCSU NO es el polinomio crudo)" % wilson_raw(20.9, 0.0))
print("Bulger 20.5C 13.8h -> %.3f (grafica 0.50)" % bulger(13.8, 20.5))
print("Bulger 20.5C 16.5h -> %.3f (grafica 0.70)" % bulger(16.5, 20.5))
print("Bulger 20.5C 20.8h -> %.3f (grafica ~0.90)" % bulger(20.8, 20.5))
print("Bulger  5.0C 20.8h -> %.3f (grafica ~0.04)" % bulger(20.8, 5.0))
print("GIM 1 ciclo -> %.3f (NCSU: ~20 %%)" % (0.15 ** (3.5 * 0.15 ** 0.75)))

# Optimos analiticos
a, b, c = 3 * -9.3e-5, 2 * 0.005, -0.069
d = math.sqrt(b * b - 4 * a * c)
r = sorted([(-b + d) / (2 * a), (-b - d) / (2 * a)])
print("Wilson: minimo local de g en %.2f C, maximo en %.2f C (NCSU 26.6)" % tuple(r))
print("Bulger: optimo %.2f C (NCSU 20.5)" % math.sqrt(0.0294 / (3 * 2.35e-5)))

print("\n== Horas de mojadura para llegar a umbrales, temperaturas tipicas de la Sabana ==")
def wilson_clip(w, t):
    return wilson_raw(w, max(t, r[0]))
print("T(C)  Wilson_recorte W0.15/W0.50   Bulger W0.50/W0.70   GIM_roya(8/21.5/32, Wmin 8) W0.20/W0.50")
for t in (8, 9, 10, 11, 12, 13, 15, 18, 20, 22, 25):
    print("%4.0f  %6.1f / %6.1f            %6.1f / %6.1f      %6.1f / %6.1f" % (
        t, w_para(0.15, wilson_clip, t), w_para(0.50, wilson_clip, t),
        w_para(0.50, bulger, t), w_para(0.70, bulger, t),
        w_para(0.20, lambda w, tt: gim(w, tt, 8, 21.5, 32, 8), t),
        w_para(0.50, lambda w, tt: gim(w, tt, 8, 21.5, 32, 8), t)))

# Comparacion contra risk.py (importado solo para contrastar)
sys.path.insert(0, os.path.join(RAIZ, "riesgo"))
import risk  # noqa: E402

maxdif = 0.0
for w in (1, 3, 6, 9, 12, 18, 24, 36, 48, 60):
    for t in (0, 5, 9.33, 10, 12, 15, 20, 25, 30, 35):
        maxdif = max(maxdif, abs(risk.indice_botrytis_bulger(w, t) - bulger(w, t)))
        maxdif = max(maxdif, abs(risk.indice_antracnosis_wilson(w, t) - wilson_clip(w, t)))
        p = risk.PARAMS_GIM["roya"]
        mine = gim(w, t, p.t_min, p.t_opt, p.t_max, p.lwd_min)
        if p.lwd_min / max(1e-9, (mine and 1) * 1) and t >= p.t_min:
            pass
print("\nMax |risk.py - reimplementacion| (Wilson con recorte, Bulger) en grilla: %.2e" % maxdif)

# Efecto de la condicion LWDmax (solo en risk.py) sobre roya
p = risk.PARAMS_GIM["roya"]
print("Roya: T por debajo de la cual risk.py anula el indice por Wmin/fT > Wmax (48 h):")
for t in [x / 2 for x in range(16, 30)]:
    a_ = math.log(2) / math.log((p.t_max - p.t_min) / (p.t_opt - p.t_min))
    ft = (2 * (t - p.t_min) ** a_ * (p.t_opt - p.t_min) ** a_ - (t - p.t_min) ** (2 * a_)) / (p.t_opt - p.t_min) ** (2 * a_) if t > p.t_min else 0
    print("  T=%.1f fT=%.3f Wmin/fT=%.1f h -> %s" % (t, ft, (p.lwd_min / ft) if ft else float('inf'),
          "anulado" if (not ft or p.lwd_min / ft > p.lwd_max) else "permitido"))
