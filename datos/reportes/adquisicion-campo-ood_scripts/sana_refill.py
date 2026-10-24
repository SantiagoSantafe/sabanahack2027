"""Sana: agrega M candidatos nuevos (V. corymbosum hoja verde; research o cultivado) a _candidatos/sana. Uso: python3 -I sana_refill.py <campo_ood_dir> <M>"""
import json, sys, os, csv, time, random, collections, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests
ROOT, M = sys.argv[1], int(sys.argv[2])
CAND = os.path.join(ROOT, "_candidatos")
OK_LIC = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
rows = json.load(open(os.path.join(ROOT, "_api", "_resumen_obs.json")))
cand_csv = os.path.join(CAND, "candidatos_inat.csv")
cands = list(csv.DictReader(open(cand_csv)))
fields = list(cands[0].keys())
have = {int(c["obs_id"]) for c in cands if c["clase"] == "sana"}
users = collections.Counter(c["autor_login"] for c in cands if c["clase"] == "sana")
pool = [r for r in rows if r["query"] == "sana_vcorymbosum_hojaverde" and (r["quality_grade"] == "research" or r["captive"]) and r["obs_id"] not in have]
random.seed(11); random.shuffle(pool)
pool.sort(key=lambda r: users[r["user_login"]])
s = requests.Session(); s.headers.update({"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon, investigacion academica)"})
added = 0
for r in pool:
    if added >= M: break
    if users[r["user_login"]] >= 3: continue
    # elegir la foto de la observacion: la primera (sin seleccion por contenido)
    p = r["photos"][0]
    if p["license"] not in OK_LIC: continue
    url = p["url"].replace("/square.", "/large.")
    fn = "inat_%d_%d.jpg" % (r["obs_id"], p["id"])
    resp = s.get(url, timeout=60)
    if resp.status_code != 200: continue
    open(os.path.join(CAND, "sana", fn), "wb").write(resp.content)
    loc = r.get("location") or ","
    lat, lon = (loc.split(",") + [""])[:2]
    cands.append({"clase": "sana", "archivo": fn, "fuente": "iNaturalist", "obs_id": r["obs_id"], "photo_id": p["id"],
                  "taxon_identificado": r["taxon"], "nivel_etiqueta": "especie_verificada+revision_visual",
                  "hospedero_declarado": "", "quality_grade": r["quality_grade"], "cultivado_captive": r["captive"],
                  "lugar": r["place_guess"], "lat": lat, "lon": lon, "fecha": r["observed_on"], "autor_login": r["user_login"],
                  "autor_nombre": r["user_name"] or "", "licencia": p["license"], "atribucion": p["attribution"],
                  "url_observacion": r["uri"], "url_foto": url})
    users[r["user_login"]] += 1; added += 1
    time.sleep(0.4)
with open(cand_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(cands)
print("agregadas", added)
