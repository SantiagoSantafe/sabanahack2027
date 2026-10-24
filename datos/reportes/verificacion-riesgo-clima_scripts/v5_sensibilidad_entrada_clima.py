"""Verificacion adversaria (5): sensibilidad de los dias en alto 2025 (HR>=90 o lluvia>=0.5) al clima de entrada:
(a) sesgo de temperatura de +-1 C (dentro del MAE 1.2-1.6 C medido frente al IDEAM),
(b) modelo meteorologico ERA5 en lugar de best_match (los dos de Open-Meteo, ya en clima/cache).
Uso: .venv/bin/python -I -B reportes/verificacion-riesgo-clima_scripts/v5_sensibilidad_entrada_clima.py
"""
import os
import sys
from dataclasses import replace

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "riesgo"))
import risk as r  # noqa: E402

PUNTOS = ("sotaquira", "tausa", "guasca", "chia")
ENF = ("antracnosis", "botrytis", "roya")
cfg = r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.5)


def altos(horas):
    d = r.resumen_diario(horas, cfg)
    return {e: sum(1 for x in d if x["clase_" + e] == "alto") for e in ENF}


base = {p: r.horas_desde_csv(os.path.join(RAIZ, "clima", "cache", "historico_2025_%s.csv" % p),
                             {"modelo": "best_match"}) for p in PUNTOS}
print("(a) Sesgo de T, suma de 4 puntos, dias en alto 2025:")
for dt in (-1.0, 0.0, 1.0):
    s = {e: 0 for e in ENF}
    for p in PUNTOS:
        for e, v in altos([replace(h, T=h.T + dt) for h in base[p]]).items():
            s[e] += v
    print("  T%+.0f C: %s" % (dt, s))
print("(b) best_match frente a ERA5, dias en alto 2025 por punto:")
for p in PUNTOS:
    era5 = r.horas_desde_csv(os.path.join(RAIZ, "clima", "cache", "historico_2025_%s_era5.csv" % p), {"modelo": "era5"})
    print("  %-10s best_match %s | era5 %s" % (p, altos(base[p]), altos(era5)))
