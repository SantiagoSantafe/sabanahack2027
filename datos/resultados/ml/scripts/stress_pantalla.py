#!/usr/bin/env python
"""Prueba de estrés SINTÉTICA de la cadena pantalla -> cámara del D1 sobre el test congelado (modo imagen).

No reemplaza la medición real con la cámara del robot (pendiente): solo estima cuánto se degradan los
modelos ante perturbaciones plausibles al fotografiar una pantalla. Parámetros = SUPUESTOS.

Escribe resultados/ml/stress/imgs/<perturbacion>/*.jpg (derivados de DrBerry CC BY 4.0, uso interno;
no redistribuir) y resultados/ml/stress/manifest_stress.csv (label = verdad, group = ráfaga, dataset = perturbación).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
TEST = D / "resultados/ml/drberry_image/splits/test.csv"
OUT = D / "resultados/ml/stress"


def baja_res(im: Image.Image) -> Image.Image:  # la imagen ocupa ~256 px del cuadro de la cámara
    w, h = im.size
    return im.resize((256, int(256 * h / w)), Image.Resampling.BILINEAR).resize((w, h), Image.Resampling.BILINEAR)


def desenfoque(im: Image.Image) -> Image.Image:
    return im.filter(ImageFilter.GaussianBlur(radius=3))


def reflejo(im: Image.Image) -> Image.Image:  # brillo alto y contraste bajo (reflejo en la pantalla)
    return ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(1.25)).enhance(0.7)


def balance_blancos(im: Image.Image) -> Image.Image:  # tono frío/azulado de pantalla LED
    a = np.asarray(im, dtype=float) * np.array([0.88, 1.0, 1.12])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def ruido(im: Image.Image, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)
    a = np.asarray(im, dtype=float) + rng.normal(0, 10, size=np.asarray(im).shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def perspectiva(im: Image.Image) -> Image.Image:  # pantalla ligeramente girada y fondo oscuro alrededor
    w, h = im.size
    r = im.rotate(7, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(20, 20, 20))
    return ImageOps.pad(r, (w, h), color=(20, 20, 20))


def jpeg(im: Image.Image, q: int = 30) -> Image.Image:
    from io import BytesIO

    b = BytesIO()
    im.save(b, format="JPEG", quality=q)
    b.seek(0)
    return Image.open(b).convert("RGB")


def combinada(im: Image.Image) -> Image.Image:
    return jpeg(ruido(reflejo(balance_blancos(desenfoque(baja_res(perspectiva(im)))))), 50)


PERTS = {"original": lambda im: im, "baja_res_256": baja_res, "desenfoque_r3": desenfoque, "reflejo": reflejo,
         "balance_blancos_frio": balance_blancos, "ruido_s10": ruido, "perspectiva_7g": perspectiva, "jpeg_q30": jpeg,
         "combinada": combinada}


def main() -> int:
    t = pd.read_csv(TEST, dtype=str, keep_default_na=False)
    rows = []
    for name, fn in PERTS.items():
        d = OUT / "imgs" / name
        d.mkdir(parents=True, exist_ok=True)
        for _, r in t.iterrows():
            with Image.open(r["path"]) as im:
                x = fn(ImageOps.exif_transpose(im).convert("RGB"))
            dest = d / (Path(r["path"]).stem + ".jpg")
            x.save(dest, quality=92)
            rows.append({"item_id": f"{name}/{r['item_id']}", "path": str(dest), "label": r["label"], "group": r["group"], "source_id": r["source_id"], "dataset": name})
    pd.DataFrame(rows).to_csv(OUT / "manifest_stress.csv", index=False, lineterminator="\n")
    print(f"{len(rows)} imágenes en {len(PERTS)} condiciones -> {OUT / 'manifest_stress.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
