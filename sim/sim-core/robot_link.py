"""Link with the real AgiBot D1 EDU through the bridge (robot_d1/d1_bridge.py).

The bridge runs in an Ubuntu VM and connects here as a WebSocket client (`/ws/robot`, contract
v1 in robot_d1/PROTOCOLO.md). This module keeps the link state, forwards teleop at 20 Hz while a
viewer drives in Manual (zeros included), relays the buttons (stand, lie, estop, resume) and turns
camera detections into `detection_stop`. Everything runs on the server's event loop: no locks, but
HTTP handlers that touch it must be `async def` (sync handlers run in a thread pool).
"""
from __future__ import annotations

import asyncio
import json
import math
import statistics
import time
from collections import deque
from typing import Any, Callable

from starlette.websockets import WebSocket, WebSocketDisconnect

from ruta_real import Orden, RutaParams, Seguidor, estaciones_scan, length, punto_en, rel_to_odom, rel_to_scene
from safety import SafetyConfig, geofence_check

TELEOP_HZ = 20.0
TELEOP_FRESH_S = 0.25  # a web teleop older than this becomes zeros (the bridge drops it at 0.3 s)
ESTOP_LOCAL_S = 0.6  # after a button, trust it over telemetry that may predate it
TELEMETRY_STALE_S = 1.0
INCIDENT_GAP_S = 6.0  # the same label reported again within this gap is the same finding
SAMPLE_GAP_S = 6.0  # ground truth: a new leaf starts when truth_label changes or after this gap
LATENCY_SAMPLES = 20
ACTIONS = ("stand", "lie", "estop", "resume")
LABELS_ES = {"sana": "sana", "oidio": "oídio", "alternaria": "alternaria", "heliothis": "Heliothis"}
SIMULATED_TH = "simulado (en producción: sensor a bordo)"
TELEMETRY_KEYS = ("t", "x", "y", "yaw", "vx", "vy", "wz", "state", "sdk_ok", "battery", "last_cmd_age_ms")
ZERO_TELEOP: dict[str, Any] = {"fwd": 0.0, "strafe": 0.0, "turn": 0.0, "fast": False}
REJECT_NOTE_S = 10.0  # a refused second bridge retries every few seconds: tell the viewer at most this often

# (event type, text, level) for bridge events; `real_alert` becomes a toast in the viewer.
BRIDGE_EVENTS: dict[str, tuple[str, str, str]] = {
    "estop": ("real_alert", "D1 real en parada de emergencia: velocidad cero hasta Reanudar", "danger"),
    "resume": ("real_alert", "D1 real reanudado: vuelve a aceptar órdenes", "ok"),
    "detection_hold_start": ("real_info", "D1 real quieto por detección", "info"),
    "detection_hold_end": ("real_info", "D1 real: termina la pausa por detección", "info"),
    "watchdog_zero": ("real_info", "D1 real sin órdenes frescas: velocidad cero", "info"),
    "sdk_error": ("real_alert", "D1 real: error del SDK", "danger"),
    "stood_up": ("real_info", "D1 real de pie", "ok"),
    "lay_down": ("real_info", "D1 real acostado", "info"),
    "battery_low": ("real_alert", "D1 real: batería baja, el puente no lo deja pararse", "danger"),
    "battery_critical": ("real_alert", "D1 real: batería crítica, el puente lo acuesta (cero primero)", "danger"),
}
ACTION_TEXT = {
    "estop": ("Orden al D1 real: parar (parada de emergencia)", "danger"),
    "resume": ("Orden al D1 real: reanudar", "info"),
    "stand": ("Orden al D1 real: pararse", "info"),
    "lie": ("Orden al D1 real: acostarse", "info"),
}

Notify = Callable[[str, str, str], None]  # (event type, text, level) → every open simulation


def label_es(label: str) -> str:
    return LABELS_ES.get(label.strip().lower(), label)


def _num(v: Any) -> float | None:
    """Finite float or None: NaN/inf would make the JSON sent to the browser invalid."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _axis(v: Any) -> float:
    f = _num(v)
    return 0.0 if f is None else max(-1.0, min(1.0, f))


class TruthTally:
    """Live hits / false alarms / misses against the jury viewer's labels, one verdict per leaf shown.

    Frames with the same `truth_label` (no gap longer than SAMPLE_GAP_S) are one leaf; the leaf counts
    as suspected if any of its frames was. The current leaf is included live, so a miss turns into a
    hit as soon as the camera flags it.
    """

    KEYS = ("hits", "false_alarms", "misses", "true_negatives", "class_match")

    def __init__(self) -> None:
        self.closed = {k: 0 for k in self.KEYS}
        self.frames = 0
        self.cur: dict[str, Any] | None = None

    @staticmethod
    def _verdict(s: dict[str, Any]) -> dict[str, int]:
        sick = s["truth"] != "sana"
        return {
            "hits": int(sick and s["suspected"]),
            "false_alarms": int(not sick and s["suspected"]),
            "misses": int(sick and not s["suspected"]),
            "true_negatives": int(not sick and not s["suspected"]),
            "class_match": int(sick and s["match"]),
        }

    def add(self, truth: str, sospecha: bool, label: str, now: float) -> None:
        truth, label = truth.strip().lower(), label.strip().lower()
        cur = self.cur
        if cur is not None and (cur["truth"] != truth or now - cur["last"] > SAMPLE_GAP_S):
            for k, v in self._verdict(cur).items():
                self.closed[k] += v
            cur = None
        if cur is None:
            cur = self.cur = {"truth": truth, "suspected": False, "match": False, "last": now, "frames": 0}
        cur["suspected"] = cur["suspected"] or sospecha
        cur["match"] = cur["match"] or (sospecha and label == truth)
        cur["frames"] += 1
        cur["last"] = now
        self.frames += 1

    def snapshot(self) -> dict[str, Any] | None:
        if self.cur is None:
            return None
        out: dict[str, Any] = dict(self.closed)
        for k, v in self._verdict(self.cur).items():
            out[k] += v
        out["leaves"] = out["hits"] + out["false_alarms"] + out["misses"] + out["true_negatives"]
        out["frames"] = self.frames
        out["current"] = {"truth": label_es(self.cur["truth"]), "suspected": self.cur["suspected"]}
        return out


def _a_campo(rel: list[tuple[float, float]], p: RutaParams) -> list[tuple[float, float]]:
    """Ruta reducida -> tamaño real del invernadero (para dibujarla en el campo y mover el gemelo por él)."""
    e = max(p.escala, 1e-6)
    return [(f / e, l / e) for f, l in rel]


class RobotLink:
    """State of the link with the bridge; at most one bridge at a time (the newest replaces the old)."""

    def __init__(self, hold_s: float = 4.0, notify: Notify | None = None, safety: SafetyConfig | None = None) -> None:
        self.hold_s = float(hold_s)
        self.safety = safety or SafetyConfig.from_env()
        self.notify: Notify = notify or (lambda *_: None)
        self._ws: WebSocket | None = None
        self._wake: asyncio.Event | None = None
        self._outbox: deque[dict[str, Any]] = deque(maxlen=64)
        self.link_id = 0  # +1 per bridge connection: the viewer re-anchors the twin's odometry
        self.connected = False
        self.connected_at: float | None = None
        self.disconnected_at: float | None = None
        self.peer: str | None = None
        self.hello: dict[str, Any] | None = None
        self.telemetry: dict[str, Any] | None = None
        self.telemetry_at: float | None = None
        self._lat: deque[float] = deque(maxlen=LATENCY_SAMPLES)
        self._estop_local = False
        self._estop_local_t = -1e9
        self.hold_until = 0.0
        self._teleop: dict[int, tuple[dict[str, Any], float]] = {}  # viewer -> (last command, monotonic t)
        self._manual: set[int] = set()
        # Viewers that were driving when a bridge (re)connected: their moving keys count again only
        # after they send a neutral teleop (keys released). Restoring the link must not restart motion.
        self._need_release: set[int] = set()
        self._last_reject_note = -1e9
        self._was_driving = False
        self.seq = 0
        self.log: deque[dict[str, Any]] = deque(maxlen=60)
        self._log_id = 0
        self.detections = 0
        self.incidents = 0
        self.last_detection: dict[str, Any] | None = None
        self._open: dict[str, Any] | None = None  # finding currently reported (dedupe)
        self.truth = TruthTally()
        # ----- safety barriers (see safety.py) -----
        self._pose: dict[int, tuple[float, float, float, Any]] = {}  # viewer -> (x, z, monotonic t, FieldMap)
        self.geo_violation: tuple[str, str] | None = None  # current geofence breach (None = inside)
        self._geo_tripped = False
        self._link_stale = False
        self._batt_low = False
        self._batt_crit_sent = False
        self.panel: dict[str, Any] | None = None  # last heartbeat of the camera panel
        self.panel_at: float | None = None  # monotonic
        self._video_lost_since: float | None = None
        self._video_block = False
        self._video_noted = False
        self._zero_until = 0.0
        # ----- Ruta real (D1 real sigue la ruta Auto escalada) -----
        self._ruta_estado = "inactiva"  # inactiva | simulacion | en_marcha | pausa | terminada | cancelada
        self._ruta_motivo = ""
        self._ruta_params = RutaParams()
        self._ruta_scene: list[tuple[float, float]] = []
        self._ruta_total = 0.0
        self._ruta_follower: Seguidor | None = None
        self._ruta_orden: Orden | None = None
        self._ruta_arranque = 0.0  # monotonic: zeros until then (the bridge wants a neutral before moving)
        self._ruta_ref: tuple[float, float, float, float] | None = None  # (t, x, y, yaw) of the last progress
        # Mirar a los lados: en cada estación el D1 se detiene, gira a la izquierda, espera, a la derecha, espera y vuelve.
        self._scan_est: list[float] = []
        self._scan_fase: list[tuple[float, float]] = []  # pendientes: (desvío de rumbo en rad, segundos mirando)
        self._scan_yaw0 = 0.0
        self._scan_resta = 0.0  # segundos que faltan mirando el lado actual (None si girando)
        self._scan_girando = False
        self._scan_t = 0.0
        self._scan_lado: str | None = None  # "izquierda" | "derecha" mientras mira un lado
        self._geo_sala = False  # ruta reducida en una sala: la geocerca de la escena no aplica hasta salir de Manual
        self._ruta_s = 0.0  # avance mostrado del gemelo (solo crece: el ruido de odometría no lo hace retroceder)
        self._sin_video_desde: float | None = None
        self.trips: dict[str, int] = {"geofence": 0, "battery": 0, "link": 0, "video": 0, "viewer": 0}

    # ----- bookkeeping -----
    def _log(self, kind: str, text: str, level: str = "info") -> None:
        self._log_id += 1
        self.log.append({"id": self._log_id, "t": round(time.time(), 3), "kind": kind, "level": level, "text": text})

    def _event(self, etype: str, text: str, level: str) -> None:
        self._log(etype, text, level)
        self.notify(etype, text, level)

    @property
    def estop(self) -> bool:
        now = time.monotonic()
        tel_fresh = self.telemetry_at is not None and time.time() - self.telemetry_at < TELEMETRY_STALE_S
        if now - self._estop_local_t < ESTOP_LOCAL_S or not tel_fresh or not self.telemetry:
            return self._estop_local
        return self.telemetry.get("state") == "estop"

    def _set_estop(self, on: bool) -> None:
        self._estop_local = on
        self._estop_local_t = time.monotonic()

    def _enqueue(self, msg: dict[str, Any]) -> bool:
        if not self.connected:
            return False
        self._outbox.append(msg)
        if self._wake is not None:
            self._wake.set()
        return True

    # ----- viewer side -----
    def set_manual(self, key: int, on: bool) -> None:
        """A viewer (one per web socket) entered or left Manual."""
        if on:
            self._manual.add(key)
        else:
            self._manual.discard(key)
            self._teleop.pop(key, None)
            self._need_release.discard(key)
            if not self._manual:
                self._geo_sala = False  # al salir de Manual vuelve la geocerca normal

    def manual_active(self) -> bool:
        return bool(self._manual)

    def set_teleop(self, msg: dict[str, Any], key: int) -> None:
        """Keys of one viewer. Only viewers in Manual count when the next teleop is built."""
        cmd = {
            "fwd": _axis(msg.get("fwd")),
            "strafe": _axis(msg.get("strafe")),
            "turn": _axis(msg.get("turn")),
            "fast": msg.get("fast") is True,  # contract: bool; "false" or 1 must not mean fast
        }
        self._teleop[key] = (cmd, time.monotonic())
        if not (cmd["fwd"] or cmd["strafe"] or cmd["turn"]):
            self._need_release.discard(key)

    def _drive_command(self, now: float) -> dict[str, Any]:
        """Fresh commands of viewers in Manual: the latest one asking to move wins, otherwise zeros.

        A viewer in Manual with no keys pressed sends zeros at 20 Hz; mixing its zeros with the
        driver's keys made the robot stutter (and, with the bridge's immediate stop, not move at all).
        """
        moving = [
            (t, cmd)
            for k, (cmd, t) in self._teleop.items()
            if k in self._manual
            and k not in self._need_release
            and now - t <= TELEOP_FRESH_S
            and (cmd["fwd"] or cmd["strafe"] or cmd["turn"])
        ]
        if not moving:
            return dict(ZERO_TELEOP)
        return self._cap(dict(max(moving, key=lambda x: x[0])[1]))

    def _cap(self, cmd: dict[str, Any]) -> dict[str, Any]:
        """Global speed limit (default 0,3 m/s): scale the axes against the bridge's own limits."""
        cap = self.safety.speed_cap_mps
        if cap <= 0:
            return cmd
        lim = (self.hello or {}).get("limits") or {}
        vx = lim.get("vx_max") or 0.4
        vy = lim.get("vy_max") or 0.25
        cmd["fwd"] = max(-1.0, min(1.0, cmd["fwd"])) * min(1.0, cap / vx)
        cmd["strafe"] = max(-1.0, min(1.0, cmd["strafe"])) * min(1.0, cap / vy)
        cmd["fast"] = False  # "fast" doubles vx: not allowed under a global cap
        return cmd

    def _blocked_reason(self) -> str | None:
        """Why teleop is forced to zero right now (besides estop/detection), or None."""
        if self._link_stale:
            return "telemetría vieja"
        if self.geo_violation is not None:
            return "geocerca"
        if self._video_block:
            return "sin video"
        if self.estop_battery_block():
            return "batería"
        return None

    def estop_battery_block(self) -> bool:
        b = self._battery()
        return b is not None and b < self.safety.battery_lie_below

    def action(self, name: str) -> bool:
        """Relay a button; returns False when the name is unknown or no bridge is connected."""
        if name not in ACTIONS:
            return False
        if name == "stand":
            b = self._battery()
            if b is not None and b < self.safety.battery_stand_min:
                self.trips["battery"] += 1
                self._event(
                    "real_alert",
                    f"Batería {b:.0f} % (< {self.safety.battery_stand_min:.0f} %): no se permite pararse. Carga el D1 antes.",
                    "danger",
                )
                return False
        if name == "estop":
            self.ruta_cancel("PARADA: la ruta se cancela, pulsa Ruta real de nuevo", "danger")
        if name in ("estop", "resume"):
            self._set_estop(name == "estop")
        sent = self._enqueue({"type": "action", "name": name})
        if sent:
            text, level = ACTION_TEXT[name]
            self._event("real_info", text, level)
        return sent

    def teleop_tick(self) -> dict[str, Any] | None:
        """Next teleop for the bridge, or None when nobody drives. Zeros while stale, stopped or held."""
        driving = self.connected and self.manual_active()
        if self._link_stale and self.connected:
            self._was_driving = driving
            return None  # (c) telemetry is old: stop sending orders; the bridge's 0,3 s TTL gives zero
        if not driving:
            if time.monotonic() < self._zero_until and self.connected:
                self.seq += 1
                return {"type": "teleop", **ZERO_TELEOP, "seq": self.seq}  # (f) browser gone: explicit zeros
            if not self._was_driving:
                return None
            cmd = dict(ZERO_TELEOP)  # one explicit stop on leaving Manual
        else:
            now = time.monotonic()
            stopped = self.estop or now < self.hold_until or self._blocked_reason() is not None
            if self._ruta_active():
                cmd = self._ruta_step(now)
            else:
                cmd = dict(ZERO_TELEOP) if stopped else self._drive_command(now)
        self._was_driving = driving
        self.seq += 1
        return {"type": "teleop", **cmd, "seq": self.seq}

    # ----- safety barriers -----
    def _battery(self) -> float | None:
        tel = self.telemetry
        if not self.connected or not tel or self.telemetry_at is None:
            return None
        if tel.get("sdk_ok") is False:
            return None  # without the SDK the bridge reports 0 %: not a real reading
        return _num(tel.get("battery"))

    def update_pose(self, key: int, x: float, z: float, fm: Any) -> None:
        """Pose of the twin in the scene (the viewer sends it at 10 Hz in Manual); feeds the geofence."""
        if math.isfinite(x) and math.isfinite(z):
            self._pose[key] = (x, z, time.monotonic(), fm)

    def panel_update(self, data: dict[str, Any]) -> None:
        """Heartbeat of the camera panel (panel_demo.py --sim-url): camera state and stable prediction."""
        keep = ("cam_ok", "fps", "clase", "confianza", "p_enfermedad", "sospecha", "estable", "p_hoja", "frame_age_s")
        self.panel = {k: data.get(k) for k in keep}
        self.panel["cam_ok"] = bool(data.get("cam_ok"))
        self.panel_at = time.monotonic()

    def video_guard_active(self) -> bool:
        mode = self.safety.video_guard
        return mode == "on" or (mode == "auto" and self.panel_at is not None)

    def video_ok(self) -> bool:
        return (
            self.panel is not None
            and self.panel_at is not None
            and time.monotonic() - self.panel_at <= self.safety.panel_fresh_s
            and bool(self.panel.get("cam_ok"))
        )

    def viewer_closed(self, key: int) -> None:
        """(f) A browser went away: if it was driving, zeros now (the bridge's TTL would do it anyway)."""
        was = key in self._manual
        self._pose.pop(key, None)
        if was:
            self.ruta_cancel("se cerró el navegador: ruta cancelada", "danger")
        if was and self.connected:
            self._zero_until = time.monotonic() + self.safety.zero_after_viewer_s
            self.trips["viewer"] += 1
            self._event("real_alert", "Se cerró el navegador que conducía: el D1 recibe ceros y se detiene", "danger")

    def _pose_now(self) -> tuple[float, float, Any] | None:
        now = time.monotonic()
        best = None
        for k, (x, z, t, fm) in self._pose.items():
            if k in self._manual and now - t <= self.safety.pose_fresh_s and (best is None or t > best[0]):
                best = (t, x, z, fm)
        return None if best is None else (best[1], best[2], best[3])

    def guard_tick(self) -> None:
        """Evaluate every barrier; called at 20 Hz by the sender and directly by the tests."""
        sf = self.safety
        now = time.monotonic()
        if not self.connected:
            self._link_stale = False
            self._geo_tripped = False
            self.geo_violation = None
            self._video_block = False
            return
        # (c) telemetry freshness
        ref = self.telemetry_at if self.telemetry_at is not None else self.connected_at
        stale = ref is not None and time.time() - ref > sf.telemetry_stale_s
        if stale and not self._link_stale:
            self._link_stale = True
            self.trips["link"] += 1
            self._event(
                "real_alert",
                f"Telemetría del D1 vieja (> {sf.telemetry_stale_s:g} s): el simulador dejó de mandar órdenes",
                "danger",
            )
        elif not stale and self._link_stale:
            self._link_stale = False
            self._need_release = set(self._manual)  # keys must be released before moving again
            self._event("real_info", "Telemetría del D1 recuperada: suelta y vuelve a pulsar para conducir", "ok")
        # (b) battery
        b = self._battery()
        if b is not None:
            if b < sf.battery_stand_min and not self._batt_low:
                self._batt_low = True
                self._event("real_alert", f"Batería baja ({b:.0f} %): no se permite pararse", "warn")
            elif b >= sf.battery_stand_min + 3 and self._batt_low:
                self._batt_low = False
            state = (self.telemetry or {}).get("state")
            if b < sf.battery_lie_below and state not in ("lying", "passive") and not self._batt_crit_sent:
                self._batt_crit_sent = True
                self.trips["battery"] += 1
                self._event("real_alert", f"Batería crítica ({b:.0f} %): se acuesta al D1 (cero primero)", "danger")
                self._enqueue({"type": "action", "name": "lie"})
            elif b >= sf.battery_lie_below + 3:
                self._batt_crit_sent = False
        # (a) geofence
        pose = self._pose_now() if sf.geofence and not self._ruta_suspends_geofence() else None
        self.geo_violation = None if pose is None else geofence_check(pose[2], pose[0], pose[1], sf.bed_margin_m)
        if self.geo_violation is None:
            self._geo_tripped = False
        elif not self._geo_tripped:
            self._geo_tripped = True
            self.trips["geofence"] += 1
            self._event("real_alert", f"{self.geo_violation[1][0].upper()}{self.geo_violation[1][1:]}: parada de emergencia", "danger")
            if not self.estop:
                self.action("estop")
        # (d) video
        if self.video_guard_active() and not self.video_ok():
            if self._video_lost_since is None:
                self._video_lost_since = now
            lost = now - self._video_lost_since
            if lost > sf.video_loss_s and self.manual_active() and not self._video_block:
                self._video_block = True
                self._video_noted = False
        else:
            if self._video_block:
                self._need_release = set(self._manual)
                self._event("real_info", "Video recuperado: suelta y vuelve a pulsar para conducir", "ok")
            self._video_lost_since = None
            self._video_block = False
            self._video_noted = False
        if self._ruta_active():
            if self._video_block and self._sin_video_desde is None:
                self._sin_video_desde = now
                self._event("real_alert", "Ruta real en pausa: se cortó el video; sigue sola si vuelve en 12 s", "warn")
            elif not self._video_block and self._sin_video_desde is not None:
                self._sin_video_desde = None
                self._event("real_info", "Video de vuelta: la ruta sigue", "ok")
            reason = None
            if self.estop:
                reason = "parada de emergencia"
            elif self._link_stale:
                reason = "telemetría vieja"
            elif self.geo_violation is not None:
                reason = "geocerca"
            elif self._video_block and self._sin_video_desde is not None and now - self._sin_video_desde > 12.0:
                reason = "sin video más de 12 s"
            elif b is not None and b < sf.battery_lie_below:
                reason = "batería crítica"
            elif not self.manual_active():
                reason = "se salió de Manual"
            if reason:
                self.ruta_cancel(f"ruta cancelada ({reason}); pulsa Ruta real de nuevo", "danger")
        if self._video_block and not self._video_noted and self._driving_or_moving():
            self._video_noted = True
            self.trips["video"] += 1
            self._event("real_alert", "Sin video: robot detenido", "danger")

    # ----- Ruta real -----
    def _ruta_active(self) -> bool:
        return self._ruta_estado in ("en_marcha", "pausa")

    def _ruta_suspends_geofence(self) -> bool:
        """A reduced route (escala < 1) does not match the scene's beds: the drift limit guards it instead."""
        return (self._ruta_active() and self._ruta_params.escala < 0.999) or self._geo_sala

    def _odom(self) -> tuple[float, float, float] | None:
        tel = self.telemetry
        if not tel or self.telemetry_at is None:
            return None
        x, y, yaw = _num(tel.get("x")), _num(tel.get("y")), _num(tel.get("yaw"))
        return None if x is None or y is None or yaw is None else (x, y, yaw)

    def _ruta_refuse(self, text: str) -> bool:
        self._event("real_alert", f"Ruta real no iniciada: {text}", "warn")
        return False

    def ruta_dryrun(self, rel: list[tuple[float, float]], params: RutaParams, scene_pose: tuple[float, float, float]) -> bool:
        """Only draws the scaled route in the scene (anchored at the twin's pose) so the operator can check it fits."""
        if self._ruta_active():
            return False
        self._ruta_params = params
        self._ruta_scene = rel_to_scene(rel, *scene_pose)  # tamaño real: lo que el D1 de verdad va a recorrer
        self._ruta_total = length(rel)
        self._ruta_estado, self._ruta_motivo = "simulacion", ""
        self._ruta_follower = None
        self._log("ruta", f"Simulación de ruta: {len(rel) - 1} tramos, {self._ruta_total:.1f} m, escala {params.escala:g}")
        return True

    def ruta_start(self, rel: list[tuple[float, float]], params: RutaParams, scene_pose: tuple[float, float, float]) -> bool:
        """Start following `rel` from the robot's current pose (the twin's pose is the anchor)."""
        if self._ruta_active():
            return self._ruta_refuse("ya hay una ruta en marcha")
        if not self.connected or self.hello is None:
            return self._ruta_refuse("no hay D1 conectado")
        if self.estop:
            return self._ruta_refuse("hay parada de emergencia: pulsa Reanudar")
        reason = self._blocked_reason()
        if reason:
            return self._ruta_refuse(f"bloqueado por seguridad ({reason})")
        if not self.manual_active():
            return self._ruta_refuse("pasa a Manual primero")
        odom = self._odom()
        if odom is None:
            return self._ruta_refuse("el D1 no da odometría")
        if (self.telemetry or {}).get("state") not in ("standing", "moving"):
            return self._ruta_refuse("el D1 debe estar de pie: pulsa Pararse primero")
        if len(rel) < 2:
            return self._ruta_refuse("la ruta no tiene tramos")
        self._ruta_params = params
        self._ruta_scene = rel_to_scene(rel, *scene_pose)  # 1:1 con el D1: el gemelo copia la odometría real
        self._ruta_follower = Seguidor(rel_to_odom(rel, *odom), params)
        self._scan_est = estaciones_scan(rel, params)
        self._geo_sala = params.escala < 0.999
        self._ruta_s = 0.0
        self._sin_video_desde = None
        self._scan_fase, self._scan_lado, self._scan_girando = [], None, False
        self._ruta_total = self._ruta_follower.total
        self._ruta_estado, self._ruta_motivo = "en_marcha", ""
        self._ruta_orden = None
        self._ruta_arranque = time.monotonic() + 1.2  # neutro corto: recién parado el D1 aún rechaza move()
        self._ruta_ref = None
        for k in list(self._teleop):
            self._need_release.add(k)  # keys held now must not count as a manual override
        extra = " La geocerca de la escena se suspende: manda el límite de deriva." if params.escala < 0.999 else ""
        self._event(
            "real_info",
            f"Ruta real iniciada: {self._ruta_follower.tramos} tramos, {self._ruta_total:.1f} m, escala {params.escala:g}, "
            f"≤ {params.v_recta:g} m/s, deriva máx. {params.deriva_max_m:g} m.{extra}",
            "ok",
        )
        return True

    def ruta_cancel(self, reason: str, level: str = "warn", estado: str = "cancelada") -> None:
        """Cancel (or finish) the route. Cancelling always requires pressing "Ruta real" again."""
        if self._ruta_estado in ("simulacion",) and estado == "cancelada":
            self._ruta_estado, self._ruta_scene, self._ruta_motivo = "inactiva", [], ""
            return
        if not self._ruta_active():
            return
        self._ruta_estado, self._ruta_motivo = estado, reason
        self._ruta_follower = None
        self._scan_est, self._scan_fase, self._scan_lado, self._scan_girando = [], [], None, False
        self._event("real_alert" if level != "ok" else "real_info", f"Ruta real: {reason}", level)

    def _ruta_step(self, now: float) -> dict[str, Any]:
        zero = dict(ZERO_TELEOP)
        fol = self._ruta_follower
        if fol is None:
            return zero
        if self._video_block and not self.estop:
            self._ruta_estado = "pausa"  # sin video: quieto; guard_tick la cancela si dura más de 12 s
            self._ruta_ref = None
            return zero
        if self.estop or self._blocked_reason() is not None:
            self.ruta_cancel("ruta cancelada por una barrera de seguridad; pulsa Ruta real de nuevo", "danger")
            return zero
        if self._drive_command(now) != ZERO_TELEOP:  # the operator touched WASD: manual wins
            self.ruta_cancel("ruta cancelada: se pulsó una tecla de conducción", "warn")
            return zero
        if now < self.hold_until:
            self._ruta_estado = "pausa"  # detection_stop: zero, resumes by itself afterwards
            return zero
        if now < self._ruta_arranque:
            return zero  # short neutral right after pressing Ruta real
        if self._ruta_estado == "pausa":
            self._ruta_estado = "en_marcha"
            self._log("ruta", "Ruta real: termina la pausa, reanuda")
        odom = self._odom()
        if odom is None:
            self.ruta_cancel("sin odometría del D1: ruta cancelada", "danger")
            return zero
        scan = self._scan_step(now, fol, odom)
        if scan is not None:
            return scan
        o = fol.step(*odom)
        self._ruta_orden = o
        if self._scan_est and o.estado == "en_marcha" and fol.s_here >= self._scan_est[0]:
            self._scan_est.pop(0)
            a = math.radians(self._ruta_params.angulo_scan_deg)
            h = self._ruta_params.pausa_scan_s
            self._scan_yaw0 = odom[2]
            self._scan_fase = [(a, h), (-a, h), (0.0, 0.0)]
            self._scan_girando, self._scan_t = True, now
            self._log("ruta", f"Ruta real: parada para mirar a los lados (quedan {len(self._scan_est)})")
            return zero
        if o.estado == "terminada":
            self.ruta_cancel("completada", "ok", estado="terminada")
            return zero
        if o.estado == "deriva":
            self.ruta_cancel(
                f"el D1 se desvió {o.deriva_m:.2f} m del camino previsto (límite {self._ruta_params.deriva_max_m:g} m): detenido",
                "danger",
            )
            return zero
        # stall: commanding motion but the odometry does not change (not standing yet, SDK refusing...)
        ref = self._ruta_ref
        moved = ref is None or math.hypot(odom[0] - ref[1], odom[1] - ref[2]) + 0.3 * abs(math.atan2(math.sin(odom[2] - ref[3]), math.cos(odom[2] - ref[3]))) >= 0.05
        if ref is None or moved or (o.v == 0.0 and o.wz == 0.0):
            self._ruta_ref = (now, *odom)
        elif now - ref[0] > 5.0:
            self.ruta_cancel("el D1 no avanza aunque se le ordena (¿no está de pie del todo?): ruta cancelada", "danger")
            return zero
        lim = (self.hello or {}).get("limits") or {}
        vx, wzm = lim.get("vx_max") or 0.4, lim.get("wz_max") or 0.6
        v = min(o.v, self._ruta_params.v_recta)
        if self.safety.speed_cap_mps > 0:
            v = min(v, self.safety.speed_cap_mps)
        return {"fwd": max(0.0, min(1.0, v / vx)), "strafe": 0.0, "turn": max(-1.0, min(1.0, o.wz / wzm)), "fast": False}

    def _scan_step(self, now: float, fol: Seguidor, odom: tuple[float, float, float]) -> dict[str, Any] | None:
        """Giro en el sitio hacia cada lado y espera; None cuando no hay escaneo en curso (sigue la ruta)."""
        if not self._scan_fase:
            return None
        dt = max(0.0, min(0.2, now - self._scan_t))
        self._scan_t = now
        objetivo, espera = self._scan_fase[0]
        err = math.atan2(math.sin(self._scan_yaw0 + objetivo - odom[2]), math.cos(self._scan_yaw0 + objetivo - odom[2]))
        self._ruta_ref = (now, *odom)  # girar en el sitio no es un atasco
        if self._scan_girando:
            if abs(err) > 0.08:
                lim = (self.hello or {}).get("limits") or {}
                wzm = lim.get("wz_max") or 0.6
                wz = math.copysign(max(0.15, min(self._ruta_params.wz_scan, 1.5 * abs(err))), err)
                self._scan_lado = None
                return {"fwd": 0.0, "strafe": 0.0, "turn": max(-1.0, min(1.0, wz / wzm)), "fast": False}
            self._scan_girando, self._scan_resta = False, espera
            self._scan_lado = "izquierda" if objetivo > 0 else "derecha" if objetivo < 0 else None
        self._scan_resta -= dt
        if self._scan_resta > 0:
            return dict(ZERO_TELEOP)  # mirando ese lado: la cámara del panel clasifica lo que tiene enfrente
        self._scan_fase.pop(0)
        self._scan_lado = None
        self._scan_girando = bool(self._scan_fase)
        return dict(ZERO_TELEOP) if self._scan_fase else None

    def scan_lado(self) -> str | None:
        """Lado al que mira el D1 en una parada de escaneo ("izquierda" | "derecha"), o None."""
        return self._scan_lado if self._ruta_active() else None

    def ruta_gemelo(self) -> tuple[float, float, float] | None:
        """Pose del gemelo en la escena durante la ruta: el avance real escalado sobre la ruta a tamaño de campo
        y el giro real (mirar a los lados) sumado al rumbo del pasillo."""
        fol, odom = self._ruta_follower, self._odom()
        if fol is None or odom is None or len(self._ruta_scene) < 2 or fol.total <= 0:
            return None
        largo = length(self._ruta_scene)
        self._ruta_s = max(self._ruta_s, fol.s_here)
        x, z, h = punto_en(self._ruta_scene, self._ruta_s / fol.total * largo)
        giro = math.atan2(math.sin(odom[2] - fol.yaw_ruta), math.cos(odom[2] - fol.yaw_ruta))
        return x, z, h + giro

    def ruta_status(self) -> dict[str, Any]:
        o = self._ruta_orden
        fol = self._ruta_follower
        show = self._ruta_estado in ("simulacion", "en_marcha", "pausa")
        return {
            "estado": self._ruta_estado,
            "motivo": self._ruta_motivo,
            "tramo": o.tramo if (o and fol) else (1 if fol else 0),
            "tramos": fol.tramos if fol else max(0, len(self._ruta_scene) - 1),
            "restante_m": round(o.restante_m, 2) if (o and fol) else round(self._ruta_total, 2),
            "total_m": round(self._ruta_total, 2),
            "deriva_m": round(o.deriva_m, 2) if (o and fol) else 0.0,
            "escala": self._ruta_params.escala,
            "largo_max_m": self._ruta_params.largo_max_m,
            "deriva_max_m": self._ruta_params.deriva_max_m,
            "puntos": [[round(x, 3), round(z, 3)] for x, z in self._ruta_scene] if show else [],
            "gemelo": None,  # el gemelo sigue la odometría 1:1 (RobotView.tsx); ruta_gemelo() queda para escala de campo
            "mirando": self.scan_lado(),
            "escaneos_pendientes": len(self._scan_est),
        }

    def _driving_or_moving(self) -> bool:
        tel = self.telemetry or {}
        moving = any(abs(tel.get(k) or 0.0) > 0.02 for k in ("vx", "vy", "wz"))
        asked = any(
            c["fwd"] or c["strafe"] or c["turn"]
            for k, (c, t) in self._teleop.items()
            if k in self._manual and time.monotonic() - t <= TELEOP_FRESH_S
        )
        return moving or asked

    def safety_status(self) -> dict[str, Any]:
        sf = self.safety
        lost = 0.0 if self._video_lost_since is None else round(time.monotonic() - self._video_lost_since, 1)
        panel_age = None if self.panel_at is None else round(time.monotonic() - self.panel_at, 1)
        b = self._battery()
        return {
            "config": {
                "speed_cap_mps": sf.speed_cap_mps,
                "geofence": sf.geofence,
                "bed_margin_m": sf.bed_margin_m,
                "battery_stand_min": sf.battery_stand_min,
                "battery_lie_below": sf.battery_lie_below,
                "video_guard": sf.video_guard,
                "video_loss_s": sf.video_loss_s,
            },
            "geofence_violation": self.geo_violation[1] if self.geo_violation else None,
            "battery_low": b is not None and b < sf.battery_stand_min,
            "battery_critical": b is not None and b < sf.battery_lie_below,
            "link_stale": self._link_stale,
            "video_guard_active": self.video_guard_active(),
            "video_ok": self.video_ok(),
            "video_lost_s": lost,
            "video_block": self._video_block,
            "blocked": self._blocked_reason(),
            "trips": dict(self.trips),
            "panel": None if self.panel is None else {**self.panel, "age_s": panel_age, "fresh": panel_age is not None and panel_age <= sf.panel_fresh_s},
        }

    # ----- bridge side -----
    def bridge_alive(self) -> bool:
        """The connected bridge sent telemetry within TELEMETRY_STALE_S (a half-open socket goes quiet)."""
        return self.connected and self.telemetry_at is not None and time.time() - self.telemetry_at < TELEMETRY_STALE_S

    async def _reject(self, ws: WebSocket) -> None:
        """A second bridge while the current one is alive: refuse it instead of taking turns with it.

        "Newest replaces the old" plus the bridges' auto-reconnect made two bridges swap the link every
        ~0.5 s; a stop pressed while the other one held the link never reached the robot that came back.
        """
        peer = f"{ws.client.host}:{ws.client.port}" if ws.client else "desconocido"
        now = time.monotonic()
        if now - self._last_reject_note >= REJECT_NOTE_S:
            self._last_reject_note = now
            self._event(
                "real_alert",
                f"Otro puente intentó conectarse desde {peer} y se rechazó: el D1 sigue con el de {self.peer}. "
                "¿Hay un puente --mock o fake_bridge olvidado?",
                "danger",
            )
        try:
            await ws.close(code=4001, reason="ya hay un puente conectado")
        except Exception:  # noqa: BLE001
            pass

    async def serve(self, ws: WebSocket) -> None:
        """Run one accepted bridge connection until it closes."""
        if self.bridge_alive():
            await self._reject(ws)
            return
        self.link_id += 1
        my_id = self.link_id
        old, self._ws = self._ws, ws
        self._wake = asyncio.Event()
        self._outbox.clear()
        self.connected = True
        self.connected_at = time.time()
        self.peer = f"{ws.client.host}:{ws.client.port}" if ws.client else None
        self.hello = None
        self.telemetry = None
        self.telemetry_at = None
        self._lat.clear()
        self._was_driving = False
        self._need_release = set(self._manual)
        self._log("link", f"Puente conectado desde {self.peer or 'desconocido'}; esperando hello")
        if self._estop_local:
            # The stop is sticky here too: a bridge that (re)connects gets it before anything else,
            # even if it was pressed while another bridge (or none) held the link.
            self._outbox.append({"type": "action", "name": "estop"})
            self._estop_local_t = time.monotonic()
            self._log("link", "Parada de emergencia vigente: reenviada al puente; Reanudar para quitarla", "danger")
        if old is not None:
            try:
                await old.close(code=4000, reason="reemplazado por un puente nuevo")
            except Exception:  # noqa: BLE001 — the old socket may already be gone
                pass
        sender = asyncio.create_task(self._sender(ws, my_id))
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(msg, dict):
                    self.on_message(msg)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            sender.cancel()
            if self.link_id == my_id:
                self._ws = None
                self._wake = None
                self.connected = False
                self.disconnected_at = time.time()
                self._event("real_link", "Se perdió el enlace con el D1 real: el puente lo deja quieto y reintenta", "warn")

    async def _sender(self, ws: WebSocket, my_id: int) -> None:
        """Single writer to the bridge: queued actions first, teleop on a steady 20 Hz clock."""
        period = 1.0 / TELEOP_HZ
        next_t = time.perf_counter()
        try:
            while self.link_id == my_id:
                wake = self._wake
                if wake is not None:
                    wake.clear()
                while self._outbox:
                    await ws.send_json(self._outbox.popleft())
                now = time.perf_counter()
                if now >= next_t:
                    self.guard_tick()
                    msg = self.teleop_tick()
                    if msg is not None:
                        await ws.send_json(msg)
                    next_t += period
                    if now - next_t > 0.5:
                        next_t = now + period
                timeout = max(0.0, next_t - time.perf_counter())
                if wake is None:
                    await asyncio.sleep(timeout)
                    continue
                try:
                    await asyncio.wait_for(wake.wait(), timeout)
                except asyncio.TimeoutError:
                    pass
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            return

    def on_message(self, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind == "hello":
            limits = msg.get("limits") if isinstance(msg.get("limits"), dict) else {}
            self.hello = {
                "robot": str(msg.get("robot") or "D1 EDU"),
                "mock": bool(msg.get("mock", False)),
                "version": msg.get("version"),
                "limits": {k: _num(v) for k, v in limits.items()},
            }
            what = "robot simulado del puente" if self.hello["mock"] else "robot real"
            self._event("real_link", f"{self.hello['robot']} conectado ({what})", "ok")
        elif kind == "telemetry":
            tel: dict[str, Any] = {}
            for k in TELEMETRY_KEYS:
                v = msg.get(k)
                tel[k] = v if k in ("state", "sdk_ok") else _num(v)
            tel["state"] = str(tel["state"]) if tel["state"] is not None else None
            tel["sdk_ok"] = bool(tel["sdk_ok"]) if tel["sdk_ok"] is not None else None
            now = time.time()
            if tel["t"] is not None:
                self._lat.append((now - tel["t"]) * 1000.0)
            self.telemetry = tel
            self.telemetry_at = now
        elif kind == "event":
            name = str(msg.get("name") or "")
            detail = str(msg.get("detail") or "").strip()
            if name in ("estop", "resume"):
                self._set_estop(name == "estop")
            etype, text, level = BRIDGE_EVENTS.get(name, ("real_info", f"D1 real: {name}", "info"))
            self._event(etype, f"{text} ({detail})" if detail else text, level)

    # ----- camera detections -----
    def on_detection(self, det: dict[str, Any]) -> dict[str, Any]:
        """Decide what a POST /api/detection does: new finding (stop + incident), duplicate, or nothing."""
        now = time.monotonic()
        label = str(det.get("label") or "sana")
        conf = _num(det.get("conf")) or 0.0
        sospecha = bool(det.get("sospecha"))
        cama = det.get("cama")
        truth = det.get("truth_label")
        self.detections += 1
        if truth:
            self.truth.add(str(truth), sospecha, label, time.time())

        new = dup = False
        incident_no: int | None = None
        op = self._open
        if sospecha:
            same = (
                op is not None
                and op["label"] == label
                and op["cama"] == cama
                and (not truth or not op["truth"] or op["truth"] == truth)
                and now - op["last"] < INCIDENT_GAP_S
            )
            if same and op is not None:
                dup = True
                op["last"] = now
                incident_no = op["no"]
            else:
                new = True
                self.incidents += 1
                incident_no = self.incidents
                self._open = {"no": incident_no, "label": label, "cama": cama, "truth": truth, "t0": now, "last": now}
        elif op is not None and now - op["t0"] >= self.hold_s:
            self._open = None  # the camera stopped seeing it: the next suspicion is a new finding

        forwarded = False
        if new:
            forwarded = self._enqueue({"type": "detection_stop", "hold_s": self.hold_s, "label": label, "conf": round(conf, 4)})
            if forwarded:
                self.hold_until = now + self.hold_s
        self.last_detection = {
            "t": round(time.time(), 3),
            "label": label,
            "label_es": label_es(label),
            "conf": round(conf, 4),
            "p_enfermedad": _num(det.get("p_enfermedad")),
            "umbral": _num(det.get("umbral")),
            "sospecha": sospecha,
            "cama": cama,
            "truth_label": truth,
            "source": det.get("source"),
            "frame": det.get("frame"),
            "incident_no": incident_no,
            "duplicate": dup,
            "forwarded": forwarded,
            "where": self._open.get("where") if dup and self._open else None,
        }
        return {"new_incident": new, "duplicate": dup, "incident_no": incident_no, "forwarded": forwarded}

    def attach_incident(self, rec: dict[str, Any]) -> None:
        """Remember where the simulation filed the last finding (shown in the robot panel)."""
        where = {k: rec.get(k) for k in ("nave", "cama", "planta", "temp_c", "rh_pct", "day", "clock")}
        if self.last_detection is not None:
            self.last_detection["where"] = where
        if self._open is not None:
            self._open["where"] = where

    # ----- status -----
    def status(self) -> dict[str, Any]:
        now = time.time()
        age = (now - self.telemetry_at) * 1000.0 if self.telemetry_at is not None else None
        latency: float | None = None
        suspect = False
        if self._lat:
            med = statistics.median(self._lat)
            if -50.0 <= med <= 5000.0:
                latency = round(max(0.0, med), 1)
            else:
                suspect = True  # clocks of the Mac and the VM disagree: the one-way estimate is meaningless
        hello = self.hello or {}
        tel = self.telemetry
        return {
            "connected": self.connected,
            "link_id": self.link_id,
            "ever_connected": self.link_id > 0,
            "hello": self.hello is not None,
            "robot": hello.get("robot"),
            "mock": hello.get("mock"),
            "version": hello.get("version"),
            "limits": hello.get("limits"),
            "peer": self.peer,
            "connected_at": self.connected_at,
            "since_disconnect_s": round(now - self.disconnected_at, 1) if (not self.connected and self.disconnected_at) else None,
            "telemetry": tel,
            "telemetry_age_ms": round(age) if age is not None else None,
            "telemetry_stale": age is None or age > TELEMETRY_STALE_S * 1000.0,
            "latency_ms": latency,
            "clock_offset_suspect": suspect,
            "state": tel.get("state") if tel else None,
            "estop": self.estop,
            "hold_s": self.hold_s,
            "hold_s_left": round(max(0.0, self.hold_until - time.monotonic()), 1),
            "teleop_active": self.connected and self.manual_active(),
            "teleop_seq": self.seq,
            "detections": self.detections,
            "incidents": self.incidents,
            "last_detection": self.last_detection,
            "truth": self.truth.snapshot(),
            "th_note": SIMULATED_TH,
            "safety": self.safety_status(),
            "ruta": self.ruta_status(),
        }
