"""Open-Meteo weather client with on-disk cache and synthetic fallback."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from config_loader import ROOT

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore


@dataclass
class HourlyWeather:
    times: list[str]
    temperature_2m: list[float]
    relative_humidity_2m: list[float]
    dew_point_2m: list[float]
    precipitation: list[float]

    def day_slice(self, day_index: int) -> "HourlyWeather":
        start = day_index * 24
        end = start + 24
        return HourlyWeather(
            times=self.times[start:end],
            temperature_2m=self.temperature_2m[start:end],
            relative_humidity_2m=self.relative_humidity_2m[start:end],
            dew_point_2m=self.dew_point_2m[start:end],
            precipitation=self.precipitation[start:end],
        )

    @property
    def n_days(self) -> int:
        return max(0, len(self.temperature_2m) // 24)


@dataclass
class DayWeatherSummary:
    day_index: int
    mean_temp_c: float
    mean_rh: float
    precip_mm: float
    wetness_hours: float
    mean_temp_during_wet_c: float
    source: str  # cache | api | synthetic


def _cache_path(cfg: dict[str, Any], year: int) -> Path:
    cache_dir = ROOT / cfg.get("cache_dir", "data/weather_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    lat = cfg["latitude"]
    lon = cfg["longitude"]
    return cache_dir / f"chia_{lat}_{lon}_{year}.json"


def _parse_payload(payload: dict[str, Any]) -> HourlyWeather:
    h = payload["hourly"]
    return HourlyWeather(
        times=list(h["time"]),
        temperature_2m=[float(x) if x is not None else 15.0 for x in h["temperature_2m"]],
        relative_humidity_2m=[float(x) if x is not None else 70.0 for x in h["relative_humidity_2m"]],
        dew_point_2m=[float(x) if x is not None else 10.0 for x in h["dew_point_2m"]],
        precipitation=[float(x) if x is not None else 0.0 for x in h["precipitation"]],
    )


def fetch_archive(cfg: dict[str, Any], year: int, force: bool = False) -> tuple[HourlyWeather, str]:
    """Return hourly weather for a full year. Prefer cache, then API, then synthetic."""
    path = _cache_path(cfg, year)
    if path.exists() and not force:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return _parse_payload(payload), "cache"

    start = f"{year}-01-01"
    end = f"{year}-12-31"
    params = {
        "latitude": cfg["latitude"],
        "longitude": cfg["longitude"],
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(cfg.get("hourly", [
            "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation"
        ])),
        "timezone": cfg.get("timezone", "America/Bogota"),
    }
    url = cfg.get("archive_url", "https://archive-api.open-meteo.com/v1/archive")

    if httpx is not None:
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.get(url, params=params)
                r.raise_for_status()
                payload = r.json()
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f)
            return _parse_payload(payload), "api"
        except Exception:
            pass

    # Synthetic Sabana-like climate (# SUPUESTO)
    syn = synthesize_year(cfg, year, seed=year)
    # Persist so offline demos are stable
    payload = {
        "latitude": cfg["latitude"],
        "longitude": cfg["longitude"],
        "timezone": cfg.get("timezone", "America/Bogota"),
        "synthetic": True,
        "note": "SUPUESTO — generated offline when API/cache unavailable",
        "hourly": {
            "time": syn.times,
            "temperature_2m": syn.temperature_2m,
            "relative_humidity_2m": syn.relative_humidity_2m,
            "dew_point_2m": syn.dew_point_2m,
            "precipitation": syn.precipitation,
        },
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)
    return syn, "synthetic"


def synthesize_year(cfg: dict[str, Any], year: int, seed: int = 0) -> HourlyWeather:
    """
    Synthetic highland tropical climate approximating Sabana de Bogotá.
    # SUPUESTO — used only when cache/API unavailable.
    """
    rng = np.random.default_rng(seed)
    # non-leap for simplicity unless leap year
    n_days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
    times: list[str] = []
    temp: list[float] = []
    rh: list[float] = []
    dew: list[float] = []
    precip: list[float] = []
    start = date(year, 1, 1)
    for d in range(n_days):
        day = start + timedelta(days=d)
        # Mild seasonality: cooler dry months (Dec–Feb), wetter Apr–May / Oct–Nov
        month = day.month
        wet_season = month in (3, 4, 5, 10, 11)
        base_t = 14.0 + 2.0 * np.sin(2 * np.pi * (d - 80) / 365)
        for h in range(24):
            t = base_t + 5.0 * np.sin(2 * np.pi * (h - 8) / 24) + float(rng.normal(0, 0.6))
            # RH high at night / early morning
            rh_h = 75.0 + 15.0 * np.cos(2 * np.pi * (h - 4) / 24)
            if wet_season:
                rh_h += 8.0
            rh_h = float(np.clip(rh_h + rng.normal(0, 4), 40, 100))
            p = 0.0
            if wet_season and 13 <= h <= 17 and rng.random() < 0.18:
                p = float(rng.uniform(0.2, 4.0))
            elif (not wet_season) and 14 <= h <= 16 and rng.random() < 0.05:
                p = float(rng.uniform(0.1, 1.5))
            # dew point approx from RH (Magnus-ish rough)
            dew_h = t - ((100 - rh_h) / 5.0)
            times.append(f"{day.isoformat()}T{h:02d}:00")
            temp.append(float(t))
            rh.append(float(rh_h))
            dew.append(float(dew_h))
            precip.append(float(p))
    return HourlyWeather(times, temp, rh, dew, precip)


def summarize_day(
    hourly: HourlyWeather,
    day_index: int,
    cfg: dict[str, Any],
    source: str,
) -> DayWeatherSummary:
    day = hourly.day_slice(day_index % max(hourly.n_days, 1))
    rh_thr = float(cfg.get("rh_wetness_threshold_pct", 90))
    precip_thr = float(cfg.get("precip_wetness_threshold_mm", 0.0))

    temps = np.array(day.temperature_2m, dtype=float)
    rhs = np.array(day.relative_humidity_2m, dtype=float)
    precs = np.array(day.precipitation, dtype=float)

    wet_mask = (rhs >= rh_thr) | (precs > precip_thr)
    wet_h = float(wet_mask.sum())
    if wet_h > 0:
        mean_t_wet = float(temps[wet_mask].mean())
    else:
        mean_t_wet = float(temps.mean()) if len(temps) else 15.0

    return DayWeatherSummary(
        day_index=day_index,
        mean_temp_c=float(temps.mean()) if len(temps) else 15.0,
        mean_rh=float(rhs.mean()) if len(rhs) else 70.0,
        precip_mm=float(precs.sum()),
        wetness_hours=wet_h,
        mean_temp_during_wet_c=mean_t_wet,
        source=source,
    )


def tick_weather_snapshot(
    hourly: HourlyWeather,
    day_index: int,
    tick: int,
    ticks_per_day: int,
    day_summary: DayWeatherSummary,
) -> dict[str, float]:
    """Interpolate within-day hourly values for the current tick."""
    day = hourly.day_slice(day_index % max(hourly.n_days, 1))
    hour = int((tick / max(ticks_per_day, 1)) * 24) % 24
    n = len(day.temperature_2m)
    if n == 0:
        return {
            "T": day_summary.mean_temp_c,
            "RH": day_summary.mean_rh,
            "wet_h": day_summary.wetness_hours,
            "precip": day_summary.precip_mm,
        }
    hour = min(hour, n - 1)
    return {
        "T": float(day.temperature_2m[hour]),
        "RH": float(day.relative_humidity_2m[hour]),
        "wet_h": day_summary.wetness_hours,
        "precip": float(day.precipitation[hour]),
    }


def ensure_cached_year(cfg: dict[str, Any], year: int) -> Path:
    """Fetch and cache a year; return path."""
    path = _cache_path(cfg, year)
    if not path.exists():
        fetch_archive(cfg, year)
    return path
