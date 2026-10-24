#!/usr/bin/env python
"""Líneas base con CLIP (open_clip ViT-B-32, pesos laion2b_s34b_b79k, caché local en pipeline/pesos/open_clip).

* ``zeroshot``: clasifica comparando la imagen con varias descripciones de texto por clase,
  promediadas sobre varias plantillas ("a photo of {}.", "a close-up photo of {}.", ...).
* ``probe``: sonda lineal = regresión logística sobre los embeddings CLIP (estandarizados),
  entrenada en train y con C elegido en VALIDACIÓN (macro-F1). Es la línea base fuerte y rápida.

Lee ``train.csv``/``val.csv``/``test.csv`` de ``split.py`` y escribe en ``--out``:
``predicciones_<modo>_<split>.csv`` (formato estándar del pipeline), ``clip_<modo>.joblib``
(cabezal reutilizable por ``predict.py``) y ``clip_<modo>_resumen.json``. Los embeddings se
guardan en caché (``--cache``), así repetir es casi instantáneo.

``--tiles K`` (solo afecta a la sonda): además del embedding de la imagen completa calcula el de
una rejilla KxK de teselas y usa como rasgo ``[global, media(teselas), máx(teselas)]`` (3x512). Sirve
para lesiones diminutas (Alternaria) que se pierden al reducir 1024 px a 224 px. El cero-shot usa
siempre la parte global.

Las descripciones por defecto en inglés son un SUPUESTO de redacción (CLIP se entrenó en inglés);
se pueden cambiar con ``--prompts-json`` ({"clase": ["desc 1", "desc 2"]}).

Ejemplo:
    .venv/bin/python -I pipeline/clip_baseline.py --splits-dir pipeline/work/drberry/splits \
        --out pipeline/work/drberry/clip --mode both
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import (  # noqa: E402
    OPEN_CLIP_CACHE,
    SPLITS,
    build_predictions_frame,
    now_iso,
    pick_device,
    read_json,
    set_offline_env,
    softmax,
    write_csv,
    write_json,
)

DEFAULT_MODEL = "ViT-B-32"
DEFAULT_PRETRAINED = "laion2b_s34b_b79k"

TEMPLATES: list[str] = [
    "a photo of {}.",
    "a close-up photo of {}.",
    "a field photo of {}.",
    "a cropped photo of {}.",
    "a bright photo of {}.",
    "a blurry photo of {}.",
    "a photo of {}, agricultural plant disease.",
]

# SUPUESTO: descripciones redactadas por el equipo a partir de la sintomatología general.
DEFAULT_PROMPTS: dict[str, list[str]] = {
    "sana": [
        "a healthy green blueberry leaf",
        "a healthy blueberry leaf with no spots or damage",
    ],
    "oidio": [
        "a blueberry leaf with powdery mildew",
        "a blueberry leaf with white powdery fungal patches",
        "a blueberry leaf with reddish blotches caused by powdery mildew",
    ],
    "alternaria": [
        "a blueberry leaf with Alternaria leaf spot",
        "a blueberry leaf with small brown necrotic spots",
        "a blueberry leaf with dark circular lesions",
    ],
    "heliothis": [
        "a blueberry leaf eaten by a caterpillar",
        "a blueberry leaf with holes chewed by Heliothis larvae",
        "a blueberry leaf with insect feeding damage",
    ],
}


def prompts_for(classes: Sequence[str], custom: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    """Descripciones por clase (las personalizadas mandan; si falta una clase se genera una genérica)."""
    base = {**DEFAULT_PROMPTS, **(custom or {})}
    return {c: base.get(c, [f"a blueberry leaf with {c.replace('_', ' ')}"]) for c in classes}


def expand_templates(descriptions: Sequence[str], templates: Sequence[str] = TEMPLATES) -> list[str]:
    return [t.format(d) for d in descriptions for t in templates]


class ClipEmbedder:
    """Envuelve open_clip: embeddings L2-normalizados de imágenes (PIL o rutas) y de textos."""

    def __init__(self, model_name: str = DEFAULT_MODEL, pretrained: str = DEFAULT_PRETRAINED, device: str = "auto", cache_dir: str | Path = OPEN_CLIP_CACHE) -> None:
        import open_clip
        import torch

        self.torch = torch
        self.device = pick_device(device)
        self.model_name, self.pretrained = model_name, pretrained
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained, cache_dir=str(cache_dir), device=self.device)
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(model_name)

    @property
    def tag(self) -> str:
        return f"{self.model_name}/{self.pretrained}"

    def embed_pil(self, images: Sequence[Any]) -> np.ndarray:
        torch = self.torch
        x = torch.stack([self.preprocess(im.convert("RGB")) for im in images]).to(self.device)
        with torch.no_grad():
            f = self.model.encode_image(x)
            f = f / f.norm(dim=-1, keepdim=True)
        return f.float().cpu().numpy()

    def features_pil(self, images: Sequence[Any], tiles: int = 0) -> np.ndarray:
        """Rasgos por imagen: embedding global o, con ``tiles=K``, ``[global, media, máx]`` de KxK teselas."""
        if not tiles:
            return self.embed_pil(images)
        crops = []
        for im in images:
            crops.append(im)
            crops.extend(tile_images(im, tiles))
        e = self.embed_pil(crops).reshape(len(images), 1 + tiles * tiles, -1)
        return np.concatenate([e[:, 0], e[:, 1:].mean(axis=1), e[:, 1:].max(axis=1)], axis=1)

    def embed_paths(self, paths: Sequence[str], batch: int = 32, progress: bool = True, tiles: int = 0) -> np.ndarray:
        from PIL import Image, ImageOps

        out = []
        t0 = time.time()
        if tiles:
            batch = max(1, batch // (1 + tiles * tiles))
        for s in range(0, len(paths), batch):
            ims = []
            for p in paths[s : s + batch]:
                with Image.open(p) as im:
                    ims.append(ImageOps.exif_transpose(im).convert("RGB"))
            out.append(self.features_pil(ims, tiles))
            if progress:
                print(f"[clip] embeddings {min(s + batch, len(paths))}/{len(paths)} ({time.time() - t0:.1f} s)", flush=True)
        return np.concatenate(out) if out else np.zeros((0, 512 * (3 if tiles else 1)), np.float32)

    def embed_text(self, texts: Sequence[str]) -> np.ndarray:
        torch = self.torch
        tok = self.tokenizer(list(texts)).to(self.device)
        with torch.no_grad():
            f = self.model.encode_text(tok)
            f = f / f.norm(dim=-1, keepdim=True)
        return f.float().cpu().numpy()

    def class_text_matrix(self, classes: Sequence[str], prompts: dict[str, list[str]], templates: Sequence[str] = TEMPLATES) -> np.ndarray:
        """Un vector por clase: promedio (re-normalizado) de todas sus plantillas x descripciones."""
        rows = []
        for c in classes:
            e = self.embed_text(expand_templates(prompts[c], templates)).mean(axis=0)
            rows.append(e / np.linalg.norm(e))
        return np.stack(rows)


def tile_images(im: Any, k: int) -> list[Any]:
    """Rejilla KxK de teselas (de izquierda a derecha y de arriba abajo) de una imagen PIL."""
    W, H = im.size
    return [im.crop((int(j * W / k), int(i * H / k), int((j + 1) * W / k), int((i + 1) * H / k))) for i in range(k) for j in range(k)]


def global_part(feats: np.ndarray, tiles: int) -> np.ndarray:
    """Parte global (re-normalizada) de los rasgos; con ``tiles=0`` devuelve los mismos rasgos."""
    if not tiles:
        return feats
    g = feats[:, : feats.shape[1] // 3]
    return g / np.linalg.norm(g, axis=1, keepdims=True)


# --------------------------------------------------------------------------- caché

def _key(path: str) -> str:
    p = Path(path)
    st = p.stat()
    return hashlib.sha1(f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()


def cached_embeddings(embedder: ClipEmbedder, paths: Sequence[str], cache: Path, batch: int = 32, tiles: int = 0) -> np.ndarray:
    cache.parent.mkdir(parents=True, exist_ok=True)
    if tiles:
        cache = cache.with_name(f"{cache.stem}_tiles{tiles}{cache.suffix}")
    tag = embedder.tag + (f"|tiles{tiles}" if tiles else "")
    store: dict[str, np.ndarray] = {}
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        if str(z["tag"]) == tag:
            store = dict(zip(z["keys"].tolist(), z["emb"]))
    keys = [_key(p) for p in paths]
    todo = [i for i, k in enumerate(keys) if k not in store]
    if todo:
        emb = embedder.embed_paths([paths[i] for i in todo], batch=batch, tiles=tiles)
        for i, e in zip(todo, emb):
            store[keys[i]] = e
        np.savez(cache, tag=np.array(tag), keys=np.array(list(store.keys())), emb=np.stack(list(store.values())))
    return np.stack([store[k] for k in keys]) if keys else np.zeros((0, 512 * (3 if tiles else 1)), np.float32)


# --------------------------------------------------------------------------- cabezales

def zeroshot_probs(img_emb: np.ndarray, text_mat: np.ndarray, logit_scale: float = 100.0) -> np.ndarray:
    return softmax(logit_scale * img_emb @ text_mat.T, axis=1)


def fit_probe(
    X_train: np.ndarray,
    y_train: Sequence[str],
    X_val: np.ndarray | None = None,
    y_val: Sequence[str] | None = None,
    Cs: Sequence[float] = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0),
    class_weight: str | None = "balanced",
    seed: int = 0,
) -> tuple[Any, dict[str, Any]]:
    """Regresión logística (con estandarización) sobre embeddings; C elegido por macro-F1 en val."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score, log_loss
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    def make(c: float) -> Any:
        return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000, class_weight=class_weight, random_state=seed))

    results = []
    if X_val is not None and y_val is not None and len(y_val):
        for c in Cs:
            m = make(c).fit(X_train, y_train)
            pv = m.predict_proba(X_val)
            f1 = f1_score(y_val, m.classes_[pv.argmax(1)], average="macro", zero_division=0)
            try:
                ll = log_loss(y_val, pv, labels=m.classes_)
            except ValueError:
                ll = float("nan")
            results.append({"C": c, "macro_f1_val": float(f1), "log_loss_val": float(ll)})
        best = sorted(results, key=lambda r: (-r["macro_f1_val"], r["log_loss_val"] if np.isfinite(r["log_loss_val"]) else 1e9, r["C"]))[0]
        c_best = best["C"]
    else:
        c_best = 1.0
    model = make(c_best).fit(X_train, y_train)
    return model, {"C_elegido": c_best, "busqueda_C": results, "class_weight": class_weight}


def save_head(path: Path, head: dict[str, Any]) -> None:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(head, path)


# --------------------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits-dir", required=True, help="Carpeta con train.csv, val.csv, test.csv (split.py)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["zeroshot", "probe", "both"], default="both")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--pretrained", default=DEFAULT_PRETRAINED)
    ap.add_argument("--cache-dir", default=str(OPEN_CLIP_CACHE), help="Caché de pesos open_clip")
    ap.add_argument("--cache", default=None, help="Archivo .npz de caché de embeddings (por defecto <out>/embeddings_cache.npz)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--prompts-json", default=None, help='{"clase": ["descripción", ...]} para el cero-shot')
    ap.add_argument("--class-weight", choices=["balanced", "none"], default="balanced")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tiles", type=int, default=0, help="K>0: rasgos [global, media, máx] de una rejilla KxK (sonda)")
    ap.add_argument("--allow-online", action="store_true", help="Permite descargar pesos si no están en caché")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    set_offline_env(args.allow_online)
    sd, out = Path(args.splits_dir), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    parts = {s: pd.read_csv(sd / f"{s}.csv", keep_default_na=False, dtype={"label": str, "source_id": str}) for s in SPLITS if (sd / f"{s}.csv").exists()}
    if "train" not in parts:
        raise SystemExit(f"Falta train.csv en {sd}")
    classes = sorted(set(parts["train"]["label"]))
    embedder = ClipEmbedder(args.model, args.pretrained, args.device, args.cache_dir)
    cache = Path(args.cache) if args.cache else out / "embeddings_cache.npz"
    t0 = time.time()
    emb = {s: cached_embeddings(embedder, df["path"].tolist(), cache, args.batch, args.tiles) for s, df in parts.items()}
    t_emb = time.time() - t0
    custom = read_json(args.prompts_json) if args.prompts_json else None
    summary: dict[str, Any] = {
        "creado": now_iso(),
        "modelo_clip": embedder.tag,
        "dispositivo": embedder.device,
        "clases": classes,
        "n_por_split": {s: int(len(df)) for s, df in parts.items()},
        "segundos_embeddings": round(t_emb, 2),
        "teselas": args.tiles,
        "splits_dir": str(sd.resolve()),
    }
    modes = ["zeroshot", "probe"] if args.mode == "both" else [args.mode]
    if "zeroshot" in modes:
        prompts = prompts_for(classes, custom)
        text_mat = embedder.class_text_matrix(classes, prompts)
        for s, df in parts.items():
            p = zeroshot_probs(global_part(emb[s], args.tiles), text_mat)
            write_csv(build_predictions_frame(df, p, classes, df["path"].tolist(), df["label"].tolist(), f"clip_zeroshot:{embedder.tag}"), out / f"predicciones_zeroshot_{s}.csv")
        save_head(out / "clip_zeroshot.joblib", {"tipo": "clip_zeroshot", "clip_model": args.model, "pretrained": args.pretrained, "classes": classes, "text_mat": text_mat, "logit_scale": 100.0, "prompts": prompts, "templates": TEMPLATES, "creado": now_iso()})
        summary["zeroshot"] = {"prompts": prompts, "plantillas": TEMPLATES}
        print("[clip] cero-shot listo")
    if "probe" in modes:
        cw = None if args.class_weight == "none" else "balanced"
        Xv = emb.get("val")
        yv = parts["val"]["label"].tolist() if "val" in parts else None
        model, info = fit_probe(emb["train"], parts["train"]["label"].tolist(), Xv, yv, class_weight=cw, seed=args.seed)
        pclasses = [str(c) for c in model.classes_]
        for s, df in parts.items():
            p = model.predict_proba(emb[s])
            write_csv(build_predictions_frame(df, p, pclasses, df["path"].tolist(), df["label"].tolist(), f"clip_probe:{embedder.tag}"), out / f"predicciones_probe_{s}.csv")
        save_head(out / "clip_probe.joblib", {"tipo": "clip_probe", "clip_model": args.model, "pretrained": args.pretrained, "classes": pclasses, "sk_model": model, "info": info, "tiles": args.tiles, "creado": now_iso()})
        summary["probe"] = info
        print(f"[clip] sonda lineal lista (C={info['C_elegido']})")
    write_json(out / "clip_resumen.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
