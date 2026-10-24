"""Analiza una exportacion YOLO (data.yaml + {train,valid,test}/{images,labels}).
Uso: python -I analiza_yolo.py <dir_export> <dataset_id> <version> <out_csv> <out_json>
No modifica nada en el dataset.
"""
import collections
import csv
import datetime
import hashlib
import json
import os
import re
import statistics
import sys

import yaml
from PIL import Image

SPLITS = ["train", "valid", "test"]


def dhash(path, size=8):
    im = Image.open(path).convert("L").resize((size + 1, size), Image.BILINEAR)
    px = list(im.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | (px[r * (size + 1) + c] > px[r * (size + 1) + c + 1])
    return bits


def orig_name(fn):
    # Roboflow renombra: <original>_<ext>.rf.<hash>.jpg
    return fn.split(".rf.")[0]


TS = re.compile(r"(20\d{6})_(\d{6})")


def ts_of(name):
    m = TS.search(name)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def main():
    root, ds, ver, out_csv, out_json = sys.argv[1:6]
    cfg = yaml.safe_load(open(os.path.join(root, "data.yaml")))
    names = cfg["names"]
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    boxes = collections.Counter()          # (split, cls) -> n cajas
    imgs_with = collections.Counter()      # (split, cls) -> n imagenes que contienen la clase
    imgs_split = collections.Counter()
    empty = collections.Counter()
    multi_cls = collections.Counter()
    per_img_boxes = collections.defaultdict(list)
    box_area = collections.defaultdict(list)  # cls -> area normalizada
    box_wh = collections.defaultdict(list)
    sizes = collections.Counter()
    modes = collections.Counter()
    weird = []
    dominant = collections.Counter()       # (split, clase dominante por nro de cajas)
    hashes = {}
    md5s = collections.defaultdict(list)
    origs = collections.defaultdict(list)
    times = collections.defaultdict(list)
    examples = {}
    for sp in SPLITS:
        idir = os.path.join(root, sp, "images")
        ldir = os.path.join(root, sp, "labels")
        if not os.path.isdir(idir):
            continue
        for fn in sorted(os.listdir(idir)):
            p = os.path.join(idir, fn)
            imgs_split[sp] += 1
            with Image.open(p) as im:
                sizes[im.size] += 1
                modes[im.mode] += 1
            md5s[hashlib.md5(open(p, "rb").read()).hexdigest()].append((sp, fn))
            hashes[(sp, fn)] = dhash(p)
            on = orig_name(fn)
            origs[on].append(sp)
            t = ts_of(on)
            if t:
                times[sp].append((t, fn))
            lp = os.path.join(ldir, os.path.splitext(fn)[0] + ".txt")
            cls_here = collections.Counter()
            if os.path.exists(lp):
                for ln, line in enumerate(open(lp)):
                    parts = line.split()
                    if not parts:
                        continue
                    if len(parts) != 5:
                        weird.append((sp, fn, ln, "campos=%d (posible poligono)" % len(parts)))
                        # intento: tomar bbox del poligono
                        try:
                            c = int(parts[0])
                            xs = list(map(float, parts[1::2]))
                            ys = list(map(float, parts[2::2]))
                            w, h = max(xs) - min(xs), max(ys) - min(ys)
                        except Exception:
                            continue
                    else:
                        c = int(parts[0])
                        x, y, w, h = map(float, parts[1:])
                        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                            weird.append((sp, fn, ln, "coords fuera de [0,1] o w/h<=0"))
                    if c < 0 or c >= len(names):
                        weird.append((sp, fn, ln, "clase fuera de rango %d" % c))
                        continue
                    cn = names[c]
                    boxes[(sp, cn)] += 1
                    cls_here[cn] += 1
                    box_area[cn].append(w * h)
                    box_wh[cn].append((w, h))
                    examples.setdefault(cn, "%s/images/%s" % (sp, fn))
            n = sum(cls_here.values())
            per_img_boxes[sp].append(n)
            if n == 0:
                empty[sp] += 1
                dominant[(sp, "_sin_etiqueta")] += 1
            else:
                for cn in cls_here:
                    imgs_with[(sp, cn)] += 1
                if len(cls_here) > 1:
                    multi_cls[sp] += 1
                top = cls_here.most_common()
                dominant[(sp, top[0][0])] += 1
    # duplicados exactos y casi-duplicados entre splits
    exact_dups = [v for v in md5s.values() if len(v) > 1]
    keys = list(hashes)
    near = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            d = bin(hashes[keys[i]] ^ hashes[keys[j]]).count("1")
            if d <= 4:
                near.append((keys[i], keys[j], d))
    near_cross = [x for x in near if x[0][0] != x[1][0]]
    orig_multi_split = {k: v for k, v in origs.items() if len(set(v)) > 1}
    orig_repeated = {k: v for k, v in origs.items() if len(v) > 1}
    # cercania temporal entre test/valid y train
    gaps = {}
    tr = sorted(times.get("train", []))
    for sp in ("valid", "test"):
        g = []
        for t, fn in times.get(sp, []):
            if tr:
                g.append(min(abs((t - t2).total_seconds()) for t2, _ in tr))
        if g:
            gaps[sp] = {
                "n": len(g),
                "mediana_s": statistics.median(g),
                "pct_<=10s": round(100 * sum(1 for x in g if x <= 10) / len(g), 1),
                "pct_<=30s": round(100 * sum(1 for x in g if x <= 30) / len(g), 1),
                "pct_<=60s": round(100 * sum(1 for x in g if x <= 60) / len(g), 1),
            }
    all_t = sorted(t for sp in times for t, _ in times[sp])
    dates = collections.Counter(t.date().isoformat() for t in all_t)
    # CSV
    rows = []
    for sp in SPLITS + ["total"]:
        sps = SPLITS if sp == "total" else [sp]
        tot_split = sum(boxes[(s, c)] for s in sps for c in names)
        for cn in names:
            nb = sum(boxes[(s, cn)] for s in sps)
            ni = sum(imgs_with[(s, cn)] for s in sps)
            nd = sum(dominant[(s, cn)] for s in sps)
            rows.append({
                "dataset": ds, "version": ver, "split": sp, "clase": cn,
                "n_cajas": nb, "pct_cajas_split": round(100 * nb / tot_split, 1) if tot_split else 0,
                "n_imagenes_con_clase": ni, "n_imagenes_clase_dominante": nd,
                "n_imagenes_split": sum(imgs_split[s] for s in sps),
            })
    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if write_header:
            w.writeheader()
        w.writerows(rows)
    summ = {
        "dataset": ds, "version": ver, "names": names,
        "imagenes_por_split": dict(imgs_split),
        "imagenes_sin_etiqueta": dict(empty),
        "imagenes_multiclase": dict(multi_cls),
        "cajas_por_imagen": {sp: {"media": round(statistics.mean(v), 2), "mediana": statistics.median(v), "max": max(v), "min": min(v)} for sp, v in per_img_boxes.items() if v},
        "tamanos_imagen": {"%dx%d" % k: v for k, v in sizes.items()},
        "modos_color": dict(modes),
        "area_caja_normalizada": {c: {"mediana": round(statistics.median(v), 4), "p10": round(sorted(v)[len(v) // 10], 4), "p90": round(sorted(v)[(9 * len(v)) // 10], 4), "min": round(min(v), 5), "max": round(max(v), 4)} for c, v in box_area.items()},
        "cajas_diminutas_(<0.1% area)": {c: sum(1 for a in v if a < 0.001) for c, v in box_area.items()},
        "cajas_grandes_(>50% area)": {c: sum(1 for a in v if a > 0.5) for c, v in box_area.items()},
        "etiquetas_raras": weird[:50], "n_etiquetas_raras": len(weird),
        "duplicados_exactos_md5": exact_dups,
        "casi_duplicados_dhash<=4": len(near), "casi_duplicados_entre_splits": len(near_cross),
        "ejemplos_casi_duplicados_entre_splits": [[a[0] + "/" + a[1], b[0] + "/" + b[1], d] for a, b, d in near_cross[:15]],
        "nombre_original_repetido": len(orig_repeated),
        "nombre_original_en_varios_splits": len(orig_multi_split),
        "ejemplos_nombre_original_en_varios_splits": list(orig_multi_split.items())[:10],
        "imagenes_con_timestamp_en_nombre": len(all_t),
        "fechas_captura_(segun_nombre)": dict(sorted(dates.items())),
        "rango_captura": [all_t[0].isoformat(), all_t[-1].isoformat()] if all_t else None,
        "brecha_temporal_a_train_mas_cercana": gaps,
        "ejemplos_rutas": examples,
    }
    with open(out_json, "w") as f:
        json.dump(summ, f, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(summ, indent=1, ensure_ascii=False, default=str)[:6000])


if __name__ == "__main__":
    main()
