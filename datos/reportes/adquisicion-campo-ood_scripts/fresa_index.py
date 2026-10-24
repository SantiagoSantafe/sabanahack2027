"""Indices por imagen de los datasets de fresa. Uso: python3 -I fresa_index.py <afzaal_extraido_dir> <mendeley_dir>"""
import json, os, sys, csv, collections

A, M = sys.argv[1], sys.argv[2]
# Mapeo a enfermedades del proyecto (proxy)
PROXY = {"gray_mold": "botrytis_proxy", "anthracnose_fruit_rot": "antracnosis_proxy",
         "powdery_mildew_leaf": "oidio_proxy", "powdery_mildew_fruit": "oidio_proxy",
         "angular_leafspot": "otra(no_foco)", "leaf_spot": "otra(no_foco)", "blossom_blight": "otra(no_foco)",
         "asymptomatic_strawberry": "sana_proxy"}
rows = []
for split in ("train", "val", "test"):
    d = os.path.join(A, split, "ann")
    for f in sorted(os.listdir(d)):
        j = json.load(open(os.path.join(d, f)))
        cls = sorted({o["classTitle"] for o in j.get("objects", [])})
        tags = sorted({t["name"] for t in j.get("tags", [])})
        rows.append({"split": split, "imagen": "extraido/%s/img/%s" % (split, f[:-5]), "clases": "|".join(cls),
                     "proxy_proyecto": "|".join(sorted({PROXY.get(c, c) for c in cls})), "n_objetos": len(j.get("objects", [])),
                     "tags": "|".join(tags), "ancho": j["size"]["width"], "alto": j["size"]["height"]})
out = os.path.join(os.path.dirname(A.rstrip("/")), "indice_imagenes.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
c = collections.Counter()
for r in rows:
    for k in r["clases"].split("|"):
        c[(r["split"], k)] += 1
print("AFZAAL", len(rows))
for k, v in sorted(c.items()):
    print(" ", k, v)
print(" multi-clase:", sum(1 for r in rows if "|" in r["clases"]), " tags:", collections.Counter(r["tags"] for r in rows))

j = json.load(open(os.path.join(M, "_annotations.coco.json")))
cat = {c["id"]: c["name"] for c in j["categories"]}
per = collections.defaultdict(set)
for a in j["annotations"]:
    per[a["image_id"]].add(cat[a["category_id"]])
rows2 = []
for im in j["images"]:
    cl = sorted(per.get(im["id"], []))
    norm = [x.lower().replace("powderly", "powdery").replace(" ", "_") for x in cl]
    rows2.append({"imagen": im["file_name"], "nombre_original": im.get("extra", {}).get("name", ""), "clases": "|".join(cl),
                  "proxy_proyecto": "|".join(sorted({PROXY.get(x, x) for x in norm})),
                  "existe_local": os.path.exists(os.path.join(M, im["file_name"]))})
with open(os.path.join(M, "indice_imagenes.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows2[0].keys())); w.writeheader(); w.writerows(rows2)
c2 = collections.Counter(x for r in rows2 for x in r["clases"].split("|"))
print("MENDELEY test", len(rows2), "existentes", sum(r["existe_local"] for r in rows2))
for k, v in sorted(c2.items()):
    print(" ", k, v)
orig = {r["nombre_original"] for r in rows2}
afz = {os.path.basename(r["imagen"]) for r in rows}
print(" nombres originales que coinciden con Afzaal:", len(orig & afz), "de", len(orig))
afz_split = {os.path.basename(r["imagen"]): r["split"] for r in rows}
print(" split Afzaal de esos:", collections.Counter(afz_split[n] for n in orig & afz))
