#!/usr/bin/env python
"""Rasgos CLIP (3x3) de las 410 capturas nuevas de la cámara del D1 (timestamp >= 2026-10-24T01):
original (k=0) y 3 aumentos leves (k=1..3, aug_camara strength 0.4), crudos y preprocesados como el panel.
Salida: resultados/ml/modelo_camara/cache/caps_nuevas.npz y filtro (estadísticas de calidad).
"""
import multiprocessing as mp, sys, time
from pathlib import Path
D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline")); sys.path.insert(0, str(D / "resultados/ml/scripts"))
import numpy as np, pandas as pd, cv2
from PIL import Image, ImageOps
import luz_common as L
K = 3; STR = 0.4

def _work(job):
    path, i = job
    with Image.open(path) as f:
        im0 = ImageOps.exif_transpose(f).convert("RGB")
    raws, pps = [], []
    st = {}
    for k in range(K + 1):
        im = im0 if k == 0 else L.aug_camara(im0, np.random.default_rng(np.random.SeedSequence([7001, i, k])), STR)[0]
        c = L.corregir_color(im)
        b = L.recorte_por_color(c)
        pp = c.crop((b[0], b[1], b[0] + b[2], b[1] + b[3])) if b else c
        if k == 0:
            g = np.asarray(im.convert("L"), np.float32)
            hsv = cv2.cvtColor(np.asarray(c), cv2.COLOR_RGB2HSV)
            st = dict(brillo=float(g.mean()), contraste=float(g.std()), hay_hoja=b is not None,
                      area_recorte=(b[2] * b[3] / (c.width * c.height)) if b else 1.0,
                      sat_media=float(hsv[..., 1].mean()))
        raws.append(np.asarray(im, np.uint8)); pps.append(np.asarray(pp, np.uint8))
    return raws, pps, st

def main():
    from luz_features import Feat
    m = pd.read_csv(D / "resultados/ml/capturas_pantalla/manifest.csv", dtype=str)
    m = m[m.timestamp >= "2026-10-24T01"].reset_index(drop=True)
    F = Feat(); t0 = time.time()
    raw, pp, stats = [], [], []
    jobs = [(str(D / p), i) for i, p in enumerate(m.captura_roi)]
    with mp.get_context("spawn").Pool(6) as pool:
        bufr, bufp = [], []
        for j, (r, p, st) in enumerate(pool.imap(_work, jobs, chunksize=2)):
            bufr += r; bufp += p; stats.append(st)
            if len(bufr) >= 16:
                raw.append(F.many(bufr)[:, 0]); pp.append(F.many(bufp)[:, 0]); bufr, bufp = [], []
            if j % 50 == 0: print(j, f"{time.time()-t0:.0f}s", flush=True)
        if bufr: raw.append(F.many(bufr)[:, 0]); pp.append(F.many(bufp)[:, 0])
    raw = np.concatenate(raw).reshape(len(m), K + 1, -1); pp = np.concatenate(pp).reshape(len(m), K + 1, -1)
    np.savez(D / "resultados/ml/modelo_camara/cache/caps_nuevas.npz", raw=raw, pp=pp)
    pd.concat([m, pd.DataFrame(stats)], axis=1).to_csv(D / "resultados/ml/modelo_camara/caps_nuevas_stats.csv", index=False)
    print("ok", raw.shape, f"{time.time()-t0:.0f}s")
if __name__ == "__main__":
    main()
