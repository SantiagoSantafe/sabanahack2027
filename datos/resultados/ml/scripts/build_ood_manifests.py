#!/usr/bin/env python
"""Arma el manifiesto OOD (fuera de DrBerry) y su spec para pipeline/ood_eval.py.

Lee SOLO los índices/manifiestos ya producidos por los agentes de adquisición (no descarga nada):
* raw/campo_ood/manifiesto.csv (iNaturalist + Wikimedia Commons; revisión manual = aceptada)
* resultados/secundarios/manifest_secundarios.csv (PlantDoc, recortes PlantDoc-OD y PlantVillage)
* raw/fresa_afzaal2021_datasetninja/indice_imagenes.csv (split test, powdery_mildew_leaf)
* raw/fresa_mendeley_k2ptxmfjhj_test/indice_imagenes.csv (Asymptomatic Strawberry)

Escribe resultados/ml/ood/manifest_ood.csv (path relativo a datos/, label = categoría OOD, group,
dataset, licencia) y resultados/ml/ood/spec_ood.json. Ejecutar desde datos/ con python -I.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
OUT = D / "resultados" / "ml" / "ood"


def campo() -> pd.DataFrame:
    m = pd.read_csv(D / "raw/campo_ood/manifiesto.csv", dtype=str, keep_default_na=False)
    m = m[m["revision_manual"] == "aceptada"]
    cat = {"sana": "campo_sana", "oidio": "campo_oidio", "roya": "campo_roya", "heliothis_oruga": "campo_oruga", "alternaria": "campo_alternaria"}
    grp = [f"inat:{o}" if o else f"commons:{p}" for o, p in zip(m["obs_id"], m["photo_id"])]
    return pd.DataFrame({"path": "raw/campo_ood/" + m["ruta"], "label": m["clase"].map(cat), "group": grp, "dataset": "campo_ood:" + m["fuente"],
                         "licencia": m["licencia"], "detalle": m["nivel_etiqueta"] + "|cultivado=" + m["cultivado_captive"]})


def secundarios() -> pd.DataFrame:
    m = pd.read_csv(D / "resultados/secundarios/manifest_secundarios.csv", dtype=str, keep_default_na=False)
    rows = []
    pv = m[m["fuente"] == "PlantVillage"]
    pv_cat = {"Blueberry___healthy": "pv_arandano_sano", "Cherry_(including_sour)___Powdery_mildew": "pv_cerezo_oidio",
              "Squash___Powdery_mildew": "pv_calabaza_oidio", "Potato___Early_blight": "pv_papa_tizon_temprano",
              "Tomato___Early_blight": "pv_tomate_tizon_temprano"}
    for _, r in pv.iterrows():
        rows.append({"path": r["ruta"], "label": pv_cat[r["clase_original"]], "group": r["grupo"] or f"img:{r['ruta']}",
                     "dataset": "PlantVillage", "licencia": r["licencia"], "detalle": r["clase_original"]})
    pdc = m[(m["fuente"] == "PlantDoc-OD-recorte") & (m["apto_lado_min_64"] == "si")]
    for _, r in pdc.iterrows():
        if r["categoria_eval"] == "sana_arandano":
            lab = {"verde_sin_sintomas_visibles": "pdc_arandano_verde", "coloracion_rojiza_otono_o_brotes": "pdc_arandano_rojizo",
                   "sintomas_o_desorden_visible": "pdc_arandano_sintomas"}.get(r["revision_visual"])
        elif r["categoria_eval"] == "oidio_otra_especie":
            lab = "pdc_calabaza_oidio"
        elif r["categoria_eval"] == "alternaria_otra_especie":
            lab = "pdc_tizon_temprano"
        else:
            lab = None
        if lab:
            rows.append({"path": r["ruta"], "label": lab, "group": f"src:{r['grupo']}", "dataset": "PlantDoc-OD-recorte",
                         "licencia": r["licencia"], "detalle": r["clase_original"]})
    pd_full = m[(m["fuente"] == "PlantDoc") & (m["duplicado_phash"] == "no")]
    for _, r in pd_full.iterrows():
        lab = {"otra_enfermedad_otra_especie": "pd_otra_enfermedad", "sana_otra_especie": "pd_otra_especie_sana"}.get(r["categoria_eval"])
        if lab:
            rows.append({"path": r["ruta"], "label": lab, "group": f"img:{r['ruta']}", "dataset": "PlantDoc", "licencia": r["licencia"],
                         "detalle": r["clase_original"]})
    return pd.DataFrame(rows)


def fresa() -> pd.DataFrame:
    a = pd.read_csv(D / "raw/fresa_afzaal2021_datasetninja/indice_imagenes.csv", dtype=str, keep_default_na=False)
    a = a[(a["split"] == "test") & (a["clases"] == "powdery_mildew_leaf")]
    fa = pd.DataFrame({"path": "raw/fresa_afzaal2021_datasetninja/" + a["imagen"], "label": "fresa_oidio_hoja",
                       "group": "img:" + a["imagen"], "dataset": "Afzaal2021 (Dataset Ninja) test", "licencia": "CC BY 4.0", "detalle": a["clases"]})
    b = pd.read_csv(D / "raw/fresa_mendeley_k2ptxmfjhj_test/indice_imagenes.csv", dtype=str, keep_default_na=False)
    b = b[b["clases"] == "Asymptomatic Strawberry"]
    fb = pd.DataFrame({"path": "raw/fresa_mendeley_k2ptxmfjhj_test/" + b["imagen"], "label": "fresa_sana",
                       "group": "img:" + b["nombre_original"], "dataset": "Mendeley k2ptxmfjhj test", "licencia": "CC BY-NC 4.0", "detalle": b["clases"]})
    return pd.concat([fa, fb], ignore_index=True)


SPEC = {
    "campo_sana": {"esperado": "sana", "descripcion": "Hoja de Vaccinium sana en campo (iNaturalist/Commons; zona templada)"},
    "campo_oidio": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "campo_sana", "descripcion": "Oídio (Erysiphe vaccinii) en Vaccinium, campo, grado research"},
    "campo_roya": {"esperado": "enfermedad", "referencia": "campo_sana", "descripcion": "Roya (Naohidemyces/Thekopsora) en Vaccinium: enfermedad NO entrenada"},
    "campo_oruga": {"esperado": "enfermedad", "clase_modelo": "heliothis", "referencia": "campo_sana", "descripcion": "PROXY: orugas (no Heliothinae) sobre Vaccinium"},
    "campo_alternaria": {"esperado": "enfermedad", "clase_modelo": "alternaria", "referencia": "campo_sana", "descripcion": "Alternaria en Vaccinium, needs_id: NO evaluable (3 fotos)"},
    "pv_arandano_sano": {"esperado": "sana", "descripcion": "E1 PlantVillage arándano sano (laboratorio, fondo uniforme; 160 hojas)"},
    "pv_cerezo_oidio": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "pv_arandano_sano", "descripcion": "E4 oídio en cerezo (PlantVillage)"},
    "pv_calabaza_oidio": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "pv_arandano_sano", "descripcion": "E4 oídio en calabaza (PlantVillage)"},
    "pv_papa_tizon_temprano": {"esperado": "enfermedad", "clase_modelo": "alternaria", "referencia": "pv_arandano_sano", "descripcion": "E5 tizón temprano (Alternaria solani) en papa, proxy débil"},
    "pv_tomate_tizon_temprano": {"esperado": "enfermedad", "clase_modelo": "alternaria", "referencia": "pv_arandano_sano", "descripcion": "E5 tizón temprano en tomate, proxy débil"},
    "pdc_arandano_verde": {"esperado": "sana", "descripcion": "E2 recortes PlantDoc de hoja de arándano verde sin síntomas (web)"},
    "pdc_arandano_rojizo": {"esperado": "sana", "descripcion": "E3 recortes PlantDoc de hoja de arándano rojiza/otoñal (no enfermedad)"},
    "pdc_arandano_sintomas": {"esperado": "enfermedad", "referencia": "pdc_arandano_verde", "descripcion": "E3 recortes PlantDoc de arándano con síntomas o desorden (no entrenado)"},
    "pdc_calabaza_oidio": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "pdc_arandano_verde", "descripcion": "E4 recortes PlantDoc de oídio en calabaza"},
    "pdc_tizon_temprano": {"esperado": "enfermedad", "clase_modelo": "alternaria", "referencia": "pdc_arandano_verde", "descripcion": "E5 recortes PlantDoc de tizón temprano (papa/tomate)"},
    "pd_otra_enfermedad": {"esperado": "enfermedad", "referencia": "pd_otra_especie_sana", "descripcion": "E6 PlantDoc: otras enfermedades en otras especies (imagen completa)"},
    "pd_otra_especie_sana": {"esperado": "sana", "descripcion": "E7 PlantDoc: hoja sana de OTRA especie (no es arándano)"},
    "fresa_oidio_hoja": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "fresa_sana", "descripcion": "Oídio en hoja de fresa (Afzaal 2021, split test)"},
    "fresa_sana": {"esperado": "sana", "descripcion": "Fresa asintomática (Mendeley k2ptxmfjhj, split test; CC BY-NC)"},
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.concat([campo(), secundarios(), fresa()], ignore_index=True)
    exists = df["path"].map(lambda p: (D / p).is_file())
    if (~exists).any():
        print(f"AVISO: {int((~exists).sum())} rutas no existen; se omiten (ej. {df.loc[~exists, 'path'].head(3).tolist()})")
    df = df[exists].reset_index(drop=True)
    df.insert(0, "item_id", [f"ood/{i:05d}" for i in range(len(df))])
    df.to_csv(OUT / "manifest_ood.csv", index=False, lineterminator="\n")
    (OUT / "spec_ood.json").write_text(json.dumps(SPEC, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(df.groupby("label").agg(n=("path", "size"), grupos=("group", "nunique")).to_string())
    print(f"total {len(df)} -> {OUT / 'manifest_ood.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
