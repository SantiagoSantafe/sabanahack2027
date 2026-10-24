"""División agrupada: sin fuga, reproducible, estratificada y con test congelado."""
from __future__ import annotations

import json
import os
import stat

import numpy as np
import pandas as pd
import pytest

import split


def _groups_csv(tmp_path, manifest, merge_every: int = 5):
    """Fusiona cada `merge_every` fuentes consecutivas en un grupo (simula ráfagas/duplicados)."""
    m = pd.read_csv(manifest, dtype=str)
    sids = sorted(m["source_id"].unique())
    g = pd.DataFrame({"source_id": sids, "group": [f"g{i // merge_every:04d}" for i in range(len(sids))]})
    p = tmp_path / "groups.csv"
    g.to_csv(p, index=False)
    return p


def _load(out):
    return {s: pd.read_csv(out / f"{s}.csv", dtype=str, keep_default_na=False) for s in ("train", "val", "test")}


def test_no_leakage_between_splits(tmp_path, synthetic_manifest):
    man = synthetic_manifest(n_sources=300, crops_per_source=4)
    gcsv = _groups_csv(tmp_path, man, merge_every=3)
    out = tmp_path / "sp"
    assert split.main(["--manifest", str(man), "--groups", str(gcsv), "--out", str(out), "--seed", "7", "--trials", "50"]) == 0
    parts = _load(out)
    allrows = pd.concat(parts.values())
    original = pd.read_csv(man, dtype=str)
    assert len(allrows) == len(original) and allrows["item_id"].is_unique
    assert set(allrows["item_id"]) == set(original["item_id"])
    for key in ("group", "source_id"):
        sets = [set(parts[s][key]) for s in parts]
        assert not (sets[0] & sets[1]) and not (sets[0] & sets[2]) and not (sets[1] & sets[2]), f"fuga por {key}"
    summary = json.loads((out / "split_summary.json").read_text())
    assert summary["fuga_grupos_entre_splits"] == 0 and summary["fuga_fuentes_entre_splits"] == 0


def test_ratios_and_stratification(tmp_path, synthetic_manifest):
    man = synthetic_manifest(n_sources=400, crops_per_source=3)
    out = tmp_path / "sp"
    split.main(["--manifest", str(man), "--out", str(out), "--seed", "3", "--trials", "100"])
    parts = _load(out)
    n = sum(len(p) for p in parts.values())
    for s, target in zip(("train", "val", "test"), (0.70, 0.15, 0.15)):
        assert abs(len(parts[s]) / n - target) < 0.03
    allrows = pd.concat([p.assign(sp=s) for s, p in parts.items()])
    tab = allrows.groupby(["label", "sp"]).size().unstack(fill_value=0)
    frac = tab.div(tab.sum(axis=1), axis=0)
    assert (tab > 0).all().all(), "cada clase debe estar en los tres splits"
    assert (abs(frac["train"] - 0.70) < 0.06).all()


def test_seed_reproducibility(tmp_path, synthetic_manifest):
    man = synthetic_manifest(n_sources=150)
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    for d, seed in ((a, 11), (b, 11), (c, 12)):
        split.main(["--manifest", str(man), "--out", str(d), "--seed", str(seed), "--trials", "30"])
    for s in ("train", "val", "test"):
        assert (a / f"{s}.csv").read_bytes() == (b / f"{s}.csv").read_bytes()
    fa = json.loads((a / "test_frozen.json").read_text())
    fb = json.loads((b / "test_frozen.json").read_text())
    fc = json.loads((c / "test_frozen.json").read_text())
    assert fa["sha256"] == fb["sha256"] and fa["sha256_contenido"] == fb["sha256_contenido"]
    assert fa["sha256_contenido"] != fc["sha256_contenido"]


def test_frozen_test_verify_and_protection(tmp_path, synthetic_manifest):
    man = synthetic_manifest(n_sources=120)
    out = tmp_path / "sp"
    assert split.main(["--manifest", str(man), "--out", str(out), "--seed", "1", "--trials", "20"]) == 0
    test_csv = out / "test.csv"
    assert not (test_csv.stat().st_mode & stat.S_IWUSR), "test.csv debe quedar en solo lectura"
    assert split.main(["--verify", str(out)]) == 0
    # re-ejecutar con la MISMA semilla es idempotente
    assert split.main(["--manifest", str(man), "--out", str(out), "--seed", "1", "--trials", "20"]) == 0
    # otra semilla cambiaría el test: se niega sin --force
    assert split.main(["--manifest", str(man), "--out", str(out), "--seed", "2", "--trials", "20"]) == 2
    assert split.main(["--verify", str(out)]) == 0
    # manipular el test congelado se detecta
    os.chmod(test_csv, stat.S_IRUSR | stat.S_IWUSR)
    with open(test_csv, "a", encoding="utf-8") as f:
        f.write("x,y\n")
    assert split.main(["--verify", str(out)]) == 1
    # con --force se re-congela
    assert split.main(["--manifest", str(man), "--out", str(out), "--seed", "2", "--trials", "20", "--force"]) == 0
    assert split.main(["--verify", str(out)]) == 0


def test_materialize_layout(tmp_path, synthetic_manifest):
    man = synthetic_manifest(n_sources=40, crops_per_source=2, with_files=True)
    out, mat = tmp_path / "sp", tmp_path / "yolo_cls"
    split.main(["--manifest", str(man), "--out", str(out), "--seed", "5", "--trials", "10", "--materialize", str(mat)])
    parts = _load(out)
    for s, df in parts.items():
        files = list((mat / s).rglob("*.jpg"))
        assert len(files) == len(df)
        assert {f.parent.name for f in files} == set(df["label"])
    # re-materializar sobre la carpeta propia funciona; sobre una ajena, no
    split.main(["--manifest", str(man), "--out", str(tmp_path / "sp2"), "--seed", "5", "--trials", "10", "--materialize", str(mat)])
    foreign = tmp_path / "ajena"
    foreign.mkdir()
    (foreign / "dato.txt").write_text("no borrar")
    with pytest.raises(SystemExit):
        split.main(["--manifest", str(man), "--out", str(tmp_path / "sp3"), "--seed", "5", "--trials", "10", "--materialize", str(foreign)])
    assert (foreign / "dato.txt").exists()


def test_assign_groups_unit():
    df = pd.DataFrame({"item_id": [f"i{k}" for k in range(60)], "label": ["a"] * 30 + ["b"] * 30, "group": [f"g{k // 2}" for k in range(60)]})
    assign, score = split.assign_groups(df, (0.7, 0.15, 0.15), seed=0, trials=20)
    assert set(assign) == set(df["group"])
    counts = pd.Series(list(assign.values())).value_counts()
    assert counts["train"] > counts["val"] and counts["train"] > counts["test"]
    assert np.isfinite(score)


def test_assign_from_reuses_source_split(tmp_path, synthetic_manifest):
    """--assign-from: un segundo manifiesto (p. ej. modo imagen) hereda el split por source_id."""
    man = synthetic_manifest(n_sources=120, crops_per_source=3)
    out1 = tmp_path / "sp1"
    assert split.main(["--manifest", str(man), "--out", str(out1), "--seed", "5", "--trials", "20"]) == 0
    m = pd.read_csv(man, dtype=str, keep_default_na=False)
    img = m.drop_duplicates("source_id").copy()
    img["item_id"] = img["source_id"] + "/img"
    man2 = tmp_path / "img_manifest.csv"
    img.to_csv(man2, index=False)
    out2 = tmp_path / "sp2"
    assert split.main(["--manifest", str(man2), "--out", str(out2), "--assign-from", str(out1)]) == 0
    p1 = pd.concat([pd.read_csv(out1 / f"{s}.csv", dtype=str) for s in ("train", "val", "test")])
    p2 = pd.concat([pd.read_csv(out2 / f"{s}.csv", dtype=str) for s in ("train", "val", "test")])
    s1 = p1.drop_duplicates("source_id").set_index("source_id")["split"]
    s2 = p2.set_index("source_id")["split"]
    assert (s2 == s1.reindex(s2.index)).all()
    # una fuente desconocida debe fallar
    extra = pd.concat([img, img.iloc[[0]].assign(source_id="desconocida", item_id="desconocida/img")])
    man3 = tmp_path / "img_manifest3.csv"
    extra.to_csv(man3, index=False)
    with pytest.raises(SystemExit):
        split.main(["--manifest", str(man3), "--out", str(tmp_path / "sp3"), "--assign-from", str(out1)])
