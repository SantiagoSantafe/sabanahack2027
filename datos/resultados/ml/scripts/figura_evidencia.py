#!/usr/bin/env python
"""Figura de evidencia: sensibilidad y tasa de falsas alarmas con IC95 Clopper-Pearson (dos paneles, misma escala).

Los conteos k/n se leen de los metrics.json / ood_metrics.json citados abajo (nada escrito a mano).
Salida: resultados/ml/figuras/evidencia_sens_fp.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline"))
import metrics as M  # noqa: E402

R = D / "resultados" / "ml"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8984"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def b(p: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    x = json.loads((p / "metrics.json").read_text())["reglas"]["umbral"]["binario"]
    return (x["tp"], x["tp"] + x["fn"]), (x["fp"], x["fp"] + x["tn"])


def o(model: str, cat: str) -> tuple[int, int]:
    a = json.loads((R / "ood/eval" / model / "ood_metrics.json").read_text())["categorias"][cat]["alarma"]
    return a["k"], a["n"]


WI, WC = R / "drberry_image", R / "drberry_crops"
rows = [  # (etiqueta, sens(k,n), fp(k,n), color)
    ("Recorte de la lesión (cota superior)", *b(WC / "eval_clip_probe_test"), BLUE),
    ("Imagen completa: modelo final", *b(WI / "eval_clip_cv_tiles3_test"), BLUE),
    ("Imagen completa: candidato post-hoc", *b(WI / "eval_cruzado_crops_probe_test"), BLUE),
    ("Imagen completa: YOLO11n-cls 224", *b(WI / "eval_yolo224_test"), BLUE),
    ("Modelo final + estrés pantalla (sintético)", *b(R / "stress/eval/image_clip_cv_tiles3/combinada"), ORANGE),
    ("Campo iNaturalist: modelo final", o("image_clip_cv_tiles3", "campo_oidio"), o("image_clip_cv_tiles3", "campo_sana"), ORANGE),
    ("Campo iNaturalist: candidato post-hoc", o("cruzado_crops_probe_umbral_imagen", "campo_oidio"), o("cruzado_crops_probe_umbral_imagen", "campo_sana"), ORANGE),
    ("Split original CON FUGA (no usar)", *b(WI / "eval_clip_probe_split_original_test"), GRAY),
]

plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK})
fig, axes = plt.subplots(1, 2, figsize=(12, 4.9), sharey=True, gridspec_kw={"wspace": 0.22})
ys = list(range(len(rows)))[::-1]
for ax, idx, title in ((axes[0], 1, "Sensibilidad (enfermas con alerta; punteada = objetivo 90 %)"), (axes[1], 2, "Tasa de falsas alarmas (sanas con alerta)")):
    for y, r in zip(ys, rows):
        k, n = r[idx]
        p = k / n
        lo, hi = M.clopper_pearson(k, n)
        ax.plot([lo, hi], [y, y], color=r[3], lw=2, solid_capstyle="round", zorder=2)
        ax.scatter([p], [y], s=64, color=r[3], edgecolor="white", linewidth=2, zorder=3)
        ax.text(1.04, y, f"{k}/{n}", va="center", ha="left", color=INK2, fontsize=9, transform=ax.get_yaxis_transform())
    ax.set_xlim(-0.02, 1.02)
    ax.set_title(title, loc="left", color=INK, fontsize=10.5)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25 %", "50 %", "75 %", "100 %"])
axes[0].axvline(0.90, color=INK2, lw=1, ls=(0, (3, 3)), zorder=1)
axes[0].set_yticks(ys)
axes[0].set_yticklabels([r[0] for r in rows])
handles = [plt.Line2D([], [], marker="o", color=c, lw=2, markersize=7, label=l) for c, l in
           ((BLUE, "DrBerry, test congelado (68 imágenes, 21 grupos; recortes: 101)"), (ORANGE, "Fuera de DrBerry (estrés sintético o fotos de campo; oídio y hojas sanas)"),
            (GRAY, "Split original de Roboflow con fuga"))]
fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.04))
fig.suptitle("Clasificador de hojas de arándano: punto ± IC95 Clopper-Pearson (k/n a la derecha)", x=0.01, ha="left", color=INK, fontsize=11.5)
out = R / "figuras" / "evidencia_sens_fp.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="#fcfcfb")
print(out)
