#!/usr/bin/env python
"""Convierte un dataset de DETECCIÓN YOLO (o uno en carpetas por clase) a un dataset de CLASIFICACIÓN.

Modos (``--mode``):

* ``crops``  (por defecto): un recorte por caja, con margen y tamaño mínimo configurables.
* ``image``: una fila por imagen completa, etiquetada con la clase dominante (más cajas; empate
  por área total y luego alfabético). ``--skip-multiclass`` descarta las imágenes con varias clases.
* ``leaf-crops``: recorta las cajas de HOJA (``--leaf-class``) y les pone la etiqueta de la lesión
  mayoritaria cuyo centro cae dentro (útil con drberry-leaf-detection-2, donde las cajas de
  Alternaria son lesiones diminutas y no hojas).
* ``folders``: dataset ya organizado como ``raiz/<clase>/*.jpg`` o ``raiz/<split>/<clase>/*.jpg``.

Estructuras YOLO aceptadas (se busca cualquier carpeta ``images`` y su gemela ``labels``):
``raiz/{train,valid,test}/{images,labels}`` (Roboflow), ``raiz/{images,labels}/{train,val}``
(Ultralytics) y ``raiz/{images,labels}`` plano. Las líneas de etiqueta pueden ser cajas
(``c cx cy w h``) o polígonos (``c x1 y1 x2 y2 ...``; se usa su caja envolvente).

Cada fila del manifiesto guarda ``source_id`` (imagen de ORIGEN; por defecto el nombre sin el
sufijo ``.rf.<hash>`` de Roboflow, para que las copias aumentadas de la misma foto queden juntas)
y así ``split.py`` puede dividir sin fuga.

Ejemplo (DrBerry original):
    .venv/bin/python -I pipeline/convert.py --input raw/drberry/drberry-original-data-v1-yolov8 \
        --out pipeline/work/drberry/crops --mode crops --margin 0.10 --min-crop-px 96 \
        --dataset-name drberry-original-v1
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from common import (  # noqa: E402
    SPLIT_ALIASES,
    list_images,
    map_class,
    now_iso,
    parse_class_map,
    roboflow_source_id,
    safe_filename,
    write_csv,
    write_json,
)

MANIFEST_COLUMNS = [
    "item_id",
    "path",
    "label",
    "source_id",
    "source_path",
    "source_split",
    "dataset",
    "mode",
    "box_index",
    "orig_class",
    "box_x1",
    "box_y1",
    "box_x2",
    "box_y2",
    "crop_x1",
    "crop_y1",
    "crop_x2",
    "crop_y2",
    "img_w",
    "img_h",
    "n_boxes_image",
    "multiclass_image",
]


@dataclass
class Box:
    cls: int
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def w(self) -> float:
        return self.x2 - self.x1

    @property
    def h(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return max(self.w, 0.0) * max(self.h, 0.0)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


# --------------------------------------------------------------------------- YOLO I/O

def load_yolo_names(root: Path, data_yaml: Path | None = None) -> list[str]:
    """Nombres de clase desde ``data.yaml`` (lista o dict ``{id: nombre}``)."""
    cand = [data_yaml] if data_yaml else [root / "data.yaml", root / "dataset.yaml", *sorted(root.glob("*.yaml"))]
    for p in cand:
        if p and p.is_file() and p.stat().st_size < 1_000_000:
            data = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace")) or {}
            names = data.get("names")
            if isinstance(names, dict):
                return [str(names[k]) for k in sorted(names, key=lambda x: int(x))]
            if isinstance(names, list):
                return [str(n) for n in names]
    raise FileNotFoundError(f"No encontré data.yaml con 'names' en {root}")


def detect_split(parts: Sequence[str]) -> str:
    for part in parts:
        s = SPLIT_ALIASES.get(part.lower())
        if s:
            return s
    return ""


def find_yolo_pairs(root: Path) -> list[tuple[Path, Path, str]]:
    """Lista ``(imagen, etiqueta, split)`` para toda imagen bajo una carpeta ``images``."""
    out = []
    for img in list_images(root):
        rel = img.relative_to(root).parts
        if "images" not in rel:
            continue
        i = len(rel) - 1 - list(reversed(rel)).index("images")
        lab_parts = list(rel[:i]) + ["labels"] + list(rel[i + 1 :])
        lab = (root.joinpath(*lab_parts)).with_suffix(".txt")
        out.append((img, lab, detect_split(rel[:-1])))
    return out


def parse_label_file(path: Path, img_w: int, img_h: int) -> tuple[list[Box], int]:
    """Lee una etiqueta YOLO (cajas o polígonos) y la pasa a píxeles. Devuelve (cajas, líneas_malas)."""
    boxes: list[Box] = []
    bad = 0
    if not path.exists():
        return boxes, 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        tok = line.split()
        if not tok:
            continue
        try:
            cls = int(float(tok[0]))
            vals = [float(v) for v in tok[1:]]
        except ValueError:
            bad += 1
            continue
        if len(vals) == 4:
            cx, cy, w, h = vals
            x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        elif len(vals) >= 6 and len(vals) % 2 == 0:
            xs, ys = vals[0::2], vals[1::2]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        else:
            bad += 1
            continue
        x1, x2 = (min(max(v, 0.0), 1.0) * img_w for v in (x1, x2))
        y1, y2 = (min(max(v, 0.0), 1.0) * img_h for v in (y1, y2))
        if x2 - x1 <= 0 or y2 - y1 <= 0 or cls < 0:
            bad += 1
            continue
        boxes.append(Box(cls, x1, y1, x2, y2))
    return boxes, bad


# --------------------------------------------------------------------------- geometría

def expand_box(
    box: tuple[float, float, float, float],
    img_w: int,
    img_h: int,
    margin: float = 0.1,
    min_crop: int = 0,
    square: bool = False,
) -> tuple[int, int, int, int]:
    """Agranda la caja (margen relativo a su tamaño, cuadrado opcional, lado mínimo) y la mete en la imagen."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    x1, x2 = x1 - margin * w, x2 + margin * w
    y1, y2 = y1 - margin * h, y2 + margin * h

    def _grow(a: float, b: float, size: float) -> tuple[float, float]:
        c = (a + b) / 2.0
        return c - size / 2.0, c + size / 2.0

    if square:
        side = max(x2 - x1, y2 - y1)
        x1, x2 = _grow(x1, x2, side)
        y1, y2 = _grow(y1, y2, side)
    if min_crop and (x2 - x1) < min_crop:
        x1, x2 = _grow(x1, x2, float(min_crop))
    if min_crop and (y2 - y1) < min_crop:
        y1, y2 = _grow(y1, y2, float(min_crop))

    def _fit(a: float, b: float, limit: int) -> tuple[int, int]:
        # Redondea conservando el tamaño y DESPLAZA (no recorta) para quedar dentro de la imagen,
        # así el recorte mantiene su escala aunque la caja esté junto al borde.
        size = int(round(min(b - a, float(limit))))
        lo = int(round(a))
        lo = min(max(lo, 0), limit - size)
        return lo, lo + size

    cx1, cx2 = _fit(x1, x2, img_w)
    cy1, cy2 = _fit(y1, y2, img_h)
    return cx1, cy1, cx2, cy2


def dominant_class(boxes: Sequence[Box], names: Sequence[str]) -> tuple[int, bool]:
    """Clase con más cajas (empate: mayor área total; luego nombre). Devuelve (clase, multiclase)."""
    cnt = Counter(b.cls for b in boxes)
    area: Counter[int] = Counter()
    for b in boxes:
        area[b.cls] += b.area
    best = sorted(cnt, key=lambda c: (-cnt[c], -area[c], names[c] if c < len(names) else str(c)))[0]
    return best, len(cnt) > 1


# --------------------------------------------------------------------------- conversión

def _source_id(path: Path, root: Path, mode: str) -> str:
    if mode == "stem":
        return path.stem
    if mode == "roboflow":
        return roboflow_source_id(path.stem)
    return str(path.relative_to(root).with_suffix(""))


def _open_rgb(path: Path, exif: bool = True) -> Image.Image:
    im = Image.open(path)
    if exif:
        im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def _save_crop(im: Image.Image, dest: Path, max_side: int, quality: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if max_side and max(im.size) > max_side:
        im = im.copy()
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    im.save(dest, format="JPEG", quality=quality)


def convert_yolo(args: argparse.Namespace) -> tuple[list[dict], dict]:
    root = Path(args.input).resolve()
    out = Path(args.out).resolve()
    names = load_yolo_names(root, Path(args.data_yaml) if args.data_yaml else None)
    cmap = parse_class_map(args.class_map)
    labels = [map_class(n, cmap) for n in names]
    include = {map_class(c, cmap) for c in args.include_classes.split(",")} if args.include_classes else None
    leaf_cls = None
    if args.mode == "leaf-crops":
        if not args.leaf_class:
            raise SystemExit("--mode leaf-crops necesita --leaf-class")
        norm = [map_class(n, {}) for n in names]
        key = map_class(args.leaf_class, {})
        if key not in norm:
            raise SystemExit(f"--leaf-class {args.leaf_class!r} no está en {names}")
        leaf_cls = norm.index(key)

    pairs = find_yolo_pairs(root)
    if not pairs:
        raise SystemExit(f"No hay imágenes bajo una carpeta 'images' en {root}")
    rows: list[dict] = []
    stats: Counter[str] = Counter()
    for img_path, lab_path, split in pairs:
        stats["imagenes"] += 1
        if not lab_path.exists():
            stats["imagenes_sin_archivo_label"] += 1
        with Image.open(img_path) as probe:
            im = ImageOps.exif_transpose(probe) if args.exif else probe
            W, H = im.size
        boxes, bad = parse_label_file(lab_path, W, H)
        stats["lineas_label_invalidas"] += bad
        stats["cajas"] += len(boxes)
        n_out = sum(1 for b in boxes if b.cls >= len(names))
        if n_out:
            stats["cajas_clase_fuera_de_rango"] += n_out
            boxes = [b for b in boxes if b.cls < len(names)]
        sid = _source_id(img_path, root, args.source_id_mode)
        stem = img_path.stem
        n_classes_img = len({b.cls for b in boxes if b.cls != leaf_cls})
        base = {
            "source_id": sid,
            "source_path": str(img_path),
            "source_split": split,
            "dataset": args.dataset_name,
            "mode": args.mode,
            "img_w": W,
            "img_h": H,
            "n_boxes_image": len(boxes),
            "multiclass_image": int(n_classes_img > 1),
        }

        if args.mode == "image":
            if not boxes:
                if args.empty_label:
                    lab = map_class(args.empty_label, cmap)
                    rows.append({**base, "item_id": f"{args.dataset_name}/{split}/{stem}", "path": str(img_path), "label": lab, "box_index": -1, "orig_class": ""})
                    stats["imagenes_vacias_etiquetadas"] += 1
                else:
                    stats["imagenes_sin_cajas_omitidas"] += 1
                continue
            c, multi = dominant_class(boxes, names)
            if multi and args.skip_multiclass:
                stats["imagenes_multiclase_omitidas"] += 1
                continue
            lab = labels[c]
            if include is not None and lab not in include:
                stats["omitidas_por_clase"] += 1
                continue
            rows.append({**base, "item_id": f"{args.dataset_name}/{split}/{stem}", "path": str(img_path), "label": lab, "box_index": -1, "orig_class": names[c]})
            continue

        # modos con recortes
        jobs: list[tuple[int, Box, str, str]] = []  # (idx, caja, etiqueta, clase_original)
        if args.mode == "crops":
            for i, b in enumerate(boxes):
                jobs.append((i, b, labels[b.cls], names[b.cls]))
        else:  # leaf-crops
            lesions = [b for b in boxes if b.cls != leaf_cls]
            for i, leaf in enumerate(boxes):
                if leaf.cls != leaf_cls:
                    continue
                inside = [l for l in lesions if leaf.x1 <= l.center[0] <= leaf.x2 and leaf.y1 <= l.center[1] <= leaf.y2]
                if inside:
                    c, multi = dominant_class(inside, names)
                    if multi and args.skip_multiclass:
                        stats["hojas_multiclase_omitidas"] += 1
                        continue
                    jobs.append((i, leaf, labels[c], names[c]))
                elif args.leaf_without_lesion_label:
                    jobs.append((i, leaf, map_class(args.leaf_without_lesion_label, cmap), names[leaf_cls]))
                else:
                    stats["hojas_sin_lesion_omitidas"] += 1
        if not jobs:
            continue
        im_rgb = None
        for i, b, lab, orig in jobs:
            if include is not None and lab not in include:
                stats["omitidas_por_clase"] += 1
                continue
            if min(b.w, b.h) < args.min_box_px:
                stats["cajas_pequenas_omitidas"] += 1
                continue
            x1, y1, x2, y2 = expand_box((b.x1, b.y1, b.x2, b.y2), W, H, args.margin, args.min_crop_px, args.square)
            if x2 - x1 < 2 or y2 - y1 < 2:
                stats["recortes_degenerados"] += 1
                continue
            if im_rgb is None:
                im_rgb = _open_rgb(img_path, args.exif)
            fname = safe_filename(f"{split or 'nosplit'}__{stem}__b{i:03d}") + ".jpg"
            dest = out / "crops" / safe_filename(lab) / fname
            _save_crop(im_rgb.crop((x1, y1, x2, y2)), dest, args.max_side, args.quality)
            rows.append(
                {
                    **base,
                    "item_id": f"{args.dataset_name}/{split}/{stem}/b{i:03d}",
                    "path": str(dest),
                    "label": lab,
                    "box_index": i,
                    "orig_class": orig,
                    "box_x1": round(b.x1, 2),
                    "box_y1": round(b.y1, 2),
                    "box_x2": round(b.x2, 2),
                    "box_y2": round(b.y2, 2),
                    "crop_x1": x1,
                    "crop_y1": y1,
                    "crop_x2": x2,
                    "crop_y2": y2,
                }
            )
            stats["recortes"] += 1
    meta = {"nombres_originales": names, "etiquetas": labels, "estadisticas": dict(stats)}
    return rows, meta


def iter_folder_images(root: Path) -> Iterator[tuple[Path, str, str]]:
    """``(imagen, clase, split)`` para ``raiz/<clase>/`` o ``raiz/<split>/<clase>/``."""
    subdirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    split_dirs = [p for p in subdirs if p.name.lower() in SPLIT_ALIASES]
    layouts = [(d, SPLIT_ALIASES[d.name.lower()]) for d in split_dirs] if split_dirs else [(root, "")]
    for base, split in layouts:
        for cdir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")):
            for img in list_images(cdir):
                yield img, cdir.name, split


def convert_folders(args: argparse.Namespace) -> tuple[list[dict], dict]:
    root = Path(args.input).resolve()
    cmap = parse_class_map(args.class_map)
    include = {map_class(c, cmap) for c in args.include_classes.split(",")} if args.include_classes else None
    rows: list[dict] = []
    stats: Counter[str] = Counter()
    sid_mode = args.source_id_mode if args.source_id_mode != "auto" else "relpath"
    for img, cname, split in iter_folder_images(root):
        lab = map_class(cname, cmap)
        stats["imagenes"] += 1
        if include is not None and lab not in include:
            stats["omitidas_por_clase"] += 1
            continue
        try:
            with Image.open(img) as im:
                W, H = im.size
        except Exception:  # noqa: BLE001
            stats["imagenes_ilegibles"] += 1
            continue
        rel = img.relative_to(root)
        rows.append(
            {
                "item_id": f"{args.dataset_name}/{rel.with_suffix('').as_posix()}",
                "path": str(img),
                "label": lab,
                "source_id": _source_id(img, root, sid_mode),
                "source_path": str(img),
                "source_split": split,
                "dataset": args.dataset_name,
                "mode": "folders",
                "box_index": -1,
                "orig_class": cname,
                "img_w": W,
                "img_h": H,
                "n_boxes_image": 0,
                "multiclass_image": 0,
            }
        )
    return rows, {"estadisticas": dict(stats)}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="Raíz del dataset YOLO (con data.yaml) o de carpetas por clase")
    ap.add_argument("--out", required=True, help="Carpeta de salida (manifest.csv, crops/, convert_summary.json)")
    ap.add_argument("--mode", choices=["crops", "image", "leaf-crops", "folders"], default="crops")
    ap.add_argument("--dataset-name", default="dataset", help="Nombre corto que se guarda en cada fila")
    ap.add_argument("--data-yaml", default=None, help="Ruta explícita a data.yaml (por defecto se busca en --input)")
    ap.add_argument("--class-map", default=None, help='Renombrar clases: "Oidio=oidio,Sana=sana" o ruta a JSON')
    ap.add_argument("--include-classes", default=None, help="Lista separada por comas de etiquetas (ya mapeadas) a conservar")
    ap.add_argument("--margin", type=float, default=0.10, help="Margen relativo al tamaño de la caja por lado (0.10 = 10%%)")
    ap.add_argument("--min-crop-px", type=int, default=0, help="Lado mínimo del recorte; cajas menores se agrandan alrededor del centro (contexto)")
    ap.add_argument("--min-box-px", type=float, default=4.0, help="Descarta cajas cuyo lado menor (sin margen) sea < este valor en px")
    ap.add_argument("--square", action="store_true", help="Recortes cuadrados (evita deformar al redimensionar)")
    ap.add_argument("--max-side", type=int, default=0, help="Si >0, reduce los recortes a este lado máximo")
    ap.add_argument("--quality", type=int, default=95, help="Calidad JPEG de los recortes")
    ap.add_argument("--source-id-mode", choices=["auto", "roboflow", "stem", "relpath"], default="auto",
                    help="Cómo identificar la imagen de origen (auto: roboflow en YOLO, relpath en carpetas)")
    ap.add_argument("--skip-multiclass", action="store_true", help="(image/leaf-crops) descarta imágenes u hojas con varias clases")
    ap.add_argument("--empty-label", default=None, help="(image) etiqueta para imágenes sin cajas; por defecto se omiten")
    ap.add_argument("--leaf-class", default=None, help="(leaf-crops) nombre de la clase de hoja en data.yaml")
    ap.add_argument("--leaf-without-lesion-label", default=None, help="(leaf-crops) etiqueta para hojas sin lesión; por defecto se omiten")
    ap.add_argument("--no-exif", dest="exif", action="store_false", help="No aplicar la orientación EXIF")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.source_id_mode == "auto" and args.mode != "folders":
        args.source_id_mode = "roboflow"
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows, meta = convert_folders(args) if args.mode == "folders" else convert_yolo(args)
    df = pd.DataFrame(rows)
    for c in MANIFEST_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[MANIFEST_COLUMNS].sort_values("item_id", kind="stable").reset_index(drop=True)
    write_csv(df, out / "manifest.csv")
    counts = df["label"].value_counts().sort_index().to_dict() if len(df) else {}
    by_split = df.groupby(["source_split", "label"]).size().unstack(fill_value=0).to_dict(orient="index") if len(df) else {}
    summary = {
        "creado": now_iso(),
        "entrada": str(Path(args.input).resolve()),
        "modo": args.mode,
        "parametros": {k: v for k, v in vars(args).items() if k not in ("input", "out")},
        "n_items": int(len(df)),
        "n_imagenes_origen": int(df["source_id"].nunique()) if len(df) else 0,
        "items_por_clase": counts,
        "items_por_split_original_y_clase": by_split,
        **meta,
    }
    write_json(out / "convert_summary.json", summary)
    print(f"[convert] {len(df)} ítems, {summary['n_imagenes_origen']} imágenes de origen -> {out / 'manifest.csv'}")
    print(f"[convert] por clase: {counts}")
    print(f"[convert] estadísticas: {meta.get('estadisticas')}")
    return 0 if len(df) else 1


if __name__ == "__main__":
    raise SystemExit(main())
