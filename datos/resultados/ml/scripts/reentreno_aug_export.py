#!/usr/bin/env python
"""Exporta los modelos aumentados (formato del modelo final) y calcula diferencias pareadas (bootstrap por grupo) vs el final."""
import json, sys
from pathlib import Path
D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos"); sys.path.insert(0, str(D / "resultados/ml/scripts")); sys.path.insert(0, str(D / "pipeline"))
import joblib, numpy as np, pandas as pd
import reentreno_aug as R
from common import now_iso

OUT = R.OUT; C = R.CACHE
res = json.load(open(OUT / "modelos_resumen.json"))
final_umbral = json.load(open(D / "resultados/ml/modelo_final/umbral.json"))
head0 = joblib.load(D / "resultados/ml/modelo_final/clip_probe_tiles3.joblib")
names = {"A": "A_aug_train", "B": "B_aug_dev(train+val)", "Au": "Au_aug_train_umbral_val+aug"}
desc = {"A": "train+aumentadas(K=5), umbral en val limpio (spec)", "B": "train+val+aumentadas(K=5), C y umbral por CV agrupada OOF limpio (protocolo del final)", "Au": "como A pero umbral en val limpio+aumentado"}
for key, fn, un in (("A", "clip_probe_tiles3_aug.joblib", "umbral.json"), ("B", "clip_probe_tiles3_aug_dev.joblib", "umbral_dev.json"), ("Au", "clip_probe_tiles3_aug_umbralaug.joblib", "umbral_umbralaug.json")):
    m = joblib.load(C / f"sk_{key}.joblib"); r = res[names[key]]
    info = {"C_elegido": r["C"], "busqueda_C": r.get("busqueda"), "class_weight": "balanced", "aumentos": "pipeline/augment_screen.py", "K": R.K, "variante": desc[key], "umbral_en": r["umbral_en"]}
    joblib.dump({"tipo": "clip_probe", "clip_model": head0["clip_model"], "pretrained": head0["pretrained"], "classes": R.CLASSES, "sk_model": m, "info": info, "tiles": 3, "creado": now_iso()}, OUT / fn)
    u = {k: v for k, v in final_umbral.items() if k not in ("validacion", "elegido_en", "umbral_puntaje_observado", "avisos")}
    u.update({"creado": now_iso(), "umbral": r["umbral"], "elegido_en": {"descripcion": r["umbral_en"], "variante": desc[key]}, "validacion": r.get("val")})
    json.dump(u, open(OUT / un, "w"), indent=2, ensure_ascii=False)

# diferencias pareadas por grupo
rd = lambda s: pd.read_csv(R.SPL / f"{s}.csv", keep_default_na=False, dtype=str)
te = rd("test"); yte = np.array([R.CLASSES.index(c) for c in te["label"]]); g = te["group"].to_numpy()
Xte = np.load(C / "clean_test.npz")["X"]; Fs = np.load(C / "var_flip_stress.npz")["X"]; Fa = np.load(C / "var_flip_aug.npz")["X"]
ms = pd.read_csv(D / "resultados/ml/stress/manifest_stress.csv", keep_default_na=False, dtype=str)
fixed = [np.load(C / f"clean_stress_{c}.npz")["X"] for c in dict.fromkeys(ms["dataset"]) if c not in ("original", "combinada")]
mods = {"F": (joblib.load(C / "sk_F.joblib"), res["F_final(train+val)"]["umbral"])}
for k in ("A0", "A", "Au", "B"): mods[k] = (joblib.load(C / f"sk_{k}.joblib"), res[[n for n in res if n.startswith(k + "_")][0]]["umbral"])
def per_img(k):
    m, t = mods[k]; pc = R.decide(m.predict_proba(Xte), t)
    out = {"clean": pc}
    for nm, V in (("flip_est", Fs), ("flip_aug", Fa)):
        pv = R.decide(m.predict_proba(V.reshape(-1, V.shape[-1])), t).reshape(V.shape[:2]); out[nm] = (pv != pc[:, None]).mean(1)
    st = [R.decide(m.predict_proba(X), t) for X in fixed]
    dis = yte != 3
    out["st_sens"] = np.mean([(p != 3) for p in st], 0)  # por imagen, promedio sobre perturbaciones
    out["st_fp"] = out["st_sens"]
    out["cl_sosp"] = (pc != 3).astype(float)
    return out
P = {k: per_img(k) for k in mods}
ug, inv = np.unique(g, return_inverse=True); rng = np.random.default_rng(1); pick = rng.integers(0, len(ug), size=(2000, len(ug)))
dis, san = yte != 3, yte == 3
def ratio(v, mask): a = np.bincount(inv, v * mask, len(ug)); b = np.bincount(inv, mask.astype(float), len(ug)); return a[pick].sum(1) / np.maximum(b[pick].sum(1), 1)
rows = []
for k in ("A0", "A", "Au", "B"):
    for nm, getv, mask in (("flip_estres_indep", lambda p: p["flip_est"], np.ones_like(dis)), ("flip_aug_propios", lambda p: p["flip_aug"], np.ones_like(dis)),
                           ("sens_estres_8pert", lambda p: p["st_sens"], dis), ("fp_estres_8pert", lambda p: p["st_sens"], san), ("sens_limpio", lambda p: p["cl_sosp"], dis), ("fp_limpio", lambda p: p["cl_sosp"], san)):
        d = ratio(getv(P[k]), mask) - ratio(getv(P["F"]), mask)
        pt = (getv(P[k])[mask].mean() - getv(P["F"])[mask].mean())
        rows.append({"modelo": k, "metrica": nm, "dif_vs_final": pt, "lo": np.quantile(d, .025), "hi": np.quantile(d, .975)})
pd.DataFrame(rows).to_csv(OUT / "diferencias_pareadas_vs_final.csv", index=False)
print(pd.DataFrame(rows).round(3).to_string())
