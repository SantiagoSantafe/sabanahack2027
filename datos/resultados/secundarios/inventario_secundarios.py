"""Inventario de datasets secundarios (PlantDoc y PlantVillage) para evaluación fuera del dominio.

Uso (desde /Users/santiagosantafe/Downloads/SabanaHack/datos, nunca desde raw/):
    .venv/bin/python -I resultados/secundarios/inventario_secundarios.py

Lee solo archivos locales ya descargados en raw/plantdoc y raw/plantvillage.
Escribe en resultados/secundarios/ y genera recortes de hojas en raw/plantdoc/crops_od/.
No usa red ni la API key de Roboflow.
"""
import csv
import collections
import hashlib
import json
import os
import statistics
import sys

from PIL import Image
import imagehash

BASE = "/Users/santiagosantafe/Downloads/SabanaHack/datos"
PD_CLS = os.path.join(BASE, "raw/plantdoc/PlantDoc-Dataset")
PD_COL = os.path.join(BASE, "raw/plantdoc/PlantDoc-Dataset_colisiones")
PD_OD = os.path.join(BASE, "raw/plantdoc/PlantDoc-Object-Detection-Dataset")
PD_CROPS = os.path.join(BASE, "raw/plantdoc/crops_od")
PV = os.path.join(BASE, "raw/plantvillage/PlantVillage-Dataset")
PV_SPLITS = os.path.join(BASE, "raw/plantvillage/hf_splits")
OUT = os.path.join(BASE, "resultados/secundarios")

LIC_PD = "CC BY 4.0 (LICENSE.txt del repo y metadatos Roboflow)"
LIC_PV = "CC BY-SA 3.0 (tarjeta HF mohanty/PlantVillage; el repo GitHub no tiene LICENSE)"

# Mapeo de clases originales a las categorías de evaluación del proyecto.
# Clases de nuestro clasificador: sana, oidio, alternaria, heliothis (arándano, DrBerry).
PD_MAP = {
    "Blueberry leaf": ("sana_arandano", "Vaccinium (especie no indicada)"),
    "Squash Powdery mildew leaf": ("oidio_otra_especie", "calabaza"),
    "Tomato Early blight leaf": ("alternaria_otra_especie", "tomate"),
    "Potato leaf early blight": ("alternaria_otra_especie", "papa"),
    "Apple leaf": ("sana_otra_especie", "manzano"),
    "Bell_pepper leaf": ("sana_otra_especie", "pimentón"),
    "Cherry leaf": ("sana_otra_especie", "cerezo"),
    "Peach leaf": ("sana_otra_especie", "durazno"),
    "Raspberry leaf": ("sana_otra_especie", "frambuesa"),
    "Soyabean leaf": ("sana_otra_especie", "soya"),
    "Strawberry leaf": ("sana_otra_especie", "fresa"),
    "Tomato leaf": ("sana_otra_especie", "tomate"),
    "grape leaf": ("sana_otra_especie", "vid"),
    "Apple Scab Leaf": ("otra_enfermedad_otra_especie", "manzano"),
    "Apple rust leaf": ("otra_enfermedad_otra_especie", "manzano"),
    "Bell_pepper leaf spot": ("otra_enfermedad_otra_especie", "pimentón"),
    "Corn Gray leaf spot": ("otra_enfermedad_otra_especie", "maíz"),
    "Corn leaf blight": ("otra_enfermedad_otra_especie", "maíz"),
    "Corn rust leaf": ("otra_enfermedad_otra_especie", "maíz"),
    "Potato leaf late blight": ("otra_enfermedad_otra_especie", "papa"),
    "Tomato Septoria leaf spot": ("otra_enfermedad_otra_especie", "tomate"),
    "Tomato leaf bacterial spot": ("otra_enfermedad_otra_especie", "tomate"),
    "Tomato leaf late blight": ("otra_enfermedad_otra_especie", "tomate"),
    "Tomato leaf mosaic virus": ("otra_enfermedad_otra_especie", "tomate"),
    "Tomato leaf yellow virus": ("otra_enfermedad_otra_especie", "tomate"),
    "Tomato mold leaf": ("otra_enfermedad_otra_especie", "tomate"),
    "grape leaf black rot": ("otra_enfermedad_otra_especie", "vid"),
    "Tomato two spotted spider mites leaf": ("excluir_acaros_fuera_de_foco", "tomate"),
    "Potato leaf": ("sana_otra_especie", "papa"),
    "Soybean leaf": ("sana_otra_especie", "soya"),
}
PV_MAP = {
    "Blueberry___healthy": ("sana_arandano", "Vaccinium (especie no indicada)"),
    "Cherry_(including_sour)___Powdery_mildew": ("oidio_otra_especie", "cerezo"),
    "Squash___Powdery_mildew": ("oidio_otra_especie", "calabaza"),
    "Potato___Early_blight": ("alternaria_otra_especie", "papa"),
    "Tomato___Early_blight": ("alternaria_otra_especie", "tomate"),
}
CROP_CLASSES = {"Blueberry leaf", "Squash Powdery mildew leaf", "Tomato Early blight leaf", "Potato leaf early blight"}
MIN_CROP_SIDE = 64  # px; recortes más pequeños se marcan como no aptos


def img_info(path):
    with Image.open(path) as im:
        w, h = im.size
        mode = im.mode
        fmt = im.format
        ph = str(imagehash.phash(im.convert("RGB")))
    return w, h, mode, fmt, ph


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    resumen = {"plantdoc": {}, "plantvillage": {}, "plantdoc_crops": {}, "duplicados": {}}

    # ---------------- PlantDoc (clasificación, imágenes completas) ----------------
    pd_hash = {}
    pd_names = collections.defaultdict(list)
    errores = []
    # En macOS (sistema de archivos insensible a mayúsculas) 6 pares de archivos chocan por nombre;
    # se restauraron ambos con `git cat-file` en PD_COL/<split>/<clase>/v_<sha7>/<nombre>.
    colis = set()
    col_files = collections.defaultdict(list)
    col_tsv = os.path.join(PD_COL, "colisiones.tsv")
    if os.path.exists(col_tsv):
        for line in open(col_tsv, encoding="utf-8"):
            sha, rel = line.rstrip("\n").split("\t", 1)
            colis.add(rel.lower())
            split_c, cls_c, name_c = rel.split("/", 2)
            col_files[(split_c, cls_c)].append(os.path.join(PD_COL, split_c, cls_c, "v_" + sha[:7], name_c))
    for split in ("train", "test"):
        sd = os.path.join(PD_CLS, split)
        for cls in sorted(os.listdir(sd)):
            cd = os.path.join(sd, cls)
            if not os.path.isdir(cd):
                continue
            ws, hs, n = [], [], 0
            paths = [os.path.join(cd, f) for f in sorted(os.listdir(cd))
                     if ("%s/%s/%s" % (split, cls, f)).lower() not in colis and not f.startswith(".")]
            paths += col_files.get((split, cls), [])
            for p in paths:
                f = os.path.basename(p)
                try:
                    w, h, mode, fmt, ph = img_info(p)
                except Exception as e:  # imagen corrupta o formato raro
                    errores.append((os.path.relpath(p, BASE), type(e).__name__))
                    continue
                n += 1
                ws.append(w)
                hs.append(h)
                pd_hash[os.path.relpath(p, BASE)] = (ph, cls, split)
                pd_names[f].append(os.path.relpath(p, BASE))
                cat, esp = PD_MAP.get(cls, ("sin_mapear", "?"))
                manifest.append({
                    "fuente": "PlantDoc", "ruta": os.path.relpath(p, BASE), "clase_original": cls,
                    "categoria_eval": cat, "especie": esp, "dominio": "web (imagen completa, fondo natural)",
                    "split_original": split, "grupo": "", "ancho": w, "alto": h, "phash": ph,
                    "licencia": LIC_PD,
                })
            key = "%s/%s" % (split, cls)
            resumen["plantdoc"][key] = {
                "imagenes": n,
                "ancho_mediana": statistics.median(ws) if ws else None,
                "alto_mediana": statistics.median(hs) if hs else None,
                "lado_min_p10": sorted(min(a, b) for a, b in zip(ws, hs))[len(ws) // 10] if ws else None,
            }
    resumen["plantdoc_errores_lectura"] = errores

    # Duplicados exactos de pHash dentro de PlantDoc (fuga train/test y entre clases)
    by_hash = collections.defaultdict(list)
    for rel, (ph, cls, split) in pd_hash.items():
        by_hash[ph].append((rel, cls, split))
    grupos = [v for v in by_hash.values() if len(v) > 1]
    cruz_split = [g for g in grupos if len({s for _, _, s in g}) > 1]
    cruz_clase = [g for g in grupos if len({c for _, c, _ in g}) > 1]
    blue = [g for g in grupos if any(c == "Blueberry leaf" for _, c, _ in g)]
    resumen["duplicados"]["plantdoc_grupos_phash_identico"] = len(grupos)
    resumen["duplicados"]["plantdoc_imagenes_en_grupos"] = sum(len(g) for g in grupos)
    resumen["duplicados"]["plantdoc_grupos_train_y_test"] = len(cruz_split)
    resumen["duplicados"]["plantdoc_grupos_entre_clases"] = len(cruz_clase)
    resumen["duplicados"]["plantdoc_grupos_con_blueberry"] = [[r for r, _, _ in g] for g in blue]
    resumen["duplicados"]["plantdoc_ejemplos_entre_clases"] = [[(r, c) for r, c, _ in g] for g in cruz_clase[:10]]
    # Casi-duplicados: distancia de Hamming de pHash <= 6 (de 64 bits)
    items = [(rel, int(ph, 16), cls, split) for rel, (ph, cls, split) in pd_hash.items()]
    near = []
    for i in range(len(items)):
        ri, hi, ci, si = items[i]
        for j in range(i + 1, len(items)):
            rj, hj, cj, sj = items[j]
            d = bin(hi ^ hj).count("1")
            if d <= 6:
                near.append((d, ri, ci, si, rj, cj, sj))
    resumen["duplicados"]["plantdoc_pares_casi_dup_hamming_le6"] = len(near)
    resumen["duplicados"]["plantdoc_pares_casi_dup_train_vs_test"] = sum(1 for x in near if x[3] != x[6])
    resumen["duplicados"]["plantdoc_pares_casi_dup_entre_clases"] = sum(1 for x in near if x[2] != x[5])
    resumen["duplicados"]["plantdoc_pares_casi_dup_con_blueberry"] = [
        (x[0], x[1], x[4]) for x in near if "Blueberry leaf" in (x[2], x[5])]
    resumen["duplicados"]["plantdoc_pares_casi_dup_entre_clases_ej"] = [
        (x[0], x[1], x[4]) for x in near if x[2] != x[5]][:15]
    dup_rel = set()
    for d, ri, ci, si, rj, cj, sj in near:
        dup_rel.add(max(ri, rj))
    for g in grupos:
        for r, _, _ in sorted(g)[1:]:
            dup_rel.add(r)
    for m in manifest:
        m["duplicado_phash"] = "si" if m["ruta"] in dup_rel else "no"

    # ---------------- PlantDoc OD: recortes por caja ----------------
    crops_rows = []
    sin_match = collections.Counter()
    for split, csvname in (("train", "train_labels.csv"), ("test", "test_labels.csv")):
        rows = list(csv.DictReader(open(os.path.join(PD_OD, csvname), encoding="utf-8")))
        idx = collections.Counter()
        for r in rows:
            cls = r["class"]
            if cls not in CROP_CLASSES:
                continue
            fname = r["filename"]
            cands = [c for c in pd_names.get(fname, []) if ("/%s/" % split) in c] or pd_names.get(fname, [])
            if not cands:
                sin_match[cls] += 1
                continue
            src = os.path.join(BASE, cands[0])
            with Image.open(src) as im:
                im = im.convert("RGB")
                W, H = im.size
                cw, chh = int(r["width"]), int(r["height"])
                sx, sy = W / cw, H / chh
                x0, y0 = max(0, int(int(r["xmin"]) * sx)), max(0, int(int(r["ymin"]) * sy))
                x1, y1 = min(W, int(int(r["xmax"]) * sx)), min(H, int(int(r["ymax"]) * sy))
                if x1 - x0 < 2 or y1 - y0 < 2:
                    sin_match[cls + " (caja vacía)"] += 1
                    continue
                crop = im.crop((x0, y0, x1, y1))
            idx[(cls, fname)] += 1
            safe_cls = cls.replace(" ", "_")
            stem = os.path.splitext(os.path.basename(fname))[0][:80].replace(" ", "_")
            # sufijo con hash de la ruta fuente: evita choques de nombre en macOS (insensible a mayúsculas)
            stem += "_" + hashlib.md5(cands[0].encode("utf-8")).hexdigest()[:6]
            outd = os.path.join(PD_CROPS, safe_cls, split)
            os.makedirs(outd, exist_ok=True)
            outp = os.path.join(outd, "%s__box%02d.jpg" % (stem, idx[(cls, fname)]))
            crop.save(outp, quality=92)
            lado = min(crop.size)
            cat, esp = PD_MAP[cls]
            crops_rows.append({
                "fuente": "PlantDoc-OD-recorte", "ruta": os.path.relpath(outp, BASE), "clase_original": cls,
                "categoria_eval": cat, "especie": esp, "dominio": "web (recorte de una hoja, fondo natural)",
                "split_original": split, "grupo": os.path.relpath(src, BASE), "ancho": crop.size[0],
                "alto": crop.size[1], "phash": "", "licencia": LIC_PD, "duplicado_phash": "",
                "apto_lado_min_64": "si" if lado >= MIN_CROP_SIDE else "no",
            })
    cc = collections.Counter((r["clase_original"], r["split_original"], r["apto_lado_min_64"]) for r in crops_rows)
    resumen["plantdoc_crops"] = {"%s|%s|apto=%s" % k: v for k, v in sorted(cc.items())}
    resumen["plantdoc_crops_sin_imagen"] = dict(sin_match)

    # ---------------- PlantVillage ----------------
    leafmap = json.load(open(os.path.join(PV, "leaf_grouping/leaf-map.json"), encoding="utf-8"))
    test = set(l.strip() for l in open(os.path.join(PV_SPLITS, "color_test.txt"), encoding="utf-8"))
    base_pv = os.path.join(PV, "raw/color")
    for cls in sorted(os.listdir(base_pv)):
        cd = os.path.join(base_pv, cls)
        files = sorted(os.listdir(cd))
        leaves = collections.Counter()
        nt = 0
        sizes = collections.Counter()
        for f in files:
            suf = f.split("___", 1)[1].rsplit(".", 1)[0].lower()
            hit = [x for x in leafmap.get(suf, []) if x.startswith(cls + ":::")]
            leaf = hit[0].split(":::")[1] if hit else ""
            if leaf:
                leaves[leaf] += 1
            hf_rel = "raw/color/%s/%s" % (cls, f)
            sp = "test" if hf_rel in test else "train"
            nt += sp == "test"
            p = os.path.join(cd, f)
            with Image.open(p) as im:
                sizes[im.size] += 1
            cat, esp = PV_MAP[cls]
            manifest.append({
                "fuente": "PlantVillage", "ruta": os.path.relpath(p, BASE), "clase_original": cls,
                "categoria_eval": cat, "especie": esp, "dominio": "laboratorio (hoja sola, fondo uniforme)",
                "split_original": "hf_" + sp, "grupo": ("leaf:" + leaf) if leaf else "", "ancho": 256,
                "alto": 256, "phash": "", "licencia": LIC_PV, "duplicado_phash": "",
            })
        per_leaf = sorted(leaves.values())
        resumen["plantvillage"][cls] = {
            "imagenes": len(files),
            "hojas_fisicas_leaf_id": len(leaves),
            "imgs_por_hoja_min_mediana_max": [per_leaf[0], statistics.median(per_leaf), per_leaf[-1]] if per_leaf else None,
            "imagenes_sin_leaf_id": len(files) - sum(leaves.values()),
            "hf_test": nt,
            "hf_train": len(files) - nt,
            "tamanos": {"%dx%d" % k: v for k, v in sizes.items()},
        }

    # ---------------- Triage visual (IA, no agronómico) de PlantDoc Blueberry ----------------
    triage = {}
    tri_csv = os.path.join(OUT, "triage_visual_plantdoc_blueberry.csv")
    if os.path.exists(tri_csv):
        for r in csv.DictReader(open(tri_csv, encoding="utf-8")):
            triage[r["ruta"]] = r["revision_visual"]
    for m in manifest + crops_rows:
        m["revision_visual"] = triage.get(m["ruta"]) or triage.get(m.get("grupo", ""), "")
    tv = collections.Counter((m["fuente"], m["split_original"], m["revision_visual"]) for m in manifest + crops_rows
                             if m["categoria_eval"] == "sana_arandano" and m["fuente"] != "PlantVillage")
    tv_apt = collections.Counter((m["split_original"], m["revision_visual"]) for m in crops_rows
                                 if m["categoria_eval"] == "sana_arandano" and m["apto_lado_min_64"] == "si")
    resumen["plantdoc_blueberry_triage"] = {"|".join(k): v for k, v in sorted(tv.items())}
    resumen["plantdoc_blueberry_crops_aptos_triage"] = {"|".join(k): v for k, v in sorted(tv_apt.items())}

    # ---------------- Salidas ----------------
    cols = ["fuente", "ruta", "clase_original", "categoria_eval", "especie", "dominio", "split_original",
            "grupo", "ancho", "alto", "phash", "duplicado_phash", "apto_lado_min_64", "revision_visual", "licencia"]
    with open(os.path.join(OUT, "manifest_secundarios.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for m in manifest + crops_rows:
            m.setdefault("apto_lado_min_64", "")
            w.writerow(m)
    cat_count = collections.Counter((m["fuente"], m["categoria_eval"]) for m in manifest + crops_rows)
    resumen["conteo_por_categoria_eval"] = {"%s|%s" % k: v for k, v in sorted(cat_count.items())}
    with open(os.path.join(OUT, "resumen_secundarios.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in resumen.items() if k != "plantdoc"}, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    sys.exit(main())
