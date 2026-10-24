#!/usr/bin/env python
"""Sonda lineal CLIP con validación cruzada AGRUPADA sobre train+val ("dev") y modelo final en dev.

Por qué: con ~25 grupos en validación, el C y el umbral fijados solo en val son muy ruidosos (el
umbral elegido en val puede no sostener la sensibilidad en test). Aquí:

1. dev = train ∪ val (el test congelado NO se toca).
2. ``StratifiedGroupKFold`` (K pliegues, sin partir grupos/ráfagas) -> predicciones fuera de pliegue
   (OOF) para cada C de la rejilla; se elige C por macro-F1 OOF.
3. Se escribe ``predicciones_cvprobe_val.csv`` = predicciones OOF de dev (columna ``split=dev_oof``):
   ``threshold.py`` fija el umbral sobre ellas igual que haría con val, pero con ~4x más datos.
4. Modelo final = sonda con ese C entrenada en TODO dev -> ``predicciones_cvprobe_test.csv`` y
   ``clip_probe.joblib`` (mismo formato que ``clip_baseline.py``; ``predict.py`` lo usa tal cual).

Usa la misma caché de embeddings que ``clip_baseline.py`` (``--cache`` o ``<out>/embeddings_cache.npz``).

Ejemplo:
    .venv/bin/python -I pipeline/cv_clip_probe.py --splits-dir resultados/ml/drberry_image/splits \
        --out resultados/ml/drberry_image/clip_cv_tiles2 --tiles 2 --cache resultados/ml/drberry_image/clip_tiles2/embeddings_cache.npz
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from clip_baseline import DEFAULT_MODEL, DEFAULT_PRETRAINED, ClipEmbedder, cached_embeddings, save_head  # noqa: E402
from common import OPEN_CLIP_CACHE, build_predictions_frame, now_iso, set_offline_env, write_csv, write_json  # noqa: E402

CS = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)


def make_probe(c: float, seed: int = 0) -> Any:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000, class_weight="balanced", random_state=seed))


def oof_predictions(X: np.ndarray, y: np.ndarray, groups: np.ndarray, classes: Sequence[str], c: float, folds: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Probabilidades fuera de pliegue (orden ``classes``) y el pliegue de cada fila."""
    from sklearn.model_selection import StratifiedGroupKFold

    cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    P = np.zeros((len(y), len(classes)))
    fold_of = np.full(len(y), -1)
    for k, (tr, te) in enumerate(cv.split(X, y, groups)):
        m = make_probe(c, seed).fit(X[tr], y[tr])
        idx = [list(m.classes_).index(cl) if cl in m.classes_ else None for cl in classes]
        p = m.predict_proba(X[te])
        for j, i in enumerate(idx):
            P[te, j] = p[:, i] if i is not None else 0.0
        fold_of[te] = k
    return P, fold_of


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tiles", type=int, default=0)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache", default=None, help="Caché .npz de embeddings (la de clip_baseline.py sirve)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--pretrained", default=DEFAULT_PRETRAINED)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--allow-online", action="store_true")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    from sklearn.metrics import f1_score

    args = build_parser().parse_args(argv)
    set_offline_env(args.allow_online)
    sd, out = Path(args.splits_dir), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rd = lambda s: pd.read_csv(sd / f"{s}.csv", keep_default_na=False, dtype={"label": str, "source_id": str, "group": str})  # noqa: E731
    dev = pd.concat([rd("train"), rd("val")], ignore_index=True)
    test = rd("test")
    embedder = ClipEmbedder(args.model, args.pretrained, args.device, OPEN_CLIP_CACHE)
    cache = Path(args.cache) if args.cache else out / "embeddings_cache.npz"
    if args.cache and args.tiles:  # cached_embeddings añade el sufijo _tilesK: aceptar la ruta ya sufijada
        stem = cache.stem.replace(f"_tiles{args.tiles}", "")
        cache = cache.with_name(stem + cache.suffix)
    Xd = cached_embeddings(embedder, dev["path"].tolist(), cache, 32, args.tiles)
    Xt = cached_embeddings(embedder, test["path"].tolist(), cache, 32, args.tiles)
    y = dev["label"].to_numpy()
    groups = dev["group"].to_numpy()
    classes = sorted(set(y))
    search = []
    best = None
    for c in CS:
        P, fold_of = oof_predictions(Xd, y, groups, classes, c, args.folds, args.seed)
        f1 = f1_score(y, np.asarray(classes)[P.argmax(1)], average="macro", zero_division=0)
        search.append({"C": c, "macro_f1_oof": float(f1)})
        if best is None or f1 > best[0] + 1e-12:
            best = (f1, c, P, fold_of)
    assert best is not None
    f1, c_best, P, fold_of = best
    tag = f"clip_probe_cv{args.folds}:{embedder.tag}" + (f"|tiles{args.tiles}" if args.tiles else "")
    oof = build_predictions_frame(dev, P, classes, dev["path"].tolist(), y.tolist(), tag)
    oof["split"] = "dev_oof"
    oof["fold"] = fold_of
    write_csv(oof, out / "predicciones_cvprobe_val.csv")
    final = make_probe(c_best, args.seed).fit(Xd, y)
    pclasses = [str(c) for c in final.classes_]
    write_csv(build_predictions_frame(test, final.predict_proba(Xt), pclasses, test["path"].tolist(), test["label"].tolist(), tag),
              out / "predicciones_cvprobe_test.csv")
    info = {"C_elegido": c_best, "busqueda_C_oof": search, "folds": args.folds, "semilla": args.seed, "class_weight": "balanced",
            "entrenado_en": "train+val (dev)", "n_dev": int(len(dev)), "n_grupos_dev": int(len(set(groups)))}
    save_head(out / "clip_probe.joblib", {"tipo": "clip_probe", "clip_model": args.model, "pretrained": args.pretrained, "classes": pclasses,
                                         "sk_model": final, "info": info, "tiles": args.tiles, "creado": now_iso()})
    write_json(out / "cv_resumen.json", {"creado": now_iso(), "splits_dir": str(sd.resolve()), "teselas": args.tiles, **info})
    print(f"[cv_clip_probe] tiles={args.tiles} C={c_best} macroF1_OOF={f1:.3f} (dev n={len(dev)}, grupos={len(set(groups))}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
