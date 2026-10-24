"""Hash perceptual y agrupación de casi-duplicados."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import dedup
from conftest import near_copy, pattern_image


def _manifest(tmp_path, images: dict[str, object]) -> str:
    rows = []
    d = tmp_path / "src"
    d.mkdir()
    for sid, im in images.items():
        p = d / f"{sid}.jpg"
        im.save(p, quality=90)
        rows.append({"item_id": f"x/{sid}/b000", "path": str(p), "label": "sana" if sid.startswith("s") else "oidio", "source_id": sid, "source_path": str(p)})
    m = tmp_path / "manifest.csv"
    pd.DataFrame(rows).to_csv(m, index=False)
    return str(m)


def test_hamming_pairs_exact():
    bits = np.zeros((3, 64), dtype=bool)
    bits[1, :5] = True  # distancia 5 a la fila 0
    bits[2, :] = True  # distancia 64 a la 0 y 59 a la 1
    pairs = dedup.near_duplicate_pairs(bits, threshold=5)
    assert pairs == [(0, 1, 5)]
    assert dedup.near_duplicate_pairs(bits, threshold=4) == []
    assert (1, 2, 59) in dedup.near_duplicate_pairs(bits, threshold=64)


def test_near_duplicates_grouped(tmp_path):
    base = pattern_image(1)
    imgs = {"a_orig": base, "a_copy": near_copy(base, 7), "a_resized": base.resize((200, 200)).resize((256, 256)),
            "b": pattern_image(2), "c": pattern_image(3), "s_d": pattern_image(4)}
    m = _manifest(tmp_path, imgs)
    out = tmp_path / "dd"
    assert dedup.main(["--manifest", m, "--out", str(out), "--threshold", "6", "--pairs-png"]) == 0
    g = pd.read_csv(out / "groups.csv", dtype=str).set_index("source_id")["group"]
    assert g["a_orig"] == g["a_copy"] == g["a_resized"]
    assert len({g["a_orig"], g["b"], g["c"], g["s_d"]}) == 4
    rep = json.loads((out / "duplicates_report.json").read_text())
    assert rep["n_imagenes_origen"] == 6 and rep["n_grupos"] == 4
    assert (out / "duplicate_pairs.png").exists()


def test_extra_groups_are_merged(tmp_path):
    imgs = {"r1": pattern_image(10), "r2": pattern_image(11), "r3": pattern_image(12)}
    m = _manifest(tmp_path, imgs)
    ext = tmp_path / "rafagas.csv"
    pd.DataFrame({"nombre_original": ["r1", "r2", "r3"], "grupo_rafaga": ["g1", "g1", "g2"]}).to_csv(ext, index=False)
    out = tmp_path / "dd"
    dedup.main(["--manifest", m, "--out", str(out), "--threshold", "0", "--extra-groups-csv", str(ext), "--extra-key", "nombre_original", "--extra-group", "grupo_rafaga"])
    g = pd.read_csv(out / "groups.csv", dtype=str).set_index("source_id")["group"]
    assert g["r1"] == g["r2"] != g["r3"]
    rep = json.loads((out / "duplicates_report.json").read_text())
    assert rep["n_uniones_por_grupos_externos"] == 1


def test_group_names_deterministic():
    bits = np.zeros((4, 64), dtype=bool)
    bits[2:, 10:40] = True
    g1, _, _ = dedup.group_sources(["d", "c", "b", "a"], bits, 2)
    g2, _, _ = dedup.group_sources(["d", "c", "b", "a"], bits, 2)
    assert g1 == g2
    assert g1[2] == g1[3] and g1[0] == g1[1]  # filas 0-1 iguales entre sí; 2-3 iguales entre sí
    assert g1[3] == "g00001"  # el grupo con el menor source_id ('a') se llama g00001
