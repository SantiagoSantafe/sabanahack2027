#!/usr/bin/env python
"""Junta métricas de resultados/ml/drberry_*/eval_*/metrics.json, umbrales y OOD en tablas CSV.

Salidas: resultados/ml/tabla_drberry_test.csv, tabla_ood.csv, tabla_stress.csv (si existen las evaluaciones).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

R = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml")

# (modo, nombre en tabla, carpeta eval test, umbral json, carpeta eval del conjunto de selección, conjunto de selección)
MODELOS = [
    ("crops", "CLIP cero-shot", "eval_clip_zeroshot_test", "umbral_clip_zeroshot.json", "eval_clip_zeroshot_val", "val"),
    ("crops", "CLIP sonda lineal", "eval_clip_probe_test", "umbral_clip_probe.json", "eval_clip_probe_val", "val"),
    ("crops", "YOLO11n-cls 224", "eval_yolo_test", "umbral_yolo.json", "eval_yolo_val", "val"),
    ("image", "CLIP cero-shot", "eval_clip_zeroshot_test", "umbral_clip_zeroshot.json", "eval_clip_zeroshot_val", "val"),
    ("image", "CLIP sonda lineal", "eval_clip_probe_test", "umbral_clip_probe.json", "eval_clip_probe_val", "val"),
    ("image", "CLIP sonda teselas 2x2", "eval_clip_probe_tiles2_test", "umbral_clip_probe_tiles2.json", "eval_clip_probe_tiles2_val", "val"),
    ("image", "CLIP sonda teselas 3x3", "eval_clip_probe_tiles3_test", "umbral_clip_probe_tiles3.json", "eval_clip_probe_tiles3_val", "val"),
    ("image", "YOLO11n-cls 224", "eval_yolo224_test", "umbral_yolo224.json", "eval_yolo224_val", "val"),
    ("image", "YOLO11n-cls 448", "eval_yolo448_test", "umbral_yolo448.json", "eval_yolo448_val", "val"),
    ("image", "YOLO11n-cls 640", "eval_yolo640_test", "umbral_yolo640.json", "eval_yolo640_val", "val"),
    ("image", "CLIP sonda CV5 (global)", "eval_clip_cv_tiles0_test", "umbral_clip_cv_tiles0.json", "eval_clip_cv_tiles0_oof", "OOF train+val"),
    ("image", "CLIP sonda CV5 teselas 2x2", "eval_clip_cv_tiles2_test", "umbral_clip_cv_tiles2.json", "eval_clip_cv_tiles2_oof", "OOF train+val"),
    ("image", "CLIP sonda CV5 teselas 3x3 [FINAL]", "eval_clip_cv_tiles3_test", "umbral_clip_cv_tiles3.json", "eval_clip_cv_tiles3_oof", "OOF train+val"),
    ("image", "CLIP sonda CV5 teselas 3x3, umbral por_clase", "eval_clip_cv_tiles3_porclase_test", "umbral_clip_cv_tiles3_porclase.json", "eval_clip_cv_tiles3_oof", "OOF train+val"),
    ("image", "Sonda CLIP de RECORTES aplicada a imagen [post-hoc]", "eval_cruzado_crops_probe_test", "umbral_cruzado_crops_probe.json", None, "val imagen"),
    ("crops", "CLIP sonda, SPLIT ORIGINAL con fuga", "eval_clip_probe_split_original_test", "umbral_clip_probe_split_original.json", None, "val original"),
    ("image", "CLIP sonda, SPLIT ORIGINAL con fuga", "eval_clip_probe_split_original_test", "umbral_clip_probe_split_original.json", None, "val original"),
]


def f(x: float, d: int = 3) -> str:
    return "" if x is None else f"{x:.{d}f}"


def ci(v) -> str:
    return "" if not v else f"[{v[0]:.2f}–{v[1]:.2f}]"


def fila(modo: str, nombre: str, ev: str, um: str, evsel: str | None, sel: str) -> dict | None:
    W = R / f"drberry_{modo}"
    p = W / ev / "metrics.json"
    if not p.exists():
        return None
    m = json.loads(p.read_text())
    a, u = m["reglas"]["argmax"], m["reglas"]["umbral"]
    b = u["binario"]
    row = {
        "modo": modo, "modelo": nombre, "n_test": m["meta"]["n"], "grupos_test": m["meta"]["n_grupos"],
        "umbral": f(u.get("umbral"), 3), "sel": sel,
        "exactitud_argmax": f(a["accuracy"]), "ic_exactitud_argmax": ci(a["ic95"]["accuracy"]),
        "macroF1_argmax": f(a["macro_f1"]),
        "exactitud_umbral": f(u["accuracy"]), "ic_exactitud_umbral": ci(u["ic95"]["accuracy"]),
        "sens": f"{b['tp']}/{b['tp'] + b['fn']} = {b['sensibilidad']:.3f}", "ic_sens_boot": ci(b["ic95"]["sensibilidad"]),
        "ic_sens_cp": ci(b["clopper_pearson"]["sensibilidad"]),
        "tasa_fp": f"{b['fp']}/{b['fp'] + b['tn']} = {b['tasa_fp']:.3f}", "ic_fp_boot": ci(b["ic95"]["tasa_fp"]),
        "ic_fp_cp": ci(b["clopper_pearson"]["tasa_fp"]),
        **{f"recall_{c}": f(v["recall"], 2) for c, v in u["por_clase"].items()},
        "auc_enfermo_sano": f(m["curvas"]["enfermo_vs_sano"].get("roc_auc")),
        "ap_enfermo_sano": f(m["curvas"]["enfermo_vs_sano"].get("average_precision")),
    }
    # detección como "sospecha" por enfermedad (sin importar si el diagnóstico es correcto)
    pr = pd.read_csv(m["meta"]["predicciones"], keep_default_na=False)
    thr = u.get("umbral")
    if thr is not None:
        alarm = (1 - pr["p_sana"].astype(float)) >= float(thr)
        for c in ("alternaria", "heliothis", "oidio"):
            mk = pr["y_true"] == c
            row[f"deteccion_{c}"] = f"{int(alarm[mk].sum())}/{int(mk.sum())}"
    # métricas en el conjunto donde se fijó el umbral: bloque "validacion" del threshold.json
    tj = W / um
    if tj.exists():
        v = json.loads(tj.read_text())["validacion"]
        row.update({"sel_n": v["tp"] + v["fn"] + v["fp"] + v["tn"], "sel_sens": f(v["sensibilidad"]), "sel_tasa_fp": f"{v['fp']}/{v['fp'] + v['tn']} = {v['tasa_fp']:.3f}"})
    if evsel and (W / evsel / "metrics.json").exists():
        ms = json.loads((W / evsel / "metrics.json").read_text())
        row["sel_macroF1_argmax"] = f(ms["reglas"]["argmax"]["macro_f1"])
    return row


def main() -> int:
    rows = [r for r in (fila(*x) for x in MODELOS) if r]
    df = pd.DataFrame(rows)
    df.to_csv(R / "tabla_drberry_test.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 40):
        print(df[["modo", "modelo", "sel", "sel_sens", "sel_tasa_fp", "exactitud_argmax", "exactitud_umbral", "sens", "ic_sens_boot", "tasa_fp", "ic_fp_cp",
                  "recall_alternaria", "recall_heliothis", "recall_oidio", "recall_sana", "deteccion_alternaria", "deteccion_heliothis", "deteccion_oidio", "auc_enfermo_sano"]].to_string(index=False))
    # OOD
    ood = []
    for d in sorted((R / "ood" / "eval").glob("*")):
        t = d / "ood_tabla.csv"
        if t.exists():
            x = pd.read_csv(t)
            x.insert(0, "modelo", d.name)
            ood.append(x)
    if ood:
        o = pd.concat(ood, ignore_index=True)
        o.to_csv(R / "tabla_ood.csv", index=False)
        piv = o.pivot_table(index="categoria", columns="modelo", values="tasa_alarma", aggfunc="first")
        print("\nTasa de alarma OOD (sospecha) por categoría y modelo:")
        with pd.option_context("display.width", 250, "display.max_columns", 40):
            print(piv.round(3).to_string())
    st = []
    for d in sorted((R / "stress" / "eval").glob("*/*")):
        p = d / "metrics.json"
        if p.exists():
            m = json.loads(p.read_text())
            u = m["reglas"]["umbral"]
            b = u["binario"]
            st.append({"modelo": d.parent.name, "condicion": d.name, "n": m["meta"]["n"], "exactitud_umbral": round(u["accuracy"], 3),
                       "sens": round(b["sensibilidad"], 3), "tasa_fp": round(b["tasa_fp"], 3), "tp": b["tp"], "fn": b["fn"], "fp": b["fp"], "tn": b["tn"],
                       "recall_alternaria": round(u["por_clase"]["alternaria"]["recall"], 2)})
    if st:
        s = pd.DataFrame(st)
        s.to_csv(R / "tabla_stress.csv", index=False)
        print("\nEstrés pantalla->cámara (sintético):")
        print(s.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
