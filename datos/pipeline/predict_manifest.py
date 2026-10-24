#!/usr/bin/env python
"""Predicciones en lote sobre un manifiesto CSV arbitrario (p. ej. conjuntos FUERA de DrBerry).

Escribe, por modelo, ``<out>/predicciones_<nombre>.csv`` en el formato estándar del pipeline
(``path, y_true, y_pred, p_<clase>...`` + metadatos), así que ``evaluate.py``, ``gallery.py`` y
``ood_eval.py`` lo leen directamente.

* El manifiesto necesita ``path`` (absoluta o relativa a ``--base-dir``) y una columna de etiqueta
  (``--label-col``, por defecto ``label``; en conjuntos OOD es la categoría, que puede no ser una
  clase del modelo). Las columnas ``item_id, source_id, group, dataset`` se copian si existen, y
  las de ``--keep-cols`` también.
* Modelos (``--weights``, repetible): ``.pt`` de Ultralytics clasificación o cabezales ``.joblib``
  de ``clip_baseline.py`` (pickles: cargue solo los generados por este pipeline). Todos los
  cabezales CLIP con el mismo backbone comparten un único cálculo de embeddings (con caché ``.npz``).
* Las imágenes se abren con PIL + orientación EXIF + RGB (igual que ``predict.py`` en la demo). Las
  que no se pueden leer se omiten y se listan en ``<out>/omitidas.csv``.

Ejemplo:
    .venv/bin/python -I pipeline/predict_manifest.py --manifest resultados/ml/ood/manifest_ood.csv \
        --base-dir . --weights resultados/ml/drberry_crops/clip/clip_probe.joblib --names crops_clip_probe \
        --weights resultados/ml/drberry_crops/runs/y11n_224/weights/best.pt --names crops_yolo --out resultados/ml/ood/pred
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from common import OPEN_CLIP_CACHE, build_predictions_frame, now_iso, pick_device, set_offline_env, softmax, write_csv, write_json  # noqa: E402


def readable_images(paths: Sequence[str]) -> tuple[list[int], list[tuple[str, str]]]:
    """Índices de las imágenes que PIL puede abrir y lista ``(ruta, error)`` de las que no."""
    ok: list[int] = []
    bad: list[tuple[str, str]] = []
    for i, p in enumerate(paths):
        try:
            with Image.open(p) as im:
                im.verify()
            ok.append(i)
        except Exception as e:  # noqa: BLE001
            bad.append((p, f"{type(e).__name__}: {e}"))
    return ok, bad


def load_rgb(path: str) -> Image.Image:
    with Image.open(path) as im:
        return ImageOps.exif_transpose(im).convert("RGB")


def yolo_probs(weights: Path, paths: Sequence[str], imgsz: int, device: str, batch: int = 32) -> tuple[np.ndarray, list[str]]:
    from ultralytics import YOLO

    model = YOLO(str(weights))
    names = [model.names[i] for i in sorted(model.names)]
    out = []
    t0 = time.time()
    for s in range(0, len(paths), batch):
        ims = [load_rgb(p) for p in paths[s : s + batch]]
        for r in model.predict(ims, imgsz=imgsz, device=device, verbose=False):
            out.append(r.probs.data.float().cpu().numpy())
        if (s // batch) % 20 == 0:
            print(f"[predict_manifest] yolo {weights.name}: {min(s + batch, len(paths))}/{len(paths)} ({time.time() - t0:.0f} s)", flush=True)
    return (np.stack(out) if out else np.zeros((0, len(names)))), names


def clip_head_probs(head: dict[str, Any], emb: np.ndarray) -> tuple[np.ndarray, list[str]]:
    classes = list(head["classes"])
    if head["tipo"] == "clip_probe":
        return head["sk_model"].predict_proba(emb), classes
    return softmax(float(head["logit_scale"]) * emb @ np.asarray(head["text_mat"]).T, axis=1), classes


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, help="CSV con al menos path y la columna de etiqueta")
    ap.add_argument("--base-dir", default=None, help="Base para rutas relativas (por defecto, la carpeta del manifiesto)")
    ap.add_argument("--label-col", default="label")
    ap.add_argument("--keep-cols", default="", help="Columnas extra a copiar, separadas por comas")
    ap.add_argument("--weights", action="append", required=True, help="Modelo .pt o .joblib (repetible)")
    ap.add_argument("--names", action="append", default=None, help="Nombre de salida por modelo (mismo orden que --weights)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--imgsz", type=int, action="append", default=None, help="imgsz por modelo YOLO (repetible; por defecto 224)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--clip-cache", default=None, help="Caché .npz de embeddings (por defecto <out>/embeddings_cache.npz)")
    ap.add_argument("--allow-online", action="store_true")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    set_offline_env(args.allow_online)
    man = Path(args.manifest).resolve()
    base = Path(args.base_dir).resolve() if args.base_dir else man.parent
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(man, keep_default_na=False, dtype=str)
    if "path" not in df.columns or args.label_col not in df.columns:
        raise SystemExit(f"El manifiesto necesita las columnas path y {args.label_col}")
    df["path"] = [str(p if Path(p).is_absolute() else (base / p)) for p in df["path"]]
    ok, bad = readable_images(df["path"].tolist())
    if bad:
        write_csv(pd.DataFrame(bad, columns=["path", "error"]), out / "omitidas.csv")
        print(f"[predict_manifest] AVISO: {len(bad)} imágenes ilegibles omitidas (omitidas.csv)")
    df = df.iloc[ok].reset_index(drop=True)
    paths = df["path"].tolist()
    names = args.names or [Path(w).stem for w in args.weights]
    if len(names) != len(args.weights):
        raise SystemExit("--names debe tener tantos valores como --weights")
    imgszs = list(args.imgsz or [])
    device = pick_device(args.device)
    keep = [c for c in args.keep_cols.split(",") if c and c in df.columns]
    resumen: dict[str, Any] = {"creado": now_iso(), "manifiesto": str(man), "n": len(df), "omitidas": len(bad), "modelos": {}}

    emb_cache: dict[tuple[str, str], np.ndarray] = {}
    yolo_k = 0
    for w, name in zip(args.weights, names):
        wp = Path(w).resolve()
        t0 = time.time()
        if wp.suffix == ".joblib":
            import joblib

            from clip_baseline import ClipEmbedder, cached_embeddings

            head = joblib.load(wp)
            if head.get("tipo") not in ("clip_probe", "clip_zeroshot"):
                raise SystemExit(f"{wp} no es un cabezal CLIP de este pipeline")
            tiles = int(head.get("tiles", 0) or 0) if head["tipo"] == "clip_probe" else 0
            key = (head["clip_model"], head["pretrained"], tiles)
            if key not in emb_cache:
                emb_cache[key] = cached_embeddings(ClipEmbedder(key[0], key[1], device, OPEN_CLIP_CACHE), paths,
                                                   Path(args.clip_cache) if args.clip_cache else out / "embeddings_cache.npz", args.batch, tiles)
            probs, classes = clip_head_probs(head, emb_cache[key])
            model_tag = f"{head['tipo']}:{wp.parent.parent.name}/{wp.name}"
        else:
            imgsz = imgszs[yolo_k] if yolo_k < len(imgszs) else (imgszs[-1] if imgszs else 224)
            yolo_k += 1
            probs, classes = yolo_probs(wp, paths, imgsz, device, args.batch)
            model_tag = f"yolo_cls:{wp.parents[1].name}/{wp.name}@{imgsz}"
        pred = build_predictions_frame(df, probs, classes, paths, df[args.label_col].tolist(), model_tag)
        for c in keep:
            pred[c] = df[c].to_numpy()
        dest = write_csv(pred, out / f"predicciones_{name}.csv")
        resumen["modelos"][name] = {"pesos": str(wp), "modelo": model_tag, "clases": classes, "segundos": round(time.time() - t0, 1), "salida": str(dest)}
        print(f"[predict_manifest] {name}: {len(pred)} predicciones -> {dest} ({time.time() - t0:.0f} s)", flush=True)
    write_json(out / "predict_manifest_resumen.json", resumen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
