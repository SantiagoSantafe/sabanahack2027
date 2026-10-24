"""Ajuste del recorte de sana: se privilegian imagenes de plantas cultivadas (Commons cultivares + iNat captive)."""
import csv, os, shutil, random, sys
R = sys.argv[1]
man = list(csv.DictReader(open(R + "manifiesto.csv")))
mf = list(man[0].keys())
des = list(csv.DictReader(open(R + "_descartadas/descartes.csv")))
df = list(des[0].keys())
restore = ["commons_1765830.jpg", "commons_91979015.jpg", "inat_165956100_287332330.jpg"]
wild = sorted([r for r in man if r["clase"] == "sana" and r["cultivado_captive"] == "False"], key=lambda r: r["archivo"])
random.seed(3)
out = random.sample(wild, len(restore))
for r in out:
    shutil.move(R + "sana/" + r["archivo"], R + "_descartadas/sana/" + r["archivo"])
    man.remove(r)
    d = {k: r.get(k, "") for k in df}; d["motivo_descarte"] = "recorte_tope_60(se_priorizan_cultivadas)"
    des.append(d)
for fn in restore:
    d = [x for x in des if x["clase"] == "sana" and x["archivo"] == fn][0]
    des.remove(d)
    shutil.move(R + "_descartadas/sana/" + fn, R + "sana/" + fn)
    m = {k: d.get(k, "") for k in mf}
    m["ruta"] = "sana/" + fn; m["revision_manual"] = "aceptada"
    if fn.startswith("commons_"):
        m["cultivado_captive"] = "True(cultivar_segun_titulo)"
    lugar = m.get("lugar") or ""
    m["pais_aprox"] = lugar.split(",")[-1].strip() if lugar else ""
    man.append(m)
import hashlib
for m in man:
    if not m.get("md5"):
        m["md5"] = hashlib.md5(open(R + m["ruta"], "rb").read()).hexdigest()
man.sort(key=lambda r: (r["clase"], r["archivo"]))
with open(R + "manifiesto.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=mf); w.writeheader(); w.writerows(man)
with open(R + "_descartadas/descartes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=df); w.writeheader(); w.writerows(des)
print("sacadas", [r["archivo"] for r in out], "sana ahora", sum(1 for r in man if r["clase"] == "sana"), "total", len(man))
