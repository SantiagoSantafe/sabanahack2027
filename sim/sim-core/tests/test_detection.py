"""Detector: valores medidos (datos/resultados/detector.yaml), mapeo honesto de clases y hoja mojada."""
from __future__ import annotations

import copy

import numpy as np
import pytest

import detection as d
from config_loader import load_all_config

DET = load_all_config()["detector"]


def test_measured_values_from_team_detector() -> None:
    sc = DET["classifier"]["scenarios"]
    # recomendacion_para_simulacion de datos/resultados/detector.yaml
    assert sc["measured"]["sensitivity"] == pytest.approx(0.7963)          # 43/54
    assert 1 - sc["measured"]["false_positive_rate"] == pytest.approx(0.6429, abs=1e-4)  # especificidad 9/14
    assert sc["pessimistic"]["sensitivity"] == pytest.approx(0.6481)       # estrés combinado 35/54
    assert 1 - sc["pessimistic"]["false_positive_rate"] == pytest.approx(0.357, abs=1e-3)
    assert DET["classifier"]["measured_recall"] == {"oidio": 0.9545, "heliothis": 1.0, "alternaria": 0.2857}
    assert DET["decision"]["score_threshold"] == pytest.approx(0.7373)
    assert DET["classifier"]["scenario"] == "measured"


def test_real_classifier_has_no_class_for_simulated_diseases() -> None:
    real = set(DET["classes"])
    for disease in ("botrytis", "anthracnose", "rust"):
        vclass = d.visual_class_for_disease(disease, DET)
        assert vclass not in real
        assert vclass in DET["future_classes"]


def test_future_mode_uses_scenario_sensitivity_and_current_mode_sees_nothing() -> None:
    assert DET["visual_classes_mode"] == "future"
    for vclass in DET["future_classes"]:
        assert d.class_recall(vclass, DET) == pytest.approx(0.7963)
    cur = copy.deepcopy(DET)
    cur["visual_classes_mode"] = "current"
    for vclass in DET["future_classes"]:
        assert d.class_recall(vclass, cur) == 0.0
    # las clases reales conservan su recall medido en cualquier modo
    assert d.class_recall("alternaria", cur) == pytest.approx(0.2857)


def test_pessimistic_scenario() -> None:
    pes = copy.deepcopy(DET)
    pes["classifier"]["scenario"] = "pessimistic"
    assert d.class_recall("botrytis", pes) == pytest.approx(0.6481)
    assert d.class_recall("oidio", pes) == pytest.approx(0.9545 * 0.6481 / 0.7963)
    assert d.false_positive_rate(pes, wet=False, h_factor=1.0) == pytest.approx(0.6429)


def test_wet_leaf_raises_false_alarms_up_to_pessimistic_cap() -> None:
    dry = d.false_positive_rate(DET, wet=False, h_factor=1.0)
    wet = d.false_positive_rate(DET, wet=True, h_factor=1.0)
    assert dry == pytest.approx(0.3571)
    assert dry < wet <= DET["wet_leaf_fpr_cap"] + 1e-12
    # cámara baja: menos copa visible -> menos falsas alarmas también
    assert d.false_positive_rate(DET, wet=False, h_factor=0.35) == pytest.approx(0.3571 * 0.35)


def test_symptomatic_hit_rate_matches_measured_sensitivity() -> None:
    rng = np.random.default_rng(0)
    n = 20000
    hits = sum(d.detect_plant(rng, d.STATE_SYMPTOMATIC, "botrytis", 1.1, 1.35, True, False, 1.0, 1.0, DET)[0]
               for _ in range(n))
    assert hits / n == pytest.approx(0.7963, abs=0.015)  # sin el viejo "empuje" de +0,03


def test_healthy_false_alarm_rate_matches_measured() -> None:
    rng = np.random.default_rng(1)
    n = 20000
    fas = sum(d.detect_plant(rng, d.STATE_HEALTHY, "", 1.1, 1.35, True, False, 1.0, 1.0, DET)[0] for _ in range(n))
    assert fas / n == pytest.approx(0.3571, abs=0.015)


def test_human_reports_the_disease_not_a_classifier_class() -> None:
    rng = np.random.default_rng(2)
    hr = {"enabled": True, "sensitivity_small": 1.0, "sensitivity_underside": 1.0}
    hit, tp, vclass = d.detect_plant(rng, d.STATE_SYMPTOMATIC, "botrytis", 1.0, 1.6, False, False, 1.0, 1.0, DET, hr)
    assert hit and tp and vclass == "botrytis"
    assert d.CLASS_LABELS[vclass] == "Botrytis"
