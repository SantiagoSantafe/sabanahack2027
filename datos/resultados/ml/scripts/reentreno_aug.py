#!/usr/bin/env python
"""Reentrena la sonda CLIP teselas 3x3 con aumentos "pantalla vista por cámara" y la compara con el modelo final.

Todo se escribe en resultados/ml/modelo_aug/ (NO toca modelo_final/). Uso (desde datos/):
    HF_HUB_OFFLINE=1 .venv/bin/python -I resultados/ml/scripts/reentreno_aug.py
Etapas con caché npz (cache/): rasgos de limpio, aumentadas de train/val (K=5), y variantes de test.
"""
from __future__ import annotations

import io
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageEnhance, ImageFilter, ImageOps  # noqa: E402

import augment_screen as AS  # noqa: E402

SPL = D / "resultados/ml/drberry_image/splits"
OUT = D / "resultados/ml/modelo_aug"
CACHE = OUT / "cache"
K = 5
CLASSES = ["alternaria", "heliothis", "oidio", "sana"]
SEEDS = {"aug_train": 101, "aug_val": 102, "test_aug": 9001, "flip_aug": 9002, "flip_stress": 9003}
N_TEST_AUG, N_FLIP = 3, 10


# ------------------------------------------------------------------ estrés independiente (no usa augment_screen)
def stress_variant(im: Image.Image, rng: np.random.Generator) -> Image.Image:
    """Variante aleatoria de las perturbaciones de stress_pantalla.py (subconjunto de 2-5 con parámetros muestreados)."""
    W, H = im.size
    ops = ["perspectiva", "baja_res", "desenfoque", "balance", "reflejo", "ruido", "jpeg"]
    pick = [o for o in ops if rng.random() < 0.55] or [ops[int(rng.integers(len(ops)))]]
    for o in ops:  # orden fijo de la cadena
        if o not in pick:
            continue
        if o == "perspectiva":
            ang = float(rng.uniform(4, 10)) * rng.choice([-1, 1])
            r = im.rotate(ang, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(20, 20, 20))
            im = ImageOps.pad(r, (W, H), color=(20, 20, 20))
        elif o == "baja_res":
            s = int(rng.uniform(180, 330))
            im = im.resize((s, int(s * H / W)), Image.Resampling.BILINEAR).resize((W, H), Image.Resampling.BILINEAR)
        elif o == "desenfoque":
            im = im.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(2, 4.5))))
        elif o == "balance":
            a = np.asarray(im, dtype=float) * np.array([rng.uniform(0.84, 0.92), 1.0, rng.uniform(1.08, 1.16)])
            im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        elif o == "reflejo":
            im = ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(rng.uniform(1.15, 1.4))).enhance(rng.uniform(0.55, 0.8))
        elif o == "ruido":
            a = np.asarray(im, dtype=float) + rng.normal(0, rng.uniform(6, 14), size=(H, W, 3))
            im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        elif o == "jpeg":
            b = io.BytesIO()
            im.save(b, format="JPEG", quality=int(rng.integers(25, 60)))
            b.seek(0)
            im = Image.open(b).convert("RGB")
    return im


def _work(job):
    kind, path, ss = job
    rng = np.random.default_rng(np.random.SeedSequence(list(ss)))
    with Image.open(path) as f:
        im = ImageOps.exif_transpose(f).convert("RGB")
    out = AS.augment(im, rng)[0] if kind == "aug" else stress_variant(im, rng)
    return np.asarray(out, dtype=np.uint8)


# ------------------------------------------------------------------ rasgos
class Feat:
    def __init__(self):
        from clip_baseline import ClipEmbedder
        from common import OPEN_CLIP_CACHE, set_offline_env

        set_offline_env(False)
        self.e = ClipEmbedder("ViT-B-32", "laion2b_s34b_b79k", "auto", OPEN_CLIP_CACHE)

    def many(self, ims, bs=8):
        out = []
        for s in range(0, len(ims), bs):
            out.append(self.e.features_pil([Image.fromarray(a) if isinstance(a, np.ndarray) else a for a in ims[s : s + bs]], 3))
        return np.concatenate(out)


def feats_clean(F: Feat, name: str, paths: list[str]) -> np.ndarray:
    f = CACHE / f"clean_{name}.npz"
    if f.exists():
        return np.load(f)["X"]
    ims = []
    for p in paths:
        with Image.open(p) as im:
            ims.append(ImageOps.exif_transpose(im).convert("RGB"))
    X = F.many(ims)
    np.savez(f, X=X)
    return X


def feats_variants(F: Feat, name: str, kind: str, paths: list[str], n: int, seed: int, pool) -> np.ndarray:
    """Rasgos (len(paths), n, 1536) de n variantes por imagen (semilla por (seed, i, k))."""
    f = CACHE / f"var_{name}.npz"
    if f.exists():
        return np.load(f)["X"]
    jobs = [(kind, p, (seed, i, k)) for i, p in enumerate(paths) for k in range(n)]
    t0 = time.time()
    res, buf = [], []
    for j, a in enumerate(pool.imap(_work, jobs, chunksize=4)):
        buf.append(a)
        if len(buf) == 16:
            res.append(F.many(buf, 8))
            buf = []
        if j % 200 == 0:
            print(f"  [{name}] {j}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    if buf:
        res.append(F.many(buf, 8))
    X = np.concatenate(res).reshape(len(paths), n, -1)
    np.savez(f, X=X)
    print(f"  [{name}] listo en {time.time() - t0:.0f}s", flush=True)
    return X


# ------------------------------------------------------------------ métricas
def decide(P: np.ndarray, thr: float, classes=CLASSES) -> np.ndarray:
    hi = classes.index("sana")
    score = 1 - P[:, hi]
    m = P.copy()
    m[:, hi] = -np.inf
    return np.where(score >= thr, m.argmax(1), hi)


def count_cols(y: np.ndarray, pred: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """(numerador, denominador) por fila para cada métrica."""
    san = CLASSES.index("sana")
    dis, sano = y != san, y == san
    sosp = pred != san
    d = {"sens": (dis & sosp, dis), "fp": (sano & sosp, sano), "acc": (pred == y, np.ones_like(y, bool))}
    for i, c in enumerate(CLASSES):
        d[f"rec_{c}"] = ((y == i) & (pred == i), y == i)
    return {k: (a.astype(float), b.astype(float)) for k, (a, b) in d.items()}


def boot_ci(cols, groups, n_boot=1000, seed=0):
    ug, inv = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(seed)
    agg = {k: (np.bincount(inv, a, len(ug)), np.bincount(inv, b, len(ug))) for k, (a, b) in cols.items()}
    pick = rng.integers(0, len(ug), size=(n_boot, len(ug)))
    out = {}
    for k, (a, b) in agg.items():
        num, den = a[pick].sum(1), b[pick].sum(1)
        r = num[den > 0] / den[den > 0]
        out[k] = (float(np.quantile(r, 0.025)), float(np.quantile(r, 0.975))) if len(r) else (np.nan, np.nan)
    return out


def summarize(y, pred, groups):
    cols = count_cols(y, pred)
    pt = {k: float(a.sum() / b.sum()) if b.sum() else np.nan for k, (a, b) in cols.items()}
    ic = boot_ci(cols, groups)
    cm = np.bincount(y * 4 + pred, minlength=16).reshape(4, 4)
    return pt, ic, cm, {k: (int(a.sum()), int(b.sum())) for k, (a, b) in cols.items()}


def flip_stats(pred_clean, pred_var, groups):
    """pred_var: (n, v). flip = % de variantes con clase distinta a la de la imagen limpia."""
    n, v = pred_var.shape
    san = CLASSES.index("sana")
    flip = (pred_var != pred_clean[:, None]).astype(float)
    flip_bin = ((pred_var != san) != (pred_clean[:, None] != san)).astype(float)
    incons = np.array([len(set(r.tolist())) > 1 for r in pred_var], float)
    res = {}
    ug, inv = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(0)
    pick = rng.integers(0, len(ug), size=(1000, len(ug)))
    for k, (num, den) in {"flip_clase": (flip.sum(1), np.full(n, v)), "flip_binario": (flip_bin.sum(1), np.full(n, v)), "inconsistente": (incons, np.ones(n))}.items():
        a, b = np.bincount(inv, num, len(ug)), np.bincount(inv, den.astype(float), len(ug))
        r = a[pick].sum(1) / b[pick].sum(1)
        res[k] = (float(num.sum() / den.sum()), float(np.quantile(r, 0.025)), float(np.quantile(r, 0.975)))
    return res


# ------------------------------------------------------------------ entrenamiento
Cs = (0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)


def make_probe(c):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000, class_weight="balanced", random_state=0))


def cv_select(Xo, Xa, y, g, seed=0):
    """C por CV agrupada: entrena con originales+aumentadas de los pliegues de train (Xa: (n,K,d) o None) y puntúa
    macro-F1 en los ORIGINALES fuera de pliegue. Devuelve (C, búsqueda, P_oof del mejor C sobre originales)."""
    from sklearn.metrics import f1_score
    from sklearn.model_selection import StratifiedGroupKFold

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    folds = list(cv.split(Xo, y, g))
    best, search = None, []
    for c in Cs:
        P = np.zeros((len(y), 4))
        for tr, te in folds:
            X = Xo[tr] if Xa is None else np.concatenate([Xo[tr], Xa[tr].reshape(-1, Xo.shape[1])])
            yy = y[tr] if Xa is None else np.concatenate([y[tr], np.repeat(y[tr], Xa.shape[1])])
            P[te] = make_probe(c).fit(X, np.array(CLASSES)[yy]).predict_proba(Xo[te])
        f1 = f1_score(y, P.argmax(1), average="macro")
        search.append({"C": c, "macro_f1_oof": float(f1)})
        if best is None or f1 > best[0] + 1e-12:
            best = (f1, c, P)
    return best[1], search, best[2]


def fit_full(Xo, Xa, y, c):
    X = Xo if Xa is None else np.concatenate([Xo, Xa.reshape(-1, Xo.shape[1])])
    yy = y if Xa is None else np.concatenate([y, np.repeat(y, Xa.shape[1])])
    return make_probe(c).fit(X, np.array(CLASSES)[yy])


def thr_for(P, y, target=0.9):
    import metrics as M

    return M.choose_threshold(y != CLASSES.index("sana"), 1 - P[:, 3], target)


# ------------------------------------------------------------------ main
def main():
    import joblib

    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    rd = lambda s: pd.read_csv(SPL / f"{s}.csv", keep_default_na=False, dtype=str)  # noqa: E731
    tr, va, te = rd("train"), rd("val"), rd("test")
    for df in (tr, va, te):
        assert all(Path(p).exists() for p in df["path"]), "rutas rotas"
    yi = lambda df: np.array([CLASSES.index(c) for c in df["label"]])  # noqa: E731
    ytr, yva, yte = yi(tr), yi(va), yi(te)
    gte = te["group"].to_numpy()
    F = Feat()
    ctx = mp.get_context("spawn")
    with ctx.Pool(5) as pool:
        Xtr, Xva, Xte = (feats_clean(F, n, d["path"].tolist()) for n, d in (("train", tr), ("val", va), ("test", te)))
        Atr = feats_variants(F, "aug_train", "aug", tr["path"].tolist(), K, SEEDS["aug_train"], pool)
        Ava = feats_variants(F, "aug_val", "aug", va["path"].tolist(), K, SEEDS["aug_val"], pool)
        Tte = feats_variants(F, "test_aug", "aug", te["path"].tolist(), N_TEST_AUG, SEEDS["test_aug"], pool)
        Fa = feats_variants(F, "flip_aug", "aug", te["path"].tolist(), N_FLIP, SEEDS["flip_aug"], pool)
        Fs = feats_variants(F, "flip_stress", "stress", te["path"].tolist(), N_FLIP, SEEDS["flip_stress"], pool)
    # estrés fijo de tabla_stress (9 condiciones ya generadas)
    ms = pd.read_csv(D / "resultados/ml/stress/manifest_stress.csv", keep_default_na=False, dtype=str)
    conds = list(dict.fromkeys(ms["dataset"]))
    fixed = {}
    for c in conds:
        sub = ms[ms["dataset"] == c].set_index("source_id").loc[te["source_id"]]
        fixed[c] = feats_clean(F, f"stress_{c}", sub["path"].tolist())
    print("rasgos listos", flush=True)

    # ---- modelos
    models = {}
    # F: final (no se modifica, solo se carga)
    hF = joblib.load(D / "resultados/ml/modelo_final/clip_probe_tiles3.joblib")
    assert hF["classes"] == CLASSES
    thrF = json.load(open(D / "resultados/ml/modelo_final/umbral.json"))["umbral"]
    models["F_final(train+val)"] = (hF["sk_model"], thrF, {"C": hF["info"]["C_elegido"], "umbral_en": "OOF dev (final)"})
    # A0: control sin aumentos, train-only
    c0, s0, _ = cv_select(Xtr, None, ytr, tr["group"].to_numpy())
    m0 = fit_full(Xtr, None, ytr, c0)
    t0 = thr_for(m0.predict_proba(Xva), yva)
    models["A0_train_sin_aug"] = (m0, t0["umbral"], {"C": c0, "busqueda": s0, "umbral_en": "val limpio", "val": {k: t0[k] for k in ("tp", "fp", "fn", "tn", "sensibilidad", "tasa_fp")}})
    # A: train + aumentadas (spec)
    cA, sA, _ = cv_select(Xtr, Atr, ytr, tr["group"].to_numpy())
    mA = fit_full(Xtr, Atr, ytr, cA)
    tA = thr_for(mA.predict_proba(Xva), yva)
    models["A_aug_train"] = (mA, tA["umbral"], {"C": cA, "busqueda": sA, "umbral_en": "val limpio", "val": {k: tA[k] for k in ("tp", "fp", "fn", "tn", "sensibilidad", "tasa_fp")}})
    # Au: mismo A, umbral en val limpio + val aumentado (extra)
    Pv = mA.predict_proba(Xva)
    Pva = mA.predict_proba(Ava.reshape(-1, Ava.shape[-1]))
    tAu = thr_for(np.concatenate([Pv, Pva]), np.concatenate([yva, np.repeat(yva, K)]))
    models["Au_aug_train_umbral_val+aug"] = (mA, tAu["umbral"], {"C": cA, "umbral_en": "val limpio + val aumentado", "val": {k: tAu[k] for k in ("tp", "fp", "fn", "tn", "sensibilidad", "tasa_fp")}})
    # B: dev=train+val con aumentadas, C y umbral por CV agrupada (mismo protocolo que el final)
    Xd, Ad = np.concatenate([Xtr, Xva]), np.concatenate([Atr, Ava])
    yd, gd = np.concatenate([ytr, yva]), np.concatenate([tr["group"].to_numpy(), va["group"].to_numpy()])
    cB, sB, PoofB = cv_select(Xd, Ad, yd, gd)
    mB = fit_full(Xd, Ad, yd, cB)
    tB = thr_for(PoofB, yd)
    models["B_aug_dev(train+val)"] = (mB, tB["umbral"], {"C": cB, "busqueda": sB, "umbral_en": "OOF dev limpio (como el final)", "val": {k: tB[k] for k in ("tp", "fp", "fn", "tn", "sensibilidad", "tasa_fp")}})
    print({k: (v[2]["C"], round(v[1], 4)) for k, v in models.items()}, flush=True)

    # ---- evaluación
    rows, cms, flips = [], {}, []
    stress_names = [c for c in conds if c != "original"]
    for mname, (m, thr, info) in models.items():
        assert [str(c) for c in m.classes_] == CLASSES, (mname, list(m.classes_))
        pc = decide(m.predict_proba(Xte), thr)
        sets = {"test_limpio": (m.predict_proba(Xte), yte, gte)}
        Pt = m.predict_proba(Tte.reshape(-1, Tte.shape[-1]))
        sets["test_aug_propios(x3)"] = (Pt, np.repeat(yte, N_TEST_AUG), np.repeat(gte, N_TEST_AUG))
        Pf = {c: m.predict_proba(fixed[c]) for c in conds}
        sets["estres_sintetico(8 pert.)"] = (np.concatenate([Pf[c] for c in stress_names if c != "combinada"]), np.tile(yte, len(stress_names) - 1), np.tile(gte, len(stress_names) - 1))
        sets["estres_combinada"] = (Pf["combinada"], yte, gte)
        for sname, (P, y, g) in sets.items():
            pt, ic, cm, cnt = summarize(y, decide(P, thr), g)
            cms[f"{mname}|{sname}"] = cm.tolist()
            r = {"modelo": mname, "conjunto": sname, "n": len(y), "umbral": thr}
            for k in pt:
                r[k], r[k + "_lo"], r[k + "_hi"] = pt[k], ic[k][0], ic[k][1]
                r[k + "_cnt"] = f"{cnt[k][0]}/{cnt[k][1]}"
            rows.append(r)
        for c in conds:  # por condición fija
            pt, ic, cm, cnt = summarize(yte, decide(Pf[c], thr), gte)
            rows.append({"modelo": mname, "conjunto": f"fijo:{c}", "n": len(yte), "umbral": thr, **{k: v for k, v in pt.items()}})
        for fname, V in (("variantes_estres_independiente", Fs), ("variantes_aumentos_propios", Fa)):
            pv = decide(m.predict_proba(V.reshape(-1, V.shape[-1])), thr).reshape(V.shape[0], V.shape[1])
            fs = flip_stats(pc, pv, gte)
            for k, (p, lo, hi) in fs.items():
                flips.append({"modelo": mname, "variantes": fname, "metrica": k, "valor": p, "lo": lo, "hi": hi})
            # flip por clase verdadera
            for ci, cn in enumerate(CLASSES):
                s = yte == ci
                fl = float((pv[s] != pc[s, None]).mean())
                flips.append({"modelo": mname, "variantes": fname, "metrica": f"flip_clase|{cn}", "valor": fl, "lo": np.nan, "hi": np.nan})
    pd.DataFrame(rows).to_csv(OUT / "tabla_comparativa.csv", index=False)
    pd.DataFrame(flips).to_csv(OUT / "flip_rate.csv", index=False)
    json.dump(cms, open(OUT / "matrices_confusion.json", "w"), indent=1)
    json.dump({k: {"umbral": v[1], **{a: b for a, b in v[2].items()}} for k, v in models.items()}, open(OUT / "modelos_resumen.json", "w"), indent=1, default=float)
    for k, v in models.items():
        joblib.dump(v[0], CACHE / f"sk_{k.split('_')[0]}.joblib")
    print("ok")


if __name__ == "__main__":
    main()
