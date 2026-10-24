#!/usr/bin/env python
"""Escribe ``resultados/detector.yaml``: el resumen del detector visual que consume la simulación.

Contiene la matriz de confusión normalizada por fila (P(decisión | verdad)), el recall por clase con
IC95, la sensibilidad y la tasa de falsos positivos binarias, el umbral, el origen de los datos
(dataset, licencia, hash del test congelado) y la fecha. Lee:

* ``--metrics``: ``metrics.json`` de ``evaluate.py`` sobre el TEST congelado,
* ``--threshold``: ``threshold.json`` de ``threshold.py`` (opcional; sin él se exporta argmax),
* ``--split-summary``: ``split_summary.json`` de ``split.py`` (opcional, recomendado),
* ``--latency``: JSON de ``predict.py --bench`` (opcional).

Ejemplo:
    .venv/bin/python -I pipeline/export_detector_yaml.py --metrics resultados/eval_probe_test/metrics.json \
        --threshold pipeline/work/drberry/clip/threshold_probe.json \
        --split-summary pipeline/work/drberry/splits/split_summary.json \
        --dataset-name "DrBerry drberry-original-data v1" --dataset-license "CC BY 4.0" \
        --dataset-url https://universe.roboflow.com/drberry/drberry-original-data/dataset/1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from common import RESULTADOS_DIR, now_iso, read_json, sha256_file  # noqa: E402


class _NoAliasDumper(yaml.SafeDumper):
    """Sin anclas/alias (&id001): el YAML queda legible y fácil de leer desde cualquier lenguaje."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


def _r(x: Any, nd: int = 4) -> Any:
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, list):
        return [_r(v, nd) for v in x]
    if isinstance(x, dict):
        return {k: _r(v, nd) for k, v in x.items()}
    return x


def build_detector(metrics: dict[str, Any], threshold: dict[str, Any] | None, split_summary: dict[str, Any] | None,
                   latency: dict[str, Any] | None, args: argparse.Namespace) -> dict[str, Any]:
    rule = "umbral" if threshold is not None and "umbral" in metrics["reglas"] else "argmax"
    r = metrics["reglas"][rule]
    mc = r["matriz_confusion"]
    b = r["binario"]
    classes = mc["clases"]
    det: dict[str, Any] = {
        "version_formato": 1,
        "generado": now_iso(),
        "descripcion": "Detector visual de hojas (clasificador). Matriz = P(decision | verdad), filas suman 1.",
        "modelo": args.model_name or metrics["meta"].get("modelo", ""),
        "clases": classes,
        "clase_sana": metrics["meta"].get("clase_sana", "sana"),
        "regla_decision": rule,
        "umbral_sospecha": _r(threshold["umbral"]) if threshold is not None else None,
        "puntaje": "1 - p(sana)",
        "objetivo_sensibilidad": threshold.get("objetivo_sensibilidad") if threshold else None,
        "matriz_confusion_normalizada": {
            "filas_verdad": classes,
            "columnas_decision": classes,
            "valores": _r(mc["normalizada_por_fila"]),
        },
        "matriz_confusion_conteos": mc["conteos"],
        "recall_por_clase": {
            c: {"valor": _r(v["recall"]), "ic95_bootstrap": _r(v["ic95"]["recall"]), "ic95_clopper_pearson": _r(v["recall_clopper_pearson"]), "n": v["soporte"]}
            for c, v in r["por_clase"].items()
        },
        "binario_enfermo_vs_sano": {
            "sensibilidad": _r(b["sensibilidad"]),
            "sensibilidad_ic95_bootstrap": _r(b["ic95"].get("sensibilidad")),
            "sensibilidad_ic95_clopper_pearson": _r(b["clopper_pearson"]["sensibilidad"]),
            "especificidad": _r(b["especificidad"]),
            "tasa_fp": _r(b["tasa_fp"]),
            "tasa_fp_ic95_bootstrap": _r(b["ic95"].get("tasa_fp")),
            "tasa_fp_ic95_clopper_pearson": _r(b["clopper_pearson"]["tasa_fp"]),
            "tasa_falsa_alarma_fdr": _r(b["tasa_falsa_alarma_fdr"]),
            "tp": b["tp"], "fp": b["fp"], "fn": b["fn"], "tn": b["tn"],
        },
        "exactitud": _r(r["accuracy"]),
        "macro_f1": _r(r["macro_f1"]),
        "evaluado_en": {
            "conjunto": metrics["meta"].get("split") or "test",
            "n": metrics["meta"]["n"],
            "n_grupos": metrics["meta"].get("n_grupos"),
            "predicciones_sha256": metrics["meta"].get("sha256_predicciones"),
            "unidad_bootstrap": metrics["meta"].get("unidad_bootstrap"),
            "n_boot": metrics["meta"].get("n_boot"),
        },
        "origen_datos": {
            "dataset": args.dataset_name,
            "url": args.dataset_url,
            "licencia": args.dataset_license,
            "notas": args.data_notes,
        },
        "advertencias": list(args.warning or []),
    }
    if threshold is not None:
        det["umbral_elegido_en"] = {"conjunto": getattr(args, "umbral_conjunto", None) or "validacion", **{k: threshold["elegido_en"][k] for k in ("n", "n_enfermos", "n_sanos", "sha256")}}
    if split_summary is not None:
        tf = split_summary.get("test_congelado", {})
        det["origen_datos"].update({
            "split_semilla": split_summary.get("semilla"),
            "items_por_split": split_summary.get("items_por_split"),
            "grupos_por_split": split_summary.get("grupos_por_split"),
            "test_congelado_sha256": tf.get("sha256"),
            "test_congelado_sha256_contenido": tf.get("sha256_contenido"),
            "fuga_grupos_entre_splits": split_summary.get("fuga_grupos_entre_splits"),
        })
    if latency is not None:
        det["latencia_ms"] = _r(latency.get("latencia_ms", latency), 2)
    n_min = min((v["soporte"] for v in r["por_clase"].values()), default=0)
    if n_min < 30:
        det["advertencias"].append(f"Clase con solo {n_min} ejemplos en test: usar los IC, no solo el valor puntual")
    return det


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metrics", required=True, help="metrics.json de evaluate.py (test)")
    ap.add_argument("--threshold", default=None, help="threshold.json de threshold.py")
    ap.add_argument("--split-summary", default=None)
    ap.add_argument("--latency", default=None, help="JSON de latencia de predict.py --bench")
    ap.add_argument("--out", default=str(RESULTADOS_DIR / "detector.yaml"))
    ap.add_argument("--model-name", default=None)
    ap.add_argument("--dataset-name", default="NO ESPECIFICADO")
    ap.add_argument("--dataset-url", default="")
    ap.add_argument("--dataset-license", default="")
    ap.add_argument("--data-notes", default="")
    ap.add_argument("--warning", action="append", help="Advertencia adicional (repetible)")
    ap.add_argument("--umbral-conjunto", default="validacion", help="Nombre del conjunto donde se fijó el umbral (p. ej. 'OOF CV5 train+val')")
    ap.add_argument("--extra-yaml", action="append", default=[], help="YAML con claves de primer nivel adicionales a fusionar (repetible)")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metrics = read_json(args.metrics)
    thr = read_json(args.threshold) if args.threshold else None
    ss = read_json(args.split_summary) if args.split_summary else None
    lat = read_json(args.latency) if args.latency else None
    det = build_detector(metrics, thr, ss, lat, args)
    det["fuentes_locales"] = {"metrics": str(Path(args.metrics).resolve()), "metrics_sha256": sha256_file(args.metrics)}
    for extra in args.extra_yaml:
        add = yaml.safe_load(Path(extra).read_text(encoding="utf-8")) or {}
        if not isinstance(add, dict):
            raise SystemExit(f"{extra}: se esperaba un mapeo YAML")
        clash = sorted(set(add) & set(det))
        if clash:
            raise SystemExit(f"{extra}: claves que ya existen en detector.yaml: {clash}")
        det.update(add)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Generado por pipeline/export_detector_yaml.py. No editar a mano.\n" + yaml.dump(det, Dumper=_NoAliasDumper, sort_keys=False, allow_unicode=True, width=120, default_flow_style=None), encoding="utf-8")
    b = det["binario_enfermo_vs_sano"]
    print(f"[export] {out}: regla={det['regla_decision']} sens={b['sensibilidad']} FPR={b['tasa_fp']} umbral={det['umbral_sospecha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
