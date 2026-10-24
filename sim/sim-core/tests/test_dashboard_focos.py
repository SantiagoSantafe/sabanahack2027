"""Focos priorizados, ciclo de acción (persistente), riesgo próximo y cobertura del dashboard."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

import dashboard
import server
from dashboard_acciones import Acciones, AccionInvalida, siguiente
from dashboard_config import load_dashboard_config
from dashboard_focos import adoptar_ids, agrupar, enriquecer
from dashboard_riesgo import avisos, cobertura, proyectar
from engine import Simulation
from weather import synthesize_year

CFG = load_dashboard_config()


def inc(i: int, nave: int, cama: int, planta: int, clase: str = "oidio", t_h: float = 10.0, estado: str = "Alerta", **kw: Any) -> dict[str, Any]:
    return {"id": f"1-{i}", "nave": nave, "cama": cama, "planta": planta, "clase": clase, "t_h": t_h, "estado": estado,
            "fuente": "simulacion", "confianza": 0.9, "frame": None, **kw}


# ---------------------------------------------------------------- agrupación y prioridad
def test_agrupa_cercanas_y_separa_lejanas() -> None:
    incs = [inc(1, 1, 1, 10), inc(2, 1, 1, 14), inc(3, 1, 1, 19), inc(4, 1, 1, 60), inc(5, 1, 2, 10), inc(6, 2, 1, 11)]
    focos = agrupar(incs, CFG)
    por = {(f["nave"], f["cama"], f["planta_min"]): f for f in focos}
    assert len(focos) == 4  # P10-P19 (saltos de <= 5), P60, otra cama, otra nave
    assert por[(1, 1, 10)]["plantas"] == 3 and por[(1, 1, 10)]["planta_max"] == 19
    assert por[(1, 1, 60)]["plantas"] == 1


def test_familia_y_ventana_de_tiempo() -> None:
    mezcla = [inc(1, 1, 1, 10, "oidio"), inc(2, 1, 1, 11, "alternaria"), inc(3, 1, 1, 12, "heliothis")]
    focos = agrupar(mezcla, CFG)
    assert sorted(f["familia"] for f in focos) == ["hongo", "plaga"]
    hongo = next(f for f in focos if f["familia"] == "hongo")
    assert hongo["plantas"] == 2 and "(+1)" in hongo["deteccion"]
    lejos = [inc(1, 1, 1, 10, t_h=0), inc(2, 1, 1, 11, t_h=200)]  # > ventana_h de 72
    assert len(agrupar(lejos, CFG)) == 2


def test_las_sanas_no_forman_focos() -> None:
    assert agrupar([inc(1, 1, 1, 5, "sana", estado="Saludable")], CFG) == []


def test_prioridad_orden_y_antiguedad() -> None:
    chico = agrupar([inc(1, 1, 1, 10)], CFG)[0]
    grande = agrupar([inc(i, 1, 2, 10 + i) for i in range(2, 10)], CFG)[0]
    a = enriquecer(chico, 0.2, 12.0, CFG)
    b = enriquecer(grande, 0.2, 12.0, CFG)
    assert b["puntaje"] > a["puntaje"]
    riesgoso = enriquecer(chico, 0.9, 12.0, CFG)
    assert riesgoso["puntaje"] > a["puntaje"]
    viejo = enriquecer(chico, 0.2, 10.0 + 30, CFG)
    assert viejo["puntaje"] > a["puntaje"] and viejo["semaforo"] == "rojo"
    assert a["semaforo"] == "verde" and 0 <= a["puntaje"] <= 100
    plaga = enriquecer(agrupar([inc(1, 1, 1, 10, "heliothis")], CFG)[0], 0.2, 12.0, CFG)
    assert plaga["gravedad"] > a["gravedad"] and plaga["puntaje"] > a["puntaje"]


def test_reloj_se_detiene_al_verificar() -> None:
    f = agrupar([inc(1, 1, 1, 10, t_h=0)], CFG)[0]
    e = enriquecer(f, 0.2, 100.0, CFG, {"estado": "verificado", "resultado": "confirmado", "verificado_sim_h": 6.0})
    assert e["horas_sin_atender"] == 6.0 and e["semaforo"] == "verde"


def test_tendencia() -> None:
    f = agrupar([inc(i, 1, 1, 10 + i, t_h=90 + i) for i in range(1, 5)], CFG)[0]
    assert enriquecer(f, 0.2, 100.0, CFG)["tendencia"] == "crece"
    assert enriquecer(f, 0.2, 500.0, CFG, {"estado": "tratado", "resultado": "confirmado"})["tendencia"] == "baja"
    assert len(enriquecer(f, 0.2, 100.0, CFG)["serie"]) == CFG["focos"]["tendencia"]["puntos"]


def test_id_estable_al_crecer_y_fusionarse() -> None:
    reg: dict[str, set[str]] = {}
    a = agrupar([inc(5, 1, 1, 10), inc(6, 1, 1, 11)], CFG)
    adoptar_ids(a, reg)
    id0 = a[0]["id"]
    b = agrupar([inc(5, 1, 1, 10), inc(6, 1, 1, 11), inc(2, 1, 1, 14, t_h=9.0)], CFG)  # llega una detección más antigua
    assert b[0]["id"] != id0  # sin adopción el id cambiaría (nace de la primera detección)
    adoptar_ids(b, reg)
    assert b[0]["id"] == id0 and b[0]["plantas"] == 3


# ---------------------------------------------------------------- ciclo de acción
def test_transiciones_validas(tmp_path: Path) -> None:
    a = Acciones(tmp_path / "a.sqlite3")
    assert a.estado("f")["estado"] == "nuevo"
    assert a.aplicar("f", "asignar", {"responsable": "Ana"}, 5.0)["estado"] == "asignado"
    a.aplicar("f", "nota", {"nota": "voy en camino"})
    s = a.aplicar("f", "verificar", {"resultado": "confirmado"}, 7.5)
    assert s["estado"] == "verificado" and s["verificado_sim_h"] == 7.5
    assert a.aplicar("f", "tratar", {"detalle": "poda y fungicida"})["estado"] == "tratado"
    assert a.aplicar("f", "cerrar", {})["estado"] == "cerrado"
    h = a.historial("f")
    assert [x["accion"] for x in h] == ["asignar", "nota", "verificar", "tratar", "cerrar"]
    assert all(x["ts"] > 0 for x in h)


def test_falsa_alarma_cierra_sin_tratar(tmp_path: Path) -> None:
    a = Acciones(tmp_path / "a.sqlite3")
    a.aplicar("g", "asignar", {"responsable": "Luis"})
    a.aplicar("g", "verificar", {"resultado": "falsa_alarma"})
    assert a.aplicar("g", "cerrar", {})["estado"] == "cerrado"
    assert a.etiquetas() == {"total": 1, "confirmadas": 0, "falsas_alarma": 1, "pct_falsas": 100.0}


@pytest.mark.parametrize("estado,res,accion,datos", [
    ("nuevo", None, "verificar", {"resultado": "confirmado"}),      # sin asignar
    ("nuevo", None, "tratar", {"detalle": "x"}),
    ("nuevo", None, "cerrar", {}),
    ("nuevo", None, "asignar", {}),                                  # falta responsable
    ("asignado", None, "tratar", {"detalle": "x"}),
    ("asignado", None, "verificar", {"resultado": "quizas"}),
    ("verificado", "falsa_alarma", "tratar", {"detalle": "x"}),
    ("verificado", "confirmado", "cerrar", {}),                      # falta tratar
    ("tratado", "confirmado", "verificar", {"resultado": "confirmado"}),
    ("cerrado", "confirmado", "asignar", {"responsable": "x"}),
    ("nuevo", None, "nota", {"nota": "  "}),
    ("nuevo", None, "bailar", {}),
])
def test_transiciones_invalidas(estado: str, res: str | None, accion: str, datos: dict[str, Any]) -> None:
    with pytest.raises(AccionInvalida):
        siguiente(estado, res, accion, datos)


def test_persistencia_tras_reinicio(tmp_path: Path) -> None:
    p = tmp_path / "persist.sqlite3"
    a = Acciones(p)
    a.aplicar("f1", "asignar", {"responsable": "Ana"})
    a.aplicar("f1", "verificar", {"resultado": "confirmado"})
    b = Acciones(p)  # "reinicio": nueva instancia sobre el mismo archivo
    assert b.estado("f1")["estado"] == "verificado" and b.estado("f1")["responsable"] == "Ana"
    assert len(b.historial("f1")) == 2
    with pytest.raises(AccionInvalida):
        b.aplicar("f1", "verificar", {"resultado": "confirmado"})
    assert len(b.historial("f1")) == 2  # la acción inválida no se guarda


# ---------------------------------------------------------------- simulación real + endpoints
class FakeSession:
    def __init__(self) -> None:
        cfg = server.CFG
        self.created = 1.0
        self.sims = [Simulation(alternative="F", seed=7, year=2025, config=cfg,
                                hourly_weather=synthesize_year(cfg["weather"], 2025, seed=2025),
                                weather_source="synthetic", patrol_dt_s=2.0)]


@pytest.fixture(scope="module")
def sesion() -> FakeSession:
    s = FakeSession()
    sim = s.sims[0]
    for _ in range(60000):
        sim.step()
        if len(sim.incident_records) >= 25:
            break
    sim.external_event("real_detection", "x", "warn", bed=0, clase="Heliothis", confianza=0.9, fuente="camara_d1", frame="frame_x.jpg")
    return s


@pytest.fixture()
def client(sesion: FakeSession, tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.include_router(dashboard.make_router(lambda: [sesion], lambda: sesion, Acciones(tmp_path / "t.sqlite3"), CFG))
    return TestClient(app)


def test_endpoint_focos(client: TestClient) -> None:
    r = client.get("/api/dashboard/focos?limit=5").json()
    assert 0 < len(r["items"]) <= 5 and r["kpis"]["focos_abiertos"] >= 1
    pts = [f["puntaje"] for f in r["items"]]
    assert pts == sorted(pts, reverse=True)
    f = r["items"][0]
    assert {"id", "ubicacion", "deteccion", "plantas", "puntaje", "semaforo", "tendencia", "serie", "por_que", "aviso", "estado"} <= set(f)
    assert r["kpis"]["detecciones"] > r["kpis"]["focos_abiertos"] or r["kpis"]["detecciones"] >= 1


def test_ciclo_por_http(client: TestClient) -> None:
    f = client.get("/api/dashboard/focos?limit=1").json()["items"][0]
    url = f"/api/dashboard/focos/{f['id']}/accion"
    assert client.post(url, json={"accion": "verificar", "resultado": "confirmado"}).status_code == 409
    assert client.post(url, json={"accion": "bailar"}).status_code == 422
    r = client.post(url, json={"accion": "asignar", "responsable": "Ana"})
    assert r.status_code == 200 and r.json()["foco"]["estado"] == "asignado"
    assert client.post(url, json={"accion": "verificar", "resultado": "falsa_alarma", "nota": "era sombra"}).status_code == 200
    h = client.get(f"/api/dashboard/focos/{f['id']}/historial").json()
    assert h["estado"]["estado"] == "verificado" and len(h["historial"]) == 2
    k = client.get("/api/dashboard/focos?abiertos=true").json()["kpis"]
    assert k["etiquetas"]["falsas_alarma"] == 1 and k["por_estado"]["verificado"] == 1
    assert client.post("/api/dashboard/focos/NOEXISTE/accion", json={"accion": "asignar", "responsable": "x"}).status_code == 404


def test_riesgo(client: TestClient, sesion: FakeSession) -> None:
    r = client.get("/api/dashboard/riesgo").json()
    sim = sesion.sims[0]
    assert r["estimado"] is True and "agrónomo" in r["nota"]
    assert len(r["camas"]) == sim.n_beds
    for c in r["camas"]:
        assert c["nivel"] in ("bajo", "medio", "alto") and len(c["ventanas"]) == 3
        assert all(v["estimado"] for v in c["ventanas"])
        assert c["ventanas"][0]["horas"] == "0-24 h"
    for a in r["avisos"]:
        assert a["nivel"] in ("medio", "alto") and "orientativa" in a["nota"] and a["texto"].startswith("Riesgo ")


def test_avisos_por_regla() -> None:
    proy = {"camas": [
        {"nave": 2, "cama": 1, "ventanas": [{"nivel": "alto", "enfermedad": "botrytis", "horas": "0-24 h", "noche": True, "riesgo": 0.9, "horas_mojadas": 10}]},
        {"nave": 2, "cama": 2, "ventanas": [{"nivel": "bajo", "enfermedad": "rust", "horas": "0-24 h", "noche": False, "riesgo": 0.0, "horas_mojadas": 0}]},
    ]}
    av = avisos(proy, CFG)
    assert len(av) == 1 and "Botrytis" in av[0]["texto"] and "N2" in av[0]["texto"] and "esta noche" in av[0]["texto"]
    assert "ventilar" in av[0]["texto"]


def test_proyeccion_y_cobertura(sesion: FakeSession) -> None:
    sim = sesion.sims[0]
    p = proyectar(sim, CFG)
    assert p["niveles"]["alto"] > p["niveles"]["medio"]
    cob = cobertura(sim, {"cobertura": {"ciego_h": -1.0}})
    visitadas = [c for c in cob["camas"] if c["horas_sin_revisar"] is not None]
    assert visitadas and all(c["ultima_hora"] for c in visitadas)
    assert all(c["ciego"] for c in cob["camas"])  # con umbral minúsculo todas lo son
    assert not any(c["ciego"] for c in cobertura(sim, {"cobertura": {"ciego_h": 1e9}})["camas"])


def test_avisos_endpoint_y_cobertura_http(client: TestClient) -> None:
    a = client.get("/api/dashboard/avisos").json()
    assert a["items"] and all(i["texto"] for i in a["items"])
    assert client.get("/api/dashboard/cobertura").json()["camas"]


# ---------------------------------------------------------------- captura segura
def test_captura_solo_dentro_de_la_carpeta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "capturas_d1"
    (root / "vivo").mkdir(parents=True)
    (root / "vivo" / "frame_1.jpg").write_bytes(b"\xff\xd8\xff")
    (tmp_path / "secreto.jpg").write_bytes(b"x")
    monkeypatch.setenv("DASHBOARD_CAPTURAS_DIR", str(root))
    assert dashboard.buscar_captura("frame_1.jpg") is not None
    for mal in ("../secreto.jpg", "..%2Fsecreto.jpg", "/etc/passwd", "frame_1.txt", "secreto.jpg", "a/b.jpg"):
        assert dashboard.buscar_captura(mal) is None
    (root / "enlace.jpg").symlink_to(tmp_path / "secreto.jpg")  # un symlink que sale de la carpeta no se sirve
    assert dashboard.buscar_captura("enlace.jpg") is None
    app = FastAPI()
    app.include_router(dashboard.make_router(lambda: [], lambda: None, Acciones(tmp_path / "x.sqlite3"), CFG))
    c = TestClient(app)
    assert c.get("/api/dashboard/captura", params={"f": "frame_1.jpg"}).status_code == 200
    assert c.get("/api/dashboard/captura", params={"f": "../secreto.jpg"}).status_code == 404


def test_incs_persisten(tmp_path: Path) -> None:
    p = tmp_path / "i.sqlite3"
    Acciones(p).aplicar("f", "asignar", {"responsable": "Ana"}, incs=["3", "4"])
    assert Acciones(p).incs_por_foco() == {"f": {"3", "4"}}
