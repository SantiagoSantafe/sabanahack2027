"""Read-only feed for the external incidents dashboard (GET /api/dashboard/*).

The dashboard never opens /ws (each /ws connection would create its own simulation). It reads the
incidents of the most recent open session instead, or of the last one that closed.
"""
from __future__ import annotations

import asyncio
import json
from collections import deque
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from dashboard_acciones import Acciones, AccionInvalida
from dashboard_config import load_dashboard_config
from dashboard_focos import adoptar_ids, agrupar, enriquecer, numeros
from dashboard_mapa import geometria, lecturas as lecturas_mapa, posicion_planta, rejilla
from dashboard_riesgo import avisos as avisos_preventivos
from dashboard_riesgo import cobertura as cobertura_de
from dashboard_riesgo import proyectar
from engine import _clock

HERE = Path(__file__).parent
_FRAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}\.(jpg|jpeg|png)$")


def capturas_dir() -> Path | None:
    """Carpeta de fotos del D1 (solo lectura). DASHBOARD_CAPTURAS_DIR la cambia; si no, busca datos/resultados/ml/capturas_d1."""
    cands = [os.environ.get("DASHBOARD_CAPTURAS_DIR"), HERE / "data/resultados/ml/capturas_d1",
             HERE.parent.parent / "datos/resultados/ml/capturas_d1",
             Path("/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/capturas_d1")]
    for c in cands:
        if c and Path(c).is_dir():
            return Path(c).resolve()
    return None


def buscar_captura(nombre: str, root: Path | None = None) -> Path | None:
    """Ruta segura de una foto por nombre de archivo; None si no existe o saldría de la carpeta."""
    root = root or capturas_dir()
    if root is None or not _FRAME_RE.match(nombre or ""):
        return None
    for p in root.rglob(nombre):
        r = p.resolve()
        if r.is_file() and r.is_relative_to(root):
            return r
    return None

CLASES = ("sana", "oidio", "alternaria", "heliothis")
_ALIAS = {
    "sana": "sana", "hoja sana": "sana", "healthy": "sana",
    "oidio": "oidio", "oídio": "oidio",
    "alternaria": "alternaria",
    "heliothis": "heliothis",
}
DETECCION = {"sana": "Hoja sana", "oidio": "Oídio", "alternaria": "Alternaria", "heliothis": "Heliothis"}
_UNHEALTHY_STATES = (2, 3, 4, 5)  # infected (asymptomatic), symptomatic, alert pending, confirmed

# rastro reciente del robot por sesión (se alimenta en cada consulta de /mapa y en el stream)
_RASTROS: dict[int, deque] = {}

# first time each record was seen (records carry simulated day/clock, not wall time)
_STAMPS: dict[tuple[int, int], float] = {}


def _horas(clock: Any) -> float:
    try:
        h, m = str(clock).split(":")
        return int(h) + int(m) / 60.0
    except (ValueError, AttributeError):
        return 0.0


def clase_de(label: Any) -> str:
    return _ALIAS.get(str(label or "").strip().lower(), "desconocida")


def normalizar(sid: int, rec: dict[str, Any]) -> dict[str, Any]:
    clase = clase_de(rec.get("clase"))
    key = (sid, int(rec["id"]))
    ts = _STAMPS.setdefault(key, time.time())
    planta = rec.get("planta")
    ubic = f"N{rec['nave']} C{rec['cama']} P{planta if planta is not None else '-'}"
    conf = rec.get("confianza")
    return {
        "id": f"{sid}-{rec['id']}",
        "ts": round(ts, 3),
        "dia": rec.get("day"),
        "hora": rec.get("clock"),
        "ubicacion": ubic,
        "nave": rec["nave"],
        "cama": rec["cama"],
        "planta": planta,
        "deteccion": DETECCION.get(clase, str(rec.get("clase") or "Desconocida")),
        "clase": clase,
        "temperatura_c": rec.get("temp_c"),
        "humedad_pct": rec.get("rh_pct"),
        "estado": "Saludable" if clase == "sana" else "Alerta",
        "fuente": "camara_d1" if rec.get("fuente") == "camara_d1" else "simulacion",
        "confianza": conf if isinstance(conf, (int, float)) else None,
        "t_h": round(float(rec.get("day", 0)) * 24 + _horas(rec.get("clock")), 3),
        "frame": os.path.basename(str(rec["frame"])) if rec.get("frame") else None,
        "verdad": rec.get("truth_label"),
    }


class BloqueIn(BaseModel):
    bloque: int


class AccionIn(BaseModel):
    accion: Literal["asignar", "verificar", "tratar", "cerrar", "nota"]
    responsable: str | None = None
    resultado: Literal["confirmado", "falsa_alarma"] | None = None
    detalle: str | None = None
    nota: str | None = None


def make_router(get_sessions: Callable[[], Iterable[Any]], get_last: Callable[[], Any],
                acciones: Acciones | None = None, cfg: dict[str, Any] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
    cfg = cfg or load_dashboard_config()
    if acciones is None:
        acciones = Acciones(os.environ.get("DASHBOARD_DB") or HERE / "data" / "dashboard_acciones.sqlite3")
    store = acciones
    registro: dict[str, set[str]] = {}  # id de foco -> incidencias, para que el id sea estable (ver adoptar_ids)
    for k, v in store.incs_por_foco().items():
        registro.setdefault(k, set()).update(v)

    def active() -> Any:
        sessions = [s for s in get_sessions() if getattr(s, "sims", None)]
        if sessions:
            return max(sessions, key=lambda s: getattr(s, "created", 0.0))
        return get_last()

    def incidencias(limit: int) -> tuple[Any, list[dict[str, Any]]]:
        s = active()
        if s is None or not s.sims:
            return None, []
        sid = id(s)
        recs = list(s.sims[0].incident_records)
        return s, [normalizar(sid, r) for r in recs[-limit:]][::-1]  # newest first

    def resumen_de(s: Any) -> dict[str, Any]:
        if s is None or not s.sims:
            return {"sesion": None, "conectado": False, "total": 0}
        sim = s.sims[0]
        items = [normalizar(id(s), r) for r in list(sim.incident_records)]
        temps = [i["temperatura_c"] for i in items if i["temperatura_c"] is not None]
        hums = [i["humedad_pct"] for i in items if i["humedad_pct"] is not None]
        por_clase = {c: 0 for c in CLASES}
        for i in items:
            por_clase[i["clase"]] = por_clase.get(i["clase"], 0) + 1
        alertas = sum(1 for i in items if i["estado"] == "Alerta")
        pending_d1 = sum(1 for i in items if i["estado"] == "Alerta" and i["fuente"] == "camara_d1")
        total_plants = max(1, sim.n_beds * sim.n_plants)
        malas = int(sum((sim.states == v).sum() for v in _UNHEALTHY_STATES))
        clima = sim._climate_now()
        return {
            "sesion": id(s),
            "conectado": s in set(get_sessions()),
            "dia": sim.day,
            "hora": _clock(sim.t),
            "bloque": int(getattr(sim, "bloque", 1)),
            "bloque_naves": next((b["naves"] for b in sim.map.layout()["blocks"] if b["id"] == getattr(sim, "bloque", 1)), []),
            "total": len(items),
            "temperatura_promedio": round(sum(temps) / len(temps), 1) if temps else round(clima["T_in"], 1),
            "humedad_promedio": round(sum(hums) / len(hums), 1) if hums else round(clima["RH_in"], 1),
            "temperatura_actual": round(clima["T_in"], 1),
            "humedad_actual": round(clima["RH_in"], 1),
            "plantas_saludables_pct": round(100.0 * (total_plants - malas) / total_plants, 1),
            "incidencias_activas": len(sim.pending) + pending_d1,
            "alertas_total": alertas,
            "por_clase": por_clase,
            "por_fuente": {
                "simulacion": sum(1 for i in items if i["fuente"] == "simulacion"),
                "camara_d1": sum(1 for i in items if i["fuente"] == "camara_d1"),
            },
        }

    def focos_de(s: Any) -> tuple[list[dict[str, Any]], float]:
        if s is None or not s.sims:
            return [], 0.0
        sim = s.sims[0]
        now_h = sim.t / 3600.0
        incs = [normalizar(id(s), r) for r in list(sim.incident_records)]
        est = store.estados()
        crudos = agrupar(incs, cfg, semilla=f"{sim.seed}{sim.alt_code}")
        adoptar_ids(crudos, registro)
        out = []
        for f in crudos:
            bed = (f["nave"] - 1) * sim.map.bpn + f["cama"] - 1
            risk = float(sim.bed_risks[bed]) if 0 <= bed < sim.n_beds else 0.0
            out.append(enriquecer(f, risk, now_h, cfg, est.get(f["id"])))
        out.sort(key=lambda f: (not f["abierto"], -f["puntaje"]))
        return out, now_h

    def foto_de(frame: str | None) -> str | None:
        return f"/api/dashboard/captura?f={frame}" if frame and buscar_captura(frame) else None

    @router.get("/incidencias")
    def get_incidencias(limit: int = Query(200, ge=1, le=2000)) -> dict[str, Any]:
        s, items = incidencias(limit)
        for i in items:
            if i.get("frame"):
                i["foto"] = foto_de(i["frame"])
        return {"sesion": id(s) if s else None, "total": len(items), "items": items}

    @router.get("/resumen")
    def get_resumen() -> dict[str, Any]:
        return resumen_de(active())

    @router.get("/focos")
    def get_focos(limit: int = Query(50, ge=1, le=500), estado: str | None = None, abiertos: bool = False) -> dict[str, Any]:
        s = active()
        todos, now_h = focos_de(s)
        focos = [f for f in todos if (not abiertos or f["abierto"]) and (not estado or f["estado"] == estado)]
        for f in focos[:limit]:
            f["foto"] = foto_de(f.get("frame"))
        return {
            "sesion": id(s) if s else None, "ahora_h": round(now_h, 1), "total": len(focos), "items": focos[:limit],
            "kpis": {
                "focos_abiertos": sum(1 for f in todos if f["abierto"]),
                "detecciones": sum(f["detecciones"] for f in todos),
                "sin_atender_rojo": sum(1 for f in todos if f["abierto"] and f["semaforo"] == "rojo"),
                "por_estado": {e: sum(1 for f in todos if f["estado"] == e) for e in ("nuevo", "asignado", "verificado", "tratado", "cerrado")},
                "etiquetas": store.etiquetas(),
            },
            "config": {"rojo_h": cfg["atencion"]["rojo_h"], "ventana_h": cfg["focos"]["ventana_h"], "max_gap_plantas": cfg["focos"]["max_gap_plantas"]},
            "nota": "Horas del escenario simulado. Prioridad = gravedad x plantas x riesgo de la cama x antigüedad (pesos en config/dashboard.yaml).",
        }

    def _foco(foco_id: str) -> tuple[dict[str, Any], float]:
        focos, now_h = focos_de(active())
        for f in focos:
            if f["id"] == foco_id:
                return f, now_h
        raise HTTPException(404, "foco no encontrado en la sesión activa")

    @router.post("/bloque")
    def post_bloque(body: BloqueIn) -> dict[str, Any]:
        """El supervisor elige desde el panel qué bloque recorre el robot (1 = naves 1–2, 2 = naves 3–4).
        Se aplica a cada visor abierto (simulador) y a la última sesión."""
        sesiones = [s for s in get_sessions() if hasattr(s, "handle")]
        last = get_last()
        if last is not None and last not in sesiones and hasattr(last, "handle"):
            sesiones.append(last)
        if not sesiones:
            raise HTTPException(status_code=409, detail="El simulador no tiene una sesión abierta")
        for ses in sesiones:
            ses.handle({"cmd": "bloque", "value": int(body.bloque)})
        b = int(getattr(sesiones[0], "bloque", body.bloque))
        return {"ok": True, "bloque": b}

    @router.post("/focos/{foco_id}/accion")
    def post_accion(foco_id: str, body: AccionIn) -> dict[str, Any]:
        foco, now_h = _foco(foco_id)
        try:
            est = store.aplicar(foco_id, body.accion, body.model_dump(exclude={"accion"}), sim_h=now_h, incs=sorted(numeros(foco)))
        except AccionInvalida as e:
            raise HTTPException(409, str(e)) from e
        f, _ = _foco(foco_id)
        return {"foco": f, "estado": est, "historial": store.historial(foco_id)}

    @router.get("/focos/{foco_id}/historial")
    def get_historial(foco_id: str) -> dict[str, Any]:
        return {"foco_id": foco_id, "estado": store.estado(foco_id), "historial": store.historial(foco_id)}

    @router.get("/riesgo")
    def get_riesgo() -> dict[str, Any]:
        s = active()
        if s is None or not s.sims:
            return {"sesion": None, "camas": [], "avisos": []}
        sim = s.sims[0]
        proy = proyectar(sim, cfg)
        w = sim._climate_now()
        return {
            "sesion": id(s), "estimado": True,
            "nota": "Riesgo de las próximas 24-72 h ESTIMADO con el clima horario del escenario (sin azar de ventilación/alero). Recomendaciones orientativas: validar con el agrónomo.",
            "clima": {"T_in": round(w["T_in"], 1), "RH_in": round(w["RH_in"], 1), "wet_now": w["wet_now"], "horas_mojadas_hoy": w["wet_h"]},
            **proy, "avisos": avisos_preventivos(proy, cfg),
            "enfermedades": [{"clave": k, "nombre": n, "riesgo_ahora": proy["pd_ahora"][k]} for k, n in
                             (("botrytis", "Botrytis"), ("anthracnose", "Antracnosis"), ("rust", "Roya"))],
        }

    @router.get("/cobertura")
    def get_cobertura() -> dict[str, Any]:
        s = active()
        if s is None or not s.sims:
            return {"sesion": None, "camas": [], "puntos_ciegos": []}
        return {"sesion": id(s), **cobertura_de(s.sims[0], cfg)}

    @router.get("/avisos")
    def get_avisos(limit: int = Query(10, ge=1, le=50)) -> dict[str, Any]:
        """Texto corto para pantalla de oficina o mensajería. No se envía a ningún servicio."""
        s = active()
        focos, _ = focos_de(s)
        items = [{"tipo": "foco", "id": f["id"], "nivel": f["nivel"], "texto": f["aviso"]} for f in focos if f["abierto"]][:limit]
        if s is not None and s.sims:
            items += [{"tipo": "prevencion", "id": a["id"], "nivel": a["nivel"], "texto": f"{a['texto']} ({a['nota']})"}
                      for a in avisos_preventivos(proyectar(s.sims[0], cfg), cfg)[:5]]
        return {"items": items, "nota": "Integración pendiente: este endpoint solo entrega el texto."}

    def rastro(s: Any) -> list[dict[str, float]]:
        r = s.sims[0].robot
        d = _RASTROS.setdefault(id(s), deque(maxlen=150))
        if not d or (d[-1]["x"] - r.x) ** 2 + (d[-1]["y"] - r.z) ** 2 >= 0.25:
            d.append({"x": round(float(r.x), 2), "y": round(float(r.z), 2)})
        return list(d)

    @router.get("/mapa")
    def get_mapa(horas: float = Query(24, ge=1, le=24 * 400), celda: float = Query(1.0, ge=0.5, le=4.0),
                 limit: int = Query(1500, ge=1, le=5000)) -> dict[str, Any]:
        """Planta del bloque: geometría, campos T/HR interpolados, detecciones ubicadas, riesgo por cama y robot."""
        s = active()
        if s is None or not s.sims:
            return {"sesion": None}
        sim = s.sims[0]
        geo = geometria(sim)
        ahora_h = sim.t / 3600.0
        lec = lecturas_mapa(sim, horas, ahora_h)
        b = geo["bounds"]
        # detecciones: todas las incidencias con su foco
        focos, _ = focos_de(s)
        de_foco = {}
        for f in focos:
            for iid in f["incidencias"]:
                de_foco[iid] = f
        dets = []
        for r in list(sim.incident_records)[-limit:]:
            n = normalizar(id(s), r)
            bed = int(r.get("cama_global", 1)) - 1
            if not 0 <= bed < sim.n_beds:
                continue
            x, y = posicion_planta(sim, bed, r.get("planta"))
            f = de_foco.get(n["id"])
            dets.append({**{k: n[k] for k in ("id", "ts", "dia", "hora", "t_h", "ubicacion", "nave", "cama", "planta", "deteccion", "clase",
                                              "temperatura_c", "humedad_pct", "estado", "fuente", "confianza")},
                         "x": round(x, 2), "y": round(y, 2), "foco_id": f["id"] if f else None,
                         "foco_estado": f["estado"] if f else None, "foco_abierto": bool(f and f["abierto"]),
                         "foco_semaforo": f["semaforo"] if f else None})
        proy = proyectar(sim, cfg)
        riesgo = [{"nave": c["nave"], "cama": c["cama"], "ahora": c["ahora"]["riesgo"], "nivel_ahora": c["ahora"]["nivel"],
                   "max": c["max_riesgo"], "nivel": c["nivel"]} for c in proy["camas"]]
        r = sim.robot
        return {
            "sesion": id(s), "ahora_h": round(ahora_h, 1), "geometria": geo, "horas_ventana": horas,
            "temperatura": rejilla([(l["x"], l["y"], l["t"]) for l in lec], b, celda),
            "humedad": rejilla([(l["x"], l["y"], l["hr"]) for l in lec], b, celda),
            "lecturas": {"n": len(lec), "por_tipo": {k: sum(1 for l in lec if l["tipo"] == k) for k in ("incidencia", "sonda_robot", "sensor_bloque")},
                         "puntos": [[l["x"], l["y"], l["t"], l["hr"], l["tipo"]] for l in lec[-400:]]},
            "detecciones": dets, "riesgo": riesgo,
            "robot": {"x": round(float(r.x), 2), "y": round(float(r.z), 2), "heading": round(float(r.heading), 3), "estado": r.state,
                      "rastro": rastro(s)},
            "nota": "T y HR interpoladas (kernel gaussiano) a partir de las lecturas puntuales; solo las celdas marcadas contienen una lectura. Datos simulados.",
        }

    @router.get("/captura")
    def get_captura(f: str = Query(..., max_length=140)) -> FileResponse:
        p = buscar_captura(f)
        if p is None:
            raise HTTPException(404, "captura no encontrada")
        return FileResponse(p, headers={"Cache-Control": "private, max-age=300"})

    @router.get("/stream")
    async def stream() -> StreamingResponse:
        async def gen() -> Any:
            sent: set[str] = set()
            sesion = object()
            while True:
                s, items = incidencias(500)
                cur = id(s) if s else None
                if s is not None and s.sims:
                    rastro(s)
                reset = cur != sesion
                if reset:
                    sent.clear()
                    sesion = cur
                nuevas = [i for i in reversed(items) if i["id"] not in sent]  # oldest first
                sent.update(i["id"] for i in nuevas)
                body = {"reset": reset, "sesion": cur, "nuevas": nuevas, "resumen": resumen_de(s), "ts": time.time()}
                yield f"event: update\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(
            gen(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
