"""
correr_2025.py -- Aplica riesgo/risk.py al clima horario 2025 (Open-Meteo, clima/derivados) de los
4 puntos y deja tablas de evidencia en riesgo/salidas/.

    /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
        /Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/correr_2025.py

Salidas:
  salidas/riesgo_2025_<punto>_eventos.csv     periodos de mojadura (criterio central HR>=90 o lluvia>=0.5 mm/h) con indices
  salidas/riesgo_2025_<punto>_diario.csv      resumen diario (indice maximo y clase por enfermedad)
  salidas/resumen_dias_por_clase_2025.csv     dias bajo/medio/alto por punto, criterio de mojadura y enfermedad
  salidas/riesgo_mensual_2025.csv             dias en alto por mes (criterio central)
  salidas/comparacion_modelos_antracnosis_2025.csv  dias en medio/alto con Wilson solo vs envolvente
  salidas/estadisticas_eventos_2025.csv       duracion y T media de los periodos de mojadura
  salidas/alertas_por_periodo_2025.csv        periodos de mojadura que llegan a medio/alto (= alertas/anio)
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import risk as r  # noqa: E402

RAIZ = os.path.dirname(AQUI)
DER = os.path.join(RAIZ, "clima", "derivados")
SAL = os.path.join(AQUI, "salidas")
PUNTOS = ("chia", "guasca", "sotaquira", "tausa")

# Criterios de mojadura (ver reportes/clima-open-meteo.md, calibracion IDEAM vs Open-Meteo):
#   HR90_P05 = escenario central (por defecto en risk.py); HR85_P05 = escenario de alerta (sensibilidad ~0.9).
CRITERIOS = {
    "HR85_P05": r.ConfigMojadura(umbral_hr=85, umbral_lluvia_mm=0.5),
    "HR90_P05": r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.5),
    "HR95_P05": r.ConfigMojadura(umbral_hr=95, umbral_lluvia_mm=0.5),
    "HR90_P0": r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.1),
    "LWP50": r.ConfigMojadura(usar_hr=False, usar_lwp=True, umbral_lwp=50, umbral_lluvia_mm=1e9),
}
CENTRAL = "HR90_P05"


def _pct(vals, q):
    v = sorted(vals)
    if not v:
        return None
    k = (len(v) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 2)


def main():
    os.makedirs(SAL, exist_ok=True)
    resumen, mensual, comp, stats, alertas = [], [], [], [], []
    for p in PUNTOS:
        ruta = os.path.join(DER, "hoja_mojada_horaria_%s.csv" % p)
        if not os.path.exists(ruta):
            print("falta", ruta)
            continue
        horas = r.horas_desde_csv(ruta)
        for nombre, cfg in CRITERIOS.items():
            dias = r.resumen_diario(horas, cfg)
            eventos = r.evaluar_eventos(horas, cfg)
            for enf in r.ENFERMEDADES:
                c = Counter(d["clase_" + enf] for d in dias)
                resumen.append({"punto": p, "criterio_mojadura": nombre, "enfermedad": enf, "dias": len(dias),
                                "dias_bajo": c["bajo"], "dias_medio": c["medio"], "dias_alto": c["alto"],
                                "pct_dias_medio_o_alto": round(100 * (c["medio"] + c["alto"]) / len(dias), 1),
                                "pct_dias_alto": round(100 * c["alto"] / len(dias), 1)})
            lwd = [e["horas_mojadas"] for e in eventos]
            tm = [e["t_media_mojada"] for e in eventos if e["t_media_mojada"] is not None]
            stats.append({"punto": p, "criterio_mojadura": nombre, "n_periodos": len(eventos),
                          "horas_mojadas_anio": sum(lwd), "lwd_mediana_h": _pct(lwd, 0.5),
                          "lwd_p90_h": _pct(lwd, 0.9), "lwd_max_h": max(lwd) if lwd else None,
                          "t_media_mojada_mediana_C": _pct(tm, 0.5), "t_media_mojada_p10_C": _pct(tm, 0.1),
                          "t_media_mojada_p90_C": _pct(tm, 0.9),
                          "pct_periodos_fuera_rango_bulger": round(
                              100 * sum(e["botrytis_fuera_de_rango"] for e in eventos) / max(1, len(eventos)), 1)})
            for enf in ("antracnosis", "botrytis", "roya"):
                c = Counter(e["clase_" + enf] for e in eventos)
                alertas.append({"punto": p, "criterio_mojadura": nombre, "enfermedad": enf,
                                "periodos_mojadura": len(eventos), "periodos_medio": c["medio"],
                                "periodos_alto": c["alto"],
                                "periodos_alto_por_mes": round(c["alto"] / 12.0, 1)})
            if nombre == CENTRAL:
                r.escribir_csv(eventos, os.path.join(SAL, "riesgo_2025_%s_eventos.csv" % p))
                r.escribir_csv(dias, os.path.join(SAL, "riesgo_2025_%s_diario.csv" % p))
                pm = defaultdict(Counter)
                for d in dias:
                    for enf in r.ENFERMEDADES:
                        pm[(d["fecha"].month, enf)][d["clase_" + enf]] += 1
                for (mes, enf), c in sorted(pm.items()):
                    mensual.append({"punto": p, "mes": mes, "enfermedad": enf, "dias_medio": c["medio"],
                                    "dias_alto": c["alto"]})
                for modelo in ("wilson", "arandano_aprox", "envolvente", "gim"):
                    dm = r.resumen_diario(horas, cfg, modelo_antracnosis=modelo)
                    c = Counter(d["clase_antracnosis"] for d in dm)
                    comp.append({"punto": p, "modelo_antracnosis": modelo, "dias_bajo": c["bajo"],
                                 "dias_medio": c["medio"], "dias_alto": c["alto"]})
        print("ok", p)
    r.escribir_csv(resumen, os.path.join(SAL, "resumen_dias_por_clase_2025.csv"))
    r.escribir_csv(mensual, os.path.join(SAL, "riesgo_mensual_2025.csv"))
    r.escribir_csv(comp, os.path.join(SAL, "comparacion_modelos_antracnosis_2025.csv"))
    r.escribir_csv(stats, os.path.join(SAL, "estadisticas_eventos_2025.csv"))
    r.escribir_csv(alertas, os.path.join(SAL, "alertas_por_periodo_2025.csv"))


if __name__ == "__main__":
    main()
