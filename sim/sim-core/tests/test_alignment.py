"""Supuestos alineados con la entrevista a AGRAR y con la evidencia del equipo."""
from __future__ import annotations

import numpy as np

from config_loader import load_all_config, load_alternative
from engine import DAY_S, INFECTED_STATES, Simulation
from weather import fetch_archive, synthesize_year


def _sim(alt: str, seed: int = 3) -> Simulation:
    cfg = load_all_config()
    hourly = synthesize_year(cfg["weather"], 2025, seed=2025)
    return Simulation(alternative=alt, seed=seed, year=2025, config=cfg, hourly_weather=hourly,
                      weather_source="synthetic", patrol_dt_s=2.0)


def record_events(sim: Simulation) -> list[dict]:
    """Every emitted event (sim.events keeps only the last ~120, and alerts can push the rest out)."""
    seen: list[dict] = []
    emit = sim._emit

    def _rec(etype: str, text: str, level: str = "info", **data: object) -> None:
        emit(etype, text, level, **data)
        seen.append(dict(sim.events[-1]))

    sim._emit = _rec  # type: ignore[method-assign]
    return seen


def test_robots_patrol_at_dawn_not_tied_to_sprayer() -> None:
    assert load_all_config()["sim"]["time"]["patrol_start_hour"] == 5.0
    for alt in ("F", "A", "D", "E"):
        assert load_alternative(alt)["schedule"]["start_hour"] == 5.0
    assert load_alternative("C")["schedule"]["start_hour"] == 9.0   # cámara en aspersora: sin cambios
    assert load_alternative("B")["schedule"]["start_hour"] == 9.0
    assert load_alternative("REF")["schedule"]["start_hour"] == 6.0
    sim = _sim("F")
    events = record_events(sim)
    sim.run_until(max_days=1)
    start = next(e for e in events if e["type"] == "patrol_start")
    assert start["clock"] == "05:00"


def test_dawn_patrol_sees_wet_leaves_in_the_tunnel() -> None:
    # Clima real 2025 (caché versionada de Open-Meteo): a las 05:00 casi todas las camas tienen hoja mojada;
    # a las 09:00 casi ninguna (ventilación). Por eso la patrulla al amanecer paga más falsas alarmas.
    cfg = load_all_config()
    hourly, _ = fetch_archive(cfg["weather"], 2025)
    sim = Simulation(alternative="F", seed=0, year=2025, config=cfg, hourly_weather=hourly, weather_source="cache")
    sim.start_day_offset = 0
    at5, at9 = [], []
    for day in range(0, hourly.n_days, 7):
        sim.day = day
        sim._update_day_climate()
        at5.append(sim.wet_bh[:, 5].mean())
        at9.append(sim.wet_bh[:, 9].mean())
    assert np.mean(at5) >= 0.9
    assert np.mean(at9) <= 0.2


def test_bush_height_is_hip_to_rib() -> None:
    f = load_all_config()["field"]
    assert (f["bush_height_min_m"], f["bush_height_max_m"]) == (0.9, 1.3)


def test_infected_counts_ignore_false_alarms() -> None:
    # Antes, una planta sana con alerta pendiente o tratada por una falsa alarma confirmada contaba como
    # "infectada" e inflaba las camas infectadas al detectar de las alternativas con más falsas alarmas.
    sim = _sim("A")
    sim.run_until(max_days=8)
    truth = int((sim.disease != "").sum())
    assert sim.metrics.infected == truth
    healthy_flagged = int((np.isin(sim.states, INFECTED_STATES) & (sim.disease == "")).sum())
    assert sim.metrics.false_alarms > 0 and healthy_flagged > 0
    assert int(np.isin(sim.states, INFECTED_STATES).sum()) == truth + healthy_flagged - _healthy_never(sim)
    if sim.metrics.beds_infected_at_detection is not None:
        assert sim.metrics.beds_infected_at_detection <= int((sim.disease != "").reshape(sim.n_beds, -1).any(1).sum())


def test_false_alarms_do_not_spread_disease() -> None:
    # Antes, una planta sana con alerta pendiente (falsa alarma) era "infecciosa" y contagiaba antracnosis
    # (disease or "anthracnose"): con la tasa medida de falsas alarmas, ~80 % de la presión de contagio de F
    # venía de plantas sanas mal marcadas.
    from detection import STATE_ALERT_PENDING, STATE_HEALTHY, STATE_SYMPTOMATIC
    sim = _sim("F")
    sim.sim["propagation"]["risk_scale"] = 100.0   # p de contagio recortada a 1: si la fuente cuenta, contagia
    sim.states[:] = STATE_HEALTHY
    sim.disease[:] = ""
    sim.bed_risks[:] = 1.0
    i = sim.idx(1, 10)
    sim.states[i] = STATE_ALERT_PENDING            # sana con falsa alarma pendiente
    sim._propagate_daily()
    assert int((sim.disease != "").sum()) == 0
    sim.states[i], sim.disease[i] = STATE_SYMPTOMATIC, "botrytis"   # control: una enferma real sí contagia
    sim._propagate_daily()
    assert set(sim.disease[sim.disease != ""]) == {"botrytis"} and int((sim.disease != "").sum()) > 1


def test_discarded_alert_does_not_cure_a_latent_infection() -> None:
    # Antes, una alerta sobre una planta infectada sin síntomas (cuenta como falsa alarma) la dejaba en
    # "falsa alarma": la latencia se detenía y la infección desaparecía de la dinámica. Con la tasa medida,
    # A borraba ~8 infecciones por corrida y casi nunca detectaba.
    from detection import STATE_FALSE_ALARM, STATE_INFECTED_ASYMP, PendingAlert
    sim = _sim("F")
    from detection import STATE_HEALTHY
    i, j = sim.idx(2, 5), sim.idx(2, 50)
    sim.states[[i, j]] = STATE_HEALTHY
    sim.disease[[i, j]] = ""
    sim._infect(i, "botrytis", day=0.0)
    for k in (i, j):
        sim._resolve_alert(PendingAlert(sim.bed_of(k), sim.plant_of(k), 0.0, 0.0, False, False, "oidio"))
    assert sim.states[i] == STATE_INFECTED_ASYMP and sim.disease[i] == "botrytis"   # sigue incubando
    assert sim.states[j] == STATE_FALSE_ALARM                                     # la sana sí queda descartada
    assert sim.metrics.false_alarms == 2


def _healthy_never(sim: Simulation) -> int:
    """Plantas realmente infectadas que hoy no están en un estado 'infectado' (p. ej. descartadas por error)."""
    return int((~np.isin(sim.states, INFECTED_STATES) & (sim.disease != "")).sum())


def test_risk_levels_use_published_botrytis_thresholds() -> None:
    w = load_all_config()["weather"]
    assert w["risk_levels"] == {"medium": 0.50, "high": 0.70}
    assert load_alternative("B")["risk_trigger"]["risk_threshold"] == 0.50
    assert w["precip_wetness_threshold_mm"] < 0.5 < w["precip_wetness_threshold_mm"] + 0.1


def test_next_patrol_reports_dawn() -> None:
    sim = _sim("F")
    nxt = sim.next_patrol()
    assert nxt is not None and nxt["clock"] == "05:00"
    assert nxt["t"] == nxt["day"] * DAY_S + 5.0 * 3600.0
