"""ood_eval.py con casos conocidos y predict_manifest.py con un cabezal CLIP falso (sin pesos reales)."""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
import pytest

import ood_eval
from conftest import pattern_image

CLASSES = ["alternaria", "heliothis", "oidio", "sana"]


def _ood_csv(tmp_path):
    # p_sana fija -> puntaje = 1 - p_sana. Umbral 0.5.
    rows = []
    # 4 sanas de campo: 1 alarma (p_sana=0.3) -> tasa FP 1/4
    for i, ps in enumerate([0.9, 0.8, 0.3, 0.7]):
        rows.append(("campo_sana", f"o{i}", [0.05, 0.05, 1 - ps - 0.1, ps]))
    # 5 oídio: 4 alarmas, de las cuales 3 decididas como oidio
    for i, (ps, top) in enumerate([(0.1, 2), (0.2, 2), (0.05, 2), (0.3, 0), (0.6, 2)]):
        p = [0.0, 0.0, 0.0, ps]
        p[top] = 1 - ps
        rows.append(("campo_oidio", f"q{i // 2}", p))
    df = pd.DataFrame([{"path": f"/x/{k}.jpg", "y_true": c, "y_pred": CLASSES[int(np.argmax(p))], "group": g, **{f"p_{n}": v for n, v in zip(CLASSES, p)}}
                       for k, (c, g, p) in enumerate(rows)])
    path = tmp_path / "pred.csv"
    df.to_csv(path, index=False)
    spec = {"campo_sana": {"esperado": "sana"}, "campo_oidio": {"esperado": "enfermedad", "clase_modelo": "oidio", "referencia": "campo_sana"}}
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(spec))
    return path, sp


def test_ood_eval_known(tmp_path):
    pred, spec = _ood_csv(tmp_path)
    out = tmp_path / "ev"
    assert ood_eval.main(["--pred", str(pred), "--threshold", "0.5", "--spec", str(spec), "--out", str(out), "--n-boot", "200"]) == 0
    m = json.loads((out / "ood_metrics.json").read_text())["categorias"]
    assert m["campo_sana"]["alarma"]["k"] == 1 and m["campo_sana"]["alarma"]["n"] == 4
    assert m["campo_sana"]["metrica"] == "tasa_falsas_alarmas"
    assert m["campo_oidio"]["alarma"]["k"] == 4
    assert m["campo_oidio"]["recall_clase"]["k"] == 3
    lo, hi = m["campo_oidio"]["alarma"]["ic95_clopper_pearson"]
    assert lo < 0.8 < hi
    assert 0.0 <= m["campo_oidio"]["separabilidad_vs_referencia"]["auc"] <= 1.0
    assert (out / "ood_tabla.csv").exists()


def test_predict_manifest_with_fake_clip_head(tmp_path, monkeypatch):
    """Ruta CLIP de predict_manifest con un embedder falso: verifica formato, metadatos y omitidas."""
    import clip_baseline
    import predict_manifest

    class FakeEmbedder:
        def __init__(self, *a, **k):
            self.tag = "fake/fake"
            self.device = "cpu"

        def embed_paths(self, paths, batch=32, progress=True, tiles=0):
            return np.stack([np.r_[np.ones(1) * (i % 2), np.zeros(3)] + 0.01 for i, _ in enumerate(paths)]).astype(np.float32)

    monkeypatch.setattr(clip_baseline, "ClipEmbedder", FakeEmbedder)
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    rows = []
    for i in range(6):
        p = img_dir / f"{i}.jpg"
        pattern_image(i, (40, 40)).save(p)
        rows.append({"path": f"imgs/{i}.jpg", "label": "campo_sana" if i % 2 else "campo_oidio", "group": f"g{i // 2}", "fuente": "x"})
    (img_dir / "roto.jpg").write_bytes(b"no es una imagen")
    rows.append({"path": "imgs/roto.jpg", "label": "campo_sana", "group": "g9", "fuente": "x"})
    man = tmp_path / "man.csv"
    pd.DataFrame(rows).to_csv(man, index=False)
    head = {"tipo": "clip_zeroshot", "clip_model": "fake", "pretrained": "fake", "classes": CLASSES,
            "text_mat": np.eye(4, dtype=np.float32), "logit_scale": 10.0}
    hp = tmp_path / "clip_zeroshot.joblib"
    joblib.dump(head, hp)
    out = tmp_path / "pred"
    assert predict_manifest.main(["--manifest", str(man), "--weights", str(hp), "--names", "zs", "--out", str(out), "--keep-cols", "fuente"]) == 0
    df = pd.read_csv(out / "predicciones_zs.csv")
    assert len(df) == 6 and {"p_sana", "p_oidio", "group", "fuente"} <= set(df.columns)
    assert np.allclose(df[[f"p_{c}" for c in CLASSES]].sum(axis=1), 1.0, atol=1e-4)
    assert pd.read_csv(out / "omitidas.csv")["path"].str.endswith("roto.jpg").all()


def test_clip_tiles_features():
    """--tiles: rejilla KxK y rasgos [global, media, máx] con un embedder falso (sin pesos)."""
    from PIL import Image

    import clip_baseline

    im = Image.new("RGB", (100, 60))
    tiles = clip_baseline.tile_images(im, 3)
    assert len(tiles) == 9 and sum(t.size[0] for t in tiles[:3]) == 100 and sum(t.size[1] for t in tiles[::3]) == 60

    class E(clip_baseline.ClipEmbedder):
        def __init__(self):
            pass

        def embed_pil(self, images):
            return np.stack([np.full(4, float(i)) for i in range(len(images))])

    f = E().features_pil([im, im], tiles=2)
    assert f.shape == (2, 12)
    # imagen 0 -> global 0, teselas 1..4 (media 2.5, máx 4); imagen 1 -> global 5, teselas 6..9
    assert np.allclose(f[0], [0] * 4 + [2.5] * 4 + [4] * 4) and np.allclose(f[1], [5] * 4 + [7.5] * 4 + [9] * 4)
    g = clip_baseline.global_part(np.array([[3.0, 4.0, 1, 1, 1, 1]]), 2)
    assert np.allclose(g, [[0.6, 0.8]])
