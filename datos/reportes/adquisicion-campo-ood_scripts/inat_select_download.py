"""Selecciona candidatos por clase (diversidad de autores) y descarga 1 foto por observacion (tamano 'large', <=1024 px)
desde inaturalist-open-data (solo licencias abiertas). Escribe _candidatos/<clase>/ y _candidatos/candidatos.csv
Uso: python3 -I inat_select_download.py <campo_ood_dir>
"""
import json, sys, os, csv, time, random, collections, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests

ROOT = sys.argv[1]
API = os.path.join(ROOT, "_api", "_resumen_obs.json")
CAND = os.path.join(ROOT, "_candidatos")
os.makedirs(CAND, exist_ok=True)
UA = {"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon, investigacion academica)"}
OK_LIC = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
MINERS = ('Cameraria', 'Gracillariidae', 'Stigmella', 'Coptodisca', 'Caloptilia', 'Parornix', 'Coleophora', 'Marmara',
          'Paraclemensia', 'Fomoria', 'Phyllocnistis', 'Lyonetia', 'Ectoedemia', 'Nepticulidae', 'Heliozelidae',
          'Antispila', 'Phyllonorycter', 'Bucculatrix')
random.seed(42)
rows = json.load(open(API))


def pick(cands, n, per_user, prefer=None):
    """round-robin por autor; prefer = funcion clave para ordenar (menor primero)"""
    random.shuffle(cands)
    if prefer:
        cands.sort(key=prefer)
    by_user = collections.OrderedDict()
    for r in cands:
        by_user.setdefault(r["user_login"], []).append(r)
    out = []
    rnd = 0
    while len(out) < n and rnd < per_user:
        for u, lst in by_user.items():
            if rnd < len(lst) and len(out) < n:
                out.append(lst[rnd])
        rnd += 1
    return out


sel = {}
oid = [r for r in rows if r["query"] == "oidio_erysiphe_vaccinii" and r["host_is_vaccinium"] is not False]
sel["oidio"] = [(r, "estricta") for r in pick(oid, 90, 3, prefer=lambda r: 0 if r["host_is_vaccinium"] else 1)]
roy = [r for r in rows if r["query"] == "roya_naohidemyces_pucciniastrum" and r["host_is_vaccinium"] is not False]
sel["roya"] = [(r, "estricta") for r in pick(roy, 90, 4, prefer=lambda r: 0 if r["host_is_vaccinium"] else 1)]
san = [r for r in rows if r["query"] == "sana_vcorymbosum_hojaverde" and (r["quality_grade"] == "research" or r["captive"])]
sel["sana"] = [(r, "especie_verificada+revision_visual") for r in pick(san, 90, 2, prefer=lambda r: 0 if r["captive"] else 1)]
lep = [r for r in rows if r["query"] == "lepidoptera_host_vaccinium" and not (r["taxon"] or "").startswith(MINERS)
       and not set(r["life_stage_values"]) & {2, 4, 7}]
sel["heliothis_oruga"] = [(r, "proxy_oruga_no_heliothinae") for r in pick(lep, 90, 6)]
alt_ids = {374777114, 188456421, 315075664}
alt = {r["obs_id"]: r for r in rows if r["obs_id"] in alt_ids}
sel["alternaria"] = [(r, "identificacion_no_verificada(needs_id)") for r in alt.values()]

out_rows = []
s = requests.Session()
s.headers.update(UA)
for clase, lst in sel.items():
    d = os.path.join(CAND, clase)
    os.makedirs(d, exist_ok=True)
    for r, nivel in lst:
        # alternaria: bajar todas las fotos (pocas observaciones); resto: primera foto
        photos = r["photos"] if clase == "alternaria" else r["photos"][:1]
        for k, p in enumerate(photos):
            if p["license"] not in OK_LIC:
                continue
            url = p["url"].replace("/square.", "/large.")
            ext = os.path.splitext(url)[1] or ".jpg"
            fn = "inat_%d_%d%s" % (r["obs_id"], p["id"], ext.lower().replace(".jpeg", ".jpg"))
            fp = os.path.join(d, fn)
            if not os.path.exists(fp):
                resp = s.get(url, timeout=60)
                if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image"):
                    print("FAIL", url, resp.status_code)
                    continue
                with open(fp, "wb") as f:
                    f.write(resp.content)
                time.sleep(0.4)
            loc = r.get("location") or ","
            lat, lon = (loc.split(",") + [""])[:2]
            out_rows.append({
                "clase": clase, "archivo": fn, "fuente": "iNaturalist", "obs_id": r["obs_id"], "photo_id": p["id"],
                "taxon_identificado": r["taxon"], "nivel_etiqueta": nivel, "hospedero_declarado": "; ".join(r["host_names"]),
                "quality_grade": r["quality_grade"], "cultivado_captive": r["captive"], "lugar": r["place_guess"],
                "lat": lat, "lon": lon, "fecha": r["observed_on"], "autor_login": r["user_login"],
                "autor_nombre": r["user_name"] or "", "licencia": p["license"], "atribucion": p["attribution"],
                "url_observacion": r["uri"], "url_foto": url,
            })
        print(clase, len(out_rows), flush=True)

with open(os.path.join(CAND, "candidatos_inat.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)
print("total", len(out_rows))
