"""Métricas en casos conocidos, bootstrap, Clopper-Pearson, selección de umbral y reglas de decisión."""
from __future__ import annotations

import numpy as np
import pytest

import metrics as M
from common import decide, disease_scores


def test_confusion_and_prf_known_case():
    classes = ["a", "b", "c"]
    y_true = ["a", "a", "a", "b", "b", "c"]
    y_pred = ["a", "a", "b", "b", "c", "c"]
    cm = M.confusion_matrix(y_true, y_pred, classes)
    assert cm.tolist() == [[2, 1, 0], [0, 1, 1], [0, 0, 1]]
    prf = M.per_class_prf(cm)
    np.testing.assert_allclose(prf["precision"], [1.0, 0.5, 0.5])
    np.testing.assert_allclose(prf["recall"], [2 / 3, 0.5, 1.0])
    np.testing.assert_allclose(prf["f1"], [0.8, 0.5, 2 / 3])
    assert prf["support"].tolist() == [3, 2, 1]
    s = M.multiclass_summary(cm)
    assert s["accuracy"] == pytest.approx(4 / 6)
    assert s["macro_f1"] == pytest.approx((0.8 + 0.5 + 2 / 3) / 3)
    assert s["balanced_accuracy"] == pytest.approx((2 / 3 + 0.5 + 1.0) / 3)
    np.testing.assert_allclose(M.normalize_rows(cm).sum(axis=1), [1, 1, 1])


def test_prf_absent_class_is_nan_not_crash():
    cm = M.confusion_matrix(["a", "a"], ["a", "a"], ["a", "b"])
    prf = M.per_class_prf(cm)
    assert np.isnan(prf["recall"][1]) and np.isnan(prf["precision"][1]) and np.isnan(prf["f1"][1])
    assert M.multiclass_summary(cm)["macro_f1"] == 1.0


def test_binary_metrics_known_case():
    # 10 enfermos (8 detectados), 5 sanas (1 falsa alarma)
    y = np.array([1] * 10 + [0] * 5, dtype=bool)
    p = np.array([1] * 8 + [0] * 2 + [1] + [0] * 4, dtype=bool)
    tp, fp, fn, tn = M.binary_counts(y, p)
    assert (tp, fp, fn, tn) == (8, 1, 2, 4)
    b = M.binary_metrics(tp, fp, fn, tn)
    assert b["sensibilidad"] == pytest.approx(0.8)
    assert b["especificidad"] == pytest.approx(0.8)
    assert b["tasa_fp"] == pytest.approx(0.2)
    assert b["tasa_falsa_alarma_fdr"] == pytest.approx(1 / 9)
    assert b["falsas_alarmas_por_100"] == pytest.approx(100 / 15)


def test_clopper_pearson_known_values():
    lo, hi = M.clopper_pearson(8, 8)
    assert lo == pytest.approx(0.025 ** (1 / 8), abs=1e-6)  # ~0.631, el valor citado en la ficha DrBerry
    assert hi == 1.0
    lo, hi = M.clopper_pearson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 10), abs=1e-6)
    lo, hi = M.clopper_pearson(5, 10)
    assert lo < 0.5 < hi


def test_bootstrap_deterministic_and_contains_point():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200).astype(bool)
    p = np.where(rng.random(200) < 0.8, y, ~y)

    def stat(idx):
        tp, fp, fn, tn = M.binary_counts(y[idx], p[idx])
        return {"acc": (tp + tn) / len(idx), "sens": tp / max(tp + fn, 1)}

    ci1 = M.bootstrap_ci(stat, 200, n_boot=1000, seed=3)
    ci2 = M.bootstrap_ci(stat, 200, n_boot=1000, seed=3)
    assert ci1 == ci2
    point = stat(np.arange(200))
    for k in ("acc", "sens"):
        assert ci1[k][0] <= point[k] <= ci1[k][1]
        assert ci1[k][1] - ci1[k][0] < 0.2
    groups = [f"g{i // 5}" for i in range(200)]
    ci_g = M.bootstrap_ci(stat, 200, n_boot=300, seed=3, groups=groups)
    assert ci_g["acc"][0] <= point["acc"] <= ci_g["acc"][1]


def test_choose_threshold_meets_target_with_min_false_alarms():
    pos = np.array([0.95, 0.9, 0.85, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2])
    neg = np.array([0.75, 0.45, 0.35, 0.1, 0.05])
    s = np.concatenate([pos, neg])
    y = np.array([True] * 10 + [False] * 5)
    # umbral_alto: el más alto que cumple 9/10 -> 0.3 (3 falsas alarmas)
    r = M.choose_threshold(y, s, target=0.9, midpoint=False, tie_break="umbral_alto")
    assert r["umbral"] == pytest.approx(0.3)
    assert r["sensibilidad"] == pytest.approx(0.9)
    assert (r["fp"], r["tn"]) == (3, 2)
    assert ((pos >= 0.4).mean()) < 0.9  # el siguiente umbral más alto ya no cumple
    # por defecto (sensibilidad): 0.2 tiene las MISMAS 3 falsas alarmas y detecta 10/10 -> se prefiere
    r_def = M.choose_threshold(y, s, target=0.9, midpoint=False)
    assert r_def["umbral"] == pytest.approx(0.2)
    assert (r_def["tp"], r_def["fp"]) == (10, 3)
    assert r_def["n_umbrales_empatados"] == 2
    # punto medio: entre 0.2 y el siguiente puntaje observado (0.1), mismas cuentas
    r_mid = M.choose_threshold(y, s, target=0.9)
    assert r_mid["umbral"] == pytest.approx(0.15)
    assert (r_mid["tp"], r_mid["fp"]) == (r_def["tp"], r_def["fp"])
    r_mid_alto = M.choose_threshold(y, s, target=0.9, tie_break="umbral_alto")
    assert r_mid_alto["umbral"] == pytest.approx(0.25) and r_mid_alto["fp"] == 3
    # objetivo 1.0 -> hay que bajar hasta el positivo más bajo
    assert M.choose_threshold(y, s, target=1.0, midpoint=False)["umbral"] == pytest.approx(0.2)


def test_choose_threshold_never_adds_false_alarms_for_sensitivity():
    # bajar de 0.6 a 0.3 cuesta 1 falsa alarma (la sana de 0.5): no se baja
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.3, 0.5, 0.1])
    y = np.array([True, True, True, True, True, False, False])
    r = M.choose_threshold(y, s, target=0.8, midpoint=False)
    assert r["umbral"] == pytest.approx(0.6) and r["fp"] == 0 and r["tp"] == 4


def test_choose_threshold_per_class_is_stricter():
    labels = ["x"] * 5 + ["z"] * 5 + ["sana"] * 4
    s = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.2, 0.1, 0.1, 0.1, 0.1])
    y = np.array([lab != "sana" for lab in labels])
    g = M.choose_threshold(y, s, 0.9, midpoint=False, tie_break="umbral_alto")
    pc = M.choose_threshold(y, s, 0.9, per_class_labels=labels, midpoint=False, tie_break="umbral_alto")
    assert g["umbral"] == pytest.approx(0.9)  # 9/10 global
    assert pc["umbral"] == pytest.approx(0.2)  # la clase z necesita 5/5 >= 0.9 de 5
    assert pc["deteccion_por_clase"]["z"] == {"detectados": 5, "n": 5}
    # con el desempate por sensibilidad, el global también baja a 0.2 (0 falsas alarmas en ambos)
    assert M.choose_threshold(y, s, 0.9, midpoint=False)["umbral"] == pytest.approx(0.2)


def test_choose_threshold_needs_positives():
    with pytest.raises(ValueError):
        M.choose_threshold(np.zeros(4, bool), np.linspace(0, 1, 4))


def test_decide_rules():
    classes = ["alternaria", "oidio", "sana"]
    probs = np.array([[0.2, 0.1, 0.7], [0.6, 0.3, 0.1], [0.15, 0.25, 0.6]])
    assert decide(probs, classes, "sana", None) == ["sana", "alternaria", "sana"]
    np.testing.assert_allclose(disease_scores(probs, classes, "sana"), [0.3, 0.9, 0.4])
    # umbral 0.35: la tercera (p_enf 0.4) pasa a sospecha y se decide la enfermedad más probable (oidio)
    assert decide(probs, classes, "sana", 0.35) == ["sana", "alternaria", "oidio"]
    with pytest.raises(ValueError):
        decide(probs, classes, "healthy", 0.5)
