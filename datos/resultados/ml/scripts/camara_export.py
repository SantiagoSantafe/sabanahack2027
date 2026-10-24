import json, sys, joblib
from pathlib import Path
D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos"); sys.path.insert(0, str(D / "pipeline"))
from common import now_iso
O = D / "resultados/ml/modelo_camara"
s = joblib.load(O / "cache/sel_tr_Mc.joblib"); r = [x for x in json.load(open(O / "test_resultados.json")) if x["modelo"] == "Mc_tr_t90" and x["entrada"] == "pp"][0]
hB = joblib.load(D / "resultados/ml/modelo_aug_B/clip_probe_tiles3_aug_dev.joblib")
cfg = {k: float(v) for k, v in r["cfg"].items()}
joblib.dump({"tipo": "clip_probe", "clip_model": hB["clip_model"], "pretrained": hB["pretrained"], "classes": hB["classes"], "sk_model": s["t90"], "tiles": 3, "creado": now_iso(),
  "info": {"variante": "Mc_tr: DrBerry train (crudo y preprocesado, +aug) + sanas públicas + 278 capturas reales de train (crudas y preprocesadas, orig + 3 aumentos leves, peso 3)", **cfg, "class_weight": "balanced", "preprocesamiento": "panel"}}, O / "clip_probe_tiles3_camara.joblib")
u = json.load(open(D / "resultados/ml/modelo_aug_B/umbral.json")); u = {k: v for k, v in u.items() if k not in ("validacion", "elegido_en", "creado")}
u.update({"creado": now_iso(), "umbral": r["umbral"], "preprocesamiento": "panel", "elegido_en": {"descripcion": "64 capturas reales de val (C, peso y umbral); sens>=0,90, minimo de falsas alarmas", "variante": "Mc_tr_t90"}, "validacion": r["val"]})
json.dump(u, open(O / "umbral.json", "w"), indent=2, ensure_ascii=False)
print(r["umbral"], cfg, r["cap"]["cm"])
