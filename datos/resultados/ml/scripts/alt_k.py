import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_cv import *
import pickle
R = pickle.load(open(OUT / "cache/oof_exp3.pkl", "rb")); y = ycap[idx_dev]
for k in (1, 2, 3, 4, 5, 8): print(line_multi(f"ENS3 shift x{k}", R["ENS3"], y, lambda P, k=k: shift(P, k))[1])
