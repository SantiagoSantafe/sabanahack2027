"""Headless batch runner: N runs per alternative → CSV + PNG charts."""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from alternatives import list_alternatives
from config_loader import ROOT, load_all_config
from engine import Simulation
from risk import combined_risk, daily_risks
from weather import fetch_archive, summarize_day

RESULTS = ROOT / "results"


def _run_one(args: tuple[str, int, int, str]) -> dict[str, Any]:
    alt, seed, year, wx_source_hint = args
    cfg = load_all_config()
    patrol_dt = float(cfg["sim"].get("time", {}).get("batch_patrol_dt_s", 2.0))
    sim = Simulation(alternative=alt, seed=seed, year=year, config=cfg, patrol_dt_s=patrol_dt)
    m = sim.run_until()
    k = sim.kpis()
    return {
        "alternative": alt,
        "seed": seed,
        "first_alert_delivered_day": m.first_alert_delivered_day if m.first_alert_delivered_day is not None else "",
        "patrols": k["patrols"],
        "avg_patrol_min": k["avg_patrol_min"] if k["avg_patrol_min"] is not None else "",
        "human_min_per_block": k["human_minutes_per_block"],
        "distance_km": k["distance_km"],
        "field_hours": k["field_hours"],
        "foliage_contacts": k["contacts"],
        "careful_passes": k["careful_passes"],
        "plants_skipped": k["plants_skipped"],
        "first_focus_day": m.first_focus_day if m.first_focus_day is not None else "",
        "first_detection_day": m.first_detection_day if m.first_detection_day is not None else "",
        "beds_infected_at_detection": m.beds_infected_at_detection
        if m.beds_infected_at_detection is not None
        else "",
        "plants_infected_at_detection": m.plants_infected_at_detection
        if m.plants_infected_at_detection is not None
        else "",
        "false_alarms": m.false_alarms,
        "missed": m.missed,
        "infected_final": m.infected,
        "detected": m.detected,
    }


def _percentile(vals: list[float], q: float) -> float:
    if not vals:
        return float("nan")
    return float(np.percentile(np.array(vals, dtype=float), q))


def _floats(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) not in ("", None)]


def write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    alts = sorted({r["alternative"] for r in rows})
    fields = [
        "alternative",
        "n",
        "detection_day_p10",
        "detection_day_median",
        "detection_day_p90",
        "beds_at_det_p10",
        "beds_at_det_median",
        "beds_at_det_p90",
        "false_alarms_median",
        "missed_median",
        "detection_rate",
        "alert_delivered_day_median",
        "avg_patrol_min_median",
        "human_min_per_block",
        "foliage_contacts_median",
        "plants_skipped_median",
    ]
    out_rows = []
    for alt in alts:
        subset = [r for r in rows if r["alternative"] == alt]
        det_days = [
            float(r["first_detection_day"])
            for r in subset
            if r["first_detection_day"] != "" and r["first_detection_day"] is not None
        ]
        beds = [
            float(r["beds_infected_at_detection"])
            for r in subset
            if r["beds_infected_at_detection"] != "" and r["beds_infected_at_detection"] is not None
        ]
        fas = [float(r["false_alarms"]) for r in subset]
        missed = [float(r["missed"]) for r in subset]
        detected_n = sum(1 for r in subset if r["first_detection_day"] != "")
        out_rows.append(
            {
                "alternative": alt,
                "n": len(subset),
                "detection_day_p10": _percentile(det_days, 10),
                "detection_day_median": _percentile(det_days, 50),
                "detection_day_p90": _percentile(det_days, 90),
                "beds_at_det_p10": _percentile(beds, 10),
                "beds_at_det_median": _percentile(beds, 50),
                "beds_at_det_p90": _percentile(beds, 90),
                "false_alarms_median": _percentile(fas, 50),
                "missed_median": _percentile(missed, 50),
                "detection_rate": detected_n / max(len(subset), 1),
                "alert_delivered_day_median": _percentile(_floats(subset, "first_alert_delivered_day"), 50),
                "avg_patrol_min_median": _percentile(_floats(subset, "avg_patrol_min"), 50),
                "human_min_per_block": subset[0]["human_min_per_block"] if subset else "",
                "foliage_contacts_median": _percentile(_floats(subset, "foliage_contacts"), 50),
                "plants_skipped_median": _percentile(_floats(subset, "plants_skipped"), 50),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)


def plot_charts(rows: list[dict[str, Any]], out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    alts = sorted({r["alternative"] for r in rows}, key=lambda a: (a == "REF", a))
    # Detection day distribution
    data_days = []
    data_beds = []
    labels = []
    for alt in alts:
        subset = [r for r in rows if r["alternative"] == alt]
        days = [
            float(r["first_detection_day"])
            for r in subset
            if r["first_detection_day"] != ""
        ]
        beds = [
            float(r["beds_infected_at_detection"])
            for r in subset
            if r["beds_infected_at_detection"] != ""
        ]
        if days:
            data_days.append(days)
            data_beds.append(beds if beds else [0.0])
            labels.append(alt)

    fig, ax = plt.subplots(figsize=(10, 5))
    if data_days:
        ax.boxplot(data_days, tick_labels=labels, showfliers=False)
    ax.set_ylabel("Día de primera detección correcta")
    ax.set_xlabel("Alternativa")
    ax.set_title("Distribución del día de detección por alternativa")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "detection_day.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    if data_beds:
        ax.boxplot(data_beds, tick_labels=labels, showfliers=False)
    ax.set_ylabel("Camas infectadas al detectar")
    ax.set_xlabel("Alternativa")
    ax.set_title("Camas infectadas al momento de detección, por alternativa")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "beds_at_detection.png", dpi=150)
    plt.close(fig)


def risk_days_by_month(year: int, out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = load_all_config()
    hourly, source = fetch_archive(cfg["weather"], year)
    thr = float(cfg["weather"].get("risk_levels", {}).get("high", cfg["weather"].get("high_risk_threshold", 0.15)))
    outdoor = [0] * 12
    tunnel = [0] * 12
    probe = Simulation(alternative="F", seed=0, year=year, config=cfg, hourly_weather=hourly, weather_source=source)
    probe.start_day_offset = 0
    for d in range(hourly.n_days):
        month = int(hourly.times[d * 24][5:7])
        summary = summarize_day(hourly, d, cfg["weather"], source)
        risks = daily_risks(summary.wetness_hours, summary.mean_temp_during_wet_c, summary.mean_temp_c, cfg["risk"])
        if combined_risk(risks, cfg["risk"].get("combine", "max")) >= thr:
            outdoor[month - 1] += 1
        probe.day = d
        probe._update_day_climate()
        if probe.combined >= thr:
            tunnel[month - 1] += 1

    path = out_dir / "risk_days_by_month.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "high_risk_days_outdoor", "high_risk_days_macrotunnel", "year", "threshold", "weather_source"])
        for i in range(12):
            w.writerow([i + 1, outdoor[i], tunnel[i], year, thr, source])

    fig, ax = plt.subplots(figsize=(10, 4))
    xs = np.arange(1, 13)
    ax.bar(xs - 0.2, outdoor, width=0.4, color="#7FB3D5", label="Afuera (Open-Meteo)")
    ax.bar(xs + 0.2, tunnel, width=0.4, color="#2d6a4f", label="Dentro del macrotúnel (cama más húmeda)")
    ax.legend()
    ax.set_xticks(xs)
    ax.set_xlabel("Mes")
    ax.set_ylabel("Días de riesgo alto")
    ax.set_title(f"Días de riesgo alto por mes — Sabana {year} (umbral {thr})")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "risk_days_by_month.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Berry sim headless batch")
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--alternatives", type=str, default="all")
    parser.add_argument("--weather", type=str, default="historical")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--base-seed", type=int, default=1000)
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)

    if args.alternatives == "all":
        alts = list_alternatives()
    else:
        alts = [a.strip() for a in args.alternatives.split(",") if a.strip()]

    # Prefetch weather cache in parent
    cfg = load_all_config()
    fetch_archive(cfg["weather"], args.year)

    jobs = [
        (alt, args.base_seed + i, args.year, "cache")
        for alt in alts
        for i in range(args.runs)
    ]
    print(f"Running {len(jobs)} simulations ({args.runs} × {len(alts)} alts)...")

    rows: list[dict[str, Any]] = []
    workers = args.workers or min(8, max(1, (os_cpu_count() or 4)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_run_one, j): j for j in jobs}
        done = 0
        for fut in as_completed(futs):
            rows.append(fut.result())
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")

    runs_path = RESULTS / "runs.csv"
    fields = list(rows[0].keys()) if rows else []
    with runs_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    write_summary(rows, RESULTS / "summary.csv")
    plot_charts(rows, RESULTS)
    risk_days_by_month(args.year, RESULTS)
    print(f"Wrote {runs_path} and summary/charts in {RESULTS}")


def os_cpu_count() -> int | None:
    import os

    return os.cpu_count()


if __name__ == "__main__":
    main()
