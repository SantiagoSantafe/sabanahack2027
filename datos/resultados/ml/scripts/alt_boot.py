import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_cv import *
import pickle
R = pickle.load(open(OUT / "cache/oof_exp3.pkl", "rb")); R1 = pickle.load(open(OUT / "cache/oof_exp1.pkl", "rb")); R.update(R1)
y = ycap[idx_dev]; g = gcap[idx_dev]; ug = np.unique(g); rows_of = {u: np.where(g == u)[0] for u in ug}
C = {"BASE": (R["BASE C.1 w3"], None), "BASE shift x3": (R["BASE C.1 w3"], 3), "34full w1": (R["V 34 base completa w=1 C=0.03"], None),
     "34s": (R["V 34s C=0.1"], None), "ENS3": (R["ENS3"], None), "ENS3 shift x2": (R["ENS3"], 2), "ENS3 shift x3": (R["ENS3"], 3)}
rng = np.random.default_rng(0); B = 3000; N = len(C)
res = {k: [] for k in C}
for b in range(B):
    ids = np.concatenate([rows_of[u] for u in rng.choice(ug, len(ug))]); yy = y[ids]
    for k, (Ps, kk) in C.items():
        res[k].append(np.mean([summary(yy, shift(P[ids], kk) if kk else P[ids])["score"] for P in Ps]))
res = {k: np.array(v) for k, v in res.items()}
alpha = 0.05 / 36; print("alpha ajustado (36 candidatos):", alpha)
pt = {k: score_multi(v[0], y, (lambda P, kk=v[1]: shift(P, kk)) if v[1] else None)[0] for k, v in C.items()}
for k in C:
    d = res[k] - res["BASE"]
    print(f"{k:16s} S={pt[k]:.3f}  dif vs BASE {pt[k]-pt['BASE']:+.3f}  IC95[{np.percentile(d,2.5):+.3f},{np.percentile(d,97.5):+.3f}]  IC ajust[{np.percentile(d,100*alpha/2):+.3f},{np.percentile(d,100*(1-alpha/2)):+.3f}]  P(d<=0)={np.mean(d<=0):.3f}")
