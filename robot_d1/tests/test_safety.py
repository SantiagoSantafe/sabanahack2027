"""Pruebas de las funciones puras de seguridad (d1/safety.py)."""

import math

import pytest

from d1.safety import (Accel, Limits, RateLimiter3, StopState, clamp_unit, clip_to_sdk, is_fresh,
                       rate_limit, sanitize_hold, scale_axes, sdk_clip)


# ------------------------------------------------------------------ ejes
@pytest.mark.parametrize("raw,expected", [
    (0.5, 0.5), (2.0, 1.0), (-7, -1.0), (None, 0.0), ("x", 0.0), (True, 0.0),
    (float("nan"), 0.0), (float("inf"), 0.0), ("0.25", 0.25),
])
def test_clamp_unit(raw, expected):
    assert clamp_unit(raw) == expected


def test_scale_axes_default_limits():
    lim = Limits()
    assert scale_axes(1, 0, 0, False, lim) == (0.4, 0.0, 0.0)
    assert scale_axes(1, 0, 0, True, lim) == (0.8, 0.0, 0.0)          # fast solo afecta a vx
    assert scale_axes(0, 1, -1, True, lim) == (0.0, 0.25, -0.6)
    assert scale_axes(-1, 0, 0, False, lim, scale=0.5) == (-0.2, 0.0, 0.0)


def test_scale_axes_fast_must_be_true_bool():
    assert scale_axes(1, 0, 0, 1, Limits())[0] == pytest.approx(0.4)   # 1 no es True


def test_scale_axes_caps_absurd_limits_to_sdk():
    v = scale_axes(1, 1, 1, True, Limits(vx_max=10, vx_fast=10, vy_max=10, wz_max=10))
    assert v == (3.0, 1.0, 3.0)


# ------------------------------------------------------------------ recorte SDK
def test_sdk_clip_deadzone_and_max():
    assert sdk_clip(0.04, 0.05, 3.0) == 0.0          # debajo del mínimo -> 0
    assert sdk_clip(-0.049, 0.05, 3.0) == 0.0
    assert sdk_clip(0.05, 0.05, 3.0) == 0.05         # en el borde vale
    assert sdk_clip(-5.0, 0.05, 3.0) == -3.0         # encima del máximo -> máximo con signo
    assert sdk_clip(float("nan"), 0.05, 3.0) == 0.0


def test_clip_to_sdk_ranges_of_guide():
    # vx 0.05-3, vy 0.1-1.0, wz 0.02-3.0 (guía 4.1.6)
    assert clip_to_sdk(0.04, 0.09, 0.019) == (0.0, 0.0, 0.0)
    assert clip_to_sdk(0.3, 0.1, 0.02) == (0.3, 0.1, 0.02)
    assert clip_to_sdk(9, -9, 9) == (3.0, -1.0, 3.0)


def test_low_speed_level_strafe_still_reaches_sdk_min():
    # Nivel 0.4 del teclado: vy = 0.25*0.4 = 0.1 (borde) => no debe caer en la zona muerta.
    vx, vy, wz = scale_axes(0, 1, 0, False, Limits(), scale=0.4)
    assert clip_to_sdk(vx, vy, wz)[1] == pytest.approx(0.1)


# ------------------------------------------------------------------ rampa
def test_rate_limit_accel_and_decel():
    v = rate_limit(0.0, 0.4, 0.05, accel=0.8, decel=1.6)
    assert v == pytest.approx(0.04)
    v = rate_limit(0.4, 0.0, 0.05, accel=0.8, decel=1.6)
    assert v == pytest.approx(0.32)                  # frena el doble de rápido
    assert rate_limit(0.39, 0.4, 0.05, 0.8, 1.6) == pytest.approx(0.4)   # no se pasa del objetivo
    assert rate_limit(0.3, 0.3, 0.05, 0.8, 1.6) == 0.3
    assert rate_limit(0.3, 0.0, 0.0, 0.8, 1.6) == 0.3    # dt=0 no cambia nada


def test_rate_limit_sign_change_stops_at_zero_first():
    assert rate_limit(0.05, -0.4, 0.05, 0.8, 1.6) == 0.0
    assert rate_limit(0.4, -0.4, 0.05, 0.8, 1.6) == pytest.approx(0.32)


def test_rate_limiter3_reaches_target_and_resets():
    rl = RateLimiter3(Accel(ax=0.8, ay=0.6, aw=1.5, decel_factor=2.0))
    for _ in range(20):
        v = rl.step((0.4, 0.25, 0.6), 0.05)
    assert v == pytest.approx((0.4, 0.25, 0.6))
    rl.reset()
    assert rl.value == (0.0, 0.0, 0.0)


# ------------------------------------------------------------------ vigencia
def test_is_fresh_ttl_0_3():
    assert is_fresh(10.0, 10.29)
    assert not is_fresh(10.0, 10.30)
    assert not is_fresh(None, 10.0)
    assert not is_fresh(10.0, 9.0)                    # del futuro lejano: no


# ------------------------------------------------------------------ estop y detección
def test_estop_blocks_until_resume_and_local_wins():
    st = StopState()
    assert st.estop("local") == [("estop", "parada de emergencia (local)")]
    assert st.estop("sim") == []                      # ya estaba en estop: sin evento duplicado
    ok, ev = st.resume("sim")
    assert not ok and ev == [] and st.estopped        # la sim no levanta un estop local
    ok, ev = st.resume("local")
    assert ok and ev[0][0] == "resume" and not st.estopped


def test_estop_from_sim_can_be_resumed_by_sim():
    st = StopState()
    st.estop("sim")
    ok, ev = st.resume("sim")
    assert ok and not st.estopped


def test_detection_hold_and_extension():
    st = StopState()
    ev = st.detection_stop(100.0, 4, "oidio", 0.93)
    assert ev and ev[0][0] == "detection_hold_start"
    assert st.detection_active(103.9)
    assert st.detection_stop(102.0, 4) == []          # prolonga sin otro evento de inicio
    assert st.detection_active(105.9)
    assert st.update(105.9) == []
    assert st.update(106.0) == [("detection_hold_end", "fin de la retención por detección")]
    assert not st.detection_active(106.0)


@pytest.mark.parametrize("raw,expected", [(None, 4.0), (-1, 4.0), ("abc", 4.0), (2, 2.0),
                                          (999, 30.0), (float("nan"), 4.0), (True, 4.0)])
def test_sanitize_hold(raw, expected):
    assert sanitize_hold(raw) == expected
    assert math.isfinite(sanitize_hold(raw))
