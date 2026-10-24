"""Resume observaciones iNat: hospedero, estadio, licencias. Resuelve taxones hospederos.
Uso: python3 -I inat_summarize.py <api_dir>  -> escribe <api_dir>/_resumen_obs.json
"""
import json, sys, os, glob, time, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests

A = sys.argv[1]
UA = {"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon, investigacion academica)"}
HOST_FIELDS = {"Host Plant ID", "Fungus Substrate/Host", "Host", "EwA - Host Documentation",
               "Host plant", "Plant host", "Host Plant"}
VACCINIUM = 48353

rows = []
host_ids = set()
for fn in sorted(glob.glob(os.path.join(A, "*.json"))):
    name = os.path.basename(fn)[:-5]
    if name.startswith("_"):
        continue
    for o in json.load(open(fn)):
        hosts = []
        for f in o.get("ofvs", []):
            if f.get("name") in HOST_FIELDS:
                hosts.append({"field": f["name"], "datatype": f.get("datatype"), "value": f.get("value")})
                if f.get("datatype") == "taxon":
                    try:
                        host_ids.add(int(f["value"]))
                    except Exception:
                        pass
        life = []
        for a in o.get("annotations", []) or []:
            if a.get("controlled_attribute_id") == 1:
                life.append(a.get("controlled_value_id"))
        country = None
        rows.append({
            "query": name, "obs_id": o["id"], "uri": o.get("uri"), "taxon": (o.get("taxon") or {}).get("name"),
            "taxon_id": (o.get("taxon") or {}).get("id"), "taxon_ancestors": (o.get("taxon") or {}).get("ancestor_ids"),
            "quality_grade": o.get("quality_grade"), "captive": o.get("captive"),
            "observed_on": o.get("observed_on"), "place_guess": o.get("place_guess"),
            "location": o.get("location"), "user_login": o["user"]["login"], "user_name": o["user"].get("name"),
            "obs_license": o.get("license_code"), "description": (o.get("description") or "")[:400],
            "hosts": hosts, "life_stage_values": life, "tags": o.get("tags"),
            "photos": [{"id": p["id"], "license": p.get("license_code"), "attribution": p.get("attribution"),
                        "url": p.get("url"), "dims": p.get("original_dimensions")} for p in o.get("photos", [])],
            "num_agree": o.get("num_identification_agreements"), "num_disagree": o.get("num_identification_disagreements"),
        })

# resolver taxones hospederos
host_info = {}
ids = sorted(host_ids)
for i in range(0, len(ids), 30):
    chunk = ids[i:i + 30]
    r = requests.get("https://api.inaturalist.org/v1/taxa/" + ",".join(map(str, chunk)), headers=UA, timeout=60)
    r.raise_for_status()
    for t in r.json()["results"]:
        host_info[t["id"]] = {"name": t["name"], "ancestors": t.get("ancestor_ids", []), "rank": t.get("rank")}
    time.sleep(1.1)

for r_ in rows:
    names, isv = [], None
    for h in r_["hosts"]:
        if h["datatype"] == "taxon":
            try:
                hi = host_info.get(int(h["value"]))
            except Exception:
                hi = None
            if hi:
                names.append(hi["name"])
                v = VACCINIUM in hi["ancestors"] or int(h["value"]) == VACCINIUM
                isv = v if isv is None else (isv or v)
        else:
            names.append(str(h["value"]))
            if isv is None and h["value"] and "vaccin" in str(h["value"]).lower():
                isv = True
    r_["host_names"] = names
    r_["host_is_vaccinium"] = isv

json.dump(rows, open(os.path.join(A, "_resumen_obs.json"), "w"), indent=0)
import collections
c = collections.Counter((r["query"], r["host_is_vaccinium"]) for r in rows)
for k, v in sorted(c.items(), key=lambda x: str(x)):
    print(k, v)
