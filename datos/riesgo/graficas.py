"""
graficas.py -- Figuras de evidencia de los modelos de riesgo (PNG en riesgo/graficas/).

    /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
        /Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/graficas.py

1. curvas_antracnosis_arandano.png: indice vs horas de mojadura a 10/15/20/25 C. Ecuacion de fresa
   (Wilson 1990, usada por SAS/BAS) frente a la aproximacion calibrada en arandano, con la franja de
   horas en que Gillett & Schilder 2009 vieron "aumento considerable" de infeccion en arandano.
2. riesgo_diario_2025.png: clase diaria (bajo/medio/alto) en 2025 por punto y enfermedad, criterio
   central de mojadura (HR >= 90 % o lluvia >= 0.5 mm/h). Requiere correr antes correr_2025.py.
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import risk as r  # noqa: E402

OUT = os.path.join(AQUI, "graficas")
SAL = os.path.join(AQUI, "salidas")

SURFACE = "#fcfcfb"
TEXT1, TEXT2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e4e3df"
SERIE1, SERIE2 = "#2a78d6", "#eb6834"      # paleta categorica validada (slots 1 y 2)
BAJO, MEDIO, ALTO = "#f0efec", "#86b6ef", "#104281"   # neutro + rampa ordinal azul validada

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "text.color": TEXT1, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
})


def curvas():
    lwd = [x / 4 for x in range(0, 4 * 60 + 1)]
    bandas = {10: (36, 48), 15: (24, 24), 20: (12, 18), 25: (12, 18)}
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.8), sharey=True)
    for ax, T in zip(axes, (10, 15, 20, 25)):
        lo, hi = bandas[T]
        ax.axvspan(lo - (0.4 if lo == hi else 0), hi + (0.4 if lo == hi else 0), color=GRID, lw=0, zorder=0)
        ax.text((lo + hi) / 2, 1.02, "arándano:\n%s h" % (("%d" % lo) if lo == hi else "%d–%d" % (lo, hi)),
                ha="center", va="bottom", fontsize=8, color=TEXT2)
        for y in r.UMBRALES["antracnosis"]:
            ax.axhline(y, color=MUTED, lw=1, zorder=1)
        w = [r.indice_antracnosis_wilson(x, T) for x in lwd]
        a = [r.indice_antracnosis_arandano_aprox(x, T) for x in lwd]
        ax.plot(lwd, w, color=SERIE1, lw=2, solid_capstyle="round", zorder=3)
        ax.plot(lwd, a, color=SERIE2, lw=2, solid_capstyle="round", zorder=3)
        ax.set_title("%d °C" % T, loc="left")
        ax.set_xlim(0, 60)
        ax.set_ylim(0, 1.18)
        ax.set_yticks([0, 0.15, 0.5, 1.0])
        ax.set_xticks([0, 12, 24, 36, 48, 60])
        ax.set_xlabel("horas de mojadura (LWD)")
        ax.grid(axis="x", color=GRID, lw=1)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("índice de infección (0–1)")
    axes[0].text(59, 0.16, "medio", ha="right", va="bottom", fontsize=8, color=TEXT2)
    axes[0].text(59, 0.51, "alto", ha="right", va="bottom", fontsize=8, color=TEXT2)
    leg = [plt.Line2D([0], [0], color=SERIE1, lw=2, label="Wilson et al. 1990 (fresa; ecuación de SAS y BAS)"),
           plt.Line2D([0], [0], color=SERIE2, lw=2, label="Aproximación arándano (anclada en Gillett & Schilder 2009)"),
           Patch(color=GRID, label="horas con aumento considerable de infección en arándano (Gillett & Schilder 2009)")]
    fig.legend(handles=leg, loc="lower center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Antracnosis: índice según horas de mojadura y temperatura media del periodo",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    ruta = os.path.join(OUT, "curvas_antracnosis_arandano.png")
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def mapa_diario():
    puntos = ("chia", "guasca", "sotaquira", "tausa")
    enfs = ("antracnosis", "botrytis", "roya", "oidio")
    etiquetas = {"antracnosis": "Antracnosis", "botrytis": "Botrytis", "roya": "Roya", "oidio": "Oídio"}
    cmap = ListedColormap([BAJO, MEDIO, ALTO])
    fig, axes = plt.subplots(len(puntos), 1, figsize=(13, 7.2), sharex=True)
    for ax, p in zip(axes, puntos):
        ruta = os.path.join(SAL, "riesgo_2025_%s_diario.csv" % p)
        filas = list(csv.DictReader(open(ruta, encoding="utf-8")))
        m = [[r.CLASES.index(f["clase_" + e]) for f in filas] for e in enfs]
        ax.imshow(m, aspect="auto", cmap=cmap, vmin=0, vmax=2, interpolation="nearest")
        ax.set_yticks(range(len(enfs)))
        ax.set_yticklabels(["%s  %d/%d" % (etiquetas[e], sum(1 for f in filas if f["clase_" + e] == "medio"),
                                           sum(1 for f in filas if f["clase_" + e] == "alto")) for e in enfs],
                           fontsize=8.5)
        ax.set_title(p.capitalize(), loc="left", fontsize=10)
        for y in range(len(enfs) - 1):
            ax.axhline(y + 0.5, color=SURFACE, lw=2)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    meses = [date(2025, m, 1).timetuple().tm_yday - 1 for m in range(1, 13)]
    axes[-1].set_xticks(meses)
    axes[-1].set_xticklabels(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])
    leg = [Patch(color=BAJO, label="bajo"), Patch(color=MEDIO, label="medio"), Patch(color=ALTO, label="alto")]
    fig.legend(handles=leg, loc="lower center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.005))
    fig.suptitle("Riesgo ambiental diario 2025 (Open-Meteo; mojadura = HR ≥ 90 % o lluvia ≥ 0,5 mm/h). "
                 "Junto a cada enfermedad: días medio/alto",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    ruta = os.path.join(OUT, "riesgo_diario_2025.png")
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print(curvas())
    print(mapa_diario())
