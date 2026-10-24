"""Same seed + alternative → identical snapshots."""
from __future__ import annotations

from config_loader import load_all_config
from engine import Simulation
from weather import synthesize_year


def _make(seed: int, alt: str = "F", patrol_dt: float = 2.0) -> Simulation:
    cfg = load_all_config()
    hourly = synthesize_year(cfg["weather"], 2025, seed=2025)
    return Simulation(
        alternative=alt,
        seed=seed,
        year=2025,
        config=cfg,
        hourly_weather=hourly,
        weather_source="synthetic",
        patrol_dt_s=patrol_dt,
    )


def test_same_seed_identical_snapshots() -> None:
    a = _make(42, "F")
    b = _make(42, "F")
    for _ in range(1500):
        a.step()
        b.step()
    sa, sb = a.snapshot(), b.snapshot()
    assert sa["plants"] == sb["plants"]
    assert sa["metrics"] == sb["metrics"]
    assert sa["risk"]["combined"] == sb["risk"]["combined"]
    assert abs(sa["robot"]["x"] - sb["robot"]["x"]) < 1e-9
    assert [e["text"] for e in sa["events"]] == [e["text"] for e in sb["events"]]


def test_different_seed_diverges() -> None:
    a = _make(1, "F")
    b = _make(2, "F")
    a.run_until(max_days=10)
    b.run_until(max_days=10)
    assert a.snapshot()["plants"] != b.snapshot()["plants"]


def test_metrics_run_until() -> None:
    sim = _make(7, "F")
    m = sim.run_until(max_days=40)
    assert m.first_focus_day is not None
    assert m.infected >= 1


def test_patrol_completes_and_reports() -> None:
    sim = _make(3, "A")
    # sim.events keeps only the last ~120 events; with the measured false-alarm rate (0.36 per plant) the
    # patrol's alerts push the start event out, so record every emitted event instead.
    seen: list[str] = []
    emit = sim._emit
    sim._emit = lambda etype, text, level="info", **data: (seen.append(etype), emit(etype, text, level, **data))  # type: ignore[method-assign]
    sim.run_until(max_days=1)
    types = seen
    assert "patrol_start" in types
    assert types.count("aisle_complete") == len(sim.map.block_aisles(sim.bloque))  # la patrulla recorre solo el bloque elegido
    assert "patrol_complete" in types
    assert sim.last_patrol_summary is not None
    assert sim.last_patrol_summary["plants"] >= sim.n // sim.map.n_blocks  # un bloque de los dos


def test_records_sync_at_dock() -> None:
    sim = _make(3, "A")
    sim.run_until(max_days=1)
    assert sim.records, "robot should log temperature/RH samples"
    assert all(r["synced"] for r in sim.records)
    assert any(e["type"] == "sync" for e in sim.events)
    assert sim.records_csv().startswith("id,day,clock")
