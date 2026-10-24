"""Modelos de riesgo portados de datos/riesgo/risk.py: casos de libro y coeficientes de config/risk.yaml.

Los valores esperados son los de BerryGoodIdea_handoff/datos/riesgo/tests/test_risk.py (grupos A-C) y
del README de esa carpeta (§4.1). Si alguien cambia un coeficiente del YAML, estas pruebas fallan.
"""
from __future__ import annotations

import math

import pytest

import risk as r
from config_loader import load_all_config

RISK = load_all_config()["risk"]
ANTH = RISK["anthracnose"]
BOT = RISK["botrytis"]["coefficients"]
GIM = RISK["rust"]["gim"]


# ---------------------------------------------------------------------------------------------------------
# Coeficientes del YAML = publicados (y sin restos de Miles 2013 ni del juego "fruit_graymold")
# ---------------------------------------------------------------------------------------------------------
def test_yaml_coefficients_are_the_published_ones() -> None:
    assert ANTH["model"] == "envelope"
    assert ANTH["wilson1990"] == r.WILSON_1990
    assert [tuple(a) for a in ANTH["gillett_schilder2009"]["w50_anchors"]] == list(r.GILLETT_SCHILDER_2009_W50)
    assert tuple(ANTH["gillett_schilder2009"]["zero_slope_temps_c"]) == r.GILLETT_SCHILDER_ZERO_T
    assert BOT == r.BULGER_1987
    assert GIM == r.GIM_RUST


def test_no_unverified_coefficients_left() -> None:
    text = str(RISK)
    assert "mature_fruit_TW" not in text and "x0" not in ANTH  # coeficientes "Miles 2013" sin fuente
    assert "fruit_graymold" not in text and "petal_necrosis" not in text
    assert not hasattr(r, "miles2013_gaussian")


def test_published_thresholds() -> None:
    assert tuple(ANTH["thresholds"]) == (0.15, 0.50)              # NCSU FLSAS; MacKenzie y Peres 2012a
    assert tuple(RISK["botrytis"]["thresholds"]) == (0.50, 0.70)  # NCSU FLSAS; MacKenzie y Peres 2012b
    assert tuple(RISK["rust"]["thresholds"]) == (0.20, 0.50)      # SUPUESTO del equipo
    assert r.classify(0.49, "botrytis", RISK) == "bajo"
    assert r.classify(0.50, "botrytis", RISK) == "medio"
    assert r.classify(0.70, "botrytis", RISK) == "alto"
    assert r.classify(0.15, "anthracnose", RISK) == "medio"


# ---------------------------------------------------------------------------------------------------------
# A. Casos de libro (mismos valores que datos/riesgo/tests)
# ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("lwd,expected", [(7.0, 0.15), (13.1, 0.50)])
def test_wilson_ncsu_graph_26_6C(lwd: float, expected: float) -> None:
    # NCSU IPM, "Strawberry Fruit Anthracnose leaf wetness graph" a 26,6 °C
    assert r.wilson1990_anthracnose(lwd, 26.6, ANTH["wilson1990"]) == pytest.approx(expected, abs=0.005)


@pytest.mark.parametrize("lwd,expected", [(13.8, 0.50), (16.5, 0.70)])
def test_bulger_ncsu_graph_20_5C(lwd: float, expected: float) -> None:
    # NCSU IPM, "Strawberry fruit Grey Mold Rot leaf wetness graph" a 20,5 °C
    assert r.bulger1987_logit(lwd, 20.5, BOT) == pytest.approx(expected, abs=0.005)


def test_optimum_temperatures_ncsu() -> None:
    _, t_opt = r.wilson_critical_temps(ANTH["wilson1990"])
    assert t_opt == pytest.approx(26.6, abs=0.15)
    assert r.bulger_optimum_temp(BOT) == pytest.approx(20.5, abs=0.15)


def test_wilson_intercept() -> None:
    assert r.wilson1990_anthracnose(1e-9, 20) == pytest.approx(0.0241, abs=0.001)


def test_wilson_cold_clip_reproduces_ncsu_curve() -> None:
    assert r.wilson1990_anthracnose(20.9, 0.0) == pytest.approx(0.06, abs=0.01)
    assert r.wilson1990_anthracnose(13.1, 0.0) == pytest.approx(0.045, abs=0.01)
    assert r.wilson1990_anthracnose(7.0, 0.0) == pytest.approx(0.035, abs=0.01)
    assert r.wilson1990_anthracnose(20.9, 0.0) == pytest.approx(r.wilson1990_anthracnose(20.9, 9.0))
    t_gmin, _ = r.wilson_critical_temps()
    assert t_gmin == pytest.approx(9.33, abs=0.01)


def test_gim_ncsu_note() -> None:
    assert r.gim_index_from_cycles(1.0) == pytest.approx(0.20, abs=0.01)
    assert r.gim_index_from_cycles(2.0) == pytest.approx(0.68, abs=0.01)
    assert r.gim_temperature_factor(GIM["t_opt_c"], GIM) == pytest.approx(1.0)


def _w50(f, t: float) -> float:
    return next(w / 10 for w in range(1, 1000) if f(w / 10, t) >= 0.5)


@pytest.mark.parametrize("t,lo,hi", [(10, 36, 48), (15, 23.9, 24.1), (20, 12, 18), (25, 12, 18), (30, 18, 24)])
def test_blueberry_approx_w50_inside_published_ranges(t: float, lo: float, hi: float) -> None:
    # Gillett y Schilder 2009: aumento considerable tras 36-48 h a 10 °C, 24 h a 15, 12-18 h a 20-25, 18-24 h a 30
    f = lambda w, tt: r.gillett_schilder2009_approx(w, tt, ANTH["gillett_schilder2009"])  # noqa: E731
    assert lo <= _w50(f, t) <= hi


@pytest.mark.parametrize("t", [10, 15, 20, 25, 30])
def test_blueberry_approx_low_at_6h(t: float) -> None:
    assert r.gillett_schilder2009_approx(6, t, ANTH["gillett_schilder2009"]) < 0.15


def test_wilson_matches_blueberry_at_20_25C() -> None:
    for t in (20, 25):
        assert 12 <= _w50(r.wilson1990_anthracnose, t) <= 18


def test_wilson_underestimates_cold_blueberry_envelope_fixes_it() -> None:
    assert r.wilson1990_anthracnose(24, 15) < 0.5
    assert r.anthracnose_index(24, 15, ANTH) >= 0.5


# ---------------------------------------------------------------------------------------------------------
# B-C. Forma y límites
# ---------------------------------------------------------------------------------------------------------
LWDS = [0.5 * i for i in range(1, 97)]


@pytest.mark.parametrize("t", [5, 10, 15, 20, 25, 30])
def test_indices_monotone_in_wetness(t: float) -> None:
    for f in (lambda w: r.anthracnose_index(w, t, ANTH), lambda w: r.bulger1987_logit(w, t, BOT)):
        vals = [f(w) for w in LWDS]
        assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))
    if t >= 10:
        vals = [r.rust_gim_index(w, t, GIM) for w in LWDS]
        assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))


def test_envelope_is_max() -> None:
    for t in (8, 12, 18, 24, 29):
        for w in (6, 12, 24, 36):
            assert r.anthracnose_index(w, t, ANTH) == max(
                r.wilson1990_anthracnose(w, t), r.gillett_schilder2009_approx(w, t))


@pytest.mark.parametrize("t", [-5, 0, 10, 20, 30, 45])
def test_no_wetness_is_zero(t: float) -> None:
    out = r.daily_risks(0.0, t, t, RISK)
    assert out == {"anthracnose": 0.0, "botrytis": 0.0, "rust": 0.0}
    assert r.combined_risk(out) == 0.0


def test_missing_temperature_is_zero() -> None:
    assert r.daily_risks(12.0, math.nan, 15.0, RISK) == {"anthracnose": 0.0, "botrytis": 0.0, "rust": 0.0}


def test_indices_in_unit_interval() -> None:
    for t in range(-5, 46, 3):
        for w in (1, 6, 12, 24, 48, 120):
            for v in r.daily_risks(w, t, t, RISK).values():
                assert 0.0 <= v <= 1.0


def test_thermal_extremes() -> None:
    assert r.rust_gim_index(48, 5, GIM) == 0.0
    assert r.rust_gim_index(48, 35, GIM) == 0.0
    assert r.bulger1987_logit(24, 40, BOT) < 0.01
    assert r.wilson1990_anthracnose(24, 42) < 0.01
    assert r.gillett_schilder2009_approx(48, 36) == pytest.approx(0.0241, abs=0.001)


def test_gim_lwd_max() -> None:
    t_cold = 8.5
    assert GIM["lwd_min_h"] / r.gim_temperature_factor(t_cold, GIM) > GIM["lwd_max_h"]
    assert r.rust_gim_index(200, t_cold, GIM) == 0.0


def test_bulger_validity_range() -> None:
    assert r.bulger_out_of_range(40, 20, RISK["botrytis"])   # > 32 h
    assert r.bulger_out_of_range(10, 2, RISK["botrytis"])    # < 5 °C
    assert not r.bulger_out_of_range(10, 20, RISK["botrytis"])


# ---------------------------------------------------------------------------------------------------------
# Interfaz que usa el motor
# ---------------------------------------------------------------------------------------------------------
def test_daily_risks_interface_uses_yaml_models() -> None:
    out = r.daily_risks(14.0, 12.0, 15.0, RISK)
    assert set(out) == {"anthracnose", "botrytis", "rust"}
    assert out["anthracnose"] == pytest.approx(r.anthracnose_index(14.0, 12.0, ANTH))
    assert out["botrytis"] == pytest.approx(r.bulger1987_logit(14.0, 12.0, BOT))
    assert out["rust"] == pytest.approx(r.rust_gim_index(14.0, 12.0, GIM))
    # Noche fría y mojada típica de la Sabana: la Botrytis domina el máximo combinado
    assert r.combined_risk(out) == out["botrytis"]
    assert r.combined_risk(out | {"bandera": 5.0}) == out["botrytis"]  # solo cuenta enfermedades
