#!/usr/bin/env python
"""Elige el umbral de "sospecha" sobre VALIDACIÓN para una sensibilidad de enfermedad >= objetivo.

Puntaje = ``1 - p(sana)``; sospecha si puntaje >= umbral. Se busca, entre los umbrales que cumplen
el objetivo (por defecto 0.90), el que produce el MÍNIMO de falsas alarmas.
Si varios umbrales empatan en ese mínimo de falsas alarmas en validación, por defecto se toma el
más bajo del empate (``--tie-break sensibilidad``): misma cantidad de falsas alarmas en validación
y más margen contra los casos no detectados. El equipo prefiere falsas alarmas (~30 USD, SUPUESTO del equipo) a casos no detectados
(~2.160 USD/ha/semana, SUPUESTO del equipo), por eso el criterio es de sensibilidad.

* ``--criterio global``: sensibilidad binaria enfermo-vs-sano >= objetivo.
* ``--criterio por_clase``: además, CADA enfermedad debe detectarse (como sospecha) en >= objetivo.
* ``--test-pred``: aplica el umbral ya fijado al test congelado SOLO para informar (no se re-ajusta).

Reporta la tasa de falsos positivos (FP/(FP+TN), sobre hojas sanas), la tasa de falsa alarma
(FP/(FP+TP), sobre alertas emitidas) y las alertas falsas por cada 100 inspecciones, con IC exacto.

Salidas: ``--out`` (threshold.json), ``<out>_curva.csv`` y ``<out>_curva.png``.

Ejemplo:
    .venv/bin/python -I pipeline/threshold.py --val-pred pipeline/work/drberry/clip/predicciones_probe_val.csv \
        --test-pred pipeline/work/drberry/clip/predicciones_probe_test.csv --out pipeline/work/drberry/clip/threshold_probe.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import metrics as M  # noqa: E402
from common import DEFAULT_HEALTHY, PROB_PREFIX, disease_scores, healthy_index, now_iso, read_predictions, sha256_file, write_csv, write_json  # noqa: E402


def _scores(path: str, healthy: str) -> tuple[pd.DataFrame, list[str], np.ndarray, np.ndarray]:
    df, classes = read_predictions(path)
    df = df[df["y_true"] != ""].reset_index(drop=True)
    probs = df[[f"{PROB_PREFIX}{c}" for c in classes]].to_numpy(float)
    s = disease_scores(probs, classes, healthy)
    hi = classes[healthy_index(classes, healthy)]
    y_pos = (df["y_true"] != hi).to_numpy()
    return df, classes, s, y_pos


def apply_threshold(y_pos: np.ndarray, scores: np.ndarray, thr: float, labels: Sequence[str] | None = None) -> dict[str, Any]:
    tp, fp, fn, tn = M.binary_counts(y_pos, scores >= thr)
    out: dict[str, Any] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, **M.binary_metrics(tp, fp, fn, tn),
                           "ic95_clopper_pearson": {"sensibilidad": list(M.clopper_pearson(tp, tp + fn)), "tasa_fp": list(M.clopper_pearson(fp, fp + tn)),
                                                    "tasa_falsa_alarma_fdr": list(M.clopper_pearson(fp, fp + tp))}}
    if labels is not None:
        lab = np.asarray(labels)
        out["deteccion_por_clase"] = {str(c): {"detectados": int((scores[lab == c] >= thr).sum()), "n": int((lab == c).sum()),
                                               "tasa": float((scores[lab == c] >= thr).mean())} for c in sorted(set(lab[y_pos]))}
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val-pred", required=True, help="Predicciones de VALIDACIÓN (aquí se fija el umbral)")
    ap.add_argument("--test-pred", default=None, help="Predicciones de test: solo se informa, no se ajusta")
    ap.add_argument("--out", required=True, help="Ruta de threshold.json")
    ap.add_argument("--target-sensitivity", type=float, default=0.90)
    ap.add_argument("--criterio", choices=["global", "por_clase"], default="global")
    ap.add_argument("--healthy-class", default=DEFAULT_HEALTHY)
    ap.add_argument("--tie-break", choices=["sensibilidad", "umbral_alto"], default="sensibilidad",
                    help="Entre umbrales con el mismo mínimo de falsas alarmas: el más bajo (más sensibilidad) o el más alto")
    ap.add_argument("--no-midpoint", action="store_true", help="Usar exactamente el puntaje observado como umbral")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out).resolve()
    df, classes, s, y_pos = _scores(args.val_pred, args.healthy_class)
    labels = df["y_true"].tolist()
    res = M.choose_threshold(y_pos, s, args.target_sensitivity, labels if args.criterio == "por_clase" else None,
                             midpoint=not args.no_midpoint, tie_break=args.tie_break)
    thr = float(res["umbral"])
    val_report = apply_threshold(y_pos, s, thr, labels)
    n_pos, n_neg = int(y_pos.sum()), int((~y_pos).sum())
    warnings = []
    if n_pos < 30:
        lo = M.clopper_pearson(val_report["tp"], n_pos)[0]
        warnings.append(f"Solo {n_pos} enfermos en validación: la sensibilidad real podría ser tan baja como {lo:.2f} (IC95 inferior)")
    if n_neg < 30:
        warnings.append(f"Solo {n_neg} sanas en validación: la tasa de FP es muy imprecisa")
    result: dict[str, Any] = {
        "creado": now_iso(),
        "umbral": thr,
        "puntaje": "1 - p(sana)",
        "regla": "sospecha si puntaje >= umbral; clase = enfermedad más probable",
        "objetivo_sensibilidad": args.target_sensitivity,
        "criterio": args.criterio,
        "desempate": args.tie_break,
        "clase_sana": args.healthy_class,
        "clases": classes,
        "elegido_en": {"archivo": str(Path(args.val_pred).resolve()), "sha256": sha256_file(args.val_pred), "n": int(len(df)), "n_enfermos": n_pos, "n_sanos": n_neg},
        "validacion": val_report,
        "umbral_puntaje_observado": res["umbral_puntaje_observado"],
        "avisos": warnings,
    }
    if args.test_pred:
        tdf, _, ts, ty = _scores(args.test_pred, args.healthy_class)
        result["test_informativo"] = {"archivo": str(Path(args.test_pred).resolve()), "sha256": sha256_file(args.test_pred), "n": int(len(tdf)),
                                      "nota": "Umbral fijado en validación; el test NO se usó para elegirlo", **apply_threshold(ty, ts, thr, tdf["y_true"].tolist())}
    write_json(out, result)

    curve = pd.DataFrame(M.threshold_table(y_pos, s))
    stem = out.with_suffix("")
    write_csv(curve, Path(f"{stem}_curva.csv"))
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    if len(curve):
        ax.step(curve["umbral"], curve["sensibilidad"], where="post", label="sensibilidad (val)")
        ax.step(curve["umbral"], curve["tasa_fp"], where="post", label="tasa FP (val)")
    ax.axhline(args.target_sensitivity, ls=":", color="gray", label=f"objetivo {args.target_sensitivity:.2f}")
    ax.axvline(thr, color="crimson", ls="--", label=f"umbral {thr:.3f}")
    ax.set_xlabel("umbral sobre 1 - p(sana)")
    ax.set_ylabel("tasa")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=8)
    ax.set_title("Selección de umbral en validación")
    fig.tight_layout()
    fig.savefig(Path(f"{stem}_curva.png"), dpi=130)
    plt.close(fig)
    v = val_report
    print(f"[threshold] umbral={thr:.4f} | val: sens={v['sensibilidad']:.3f} ({v['tp']}/{v['tp'] + v['fn']}), FPR={v['tasa_fp']:.3f} ({v['fp']}/{v['fp'] + v['tn']}), FDR={v['tasa_falsa_alarma_fdr']:.3f}")
    if args.test_pred:
        t = result["test_informativo"]
        print(f"[threshold] test (informativo): sens={t['sensibilidad']:.3f} ({t['tp']}/{t['tp'] + t['fn']}), FPR={t['tasa_fp']:.3f} ({t['fp']}/{t['fp'] + t['tn']})")
    for w in warnings:
        print(f"[threshold] AVISO: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
