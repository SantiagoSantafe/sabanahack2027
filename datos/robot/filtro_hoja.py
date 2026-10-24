"""Filtro "¿hay una hoja en primer plano?" con CLIP cero-shot (el mismo CLIP del clasificador).

p_hoja = suma de probabilidades de los textos de hoja frente a textos de otras cosas (personas,
muebles, piso, pantalla vacía, arbusto entero...). Si p_hoja < umbral: "sin hoja", no se alerta.
Calibración: python3 robot/filtro_hoja.py  (usa las 68 hojas del test y los cuadros de la sala).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DATOS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATOS / "pipeline"))

HOJA = [
    "a close-up photo of a plant leaf",
    "a close-up photo of a green leaf",
    "a photo of a leaf with brown spots",
    "a photo of a leaf with white powdery mildew",
    "a photo of a leaf eaten by a caterpillar",
    "a close-up photo of blueberry leaves",
]
OTRO = [
    "a photo of a person", "a photo of people sitting on chairs", "a photo of a person's legs",
    "a photo of a chair", "a photo of a carpet floor", "a photo of an office room",
    "a photo of a ceiling with lights", "a photo of a laptop", "a photo of a blank computer screen",
    "a photo of a backpack", "a photo of a whole bush with berries", "a photo of blueberries fruit",
    "a photo of a hand", "a photo of a table",
]
UMBRAL_DEFECTO = 0.5


class FiltroHoja:
    def __init__(self, embedder) -> None:
        self.emb = embedder
        t = np.asarray(embedder.embed_text(HOJA + OTRO), dtype=np.float32)
        self.text = t / np.linalg.norm(t, axis=1, keepdims=True)
        self.n = len(HOJA)
        cfg = DATOS / "robot/filtro_hoja.json"
        self.umbral = json.load(open(cfg))["umbral"] if cfg.exists() else UMBRAL_DEFECTO

    def p_hoja(self, ims) -> np.ndarray:
        e = np.asarray(self.emb.embed_pil(ims), dtype=np.float32)
        e = e / np.linalg.norm(e, axis=1, keepdims=True)
        z = 100.0 * e @ self.text.T
        z = np.exp(z - z.max(axis=1, keepdims=True))
        p = z / z.sum(axis=1, keepdims=True)
        return p[:, : self.n].sum(axis=1)


def calibrar() -> None:
    from predict import load_classifier

    clf = load_classifier(DATOS / "resultados/ml/modelo_final/clip_probe_tiles3.joblib")
    f = FiltroHoja(clf.embedder)
    rows = list(csv.DictReader(open(DATOS / "resultados/ml/drberry_image/splits/test_relativo.csv")))
    hojas = f.p_hoja([Image.open(DATOS / r["path"]).convert("RGB") for r in rows])
    otros_paths = sorted((DATOS / "resultados/ml/capturas_d1").rglob("*.jpg"))
    otros_ims = []
    for p in otros_paths:  # cuadro completo y 4 recortes por cuadro de la sala
        im = Image.open(p).convert("RGB")
        W, H = im.size
        otros_ims.append(im)
        for x, y in ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)):
            otros_ims.append(im.crop((int(x * W), int(y * H), int((x + 0.5) * W), int((y + 0.5) * H))))
    otros = f.p_hoja(otros_ims) if otros_ims else np.array([])
    print(f"hojas del test (n={len(hojas)}): min {hojas.min():.3f}  p5 {np.percentile(hojas,5):.3f}  mediana {np.median(hojas):.3f}")
    if len(otros):
        print(f"sala (n={len(otros)}): max {otros.max():.3f}  p95 {np.percentile(otros,95):.3f}  mediana {np.median(otros):.3f}")
    # umbral: deja pasar >= 97 % de las hojas del test y queda por encima de lo visto en la sala
    u = float(np.percentile(hojas, 3))
    if len(otros):
        u = max(min(u, 0.9), float(otros.max()) + 0.01) if otros.max() < u else u
    print(f"umbral elegido: {u:.3f} · hojas que pasan {np.mean(hojas >= u)*100:.0f}% · sala rechazada {np.mean(otros < u)*100 if len(otros) else 0:.0f}%")
    json.dump({"umbral": round(u, 4), "hojas_pasan": float(np.mean(hojas >= u)), "sala_rechazada": float(np.mean(otros < u)) if len(otros) else None,
               "n_hojas": int(len(hojas)), "n_sala": int(len(otros))}, open(DATOS / "robot/filtro_hoja.json", "w"), indent=2)


if __name__ == "__main__":
    calibrar()
