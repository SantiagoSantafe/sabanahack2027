"""Tabla por imagen de DrBerry-Original-Data v1 con grupo de rafaga temporal.
Uso: python -I tabla_imagenes.py <dir_export_yolo> <out_csv> <umbral_s>
Grupo de rafaga: imagenes de la misma camara (inferida por nombre) cuyo timestamp
(en el nombre) dista <= umbral_s de la anterior; DSC: numeros consecutivos (diferencia <= 1).
"""
import collections
import csv
import datetime
import glob
import os
import re
import sys

import yaml

root, out, th = sys.argv[1], sys.argv[2], float(sys.argv[3])
names = yaml.safe_load(open(os.path.join(root, "data.yaml")))["names"]
rows = []
for p in sorted(glob.glob(os.path.join(root, "*", "images", "*"))):
    sp = p.split(os.sep)[-3]
    fn = os.path.basename(p)
    on = fn.split(".rf.")[0]
    if on.startswith("IMG_"):
        cam = "IMG_ (Huawei Y7 2019? inferido)"
    elif on.startswith("DSC"):
        cam = "DSC (Sony DSC-W630? inferido)"
    else:
        cam = "YYYYMMDD_HHMMSS (Samsung A30? inferido)"
    m = re.search(r"(20\d{6})_(\d{6})", on)
    ts = datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S") if m else None
    dsc = int(re.search(r"DSC(\d+)", on).group(1)) if on.startswith("DSC") else None
    lp = os.path.join(root, sp, "labels", os.path.splitext(fn)[0] + ".txt")
    c = collections.Counter()
    for line in open(lp):
        if line.strip():
            c[names[int(line.split()[0])]] += 1
    dom = c.most_common(1)[0][0] if c else ""
    rows.append(dict(split=sp, ruta_relativa="%s/images/%s" % (sp, fn), nombre_original=on,
                     camara_inferida=cam, timestamp_nombre=ts.isoformat() if ts else "",
                     _ts=ts, _dsc=dsc, n_cajas=sum(c.values()),
                     **{"n_" + k: c.get(k, 0) for k in names},
                     clase_dominante=dom, multiclase=int(len(c) > 1)))
# agrupar
gid = 0
for cam in sorted(set(r["camara_inferida"] for r in rows)):
    rs = [r for r in rows if r["camara_inferida"] == cam]
    if rs[0]["_dsc"] is not None:
        rs.sort(key=lambda r: r["_dsc"])
        prev = None
        for r in rs:
            if prev is None or r["_dsc"] - prev > 1:
                gid += 1
            r["grupo_rafaga"] = "g%03d" % gid
            prev = r["_dsc"]
    else:
        rs.sort(key=lambda r: r["_ts"])
        prev = None
        for r in rs:
            if prev is None or (r["_ts"] - prev).total_seconds() > th:
                gid += 1
            r["grupo_rafaga"] = "g%03d" % gid
            prev = r["_ts"]
grp_splits = collections.defaultdict(set)
grp_n = collections.Counter()
for r in rows:
    grp_splits[r["grupo_rafaga"]].add(r["split"])
    grp_n[r["grupo_rafaga"]] += 1
for r in rows:
    r["grupo_en_varios_splits"] = int(len(grp_splits[r["grupo_rafaga"]]) > 1)
    r["tam_grupo"] = grp_n[r["grupo_rafaga"]]
rows.sort(key=lambda r: (r["camara_inferida"], r["_ts"] or datetime.datetime.min, r["_dsc"] or 0))
fields = [k for k in rows[0] if not k.startswith("_")]
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
multi = [g for g, s in grp_splits.items() if len(s) > 1]
print("imagenes", len(rows), "grupos", len(grp_splits), "grupos en >1 split", len(multi))
for sp in ("valid", "test"):
    n = sum(1 for r in rows if r["split"] == sp)
    k = sum(1 for r in rows if r["split"] == sp and r["grupo_en_varios_splits"])
    print(sp, "imagenes", n, "en grupo compartido con otro split", k, "(%.1f%%)" % (100.0 * k / n))
print("tam grupo: max", max(grp_n.values()), "mediana", sorted(grp_n.values())[len(grp_n) // 2])
# clases por grupo (independencia efectiva)
gc = collections.defaultdict(collections.Counter)
for r in rows:
    gc[r["clase_dominante"]][r["grupo_rafaga"]] += 1
print("grupos por clase dominante:", {k: len(v) for k, v in gc.items()})
