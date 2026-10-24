import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_cv import *
import pickle
Z = np.load(OUT / "cache/alt_feats.npz")
dr_t, dr_s, pub_t, pub_s, syn_t, syn_s, syn_src = Z["dr_t"], Z["dr_s"], Z["pub_t"], Z["pub_s"], Z["syn_t"], Z["syn_s"], Z["syn_src"]
cap_t, cap_s = Z["caps_t"], Z["caps_s"]; npub = len(pub_t) // 2
def feat(t, s, mode):
    """t: (...,2,1536) [3x3,4x4]; s: (...,1024) -> vector segun modo"""
    f3, f4 = t[..., 0, :], t[..., 1, :]
    parts = {"3": [f3], "4": [f4], "34": [f3, f4[..., 512:]], "3s": [f3, s], "34s": [f3, f4[..., 512:], s], "4s": [f4, s]}[mode]
    return np.concatenate(parts, -1)
def build2(excl, cap_idx, mode="3", naug=3, w=3.0, altw=1.0, syn=0.0, pub=True):
    msk = ~np.isin(gtr, list(excl))
    ids = np.where(msk)[0]; Xs, ys, ws = [], [], []
    def add(X, y, wt): Xs.append(X.reshape(-1, X.shape[-1])); ys.append(np.repeat(y, X.size // X.shape[-1] // len(y))); ws.append(np.full(len(Xs[-1]), wt))
    y = ytr[ids]
    add(feat(dr_t[ids], dr_s[ids], mode), y, 1.0)
    aug_ids = (278 + ids[:, None] * 3 + np.arange(3)).reshape(-1)
    Xa = feat(dr_t[aug_ids], dr_s[aug_ids], mode); Xs.append(Xa); ys.append(np.repeat(y, 3)); ws.append(np.ones(len(Xa)))
    if pub:
        add(feat(pub_t, pub_s, mode), np.full(len(pub_t), SANA), 1.0)
    k = slice(0, 1 + naug)
    add(feat(cap_t[cap_idx][:, k], cap_s[cap_idx][:, k], mode), ycap[cap_idx], w)
    if syn > 0:
        ok = np.where((syn_src == -1) | ~np.isin(gtr[np.clip(syn_src, 0, None)], list(excl)))[0]
        add(feat(syn_t[ok], syn_s[ok], mode), np.full(len(ok), ALT), syn)
    X, y, wt = np.concatenate(Xs), np.concatenate(ys), np.concatenate(ws)
    return X, y, np.where(y == ALT, wt * altw, wt)
def _f(a, b, kw, c):
    X, y, wt = build2(set(gcap[b]), a, **kw); mdl = fit(X, y, wt, c)
    return b, mdl.predict_proba(feat(cap_t[b][:, 0], cap_s[b][:, 0], kw.get("mode", "3")))
def oof2(kw, c, seed):
    out = np.zeros((len(m), 4))
    for b, P in Parallel(n_jobs=5)(delayed(_f)(a, b, kw, c) for a, b in folds(seed)): out[b] = P
    return out[idx_dev]
if __name__ == "__main__":
    y = ycap[idx_dev]; R = {}
    def run(name, kw, c, seeds=(0, 1, 2)):
        Ps = [oof2(kw, c, s) for s in seeds]; R[name] = Ps; print(line_multi(name, Ps, y)[1], flush=True)
    for c in (0.03, 0.1):
        run(f"V0 3x3 pp C={c}", dict(mode="3"), c)
    for mode in ("4", "34", "3s", "34s"):
        for c in (0.03, 0.1): run(f"V {mode} C={c}", dict(mode=mode), c)
    for syn in (0.5, 1.0):
        for mode in ("3", "3s"): run(f"V {mode} +syn{syn} C=0.1", dict(mode=mode, syn=syn), 0.1)
    pickle.dump(R, open(OUT / "cache/oof_exp2.pkl", "wb"))
