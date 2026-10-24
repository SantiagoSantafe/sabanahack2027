"""Métricas puras (numpy) usadas por evaluate.py y threshold.py.

Convención: "positivo" = enfermo (cualquier clase distinta de la sana). Sensibilidad = TP/(TP+FN),
tasa de falsos positivos (FPR) = FP/(FP+TN), tasa de falsa alarma (FDR) = FP/(TP+FP).
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy import stats


# --------------------------------------------------------------------------- multiclase

def confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str], classes: Sequence[str]) -> np.ndarray:
    """Matriz de confusión (filas = verdad, columnas = predicción) en el orden de ``classes``."""
    idx = {c: i for i, c in enumerate(classes)}
    k = len(classes)
    t = np.array([idx[c] for c in y_true], dtype=int)
    p = np.array([idx[c] for c in y_pred], dtype=int)
    return confusion_from_indices(t, p, k)


def confusion_from_indices(t: np.ndarray, p: np.ndarray, k: int) -> np.ndarray:
    return np.bincount(t * k + p, minlength=k * k).reshape(k, k)


def _safe_div(a: np.ndarray | float, b: np.ndarray | float) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / np.where(b > 0, b, 1.0), np.nan)


def per_class_prf(cm: np.ndarray) -> dict[str, np.ndarray]:
    """Precision, recall, F1 y soporte por clase a partir de la matriz de confusión."""
    cm = np.asarray(cm, dtype=float)
    tp = np.diag(cm)
    pred_pos = cm.sum(axis=0)
    support = cm.sum(axis=1)
    precision = _safe_div(tp, pred_pos)
    recall = _safe_div(tp, support)
    # F1 = 2TP / (2TP + FP + FN); solo es indefinido si la clase no aparece ni en verdad ni en predicción.
    f1 = _safe_div(2 * tp, pred_pos + support)
    return {"precision": precision, "recall": recall, "f1": f1, "support": support.astype(int)}


def multiclass_summary(cm: np.ndarray) -> dict[str, float]:
    """Exactitud, macro-F1 y exactitud balanceada (promedio de recall de las clases con soporte)."""
    cm = np.asarray(cm, dtype=float)
    n = cm.sum()
    prf = per_class_prf(cm)
    has = prf["support"] > 0
    return {
        "accuracy": float(np.trace(cm) / n) if n else float("nan"),
        "macro_f1": float(np.nanmean(prf["f1"][has])) if has.any() else float("nan"),
        "balanced_accuracy": float(np.nanmean(prf["recall"][has])) if has.any() else float("nan"),
    }


def normalize_rows(cm: np.ndarray) -> np.ndarray:
    cm = np.asarray(cm, dtype=float)
    s = cm.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(s > 0, cm / np.where(s > 0, s, 1.0), 0.0)


# --------------------------------------------------------------------------- binario

def binary_counts(y_pos: np.ndarray, pred_pos: np.ndarray) -> tuple[int, int, int, int]:
    """(TP, FP, FN, TN)."""
    y = np.asarray(y_pos, dtype=bool)
    p = np.asarray(pred_pos, dtype=bool)
    return int((y & p).sum()), int((~y & p).sum()), int((y & ~p).sum()), int((~y & ~p).sum())


def binary_metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    n = tp + fp + fn + tn
    return {
        "sensibilidad": float(_safe_div(tp, tp + fn)),
        "especificidad": float(_safe_div(tn, tn + fp)),
        "tasa_fp": float(_safe_div(fp, fp + tn)),
        "tasa_falsa_alarma_fdr": float(_safe_div(fp, fp + tp)),
        "vpp": float(_safe_div(tp, tp + fp)),
        "vpn": float(_safe_div(tn, tn + fn)),
        "falsas_alarmas_por_100": float(_safe_div(100.0 * fp, n)),
        "no_detectados_por_100": float(_safe_div(100.0 * fn, n)),
    }


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Intervalo exacto (Clopper-Pearson) para una proporción k/n."""
    if n <= 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


# --------------------------------------------------------------------------- bootstrap

def bootstrap_ci(
    stat_fn: Callable[[np.ndarray], dict[str, float]],
    n: int,
    n_boot: int = 1000,
    seed: int = 0,
    groups: Sequence[str] | None = None,
    alpha: float = 0.05,
) -> dict[str, tuple[float, float]]:
    """IC percentil por bootstrap de cada métrica que devuelve ``stat_fn(indices)``.

    Si ``groups`` se da, se remuestrean GRUPOS completos (bootstrap por conglomerados), que es lo
    honesto cuando hay varias fotos de la misma hoja o ráfaga.
    """
    rng = np.random.default_rng(seed)
    if groups is not None:
        g = np.asarray(groups)
        uniq, inv = np.unique(g, return_inverse=True)
        members = [np.flatnonzero(inv == i) for i in range(len(uniq))]
    samples: dict[str, list[float]] = {}
    for _ in range(n_boot):
        if groups is not None:
            pick = rng.integers(0, len(members), size=len(members))
            idx = np.concatenate([members[i] for i in pick])
        else:
            idx = rng.integers(0, n, size=n)
        for key, val in stat_fn(idx).items():
            samples.setdefault(key, []).append(val)
    out: dict[str, tuple[float, float]] = {}
    for key, vals in samples.items():
        arr = np.asarray(vals, dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            out[key] = (float("nan"), float("nan"))
        else:
            out[key] = (float(np.quantile(arr, alpha / 2)), float(np.quantile(arr, 1 - alpha / 2)))
    return out


# --------------------------------------------------------------------------- curvas y umbral

def average_precision(y_pos: np.ndarray, scores: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score

    y = np.asarray(y_pos, dtype=bool)
    if y.all() or (~y).all():
        return float("nan")
    return float(average_precision_score(y, scores))


def roc_auc(y_pos: np.ndarray, scores: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y_pos, dtype=bool)
    if y.all() or (~y).all():
        return float("nan")
    return float(roc_auc_score(y, scores))


def pr_curve(y_pos: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from sklearn.metrics import precision_recall_curve

    return precision_recall_curve(np.asarray(y_pos, dtype=bool), np.asarray(scores, dtype=float))


def threshold_table(y_pos: np.ndarray, scores: np.ndarray) -> list[dict[str, float]]:
    """Métricas binarias para cada umbral candidato (valores únicos de puntaje, descendente)."""
    y = np.asarray(y_pos, dtype=bool)
    s = np.asarray(scores, dtype=float)
    rows = []
    for t in np.unique(s)[::-1]:
        tp, fp, fn, tn = binary_counts(y, s >= t)
        rows.append({"umbral": float(t), "tp": tp, "fp": fp, "fn": fn, "tn": tn, **binary_metrics(tp, fp, fn, tn)})
    return rows


def choose_threshold(
    y_pos: np.ndarray,
    scores: np.ndarray,
    target: float = 0.90,
    per_class_labels: Sequence[str] | None = None,
    midpoint: bool = True,
    tie_break: str = "sensibilidad",
) -> dict[str, object]:
    """Umbral que cumple sensibilidad de enfermedad (``score >= t``) >= ``target`` con el MÍNIMO de
    falsas alarmas.

    Entre los umbrales factibles se toma el número mínimo de falsos positivos. Si varios umbrales
    empatan en ese mínimo, ``tie_break="sensibilidad"`` (por defecto) elige el MÁS BAJO, que da la
    mayor sensibilidad sin añadir falsas alarmas en validación (más margen ante casos no
    detectados, el error caro); ``tie_break="umbral_alto"`` elige el más alto.
    Si ``per_class_labels`` se da (etiqueta verdadera de cada fila), se exige que la tasa de
    detección de CADA clase enferma cumpla el objetivo (criterio más estricto).
    Con ``midpoint`` el umbral final queda a mitad de camino entre el puntaje elegido y el
    siguiente puntaje más bajo observado: mismas cuentas en validación, algo de margen.
    """
    y = np.asarray(y_pos, dtype=bool)
    s = np.asarray(scores, dtype=float)
    if not y.any():
        raise ValueError("No hay positivos (enfermos) en el conjunto: no se puede fijar el umbral")
    if tie_break not in ("sensibilidad", "umbral_alto"):
        raise ValueError(f"tie_break inválido: {tie_break}")
    labels = np.asarray(per_class_labels) if per_class_labels is not None else None
    disease_classes = sorted(set(labels[y])) if labels is not None else []
    cands = np.unique(s)[::-1]
    feasible: list[tuple[float, int]] = []  # (umbral, fp)
    for t in cands:
        pred = s >= t
        ok = pred[y].mean() >= target - 1e-12
        if ok and labels is not None:
            ok = all(pred[labels == c].mean() >= target - 1e-12 for c in disease_classes)
        if ok:
            feasible.append((float(t), int((pred & ~y).sum())))
    if not feasible:  # el mínimo puntaje siempre detecta todo; salvaguarda numérica
        feasible = [(float(cands[-1]), int((~y).sum()))]
    min_fp = min(fp for _, fp in feasible)
    tied = [t for t, fp in feasible if fp == min_fp]
    chosen = min(tied) if tie_break == "sensibilidad" else max(tied)
    final = chosen
    if midpoint:
        lower = s[s < chosen]
        if len(lower):
            final = float((chosen + lower.max()) / 2.0)
    tp, fp, fn, tn = binary_counts(y, s >= final)
    res: dict[str, object] = {
        "umbral": final,
        "umbral_puntaje_observado": chosen,
        "desempate": tie_break,
        "n_umbrales_empatados": len(tied),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        **binary_metrics(tp, fp, fn, tn),
    }
    if labels is not None:
        res["deteccion_por_clase"] = {
            str(c): {"detectados": int((s[labels == c] >= final).sum()), "n": int((labels == c).sum())}
            for c in disease_classes
        }
    return res
