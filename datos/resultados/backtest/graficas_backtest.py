"""
graficas_backtest.py -- Graficas PNG (16:9, para diapositiva) a partir de los CSV de backtest_riesgo.py.

    /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
        /Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/backtest/graficas_backtest.py

Paleta: paleta de referencia del skill dataviz (validada con scripts/validate_palette.js):
  secuencial azul 100-650 (heatmap), rampa ordinal azul 250/450/650 (umbral HR, --ordinal PASS),
  categoricos 1-3 (#2a78d6, #eb6834, #1baf7a; PASS), estado: medio = warning #fab219, alto = critical #d03b3b
  (siempre con etiqueta en la leyenda).
"""
from __future__ import annotations

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.colors as mcolors  # noqa: E402
import pandas as pd  # noqa: E402

warnings.filterwarnings("ignore")
AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "graficas")
os.makedirs(OUT, exist_ok=True)

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SEQ = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#104281"]
ORD = {"HR85": "#104281", "HR90": "#2a78d6", "HR95": "#86b6ef"}
CAT = ["#2a78d6", "#eb6834", "#1baf7a"]
MEDIO, ALTO, BAJO = "#fab219", "#d03b3b", "#e9e8e3"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
ENF = ["antracnosis", "botrytis", "roya"]
ENF_TXT = {"antracnosis": "Antracnosis", "botrytis": "Botrytis", "roya": "Roya"}
PUNTOS = ["sotaquira", "tausa", "guasca", "chia"]
PT_TXT = {"sotaquira": "Sotaquirá (182 ha)", "tausa": "Tausa (121 ha)", "guasca": "Guasca (57 ha)",
          "chia": "Chía (demo)"}
PIE = ("Weather data by Open-Meteo.com (CC BY 4.0), horario 2025, best_match · modelos: riesgo/risk.py · "
       "Índice ambiental, sin validación con incidencia de campo.")

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.facecolor": SURF, "figure.facecolor": SURF, "savefig.facecolor": SURF, "axes.titlecolor": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
})


def _titulo(fig, t, sub=None, pie=PIE):
    fig.text(0.015, 0.975, t, fontsize=17, fontweight="bold", color=INK, va="top")
    if sub:
        fig.text(0.015, 0.925, sub, fontsize=11, color=INK2, va="top")
    if pie:
        fig.text(0.015, 0.012, pie, fontsize=8.5, color=MUTED, va="bottom")


def _guardar(fig, nombre):
    ruta = os.path.join(OUT, nombre)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    print("->", ruta)


def _luminancia(hexc):
    r, g, b = mcolors.to_rgb(hexc)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ------------------------------------------------------------------ G1 heatmap dias alto por mes
def g1_heatmap(m):
    c = m[m.criterio == "HR90"]
    cmap = mcolors.ListedColormap(SEQ)
    norm = mcolors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 99], cmap.N)
    fig, axs = plt.subplots(3, 1, figsize=(12.8, 7.2), gridspec_kw={"hspace": 0.55})
    fig.subplots_adjust(left=0.15, right=0.9, top=0.84, bottom=0.08)
    for ax, enf in zip(axs, ENF):
        piv = c[c.enfermedad == enf].pivot_table(index="punto", columns="mes", values="dias_alto").reindex(PUNTOS)
        ax.imshow(piv.values, cmap=cmap, norm=norm, aspect="auto")
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = int(piv.values[i, j])
                col = SEQ[min(v, 7)]
                ax.text(j, i, str(v) if v else "·", ha="center", va="center", fontsize=10,
                        color=("#ffffff" if _luminancia(col) < 0.45 else (INK if v else MUTED)))
        ax.set_xticks(range(12))
        ax.set_xticklabels(MESES if enf == "roya" else [""] * 12)
        ax.set_yticks(range(4))
        ax.set_yticklabels([PT_TXT[p] for p in PUNTOS], color=INK2)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xticks([x - 0.5 for x in range(1, 12)], minor=True)
        ax.set_yticks([y - 0.5 for y in range(1, 4)], minor=True)
        ax.grid(which="minor", color=SURF, linewidth=2)
        ax.tick_params(which="both", length=0)
        tot = c[c.enfermedad == enf].groupby("punto")["dias_alto"].sum().reindex(PUNTOS)
        ax.set_title(ENF_TXT[enf], loc="left", fontsize=12.5, fontweight="bold", color=INK, pad=6)
        ax.text(12.0, -0.85, "total año", ha="left", fontsize=9, color=MUTED)
        for i, p in enumerate(PUNTOS):
            ax.text(12.0, i, "%d" % tot[p], va="center", ha="left", fontsize=10, color=INK2)
    _titulo(fig, "Días de riesgo ALTO por mes, 2025",
            "Hoja mojada = HR ≥ 90 % o lluvia ≥ 0,5 mm/h (criterio central). El riesgo se concentra en feb–may y "
            "repunta en ago y oct.")
    _guardar(fig, "g1_heatmap_dias_alto_mensual_2025.png")


# ------------------------------------------------------------------ G2 columnas medio/alto por mes
def _panel_mensual(ax, d, enf, ymax, titulo=True, ylab=True):
    x = list(range(1, 13))
    a = d.set_index("mes").reindex(x)["dias_alto"].fillna(0)
    me = d.set_index("mes").reindex(x)["dias_medio"].fillna(0)
    w = 0.62
    ax.bar(x, a, width=w, color=ALTO, label="alto", zorder=3)
    ax.bar(x, me, width=w, bottom=a + (a > 0) * 0.12, color=MEDIO, label="medio", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([mm[0] for mm in MESES], fontsize=9)
    ax.set_ylim(0, ymax)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    if titulo:
        ax.set_title("%s · %d alto / %d medio" % (ENF_TXT[enf], a.sum(), me.sum()), loc="left", fontsize=11.5,
                     color=INK)
    if ylab:
        ax.set_ylabel("días en el mes")


def g2_mensual(m):
    c = m[m.criterio == "HR90"]
    ymax = (c.dias_alto + c.dias_medio).max() + 1.5
    for p in PUNTOS:
        fig, axs = plt.subplots(1, 3, figsize=(12.8, 7.2), sharey=True)
        fig.subplots_adjust(left=0.06, right=0.98, top=0.78, bottom=0.12, wspace=0.08)
        for k, (ax, enf) in enumerate(zip(axs, ENF)):
            _panel_mensual(ax, c[(c.punto == p) & (c.enfermedad == enf)], enf, ymax, ylab=(k == 0))
        h, l = axs[0].get_legend_handles_labels()
        fig.legend(h, ["riesgo alto", "riesgo medio"], loc="upper right", bbox_to_anchor=(0.98, 0.9), ncol=2,
                   frameon=False, fontsize=10)
        _titulo(fig, "%s: días de riesgo medio y alto por mes, 2025" % PT_TXT[p],
                "Hoja mojada = HR ≥ 90 % o lluvia ≥ 0,5 mm/h. Días restantes = bajo.")
        _guardar(fig, "g2_mensual_medio_alto_%s.png" % p)
    fig, axs = plt.subplots(3, 4, figsize=(12.8, 7.2), sharey=True, sharex=True)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.77, bottom=0.08, wspace=0.08, hspace=0.45)
    for i, enf in enumerate(ENF):
        for j, p in enumerate(PUNTOS):
            ax = axs[i, j]
            d = c[(c.punto == p) & (c.enfermedad == enf)]
            _panel_mensual(ax, d, enf, ymax, titulo=False, ylab=(j == 0))
            ax.set_title("%s · %d alto" % (ENF_TXT[enf], d.dias_alto.sum()), loc="left", fontsize=10, color=INK)
            if i == 0:
                ax.text(0.0, 1.3, PT_TXT[p], transform=ax.transAxes, fontsize=11.5, fontweight="bold", color=INK)
            if j > 0:
                ax.set_ylabel("")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, ["riesgo alto", "riesgo medio"], loc="upper right", bbox_to_anchor=(0.985, 0.975), ncol=2,
               frameon=False, fontsize=10)
    _titulo(fig, "Días de riesgo medio y alto por mes, 2025, por punto y enfermedad",
            "Criterio central de hoja mojada (HR ≥ 90 % o lluvia ≥ 0,5 mm/h)")
    _guardar(fig, "g2_mensual_medio_alto_todos.png")


# ------------------------------------------------------------------ G3 sensibilidad al umbral de HR
def g3_sensibilidad(s):
    fig, axs = plt.subplots(1, 3, figsize=(12.8, 7.2), sharey=True)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.76, bottom=0.14, wspace=0.08)
    w = 0.26
    ymax = s[["dias_alto_HR85"]].values.max() * 1.15
    for ax, enf in zip(axs, ENF):
        d = s[s.enfermedad == enf].set_index("punto").reindex(PUNTOS)
        for k, crit in enumerate(["HR85", "HR90", "HR95"]):
            xs = [i + (k - 1) * (w + 0.02) for i in range(4)]
            vals = d["dias_alto_" + crit].values
            ax.bar(xs, vals, width=w, color=ORD[crit], zorder=3,
                   label={"HR85": "HR ≥ 85 % (alerta)", "HR90": "HR ≥ 90 % (central)", "HR95": "HR ≥ 95 %"}[crit])
            for x, v in zip(xs, vals):
                ax.text(x, v + ymax * 0.012, str(int(v)), ha="center", va="bottom", fontsize=9, color=INK2)
        tot = {c: int(d["dias_alto_" + c].sum()) for c in ("HR85", "HR90", "HR95")}
        ax.set_title("%s · total 4 puntos: %d / %d / %d" % (ENF_TXT[enf], tot["HR85"], tot["HR90"], tot["HR95"]),
                     loc="left", fontsize=11.5, color=INK)
        ax.set_xticks(range(4))
        ax.set_xticklabels([PT_TXT[p].split(" (")[0] for p in PUNTOS], fontsize=10)
        ax.set_ylim(0, ymax)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.tick_params(length=0)
        ax.spines["left"].set_visible(False)
    axs[0].set_ylabel("días en alto en 2025")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", bbox_to_anchor=(0.98, 0.875), ncol=3, frameon=False, fontsize=10)
    _titulo(fig, "Sensibilidad al umbral de hoja mojada: días en alto por año",
            "Siempre con lluvia ≥ 0,5 mm/h. Bajar de 90 % a 85 % multiplica los días en alto por 2–4; "
            "subir a 95 % los reduce a casi cero.")
    _guardar(fig, "g3_sensibilidad_umbral_hr.png")


# ------------------------------------------------------------------ G4 serie diaria: lluvia vs clase de riesgo
def g4_serie(p):
    d = pd.read_csv(os.path.join(AQUI, "diario_%s_HR90.csv" % p), parse_dates=["fecha"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.8, 7.2), sharex=True, gridspec_kw={"height_ratios": [1.5, 1]})
    fig.subplots_adjust(left=0.1, right=0.98, top=0.78, bottom=0.1, hspace=0.12)
    secas = [("2025-01-01", "2025-03-01"), ("2025-06-01", "2025-09-01"), ("2025-12-01", "2026-01-01")]
    for ax in (a1, a2):
        for i0, i1 in secas:
            ax.axvspan(pd.Timestamp(i0), pd.Timestamp(i1), color="#f3f2ee", zorder=0, lw=0)
    a1.bar(d.fecha, d.lluvia_om_mm, width=0.8, color=CAT[0], zorder=3, label="lluvia Open-Meteo")
    a1.set_ylabel("lluvia diaria (mm)")
    a1.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=1)
    a1.spines["left"].set_visible(False)
    a1.tick_params(length=0)
    a1.text(pd.Timestamp("2025-01-03"), a1.get_ylim()[1] * 0.92, "temporada seca", fontsize=9, color=MUTED)
    a1.text(pd.Timestamp("2025-03-03"), a1.get_ylim()[1] * 0.92, "temporada lluviosa", fontsize=9, color=MUTED)
    col = {"bajo": BAJO, "medio": MEDIO, "alto": ALTO}
    for i, enf in enumerate(ENF[::-1]):
        a2.bar(d.fecha, [0.8] * len(d), bottom=i + 0.1, width=1.0, color=[col[c] for c in d["clase_" + enf]],
               zorder=3, linewidth=0)
    a2.set_yticks([0.5, 1.5, 2.5])
    a2.set_yticklabels([ENF_TXT[e] for e in ENF[::-1]], color=INK2)
    a2.set_ylim(0, 3)
    a2.tick_params(length=0)
    for s in ("left", "bottom"):
        a2.spines[s].set_visible(False)
    a2.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
    a2.set_xticks(pd.date_range("2025-01-01", "2025-12-01", freq="MS"))
    a2.set_xticklabels(MESES)
    a2.set_xlim(pd.Timestamp("2024-12-31"), pd.Timestamp("2026-01-01"))
    from matplotlib.patches import Patch
    fig.legend([Patch(color=BAJO), Patch(color=MEDIO), Patch(color=ALTO)], ["bajo", "medio", "alto"],
               loc="upper right", bbox_to_anchor=(0.98, 0.86), ncol=3, frameon=False, fontsize=10,
               title="clase de riesgo del día", title_fontsize=9)
    _titulo(fig, "Prueba de cordura, %s: lluvia diaria y clase de riesgo, 2025" % PT_TXT[p],
            "Los días en alto caen en rachas lluviosas y las semanas secas quedan en bajo, pero no toda racha lluviosa "
            "llega a alto.\nFranjas grises = temporadas secas (dic–feb, jun–ago) según reportes/ciencia-enfermedades.md.")
    _guardar(fig, "g4_cordura_serie_%s.png" % p)


# ------------------------------------------------------------------ G5 concordancia estacion vs Open-Meteo
def g5_concordancia(c):
    sel = c[(c.referencia == "est_HR90_P>0") & (c.criterio_om == "HR85") & (c.alerta_om_si == "medio_o_alto")]
    g = sel.groupby("punto")[["dias_alto_estacion", "VP_ventana_72h", "FP_con_estacion_en_bajo"]].sum()
    est = {"chia": "U. de La Sabana (Chía)", "tausa": "Cucunubá (Tausa, 12 km)", "sotaquira": "Duitama (Sotaquirá, 22 km)"}
    orden = ["chia", "tausa", "sotaquira"]
    g = g.reindex(orden)
    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.24, right=0.95, top=0.74, bottom=0.14)
    h = 0.32
    for i, p in enumerate(orden):
        det = g.loc[p, "VP_ventana_72h"]
        tot = g.loc[p, "dias_alto_estacion"]
        nod = tot - det
        fa = g.loc[p, "FP_con_estacion_en_bajo"]
        y = i
        ax.barh(y - h / 2 - 0.02, det, height=h, color=CAT[0], zorder=3, label="detectados por Open-Meteo (±1 día)" if i == 0 else None)
        ax.barh(y - h / 2 - 0.02, nod, left=det + (0.25 if det else 0), height=h, color=CAT[1], zorder=3,
                label="no detectados" if i == 0 else None)
        ax.text(det + nod + 1.2, y - h / 2 - 0.02, "%d de %d días en alto según la estación" % (det, tot),
                va="center", fontsize=10, color=INK2)
        ax.barh(y + h / 2 + 0.02, fa, height=h, color=CAT[2], zorder=3,
                label="alertas de Open-Meteo con la estación en bajo" if i == 0 else None)
        ax.text(fa + 1.2, y + h / 2 + 0.02, "%d falsas alarmas relativas" % fa, va="center", fontsize=10, color=INK2)
    ax.set_xlim(0, max(g.max()) * 1.35)
    ax.set_yticks(range(3))
    ax.set_yticklabels([est[p] for p in orden], color=INK, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("días-enfermedad (antracnosis + Botrytis + roya, días con 24 h de datos)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.2), ncol=3, frameon=False, fontsize=10)
    _titulo(fig, "¿Cuánto riesgo real ve el sistema con clima de modelo? Estación IDEAM vs Open-Meteo, 2025",
            "Referencia: modelos de riesgo con datos de estación (HR ≥ 90 % o lluvia > 0). Sistema: Open-Meteo en "
            "las coordenadas de la estación,\nalerta si medio o alto con HR ≥ 85 %. Mide error de entrada, no "
            "enfermedad.",
            pie="IDEAM vía datos.gov.co (CC BY-SA 4.0; hora UTC corregida a −5 h) · Weather data by Open-Meteo.com "
                "(CC BY 4.0) · riesgo/risk.py · Concordancia de entrada; sin datos de incidencia.")
    _guardar(fig, "g5_concordancia_estacion_vs_openmeteo.png")


def main():
    m = pd.read_csv(os.path.join(AQUI, "dias_riesgo_mensual_2025.csv"))
    s = pd.read_csv(os.path.join(AQUI, "sensibilidad_umbral_hr.csv"))
    c = pd.read_csv(os.path.join(AQUI, "concordancia_estacion_vs_openmeteo.csv"))
    g1_heatmap(m)
    g2_mensual(m)
    g3_sensibilidad(s)
    for p in ("chia", "tausa", "sotaquira"):
        g4_serie(p)
    g5_concordancia(c)


if __name__ == "__main__":
    main()
