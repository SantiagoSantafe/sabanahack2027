"""Utilidades comunes del experimento 'alternaria' (CV agrupada sobre capturas train+val; test congelado aparte)."""
import sys, warnings, time
from pathlib import Path
D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
sys.path.insert(0, str(D / "pipeline")); sys.path.insert(0, str(D / "resultados/ml/scripts"))
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold
CL = ["alternaria", "heliothis", "oidio", "sana"]; ALT = 0; SANA = 3
SPL = D / "resultados/ml/drberry_image/splits"; MA = D / "resultados/ml/modelo_aug/cache"; ML = D / "resultados/ml/modelo_luz/cache"
OUT = D / "resultados/ml/modelo_camara_v2"; CAM = D / "resultados/ml/modelo_camara"
yi = lambda s: np.array([CL.index(c) for c in s])
rd = lambda s: pd.read_csv(SPL / f"{s}.csv", keep_default_na=False, dtype=str)
tr, va, te = rd("train"), rd("val"), rd("test")
ntr = len(tr)
pre = str(D) + "/"
rel = lambda s: s.str.replace(pre, "", regex=False)
path2group = {}
for df in (tr, va, te):
    for p, g in zip(rel(df.path), df.group): path2group[p] = g
# base DrBerry (solo train, familia 'tr')
raw_c = np.load(MA / "clean_train.npz")["X"]; raw_a = np.load(MA / "var_aug_train.npz")["X"]          # (278,1536) (278,5,1536)
pp_c = np.load(ML / "dev_clean.npz")["pp"][:ntr, 0]; pp_a = np.load(ML / "dev_aug.npz")["pp"][:ntr, :, 0]  # (278,1536) (278,6,1536)
pp_c4 = np.load(ML / "dev_clean.npz")["pp"][:ntr, 1]; pp_a4 = np.load(ML / "dev_aug.npz")["pp"][:ntr, :, 1]
pt_c = np.load(ML / "pub_train_clean.npz")["pp"][:, 0]; pt_a = np.load(ML / "pub_train_aug.npz")["pp"][:, :, 0]
pt_c4 = np.load(ML / "pub_train_clean.npz")["pp"][:, 1]; pt_a4 = np.load(ML / "pub_train_aug.npz")["pp"][:, :, 1]
ytr = yi(tr.label); gtr = np.array([g for g in tr.group])
tc = np.load(ML / "test_clean.npz"); te_raw, te_pp = tc["raw"][:, 0], tc["pp"][:, 0]; te_pp4 = tc["pp"][:, 1]
yte = yi(te.label); gte = te.group.to_numpy()
# capturas
m = pd.read_csv(D / "resultados/ml/capturas_pantalla/manifest.csv", dtype=str)
m = m[m.timestamp >= "2026-10-24T01"].reset_index(drop=True)
cf = np.load(CAM / "cache/caps_nuevas.npz"); CR, CP = cf["raw"], cf["pp"]
ycap = yi(m.label); split = m.split.to_numpy(); gcap = np.array([path2group[o] for o in m.origen])
st = pd.read_csv(CAM / "caps_nuevas_stats.csv")
idx_dev = np.where(split != "test")[0]; idx_te = np.where(split == "test")[0]
assert (m.label.values[idx_te] == te.set_index(rel(te.path)).loc[m.origen.values[idx_te]].label.values).all()

def probe(c): return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000, class_weight="balanced", random_state=0))

def folds(seed=0, k=5):
    sg = StratifiedGroupKFold(k, shuffle=True, random_state=seed)
    return [(idx_dev[a], idx_dev[b]) for a, b in sg.split(idx_dev, ycap[idx_dev], gcap[idx_dev])]

def metr(y, P, thr, g=None):
    """Regla del panel: sospecha si 1-p(sana)>=thr; devuelve contadores."""
    enf = y != SANA; sosp = (1 - P[:, SANA]) >= thr
    mk = P.copy(); mk[:, SANA] = -1; pred = np.where(sosp, mk.argmax(1), SANA)
    return dict(sens=(sosp & enf).sum() / enf.sum(), fp=(sosp & ~enf).sum() / (~enf).sum(),
                alt=(pred == ALT)[y == ALT].mean(), alt_sosp=sosp[y == ALT].mean(), acc=(pred == y).mean(),
                oidio=(pred == 2)[y == 2].mean(), helio=(pred == 1)[y == 1].mean())
