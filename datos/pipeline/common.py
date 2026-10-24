"""Utilidades compartidas del pipeline de imágenes (Sabana Hack, reto "Berry Good Idea").

Convenciones que usan todos los módulos:

* Manifiesto (salida de ``convert.py``): una fila por ítem de clasificación con, al menos,
  ``item_id, path, label, source_id, source_path``. ``source_id`` identifica la imagen de
  ORIGEN y es la unidad que nunca se reparte entre splits.
* Predicciones (salida de ``clip_baseline.py`` y ``train_yolo_cls.py``): CSV con
  ``path, y_true, y_pred`` y una columna ``p_<clase>`` por clase, más metadatos opcionales
  (``item_id, source_id, group, split, model``). ``evaluate.py``, ``threshold.py`` y
  ``gallery.py`` solo dependen de este formato, así que sirven para cualquier modelo.
* Puntaje de enfermedad: ``1 - p_<clase_sana>``. Una imagen es "sospecha" si el puntaje es
  >= umbral; en ese caso la clase decidida es la enfermedad más probable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

PIPELINE_DIR: Path = Path(__file__).resolve().parent
DATOS_DIR: Path = PIPELINE_DIR.parent
PESOS_DIR: Path = PIPELINE_DIR / "pesos"
RESULTADOS_DIR: Path = DATOS_DIR / "resultados"
OPEN_CLIP_CACHE: Path = PESOS_DIR / "open_clip"
YOLO_CLS_WEIGHTS: Path = PESOS_DIR / "yolo11n-cls.pt"

IMG_EXTS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"})
DEFAULT_HEALTHY: str = "sana"
PROB_PREFIX: str = "p_"
SPLITS: tuple[str, str, str] = ("train", "val", "test")
SPLIT_ALIASES: dict[str, str] = {
    "train": "train",
    "training": "train",
    "valid": "val",
    "val": "val",
    "validation": "val",
    "test": "test",
    "testing": "test",
}

_RF_SUFFIX = re.compile(r"\.rf\.[0-9a-fA-F]{8,}$")


# --------------------------------------------------------------------------- nombres

def normalize_name(name: str) -> str:
    """Nombre canónico: minúsculas, sin tildes, separadores como ``_``.

    >>> normalize_name("Oídio ")
    'oidio'
    """
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s.strip().lower()).strip("_")
    return s or "sin_nombre"


def parse_class_map(spec: str | None) -> dict[str, str]:
    """Lee un mapeo de clases ``"A=b,C=d"`` o la ruta a un JSON ``{"A": "b"}``.

    Las claves se comparan después de ``normalize_name``; los valores también se normalizan.
    """
    if not spec:
        return {}
    p = Path(spec)
    if p.suffix.lower() == ".json" and p.exists():
        raw = json.loads(p.read_text(encoding="utf-8"))
        items = raw.items()
    else:
        items = []
        for part in spec.split(","):
            if not part.strip():
                continue
            if "=" not in part:
                raise ValueError(f"Mapeo de clase inválido (esperado A=b): {part!r}")
            k, v = part.split("=", 1)
            items.append((k, v))
    return {normalize_name(k): normalize_name(v) for k, v in items}


def map_class(name: str, class_map: dict[str, str]) -> str:
    """Normaliza ``name`` y aplica ``class_map`` (si la clase no está, queda normalizada)."""
    n = normalize_name(name)
    return class_map.get(n, n)


def roboflow_source_id(stem: str) -> str:
    """Quita el sufijo ``.rf.<hash>`` que Roboflow añade a cada copia exportada/aumentada."""
    return _RF_SUFFIX.sub("", stem)


def safe_filename(text: str, max_len: int = 150) -> str:
    """Convierte un texto en un nombre de archivo seguro (sin separadores de ruta)."""
    s = re.sub(r"[^0-9A-Za-z._-]+", "_", text).strip("._")
    return (s or "x")[:max_len]


# --------------------------------------------------------------------------- archivos

def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    """SHA-256 hexadecimal de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if not np.isfinite(v) else v
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"No serializable: {type(o)}")


def _clean_nan(obj: Any) -> Any:
    """Reemplaza NaN/inf por None para producir JSON válido."""
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_nan(v) for v in obj]
    return obj


def write_json(path: str | Path, obj: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(_clean_nan(obj), indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    return p


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def list_images(root: str | Path, recursive: bool = True) -> list[Path]:
    """Imágenes bajo ``root`` (orden determinista). Ignora archivos ocultos."""
    root = Path(root)
    it: Iterable[Path] = root.rglob("*") if recursive else root.glob("*")
    out = [
        p
        for p in it
        if p.is_file() and p.suffix.lower() in IMG_EXTS and not any(part.startswith(".") for part in p.relative_to(root).parts)
    ]
    return sorted(out)


def write_csv(df: pd.DataFrame, path: str | Path) -> Path:
    """CSV determinista (sin índice, fin de línea ``\\n``)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, lineterminator="\n")
    return p


def read_manifests(paths: Sequence[str | Path]) -> pd.DataFrame:
    """Concatena uno o varios manifiestos y valida columnas mínimas e ``item_id`` único."""
    frames = [pd.read_csv(p, dtype={"source_id": str, "item_id": str, "label": str}, keep_default_na=False) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    required = {"item_id", "path", "label", "source_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Al manifiesto le faltan columnas: {sorted(missing)}")
    dups = df["item_id"][df["item_id"].duplicated()].unique()
    if len(dups):
        raise ValueError(f"item_id duplicados entre manifiestos (ej. {list(dups[:3])})")
    if "source_path" not in df.columns:
        df["source_path"] = df["path"]
    return df


# --------------------------------------------------------------------------- entorno

def set_offline_env(allow_online: bool = False) -> None:
    """Evita llamadas de red de Ultralytics/Hugging Face en este proceso (no toca configuración)."""
    if allow_online:
        return
    os.environ.setdefault("YOLO_OFFLINE", "1")
    if (OPEN_CLIP_CACHE / "models--laion--CLIP-ViT-B-32-laion2B-s34B-b79K").exists():
        os.environ.setdefault("HF_HUB_OFFLINE", "1")


def pick_device(pref: str = "auto") -> str:
    """``mps`` si está disponible (Apple Silicon), si no ``cpu``; respeta una preferencia explícita."""
    if pref and pref != "auto":
        return pref
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


# --------------------------------------------------------------------------- predicciones

def prob_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith(PROB_PREFIX)]


def read_predictions(path: str | Path) -> tuple[pd.DataFrame, list[str]]:
    """Lee un CSV de predicciones y devuelve ``(df, clases)`` en el orden de las columnas ``p_*``."""
    df = pd.read_csv(path, keep_default_na=False, dtype={"y_true": str, "y_pred": str})
    cols = prob_columns(df)
    if not cols:
        raise ValueError(f"{path}: no hay columnas {PROB_PREFIX}<clase>")
    for c in ("path", "y_true"):
        if c not in df.columns:
            raise ValueError(f"{path}: falta la columna {c}")
    classes = [c[len(PROB_PREFIX):] for c in cols]
    df[cols] = df[cols].astype(float)
    return df, classes


def build_predictions_frame(
    meta: pd.DataFrame | None,
    probs: np.ndarray,
    classes: Sequence[str],
    paths: Sequence[str],
    y_true: Sequence[str] | None,
    model_name: str,
) -> pd.DataFrame:
    """Arma el DataFrame estándar de predicciones."""
    probs = np.asarray(probs, dtype=float)
    out = pd.DataFrame({"path": list(paths)})
    out["y_true"] = list(y_true) if y_true is not None else [""] * len(paths)
    out["y_pred"] = [classes[i] for i in probs.argmax(axis=1)] if len(probs) else []
    for j, c in enumerate(classes):
        out[f"{PROB_PREFIX}{c}"] = np.round(probs[:, j], 6) if len(probs) else []
    if meta is not None:
        for col in ("item_id", "source_id", "group", "split", "dataset"):
            if col in meta.columns:
                out[col] = meta[col].to_numpy()
    out["model"] = model_name
    return out


def healthy_index(classes: Sequence[str], healthy: str) -> int:
    h = normalize_name(healthy)
    names = [normalize_name(c) for c in classes]
    if h not in names:
        raise ValueError(f"La clase sana {healthy!r} no está entre las clases {list(classes)}")
    return names.index(h)


def disease_scores(probs: np.ndarray, classes: Sequence[str], healthy: str = DEFAULT_HEALTHY) -> np.ndarray:
    """Puntaje de enfermedad = 1 - p(sana)."""
    probs = np.asarray(probs, dtype=float)
    return 1.0 - probs[:, healthy_index(classes, healthy)]


def decide(
    probs: np.ndarray,
    classes: Sequence[str],
    healthy: str = DEFAULT_HEALTHY,
    threshold: float | None = None,
) -> list[str]:
    """Clase decidida por fila.

    Sin umbral: argmax. Con umbral: si ``1 - p(sana) >= umbral`` se decide la enfermedad más
    probable; si no, la clase sana.
    """
    probs = np.asarray(probs, dtype=float)
    if threshold is None:
        return [classes[i] for i in probs.argmax(axis=1)]
    hi = healthy_index(classes, healthy)
    scores = 1.0 - probs[:, hi]
    masked = probs.copy()
    masked[:, hi] = -np.inf
    best_disease = masked.argmax(axis=1)
    return [classes[int(best_disease[i])] if scores[i] >= threshold else classes[hi] for i in range(len(probs))]


def load_threshold(path_or_value: str | float | None) -> float | None:
    """Acepta un número o la ruta a ``threshold.json`` (clave ``umbral``)."""
    if path_or_value is None or path_or_value == "":
        return None
    if isinstance(path_or_value, (int, float)):
        return float(path_or_value)
    p = Path(str(path_or_value))
    if p.exists():
        return float(read_json(p)["umbral"])
    return float(path_or_value)


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    z = x - x.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)
