import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_cv import *
import time
if __name__ == "__main__":
    y = ycap[idx_dev]; print(len(y), np.bincount(y))
    t=time.time()
    P = oof(dict(naug=3,w=3.0),0.1); print(time.time()-t)
    print(line("base Mc_tr C.1 w3",y,P))
    np.save(OUT/"cache/oof_base.npy",P)
