"""Reentrena el modelo B con capturas reales de la cámara del D1 (pantalla → cámara).

1. Preprocesa cada captura igual que el panel: corrección de color + auto-recorte por color de hoja.
2. Verifica que cada captura corresponda a su imagen original (CLIP, top-1 entre las imágenes capturadas).
3. Validación cruzada agrupada (5 pliegues por imagen de origen) SOBRE LAS CAPTURAS:
   B (fijo) frente a B+capturas (entrenado sin las capturas del pliegue).
4. Exporta resultados/ml/modelo_capturas/ (mismo formato que B).
Uso: HF_HUB_OFFLINE=1 .venv/bin/python -I resultados/ml/scripts/entrenar_capturas.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

DATOS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DATOS / "pipeline"))
sys.path.insert(0, str(DATOS / "robot"))
sys.argv = sys.argv[:1]
import panel_demo as P  # noqa: E402  (corregir_color, recorte_por_color)
from predict import load_classifier  # noqa: E402

CLASSES = ["alternaria", "heliothis", "oidio", "sana"]
CAP = DATOS / "resultados/ml/capturas_pantalla"
AUG = DATOS / "resultados/ml/modelo_aug"
OUT = DATOS / "resultados/ml/modelo_capturas"
C = 0.003  # el mismo C que eligió B por validación cruzada


def probe(c=C):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000, class_weight="balanced", random_state=0))


def preprocesar(path: Path) -> Image.Image:
    im = P.corregir_color(Image.open(path).convert("RGB"))
    b = P.recorte_por_color(im)
    return im.crop((b[0], b[1], b[0] + b[2], b[1] + b[3])) if b else im


def metricas(y, Pm, thr):
    y = np.asarray(y)
    enf = y != CLASSES.index("sana")
    sosp = (1 - Pm[:, 3]) >= thr
    masked = Pm.copy(); masked[:, 3] = -1
    pred = np.where(sosp, masked.argmax(1), 3)
    return {"sensibilidad": f"{int((sosp & enf).sum())}/{int(enf.sum())}",
            "falsas_alarmas": f"{int((sosp & ~enf).sum())}/{int((~enf).sum())}",
            "clase_exacta": f"{int((pred == y).sum())}/{len(y)}",
            "acierto_sana_enferma": f"{int((sosp == enf).sum())}/{len(y)}"}


def main() -> None:
    rows = list(csv.DictReader(open(CAP / "manifest.csv")))
    clf = load_classifier(DATOS / "resultados/ml/modelo_aug_B/clip_probe_tiles3_aug_dev.joblib")
    head = joblib.load(DATOS / "resultados/ml/modelo_aug_B/clip_probe_tiles3_aug_dev.joblib")
    thr = json.load(open(DATOS / "resultados/ml/modelo_aug_B/umbral.json"))["umbral"]
    emb = clf.embedder

    caps = [preprocesar(DATOS / r["captura_roi"]) for r in rows]
    srcs = [Image.open(DATOS / r["origen"]).convert("RGB") for r in rows]
    # 2) verificación de correspondencia (embedding global)
    ec = np.asarray(emb.embed_pil(caps)); es = np.asarray(emb.embed_pil(srcs))
    ec /= np.linalg.norm(ec, axis=1, keepdims=True); es /= np.linalg.norm(es, axis=1, keepdims=True)
    S = ec @ es.T
    ok = S.argmax(1) == np.arange(len(rows))
    top3 = (np.argsort(-S, 1)[:, :3] == np.arange(len(rows))[:, None]).any(1)
    print(f"correspondencia top-1: {ok.sum()}/{len(rows)} · top-3: {top3.sum()}/{len(rows)}")
    keep = top3  # tolera vecinos casi idénticos (ráfagas de la misma planta)
    rows = [r for r, k in zip(rows, keep) if k]
    caps = [c for c, k in zip(caps, keep) if k]
    y = np.array([CLASSES.index(r["label"]) for r in rows])
    groups = np.array([Path(r["origen"]).stem.split("_jpg")[0] for r in rows])

    Xc = np.asarray(emb.features_pil(caps, 3))
    # datos de B: train+val limpios + aumentadas (cachés del reentreno anterior)
    def ys(split):
        return np.array([CLASSES.index(r["label"]) for r in csv.DictReader(open(DATOS / f"resultados/ml/drberry_image/splits/{split}.csv"))])
    Xo = np.concatenate([np.load(AUG / "cache/clean_train.npz")["X"], np.load(AUG / "cache/clean_val.npz")["X"]])
    yo = np.concatenate([ys("train"), ys("val")])
    Xa = np.concatenate([np.load(AUG / "cache/var_aug_train.npz")["X"], np.load(AUG / "cache/var_aug_val.npz")["X"]])
    Xa = Xa.reshape(-1, Xo.shape[1]); ya = np.repeat(yo, Xa.shape[0] // len(yo))
    base_X = np.concatenate([Xo, Xa]); base_y = np.concatenate([yo, ya])

    # 3) CV agrupada sobre las capturas
    from sklearn.model_selection import StratifiedGroupKFold
    PB = head["sk_model"].predict_proba(Xc)
    PN = np.zeros_like(PB)
    for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=0).split(Xc, y, groups):
        m = probe().fit(np.concatenate([base_X, Xc[tr]]), np.array(CLASSES)[np.concatenate([base_y, y[tr]])])
        PN[te] = m.predict_proba(Xc[te])
    res = {"n_capturas_usadas": int(len(y)), "descartadas_por_no_coincidir": int((~keep).sum()),
           "B_en_capturas": metricas(y, PB, thr), "B_mas_capturas_CV": metricas(y, PN, thr), "umbral": thr}
    print(json.dumps(res, indent=2, ensure_ascii=False))

    # 4) modelo final con todas las capturas
    OUT.mkdir(parents=True, exist_ok=True)
    final = probe().fit(np.concatenate([base_X, Xc]), np.array(CLASSES)[np.concatenate([base_y, y])])
    nh = dict(head); nh["sk_model"] = final; nh["nota"] = "B + capturas reales de la cámara del D1"
    joblib.dump(nh, OUT / "clip_probe_tiles3_capturas.joblib")
    json.dump({**json.load(open(DATOS / "resultados/ml/modelo_aug_B/umbral.json")), "nota": "umbral de B"},
              open(OUT / "umbral.json", "w"), indent=2)
    json.dump(res, open(OUT / "evaluacion_cv_capturas.json", "w"), indent=2, ensure_ascii=False)
    print("exportado en", OUT)


if __name__ == "__main__":
    main()
