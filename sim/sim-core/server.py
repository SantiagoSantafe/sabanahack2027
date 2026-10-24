"""FastAPI WebSocket server: emit simulation state, receive controls."""
from __future__ import annotations

import asyncio
import math
import json
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from alternatives import list_alternatives, load_alternative
from config_loader import load_all_config
from dashboard import make_router as make_dashboard_router
from engine import Simulation
from robot_link import SIMULATED_TH, RobotLink, label_es
from robot_link import _num as _finite
from ruta_real import RutaParams, plan_relativa
from weather import fetch_archive

app = FastAPI(title="Berry Sim", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # includes the dashboard at http://localhost:5180
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CFG = load_all_config()
MAX_STEPS_PER_EMIT = 60

# One simulation per open viewer; the real D1 link is shared by all of them.
SESSIONS: set["Session"] = set()
LAST_SESSION: "Session | None" = None  # most recent session (kept after it closes) for the read-only dashboard feed


def _notify(etype: str, text: str, level: str) -> None:
    for s in list(SESSIONS):
        s.link_event(etype, text, level)


LINK = RobotLink(hold_s=float(CFG["robot"].get("path", {}).get("stop_inspect_seconds", 4.0)), notify=_notify)


class Session:
    def __init__(self) -> None:
        self.cfg = CFG
        self.seed = int(self.cfg["sim"]["default_seed"])
        self.alt = "F"
        self.speed = float(self.cfg["sim"].get("default_speed", 1.0))
        self.playing = True
        self.mast_override: bool | None = None
        self.manual = False
        self.bloque = 1  # se conserva entre reinicios de la simulación
        self.compare_mode = False
        self.compare_alts = ["F", "A", "C", "REF"]
        self.emit_hz = float(self.cfg["sim"].get("emit_hz", 10))
        self.year = int(self.cfg["weather"].get("default_year", 2025))
        self.hourly, self.wx_source = fetch_archive(self.cfg["weather"], self.year)
        self.sims: list[Simulation] = []
        self.run_id = 0
        self.heights_sent = False
        self.export_requested = False
        self.acc = 0.0
        self.created = time.time()
        self.reset()

    def _alt_cfg(self, code: str) -> dict[str, Any]:
        alt_cfg = dict(load_alternative(code))
        if self.mast_override is not None and alt_cfg.get("platform") == "quadruped":
            alt_cfg["mast"] = self.mast_override
            sensor = dict(alt_cfg.get("sensor", {}))
            if self.mast_override:
                sensor["camera_height_m"] = float(self.cfg["robot"].get("mast", {}).get("camera_height_m", 1.35))
                sensor["sees_full_bush"] = True
            else:
                sensor["camera_height_m"] = float(self.cfg["robot"].get("camera_height_m", 0.3))
                sensor["sees_full_bush"] = False
            alt_cfg["sensor"] = sensor
        return alt_cfg

    def reset(self) -> None:
        self.run_id += 1
        self.heights_sent = False
        self.acc = 0.0
        alts = self.compare_alts if self.compare_mode else [self.alt]
        self.sims = [
            Simulation(
                alternative=a,
                seed=self.seed,
                year=self.year,
                config=self.cfg,
                alt=self._alt_cfg(a),
                hourly_weather=self.hourly,
                weather_source=self.wx_source,
                run_id=self.run_id,
            )
            for a in alts
        ]
        for s in self.sims:
            s.bloque = self.bloque
        if self.manual and not self.compare_mode:
            self.sims[0].set_manual(True)
        else:
            self.manual = False

    def handle(self, msg: dict[str, Any]) -> None:
        cmd = msg.get("cmd")
        if cmd == "play":
            self.playing = True
        elif cmd == "pause":
            self.playing = False
        elif cmd == "speed":
            self.speed = max(0.1, min(float(msg.get("value", 1.0)), float(MAX_STEPS_PER_EMIT)))
        elif cmd == "seed":
            self.seed = int(msg.get("value", self.seed))
            self.reset()
        elif cmd == "alternative":
            self.alt = str(msg.get("value", "F"))
            self.compare_mode = False
            self.reset()
        elif cmd == "reset":
            self.reset()
        elif cmd == "mast":
            self.mast_override = bool(msg.get("value", False))
            self.reset()
        elif cmd == "compare":
            self.compare_mode = bool(msg.get("value", True))
            alts = msg.get("alternatives")
            if isinstance(alts, list) and alts:
                self.compare_alts = [str(a) for a in alts][:4]
            self.reset()
        elif cmd == "manual":
            if self.compare_mode:
                return
            self.manual = bool(msg.get("value", False))
            self.sims[0].set_manual(self.manual)
        elif cmd == "pose":
            if self.manual and not self.compare_mode:
                x, z = _finite(msg.get("x")), _finite(msg.get("z"))
                self.sims[0].set_pose(
                    float(msg.get("x", 0.0)),
                    float(msg.get("z", 0.0)),
                    float(msg.get("heading", 0.0)),
                    float(msg.get("speed", 0.0)),
                )
                if x is not None and z is not None:
                    LINK.update_pose(id(self), x, z, self.sims[0].map)  # geofence of the real D1
                # En Ruta real solo cuenta la cámara del D1: el simulador no "ve" sus plantas simuladas.
                self.sims[0].solo_camara_real = LINK._ruta_active()
        elif cmd == "ruta":
            self._ruta(msg)
        elif cmd == "bloque":
            try:
                self.bloque = int(msg.get("value", 1))
            except (TypeError, ValueError):
                return
            for s in self.sims:
                s.set_bloque(self.bloque)
            self.bloque = self.sims[0].bloque if self.sims else self.bloque
        elif cmd == "inicio":
            if self.sims and not self.compare_mode:
                self.sims[0].inicio_bloque()
        elif cmd == "inspect":
            if self.manual and not self.compare_mode:
                self.sims[0].manual_inspect()
        elif cmd == "skip":
            if not self.manual:
                for sim in self.sims:
                    sim.skip_to_next_patrol()
        elif cmd == "export":
            self.export_requested = True
        elif cmd == "statics":
            self.heights_sent = False

    def _ruta(self, msg: dict[str, Any]) -> None:
        """Ruta real: op = dryrun | start | cancel. The route is the Auto one, scaled, anchored at the twin's pose."""
        op = msg.get("op")
        if op == "cancel":
            LINK.ruta_cancel("cancelada por el operador; pulsa Ruta real de nuevo", "warn")
            return
        if self.compare_mode or not self.sims or op not in ("dryrun", "start"):
            return
        sim = self.sims[0]
        params = RutaParams.from_dict(msg)
        rel = plan_relativa(sim.map, params, sim.map.block_aisles(self.bloque))  # solo los pasillos del bloque elegido
        pose = (sim.robot.x, sim.robot.z, sim.robot.heading)
        if op == "dryrun":
            LINK.ruta_dryrun(rel, params, pose)
        elif self.manual:
            LINK.set_manual(id(self), True)  # the 'manual' message may be in this same batch: the link learns it at the tick's end
            LINK.ruta_start(rel, params, pose)
        else:
            LINK._ruta_refuse("pasa a Manual primero")

    def advance(self) -> None:
        if not self.playing:
            return
        self.acc += self.speed
        n = min(int(self.acc), MAX_STEPS_PER_EMIT)
        self.acc -= int(self.acc)
        for _ in range(n):
            for sim in self.sims:
                if not sim.done():
                    sim.step()

    def payload(self) -> dict[str, Any]:
        include_heights = not self.heights_sent
        self.heights_sent = True
        if self.compare_mode:
            out: dict[str, Any] = {"mode": "compare", "states": [s.snapshot() for s in self.sims]}
        else:
            out = self.sims[0].snapshot()
            out["mode"] = "single"
        out["playing"] = self.playing
        out["speed"] = self.speed
        out["manual"] = self.manual
        out["bloque"] = self.bloque
        out["mast_override"] = self.mast_override
        out["real_robot"] = LINK.status()
        if include_heights and self.sims:
            out.update(self.sims[0].static_payload())
        return out

    def link_event(self, etype: str, text: str, level: str) -> None:
        if not self.compare_mode and self.sims:
            self.sims[0].external_event(etype, text, level)

    def real_detection(self, det: dict[str, Any], text: str, incident_no: int | None, level: str = "warn") -> dict[str, Any] | None:
        """File a real-camera finding at the robot's current position (ArUco bed id wins when it is valid)."""
        if self.compare_mode or not self.sims:
            return None
        sim = self.sims[0]
        cama = det.get("cama")
        if isinstance(cama, int) and 1 <= cama <= sim.n_beds:
            bed = cama - 1  # simulation markers carry the global bed number (ArUco 1 = Nave 1 · Cama 1)
        elif LINK.scan_lado() is not None:
            # Ruta real mirando a un lado: la cama es la del pasillo actual hacia donde apunta la cámara.
            a = sim.map.nearest_aisle(sim.robot.x)
            fx = math.sin(sim.robot.heading)  # adelante = (sin h, cos h): fx > 0 mira hacia +x
            lados = sorted((a.left, a.right), key=lambda b: sim.map.bed_centers_x[b])
            bed = lados[1] if fx > 0 else lados[0]
        else:
            bed = min(range(sim.n_beds), key=lambda b: abs(sim.map.bed_centers_x[b] - sim.robot.x))
        conf = det.get("conf")
        return sim.external_event(
            "real_detection", text, level, bed=bed,
            clase=label_es(str(det.get("label") or "")), confianza=round(float(conf), 2) if conf is not None else None,
            fuente="camara_d1", th_fuente=SIMULATED_TH, incidente_d1=incident_no,
            truth_label=det.get("truth_label"), frame=det.get("frame"),
        )

    def export_payload(self) -> dict[str, Any]:
        self.export_requested = False
        sim = self.sims[0]
        return {
            "mode": "export",
            "filename": f"registros_{sim.alt_code}_semilla{sim.seed}_dia{sim.day}.csv",
            "csv": sim.records_csv(),
        }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/alternatives")
def alternatives() -> list[dict[str, str]]:
    out = []
    for code in list_alternatives():
        a = load_alternative(code)
        out.append({"code": code, "name": str(a.get("name", code)), "title": str(a.get("title", code))})
    return out


class DetectionIn(BaseModel):
    """POST /api/detection (contract v1, section 3). Extra fields are accepted and ignored."""

    model_config = ConfigDict(extra="allow")
    ts: float | None = None
    label: str = "sana"
    conf: float = 0.0
    p_enfermedad: float | None = None
    sospecha: bool = False
    umbral: float | None = None
    cama: int | None = None
    truth_label: str | None = None
    frame: str | None = None
    source: str | None = None


class ActionIn(BaseModel):
    name: str


app.include_router(make_dashboard_router(lambda: list(SESSIONS), lambda: LAST_SESSION))


# The handlers below are async on purpose: they share LINK and SESSIONS with the WebSocket loops.
@app.post("/api/detection")
async def post_detection(det: DetectionIn) -> dict[str, Any]:
    d = det.model_dump()
    # NaN/inf (JSON from Python accepts them) would end up in the incident and make every later state
    # frame invalid for the browser's JSON.parse: the viewer would freeze.
    conf = _finite(d.get("conf"))
    d["conf"] = 0.0 if conf is None else max(0.0, min(conf, 1.0))
    for k in ("p_enfermedad", "umbral", "ts"):
        d[k] = _finite(d.get(k))
    decision = LINK.on_detection(d)
    incident_id = decision["incident_no"] if decision["duplicate"] else None
    if decision["new_incident"]:
        text = f"Cámara del D1: {label_es(det.label)} {d['conf'] * 100:.0f} %"
        recs = [r for s in list(SESSIONS) if (r := s.real_detection(d, text, decision["incident_no"])) is not None]
        if recs:
            incident_id = decision["incident_no"]
            LINK.attach_incident(recs[0])
    elif not d.get("sospecha") and str(det.label).strip().lower() in ("sana", "healthy", "hoja sana"):
        # Hoja sana vista por la cámara: queda en el registro como "Saludable", sin parar al robot ni crear alerta.
        text = f"Cámara del D1: hoja sana {d['conf'] * 100:.0f} %, sin alerta"
        for s in list(SESSIONS):
            s.real_detection(d, text, None, level="info")
    return {
        "ok": True,
        "forwarded_to_robot": decision["forwarded"],
        "incident_id": incident_id,
        "duplicate": decision["duplicate"],
    }


class PanelIn(BaseModel):
    """POST /api/panel: heartbeat of the camera panel (panel_demo.py --sim-url), about 2 per second."""

    model_config = ConfigDict(extra="allow")
    cam_ok: bool = False
    fps: float | None = None
    clase: str | None = None
    confianza: float | None = None
    p_enfermedad: float | None = None
    sospecha: bool | None = None
    estable: bool | None = None
    p_hoja: float | None = None
    frame_age_s: float | None = None


@app.post("/api/panel")
async def post_panel(p: PanelIn) -> dict[str, Any]:
    d = p.model_dump()
    for k in ("fps", "confianza", "p_enfermedad", "p_hoja", "frame_age_s"):
        d[k] = _finite(d.get(k))
    LINK.panel_update(d)
    return {"ok": True}


@app.get("/api/safety")
async def get_safety() -> dict[str, Any]:
    return LINK.safety_status()


@app.post("/api/safety")
async def post_safety(body: dict[str, Any]) -> dict[str, Any]:
    """Change the barriers' settings at run time, e.g. {"speed_cap_mps": 0.2} or {"video_guard": "off"}."""
    LINK.safety.update(body)
    return LINK.safety_status()


@app.get("/api/robot")
async def get_robot() -> dict[str, Any]:
    return {**LINK.status(), "log": list(LINK.log)}


@app.post("/api/robot/action")
async def post_robot_action(body: ActionIn) -> dict[str, Any]:
    """Same buttons as the viewer (stand, lie, estop, resume), handy from curl or a second laptop."""
    return {"ok": body.name in ("stand", "lie", "estop", "resume"), "sent": LINK.action(body.name)}


async def _headless_loop() -> None:
    """DASHBOARD_AUTOSESSION=1: one simulation that runs with no browser open, so the dashboard has data."""
    global LAST_SESSION
    import os

    session = Session()
    session.speed = float(os.environ.get("DASHBOARD_SPEED", session.speed))
    LAST_SESSION = session
    SESSIONS.add(session)
    period = 1.0 / session.emit_hz
    while True:
        session.advance()
        await asyncio.sleep(period)


@app.on_event("startup")
async def _maybe_headless() -> None:
    import os

    if os.environ.get("DASHBOARD_AUTOSESSION") == "1":
        app.state.headless = asyncio.create_task(_headless_loop())


@app.websocket("/ws/robot")
async def ws_robot(ws: WebSocket) -> None:
    """The D1 bridge connects here (client WebSocket from the Ubuntu VM)."""
    await ws.accept()
    await LINK.serve(ws)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    session = Session()
    sid = id(session)
    SESSIONS.add(session)
    global LAST_SESSION
    LAST_SESSION = session
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def reader() -> None:
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(msg, dict):
                    continue
                # Teleop and robot buttons skip the 10 Hz simulation tick: they go straight to the link.
                if msg.get("cmd") == "teleop":
                    LINK.set_teleop(msg, sid)  # only counts while this viewer is in Manual
                elif msg.get("cmd") == "robot_action":
                    LINK.action(str(msg.get("name", "")))
                else:
                    await queue.put(msg)
        except WebSocketDisconnect:
            await queue.put({"cmd": "__closed__"})

    # The simulation clock must not depend on how fast the browser reads: the tick loop
    # advances at emit_hz and the sender only ships the latest snapshot.
    static_keys = ("heights", "spread_l", "spread_r")
    latest: dict[str, Any] = {"payload": None, "static": None, "extra": []}
    ready = asyncio.Event()
    closed = asyncio.Event()

    def publish(p: dict[str, Any]) -> None:
        if "heights" in p:
            latest["static"] = {k: p.pop(k) for k in static_keys if k in p}
        latest["payload"] = p
        ready.set()

    async def sender() -> None:
        try:
            while not closed.is_set():
                await ready.wait()
                ready.clear()
                payload, static, extra = latest["payload"], latest["static"], latest["extra"]
                latest["static"], latest["extra"] = None, []
                if payload is not None:
                    await ws.send_json({**payload, **static} if static else payload)
                for msg in extra:
                    await ws.send_json(msg)
        except (WebSocketDisconnect, RuntimeError):
            closed.set()

    publish(session.payload())

    reader_task = asyncio.create_task(reader())
    sender_task = asyncio.create_task(sender())
    period = 1.0 / session.emit_hz
    try:
        next_t = time.perf_counter()
        while not closed.is_set():
            while not queue.empty():
                msg = queue.get_nowait()
                if msg.get("cmd") == "__closed__":
                    return
                session.handle(msg)
            LINK.set_manual(sid, session.manual and not session.compare_mode)
            session.advance()
            if session.export_requested:
                latest["extra"].append(session.export_payload())
            publish(session.payload())
            next_t += period
            await asyncio.sleep(max(0.0, next_t - time.perf_counter()))
            if time.perf_counter() - next_t > 1.0:
                next_t = time.perf_counter()
    except (WebSocketDisconnect, RuntimeError):
        return
    finally:
        SESSIONS.discard(session)
        LINK.viewer_closed(sid)
        LINK.set_manual(sid, False)
        closed.set()
        ready.set()
        reader_task.cancel()
        sender_task.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
