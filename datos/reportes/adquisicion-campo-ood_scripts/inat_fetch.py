"""Descarga METADATOS de observaciones iNaturalist (API publica v1, sin login).
Guarda respuestas crudas en raw/campo_ood/_api/<nombre>.json
Uso: python3 -I inat_fetch.py <outdir>
"""
import json, sys, time, os, urllib.parse, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
BASE = "https://api.inaturalist.org/v1/observations"
LIC = "cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa"
UA = {"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon, investigacion academica)"}

VACC_SPP = [52740, 84542, 52741, 52742, 126142, 84270, 127029, 64714, 48349, 48354,
            48347, 81818, 67792, 52739, 126375, 63820, 170106, 79471, 56312, 63749,
            535109, 48353, 48346]

QUERIES = {
    "oidio_erysiphe_vaccinii": [dict(taxon_id=765061, quality_grade="research")],
    "roya_naohidemyces_pucciniastrum": [dict(taxon_id="628810,1706161", quality_grade="research")],
    "alternaria_q": [dict(taxon_id=327996, q="blueberry"), dict(taxon_id=327996, q="Vaccinium"),
                     dict(taxon_id=327996, q="arandano"), dict(taxon_id=327996, q="arándano")],
    "heliothinae_hostfield": [dict(taxon_id=122535, **{"field:Host Plant ID": ""})],
    "heliothinae_q": [dict(taxon_id=122535, q="blueberry"), dict(taxon_id=122535, q="Vaccinium")],
    "sana_vcorymbosum_hojaverde": [dict(taxon_id=52740, term_id=36, term_value_id=38)],
}
# Orugas (Lepidoptera) con planta hospedera Vaccinium declarada en el campo "Host Plant ID"
QUERIES["lepidoptera_host_vaccinium"] = [dict(taxon_id=47157, **{"field:Host Plant ID": str(t)}) for t in VACC_SPP]
# Alternaria con hospedero Vaccinium declarado
QUERIES["alternaria_host_vaccinium"] = [dict(taxon_id=327996, **{"field:Host Plant ID": str(t)}) for t in VACC_SPP]
QUERIES["alternaria_fungushost"] = [dict(taxon_id=327996, **{"field:Fungus Substrate/Host": ""})]

log = []
for name, plist in QUERIES.items():
    seen = {}
    for p in plist:
        page = 1
        while True:
            params = dict(p)
            params.update(photo_license=LIC, photos="true", per_page=200, page=page, order_by="id", order="asc")
            r = requests.get(BASE, params=params, headers=UA, timeout=60)
            url = r.url
            r.raise_for_status()
            d = r.json()
            for o in d["results"]:
                seen[o["id"]] = o
            log.append({"query": name, "url": url, "total": d["total_results"], "page": page})
            print(name, page, d["total_results"], len(seen), flush=True)
            time.sleep(1.1)
            if page * 200 >= d["total_results"] or not d["results"]:
                break
            page += 1
    with open(os.path.join(OUT, name + ".json"), "w") as f:
        json.dump(list(seen.values()), f)
with open(os.path.join(OUT, "_query_log.json"), "w") as f:
    json.dump(log, f, indent=1)
