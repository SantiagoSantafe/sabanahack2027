#!/usr/bin/env python
"""Evaluación FUERA del dataset de entrenamiento (OOD): tasa de alarma por categoría con IC.

Las categorías OOD (``y_true`` del CSV de predicciones) no tienen por qué ser clases del modelo
(p. ej. ``roya`` u ``oidio_cerezo``). Un JSON ``--spec`` dice qué se espera de cada una::

    {"campo_sana":  {"esperado": "sana", "descripcion": "Hoja sana de campo (iNaturalist)"},
     "campo_oidio": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "campo_sana"}}

* ``esperado = "sana"``: la alarma es una FALSA ALARMA -> se reporta la tasa de FP (y especificidad).
* ``esperado = "enfermedad"``: la alarma es lo deseado -> se reporta la sensibilidad (detección como
  "sospecha"); si hay ``clase_modelo`` también el recall de esa clase (diagnóstico correcto).
* ``referencia``: categoría sana del mismo dominio para calcular AUC/AP de separabilidad (independiente
  del umbral: dice si re-calibrar el umbral en ese dominio podría bastar).
* Las categorías sin entrada en el spec se reportan con ``esperado = "desconocido"``.

La regla de decisión es la del pipeline (``common.decide``): sospecha si ``1 - p(sana) >= umbral``.
IC95: Clopper-Pearson (supone independencia) y bootstrap percentil remuestreando GRUPOS (columna
``group``: observación, hoja o imagen de origen), que es el honesto cuando hay varias fotos por grupo.

Salidas: ``<out>/ood_metrics.json`` y ``<out>/ood_tabla.csv``.

Ejemplo:
    .venv/bin/python -I pipeline/ood_eval.py --pred resultados/ml/ood/pred/predicciones_crops_yolo.csv \
        --threshold resultados/ml/drberry_crops/umbral_yolo.json --spec resultados/ml/ood/spec_ood.json \
        --out resultados/ml/ood/eval/crops_yolo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import metrics as M  # noqa: E402
from common import DEFAULT_HEALTHY, PROB_PREFIX, decide, disease_scores, load_threshold, now_iso, read_json, read_predictions, sha256_file, write_csv, write_json  # noqa: E402


def rate_with_ci(flags: np.ndarray, groups: np.ndarray | None, n_boot: int, seed: int) -> dict[str, Any]:
    n = int(len(flags))
    k = int(flags.sum())
    out: dict[str, Any] = {"k": k, "n": n, "tasa": (k / n) if n else float("nan"), "ic95_clopper_pearson": list(M.clopper_pearson(k, n))}
    if n and groups is not None and len(np.unique(groups)) > 1:
        ci = M.bootstrap_ci(lambda idx: {"t": float(flags[idx].mean())}, n, n_boot=n_boot, seed=seed, groups=groups)
        out["ic95_bootstrap_grupos"] = list(ci["t"])
    return out


def evaluate_ood(df: pd.DataFrame, classes: Sequence[str], thr: float | None, spec: dict[str, Any], healthy: str = DEFAULT_HEALTHY,
                 n_boot: int = 1000, seed: int = 0) -> dict[str, Any]:
    probs = df[[f"{PROB_PREFIX}{c}" for c in classes]].to_numpy(float)
    score = disease_scores(probs, classes, healthy)
    decided = np.asarray(decide(probs, classes, healthy, thr))
    alarm = decided != healthy
    groups_all = df["group"].astype(str).to_numpy() if "group" in df.columns else None
    cats: dict[str, Any] = {}
    for cat in sorted(df["y_true"].unique()):
        m = (df["y_true"] == cat).to_numpy()
        sp = spec.get(cat, {})
        esperado = sp.get("esperado", "desconocido")
        g = groups_all[m] if groups_all is not None else None
        r = rate_with_ci(alarm[m], g, n_boot, seed)
        row: dict[str, Any] = {
            "descripcion": sp.get("descripcion", ""),
            "esperado": esperado,
            "n": int(m.sum()),
            "n_grupos": int(len(np.unique(g))) if g is not None else None,
            "alarma": r,
            "metrica": {"sana": "tasa_falsas_alarmas", "enfermedad": "sensibilidad_sospecha"}.get(esperado, "tasa_alarma"),
            "distribucion_decision": {c: float((decided[m] == c).mean()) for c in classes},
            "p_enfermedad_mediana": float(np.median(score[m])),
        }
        cm = sp.get("clase_modelo")
        if cm:
            if cm not in classes:
                raise SystemExit(f"clase_modelo {cm!r} de {cat!r} no está en {list(classes)}")
            row["clase_modelo"] = cm
            row["recall_clase"] = rate_with_ci(decided[m] == cm, g, n_boot, seed)
        ref = sp.get("referencia")
        if ref and (df["y_true"] == ref).any():
            mr = (df["y_true"] == ref).to_numpy()
            y_pos = np.r_[np.ones(m.sum(), bool), np.zeros(mr.sum(), bool)]
            s = np.r_[score[m], score[mr]]
            row["separabilidad_vs_referencia"] = {"referencia": ref, "auc": float(M.roc_auc(y_pos, s)), "ap": float(M.average_precision(y_pos, s))}
        cats[cat] = row
    return cats


def table(cats: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for cat, r in cats.items():
        a = r["alarma"]
        rows.append({
            "categoria": cat, "esperado": r["esperado"], "metrica": r["metrica"], "n": r["n"], "n_grupos": r["n_grupos"],
            "alarmas": a["k"], "tasa_alarma": round(a["tasa"], 4),
            "ic95_cp": f"[{a['ic95_clopper_pearson'][0]:.3f}, {a['ic95_clopper_pearson'][1]:.3f}]",
            "ic95_boot_grupos": (f"[{a['ic95_bootstrap_grupos'][0]:.3f}, {a['ic95_bootstrap_grupos'][1]:.3f}]" if "ic95_bootstrap_grupos" in a else ""),
            "clase_modelo": r.get("clase_modelo", ""),
            "recall_clase": round(r["recall_clase"]["tasa"], 4) if "recall_clase" in r else "",
            "auc_vs_ref": round(r["separabilidad_vs_referencia"]["auc"], 4) if "separabilidad_vs_referencia" in r else "",
            **{f"dec_{c}": round(v, 3) for c, v in r["distribucion_decision"].items()},
            "descripcion": r["descripcion"],
        })
    return pd.DataFrame(rows)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", required=True, help="CSV de predicciones (predict_manifest.py)")
    ap.add_argument("--threshold", default=None, help="threshold.json del modelo (fijado en val de DrBerry) o número")
    ap.add_argument("--spec", default=None, help="JSON {categoria: {esperado, clase_modelo, referencia, descripcion}}")
    ap.add_argument("--healthy-class", default=DEFAULT_HEALTHY)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    df, classes = read_predictions(args.pred)
    thr = load_threshold(args.threshold)
    spec = read_json(args.spec) if args.spec else {}
    cats = evaluate_ood(df, classes, thr, spec, args.healthy_class, args.n_boot, args.seed)
    out = Path(args.out)
    res = {"creado": now_iso(), "predicciones": str(Path(args.pred).resolve()), "sha256_predicciones": sha256_file(args.pred),
           "modelo": str(df["model"].iloc[0]) if "model" in df.columns and len(df) else "", "clases": classes, "umbral": thr,
           "regla": "sospecha si 1 - p(sana) >= umbral" if thr is not None else "argmax", "categorias": cats}
    write_json(out / "ood_metrics.json", res)
    tab = table(cats)
    write_csv(tab, out / "ood_tabla.csv")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(tab.drop(columns=["descripcion"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
