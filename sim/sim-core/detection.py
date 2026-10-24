"""Modelo de detección: tasas medidas del clasificador, factor de altura, hoja mojada y confirmación humana.

Los valores vienen de config/detector.yaml (medidos por el equipo en el test congelado de DrBerry). El
clasificador real no tiene clases de Botrytis, antracnosis ni roya: el YAML decide si se tratan como clases
futuras con desempeño supuesto o como no detectables por cámara (ver visual_classes_mode).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


# Plant visual/health states (uint8 codes)
STATE_HEALTHY = 0
STATE_AT_RISK = 1
STATE_INFECTED_ASYMP = 2
STATE_SYMPTOMATIC = 3
STATE_ALERT_PENDING = 4
STATE_CONFIRMED = 5
STATE_TREATED = 6
STATE_FALSE_ALARM = 7


@dataclass
class DetectionEvent:
    bed: int
    plant: int
    true_positive: bool
    false_alarm: bool
    visual_class: str
    day: float


@dataclass
class PendingAlert:
    bed: int
    plant: int
    created_s: float
    delay_s: float  # operator decision time once the alert reaches the agronomist
    is_true_positive: bool
    confirm: bool
    visual_class: str
    delivered_s: float | None = None  # when the record reached the database
    deliver_at_s: float | None = None  # scheduled delivery (manual reports)


CLASS_LABELS = {
    "healthy": "hoja sana",
    "oidio": "oídio",
    "alternaria": "alternaria",
    "heliothis": "Heliothis",
    # Clases futuras (no existen en el clasificador real; ver detector.yaml)
    "botrytis": "Botrytis",
    "antracnosis": "antracnosis",
    "roya": "roya",
}

# Clases que el clasificador real entrega hoy (se usan para rotular las falsas alarmas)
DISEASE_CLASSES = ("oidio", "alternaria", "heliothis")


def classifier_score(
    rng: np.random.Generator, raise_alert: bool, threshold: float
) -> float:
    """Displayed confidence consistent with the decision: above threshold iff alert."""
    if raise_alert:
        return float(rng.uniform(threshold, 0.98))
    return float(rng.uniform(0.02, threshold))


def active_scenario(det_cfg: dict[str, Any]) -> dict[str, float]:
    """Escenario activo del clasificador (measured | pessimistic) con sensibilidad y tasa de falsas alarmas."""
    clf = det_cfg.get("classifier", {}) or {}
    name = str(clf.get("scenario", "measured"))
    scenarios = clf.get("scenarios", {}) or {}
    if name not in scenarios:
        raise ValueError(f"escenario de clasificador desconocido: {name}")
    sc = scenarios[name]
    return {"sensitivity": float(sc["sensitivity"]), "false_positive_rate": float(sc["false_positive_rate"])}


def class_recall(vclass: str, det_cfg: dict[str, Any]) -> float:
    """P(alerta | planta con síntomas de la clase visual vclass), antes de altura, niebla y plataforma."""
    clf = det_cfg.get("classifier", {}) or {}
    sc = active_scenario(det_cfg)
    measured = clf.get("measured_recall", {}) or {}
    if vclass in measured:
        ref = float(((clf.get("scenarios", {}) or {}).get("measured", {}) or {}).get("sensitivity", sc["sensitivity"]))
        scale = sc["sensitivity"] / ref if ref > 0 else 1.0
        return float(np.clip(float(measured[vclass]) * scale, 0.0, 1.0))
    if vclass in (det_cfg.get("future_classes", []) or []):
        if str(det_cfg.get("visual_classes_mode", "future")) == "current":
            return 0.0  # el clasificador de hoy no tiene esta clase
        return sc["sensitivity"]  # SUPUESTO: clase futura con la sensibilidad global del escenario
    return 0.0


def false_positive_rate(det_cfg: dict[str, Any], wet: bool, h_factor: float) -> float:
    """Tasa de falsas alarmas por planta sana capturada: medida, con hoja mojada y factor de altura."""
    sc = active_scenario(det_cfg)
    fpr = sc["false_positive_rate"]
    if wet:
        cap = float(det_cfg.get("wet_leaf_fpr_cap", 1.0))
        fpr = min(fpr * float(det_cfg.get("wet_leaf_fpr_multiplier", 1.0)), max(cap, fpr))
    return float(np.clip(fpr * float(h_factor), 0.0, 1.0))


def height_sensitivity_factor(
    camera_height_m: float,
    bush_height_m: float,
    sees_full_bush: bool,
    cfg: dict[str, Any],
) -> float:
    if sees_full_bush:
        return 1.0
    hp = cfg.get("height_penalty", {})
    if not hp.get("enabled", True):
        return 1.0
    min_factor = float(hp.get("min_factor", 0.35))
    if bush_height_m <= 0:
        return 1.0
    uncovered = max(0.0, bush_height_m - camera_height_m) / bush_height_m
    return float(np.clip(1.0 - uncovered, min_factor, 1.0))


def visual_class_for_disease(disease: str, det_cfg: dict[str, Any]) -> str:
    mapping = det_cfg.get("disease_to_visual", {}) or {}
    return str(mapping.get(disease, disease))


def detect_plant(
    rng: np.random.Generator,
    state: int,
    disease: str,
    bush_height_m: float,
    camera_height_m: float,
    sees_full_bush: bool,
    wet_day: bool,
    fog_penalty: float,
    base_sensitivity: float,
    det_cfg: dict[str, Any],
    human_review: dict[str, Any] | None = None,
) -> tuple[bool, bool, str]:
    """
    Returns (raise_alert, is_true_positive, visual_class).
    Only symptomatic plants can be true positives.
    Healthy plants may trigger false alarms. `wet_day` = leaf wet at the moment of the capture.
    """
    # Human-only path (REF / B review)
    if human_review and human_review.get("enabled"):
        return _human_detect(
            rng, state, disease, bush_height_m, wet_day, human_review, det_cfg, base_sensitivity
        )

    h_factor = height_sensitivity_factor(camera_height_m, bush_height_m, sees_full_bush, det_cfg)
    fog = float(fog_penalty) if fog_penalty else 1.0

    if state == STATE_SYMPTOMATIC:
        vclass = visual_class_for_disease(disease, det_cfg)
        p = class_recall(vclass, det_cfg) * h_factor * fog * float(base_sensitivity)
        p = float(np.clip(p, 0.0, 1.0))
        hit = bool(rng.random() < p)
        return hit, hit, vclass

    if state in (STATE_HEALTHY, STATE_AT_RISK, STATE_INFECTED_ASYMP):
        fa = bool(rng.random() < false_positive_rate(det_cfg, wet_day, h_factor))
        return fa, False, "healthy"

    return False, False, "healthy"


def _human_detect(
    rng: np.random.Generator,
    state: int,
    disease: str,
    bush_height_m: float,
    wet_day: bool,
    human_review: dict[str, Any],
    det_cfg: dict[str, Any],
    base_sensitivity: float,
) -> tuple[bool, bool, str]:
    sens_small = float(human_review.get("sensitivity_small", 0.5))
    sens_under = float(human_review.get("sensitivity_underside", 0.4))
    # Combine: taller bushes harder underside
    under_factor = float(np.clip(1.0 - 0.3 * (bush_height_m - 1.0), 0.5, 1.0))
    if state == STATE_SYMPTOMATIC:
        p = sens_small * sens_under * under_factor * float(base_sensitivity or 1.0)
        p = float(np.clip(p, 0.0, 1.0))
        hit = bool(rng.random() < p)
        # una persona reconoce la enfermedad, no una clase del clasificador
        return hit, hit, visual_class_for_disease(disease, det_cfg)
    if state in (STATE_HEALTHY, STATE_AT_RISK):
        fpr = float(det_cfg.get("human_false_positive_rate", 0.03))
        if wet_day:
            fpr *= float(det_cfg.get("human_wet_fpr_multiplier", 1.5))
        fa = bool(rng.random() < fpr)
        return fa, False, "healthy"
    return False, False, "healthy"


def schedule_operator_resolution(
    rng: np.random.Generator,
    created_day: float,
    is_tp: bool,
    det_cfg: dict[str, Any],
) -> tuple[float, bool]:
    """
    Returns (resolve_day, final_confirmed_as_disease).
    Operator can err both ways.
    """
    op = det_cfg.get("operator", {})
    dmin = float(op.get("delay_days_min", 0.5))
    dmax = float(op.get("delay_days_max", 2.0))
    delay = float(rng.uniform(dmin, dmax))
    resolve_day = created_day + delay
    if is_tp:
        # wrongly discard
        err = float(op.get("confirm_error_rate", 0.05))
        confirmed = not (rng.random() < err)
    else:
        # wrongly confirm FA
        err = float(op.get("discard_error_rate", 0.10))
        confirmed = bool(rng.random() < err)
    return resolve_day, confirmed
