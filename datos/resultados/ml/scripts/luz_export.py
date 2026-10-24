"""Exporta el modelo L4 (sonda 3x3 + sanas públicas) al formato de modelo_aug_B: joblib + umbral.json."""
import json, sys
from pathlib import Path
D = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos"); sys.path.insert(0, str(D / "pipeline"))
import joblib
from common import now_iso
OUT = D / "resultados/ml/modelo_luz"
NAME = sys.argv[1] if len(sys.argv) > 1 else "L4"
res = json.load(open(OUT / "modelos_resumen.json"))[NAME]
hB = joblib.load(D / "resultados/ml/modelo_aug_B/clip_probe_tiles3_aug_dev.joblib")
tiles = 3 if res["grid"] == 0 else 4
info = {"C_elegido": res["C"], "busqueda_C": res.get("busqueda"), "class_weight": "balanced", "variante": f"{NAME}: train+val preprocesados (corregir_color+recorte_por_color del panel) + 6 aumentos de cámara por imagen" + (" + sanas públicas (PlantDoc/PlantVillage/iNaturalist, partes de entrenamiento agrupadas)" if res.get("publicas") else ""),
        "preprocesamiento": "corregir_color + recorte_por_color (robot/panel_demo.py); el panel debe aplicarlos antes de clasificar", "aumentos": "resultados/ml/scripts/luz_common.py:aug_camara", "umbral_en": "OOF dev limpio preprocesado (regla de B, sens>=0,90)"}
joblib.dump({"tipo": "clip_probe", "clip_model": hB["clip_model"], "pretrained": hB["pretrained"], "classes": hB["classes"], "sk_model": joblib.load(OUT / f"cache/sk_{NAME}.joblib"), "info": info, "tiles": tiles, "creado": now_iso()}, OUT / f"clip_probe_tiles{tiles}_luz.joblib")
u = {k: v for k, v in json.load(open(D / "resultados/ml/modelo_aug_B/umbral.json")).items() if k not in ("validacion", "elegido_en", "creado")}
u.update({"creado": now_iso(), "umbral": res["umbral"], "elegido_en": {"descripcion": "OOF dev limpio preprocesado (CV agrupada 5 pliegues)", "variante": NAME}, "validacion": res["oof_dev"]})
json.dump(u, open(OUT / "umbral.json", "w"), indent=2, ensure_ascii=False)
print("ok", NAME, tiles, res["umbral"])
