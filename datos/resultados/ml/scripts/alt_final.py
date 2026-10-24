import sys; sys.path.insert(0, "/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
from alt_exp3 import *
import json, joblib, pickle
from common import now_iso
K = 3.0; FP_T = 0.30
y_dev = ycap[idx_dev]
R3 = pickle.load(open(OUT / "cache/oof_exp3.pkl", "rb")); R1 = pickle.load(open(OUT / "cache/oof_exp1.pkl", "rb"))
# --- umbrales por OOF (media de 3 semillas de pliegue) al objetivo FP=0.30 de sanas
thr_ens = float(np.mean([at_fp(y_dev, shift(P, K), FP_T) for P in R3["ENS3"]]))
thr_base = float(np.mean([at_fp(y_dev, P, FP_T) for P in R1["BASE C.1 w3"]]))
print("thr OOF ens", thr_ens, "base", thr_base)
oofm = lambda Ps, f, t: {k: float(np.mean([metr(y_dev, f(P), t)[k] for P in Ps])) for k in ("sens", "fp", "alt", "acc", "oidio", "helio")}
print("OOF ens", oofm(R3["ENS3"], lambda P: shift(P, K), thr_ens)); print("OOF base", oofm(R1["BASE C.1 w3"], lambda P: P, thr_base))
# --- ajuste final con capturas train+val
X, yy, wt = build(set(), idx_dev, naug=3, w=3.0); m1 = fit(X, yy, wt, 0.1)
X, yy, wt = build2(set(), idx_dev, mode="34s", naug=3, w=3.0); m2 = fit(X, yy, wt, 0.1)
X, yy, wt = build3(set(), idx_dev, naug=3, w=3.0); m3 = fit(X, yy, wt, 0.03)
it = idx_te; yt = ycap[it]; gt = gcap[it]
f3t, f4t, st_ = cap_t[it][:, 0, 0], cap_t[it][:, 0, 1], cap_s[it][:, 0]
def ens_probs(f3, f4, s):
    P = np.mean([m1.predict_proba(f3), m2.predict_proba(np.concatenate([f3, f4[:, 512:], s], 1)), m3.predict_proba(np.concatenate([f3, f4[:, 512:]], 1))], 0)
    return P
Pc_raw = ens_probs(f3t, f4t, st_); Pc = shift(Pc_raw, K)
ship = joblib.load(CAM / "clip_probe_tiles3_camara.joblib")["sk_model"]; thr_ship = json.load(open(CAM / "umbral.json"))["umbral"]
Ps = ship.predict_proba(CP[it][:, 0]); Pb = m1.predict_proba(CP[it][:, 0])
# limpio DrBerry
drs = Z["drtest_s"]; Pcl = shift(ens_probs(te_pp, te_pp4, drs), K); Psl = ship.predict_proba(te_pp); Pbl = m1.predict_proba(te_pp)
def boot(y, P, thr, g, B=2000, seed=0):
    rng = np.random.default_rng(seed); ug = np.unique(g); rows = {u: np.where(g == u)[0] for u in ug}; out = {k: [] for k in ("sens", "fp", "alt", "acc", "oidio", "helio")}
    for _ in range(B):
        ids = np.concatenate([rows[u] for u in rng.choice(ug, len(ug))]); q = metr(y[ids], P[ids], thr)
        for k in out: out[k].append(q[k])
    return {k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for k, v in out.items()}
def counts(y, P, thr):
    enf = y != SANA; sosp = (1 - P[:, SANA]) >= thr; mk = P.copy(); mk[:, SANA] = -1; pred = np.where(sosp, mk.argmax(1), SANA)
    cm = np.zeros((4, 4), int)
    for a, b in zip(y, pred): cm[a, b] += 1
    return dict(sens=f"{int((sosp&enf).sum())}/{int(enf.sum())}", fp=f"{int((sosp&~enf).sum())}/{int((~enf).sum())}", alt=f"{int(((pred==ALT)&(y==ALT)).sum())}/{int((y==ALT).sum())}",
                oidio=f"{int(((pred==2)&(y==2)).sum())}/{int((y==2).sum())}", helio=f"{int(((pred==1)&(y==1)).sum())}/{int((y==1).sum())}", exact=f"{int((pred==pred*0+y).sum())}/{len(y)}", cm=cm.tolist())
res = {}
for nm, P, thr, Pl in (("actual Mc_tr (umbral enviado 0,986)", Ps, thr_ship, Psl), ("control: receta actual reajustada con train+val (umbral OOF FP=0,30)", Pb, thr_base, Pbl),
                       ("candidato v2: ensamble x3 + peso alternaria x3 (umbral OOF FP=0,30)", Pc, thr_ens, Pcl)):
    res[nm] = dict(thr=thr, cap=dict(**metr(yt, P, thr), cnt=counts(yt, P, thr), ic=boot(yt, P, thr, gt)), limpio=dict(**metr(yte, Pl, thr), cnt=counts(yte, Pl, thr), ic=boot(yte, Pl, thr, gte)))
    c = res[nm]; print(nm, thr); print(" CAP", c["cap"]["cnt"], {k: round(c["cap"][k], 2) for k in ("sens", "fp", "alt", "oidio", "helio", "acc")}, c["cap"]["ic"]["sens"], c["cap"]["ic"]["fp"], c["cap"]["ic"]["alt"]); print(" LIMPIO", c["limpio"]["cnt"]["sens"], c["limpio"]["cnt"]["fp"], c["limpio"]["cnt"]["alt"])
json.dump(dict(K=K, fp_target=FP_T, thr_ens=thr_ens, thr_base=thr_base, res=res), open(OUT / "test_resultados.json", "w"), indent=1, default=float)
# --- exportar
hB = joblib.load(CAM / "clip_probe_tiles3_camara.joblib")
joblib.dump({"tipo": "clip_probe_ens", "clip_model": hB["clip_model"], "pretrained": hB["pretrained"], "classes": hB["classes"], "tiles": 3, "creado": now_iso(),
             "miembros": [{"modo": "3", "sk_model": m1}, {"modo": "34s", "sk_model": m2}, {"modo": "34", "sk_model": m3}], "peso_clase": [K, 1.0, 1.0, 1.0],
             "info": {"variante": "ensamble de 3 sondas (3x3 raw+pp de Mc; 3x3+4x4+recortes de manchas; 3x3+4x4), capturas train+val, peso alternaria x3", "preprocesamiento": "panel"}}, OUT / "clip_probe_ens_camara_v2.joblib")
u = json.load(open(CAM / "umbral.json")); u.update({"umbral": thr_ens, "creado": now_iso(), "preprocesamiento": "panel", "peso_clase": {"alternaria": K, "heliothis": 1.0, "oidio": 1.0, "sana": 1.0},
    "regla": "p' = p_ens * peso_clase (renormalizado, ya aplicado dentro de EnsembleClassifier.predict_proba); sospecha si 1 - p'(sana) >= umbral; clase = enfermedad mas probable de p'",
    "modelo": "clip_probe_ens_camara_v2.joblib", "elegido_en": {"descripcion": "CV agrupada 5 pliegues x 3 semillas sobre 342 capturas train+val; umbral = FP OOF 0,30 de sanas", "variante": "ENS3_shift3"}})
u.pop("validacion", None); json.dump(u, open(OUT / "umbral.json", "w"), indent=2, ensure_ascii=False)
np.save(OUT / "cache/test_probs_candidato.npy", Pc)
