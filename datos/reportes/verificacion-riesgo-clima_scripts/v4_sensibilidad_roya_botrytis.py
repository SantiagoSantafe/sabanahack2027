"""Verificacion adversaria (4): cuanto dependen los dias en alto de supuestos no publicados.
 - Roya: Tmin (SUPUESTO 8 C) frente a 10, 12 y 15 C (EPPO/DEFRA: 15-25 C) y la regla empirica decidida por el
   equipo (19-25 C con mojadura prolongada).
 - Botrytis: dias en alto que dependen de LWD > 32 h (fuera del rango experimental de Bulger, NO VERIFICADO).
 - Umbral de accion validado de Botrytis (0.50, MacKenzie y Peres 2012) frente a 'alto' (0.70, NCSU).
No modifica risk.py: cambia PARAMS_GIM solo en memoria.
Uso: .venv/bin/python -I -B reportes/verificacion-riesgo-clima_scripts/v4_sensibilidad_roya_botrytis.py
"""
import os
import sys
from collections import Counter
from dataclasses import replace

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "riesgo"))
import risk as r  # noqa: E402

PUNTOS = ("sotaquira", "tausa", "guasca", "chia")
cfg = r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.5)
base = r.PARAMS_GIM["roya"]
horas = {p: r.horas_desde_csv(os.path.join(RAIZ, "clima", "cache", "historico_2025_%s.csv" % p),
                              {"modelo": "best_match"}) for p in PUNTOS}

print("== Roya: dias medio/alto 2025 (HR>=90 o lluvia>=0.5) segun Tmin del GIM ==")
for tmin in (8.0, 10.0, 12.0, 15.0):
    r.PARAMS_GIM["roya"] = replace(base, t_min=tmin)
    fila = []
    for p in PUNTOS:
        c = Counter(d["clase_roya"] for d in r.resumen_diario(horas[p], cfg))
        fila.append("%s %d/%d" % (p, c["medio"], c["alto"]))
    print("Tmin=%4.1f  " % tmin + "  ".join(fila))
r.PARAMS_GIM["roya"] = base

print("\n== Roya, regla empirica del equipo: periodo con T media 19-25 C y >= 48 h mojadas (EPPO) o >= 24 h ==")
for p in PUNTOS:
    per = r.detectar_periodos(horas[p], cfg)
    n48 = sum(1 for x in per if 19 <= x.t_media <= 25 and x.horas_mojadas >= 48)
    n24 = sum(1 for x in per if 19 <= x.t_media <= 25 and x.horas_mojadas >= 24)
    n15 = sum(1 for x in per if 15 <= x.t_media <= 25 and x.horas_mojadas >= 24)
    tmax = max(x.t_media for x in per if x.horas_mojadas >= 12)
    print("%-10s periodos: %d; 19-25C>=48h: %d; 19-25C>=24h: %d; 15-25C>=24h: %d; T media maxima en periodos >=12 h: %.1f C"
          % (p, len(per), n48, n24, n15, tmax))

print("\n== Botrytis: dias en alto, dependencia de LWD > 32 h y umbral de accion 0.50 ==")
for p in PUNTOS:
    dias = r.resumen_diario(horas[p], cfg)
    alto = [d for d in dias if d["clase_botrytis"] == "alto"]
    ext = [d for d in alto if d.get("botrytis_lwd_h", 0) > r.BULGER_LWD_MAX]
    ge50 = [d for d in dias if d["idx_botrytis"] >= 0.50]
    print("%-10s alto(>=0.70): %d, de ellos con LWD>32 h: %d; dias >= 0.50 (umbral validado MacKenzie y Peres): %d"
          % (p, len(alto), len(ext), len(ge50)))
