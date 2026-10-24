#!/usr/bin/env python
"""Evalúa un CSV de predicciones (formato estándar del pipeline) y exporta JSON + PNG.

Calcula, para la regla argmax y (si se da ``--threshold``) para la regla de umbral de sospecha:

* matriz de confusión (conteos y normalizada por fila = recall por clase),
* precision / recall / F1 por clase, exactitud, macro-F1, exactitud balanceada,
* binario enfermo-vs-sano: sensibilidad, especificidad, tasa de FP, tasa de falsa alarma (FDR),
  VPP/VPN, conteos TP/FP/FN/TN, y además IC exacto Clopper-Pearson de sensibilidad y especificidad,
* intervalos bootstrap (``--n-boot`` 1000 por defecto) de TODAS las métricas; si el CSV trae la
  columna ``group`` se remuestrean grupos completos (``--bootstrap-unit auto``),
* curva PR del puntaje de enfermedad (``1 - p(sana)``) y curvas uno-contra-resto por clase, con
  precisión media (AP) y AUC-ROC, también con IC bootstrap.

Salidas en ``--out``: ``metrics.json``, ``per_class.csv``, ``confusion_matrix.png``, ``pr_curve.png``.

Ejemplo:
    .venv/bin/python -I pipeline/evaluate.py --pred pipeline/work/drberry/clip/predicciones_probe_test.csv \
        --threshold pipeline/work/drberry/clip/threshold_probe.json --out resultados/eval_probe_test
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
from common import DEFAULT_HEALTHY, PROB_PREFIX, decide, disease_scores, healthy_index, load_threshold, now_iso, read_predictions, sha256_file, write_csv, write_json  # noqa: E402


def evaluate_rule(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    classes: Sequence[str],
    healthy: str,
    n_boot: int = 1000,
    seed: int = 0,
    groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Métricas puntuales + IC bootstrap para una regla de decisión."""
    k = len(classes)
    idx = {c: i for i, c in enumerate(classes)}
    t = np.array([idx[c] for c in y_true], dtype=int)
    p = np.array([idx[c] for c in y_pred], dtype=int)
    hi = healthy_index(classes, healthy)
    y_pos, p_pos = t != hi, p != hi

    def stats_for(sel: np.ndarray) -> dict[str, float]:
        cm = M.confusion_from_indices(t[sel], p[sel], k)
        prf = M.per_class_prf(cm)
        out = dict(M.multiclass_summary(cm))
        for j, c in enumerate(classes):
            out[f"precision/{c}"] = float(prf["precision"][j])
            out[f"recall/{c}"] = float(prf["recall"][j])
            out[f"f1/{c}"] = float(prf["f1"][j])
        tp, fp, fn, tn = M.binary_counts(y_pos[sel], p_pos[sel])
        for key, v in M.binary_metrics(tp, fp, fn, tn).items():
            out[f"binario/{key}"] = v
        return out

    point = stats_for(np.arange(len(t)))
    ci = M.bootstrap_ci(stats_for, len(t), n_boot=n_boot, seed=seed, groups=groups) if n_boot > 0 else {}
    cm = M.confusion_from_indices(t, p, k)
    prf = M.per_class_prf(cm)
    tp, fp, fn, tn = M.binary_counts(y_pos, p_pos)

    def pci(key: str) -> list[float] | None:
        return list(ci[key]) if key in ci else None

    return {
        "n": int(len(t)),
        "accuracy": point["accuracy"],
        "macro_f1": point["macro_f1"],
        "balanced_accuracy": point["balanced_accuracy"],
        "ic95": {key: pci(key) for key in ("accuracy", "macro_f1", "balanced_accuracy")},
        "por_clase": {
            c: {
                "precision": float(prf["precision"][j]),
                "recall": float(prf["recall"][j]),
                "f1": float(prf["f1"][j]),
                "soporte": int(prf["support"][j]),
                "ic95": {m: pci(f"{m}/{c}") for m in ("precision", "recall", "f1")},
                "recall_clopper_pearson": list(M.clopper_pearson(int(cm[j, j]), int(cm[j].sum()))),
            }
            for j, c in enumerate(classes)
        },
        "binario": {
            "positivo": "enfermo (cualquier clase distinta de la sana)",
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            **M.binary_metrics(tp, fp, fn, tn),
            "ic95": {key.split("/", 1)[1]: pci(key) for key in point if key.startswith("binario/")},
            "clopper_pearson": {
                "sensibilidad": list(M.clopper_pearson(tp, tp + fn)),
                "especificidad": list(M.clopper_pearson(tn, tn + fp)),
                "tasa_fp": list(M.clopper_pearson(fp, fp + tn)),
            },
        },
        "matriz_confusion": {
            "clases": list(classes),
            "filas": "verdad",
            "columnas": "prediccion",
            "conteos": cm.tolist(),
            "normalizada_por_fila": np.round(M.normalize_rows(cm), 4).tolist(),
        },
    }


def curves(y_true: Sequence[str], probs: np.ndarray, classes: Sequence[str], healthy: str, n_boot: int, seed: int, groups: Sequence[str] | None) -> dict[str, Any]:
    hi = healthy_index(classes, healthy)
    y_pos = np.array([c != classes[hi] for c in y_true])
    score = disease_scores(probs, classes, healthy)

    def stat(sel: np.ndarray) -> dict[str, float]:
        return {"ap": M.average_precision(y_pos[sel], score[sel]), "auc": M.roc_auc(y_pos[sel], score[sel])}

    ci = M.bootstrap_ci(stat, len(y_pos), n_boot=n_boot, seed=seed, groups=groups) if n_boot > 0 else {}
    ovr = {}
    for j, c in enumerate(classes):
        yc = np.array([t == c for t in y_true])
        ovr[c] = {"ap": M.average_precision(yc, probs[:, j]), "auc": M.roc_auc(yc, probs[:, j]), "n_pos": int(yc.sum())}
    return {
        "enfermo_vs_sano": {
            "puntaje": "1 - p(sana)",
            "average_precision": M.average_precision(y_pos, score),
            "roc_auc": M.roc_auc(y_pos, score),
            "ic95": {"average_precision": list(ci["ap"]) if "ap" in ci else None, "roc_auc": list(ci["auc"]) if "auc" in ci else None},
            "n_pos": int(y_pos.sum()),
            "n_neg": int((~y_pos).sum()),
        },
        "uno_contra_resto": ovr,
    }


def plot_confusion(cm: np.ndarray, classes: Sequence[str], dest: Path, title: str) -> None:
    norm = M.normalize_rows(cm)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, mat, ttl, fmt in ((axes[0], cm, "Conteos", "d"), (axes[1], norm, "Normalizada por fila (recall)", ".2f")):
        im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=(mat.max() if mat.max() > 0 else 1))
        ax.set_xticks(range(len(classes)), classes, rotation=30, ha="right")
        ax.set_yticks(range(len(classes)), classes)
        ax.set_xlabel("Predicción")
        ax.set_ylabel("Verdad")
        ax.set_title(ttl)
        thr = mat.max() / 2 if mat.max() > 0 else 0.5
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                ax.text(j, i, format(int(v) if fmt == "d" else v, fmt), ha="center", va="center", color="white" if v > thr else "black", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(title)
    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=130)
    plt.close(fig)


def plot_pr(y_true: Sequence[str], probs: np.ndarray, classes: Sequence[str], healthy: str, dest: Path, threshold: float | None, title: str) -> None:
    hi = healthy_index(classes, healthy)
    y_pos = np.array([c != classes[hi] for c in y_true])
    score = disease_scores(probs, classes, healthy)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    ax = axes[0]
    if y_pos.any() and (~y_pos).any():
        pr, rc, _ = M.pr_curve(y_pos, score)
        ax.step(rc, pr, where="post", lw=2, label=f"enfermo vs sano (AP={M.average_precision(y_pos, score):.3f})")
        if threshold is not None:
            tp, fp, fn, tn = M.binary_counts(y_pos, score >= threshold)
            bm = M.binary_metrics(tp, fp, fn, tn)
            ax.scatter([bm["sensibilidad"]], [bm["vpp"]], s=70, zorder=5, color="crimson", label=f"umbral {threshold:.3f}")
        ax.axhline(y_pos.mean(), ls=":", color="gray", label=f"prevalencia {y_pos.mean():.2f}")
    ax.set_xlabel("Recall (sensibilidad)")
    ax.set_ylabel("Precisión (VPP)")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_title("Enfermo vs sano")
    ax.legend(loc="lower left", fontsize=8)
    ax = axes[1]
    for j, c in enumerate(classes):
        yc = np.array([t == c for t in y_true])
        if yc.any() and (~yc).any():
            pr, rc, _ = M.pr_curve(yc, probs[:, j])
            ax.step(rc, pr, where="post", label=f"{c} (AP={M.average_precision(yc, probs[:, j]):.3f}, n={int(yc.sum())})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precisión")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_title("Uno contra resto")
    ax.legend(loc="lower left", fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=130)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", required=True, help="CSV de predicciones (path, y_true, y_pred, p_<clase>...)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--healthy-class", default=DEFAULT_HEALTHY)
    ap.add_argument("--threshold", default=None, help="Umbral (número) o threshold.json de threshold.py")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--bootstrap-unit", choices=["auto", "sample", "group"], default="auto",
                    help="auto: por grupo si existe la columna 'group' (más honesto con ráfagas/duplicados)")
    ap.add_argument("--title", default=None)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    df, classes = read_predictions(args.pred)
    df = df[df["y_true"] != ""].reset_index(drop=True)
    unknown = sorted(set(df["y_true"]) - set(classes))
    if unknown:
        raise SystemExit(f"Etiquetas verdaderas sin columna de probabilidad: {unknown}")
    probs = df[[f"{PROB_PREFIX}{c}" for c in classes]].to_numpy(float)
    y_true = df["y_true"].tolist()
    unit = args.bootstrap_unit
    if unit == "auto":
        unit = "group" if "group" in df.columns and (df["group"] != "").all() else "sample"
    groups = df["group"].tolist() if unit == "group" else None
    thr = load_threshold(args.threshold)
    title = args.title or Path(args.pred).stem

    rules: dict[str, Any] = {"argmax": evaluate_rule(y_true, decide(probs, classes, args.healthy_class, None), classes, args.healthy_class, args.n_boot, args.seed, groups)}
    if thr is not None:
        rules["umbral"] = evaluate_rule(y_true, decide(probs, classes, args.healthy_class, thr), classes, args.healthy_class, args.n_boot, args.seed, groups)
        rules["umbral"]["umbral"] = thr
    result = {
        "meta": {
            "creado": now_iso(),
            "predicciones": str(Path(args.pred).resolve()),
            "sha256_predicciones": sha256_file(args.pred),
            "modelo": str(df["model"].iloc[0]) if "model" in df.columns and len(df) else "",
            "split": str(df["split"].iloc[0]) if "split" in df.columns and len(df) else "",
            "n": int(len(df)),
            "n_grupos": int(df["group"].nunique()) if "group" in df.columns else None,
            "clases": classes,
            "clase_sana": args.healthy_class,
            "n_boot": args.n_boot,
            "semilla_bootstrap": args.seed,
            "unidad_bootstrap": unit,
            "nota_ic": "IC95 percentil por bootstrap; con pocos grupos por clase los intervalos son anchos y es lo esperado",
        },
        "reglas": rules,
        "curvas": curves(y_true, probs, classes, args.healthy_class, args.n_boot, args.seed, groups),
    }
    write_json(out / "metrics.json", result)
    rows = []
    for rule, r in rules.items():
        for c, v in r["por_clase"].items():
            rows.append({"regla": rule, "clase": c, "precision": v["precision"], "recall": v["recall"], "f1": v["f1"], "soporte": v["soporte"],
                         "recall_ic95_lo": (v["ic95"]["recall"] or [None, None])[0], "recall_ic95_hi": (v["ic95"]["recall"] or [None, None])[1]})
    write_csv(pd.DataFrame(rows), out / "per_class.csv")
    main_rule = "umbral" if thr is not None else "argmax"
    plot_confusion(np.array(rules[main_rule]["matriz_confusion"]["conteos"]), classes, out / "confusion_matrix.png", f"{title} — regla {main_rule}")
    plot_pr(y_true, probs, classes, args.healthy_class, out / "pr_curve.png", thr, title)
    b = rules[main_rule]["binario"]
    print(f"[evaluate] {title}: n={len(df)} regla={main_rule} acc={rules[main_rule]['accuracy']:.3f} macroF1={rules[main_rule]['macro_f1']:.3f} "
          f"sens={b['sensibilidad']:.3f} IC95={b['ic95'].get('sensibilidad')} FPR={b['tasa_fp']:.3f} -> {out / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
