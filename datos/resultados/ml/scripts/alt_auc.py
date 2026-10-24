import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_exp3 import *
import joblib, json, warnings; warnings.filterwarnings('ignore')
from sklearn.metrics import roc_auc_score
from PIL import Image
sys.path.insert(0, str(OUT))
from ens_clasificador import EnsembleClassifier
it = idx_te; yt = ycap[it]; gt = gcap[it]
Pc = np.load(OUT / "cache/test_probs_candidato.npy")
ship = joblib.load(CAM / "clip_probe_tiles3_camara.joblib")["sk_model"]; Ps = ship.predict_proba(CP[it][:, 0])
X, yy, wt = build(set(), idx_dev, naug=3, w=3.0); m1 = fit(X, yy, wt, 0.1); Pb = m1.predict_proba(CP[it][:, 0])
def aucs(y, P):
    s = 1 - P[:, SANA]; a = roc_auc_score(y != SANA, s); m = (y == ALT) | (y == SANA); b = roc_auc_score(y[m] == ALT, s[m]); return a, b
rng = np.random.default_rng(0); ug = np.unique(gt); rows = {u: np.where(gt == u)[0] for u in ug}
for nm, P in (("actual", Ps), ("control", Pb), ("candidato", Pc)):
    pt = aucs(yt, P); bs = []
    for _ in range(1000):
        ids = np.concatenate([rows[u] for u in rng.choice(ug, len(ug))])
        if len(set(yt[ids])) < 4: continue
        bs.append(aucs(yt[ids], P[ids]))
    bs = np.array(bs); print(nm, "AUC enferma-vs-sana %.3f [%.2f,%.2f]  AUC alternaria-vs-sana %.3f [%.2f,%.2f]" % (pt[0], *np.percentile(bs[:, 0], [2.5, 97.5]), pt[1], *np.percentile(bs[:, 1], [2.5, 97.5])))
# verificacion del cargador con imagenes reales (preprocesamiento del panel)
import luz_common as L
clf = EnsembleClassifier(OUT / "clip_probe_ens_camara_v2.joblib")
sel = list(range(0, 68, 9)); ims = []
for j in sel:
    im = Image.open(D / m.captura_roi[it[j]]).convert("RGB"); ims.append(L.preprocesar(im))
P = clf.predict_proba(ims); print("max |dif| cargador vs cache:", np.abs(P - Pc[sel]).max())
