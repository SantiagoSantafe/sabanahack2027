#!/usr/bin/env python
"""Reentreno con capturas REALES de la cámara del D1. Selección (C, peso, umbral) SOLO con las 64 capturas de val;
test (68 capturas + test limpio DrBerry) se evalúa una vez al final con los modelos ya elegidos.
Uso: HF_HUB_OFFLINE=1 .venv/bin/python -I resultados/ml/scripts/camara_entrenar.py
"""
import json, sys, itertools, time, warnings
from pathlib import Path
D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline")); sys.path.insert(0, str(D / "resultados/ml/scripts"))
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, joblib
import reentreno_aug as R
import metrics as M
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CL = R.CLASSES; OUT = D / "resultados/ml/modelo_camara"
SPL = D / "resultados/ml/drberry_image/splits"; MA = D / "resultados/ml/modelo_aug/cache"; ML = D / "resultados/ml/modelo_luz/cache"
yi = lambda s: np.array([CL.index(c) for c in s])
rd = lambda s: pd.read_csv(SPL / f"{s}.csv", keep_default_na=False, dtype=str)
tr, va, te = rd("train"), rd("val"), rd("test")
ydev = yi(list(tr.label) + list(va.label)); ntr = len(tr)

# ---------------- datos DrBerry
raw_c = np.concatenate([np.load(MA / "clean_train.npz")["X"], np.load(MA / "clean_val.npz")["X"]])
raw_a = np.concatenate([np.load(MA / "var_aug_train.npz")["X"], np.load(MA / "var_aug_val.npz")["X"]])
pp_c = np.load(ML / "dev_clean.npz")["pp"][:, 0]; pp_a = np.load(ML / "dev_aug.npz")["pp"][:, :, 0]
pt_c = np.load(ML / "pub_train_clean.npz")["pp"][:, 0]; pt_a = np.load(ML / "pub_train_aug.npz")["pp"][:, :, 0]
pt_c_y = np.full(len(pt_c), 3)
tc = np.load(ML / "test_clean.npz"); te_raw, te_pp = tc["raw"][:, 0], tc["pp"][:, 0]
assert len(raw_c) == len(pp_c) == len(ydev)

# ---------------- capturas nuevas
m = pd.read_csv(D / "resultados/ml/capturas_pantalla/manifest.csv", dtype=str)
m = m[m.timestamp >= "2026-10-24T01"].reset_index(drop=True)
st = pd.read_csv(OUT / "caps_nuevas_stats.csv")
cf = np.load(OUT / "cache/caps_nuevas.npz"); CR, CP = cf["raw"], cf["pp"]   # (410,4,1536)
ycap = yi(m.label); split = m.split.to_numpy()
# descartes de calidad: casi vacías / oscuras
bad = (st.brillo < 20) | (st.contraste < 6)
print("descartadas por vacías/oscuras:", int(bad.sum()), "| sin mancha de hoja (no se descartan):", int((~st.hay_hoja).sum()), flush=True)
keep = ~bad.to_numpy()
idx = {s: np.where((split == s) & keep)[0] for s in ("train", "val", "test")}
print({s: len(v) for s, v in idx.items()})
pre = "/Users/santiagosantafe/Downloads/SabanaHack/datos/"
tpath = {p.replace(pre, ""): g for p, g in zip(te.path, te.group)}
gcap = np.array([tpath.get(o, "?") for o in m.origen])

def probe(c): return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=3000, class_weight="balanced", random_state=0))

def build(base, cap, naug, w, fam):
    """-> X, y, sample_weight. base: B|L4|M ; cap: tipo de rasgos de captura ; fam: full|tr (tr excluye val DrBerry)."""
    sel = np.arange(len(ydev)) if fam == "full" else np.arange(ntr)
    Xs, ys, ws = [], [], []
    def add(X, y, wt): Xs.append(X.reshape(-1, X.shape[-1])); ys.append(np.repeat(y, X.size // X.shape[-1] // len(y))); ws.append(np.full(len(Xs[-1]), wt))
    if base in ("B", "M"):
        add(raw_c[sel], ydev[sel], 1.0); add(raw_a[sel], ydev[sel], 1.0)
    if base in ("L4", "M"):
        add(pp_c[sel], ydev[sel], 1.0); add(pp_a[sel], ydev[sel], 1.0)
        add(pt_c, pt_c_y, 1.0); add(pt_a, pt_c_y, 1.0)
    if cap:
        ii = idx["train"]; k = slice(0, 1 + naug)
        for kind in cap:
            add((CR if kind == "raw" else CP)[ii][:, k], ycap[ii], w)
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(ws)

def fit(X, y, wt, c):
    mdl = probe(c); mdl.fit(X, np.array(CL)[y], logisticregression__sample_weight=wt); return mdl

# ---------------- rejilla
Cs = (0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3)
# tipo -> (base, cap_kinds, entrada de inferencia)
TIPOS = {"Bc": ("B", ("raw",), "raw"), "Lc": ("L4", ("pp",), "pp"), "Mc": ("M", ("raw", "pp"), "pp")}
INF = {"raw": CR, "pp": CP}
iv = idx["val"]; yv = ycap[iv]
res = []; models = {}
t0 = time.time()
for fam, tipo, naug, w, c in itertools.product(("tr", "full"), TIPOS, (0, 3), (1.0, 3.0), Cs):
    base, cap, inp = TIPOS[tipo]
    X, y, wt = build(base, cap, naug, w, fam)
    mdl = fit(X, y, wt, c)
    P = mdl.predict_proba(INF[inp][iv][:, 0])
    t9 = M.choose_threshold(yv != 3, 1 - P[:, 3], 0.90); t8 = M.choose_threshold(yv != 3, 1 - P[:, 3], 0.80)
    row = {"fam": fam, "tipo": tipo, "naug": naug, "w": w, "C": c, "inp": inp}
    for nm, t in (("t90", t9), ("t80", t8)):
        pr = R.decide(P, t["umbral"]); row[f"{nm}_thr"] = t["umbral"]; row[f"{nm}_sens"] = float(((pr != 3) & (yv != 3)).sum() / (yv != 3).sum())
        row[f"{nm}_fp"] = float(((pr != 3) & (yv == 3)).sum() / (yv == 3).sum()); row[f"{nm}_acc"] = float((pr == yv).mean())
    res.append(row); models[(fam, tipo, naug, w, c)] = mdl
    if len(res) % 20 == 0: print(len(res), f"{time.time()-t0:.0f}s", flush=True)
rs = pd.DataFrame(res); rs.to_csv(OUT / "val_rejilla.csv", index=False)

# ---------------- referencias B y L4 en val capturas (OJO: vieron los originales de val)
hB = joblib.load(D / "resultados/ml/modelo_aug_B/clip_probe_tiles3_aug_dev.joblib")["sk_model"]; tB = json.load(open(D / "resultados/ml/modelo_aug_B/umbral.json"))["umbral"]
hL = joblib.load(ML / "sk_L4.joblib"); tL = json.load(open(D / "resultados/ml/modelo_luz/umbral.json"))["umbral"]

# ---------------- selección: mejor config por (fam, tipo) por val (FP min con sens>=.9, luego acc)
def best(df, nm):
    ok = df[df[f"{nm}_sens"] >= (0.9 if nm == "t90" else 0.8) - 1e-9]
    ok = ok if len(ok) else df
    return ok.sort_values([f"{nm}_fp", f"{nm}_acc", "C"], ascending=[True, False, True]).iloc[0]
sel = {}
for (fam, tipo), df in rs.groupby(["fam", "tipo"]):
    b = best(df, "t90"); sel[(fam, tipo)] = b
    print(fam, tipo, dict(b[["naug", "w", "C", "t90_thr", "t90_sens", "t90_fp", "t90_acc", "t80_sens", "t80_fp"]]))

# ---------------- TEST (una vez)
it = idx["test"]; yt = ycap[it]; gt = gcap[it]; yte = yi(te.label); gte = te.group.to_numpy()
def ev(P, thr, y, g):
    pt, ic, cm, cnt = R.summarize(y, R.decide(P, thr), g)
    return {"sens": pt["sens"], "sens_ic": ic["sens"], "fp": pt["fp"], "fp_ic": ic["fp"], "acc": pt["acc"], "acc_ic": ic["acc"],
            "rec_alt": pt["rec_alternaria"], "cnt_sens": cnt["sens"], "cnt_fp": cnt["fp"], "cm": cm.tolist()}
rows = []
def add(nombre, mdl, thr, inp, extra=None):
    P = mdl.predict_proba(INF[inp][it][:, 0]); r = ev(P, thr, yt, gt)
    Ptl = mdl.predict_proba(te_raw if inp == "raw" else te_pp); l = ev(Ptl, thr, yte, gte)
    # votación sintética: media de probabilidades de original + 3 aumentos leves
    Pv = np.mean([mdl.predict_proba(INF[inp][it][:, k]) for k in range(4)], 0); v = ev(Pv, thr, yt, gt)
    rows.append({"modelo": nombre, "entrada": inp, "umbral": thr, "cap": r, "limpio": l, "voto4": v, **(extra or {})})
for nombre, mdl, thr in (("B", hB, tB), ("L4", hL, tL)):
    for inp in ("raw", "pp"): add(nombre, mdl, thr, inp)
for (fam, tipo), b in sel.items():
    key = (fam, tipo, int(b.naug), float(b.w), float(b.C)); mdl = models[key]
    b80 = best(rs[(rs.fam == fam) & (rs.tipo == tipo)], "t80")
    inps = ("raw", "pp") if tipo == "Mc" else (TIPOS[tipo][2],)
    for inp in inps:
        add(f"{tipo}_{fam}_t90", mdl, float(b.t90_thr), inp, {"cfg": dict(naug=int(b.naug), w=float(b.w), C=float(b.C)), "val": dict(sens=b.t90_sens, fp=b.t90_fp, acc=b.t90_acc)})
    key8 = (fam, tipo, int(b80.naug), float(b80.w), float(b80.C)); m8 = models[key8]
    inp = TIPOS[tipo][2]
    add(f"{tipo}_{fam}_t80", m8, float(b80.t80_thr), inp, {"cfg": dict(naug=int(b80.naug), w=float(b80.w), C=float(b80.C)), "val": dict(sens=b80.t80_sens, fp=b80.t80_fp, acc=b80.t80_acc)})
    joblib.dump({"t90": mdl, "t80": m8, "sel": b.to_dict(), "sel80": b80.to_dict()}, OUT / f"cache/sel_{fam}_{tipo}.joblib")
json.dump(rows, open(OUT / "test_resultados.json", "w"), indent=1, default=float)
# referencias en val para B y L4
for nombre, mdl, thr in (("B", hB, tB), ("L4", hL, tL)):
    for inp in ("raw", "pp"):
        P = mdl.predict_proba(INF[inp][iv][:, 0]); pr = R.decide(P, thr)
        print("VAL(contaminada)", nombre, inp, "sens", ((pr != 3) & (yv != 3)).sum() / (yv != 3).sum(), "fp", ((pr != 3) & (yv == 3)).sum() / (yv == 3).sum())
print("\n%-14s %-4s | CAP sens  fp   acc  alt | LIMPIO sens fp acc | VOTO4 sens fp acc" % ("modelo", "inp"))
for r in rows:
    c, l, v = r["cap"], r["limpio"], r["voto4"]
    print("%-14s %-4s | %.3f %.3f %.3f %.2f | %.3f %.3f %.3f | %.3f %.3f %.3f  thr=%.3f" % (r["modelo"], r["entrada"], c["sens"], c["fp"], c["acc"], c["rec_alt"], l["sens"], l["fp"], l["acc"], v["sens"], v["fp"], v["acc"], r["umbral"]))
