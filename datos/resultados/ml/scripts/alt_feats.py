#!/usr/bin/env python
"""Rasgos nuevos para el experimento alternaria: 3x3, 4x4 y 'recortes de manchas' (3 ventanas centradas en
manchas rojizas/oscuras de la hoja; media y max de CLIP), todo sobre imagen preprocesada como el panel.
Conjuntos: caps (410 x 4 variantes, mismas semillas que camara_features), dr (DrBerry train clean + 3 aug), drtest (68 limpio),
pub (sanas publicas train clean + 1 aug), syn (manchas sinteticas pintadas sobre hojas sanas -> etiqueta alternaria).
Salida: modelo_camara_v2/cache/alt_feats.npz"""
import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
import multiprocessing as mp, time
from alt_common import *
import cv2
from PIL import Image, ImageOps
import luz_common as L

def spot_windows(pp: Image.Image, n=3, frac=0.30):
    a = np.asarray(pp); H, W = a.shape[:2]
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    leaf = (((hsv[..., 0] >= 25) & (hsv[..., 0] <= 95) & (hsv[..., 1] >= 45) & (hsv[..., 2] >= 40)) | ((hsv[..., 0] >= 15) & (hsv[..., 0] < 25) & (hsv[..., 1] >= 70))).astype(np.uint8)
    leaf = cv2.erode(leaf, np.ones((9, 9), np.uint8))
    lab = cv2.cvtColor(a, cv2.COLOR_RGB2LAB).astype(np.float32)
    ok = leaf > 0
    if ok.sum() < 500: ok = np.ones_like(ok)
    ma, mL = np.median(lab[..., 1][ok]), np.median(lab[..., 0][ok])
    sm = np.maximum(0, lab[..., 1] - ma) + 0.5 * np.maximum(0, mL - lab[..., 0])
    sm = cv2.GaussianBlur(sm, (0, 0), max(2, 0.012 * max(H, W))) * ok
    wins = []; r = int(0.12 * max(H, W)); half = int(frac * max(H, W) / 2)
    for _ in range(n):
        y, x = np.unravel_index(np.argmax(sm), sm.shape)
        cx, cy = int(np.clip(x, half, W - half)), int(np.clip(y, half, H - half))
        wins.append((cx - half, cy - half, cx + half, cy + half))
        cv2.circle(sm, (int(x), int(y)), r, 0, -1)
    return [pp.crop(w) for w in wins]

def paint_spots(im: Image.Image, rng):
    a = np.asarray(im.convert("RGB")).astype(np.float32).copy(); H, W = a.shape[:2]
    hsv = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2HSV)
    leaf = ((hsv[..., 0] >= 25) & (hsv[..., 0] <= 95) & (hsv[..., 1] >= 45) & (hsv[..., 2] >= 40)); leaf = cv2.erode(leaf.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    ys, xs = np.where(leaf)
    if len(ys) < 200: return im
    out = a.copy(); n = int(rng.integers(4, 26)); S = max(H, W)
    for _ in range(n):
        j = int(rng.integers(len(ys))); cy, cx = int(ys[j]), int(xs[j]); r = max(1.5, rng.uniform(0.004, 0.013) * S)
        m = np.zeros((H, W), np.float32); cv2.ellipse(m, (cx, cy), (int(r), int(max(1, r * rng.uniform(0.6, 1.0)))), float(rng.uniform(0, 180)), 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), max(0.7, r * 0.35)); col = np.array([rng.uniform(95, 165), rng.uniform(45, 85), rng.uniform(35, 65)], np.float32)
        out = out * (1 - m[..., None] * 0.85) + col * (m[..., None] * 0.85)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def _work(job):
    kind, path, ss = job
    rng = np.random.default_rng(np.random.SeedSequence(list(ss)))
    if kind == "cap":
        with Image.open(path) as f: im0 = ImageOps.exif_transpose(f).convert("RGB")
        i, k = ss[1], ss[2]
        im = im0 if k == 0 else L.aug_camara(im0, rng, 0.4)[0]
    else:
        im = L.cargar(path)
        if kind == "syn": im = paint_spots(im, rng)
        if kind in ("aug", "syn"): im = L.aug_camara(im, rng)[0]
    pp = L.preprocesar(im)
    return np.asarray(pp, np.uint8)

def embed_batch(F, arrs):
    from clip_baseline import tile_images
    out = []
    for a in arrs:
        im = Image.fromarray(a); sp = spot_windows(im)
        crops = [im] + tile_images(im, 3) + tile_images(im, 4) + sp
        out.append(crops)
    flat = [c for cs in out for c in cs]
    e = F.e.embed_pil(flat).reshape(len(arrs), 29, -1)
    g = e[:, 0]
    f3 = np.concatenate([g, e[:, 1:10].mean(1), e[:, 1:10].max(1)], 1)
    f4 = np.concatenate([g, e[:, 10:26].mean(1), e[:, 10:26].max(1)], 1)
    fs = np.concatenate([e[:, 26:].mean(1), e[:, 26:].max(1)], 1)
    return np.stack([f3, f4], 1), fs

def run(F, pool, jobs, name, res):
    t0 = time.time(); A, S, buf = [], [], []
    for j, a in enumerate(pool.imap(_work, jobs, chunksize=4)):
        buf.append(a)
        if len(buf) == 12:
            x, s = embed_batch(F, buf); A.append(x); S.append(s); buf = []
        if j % 300 == 0: print(f"[{name}] {j}/{len(jobs)} {time.time()-t0:.0f}s", flush=True)
    if buf: x, s = embed_batch(F, buf); A.append(x); S.append(s)
    res[name + "_t"] = np.concatenate(A).astype(np.float32); res[name + "_s"] = np.concatenate(S).astype(np.float32)

def main():
    from luz_features import Feat
    F = Feat(); res = {}
    pub = pd.read_csv(ML.parent / "publicas_split.csv"); ptr = pub[pub.parte == "train"]
    assert len(ptr) == len(pt_c)
    sana_tr = [i for i in range(ntr) if ytr[i] == SANA]
    with mp.get_context("spawn").Pool(6) as pool:
        run(F, pool, [("cap", str(D / p), (7001, i, k)) for i, p in enumerate(m.captura_roi) for k in range(4)], "caps", res)
        res["caps_t"] = res["caps_t"].reshape(len(m), 4, 2, -1); res["caps_s"] = res["caps_s"].reshape(len(m), 4, -1)
        run(F, pool, [("clean", p, (0,)) for p in te.path], "drtest", res)
        run(F, pool, [("clean", p, (0,)) for p in tr.path] + [("aug", p, (301, i, k)) for i, p in enumerate(tr.path) for k in range(3)], "dr", res)
        run(F, pool, [("clean", p, (0,)) for p in ptr.path] + [("aug", p, (302, i, 0)) for i, p in enumerate(ptr.path)], "pub", res)
        # sintéticas: manchas pintadas sobre sanas de DrBerry train (4 por imagen) y 120 sanas públicas (1 por imagen)
        sj = [("syn", tr.path.iloc[i], (303, i, k)) for i in sana_tr for k in range(4)] + [("syn", p, (304, i, 0)) for i, p in enumerate(ptr.path.iloc[:120])]
        run(F, pool, sj, "syn", res)
        res["syn_src"] = np.array(list(np.repeat(sana_tr, 4)) + [-1] * 120)
    np.savez(OUT / "cache/alt_feats.npz", **res); print("ok", {k: v.shape for k, v in res.items()})

if __name__ == "__main__":
    main()
