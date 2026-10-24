"""Fixtures con imágenes SINTÉTICAS generadas al vuelo (no se usa ningún dato real)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import pytest
from PIL import Image, ImageDraw

PIPE = Path(__file__).resolve().parents[1]
if str(PIPE) not in sys.path:
    sys.path.insert(0, str(PIPE))

NAMES = ["Alternaria", "Heliothis", "Oidio", "Sana"]
COLORS = {0: (150, 70, 30), 1: (40, 40, 200), 2: (235, 235, 235), 3: (40, 170, 40)}

RUN_SLOW = os.environ.get("RUN_SLOW") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="prueba lenta: exporta RUN_SLOW=1 para correrla")


def pattern_image(seed: int, size: tuple[int, int] = (256, 256)) -> Image.Image:
    """Patrón de baja frecuencia único por semilla (da phash distintos entre semillas)."""
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 256, size=(6, 6, 3), dtype=np.uint8)
    return Image.fromarray(small).resize(size, Image.Resampling.BICUBIC)


def near_copy(im: Image.Image, seed: int, noise: float = 4.0) -> Image.Image:
    rng = np.random.default_rng(seed)
    a = np.asarray(im, dtype=float) + rng.normal(0, noise, size=np.asarray(im).shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def draw_boxes(im: Image.Image, boxes: Sequence[tuple[int, float, float, float, float]]) -> Image.Image:
    im = im.copy()
    d = ImageDraw.Draw(im)
    for c, x1, y1, x2, y2 in boxes:
        d.rectangle([x1, y1, x2, y2], fill=COLORS[c % 4])
    return im


def yolo_line(c: int, x1: float, y1: float, x2: float, y2: float, W: int, H: int) -> str:
    return f"{c} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}"


@pytest.fixture
def make_yolo_dataset(tmp_path: Path) -> Callable[..., tuple[Path, list[dict]]]:
    """Crea un dataset YOLO sintético. Devuelve (raíz, lista de imágenes con sus cajas)."""

    def _make(layout: str = "roboflow", n_per_split: int = 4, names: Sequence[str] = NAMES, W: int = 256, H: int = 192,
              rf_copies: int = 1, extra_boxes: dict[str, list] | None = None) -> tuple[Path, list[dict]]:
        root = tmp_path / f"yolo_{layout}"
        (root).mkdir(parents=True, exist_ok=True)
        (root / "data.yaml").write_text(
            "train: ../train/images\nval: ../valid/images\ntest: ../test/images\n"
            f"nc: {len(names)}\nnames: {list(names)!r}\n", encoding="utf-8")
        info = []
        k = 0
        for split in ("train", "valid", "test"):
            for i in range(n_per_split):
                c = k % len(names)
                boxes = [(c, 20 + 3 * i, 30, 120 + 3 * i, 140)]
                if i % 2 == 1:
                    boxes.append(((c + 1) % len(names), 150, 20, 230, 90))
                stem_base = f"IMG_{k:04d}_jpg"
                if extra_boxes and stem_base in extra_boxes:
                    boxes = extra_boxes[stem_base]
                im = draw_boxes(pattern_image(k, (W, H)), boxes)
                for r in range(rf_copies):
                    stem = f"{stem_base}.rf.{(k * 1000 + r):032x}"
                    if layout == "roboflow":
                        img_dir, lab_dir = root / split / "images", root / split / "labels"
                    elif layout == "ultralytics":
                        s = "val" if split == "valid" else split
                        img_dir, lab_dir = root / "images" / s, root / "labels" / s
                    else:  # flat
                        img_dir, lab_dir = root / "images", root / "labels"
                    img_dir.mkdir(parents=True, exist_ok=True)
                    lab_dir.mkdir(parents=True, exist_ok=True)
                    im.save(img_dir / f"{stem}.jpg", quality=95)
                    (lab_dir / f"{stem}.txt").write_text("\n".join(yolo_line(*b, W, H) for b in boxes) + "\n", encoding="utf-8")
                    info.append({"stem": stem, "source_id": stem_base, "split": split, "boxes": boxes, "W": W, "H": H})
                k += 1
        return root, info

    return _make


@pytest.fixture
def synthetic_manifest(tmp_path: Path) -> Callable[..., Path]:
    """Manifiesto sintético (sin imágenes) con varias fuentes, varios recortes por fuente y 4 clases."""

    def _make(n_sources: int = 300, crops_per_source: int = 3, classes: Sequence[str] = ("alternaria", "heliothis", "oidio", "sana"),
              seed: int = 1, with_files: bool = False) -> Path:
        import pandas as pd

        rng = np.random.default_rng(seed)
        rows = []
        img_dir = tmp_path / "imgs"
        for s in range(n_sources):
            c = classes[int(rng.integers(0, len(classes)))]
            for j in range(int(rng.integers(1, crops_per_source + 1))):
                lab = c if rng.random() > 0.1 else classes[int(rng.integers(0, len(classes)))]
                p = img_dir / f"s{s:04d}_{j}.jpg"
                if with_files:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    pattern_image(s * 10 + j, (32, 32)).save(p)
                rows.append({"item_id": f"syn/train/s{s:04d}/b{j:03d}", "path": str(p), "label": lab, "source_id": f"s{s:04d}", "source_path": str(p)})
        out = tmp_path / f"manifest_{seed}.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        return out

    return _make
