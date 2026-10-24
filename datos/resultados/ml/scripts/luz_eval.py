#!/usr/bin/env python
"""Etapa 2: entrena B0 (referencia), L1, L2, L3 (ensamble L1+B) y L4/L4x4 (L1/L2 + sanas públicas) y evalúa.
Usa los cachés de luz_features.py. Salidas en resultados/ml/modelo_luz/.
    HF_HUB_OFFLINE=1 .venv/bin/python -I resultados/ml/scripts/luz_eval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline"))
sys.path.insert(0, str(D / "resultados/ml/scripts"))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

import reentreno_aug as R  # noqa: E402  (decide, summarize, flip_stats, make_probe, thr_for, boot_ci, count_cols)

OUT = D / "resultados/ml/modelo_luz"
CACHE = OUT / "cache"
CL = R.CLASSES
SAN = 3
Cs = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3)
ld = lambda n: np.load(CACHE / f"{n}.npz")  # noqa: E731


def folds_by_group(y, g, seed=0):
    from sklearn.model_selection import StratifiedGroupKFold

    return StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(np.zeros(len(y)), y, g)


def fit(X, y, c):
    return R.make_probe(c).fit(X, np.array(CL)[y])


def cv_train(rows, dev_idx, Cfix=None):
    """rows: dict X,y,g,orig(bool) de TODAS las filas de entrenamiento (originales + aumentadas).
    Pliegues por grupo (las aumentadas siguen a su original). C por macro-F1 OOF en las originales de dev."""
    from sklearn.metrics import f1_score

    X, y, g, orig = rows["X"], rows["y"], rows["g"], rows["orig"]
    oi = np.where(orig)[0]
    fold_of = {}
    for k, (_, te) in enumerate(folds_by_group(y[oi], g[oi])):
        for gg in set(g[oi][te]):
            fold_of[gg] = k
    fold = np.array([fold_of[x] for x in g])
    cs = Cs if Cfix is None else (Cfix,)

    def job(c, k):
        m = fit(X[fold != k], y[fold != k], c)
        te = np.where((fold == k) & orig)[0]
        return c, k, te, m.predict_proba(X[te])

    res = Parallel(n_jobs=5)(delayed(job)(c, k) for c in cs for k in range(5))
    P = {c: np.zeros((len(y), 4)) for c in cs}
    for c, k, te, p in res:
        P[c][te] = p
    best, search = None, []
    for c in cs:
        f1 = f1_score(y[dev_idx], P[c][dev_idx].argmax(1), average="macro")
        search.append({"C": c, "macro_f1_oof": float(f1)})
        if best is None or f1 > best[0] + 1e-12:
            best = (f1, c)
    return best[1], search, P[best[1]][dev_idx], fold


def main():
    rd = lambda s: pd.read_csv(R.SPL / f"{s}.csv", keep_default_na=False, dtype=str)  # noqa: E731
    tr, va, te = rd("train"), rd("val"), rd("test")
    yi = lambda df: np.array([CL.index(c) for c in df["label"]])  # noqa: E731
    ydev = np.concatenate([yi(tr), yi(va)])
    gdev = np.concatenate([tr["group"], va["group"]])
    yte, gte = yi(te), te["group"].to_numpy()
    pub = pd.read_csv(OUT / "publicas_split.csv", keep_default_na=False, dtype=str)
    ptr, pho = pub[pub.parte == "train"].reset_index(drop=True), pub[pub.parte == "heldout"].reset_index(drop=True)

    Xdev = ld("dev_clean")["pp"]  # (342,2,d)
    Adev = ld("dev_aug")["pp"]  # (342,K,2,d)
    Xpub = ld("pub_train_clean")["pp"]
    Apub = ld("pub_train_aug")["pp"]
    K, Kp = Adev.shape[1], Apub.shape[1]
    n = len(ydev)
    dev_idx = np.arange(n)

    def build(grid, with_pub):
        X = [Xdev[:, grid]]
        y = [ydev]
        g = [gdev]
        o = [np.ones(n, bool)]
        X.append(Adev[:, :, grid].reshape(-1, Xdev.shape[-1]))
        y.append(np.repeat(ydev, K))
        g.append(np.repeat(gdev, K))
        o.append(np.zeros(n * K, bool))
        if with_pub:
            m = len(ptr)
            X += [Xpub[:, grid], Apub[:, :, grid].reshape(-1, Xdev.shape[-1])]
            y += [np.full(m, SAN), np.full(m * Kp, SAN)]
            g += [ptr["grupo"].to_numpy(), np.repeat(ptr["grupo"].to_numpy(), Kp)]
            o += [np.ones(m, bool), np.zeros(m * Kp, bool)]
        return {"X": np.concatenate(X), "y": np.concatenate(y), "g": np.concatenate(g).astype(object), "orig": np.concatenate(o)}

    models = {}  # nombre -> dict(m, thr, grid, info, ens)
    # ---- B0: tal cual
    hB = joblib.load(D / "resultados/ml/modelo_aug_B/clip_probe_tiles3_aug_dev.joblib")
    thrB = json.load(open(D / "resultados/ml/modelo_aug_B/umbral.json"))["umbral"]
    models["B0"] = {"m": hB["sk_model"], "thr": thrB, "grid": 0, "info": {"C": hB["info"]["C_elegido"], "nota": "modelo_aug_B sin tocar"}}

    oof = {}
    for name, grid, pubflag in (("L1", 0, False), ("L2", 1, False), ("L4", 0, True), ("L4x4", 1, True)):
        rows = build(grid, pubflag)
        c, search, Po, fold = cv_train(rows, dev_idx)
        m = fit(rows["X"], rows["y"], c)
        t = R.thr_for(Po, ydev)
        models[name] = {"m": m, "thr": t["umbral"], "grid": grid, "info": {"C": c, "busqueda": search, "n_filas_train": int(len(rows["y"])), "publicas": pubflag, "oof_dev": {k: t[k] for k in ("tp", "fp", "fn", "tn", "sensibilidad", "tasa_fp")}}}
        oof[name] = (Po, rows, fold)
        print(name, "C", c, "thr", round(t["umbral"], 4), {k: t[k] for k in ("sensibilidad", "fp", "tn")}, flush=True)

    # ---- L3: ensamble L1 + B0 (B0 recibe las mismas imágenes preprocesadas). OOF de B-tipo: entrenado con rasgos crudos de dev (+aug crudas)
    rawc = [np.load(D / f"resultados/ml/modelo_aug/cache/{f}.npz")["X"] for f in ("clean_train", "clean_val")]
    rawa = [np.load(D / f"resultados/ml/modelo_aug/cache/{f}.npz")["X"] for f in ("var_aug_train", "var_aug_val")]
    Xr, Ar = np.concatenate(rawc), np.concatenate(rawa)
    Po1, rows1, fold1 = oof["L1"]
    fdev = fold1[:n]
    Pb = np.zeros((n, 4))
    for k in range(5):
        trn = fdev != k
        Xk = np.concatenate([Xr[trn], Ar[trn].reshape(-1, Xr.shape[1])])
        yk = np.concatenate([ydev[trn], np.repeat(ydev[trn], Ar.shape[1])])
        mk = fit(Xk, yk, 0.003)
        Pb[fdev == k] = mk.predict_proba(Xdev[fdev == k][:, 0])
    Pe = (Po1 + Pb) / 2
    t3 = R.thr_for(Pe, ydev)
    models["L3"] = {"ens": ("L1", "B0"), "thr": t3["umbral"], "grid": 0, "info": {"nota": "media de probabilidades L1 y B0 (ambos sobre imagen preprocesada)", "oof_dev": {k: t3[k] for k in ("tp", "fp", "fn", "tn", "sensibilidad", "tasa_fp")}}}
    print("L3 thr", round(t3["umbral"], 4), flush=True)

    def proba(name, X):  # X (n,2,d)
        mm = models[name]
        if "ens" in mm:
            return (proba(mm["ens"][0], X) + proba(mm["ens"][1], X)) / 2
        return mm["m"].predict_proba(X[:, mm["grid"]])

    views = [("B0_crudo", "B0", "raw"), ("B0_pp", "B0", "pp"), ("L1", "L1", "pp"), ("L2", "L2", "pp"), ("L3", "L3", "pp"), ("L4", "L4", "pp"), ("L4x4", "L4x4", "pp")]

    # ---- conjuntos de evaluación
    S = {}
    tc, ta = ld("test_clean"), ld("test_aug")
    S["test_limpio"] = lambda inp: (tc[inp], yte, gte)
    S["test_estres_realista(x3)"] = lambda inp: (ta[inp].reshape(-1, 2, ta[inp].shape[-1]), np.repeat(yte, 3), np.repeat(gte, 3))
    ms = pd.read_csv(D / "resultados/ml/stress/manifest_stress.csv", keep_default_na=False, dtype=str)
    conds = list(dict.fromkeys(ms["dataset"]))
    fixed = {c: ld(f"fixed_{c}") for c in conds}
    pert = [c for c in conds if c not in ("original", "combinada")]
    S["estres_fijo(8 pert.)"] = lambda inp: (np.concatenate([fixed[c][inp] for c in pert]), np.tile(yte, len(pert)), np.tile(gte, len(pert)))
    S["estres_combinada"] = lambda inp: (fixed["combinada"][inp], yte, gte)
    # capturas verificadas (top-3 CLIP global vs su origen, como entrenar_capturas.py)
    cap = pd.read_csv(D / "resultados/ml/capturas_pantalla/manifest.csv", dtype=str)
    c_, cs_ = ld("caps"), ld("caps_src")
    ec, es = c_["pp"][:, 0, :512], cs_["raw"][:, 0, :512]
    ec = ec / np.linalg.norm(ec, axis=1, keepdims=True)
    es = es / np.linalg.norm(es, axis=1, keepdims=True)
    Sim = ec @ es.T
    keep = (np.argsort(-Sim, 1)[:, :3] == np.arange(len(cap))[:, None]).any(1)
    ycap = np.array([CL.index(x) for x in cap.label])[keep]
    gcap = np.array([Path(o).stem.split("_jpg")[0] for o in cap.origen])[keep]
    print("capturas verificadas:", int(keep.sum()), "/", len(cap), flush=True)
    S["capturas_reales_verificadas"] = lambda inp: (c_[inp][keep], ycap, gcap)
    ph = ld("pub_held_clean")
    for src in ("plantdoc", "plantvillage", "inat"):
        mk = (pho["fuente"] == src).to_numpy()
        S[f"publica_sana:{src}"] = (lambda mk: lambda inp: (ph[inp][mk], np.full(int(mk.sum()), SAN), pho["grupo"].to_numpy()[mk]))(mk)
    S["publica_sana:todas"] = lambda inp: (ph[inp], np.full(len(pho), SAN), pho["grupo"].to_numpy())

    rows, cms, preds = [], {}, {}
    for vname, mname, inp in views:
        thr = models[mname]["thr"]
        for sname, fn in S.items():
            X, y, g = fn(inp)
            P = proba(mname, X)
            pred = R.decide(P, thr)
            preds[(vname, sname)] = (pred, y, g)
            pt, ic, cm, cnt = R.summarize(y, pred, g)
            cms[f"{vname}|{sname}"] = cm.tolist()
            r = {"modelo": vname, "conjunto": sname, "n": len(y), "n_grupos": len(set(g)), "umbral": thr}
            for k in pt:
                r[k], r[k + "_lo"], r[k + "_hi"] = pt[k], ic[k][0], ic[k][1]
                r[k + "_cnt"] = f"{cnt[k][0]}/{cnt[k][1]}"
            rows.append(r)
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "tabla_comparativa.csv", index=False)
    json.dump(cms, open(OUT / "matrices_confusion.json", "w"), indent=1)

    # ---- flip rate (10 variantes/imagen) respecto a la predicción sobre la imagen limpia
    fl, flrows = {}, []
    for vname, mname, inp in views:
        thr = models[mname]["thr"]
        pc = R.decide(proba(mname, tc[inp]), thr)
        for fname in ("flip_aug", "flip_ind"):
            V = ld(fname)[inp]
            pv = R.decide(proba(mname, V.reshape(-1, 2, V.shape[-1])), thr).reshape(V.shape[0], V.shape[1])
            fs = R.flip_stats(pc, pv, gte)
            fl[(vname, fname)] = (pc, pv)
            for k, (p, lo, hi) in fs.items():
                flrows.append({"modelo": vname, "variantes": fname, "metrica": k, "valor": p, "lo": lo, "hi": hi})
            for ci, cn in enumerate(CL):
                s = yte == ci
                flrows.append({"modelo": vname, "variantes": fname, "metrica": f"flip_clase|{cn}", "valor": float((pv[s] != pc[s, None]).mean()), "lo": np.nan, "hi": np.nan})
            # sensibilidad / falsas alarmas con las variantes (estrés realista o independiente)
            flrows.append({"modelo": vname, "variantes": fname, "metrica": "sens_variantes", "valor": float((pv[yte != SAN] != SAN).mean()), "lo": np.nan, "hi": np.nan})
            flrows.append({"modelo": vname, "variantes": fname, "metrica": "fp_variantes", "valor": float((pv[yte == SAN] != SAN).mean()), "lo": np.nan, "hi": np.nan})
    pd.DataFrame(flrows).to_csv(OUT / "flip_rate.csv", index=False)

    # ---- comparación pareada con B0 (bootstrap por grupo, mismas remuestras)
    def agg(num, den, g):
        ug, inv = np.unique(g, return_inverse=True)
        return ug, np.bincount(inv, num, len(ug)), np.bincount(inv, den, len(ug))

    prow = []
    rng = np.random.default_rng(5)
    for base in ("B0_pp", "B0_crudo"):
        for vname, _, _ in views:
            if vname == base:
                continue
            for sname in S:
                pa, y, g = preds[(vname, sname)]
                pb, _, _ = preds[(base, sname)]
                ca, cb = R.count_cols(y, pa), R.count_cols(y, pb)
                ug = np.unique(g)
                pick = rng.integers(0, len(ug), size=(2000, len(ug)))
                for met in ("sens", "fp", "acc", "rec_alternaria"):
                    if ca[met][1].sum() == 0:
                        continue
                    _, na, da = agg(ca[met][0], ca[met][1], g)
                    _, nb, db = agg(cb[met][0], cb[met][1], g)
                    ok = da.sum() > 0
                    pt = na.sum() / da.sum() - nb.sum() / db.sum()
                    rr = (na[pick].sum(1) / np.maximum(da[pick].sum(1), 1)) - (nb[pick].sum(1) / np.maximum(db[pick].sum(1), 1))
                    prow.append({"base": base, "modelo": vname, "conjunto": sname, "metrica": met, "dif": pt, "lo": np.quantile(rr, 0.025), "hi": np.quantile(rr, 0.975)})
            for fname in ("flip_aug", "flip_ind"):
                fa = (fl[(vname, fname)][1] != fl[(vname, fname)][0][:, None]).mean(1)
                fb = (fl[(base, fname)][1] != fl[(base, fname)][0][:, None]).mean(1)
                ug = np.unique(gte)
                pick = rng.integers(0, len(ug), size=(2000, len(ug)))
                _, na, da = agg(fa, np.ones(len(fa)), gte)
                _, nb, db = agg(fb, np.ones(len(fb)), gte)
                rr = na[pick].sum(1) / da[pick].sum(1) - nb[pick].sum(1) / db[pick].sum(1)
                prow.append({"base": base, "modelo": vname, "conjunto": fname, "metrica": "flip_clase", "dif": fa.mean() - fb.mean(), "lo": np.quantile(rr, 0.025), "hi": np.quantile(rr, 0.975)})
    pd.DataFrame(prow).to_csv(OUT / "diferencias_pareadas.csv", index=False)

    for k, v in models.items():
        if "m" in v:
            joblib.dump(v["m"], CACHE / f"sk_{k}.joblib")
    json.dump({k: {"umbral": v["thr"], "grid": v["grid"], **v["info"]} for k, v in models.items()}, open(OUT / "modelos_resumen.json", "w"), indent=1, default=float)
    print("ok", flush=True)


if __name__ == "__main__":
    main()
