import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_cv import *
import pickle
if __name__ == "__main__":
    y = ycap[idx_dev]; R = {}
    def run(name, cfg, c, **kw):
        Ps = multi(cfg, c, **kw); R[name] = Ps; print(line_multi(name, Ps, y)[1], flush=True); return Ps
    base = run("BASE C.1 w3", dict(naug=3, w=3.0), 0.1)
    for c in (0.01, 0.03, 0.3): run(f"C={c}", dict(naug=3, w=3.0), c)
    for a in (1.5, 2, 3): run(f"altw={a}", dict(naug=3, w=3.0, altw=a), 0.1)
    for w in (1.0, 5.0): run(f"w={w}", dict(naug=3, w=w), 0.1)
    run("naug=0", dict(naug=0, w=3.0), 0.1)
    run("solo pp", dict(naug=3, w=3.0, use_raw=False), 0.1)
    run("sin sanas publicas", dict(naug=3, w=3.0, pub=False), 0.1)
    run("filtro calidad", dict(naug=3, w=3.0, qual=True), 0.1)
    for k in (1.5, 2, 3, 5):
        print(line_multi(f"prior-shift alt x{k}", base, y, lambda P, k=k: shift(P, k))[1])
    pickle.dump(R, open(OUT / "cache/oof_exp1.pkl", "wb"))
