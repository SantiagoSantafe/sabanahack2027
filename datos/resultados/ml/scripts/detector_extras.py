#!/usr/bin/env python
"""Arma resultados/ml/detector_extras.yaml (secciones adicionales de detector.yaml) desde los archivos de métricas.

Todo número sale de un archivo local que se cita en ``fuente``. Ejecutar con .venv/bin/python -I.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline"))
import metrics as M  # noqa: E402

R = D / "resultados" / "ml"
WI, WC = R / "drberry_image", R / "drberry_crops"


def rd(p: Path) -> dict:
    return json.loads(p.read_text())


def r4(x):
    return None if x is None else round(float(x), 4)


def binario(ev: Path) -> dict:
    m = rd(ev / "metrics.json")
    u = m["reglas"]["umbral"]
    b = u["binario"]
    return {"umbral": r4(u.get("umbral")), "sensibilidad": r4(b["sensibilidad"]), "tp_de": f"{b['tp']}/{b['tp'] + b['fn']}",
            "sensibilidad_ic95_clopper_pearson": [r4(v) for v in b["clopper_pearson"]["sensibilidad"]],
            "sensibilidad_ic95_bootstrap_grupos": [r4(v) for v in b["ic95"]["sensibilidad"]],
            "tasa_fp": r4(b["tasa_fp"]), "fp_de": f"{b['fp']}/{b['fp'] + b['tn']}",
            "tasa_fp_ic95_clopper_pearson": [r4(v) for v in b["clopper_pearson"]["tasa_fp"]],
            "exactitud": r4(u["accuracy"]), "fuente": str(ev / "metrics.json")}


def deteccion_por_enfermedad(pred_csv: Path, thr: float) -> dict:
    p = pd.read_csv(pred_csv, keep_default_na=False)
    alarm = (1 - p["p_sana"].astype(float)) >= thr
    out = {}
    for c in ("alternaria", "heliothis", "oidio"):
        mk = p["y_true"] == c
        k, n = int(alarm[mk].sum()), int(mk.sum())
        out[c] = {"detectadas_como_sospecha": f"{k}/{n}", "valor": r4(k / n), "ic95_clopper_pearson": [r4(v) for v in M.clopper_pearson(k, n)],
                  "n_grupos": int(p.loc[mk, "group"].nunique())}
    return out


def ood(model: str, cats: list[str]) -> dict:
    f = R / "ood" / "eval" / model / "ood_metrics.json"
    if not f.exists():
        return {"pendiente": str(f)}
    m = rd(f)["categorias"]
    out = {}
    for c in cats:
        if c in m:
            a = m[c]["alarma"]
            out[c] = {"metrica": m[c]["metrica"], "valor": r4(a["tasa"]), "k_de_n": f"{a['k']}/{a['n']}",
                      "ic95_clopper_pearson": [r4(v) for v in a["ic95_clopper_pearson"]], "descripcion": m[c]["descripcion"]}
    out["fuente"] = str(f)
    return out


def main() -> int:
    thr_final = rd(WI / "umbral_clip_cv_tiles3.json")["umbral"]
    extras = {
        "seleccion_modelo": {
            "unidad": "imagen completa (lo que el D1 ve en la pantalla)",
            "protocolo": str(R / "protocolo_seleccion.json"),
            "familia_elegida_en_val": "sonda lineal CLIP ViT-B-32 (FPR val 0/10 con teselas) frente a YOLO11n-cls 224/448/640 (FPR val 6/10, 2/10, 2/10)",
            "variante_elegida_en_oof": "teselas 3x3 (FPR OOF 15/46 = 0.326 con sens OOF 0.902; empata con 2x2 y gana por macro-F1 OOF)",
            "umbral_elegido_en": "predicciones OOF de validación cruzada agrupada 5 pliegues sobre train+val (342 imágenes, 118 grupos)",
            "declaracion": "el cambio de val a CV se decidió después de ver que el umbral de val no sostuvo la sensibilidad en test",
        },
        "deteccion_por_enfermedad_test": {**deteccion_por_enfermedad(WI / "clip_cv_tiles3" / "predicciones_cvprobe_test.csv", thr_final),
                                          "nota": "sospecha = 1 - p(sana) >= umbral, sin importar si el diagnóstico es correcto"},
        "puntos_operacion_test": {
            "global_sens90_oof [ELEGIDO]": binario(WI / "eval_clip_cv_tiles3_test"),
            "por_clase_sens90_oof [alta sensibilidad]": binario(WI / "eval_clip_cv_tiles3_porclase_test"),
        },
        "comparaciones_test": {
            "cota_superior_recortes_localizacion_perfecta (sonda CLIP en recortes de caja)": binario(WC / "eval_clip_probe_test"),
            "yolo11n_cls_224_imagen (alternativa más robusta en el estrés sintético)": binario(WI / "eval_yolo224_test"),
            "split_original_con_fuga_imagen (sonda CLIP, NO usar)": binario(WI / "eval_clip_probe_split_original_test"),
        },
        "candidato_post_hoc_sonda_recortes_en_imagen": {
            "descripcion": ("Sonda CLIP entrenada con RECORTES de caja (train) y aplicada a la imagen completa; umbral fijado en val de imagen. "
                            "Se evaluó DESPUÉS de elegir el modelo final, así que sus cifras de test no son una estimación sin sesgo: confirmar con datos nuevos."),
            "test": binario(WI / "eval_cruzado_crops_probe_test"),
            "deteccion_por_enfermedad_test": deteccion_por_enfermedad(WI / "cruzado_crops_probe_en_imagen" / "predicciones_cruzado_test.csv",
                                                                      rd(WI / "umbral_cruzado_crops_probe.json")["umbral"]),
            "fuera_de_dominio": ood("cruzado_crops_probe_umbral_imagen", ["campo_sana", "pdc_arandano_verde", "pv_arandano_sano", "campo_oidio", "campo_roya", "campo_oruga"]),
            "estres_combinado": binario(R / "stress" / "eval" / "cruzado_crops_probe" / "combinada"),
            "pesos": str(R / "modelo_final" / "alternativa_sonda_recortes_en_imagen"),
        },
        "fuera_de_dominio": ood("image_clip_cv_tiles3", ["campo_sana", "pdc_arandano_verde", "pdc_arandano_rojizo", "pv_arandano_sano",
                                                       "campo_oidio", "campo_roya", "campo_oruga", "pd_otra_especie_sana"]),
        "estres_pantalla_camara_sintetico": {
            c: binario(R / "stress" / "eval" / "image_clip_cv_tiles3" / c) for c in ("original", "combinada")
            if (R / "stress" / "eval" / "image_clip_cv_tiles3" / c / "metrics.json").exists()
        },
    }
    det = extras["deteccion_por_enfermedad_test"]
    fin = extras["puntos_operacion_test"]["global_sens90_oof [ELEGIDO]"]
    cs = extras["fuera_de_dominio"].get("campo_sana", {})
    comb = extras["estres_pantalla_camara_sintetico"].get("combinada", {})
    extras["recomendacion_para_simulacion"] = {
        "sensibilidad_clasificador": {"valor": fin["sensibilidad"], "ic95_clopper_pearson": fin["sensibilidad_ic95_clopper_pearson"],
                                      "escenario_pesimista_estres_combinado": comb.get("sensibilidad"), "etiqueta": "MEDIDO (DrBerry test congelado, imagen completa)"},
        "por_clase_deteccion": {c: det[c]["valor"] for c in ("oidio", "alternaria", "heliothis")},
        "especificidad_clasificador": {"drberry_test": r4(1 - fin["tasa_fp"]), "campo_inaturalist_sanas": r4(1 - cs["valor"]) if cs else None,
                                       "etiqueta": "MEDIDO; la de campo mide cambio de dominio (fotos de planta entera con fruto y flor de Vaccinium sobre todo silvestre templado; no es la vista del robot) y no es la especificidad esperada en una finca andina; es mucho menor"},
        "nota": "No hay medición real pantalla->cámara del D1. Las clases del modelo (oídio, alternaria, heliothis) no incluyen antracnosis, Botrytis ni roya.",
    }
    out = R / "detector_extras.yaml"
    out.write_text(yaml.safe_dump(extras, sort_keys=False, allow_unicode=True, width=140), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
