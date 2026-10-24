"""Conversión YOLO -> clasificación (recortes, imagen completa, hojas por lesión, carpetas)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

import convert
from conftest import draw_boxes, pattern_image


def _run(args: list[str]) -> pd.DataFrame:
    assert convert.main(args) == 0
    out = Path(args[args.index("--out") + 1])
    return pd.read_csv(out / "manifest.csv", keep_default_na=False, dtype={"source_id": str})


def test_crops_roboflow_layout(make_yolo_dataset, tmp_path):
    root, info = make_yolo_dataset("roboflow", n_per_split=4, rf_copies=2)
    out = tmp_path / "out"
    df = _run(["--input", str(root), "--out", str(out), "--margin", "0.1", "--dataset-name", "syn"])
    n_boxes = sum(len(i["boxes"]) for i in info)
    assert len(df) == n_boxes
    # clases normalizadas (minúsculas, sin tildes)
    assert set(df["label"]) <= {"alternaria", "heliothis", "oidio", "sana"}
    # el id de origen quita el sufijo .rf.<hash>: las 2 copias comparten source_id
    assert df["source_id"].nunique() == len({i["source_id"] for i in info})
    assert all(".rf." not in s for s in df["source_id"])
    assert set(df["source_split"]) == {"train", "val", "test"}
    # cada recorte existe y su tamaño coincide con las coordenadas guardadas
    for _, r in df.head(10).iterrows():
        with Image.open(r["path"]) as im:
            assert im.size == (r["crop_x2"] - r["crop_x1"], r["crop_y2"] - r["crop_y1"])
        assert Path(r["path"]).parent.name == r["label"]
    summary = (out / "convert_summary.json").read_text()
    assert "recortes" in summary


def test_crop_coordinates_with_margin(make_yolo_dataset, tmp_path):
    root, info = make_yolo_dataset("roboflow", n_per_split=1)
    df = _run(["--input", str(root), "--out", str(tmp_path / "o"), "--margin", "0.5"])
    first = info[0]
    c, x1, y1, x2, y2 = first["boxes"][0]
    row = df[(df["source_id"] == first["source_id"]) & (df["box_index"] == 0)].iloc[0]
    w, h = x2 - x1, y2 - y1
    exp = convert.expand_box((x1, y1, x2, y2), first["W"], first["H"], margin=0.5)
    got = (row["crop_x1"], row["crop_y1"], row["crop_x2"], row["crop_y2"])
    assert all(abs(int(a) - b) <= 1 for a, b in zip(got, exp))  # tolerancia de redondeo de la etiqueta YOLO
    # caja (20,30)-(120,140) en 256x192 con margen 50 %: x -> 200 px desplazado al borde; y -> 220 px > 192, se limita
    assert (x1, y1, x2, y2) == (20, 30, 120, 140) and (w, h) == (100, 110)
    assert exp == (0, 0, 200, 192)
    assert row["label"] == convert.map_class(convert.load_yolo_names(root)[c], {})


def test_expand_box_rules():
    # margen 50 %: caja 20x10 -> 40x20
    assert convert.expand_box((100, 100, 120, 110), 1000, 1000, margin=0.5) == (90, 95, 130, 115)
    # tamaño mínimo: se agranda alrededor del centro
    x1, y1, x2, y2 = convert.expand_box((100, 100, 120, 110), 1000, 1000, margin=0.0, min_crop=64)
    assert (x2 - x1, y2 - y1) == (64, 64)
    assert (x1 + x2) / 2 == 110 and (y1 + y2) / 2 == 105
    # junto al borde: se desplaza para quedar dentro de la imagen sin perder tamaño
    assert convert.expand_box((0, 0, 10, 10), 200, 200, margin=0.0, min_crop=64) == (0, 0, 64, 64)
    assert convert.expand_box((190, 190, 200, 200), 200, 200, margin=0.0, min_crop=64) == (136, 136, 200, 200)
    # más grande que la imagen: se recorta a la imagen
    assert convert.expand_box((10, 10, 90, 90), 100, 100, margin=1.0) == (0, 0, 100, 100)
    # cuadrado
    x1, y1, x2, y2 = convert.expand_box((0, 40, 100, 60), 200, 200, margin=0.0, square=True)
    assert x2 - x1 == y2 - y1 == 100


def test_polygon_and_invalid_lines(tmp_path):
    lab = tmp_path / "l.txt"
    lab.write_text("0 0.1 0.1 0.3 0.1 0.3 0.4 0.1 0.4\n1 0.5 0.5\nx y z w h\n2 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    boxes, bad = convert.parse_label_file(lab, 100, 200)
    assert bad == 2
    assert len(boxes) == 2
    b = boxes[0]
    assert b.cls == 0
    assert (round(b.x1), round(b.y1), round(b.x2), round(b.y2)) == (10, 20, 30, 80)


def test_min_box_filter_and_min_crop(make_yolo_dataset, tmp_path):
    W, H = 256, 192
    extra = {"IMG_0000_jpg": [(0, 50, 50, 52, 52), (2, 10, 10, 110, 110)]}  # una caja de 2 px y una normal
    root, _ = make_yolo_dataset("roboflow", n_per_split=1, extra_boxes=extra)
    df = _run(["--input", str(root), "--out", str(tmp_path / "o"), "--min-box-px", "4"])
    sub = df[df["source_id"] == "IMG_0000_jpg"]
    assert len(sub) == 1 and sub.iloc[0]["label"] == "oidio"
    df2 = _run(["--input", str(root), "--out", str(tmp_path / "o2"), "--min-box-px", "1", "--min-crop-px", "64"])
    tiny = df2[(df2["source_id"] == "IMG_0000_jpg") & (df2["label"] == "alternaria")].iloc[0]
    assert tiny["crop_x2"] - tiny["crop_x1"] == 64 and tiny["crop_y2"] - tiny["crop_y1"] == 64


def test_ultralytics_and_flat_layouts(make_yolo_dataset, tmp_path):
    root, info = make_yolo_dataset("ultralytics", n_per_split=2)
    df = _run(["--input", str(root), "--out", str(tmp_path / "u")])
    assert set(df["source_split"]) == {"train", "val", "test"}
    assert len(df) == sum(len(i["boxes"]) for i in info)
    root2, info2 = make_yolo_dataset("flat", n_per_split=2)
    df2 = _run(["--input", str(root2), "--out", str(tmp_path / "f")])
    assert len(df2) == sum(len(i["boxes"]) for i in info2)
    assert set(df2["source_split"]) == {""}


def test_image_mode_dominant_class(make_yolo_dataset, tmp_path):
    extra = {"IMG_0000_jpg": [(1, 10, 10, 40, 40), (1, 50, 50, 80, 80), (3, 100, 20, 250, 180)]}
    root, info = make_yolo_dataset("roboflow", n_per_split=2, extra_boxes=extra)
    df = _run(["--input", str(root), "--out", str(tmp_path / "i"), "--mode", "image"])
    assert len(df) == len(info)
    row = df[df["source_id"] == "IMG_0000_jpg"].iloc[0]
    assert row["label"] == "heliothis"  # 2 cajas de Heliothis ganan a 1 de Sana aunque sea más grande
    assert row["multiclass_image"] == 1
    assert Path(row["path"]).exists()
    df2 = _run(["--input", str(root), "--out", str(tmp_path / "i2"), "--mode", "image", "--skip-multiclass"])
    assert "IMG_0000_jpg" not in set(df2["source_id"])


def test_leaf_crops_mode(tmp_path):
    root = tmp_path / "leafds"
    (root / "train" / "images").mkdir(parents=True)
    (root / "train" / "labels").mkdir(parents=True)
    (root / "data.yaml").write_text("names: ['Dano por Alternaria', 'Dano por Oidio', 'Hoja de arandano']\n", encoding="utf-8")
    W, H = 300, 200
    boxes = [(2, 10, 10, 140, 190), (0, 50, 50, 56, 56), (0, 80, 90, 86, 96), (1, 100, 150, 110, 160),  # hoja 1: 2 alternaria + 1 oidio
             (2, 160, 10, 290, 190)]  # hoja 2 sin lesión
    draw_boxes(pattern_image(5, (W, H)), boxes).save(root / "train" / "images" / "a.jpg")
    from conftest import yolo_line

    (root / "train" / "labels" / "a.txt").write_text("\n".join(yolo_line(*b, W, H) for b in boxes), encoding="utf-8")
    cmap = "Dano por Alternaria=alternaria,Dano por Oidio=oidio,Hoja de arandano=hoja"
    df = _run(["--input", str(root), "--out", str(tmp_path / "lo"), "--mode", "leaf-crops", "--leaf-class", "Hoja de arandano", "--class-map", cmap])
    assert len(df) == 1 and df.iloc[0]["label"] == "alternaria"
    df2 = _run(["--input", str(root), "--out", str(tmp_path / "lo2"), "--mode", "leaf-crops", "--leaf-class", "Hoja de arandano",
                "--class-map", cmap, "--leaf-without-lesion-label", "sana"])
    assert sorted(df2["label"]) == ["alternaria", "sana"]


def test_folders_mode(tmp_path):
    root = tmp_path / "folders"
    n = 0
    for split in ("train", "val"):
        for cls in ("Sana", "Oídio"):
            d = root / split / cls
            d.mkdir(parents=True)
            for k in range(3):
                pattern_image(n, (40, 40)).save(d / f"img{k}.png")
                n += 1
    df = _run(["--input", str(root), "--out", str(tmp_path / "fo"), "--mode", "folders", "--dataset-name", "fx"])
    assert len(df) == 12
    assert set(df["label"]) == {"sana", "oidio"}
    assert set(df["source_split"]) == {"train", "val"}
    assert df["source_id"].is_unique  # relpath: no fusiona img0 de clases distintas


def test_missing_yaml_raises(tmp_path):
    (tmp_path / "x" / "images").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        convert.load_yolo_names(tmp_path / "x")
