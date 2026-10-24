"""Motor de CV agrupada para candidatos de alternaria."""
from alt_common import *
from joblib import Parallel, delayed

def build(excl_groups, cap_idx, naug=3, w=3.0, altw=1.0, base4=False, cap_extra=None, use_raw=True, use_pp=True, pub=True):
    msk = ~np.isin(gtr, list(excl_groups))
    Xs, ys, ws = [], [], []
    def add(X, y, wt):
        n = X.size // X.shape[-1] // len(y)
        Xs.append(X.reshape(-1, X.shape[-1])); ys.append(np.repeat(y, n)); ws.append(np.full(len(Xs[-1]), wt))
    y = ytr[msk]
    if use_raw: add(raw_c[msk], y, 1.0); add(raw_a[msk], y, 1.0)
    if use_pp: add(pp_c[msk], y, 1.0); add(pp_a[msk], y, 1.0)
    if pub: add(pt_c, np.full(len(pt_c), 3), 1.0); add(pt_a, np.full(len(pt_c), 3), 1.0)
    k = slice(0, 1 + naug)
    if use_raw: add(CR[cap_idx][:, k], ycap[cap_idx], w)
    if use_pp: add(CP[cap_idx][:, k], ycap[cap_idx], w)
    X, y, wt = np.concatenate(Xs), np.concatenate(ys), np.concatenate(ws)
    wt = np.where(y == ALT, wt * altw, wt)
    return X, y, wt

def fit(X, y, wt, c):
    mdl = probe(c); mdl.fit(X, np.array(CL)[y], logisticregression__sample_weight=wt); return mdl

GOOD = ~((st.brillo < 40) | (st.contraste < 15) | (~st.hay_hoja)).to_numpy()
def _fold(a, b, cfg, c, inp):
    cfg = dict(cfg)
    if cfg.pop("qual", False): a = a[GOOD[a]]
    X, y, wt = build(set(gcap[b]), a, **cfg)
    mdl = fit(X, y, wt, c)
    return b, mdl.predict_proba((CP if inp == "pp" else CR)[b][:, 0])

def oof(cfg, c, inp="pp", seed=0, n_jobs=5):
    out = np.zeros((len(m), 4)); fs = folds(seed)
    for b, P in Parallel(n_jobs=n_jobs)(delayed(_fold)(a, b, cfg, c, inp) for a, b in fs): out[b] = P
    return out[idx_dev]

def at_fp(y, P, target):
    """umbral tal que la tasa de falsas alarmas OOF <= target (el mas bajo posible que lo cumple)."""
    s = np.sort((1 - P[:, SANA])[y == SANA])[::-1]; k = int(np.floor(target * len(s)))
    thr = s[k] + 1e-12 if k < len(s) else 0.0
    return thr

def summary(y, P, fps=(0.2, 0.3)):
    r = {}
    for f in fps:
        t = at_fp(y, P, f); q = metr(y, P, t); r[f] = dict(thr=t, **q)
    r["score"] = float(np.mean([(r[f]["alt"] + r[f]["sens"]) / 2 for f in fps]))
    return r

def line(name, y, P):
    r = summary(y, P); a, b = r[0.2], r[0.3]
    return f"{name:34s} S={r['score']:.3f} | fp.2: sens {a['sens']:.2f} alt {a['alt']:.2f} oid {a['oidio']:.2f} hel {a['helio']:.2f} | fp.3: sens {b['sens']:.2f} alt {b['alt']:.2f} oid {b['oidio']:.2f} hel {b['helio']:.2f}"

def shift(P, k):
    Q = P * np.array([k, 1, 1, 1]); return Q / Q.sum(1, keepdims=True)

def multi(cfg, c, seeds=(0, 1, 2), inp="pp"):
    return [oof(cfg, c, inp, s) for s in seeds]

def score_multi(Ps, y, fn=None):
    """promedia el resumen sobre semillas de pliegue"""
    rs = [summary(y, fn(P) if fn else P) for P in Ps]
    return float(np.mean([r["score"] for r in rs])), rs

def line_multi(name, Ps, y, fn=None):
    sc, rs = score_multi(Ps, y, fn)
    g = lambda f, k: np.mean([r[f][k] for r in rs])
    return sc, f"{name:34s} S={sc:.3f} | fp.2: sens {g(0.2,'sens'):.2f} alt {g(0.2,'alt'):.2f} oid {g(0.2,'oidio'):.2f} hel {g(0.2,'helio'):.2f} | fp.3: sens {g(0.3,'sens'):.2f} alt {g(0.3,'alt'):.2f} oid {g(0.3,'oidio'):.2f} hel {g(0.3,'helio'):.2f}"
