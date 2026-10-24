"""Core simulation: outbreak, macrotunnel microclimate, robot patrol, detection, records.

Time model: the clock is in simulated seconds. While a robot/scout is moving the engine
advances `patrol_dt_s` per step (real-time feel in the viewer); otherwise it advances
`idle_dt_min` per step (fast-forward between patrols).
"""
from __future__ import annotations

import base64
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from alternatives import load_alternative, validate_alternative
from config_loader import load_all_config
from detection import (
    CLASS_LABELS,
    DISEASE_CLASSES,
    STATE_ALERT_PENDING,
    STATE_AT_RISK,
    STATE_CONFIRMED,
    STATE_FALSE_ALARM,
    STATE_HEALTHY,
    STATE_INFECTED_ASYMP,
    STATE_SYMPTOMATIC,
    STATE_TREATED,
    PendingAlert,
    classifier_score,
    detect_plant,
    schedule_operator_resolution,
)
from risk import combined_risk, daily_risks
from robot import FieldMap, RobotController, prioritize_by_risk
from weather import fetch_archive

DISEASES = ("anthracnose", "botrytis", "rust")
DAY_S = 86400.0
INFECTED_STATES = [STATE_INFECTED_ASYMP, STATE_SYMPTOMATIC, STATE_ALERT_PENDING, STATE_CONFIRMED, STATE_TREATED]
INFECTIOUS_STATES = [STATE_INFECTED_ASYMP, STATE_SYMPTOMATIC, STATE_ALERT_PENDING, STATE_CONFIRMED]
MAX_RECORDS = 20000


@dataclass
class Metrics:
    infected: int = 0
    symptomatic: int = 0
    detected: int = 0
    false_alarms: int = 0
    missed: int = 0
    confirmed: int = 0
    treated: int = 0
    first_focus_day: float | None = None
    first_detection_day: float | None = None
    first_alert_delivered_day: float | None = None
    beds_infected_at_detection: int | None = None
    plants_infected_at_detection: int | None = None


def _clock(t: float) -> str:
    s = t % DAY_S
    return f"{int(s // 3600):02d}:{int((s % 3600) // 60):02d}"


class Simulation:
    def __init__(
        self,
        alternative: str = "F",
        seed: int = 42,
        weather_mode: str = "historical",
        year: int | None = None,
        config: dict[str, Any] | None = None,
        alt: dict[str, Any] | None = None,
        hourly_weather: Any = None,
        weather_source: str = "cache",
        patrol_dt_s: float | None = None,
        run_id: int = 0,
    ):
        self.cfg = config or load_all_config()
        self.sim = self.cfg["sim"]
        self.field = self.cfg["field"]
        self.risk_cfg = self.cfg["risk"]
        self.det_cfg = self.cfg["detector"]
        self.robot_cfg = self.cfg["robot"]
        self.weather_cfg = self.cfg["weather"]
        self.climate = self.cfg.get("climate", {}) or {}
        self.run_id = run_id

        self.alt_code = "REF" if alternative.lower() == "ref" else alternative.upper()
        self.alt = validate_alternative(alt or load_alternative(self.alt_code))
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)

        self.map = FieldMap(self.field, self.robot_cfg)
        self.n_beds = self.map.n_beds
        self.n_plants = self.map.n_plants
        self.n = self.n_beds * self.n_plants
        self.max_days = int(self.sim["max_days"])

        tcfg = self.sim.get("time", {})
        self.idle_dt_s = float(tcfg.get("idle_dt_min", 30)) * 60.0
        self.patrol_dt_s = float(patrol_dt_s if patrol_dt_s is not None else tcfg.get("patrol_dt_s", 0.1))
        start_h = self.alt.get("schedule", {}).get("start_hour")
        self.patrol_start_h = float(start_h if start_h is not None else tcfg.get("patrol_start_hour", 9.0))

        self.states = np.zeros(self.n, dtype=np.uint8)
        self.heights = self.rng.uniform(
            float(self.field["bush_height_min_m"]), float(self.field["bush_height_max_m"]), size=self.n
        ).astype(np.float32)
        self._init_foliage()
        self.latent_left = np.zeros(self.n, dtype=np.float32)
        self.disease = np.full(self.n, "", dtype=object)
        self.detected_mask = np.zeros(self.n, dtype=bool)
        self.ever_symptomatic = np.zeros(self.n, dtype=bool)

        self.t = 0.0
        self.day = 0
        self.playing = True

        self.year = year or int(self.weather_cfg.get("default_year", 2025))
        if hourly_weather is not None:
            self.hourly, self.weather_source = hourly_weather, weather_source
        else:
            self.hourly, self.weather_source = fetch_archive(self.weather_cfg, self.year)
        self.start_day_offset = int(self.rng.integers(0, max(1, self.hourly.n_days - self.max_days)))

        self.risks: dict[str, float] = {d: 0.0 for d in DISEASES}
        self.combined = 0.0
        self.bed_risks = np.zeros(self.n_beds, dtype=np.float32)
        self.bed_wet_h = np.zeros(self.n_beds, dtype=np.float32)
        self.vent_forgotten = False
        self.alero_open = False

        self.pending: list[PendingAlert] = []
        self.metrics = Metrics()
        self.events: list[dict[str, Any]] = []
        self._event_id = 0
        self.records: list[dict[str, Any]] = []
        self.incident_records: list[dict[str, Any]] = []
        self.bloque = 1  # bloque que recorre el robot (1 = naves 1–2, 2 = naves 3–4); lo elige el operario
        self.solo_camara_real = False  # Ruta real: no sensar plantas simuladas, solo la cámara del D1 registra
        self._healthy_seen = 0  # capturas sin alerta; 1 de cada N se registra como "hoja sana" (ver _capture)
        self.bed_last_t: dict[int, float] = {}  # bed -> sim time (s) of the last capture there (coverage, read by the dashboard)
        self._record_id = 0
        self._unsynced = 0
        self._unsynced_inc = 0
        self.synced_records = 0
        self.last_sync: dict[str, Any] | None = None
        conn = self.climate.get("connectivity", {})
        self.conn_mode = str(conn.get("mode", "store_and_forward"))
        self.human_report_h = float(conn.get("human_report_hour", 14))
        probe = self.climate.get("robot_probe", {})
        self.probe_t_noise = float(probe.get("temp_noise_c", 0.3))
        self.probe_rh_noise = float(probe.get("rh_noise_pct", 2.0))
        self.sample_every_m = float(probe.get("sample_every_m", 5.0))
        self._next_sample_odo = self.sample_every_m

        self.robot = RobotController(self.map, self.robot_cfg, self.alt, self.rng)
        self._patrol_days_done: set[int] = set()
        self._manual_seen: dict[tuple[int, int], float] = {}
        self._manual_aisle = -1

        self.frames = 0
        self.last_capture: dict[str, Any] | None = None
        self.recent_captures: list[dict[str, Any]] = []
        self.capture_seq = 0
        self.last_aruco: dict[str, Any] | None = None
        self.last_probe: dict[str, Any] | None = None
        self.patrol_stats = self._new_patrol_stats()
        self.last_patrol_summary: dict[str, Any] | None = None
        self.patrols_done = 0
        self.patrol_minutes_total = 0.0
        self.stop_s = float(self.robot_cfg.get("path", {}).get("stop_inspect_seconds", 4.0))
        self.human_h_per_ha = float(self.sim.get("human_baseline_hours_per_ha", 2.4))

        self._seed_foci()
        self._update_day_climate()

    # ----- helpers -----
    def idx(self, bed: int, plant: int) -> int:
        return bed * self.n_plants + plant

    def bed_of(self, i: int) -> int:
        return i // self.n_plants

    def plant_of(self, i: int) -> int:
        return i % self.n_plants

    def _emit(self, etype: str, text: str, level: str = "info", **data: Any) -> None:
        self._event_id += 1
        self.events.append(
            {"id": self._event_id, "type": etype, "level": level, "text": text, "day": self.day, "clock": _clock(self.t), **data}
        )
        if len(self.events) > 200:
            self.events = self.events[-120:]

    def _new_patrol_stats(self) -> dict[str, Any]:
        return {
            "started_s": None, "plants": 0, "alerts": 0, "per_aisle": {}, "per_bed_alerts": {},
            "odometry_start": 0.0, "battery_start": 1.0, "contacts_start": 0, "careful_start": 0, "skipped_start": 0,
        }

    def _init_foliage(self) -> None:
        f = self.field.get("foliage", {})
        mean = float(f.get("half_width_mean_m", 0.45))
        sd = float(f.get("half_width_sd_m", 0.06))
        p_over = float(f.get("overflow_prob", 0.22))
        lo, hi = (float(v) for v in f.get("overflow_extra_m", [0.25, 0.6]))
        both = float(f.get("both_sides_prob", 0.3))
        base_l = np.clip(self.rng.normal(mean, sd, self.n), 0.25, None)
        base_r = np.clip(self.rng.normal(mean, sd, self.n), 0.25, None)
        over = self.rng.random(self.n) < p_over
        extra = self.rng.uniform(lo, hi, self.n)
        side = self.rng.random(self.n)
        two = self.rng.random(self.n) < both
        add_l = over & (two | (side < 0.5))
        add_r = over & (two | (side >= 0.5))
        self.map.spread_l = (base_l + add_l * extra).astype(np.float32)
        self.map.spread_r = (base_r + add_r * extra).astype(np.float32)
        self.overflowing = over

    def _seed_foci(self) -> None:
        n_foci = int(self.rng.integers(int(self.sim["initial_foci_min"]), int(self.sim["initial_foci_max"]) + 1))
        for i in self.rng.choice(self.n, size=n_foci, replace=False):
            self._infect(int(i), DISEASES[int(self.rng.integers(0, len(DISEASES)))], day=0.0)

    def _infect(self, i: int, disease: str, day: float) -> None:
        if self.states[i] in INFECTED_STATES:
            return
        self.states[i] = STATE_INFECTED_ASYMP
        self.disease[i] = disease
        self.latent_left[i] = float(self.rng.uniform(float(self.sim["latent_days_min"]), float(self.sim["latent_days_max"])))
        if self.metrics.first_focus_day is None:
            self.metrics.first_focus_day = day

    # ----- microclimate & outbreak -----
    def _day_index(self) -> int:
        return (self.start_day_offset + self.day) % max(self.hourly.n_days, 1)

    def _hour(self) -> float:
        return (self.t % DAY_S) / 3600.0

    def _bed_gradient(self) -> np.ndarray:
        g = float(self.climate.get("spatial_rh_gradient_pct", 0.0))
        mid = float(self.climate.get("middle_bed_rh_extra_pct", 0.0))
        k = np.arange(self.n_beds) // self.map.bpn
        j = np.arange(self.n_beds) % self.map.bpn
        n = self.map.n_naves
        centrality = 1.0 - np.abs((2 * k / max(n - 1, 1)) - 1.0) if n > 1 else np.ones(self.n_beds)
        middle = (j > 0) & (j < self.map.bpn - 1)
        return g * (centrality - 0.5) + mid * middle

    def _update_day_climate(self) -> None:
        day = self.hourly.day_slice(self._day_index())
        T = np.array(day.temperature_2m or [15.0] * 24, dtype=float)
        RH = np.array(day.relative_humidity_2m or [70.0] * 24, dtype=float)
        P = np.array(day.precipitation or [0.0] * 24, dtype=float)
        hours = np.arange(len(T))
        c = self.climate
        self.out_T, self.out_RH, self.out_P = T, RH, P
        if c.get("enabled", True):
            d0, d1 = c.get("day_hours", [6, 18])
            is_day = (hours >= d0) & (hours < d1)
            T_in = T + np.where(is_day, float(c.get("day_temp_offset_c", 0)), float(c.get("night_temp_offset_c", 0)))
            RH_in = RH + np.where(is_day, 0.0, float(c.get("night_rh_offset_pct", 0)))
            vent = c.get("ventilation", {})
            auto = vent.get("mode", "auto") == "auto"
            self.vent_forgotten = bool(auto and self.rng.random() < float(vent.get("forget_prob_per_day", 0)))
            v0, v1 = vent.get("hours", [6, 18])
            vent_on = auto and not self.vent_forgotten
            on = vent_on & (hours >= v0) & (hours < v1) & (RH_in > float(vent.get("rh_setpoint_pct", 85)))
            RH_in = RH_in - on * float(vent.get("rh_reduction_pct", 0))
            T_in = T_in - on * float(vent.get("temp_reduction_c", 0))
            rain = c.get("rain", {})
            self.alero_open = bool(P.sum() > 0 and self.rng.random() < float(rain.get("alero_open_prob", 0)))
            rain_wet = (P > 0) & (self.alero_open or not rain.get("cover_blocks_rain", True))
            self.vent_on_h = on
        else:
            T_in, RH_in, rain_wet = T, RH, P > 0
            self.vent_forgotten = self.alero_open = False
            self.vent_on_h = np.zeros(len(T), dtype=bool)
        self.T_in = T_in
        self.RH_bed = np.clip(RH_in[None, :] + self._bed_gradient()[:, None], 0, 100)
        thr = float(self.weather_cfg.get("rh_wetness_threshold_pct", 90))
        self.wet_bh = (self.RH_bed >= thr) | rain_wet[None, :]
        how = self.risk_cfg.get("combine", "max")
        per_disease = {d: 0.0 for d in DISEASES}
        for b in range(self.n_beds):
            wet = self.wet_bh[b]
            wet_h = float(wet.sum())
            t_wet = float(T_in[wet].mean()) if wet_h > 0 else float(T_in.mean())
            r = daily_risks(wet_h, t_wet, float(T_in.mean()), self.risk_cfg)
            self.bed_wet_h[b] = wet_h
            self.bed_risks[b] = combined_risk(r, how)
            for d in DISEASES:
                per_disease[d] = max(per_disease[d], r[d])
        self.risks = per_disease
        self.combined = float(self.bed_risks.max()) if self.n_beds else 0.0
        trig = float(self.weather_cfg.get("risk_levels", {}).get("high", 0.15))
        for b in range(self.n_beds):
            sl = slice(b * self.n_plants, (b + 1) * self.n_plants)
            cur = self.states[sl]
            if self.bed_risks[b] >= trig:
                self.states[sl] = np.where(cur == STATE_HEALTHY, STATE_AT_RISK, cur)
            else:
                self.states[sl] = np.where(cur == STATE_AT_RISK, STATE_HEALTHY, cur)
        if self.vent_forgotten:
            self._emit("ventilation", "Ventilación apagada hoy: un operario olvidó encender los ventiladores", "warn")
        if self.alero_open:
            self._emit("alero", "Llovió con el alero abierto: el follaje se mojó", "warn")

    def _propagate_daily(self) -> None:
        prop = self.sim.get("propagation", {})
        scale = float(prop.get("risk_scale", 1.0))
        base_same = float(prop.get("p_same_bed", 0.18))
        base_adj = float(prop.get("p_adjacent_bed", 0.04))
        susceptible = (STATE_HEALTHY, STATE_AT_RISK, STATE_FALSE_ALARM)
        new_inf: list[tuple[int, str]] = []
        # Only plants that really carry a disease spread it: a healthy plant with a pending/confirmed false alarm is not a source
        for i in np.where(np.isin(self.states, INFECTIOUS_STATES) & (self.disease != ""))[0]:
            bed, plant = self.bed_of(int(i)), self.plant_of(int(i))
            r = float(self.bed_risks[bed]) * scale
            p_same = float(np.clip(base_same * r, 0, 1))
            p_adj = float(np.clip(base_adj * r, 0, 1))
            disease = self.disease[i] or "anthracnose"
            for dp in (-1, 1):
                pj = plant + dp
                if 0 <= pj < self.n_plants:
                    j = self.idx(bed, pj)
                    if self.states[j] in susceptible and self.rng.random() < p_same:
                        new_inf.append((j, disease))
            for db in (-1, 1):
                bj = bed + db
                if 0 <= bj < self.n_beds and bj // self.map.bpn == bed // self.map.bpn:
                    j = self.idx(bj, plant)
                    if self.states[j] in susceptible and self.rng.random() < p_adj:
                        new_inf.append((j, disease))
        for j, disease in new_inf:
            self._infect(j, disease, day=float(self.day))
        asym = self.states == STATE_INFECTED_ASYMP
        self.latent_left[asym] -= 1.0
        become = asym & (self.latent_left <= 0)
        self.states[become] = STATE_SYMPTOMATIC
        self.ever_symptomatic[become] = True

    def _on_new_day(self) -> None:
        self._update_day_climate()
        self._propagate_daily()

    # ----- patrol scheduling -----
    def _is_patrol_day(self, day: int) -> bool:
        sched = self.alt.get("schedule", {})
        if sched.get("only_spray_days"):
            return day % max(1, int(self.sim.get("spray_interval_days", 10))) == 0
        return day % max(1, int(sched.get("every_n_days", 1))) == 0

    def next_patrol(self) -> dict[str, Any] | None:
        for d in range(self.day, self.max_days):
            if d in self._patrol_days_done or not self._is_patrol_day(d):
                continue
            t = d * DAY_S + self.patrol_start_h * 3600.0
            if t >= self.t - 1:
                return {"day": d, "clock": _clock(t), "t": t}
        return None

    def _aisle_risks(self) -> list[float]:
        return [max(float(self.bed_risks[a.left]), float(self.bed_risks[a.right])) for a in self.map.aisles]

    def _maybe_start_patrol(self) -> None:
        if self.day in self._patrol_days_done or self._hour() < self.patrol_start_h:
            return
        rt = self.alt.get("risk_trigger", {})
        hr = self.alt.get("human_review", {})
        if rt.get("enabled") and rt.get("action") == "human_review":
            thr = float(rt.get("risk_threshold", 0.55))
            risk_hit = float(np.max(self.bed_risks)) >= thr
            sched_hit = bool(hr.get("review_on_schedule", False)) and self._is_patrol_day(self.day)
            self._patrol_days_done.add(self.day)
            if risk_hit or sched_hit:
                self._run_human_block_review(risk_hit)
            return
        if not self._is_patrol_day(self.day):
            return
        self._patrol_days_done.add(self.day)
        if not self.robot.active or self.robot.mode == "manual":
            return
        if self.robot.state in ("failed", "stuck", "walking", "returning", "inspecting", "charging"):
            return
        if self.alt.get("prioritize_by_risk"):
            order = prioritize_by_risk(self._aisle_risks(), float(rt.get("risk_threshold", 0.4)))
        else:
            order = list(range(len(self.map.aisles)))
        del_bloque = set(self.map.block_aisles(self.bloque))
        order = [a for a in order if a in del_bloque] or order  # solo el bloque elegido
        self.robot.start_patrol(order)
        self.patrol_stats = self._new_patrol_stats()
        ps = self.patrol_stats
        ps.update(
            started_s=self.t, odometry_start=self.robot.odometry_m, battery_start=self.robot.battery,
            contacts_start=self.robot.contacts, careful_start=self.robot.careful_passes, skipped_start=self.robot.plants_skipped,
        )
        self._next_sample_odo = self.robot.odometry_m + self.sample_every_m
        first = self.map.aisles[order[0]]
        why = ", empieza por el pasillo de mayor riesgo" if self.alt.get("prioritize_by_risk") else ""
        self._emit("patrol_start", f"Inicia recorrido por {len(order)} pasillos desde {self.map.aisle_label(first)}{why}", "info")

    def _run_human_block_review(self, risk_hit: bool) -> None:
        thr = float(self.alt.get("risk_trigger", {}).get("risk_threshold", 0.55))
        beds = [b for b in range(self.n_beds) if self.bed_risks[b] >= thr] or list(range(self.n_beds))
        before = len(self.pending) + self.metrics.detected
        for b in beds:
            for p in range(self.n_plants):
                self._capture(b, p, force_human=True)
        cause = "riesgo alto en la red de sensores" if risk_hit else "revisión programada"
        found = len(self.pending) + self.metrics.detected - before
        self._emit("human_review", f"Revisión humana de {len(beds)} camas por {cause}: {found} hallazgos", "info")

    # ----- sensing & records -----
    def _wet_now(self, bed: int) -> bool:
        h = min(int(self._hour()), self.wet_bh.shape[1] - 1)
        return bool(self.wet_bh[bed, h])

    def _probe(self, bed: int) -> tuple[float, float]:
        h = min(int(self._hour()), len(self.T_in) - 1)
        t = float(self.T_in[h] + self.rng.normal(0, self.probe_t_noise))
        rh = float(np.clip(self.RH_bed[bed, h] + self.rng.normal(0, self.probe_rh_noise), 0, 100))
        return round(t, 1), round(rh, 1)

    def _record(self, kind: str, bed: int, plant: int | None, **extra: Any) -> dict[str, Any]:
        human = extra.get("fuente") == "humano"
        t_c, rh = (None, None) if human else self._probe(bed)
        self._record_id += 1
        nave = bed // self.map.bpn + 1
        rec = {
            "id": self._record_id, "day": self.day, "clock": _clock(self.t), "kind": kind,
            "nave": nave, "cama": bed % self.map.bpn + 1, "cama_global": bed + 1,
            "planta": (plant + 1) if plant is not None else None,
            "x": round(self.robot.x, 2), "z": round(self.robot.z, 2),
            "temp_c": t_c, "rh_pct": rh, "synced": self.conn_mode == "live", **extra,
        }
        self.records.append(rec)
        if kind == "incidencia":
            self.incident_records.append(rec)
        if not rec["synced"]:
            self._unsynced += 1
            self._unsynced_inc += kind == "incidencia"
        if len(self.records) > MAX_RECORDS:
            self.records = self.records[-MAX_RECORDS:]
        if not human:
            self.last_probe = {"temp_c": t_c, "rh_pct": rh, "bed": bed, "kind": kind}
        return rec

    def _capture(self, bed: int, plant: int, force_human: bool = False) -> bool:
        """Sense one plant face. Returns True if the robot should stop (alert raised)."""
        i = self.idx(bed, plant)
        st = int(self.states[i])
        self.bed_last_t[bed] = self.t
        self.frames += 1
        self.capture_seq += 1
        ps = self.patrol_stats
        ps["plants"] += 1
        a = self.robot.current_aisle
        pa = ps["per_aisle"].setdefault(a, {"plants": 0, "alerts": 0})
        pa["plants"] += 1

        if st in (STATE_ALERT_PENDING, STATE_CONFIRMED, STATE_TREATED):
            self._set_capture({"seq": self.capture_seq, "bed": bed, "plant": plant, "label": "ya registrada",
                               "score": None, "alert": False, "state": st})
            return False

        sensor = self.alt["sensor"]
        camera_h = float(sensor.get("camera_height_m", 0.3))
        if self.robot.mast:
            camera_h = max(camera_h, float(self.robot_cfg.get("mast", {}).get("camera_height_m", camera_h)))
        fog = float(self.alt.get("fog_sensitivity_penalty", 1.0))
        if self.alt.get("schedule", {}).get("only_spray_days"):
            fog = min(fog, float(self.det_cfg.get("fog_sensitivity_penalty", 0.55)))
        human = force_human or self.alt.get("platform") == "human"
        hr = self.alt.get("human_review") if human else None
        if human and not (hr and hr.get("enabled")):
            hr = {"enabled": True, "sensitivity_small": 0.55, "sensitivity_underside": 0.4}
        detect_state = STATE_HEALTHY if st == STATE_FALSE_ALARM else st
        raise_alert, is_tp, vclass = detect_plant(
            self.rng, detect_state, str(self.disease[i] or "anthracnose"), float(self.heights[i]),
            camera_h, bool(sensor.get("sees_full_bush", False)), self._wet_now(bed), fog,
            float(sensor.get("base_sensitivity", 1.0)), self.det_cfg, human_review=hr,
        )
        thr = float(self.det_cfg.get("decision", {}).get("score_threshold", 0.35))
        score = classifier_score(self.rng, raise_alert, thr)
        if raise_alert and not is_tp:
            vclass = DISEASE_CLASSES[int(self.rng.integers(0, len(DISEASE_CLASSES)))]
        label = CLASS_LABELS.get(vclass if raise_alert else "healthy", vclass)
        self._set_capture({"seq": self.capture_seq, "bed": bed, "plant": plant, "label": label,
                           "score": round(score, 2), "alert": raise_alert, "state": st})
        if not raise_alert:
            # Registro de casos sanos: muestra cómo se comporta el sistema sin enfermedad (la rúbrica lo pide).
            # No se guarda cada planta (serían miles); 1 de cada N inspecciones sin hallazgo.
            if not human:
                self._healthy_seen += 1
                every = int(self.det_cfg.get("registro_sanas_cada", 6))
                if every > 0 and self._healthy_seen % every == 0:
                    # confianza de "sana" = margen bajo el umbral de alerta: 0,5 justo en el umbral, 1,0 sin señal de enfermedad
                    self._record("incidencia", bed, plant, clase="sana", confianza=round(0.5 + 0.5 * (1.0 - score / max(thr, 1e-6)), 2), fuente="robot",
                                 truth_label="enferma_no_detectada" if st in (STATE_INFECTED_ASYMP, STATE_SYMPTOMATIC) else "sana")
            return False

        delay_d, confirm = schedule_operator_resolution(self.rng, 0.0, is_tp, self.det_cfg)
        alert = PendingAlert(bed, plant, self.t, delay_d * DAY_S, is_tp, confirm, vclass)
        if human:
            alert.deliver_at_s = self._next_report_s()
            alert.delay_s = 0.0
            alert.confirm = is_tp
        elif self.conn_mode == "live":
            alert.delivered_s = self.t
        self.states[i] = STATE_ALERT_PENDING
        self.pending.append(alert)
        ps["alerts"] += 1
        pa["alerts"] += 1
        ps["per_bed_alerts"][bed] = ps["per_bed_alerts"].get(bed, 0) + 1
        rec = self._record("incidencia", bed, plant, clase=label, confianza=None if human else round(score, 2),
                           fuente="humano" if human else "robot")
        if is_tp:
            self.detected_mask[i] = True
            if self.metrics.first_detection_day is None:
                self.metrics.first_detection_day = self.t / DAY_S
                self.metrics.beds_infected_at_detection = self._count_infected_beds()
                self.metrics.plants_infected_at_detection = self._count_infected_plants()
        if not human:
            self._emit(
                "alert",
                f"{self.map.bed_label(bed)}, planta {plant + 1}: {label} ({score:.2f}) a {rec['temp_c']:.1f} °C y "
                f"{rec['rh_pct']:.0f} % HR. Registrada para el agrónomo",
                "warn", bed=bed, plant=plant,
            )
        elif self.alt.get("platform") == "human":
            self._emit("alert", f"El operario anota {self.map.bed_label(bed)}, planta {plant + 1}: {label}. "
                       f"Se digitaliza a las {int(self.human_report_h)}:00", "warn", bed=bed, plant=plant)
        return not human

    def _set_capture(self, cap: dict[str, Any]) -> None:
        self.last_capture = cap
        self.recent_captures = (self.recent_captures + [cap])[-2:]

    def _next_report_s(self) -> float:
        today = self.day * DAY_S + self.human_report_h * 3600.0
        return today if self.t <= today else today + DAY_S

    def _routine_sample(self) -> None:
        r = self.robot
        if r.platform == "human" or r.current_aisle < 0 or not (self.map.bed_z0 <= r.z <= self.map.bed_z1):
            return
        if r.odometry_m < self._next_sample_odo:
            return
        self._next_sample_odo = r.odometry_m + self.sample_every_m
        a = self.map.aisles[r.current_aisle]
        self._record("muestra", a.left if (self.robot.x - a.x) < 0 else a.right, self.map.nearest_plant(r.z))

    def _sync(self, how: str) -> None:
        pending = [r for r in self.records if not r["synced"]] if self._unsynced else []
        n_inc = sum(1 for r in pending if r["kind"] == "incidencia")
        for r in pending:
            r["synced"] = True
        self._unsynced = self._unsynced_inc = 0
        self.synced_records += len(pending)
        delivered = 0
        for a in self.pending:
            if a.delivered_s is None and a.deliver_at_s is None:
                a.delivered_s = self.t
                delivered += 1
                if a.is_true_positive and self.metrics.first_alert_delivered_day is None:
                    self.metrics.first_alert_delivered_day = self.t / DAY_S
        self.last_sync = {"day": self.day, "clock": _clock(self.t), "records": len(pending), "incidents": n_inc}
        if pending:
            self._emit("sync", f"{how}: {len(pending)} registros ({n_inc} incidencias) enviados a la base de datos", "ok")

    def _manual_sense(self, force: bool = False) -> None:
        r, m = self.robot, self.map
        in_zone = m.bed_z0 - 0.5 <= r.z <= m.bed_z1 + 0.5
        a = m.nearest_aisle(r.x)
        in_aisle = abs(r.x - a.x) < m.pitch / 2.0 - m.bed_w / 2.0
        if in_zone and in_aisle:
            if a.index != self._manual_aisle:
                self._manual_aisle = a.index
                r.current_aisle = a.index
                r.bed_label = m.aisle_label(a)
                self._on_robot_event({"type": "aruco", "aisle": a.index, "beds": [a.left, a.right]})
        elif not in_zone:
            self._manual_aisle = -1
            r.current_aisle = -1
        ch = math.cos(r.heading)
        if not (in_zone and in_aisle) or (abs(ch) < 0.6 and not force):
            r.target = None
            return
        dirz = 1.0 if ch >= 0 else -1.0
        p = int(round((r.z + dirz * r.lookahead - m.z0) / m.spacing))
        if not 0 <= p < m.n_plants:
            r.target = None
            return
        r.target = (a.index, p)
        if self.solo_camara_real:
            return
        for k in [k for k, t in self._manual_seen.items() if self.t - t > 120]:
            del self._manual_seen[k]
        for bed in (a.left, a.right):
            if force or (bed, p) not in self._manual_seen:
                self._manual_seen[(bed, p)] = self.t
                self._capture(bed, p)
        self._routine_sample()

    def _on_robot_event(self, e: dict[str, Any]) -> None:
        t = e["type"]
        r, m = self.robot, self.map
        if t == "aruco":
            a = m.aisles[e["aisle"]]
            self.last_aruco = {"seq": self._event_id + 1, "aisle": e["aisle"], "beds": e["beds"],
                               "marker_ids": [b + 1 for b in e["beds"]]}
            self._emit("aruco", f"Marcadores ArUco {a.left + 1} y {a.right + 1}: Bloque 1 · {m.aisle_label(a)}", aisle=e["aisle"])
        elif t == "aisle_complete":
            pa = self.patrol_stats["per_aisle"].get(e["aisle"], {"plants": 0, "alerts": 0})
            n_al = pa["alerts"]
            msg = "sin hallazgos" if n_al == 0 else f"{n_al} alerta{'s' if n_al != 1 else ''}"
            self._emit(
                "aisle_complete", f"{m.aisle_label(m.aisles[e['aisle']])} completo: {pa['plants']} plantas, {msg}",
                "warn" if n_al else "ok", aisle=e["aisle"], plants=pa["plants"], alerts=n_al,
            )
        elif t == "careful":
            what = "roza las hojas" if e["contact"] else "baja la velocidad"
            self._emit("careful", f"Follaje desbordado en {m.aisle_label(m.aisles[e['aisle']])}: {what}", "info", aisle=e["aisle"])
        elif t == "blocked":
            self._emit(
                "blocked",
                f"No cabe por {m.aisle_label(m.aisles[e['aisle']])}: el follaje desbordado bloquea el paso. "
                f"Quedan {e['skipped']} plantas sin revisar en ese pasillo",
                "danger", aisle=e["aisle"],
            )
        elif t == "patrol_complete":
            ps = self.patrol_stats
            dur_min = (self.t - (ps["started_s"] or self.t)) / 60.0
            self.patrols_done += 1
            self.patrol_minutes_total += dur_min
            summary = {
                "day": self.day, "clock": _clock(self.t),
                "aisles": len(r.aisles_done), "beds": self.n_beds,
                "plants": ps["plants"], "alerts": ps["alerts"],
                "minutes": round(dur_min, 1),
                "distance_m": round(r.odometry_m - ps["odometry_start"], 1),
                "battery_used": round((ps["battery_start"] - r.battery) * 100, 1),
                "alert_beds": sorted(m.bed_label(b) for b in ps["per_bed_alerts"]),
                "contacts": r.contacts - ps["contacts_start"],
                "careful": r.careful_passes - ps["careful_start"],
                "skipped": r.plants_skipped - ps["skipped_start"],
                "human_minutes": round(m.area_ha * self.human_h_per_ha * 60, 0),
            }
            self.last_patrol_summary = summary
            self._emit(
                "patrol_complete",
                f"Recorrido completo: {summary['plants']} plantas y {summary['alerts']} alertas en {summary['minutes']:.0f} min",
                "ok", summary=summary,
            )
        elif t == "docked":
            if self.conn_mode == "store_and_forward" and r.platform != "human":
                self._sync("Sincronizado en la base")
        elif t == "battery_low":
            self._emit("battery_low", f"Batería al {e['battery'] * 100:.0f} %. Vuelve a la base", "warn")
        elif t == "docked_charging":
            self._emit("charging", "En la base, cargando", "info")
        elif t == "charged":
            self._emit("charged", "Batería cargada. Retoma el recorrido", "info")
        elif t == "failed":
            self._emit("failed", f"Caída o detención en {m.aisle_label(m.aisles[e['aisle']])}. Requiere rescate", "danger")
        elif t == "stuck":
            self._emit("stuck", f"Atascado en {m.aisle_label(m.aisles[e['aisle']])}", "danger")
        elif t == "unstuck":
            self._emit("unstuck", "Se liberó y continúa", "info")
        elif t == "rescued":
            self._emit("rescued", "Un operario llevó el robot a la base", "info")

    # ----- alerts -----
    def _resolve_alert(self, a: PendingAlert) -> None:
        i = self.idx(a.bed, a.plant)
        where = f"{self.map.bed_label(a.bed)}, planta {a.plant + 1}"
        if a.confirm:
            self.metrics.confirmed += 1
            self.states[i] = STATE_TREATED
            self.metrics.treated += 1
            if a.is_true_positive:
                self.metrics.detected += 1
            else:
                self.metrics.false_alarms += 1
            self._emit("confirmed", f"Agrónomo confirmó {where}. Tratada", "ok")
        elif a.is_true_positive:
            self.states[i] = STATE_SYMPTOMATIC
            self._emit("discarded", f"Agrónomo descartó {where}", "warn")
        else:
            # A discarded alert on a plant that is really infected (no symptoms yet) does not cure it: back to latent
            self.states[i] = STATE_INFECTED_ASYMP if self.disease[i] else STATE_FALSE_ALARM
            self.metrics.false_alarms += 1
            self._emit("false_alarm", f"Falsa alarma en {where}", "info")

    def _process_pending(self) -> None:
        report_due = [a for a in self.pending if a.delivered_s is None and a.deliver_at_s is not None and self.t >= a.deliver_at_s]
        if report_due:
            for a in report_due:
                a.delivered_s = self.t
                if a.is_true_positive and self.metrics.first_alert_delivered_day is None:
                    self.metrics.first_alert_delivered_day = self.t / DAY_S
            for r in self.records:
                if not r["synced"] and r.get("fuente") == "humano":
                    r["synced"] = True
                    self._unsynced -= 1
                    self._unsynced_inc -= r["kind"] == "incidencia"
            self._emit("sync", f"Registro manual digitalizado: {len(report_due)} incidencias llegan al agrónomo", "ok")
        keep: list[PendingAlert] = []
        for a in self.pending:
            if a.delivered_s is not None and self.t >= a.delivered_s + a.delay_s:
                self._resolve_alert(a)
            else:
                keep.append(a)
        self.pending = keep

    # ----- metrics -----
    def _count_infected_plants(self) -> int:
        # Ground truth (plants that ever got a disease): a healthy plant with a pending or confirmed false alarm is not infected
        return int((self.disease != "").sum())

    def _count_infected_beds(self) -> int:
        grid = (self.disease != "").reshape(self.n_beds, self.n_plants)
        return int(grid.any(axis=1).sum())

    def _update_metrics(self) -> None:
        self.metrics.infected = self._count_infected_plants()
        self.metrics.symptomatic = int(np.isin(self.states, [STATE_SYMPTOMATIC, STATE_ALERT_PENDING]).sum())
        self.metrics.missed = int((self.ever_symptomatic & ~self.detected_mask & (self.states != STATE_TREATED)).sum())

    # ----- manual control -----
    def set_manual(self, on: bool) -> None:
        self.robot.set_manual(on)
        self._manual_aisle = -1
        self._emit("mode", "Control manual activado" if on else "Modo automático: retoma el recorrido", "info")

    def set_pose(self, x: float, z: float, heading: float, speed: float) -> None:
        self.robot.set_pose(x, z, heading, speed)

    def set_bloque(self, b: int) -> None:
        b = int(min(max(b, 1), self.map.n_blocks))
        self.bloque = b
        a = self.map.aisles[self.map.block_aisles(b)[0]]
        self._emit("bloque", f"Bloque {b} elegido: el robot empieza en {self.map.aisle_label(a)}, entrada sur, mirando al fondo", "info")

    def inicio_bloque(self) -> tuple[float, float, float]:
        """Pone el robot en el inicio del bloque elegido (solo en Manual: en Auto manda la patrulla)."""
        x, z, h = self.map.block_start(self.bloque)
        if self.robot.mode == "manual":
            self.robot.set_pose(x, z, h, 0.0)
            self._manual_aisle = -1
            self._emit("bloque", f"Robot de vuelta al inicio del Bloque {self.bloque}", "info")
        return x, z, h

    def manual_inspect(self) -> None:
        if self.robot.mode == "manual":
            self._manual_sense(force=True)

    def external_event(self, etype: str, text: str, level: str = "info", bed: int | None = None, **fields: Any) -> dict[str, Any] | None:
        """Log an event from outside the engine (link with the real D1). With `bed` it also files an
        `incidencia` at the robot's position; its °C and % HR come from that bed's simulated microclimate
        (the demo has no onboard sensor) and are appended to `text`."""
        if bed is None:
            self._emit(etype, text, level)
            return None
        bed = int(min(max(bed, 0), self.n_beds - 1))
        plant = self.map.nearest_plant(self.robot.z)
        rec = self._record("incidencia", bed, plant, **fields)
        t_c = f"{rec['temp_c']:.1f}".replace(".", ",")
        self._emit(etype, f"{text} · {self.map.bed_label(bed)} · {t_c} °C {rec['rh_pct']:.0f} % HR (simulado)",
                   level, bed=bed, plant=plant, record_id=rec["id"])
        return rec

    def skip_to_next_patrol(self) -> None:
        """Fast-forward idle time until the next scheduled patrol starts."""
        guard = 0
        while not self.robot.is_busy() and not self.done() and guard < 20000:
            self.step()
            guard += 1

    # ----- main loop -----
    def done(self) -> bool:
        return self.day >= self.max_days

    def step(self) -> None:
        if self.done():
            self.playing = False
            return
        if self.robot.is_busy():
            dt = self.patrol_dt_s
        else:
            dt = min(self.idle_dt_s, (self.day + 1) * DAY_S - self.t)
            ps = self.day * DAY_S + self.patrol_start_h * 3600.0
            if self.t < ps and self.day not in self._patrol_days_done:
                dt = min(dt, ps - self.t)
            dt = max(dt, 1e-3)
        muddy = bool(self.out_P.sum() > 5.0 and self.alero_open)
        for e in self.robot.step(dt, muddy, self._capture):
            self._on_robot_event(e)
        if self.robot.mode == "manual":
            self._manual_sense()
        elif self.robot.state == "walking":
            self._routine_sample()
        self.t += dt
        new_day = int((self.t + 1e-6) // DAY_S)
        while new_day > self.day:
            self.day += 1
            self._on_new_day()
        self._maybe_start_patrol()
        self._process_pending()
        self._update_metrics()

    def run_until(self, max_days: int | None = None) -> Metrics:
        limit = max_days or self.max_days
        while self.day < limit:
            self.step()
        self.metrics.missed = int((self.ever_symptomatic & ~self.detected_mask).sum())
        return self.metrics

    # ----- serialization -----
    def _climate_now(self) -> dict[str, Any]:
        h = min(int(self._hour()), len(self.T_in) - 1)
        rh_in = float(self.RH_bed[:, h].mean())
        return {
            "T": float(self.out_T[h]), "RH": float(self.out_RH[h]), "precip": float(self.out_P[h]),
            "precip_day": float(self.out_P.sum()),
            "T_in": float(self.T_in[h]), "RH_in": rh_in,
            "RH_bed": [round(float(v), 1) for v in self.RH_bed[:, h]],
            "wet_h": float(self.bed_wet_h.max()), "wet_now": bool(self.wet_bh[:, h].any()),
            "vent_on": bool(self.vent_on_h[h]), "vent_forgotten": self.vent_forgotten, "alero_open": self.alero_open,
            "tunnel": bool(self.climate.get("enabled", True)),
        }

    def kpis(self) -> dict[str, Any]:
        r = self.robot
        hours = r.busy_s / 3600.0
        plants = self.frames
        return {
            "distance_km": round(r.odometry_m / 1000.0, 2),
            "field_hours": round(hours, 2),
            "captures": plants,
            "captures_per_hour": round(plants / hours, 0) if hours > 0 else 0,
            "patrols": self.patrols_done,
            "avg_patrol_min": round(self.patrol_minutes_total / self.patrols_done, 1) if self.patrols_done else None,
            "human_minutes_per_block": round(self.map.area_ha * self.human_h_per_ha * 60, 0),
            "block_area_ha": round(self.map.area_ha, 3),
            "records": len(self.records),
            "unsynced": self._unsynced,
            "unsynced_incidents": self._unsynced_inc,
            "contacts": r.contacts,
            "careful_passes": r.careful_passes,
            "plants_skipped": r.plants_skipped,
            "overflowing_plants": int(self.overflowing.sum()),
        }

    def snapshot(self) -> dict[str, Any]:
        robot = self.robot.snapshot()
        robot["sensors"] = {
            "frames": self.frames,
            "last_capture": self.last_capture,
            "recent_captures": self.recent_captures,
            "last_aruco": self.last_aruco,
            "probe": self.last_probe,
        }
        robot["patrol_plants"] = self.patrol_stats["plants"]
        robot["patrol_alerts"] = self.patrol_stats["alerts"]
        rt = self.alt.get("risk_trigger", {})
        nxt = self.next_patrol()
        recent = self.incident_records[-8:]
        return {
            "run_id": self.run_id,
            "day": self.day,
            "max_days": self.max_days,
            "clock": _clock(self.t),
            "sim_time_days": self.t / DAY_S,
            "realtime": self.robot.is_busy(),
            "done": self.done(),
            "next_patrol": {"day": nxt["day"], "clock": nxt["clock"]} if nxt else None,
            "seed": self.seed,
            "alternative": self.alt_code,
            "alternative_title": self.alt.get("title") or self.alt_code,
            "alternative_name": self.alt.get("name") or self.alt_code,
            "sensor_network": bool(rt.get("enabled") or self.alt.get("prioritize_by_risk")),
            "decision_threshold": float(self.det_cfg.get("decision", {}).get("score_threshold", 0.35)),
            "risk_levels": self.weather_cfg.get("risk_levels", {"medium": 0.05, "high": 0.15}),
            "weather": self._climate_now(),
            "weather_source": self.weather_source,
            "risk": {"per_disease": self.risks, "combined": self.combined, "per_bed": self.bed_risks.tolist()},
            "plants": base64.b64encode(self.states.tobytes()).decode("ascii"),
            "n_beds": self.n_beds,
            "n_plants": self.n_plants,
            "layout": self.map.layout(),
            "robot": robot,
            "events": self.events[-60:],
            "last_patrol": self.last_patrol_summary,
            "last_sync": self.last_sync,
            "connectivity": self.conn_mode,
            "incidents": recent,
            "kpis": self.kpis(),
            "metrics": {
                "infected": self.metrics.infected,
                "symptomatic": self.metrics.symptomatic,
                "detected": self.metrics.detected,
                "false_alarms": self.metrics.false_alarms,
                "missed": self.metrics.missed,
                "confirmed": self.metrics.confirmed,
                "treated": self.metrics.treated,
                "pending": len(self.pending),
                "first_focus_day": self.metrics.first_focus_day,
                "first_detection_day": self.metrics.first_detection_day,
                "first_alert_delivered_day": self.metrics.first_alert_delivered_day,
                "beds_infected_at_detection": self.metrics.beds_infected_at_detection,
                "plants_infected_at_detection": self.metrics.plants_infected_at_detection,
            },
            "field": {
                "plant_spacing_m": self.map.spacing,
                "bed_height_m": float(self.field.get("bed_height_m", 0.35)),
                "bed_width_m": self.map.bed_w,
                "pot_diameter_m": float(self.field.get("pot_diameter_m", 0.42)),
                "cultivation_mode": self.field.get("cultivation_mode", "macrotunnel"),
                "arch_height_m": float(self.field.get("macrotunnel", {}).get("arch_height_m", 4.2)),
            },
        }

    def static_payload(self) -> dict[str, Any]:
        return {
            "heights": [round(float(h), 3) for h in self.heights],
            "spread_l": [round(float(v), 3) for v in self.map.spread_l],
            "spread_r": [round(float(v), 3) for v in self.map.spread_r],
        }

    def records_csv(self) -> str:
        cols = ["id", "day", "clock", "kind", "fuente", "nave", "cama", "cama_global", "planta",
                "x", "z", "temp_c", "rh_pct", "clase", "confianza", "synced"]
        lines = [",".join(cols)]
        for r in self.records:
            lines.append(",".join("" if r.get(c) is None else str(r.get(c)) for c in cols))
        return "\n".join(lines) + "\n"
