#!/usr/bin/env python
"""Etapa 1: genera imágenes (limpias, aumentadas de cámara, estrés independiente), las preprocesa como el panel
y guarda rasgos CLIP ViT-B-32 laion2b [global, media, máx] con teselas 3x3 y 4x4 (un solo pase de 26 recortes).
Cachés npz en resultados/ml/modelo_luz/cache/. Uso:
    HF_HUB_OFFLINE=1 .venv/bin/python -I resultados/ml/scripts/luz_features.py
"""
from __future__ import annotations

import multiprocessing as mp
import sys
import time
from pathlib import Path

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline"))
sys.path.insert(0, str(D / "resultados/ml/scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

import luz_common as L  # noqa: E402

OUT = D / "resultados/ml/modelo_luz"
CACHE = OUT / "cache"
SPL = D / "resultados/ml/drberry_image/splits"
K_DEV, K_PUB = 6, 3
SEEDS = {"aug_train": 201, "aug_val": 202, "test_aug": 9101, "flip_aug": 9102, "flip_ind": 9103, "pub_aug": 203}


def _work(job):
    kind, path, ss, want_raw = job
    rng = np.random.default_rng(np.random.SeedSequence(list(ss)))
    if kind == "native":  # capturas reales: resolución nativa, como en el panel
        from PIL import ImageOps

        with Image.open(path) as f:
            im = ImageOps.exif_transpose(f).convert("RGB")
    else:
        im = L.cargar(path)
    if kind == "aug":
        im = L.aug_camara(im, rng)[0]
    elif kind == "ind":
        import reentreno_aug as R

        im = R.stress_variant(im, rng)
    pp = L.preprocesar(im)
    return np.asarray(pp, np.uint8), (np.asarray(im, np.uint8) if want_raw else None)


class Feat:
    def __init__(self):
        from clip_baseline import ClipEmbedder
        from common import OPEN_CLIP_CACHE, set_offline_env

        set_offline_env(False)
        self.e = ClipEmbedder("ViT-B-32", "laion2b_s34b_b79k", "auto", OPEN_CLIP_CACHE)

    def many(self, arrs, bs=6):
        """-> (n, 2, 1536): [:,0]=3x3, [:,1]=4x4."""
        from clip_baseline import tile_images

        out = []
        for s in range(0, len(arrs), bs):
            ims = [Image.fromarray(a) for a in arrs[s : s + bs]]
            crops = []
            for im in ims:
                crops += [im] + tile_images(im, 3) + tile_images(im, 4)
            e = self.e.embed_pil(crops).reshape(len(ims), 26, -1)
            g = e[:, 0]
            f3 = np.concatenate([g, e[:, 1:10].mean(1), e[:, 1:10].max(1)], 1)
            f4 = np.concatenate([g, e[:, 10:].mean(1), e[:, 10:].max(1)], 1)
            out.append(np.stack([f3, f4], 1))
        return np.concatenate(out).astype(np.float32)


def run_set(F, pool, name, jobs, shape):
    """jobs: lista de (kind, path, seed_tuple, want_raw). Guarda X_pp (n,2,1536) y X_raw si want_raw."""
    f = CACHE / f"{name}.npz"
    if f.exists():
        return
    t0 = time.time()
    pp, raw, bp, br = [], [], [], []
    want = jobs[0][3]
    for j, (a, r) in enumerate(pool.imap(_work, jobs, chunksize=4)):
        bp.append(a)
        if want:
            br.append(r)
        if len(bp) == 12:
            pp.append(F.many(bp))
            bp = []
            if want:
                raw.append(F.many(br))
                br = []
        if j % 300 == 0:
            print(f"  [{name}] {j}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    if bp:
        pp.append(F.many(bp))
        if want:
            raw.append(F.many(br))
    d = {"pp": np.concatenate(pp).reshape(*shape, 2, -1)}
    if want:
        d["raw"] = np.concatenate(raw).reshape(*shape, 2, -1)
    np.savez(f, **d)
    print(f"  [{name}] listo {time.time() - t0:.0f}s", flush=True)


def public_sets():
    """Fuentes públicas de hojas SANAS, divididas 70/30 por grupo (hoja / imagen de origen / observación)."""
    m = pd.read_csv(D / "resultados/secundarios/manifest_secundarios.csv", keep_default_na=False, dtype=str)
    pd_ = m[(m.fuente == "PlantDoc-OD-recorte") & (m.categoria_eval == "sana_arandano") & (m.revision_visual == "verde_sin_sintomas_visibles") & (m.apto_lado_min_64 == "si")]
    pv = m[(m.fuente == "PlantVillage") & (m.categoria_eval == "sana_arandano")]
    inat = pd.read_csv(D / "raw/campo_ood/manifiesto.csv", keep_default_na=False, dtype=str)
    inat = inat[inat["clase"] == "sana"]
    rows = []
    for src, df, pcol, gcol, cap in (("plantdoc", pd_, "ruta", "grupo", 2), ("plantvillage", pv, "ruta", "grupo", 1), ("inat", inat, "ruta", "obs_id", 1)):
        groups = sorted(set(df[gcol]))
        rng = np.random.default_rng(abs(hash(src)) % 1000 if False else {"plantdoc": 11, "plantvillage": 12, "inat": 13}[src])
        rng.shuffle(groups)
        n_tr = int(round(0.7 * len(groups)))
        tr_g = set(groups[:n_tr])
        seen = {}
        for _, r in df.sample(frac=1, random_state=0).iterrows():
            g = r[gcol]
            path = D / r[pcol] if src != "inat" else D / "raw/campo_ood" / r[pcol]
            part = "train" if g in tr_g else "heldout"
            if part == "train":
                seen[g] = seen.get(g, 0) + 1
                if seen[g] > cap:
                    continue
            rows.append({"fuente": src, "grupo": f"{src}:{g}", "path": str(path), "parte": part})
    return pd.DataFrame(rows)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    rd = lambda s: pd.read_csv(SPL / f"{s}.csv", keep_default_na=False, dtype=str)  # noqa: E731
    tr, va, te = rd("train"), rd("val"), rd("test")
    pub = public_sets()
    pub.to_csv(OUT / "publicas_split.csv", index=False)
    print(pub.groupby(["fuente", "parte"]).agg(n=("path", "size"), grupos=("grupo", "nunique")), flush=True)
    ms = pd.read_csv(D / "resultados/ml/stress/manifest_stress.csv", keep_default_na=False, dtype=str)
    conds = list(dict.fromkeys(ms["dataset"]))
    cap = pd.read_csv(D / "resultados/ml/capturas_pantalla/manifest.csv", dtype=str)
    F = Feat()
    ctx = mp.get_context("spawn")
    with ctx.Pool(6) as pool:
        J = lambda kind, paths, seed=None, n=1, raw=False: [(kind, str(p), (seed or 0, i, k), raw) for i, p in enumerate(paths) for k in range(n)]  # noqa: E731
        run_set(F, pool, "dev_clean", J("clean", list(tr.path) + list(va.path)), (len(tr) + len(va),))
        run_set(F, pool, "dev_aug", J("aug", list(tr.path) + list(va.path), SEEDS["aug_train"], K_DEV), (len(tr) + len(va), K_DEV))
        run_set(F, pool, "test_clean", J("clean", te.path, raw=True), (len(te),))
        run_set(F, pool, "test_aug", J("aug", te.path, SEEDS["test_aug"], 3, True), (len(te), 3))
        run_set(F, pool, "flip_aug", J("aug", te.path, SEEDS["flip_aug"], 10, True), (len(te), 10))
        run_set(F, pool, "flip_ind", J("ind", te.path, SEEDS["flip_ind"], 10, True), (len(te), 10))
        for c in conds:
            sub = ms[ms["dataset"] == c].set_index("source_id").loc[te["source_id"]]
            run_set(F, pool, f"fixed_{c}", J("clean", sub["path"], raw=True), (len(te),))
        run_set(F, pool, "caps", J("native", [D / p for p in cap.captura_roi], raw=True), (len(cap),))
        run_set(F, pool, "caps_src", J("clean", [D / p for p in cap.origen], raw=True), (len(cap),))
        ptr, pho = pub[pub.parte == "train"], pub[pub.parte == "heldout"]
        run_set(F, pool, "pub_train_clean", J("clean", ptr.path), (len(ptr),))
        run_set(F, pool, "pub_train_aug", J("aug", ptr.path, SEEDS["pub_aug"], K_PUB), (len(ptr), K_PUB))
        run_set(F, pool, "pub_held_clean", J("clean", pho.path, raw=True), (len(pho),))
    print("features ok", flush=True)


if __name__ == "__main__":
    main()
