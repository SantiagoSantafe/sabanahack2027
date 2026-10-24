"""Sonda lineal y cero-shot (sin cargar CLIP), predict.py con un clasificador falso y el presupuesto de tiempo de YOLO.

Las pruebas marcadas ``slow`` cargan CLIP y YOLO reales y entrenan 1 época con imágenes sintéticas;
se activan con ``RUN_SLOW=1``.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from PIL import Image

import clip_baseline as CB
import predict
import train_yolo_cls as TY
from common import decide
from conftest import pattern_image, slow


# --------------------------------------------------------------------------- CLIP (sin modelo)

def test_fit_probe_separable_embeddings():
    rng = np.random.default_rng(0)
    centers = rng.normal(0, 1, (4, 64))
    labels = ["alternaria", "heliothis", "oidio", "sana"]

    def sample(n):
        y = [labels[i % 4] for i in range(n)]
        X = np.stack([centers[labels.index(c)] + rng.normal(0, 0.3, 64) for c in y])
        return X / np.linalg.norm(X, axis=1, keepdims=True), y

    Xtr, ytr = sample(120)
    Xv, yv = sample(40)
    model, info = CB.fit_probe(Xtr, ytr, Xv, yv)
    assert info["C_elegido"] in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)
    assert len(info["busqueda_C"]) == 7
    pred = model.classes_[model.predict_proba(Xv).argmax(1)]
    assert (pred == np.array(yv)).mean() > 0.95
    np.testing.assert_allclose(model.predict_proba(Xv).sum(1), 1.0)


def test_prompts_and_templates():
    pr = CB.prompts_for(["sana", "oidio", "clase_nueva"])
    assert pr["sana"] == CB.DEFAULT_PROMPTS["sana"]
    assert pr["clase_nueva"] == ["a blueberry leaf with clase nueva"]
    texts = CB.expand_templates(pr["oidio"])
    assert len(texts) == len(pr["oidio"]) * len(CB.TEMPLATES)
    assert all("powdery mildew" in t or "powdery" in t or "reddish" in t for t in texts)
    custom = CB.prompts_for(["sana"], {"sana": ["x"]})
    assert custom == {"sana": ["x"]}


def test_zeroshot_probs_pick_nearest_text():
    text = np.eye(3)
    img = np.array([[0.9, 0.1, 0.0], [0.0, 0.2, 0.98]])
    img = img / np.linalg.norm(img, axis=1, keepdims=True)
    p = CB.zeroshot_probs(img, text)
    np.testing.assert_allclose(p.sum(1), 1.0)
    assert p.argmax(1).tolist() == [0, 2]


# --------------------------------------------------------------------------- predict.py

class FakeClassifier:
    classes = ["alternaria", "oidio", "sana"]
    name = "falso"

    def __init__(self, probs):
        self.probs = np.asarray(probs, float)
        self.calls = 0

    def predict_proba(self, images):
        self.calls += 1
        assert all(isinstance(im, Image.Image) for im in images)
        return np.repeat(self.probs[None, :], len(images), axis=0)


def test_decide_one_matches_common_decide():
    classes = FakeClassifier.classes
    for probs in ([0.2, 0.1, 0.7], [0.5, 0.3, 0.2], [0.1, 0.25, 0.65]):
        for thr in (None, 0.3, 0.5, 0.9):
            r = predict.decide_one(np.array(probs), classes, "sana", thr)
            assert r["clase"] == decide(np.array([probs]), classes, "sana", thr)[0]
            assert r["sospecha"] == (r["clase"] != "sana")


def test_predict_cli_with_fake_classifier(tmp_path, capsys):
    img = tmp_path / "hoja.png"
    pattern_image(3, (120, 80)).save(img)
    clf = FakeClassifier([0.2, 0.15, 0.65])  # p_enfermedad = 0.35
    log = tmp_path / "log.jsonl"
    assert predict.main(["--weights", "x.joblib", "--image", str(img), "--threshold", "0.3", "--log", str(log), "--center-crop", "0.5"], classifier=clf) == 0
    res = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert res["sospecha"] is True and res["clase"] == "alternaria" and res["clase_top1"] == "sana"
    assert res["p_enfermedad"] == pytest.approx(0.35)
    assert set(res["latencia_ms"]) == {"preproceso", "inferencia", "total"} and res["latencia_ms"]["total"] >= 0
    assert json.loads(log.read_text().strip())["clase"] == "alternaria"
    assert clf.calls == 2  # calentamiento + inferencia
    # sin umbral: argmax -> sana, sin sospecha
    predict.main(["--weights", "x.joblib", "--image", str(img), "--no-warmup"], classifier=clf)
    res2 = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert res2["clase"] == "sana" and res2["sospecha"] is False


def test_predict_bench_and_dir(tmp_path, capsys):
    d = tmp_path / "imgs"
    d.mkdir()
    for i in range(3):
        pattern_image(i, (40, 40)).save(d / f"{i}.jpg")
    clf = FakeClassifier([0.6, 0.3, 0.1])
    predict.main(["--weights", "x.pt", "--dir", str(d), "--threshold", "0.5"], classifier=clf)
    lines = [json.loads(x) for x in capsys.readouterr().out.strip().splitlines()]
    assert len(lines) == 3 and all(x["sospecha"] for x in lines)
    bench = tmp_path / "lat.json"
    predict.main(["--weights", "x.pt", "--image", str(d / "0.jpg"), "--bench", "5", "--bench-out", str(bench)], classifier=clf)
    b = json.loads(bench.read_text())
    assert b["n"] == 5 and b["latencia_ms"]["p95"] >= b["latencia_ms"]["p50"] >= 0


def test_crop_frame_roi():
    im = Image.new("RGB", (200, 100))
    assert predict.crop_frame(im, (0.5, 0.0, 0.5, 0.5)).size == (100, 50)
    assert predict.crop_frame(im, None, 0.5).size == (100, 50)
    with pytest.raises(ValueError):
        predict.parse_roi("0,0,2,1")


# --------------------------------------------------------------------------- presupuesto de tiempo (sin Ultralytics)

def _fake_trainer(tmp_path, epochs=10):
    w = tmp_path / "weights"
    w.mkdir(parents=True, exist_ok=True)
    (w / "last.pt").write_bytes(b"ckpt")
    return SimpleNamespace(epoch=0, start_epoch=0, epochs=epochs, stop=False, save_dir=str(tmp_path), last=str(w / "last.pt"), fitness=0.5, metrics={"metrics/accuracy_top1": 0.8})


def test_time_budget_estimates_and_stops(tmp_path, monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(TY.time, "time", lambda: clock["t"])
    tr = _fake_trainer(tmp_path)
    tb = TY.TimeBudget(max_minutes=2.5, status_path_fn=lambda t: Path(t.save_dir) / TY.STATUS)
    tb.on_train_start(tr)
    for e in range(10):
        tr.epoch = e
        clock["t"] += 60.0  # 1 minuto por época
        tb.on_train_epoch_end(tr)
        tb.on_model_save(tr)
        tb.on_fit_epoch_end(tr)
        if tr.stop:
            break
    st = json.loads((tmp_path / TY.STATUS).read_text())
    assert tr.stop and tb.stopped_by_time
    assert st["epocas_completadas"] == 2  # tras 2 min, una 3.ª época (1 min) excede 2.5 min
    assert st["minutos_estimados_total_esta_sesion"] == pytest.approx(10.0)
    assert (tmp_path / "weights" / "resume.pt").exists()
    # la llamada extra de final_eval no cuenta como época
    tr.epoch += 1
    tb.on_fit_epoch_end(tr)
    assert len(tb.epoch_times) == 2


def test_time_budget_estimate_only(tmp_path, monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(TY.time, "time", lambda: clock["t"])
    tr = _fake_trainer(tmp_path, epochs=30)
    tb = TY.TimeBudget(None, lambda t: Path(t.save_dir) / TY.STATUS, estimate_only=True)
    tb.on_train_start(tr)
    clock["t"] += 12.0
    tb.on_train_epoch_end(tr)
    tb.on_fit_epoch_end(tr)
    assert tr.stop and not tb.stopped_by_time
    assert json.loads((tmp_path / TY.STATUS).read_text())["minutos_estimados_total_esta_sesion"] == pytest.approx(6.0)


# --------------------------------------------------------------------------- integración real (lenta)

def _tiny_cls_dataset(root: Path, n: int = 12) -> pd.DataFrame:
    rows = []
    colors = {"oidio": (230, 230, 230), "sana": (30, 160, 30)}
    for s in ("train", "val", "test"):
        for c, col in colors.items():
            for i in range(n if s == "train" else 4):
                p = root / s / c / f"{s}_{c}_{i}.jpg"
                p.parent.mkdir(parents=True, exist_ok=True)
                a = np.asarray(pattern_image(i + (0 if s == "train" else 500), (64, 64)), float) * 0.3 + np.array(col) * 0.7
                Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(p)
                rows.append({"item_id": f"{s}/{c}/{i}", "path": str(p), "label": c, "source_id": f"{s}{c}{i}", "group": f"{s}{c}{i}", "split": s})
    return pd.DataFrame(rows)


@slow
def test_yolo_train_resume_and_predict_slow(tmp_path):
    df = _tiny_cls_dataset(tmp_path / "data")
    sd = tmp_path / "splits"
    sd.mkdir()
    for s in ("train", "val", "test"):
        df[df["split"] == s].to_csv(sd / f"{s}.csv", index=False)
    args = ["--data-dir", str(tmp_path / "data"), "--project", str(tmp_path / "runs"), "--name", "t", "--epochs", "2", "--imgsz", "64",
            "--batch", "8", "--workers", "0", "--device", "cpu"]
    assert TY.main(args + ["--estimate-only"]) == 0
    run = tmp_path / "runs" / "t"
    st = json.loads((run / TY.STATUS).read_text())
    assert st["epocas_completadas"] == 1 and not st["completado"] and (run / "weights" / "resume.pt").exists()
    assert TY.main(["--resume", str(run), "--splits-dir", str(sd), "--device", "cpu", "--workers", "0"]) == 0
    st = json.loads((run / TY.STATUS).read_text())
    assert st["completado"] and st["epocas_completadas"] == 2
    pred = pd.read_csv(run / "predicciones_yolo_test.csv")
    assert {"p_oidio", "p_sana"} <= set(pred.columns) and len(pred) == 8


@slow
def test_clip_real_model_slow(tmp_path):
    df = _tiny_cls_dataset(tmp_path / "data", n=6)
    sd = tmp_path / "splits"
    sd.mkdir()
    for s in ("train", "val", "test"):
        df[df["split"] == s].to_csv(sd / f"{s}.csv", index=False)
    out = tmp_path / "clip"
    assert CB.main(["--splits-dir", str(sd), "--out", str(out), "--mode", "both", "--prompts-json", str(_prompts(tmp_path))]) == 0
    for m in ("zeroshot", "probe"):
        p = pd.read_csv(out / f"predicciones_{m}_test.csv")
        np.testing.assert_allclose(p[["p_oidio", "p_sana"]].sum(1), 1.0, atol=1e-4)
        assert (out / f"clip_{m}.joblib").exists()
    clf = predict.load_classifier(out / "clip_probe.joblib")
    probs = clf.predict_proba([Image.open(df["path"].iloc[0])])
    assert probs.shape == (1, 2)


def _prompts(tmp_path: Path) -> Path:
    p = tmp_path / "prompts.json"
    p.write_text(json.dumps({"oidio": ["a white square"], "sana": ["a green square"]}))
    return p
