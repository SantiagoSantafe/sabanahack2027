"""
robustez_backtest.py -- Robustez de los dias de riesgo ALTO 2025 (criterio central HR>=90 o lluvia>=0.5 mm/h)
frente a (a) error de temperatura de entrada +-1 C (MAE Open-Meteo vs IDEAM 1.2-1.6 C, reportes/clima-open-meteo.md),
(b) umbral de alerta de Botrytis en 0.50 (unico validado en campo, MacKenzie y Peres 2012b, citado en riesgo/README.md)
y (c) Tmin del GIM de roya (8 C es SUPUESTO; 15 C = limite inferior EPPO/DEFRA citado en risk.py).
Responde a reportes/verificacion-riesgo-clima.md (secciones 5.1, 5.3 y 5.4). No modifica risk.py.

    /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
        /Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/backtest/robustez_backtest.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(RAIZ, "riesgo"))
sys.path.insert(0, AQUI)
import risk as r  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import graficas_backtest as G  # noqa: E402  (paleta y estilo validados)

PUNTOS = ("sotaquira", "tausa", "guasca", "chia")
ENF = ("antracnosis", "botrytis", "roya")
CFG = r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.5)


def cargar(p):
    return r.horas_desde_csv(os.path.join(RAIZ, "clima", "cache", "historico_2025_%s.csv" % p), {"modelo": "best_match"})


def dias(horas):
    return r.resumen_diario(horas, CFG)


def main():
    filas = []
    base_h = {p: cargar(p) for p in PUNTOS}
    for p in PUNTOS:
        res = {}
        for nombre, dt in (("T-1C", -1.0), ("base", 0.0), ("T+1C", 1.0)):
            hs = base_h[p] if dt == 0 else [replace(h, T=h.T + dt) for h in base_h[p]]
            res[nombre] = dias(hs)
        for esc, d in res.items():
            for e in ENF:
                filas.append({"punto": p, "escenario": esc, "enfermedad": e,
                              "dias_alto": sum(1 for x in d if x["clase_" + e] == "alto"),
                              "dias_medio_o_alto": sum(1 for x in d if x["clase_" + e] != "bajo")})
        d0 = res["base"]
        filas.append({"punto": p, "escenario": "botrytis_alerta_desde_0.50", "enfermedad": "botrytis",
                      "dias_alto": sum(1 for x in d0 if x["idx_botrytis"] >= 0.50),
                      "dias_medio_o_alto": sum(1 for x in d0 if x["idx_botrytis"] >= 0.50)})
    # (c) Tmin de roya: se cambia temporalmente PARAMS_GIM['roya'] y se restaura.
    orig = r.PARAMS_GIM["roya"]
    try:
        for tmin in (10.0, 12.0, 15.0):
            r.PARAMS_GIM["roya"] = replace(orig, t_min=tmin)
            for p in PUNTOS:
                d = dias(base_h[p])
                filas.append({"punto": p, "escenario": "roya_tmin_%g" % tmin, "enfermedad": "roya",
                              "dias_alto": sum(1 for x in d if x["clase_roya"] == "alto"),
                              "dias_medio_o_alto": sum(1 for x in d if x["clase_roya"] != "bajo")})
    finally:
        r.PARAMS_GIM["roya"] = orig
    ruta = os.path.join(AQUI, "robustez_dias_alto_2025.csv")
    r.escribir_csv(filas, ruta)
    print("->", ruta)
    # resumen: suma 4 puntos
    tot = {}
    for f in filas:
        k = (f["escenario"], f["enfermedad"])
        tot[k] = tot.get(k, 0) + f["dias_alto"]
    for k in sorted(tot):
        print("  %-28s %-12s %d" % (k[0], k[1], tot[k]))
    grafica(filas)


def grafica(filas):
    col = {"T-1C": G.ORD["HR95"], "base": G.ORD["HR90"], "T+1C": G.ORD["HR85"]}
    lab = {"T-1C": "T − 1 °C", "base": "Clima Open-Meteo (publicado)", "T+1C": "T + 1 °C"}
    fig, axs = plt.subplots(1, 3, figsize=(12.8, 7.2), sharey=True)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.76, bottom=0.14, wspace=0.08)
    w = 0.26
    ymax = max(f["dias_alto"] for f in filas if f["escenario"] in col) * 1.15
    for ax, e in zip(axs, ENF):
        tots = {}
        for k, esc in enumerate(("T-1C", "base", "T+1C")):
            vals = [next(f["dias_alto"] for f in filas if f["punto"] == p and f["escenario"] == esc
                         and f["enfermedad"] == e) for p in PUNTOS]
            tots[esc] = sum(vals)
            xs = [i + (k - 1) * (w + 0.02) for i in range(4)]
            ax.bar(xs, vals, width=w, color=col[esc], zorder=3, label=lab[esc])
            for x, v in zip(xs, vals):
                ax.text(x, v + ymax * 0.012, str(v), ha="center", va="bottom", fontsize=9, color=G.INK2)
        ax.set_title("%s · total 4 puntos: %d – %d – %d" % (G.ENF_TXT[e], tots["T-1C"], tots["base"], tots["T+1C"]),
                     loc="left", fontsize=11.5, color=G.INK)
        ax.set_xticks(range(4))
        ax.set_xticklabels([G.PT_TXT[p].replace(" (", "\n(") for p in PUNTOS], fontsize=9.5, color=G.INK2)
        ax.set_ylim(0, ymax)
        ax.yaxis.grid(True, color=G.GRID, zorder=0)
        ax.tick_params(length=0)
    axs[0].set_ylabel("Días en riesgo alto, 2025")
    axs[0].legend(loc="upper left", frameon=False, fontsize=9.5)
    G._titulo(fig, "Robustez: un error de ±1 °C en el clima cambia mucho los días en alto",
              "Error medio de temperatura de Open-Meteo frente al IDEAM: 1,2–1,6 °C. Los conteos se presentan como rango, "
              "no como cifra exacta.\nHoja mojada = HR ≥ 90 % o lluvia ≥ 0,5 mm/h.")
    G._guardar(fig, "g6_robustez_temperatura.png")


if __name__ == "__main__":
    main()
