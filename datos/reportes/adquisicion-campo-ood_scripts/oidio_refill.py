"""Oidio: excluye formas de Erysiphe vaccinii sobre hospederos no-Vaccinium (f. elevata=Catalpa, f. epigaeae=Epigaea,
f. eucalyptorum=Eucalyptus, f. convertibilis) y rellena hasta N candidatos con E. vaccinii (especie) / f. vaccinii.
Uso: python3 -I oidio_refill.py <campo_ood_dir> <N>
"""
import json, sys, os, csv, time, random, shutil, collections, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests

ROOT, N = sys.argv[1], int(sys.argv[2])
CAND = os.path.join(ROOT, "_candidatos")
DESC = os.path.join(ROOT, "_descartadas", "oidio")
os.makedirs(DESC, exist_ok=True)
ALLOWED = {"Erysiphe vaccinii", "Erysiphe vaccinii vaccinii"}
OK_LIC = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
rows = json.load(open(os.path.join(ROOT, "_api", "_resumen_obs.json")))
byid = {r["obs_id"]: r for r in rows if r["query"] == "oidio_erysiphe_vaccinii"}
cand_csv = os.path.join(CAND, "candidatos_inat.csv")
cands = list(csv.DictReader(open(cand_csv)))
fields = list(cands[0].keys())
moved = []
keep = []
for c in cands:
    if c["clase"] != "oidio":
        keep.append(c); continue
    r = byid[int(c["obs_id"])]
    if r["taxon"] not in ALLOWED:
        src = os.path.join(CAND, "oidio", c["archivo"])
        if os.path.exists(src):
            shutil.move(src, os.path.join(DESC, c["archivo"]))
        c["motivo_descarte"] = "forma_no_vaccinium:" + r["taxon"]
        moved.append(c)
    else:
        keep.append(c)
have = {int(c["obs_id"]) for c in keep if c["clase"] == "oidio"}
users = collections.Counter(c["autor_login"] for c in keep if c["clase"] == "oidio")
pool = [r for r in byid.values() if r["taxon"] in ALLOWED and r["host_is_vaccinium"] is not False and r["obs_id"] not in have]
random.seed(7)
random.shuffle(pool)
pool.sort(key=lambda r: (users[r["user_login"]], 0 if r["host_is_vaccinium"] else 1))
s = requests.Session()
s.headers.update({"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon, investigacion academica)"})
added = 0
for r in pool:
    if len(have) >= N:
        break
    if users[r["user_login"]] >= 3:
        continue
    p = r["photos"][0]
    if p["license"] not in OK_LIC:
        continue
    url = p["url"].replace("/square.", "/large.")
    fn = "inat_%d_%d.jpg" % (r["obs_id"], p["id"])
    resp = s.get(url, timeout=60)
    if resp.status_code != 200:
        continue
    open(os.path.join(CAND, "oidio", fn), "wb").write(resp.content)
    loc = r.get("location") or ","
    lat, lon = (loc.split(",") + [""])[:2]
    keep.append({"clase": "oidio", "archivo": fn, "fuente": "iNaturalist", "obs_id": r["obs_id"], "photo_id": p["id"],
                 "taxon_identificado": r["taxon"], "nivel_etiqueta": "estricta", "hospedero_declarado": "; ".join(r["host_names"]),
                 "quality_grade": r["quality_grade"], "cultivado_captive": r["captive"], "lugar": r["place_guess"],
                 "lat": lat, "lon": lon, "fecha": r["observed_on"], "autor_login": r["user_login"],
                 "autor_nombre": r["user_name"] or "", "licencia": p["license"], "atribucion": p["attribution"],
                 "url_observacion": r["uri"], "url_foto": url})
    have.add(r["obs_id"]); users[r["user_login"]] += 1; added += 1
    time.sleep(0.4)
with open(cand_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(keep)
with open(os.path.join(ROOT, "_descartadas", "descartes_prefiltro_oidio.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields + ["motivo_descarte"]); w.writeheader(); w.writerows(moved)
print("movidas", len(moved), "agregadas", added, "oidio total", len(have))
