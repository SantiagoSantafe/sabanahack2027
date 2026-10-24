import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_exp2 import *
c34 = lambda f3, f4: np.concatenate([f3, f4[..., 512:]], -1)
def build3(excl, cap_idx, naug=3, w=3.0, raw=False):
    msk = ~np.isin(gtr, list(excl)); y = ytr[msk]; Xs, ys, ws = [], [], []
    def add(X, y, wt): Xs.append(X.reshape(-1, X.shape[-1])); ys.append(np.repeat(y, X.size // X.shape[-1] // len(y))); ws.append(np.full(len(Xs[-1]), wt))
    add(c34(pp_c[msk], pp_c4[msk]), y, 1.0); add(c34(pp_a[msk], pp_a4[msk]), y, 1.0)
    add(c34(pt_c, pt_c4), np.full(len(pt_c), SANA), 1.0); add(c34(pt_a, pt_a4), np.full(len(pt_c), SANA), 1.0)
    k = slice(0, 1 + naug); add(c34(cap_t[cap_idx][:, k, 0], cap_t[cap_idx][:, k, 1]), ycap[cap_idx], w)
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(ws)
def _f3(a, b, kw, c):
    X, y, wt = build3(set(gcap[b]), a, **kw); mdl = fit(X, y, wt, c)
    return b, mdl.predict_proba(c34(cap_t[b][:, 0, 0], cap_t[b][:, 0, 1]))
def oof3(kw, c, seed):
    out = np.zeros((len(m), 4))
    for b, P in Parallel(n_jobs=5)(delayed(_f3)(a, b, kw, c) for a, b in folds(seed)): out[b] = P
    return out[idx_dev]
if __name__ == "__main__":
    y = ycap[idx_dev]; R = pickle.load(open(OUT / "cache/oof_exp2.pkl", "rb")); R1 = pickle.load(open(OUT / "cache/oof_exp1.pkl", "rb"))
    def run3(name, kw, c, seeds=(0, 1, 2)):
        Ps = [oof3(kw, c, s) for s in seeds]; R[name] = Ps; print(line_multi(name, Ps, y)[1], flush=True)
    for c in (0.01, 0.03, 0.1): run3(f"V 34 base completa C={c}", dict(), c)
    run3("V 34 base completa w=1 C=0.03", dict(w=1.0), 0.03)
    ens = lambda A, B: [(a + b) / 2 for a, b in zip(A, B)]
    R["ENS BASE+34s"] = ens(R1["BASE C.1 w3"], R["V 34s C=0.1"]); print(line_multi("ENS BASE+34s", R["ENS BASE+34s"], y)[1])
    R["ENS BASE+34full"] = ens(R1["BASE C.1 w3"], R["V 34 base completa C=0.03"]); print(line_multi("ENS BASE+34full", R["ENS BASE+34full"], y)[1])
    R["ENS 34s+34full"] = ens(R["V 34s C=0.1"], R["V 34 base completa C=0.03"]); print(line_multi("ENS 34s+34full", R["ENS 34s+34full"], y)[1])
    R["ENS3"] = [(a + b + c_) / 3 for a, b, c_ in zip(R1["BASE C.1 w3"], R["V 34s C=0.1"], R["V 34 base completa C=0.03"])]; print(line_multi("ENS3", R["ENS3"], y)[1])
    for k in (2, 3):
        print(line_multi(f"ENS3 prior-shift x{k}", R["ENS3"], y, lambda P, k=k: shift(P, k))[1])
        print(line_multi(f"34s prior-shift x{k}", R["V 34s C=0.1"], y, lambda P, k=k: shift(P, k))[1])
    pickle.dump(R, open(OUT / "cache/oof_exp3.pkl", "wb"))
