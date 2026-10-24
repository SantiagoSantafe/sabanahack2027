"""Cadena evaluate -> threshold -> gallery -> export_detector_yaml sobre predicciones sintéticas."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

import evaluate
import export_detector_yaml
import gallery
import threshold
from conftest import pattern_image

CLASSES = ["alternaria", "heliothis", "oidio", "sana"]


def _pred_csv(tmp_path: Path, name: str, n: int, seed: int, strength: float = 2.5) -> Path:
    rng = np.random.default_rng(seed)
    img_dir = tmp_path / f"img_{name}"
    img_dir.mkdir()
    rows = []
    for i in range(n):
        t = CLASSES[i % 4]
        logits = rng.normal(0, 1, 4)
        logits[CLASSES.index(t)] += strength
        p = np.exp(logits) / np.exp(logits).sum()
        path = img_dir / f"{i:03d}.jpg"
        pattern_image(seed * 1000 + i, (48, 48)).save(path)
        row = {"path": str(path), "y_true": t, "y_pred": CLASSES[int(p.argmax())], "item_id": f"{name}/{i}", "group": f"g{i // 2}", "split": name, "model": "sintetico"}
        row.update({f"p_{c}": float(v) for c, v in zip(CLASSES, p)})
        rows.append(row)
    out = tmp_path / f"pred_{name}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _known_csv(tmp_path: Path) -> Path:
    # 6 casos con probabilidades fijas: argmax = [a, a, h, s, s, o]; verdad = [a, a, h, h, s, s]
    probs = [[0.7, 0.1, 0.1, 0.1], [0.6, 0.2, 0.1, 0.1], [0.1, 0.8, 0.05, 0.05], [0.1, 0.3, 0.1, 0.5], [0.05, 0.05, 0.1, 0.8], [0.1, 0.1, 0.45, 0.35]]
    truth = ["alternaria", "alternaria", "heliothis", "heliothis", "sana", "sana"]
    rows = []
    for i, (p, t) in enumerate(zip(probs, truth)):
        rows.append({"path": f"/no/existe/{i}.jpg", "y_true": t, "y_pred": CLASSES[int(np.argmax(p))], **{f"p_{c}": v for c, v in zip(CLASSES, p)}})
    out = tmp_path / "known.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def test_evaluate_known_case(tmp_path):
    pred = _known_csv(tmp_path)
    out = tmp_path / "ev"
    assert evaluate.main(["--pred", str(pred), "--out", str(out), "--n-boot", "1000", "--threshold", "0.6"]) == 0
    m = json.loads((out / "metrics.json").read_text())
    a = m["reglas"]["argmax"]
    assert a["accuracy"] == pytest.approx(4 / 6)
    assert a["por_clase"]["alternaria"]["recall"] == 1.0
    assert a["por_clase"]["heliothis"]["recall"] == 0.5
    assert a["por_clase"]["sana"]["precision"] == 0.5
    # binario argmax: enfermos = 4 (a,a,h,h), detectados 3; sanas 2, una alarma (la última -> oidio)
    b = a["binario"]
    assert (b["tp"], b["fp"], b["fn"], b["tn"]) == (3, 1, 1, 1)
    assert b["sensibilidad"] == pytest.approx(0.75)
    assert b["ic95"]["sensibilidad"][0] <= 0.75 <= b["ic95"]["sensibilidad"][1]
    assert m["meta"]["n_boot"] == 1000 and m["meta"]["unidad_bootstrap"] == "sample"
    # umbral 0.6 sobre 1 - p(sana): puntajes = [.9, .9, .95, .5, .2, .65] -> sospecha en 0,1,2,5
    u = m["reglas"]["umbral"]["binario"]
    assert (u["tp"], u["fp"], u["fn"], u["tn"]) == (3, 1, 1, 1)
    assert m["reglas"]["umbral"]["matriz_confusion"]["conteos"][3] == [0, 0, 1, 1]
    assert m["curvas"]["enfermo_vs_sano"]["n_pos"] == 4
    for f in ("confusion_matrix.png", "pr_curve.png", "per_class.csv"):
        assert (out / f).stat().st_size > 0


def test_threshold_gallery_export_chain(tmp_path):
    val = _pred_csv(tmp_path, "val", 80, seed=1)
    test = _pred_csv(tmp_path, "test", 60, seed=2)
    thr_json = tmp_path / "thr" / "threshold.json"
    thr_json.parent.mkdir()
    assert threshold.main(["--val-pred", str(val), "--test-pred", str(test), "--out", str(thr_json), "--target-sensitivity", "0.9"]) == 0
    t = json.loads(thr_json.read_text())
    assert t["validacion"]["sensibilidad"] >= 0.9
    assert 0.0 <= t["umbral"] <= 1.0
    assert "test_informativo" in t and t["test_informativo"]["n"] == 60
    assert (tmp_path / "thr" / "threshold_curva.csv").exists() and (tmp_path / "thr" / "threshold_curva.png").exists()

    ev = tmp_path / "ev"
    assert evaluate.main(["--pred", str(test), "--out", str(ev), "--threshold", str(thr_json), "--n-boot", "200"]) == 0
    m = json.loads((ev / "metrics.json").read_text())
    assert m["meta"]["unidad_bootstrap"] == "group"
    assert m["reglas"]["umbral"]["umbral"] == pytest.approx(t["umbral"])
    # la regla de umbral nunca detecta menos enfermos que... ella misma en threshold.py
    assert m["reglas"]["umbral"]["binario"]["tp"] == t["test_informativo"]["tp"]

    gal = tmp_path / "gal"
    assert gallery.main(["--pred", str(test), "--out", str(gal), "--threshold", str(thr_json), "--attribution", "sintético"]) == 0
    err = pd.read_csv(gal / "errores.csv")
    assert set(err["tipo_error"]) <= {"falsas_alarmas", "no_detectados", "confusion_enfermedades"}
    assert (err["tipo_error"] == "falsas_alarmas").sum() == m["reglas"]["umbral"]["binario"]["fp"]
    assert (err["tipo_error"] == "no_detectados").sum() == m["reglas"]["umbral"]["binario"]["fn"]
    html = (gal / "galeria.html").read_text()
    assert "data:image/jpeg;base64," in html or len(err) == 0
    for k in ("falsas_alarmas", "no_detectados", "confusion_enfermedades"):
        assert (gal / f"{k}.png").exists()

    det_path = tmp_path / "resultados" / "detector.yaml"
    assert export_detector_yaml.main(["--metrics", str(ev / "metrics.json"), "--threshold", str(thr_json), "--out", str(det_path),
                                      "--dataset-name", "sintético", "--dataset-license", "n/a"]) == 0
    det = yaml.safe_load(det_path.read_text())
    mat = np.array(det["matriz_confusion_normalizada"]["valores"])
    np.testing.assert_allclose(mat.sum(axis=1), 1.0, atol=1e-3)
    assert det["clases"] == CLASSES and det["regla_decision"] == "umbral"
    assert det["umbral_sospecha"] == pytest.approx(round(t["umbral"], 4))
    assert set(det["recall_por_clase"]) == set(CLASSES)
    assert 0 <= det["binario_enfermo_vs_sano"]["tasa_fp"] <= 1
    assert det["origen_datos"]["dataset"] == "sintético"
    assert "generado" in det
