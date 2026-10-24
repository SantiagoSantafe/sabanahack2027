"""Vista cenital: rejilla interpolada, geometría y detecciones dentro del bloque."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

import dashboard
import server
from dashboard_acciones import Acciones
from dashboard_config import load_dashboard_config
from dashboard_mapa import geometria, lecturas, rejilla
from engine import Simulation
from weather import synthesize_year

B = {"x0": 0.0, "x1": 10.0, "y0": 0.0, "y1": 20.0}


def test_rejilla_forma() -> None:
    g = rejilla([(5.0, 5.0, 12.0)], B, 1.0)
    assert (g["nx"], g["ny"]) == (10, 20) and len(g["valores"]) == 200
    assert g["n_lecturas"] == 1 and g["min"] == g["max"] == 12.0
    g2 = rejilla([(5.0, 5.0, 12.0)], B, 2.0)
    assert (g2["nx"], g2["ny"]) == (5, 10)


def test_una_lectura_es_campo_constante_y_marca_medido() -> None:
    g = rejilla([(2.5, 3.5, 9.0)], B, 1.0)
    assert all(v == 9.0 for v in g["valores"])
    assert g["medido"] and all(0 <= i < 200 for i in g["medido"])
    idx = 3 * g["nx"] + 2  # celda que contiene (2.5, 3.5)
    assert idx in g["medido"]
    assert 19 * g["nx"] + 9 not in g["medido"]


def test_n_lecturas_interpola_entre_extremos() -> None:
    g = rejilla([(1.0, 1.0, 10.0), (9.0, 19.0, 20.0)], B, 1.0, sigma=6.0)
    v = g["valores"]
    cerca_a, cerca_b = v[1 * 10 + 1], v[18 * 10 + 8]
    assert cerca_a < 12 and cerca_b > 18 and cerca_a < v[10 * 10 + 5] < cerca_b
    assert 10 <= g["min"] <= g["max"] <= 20  # nunca fuera del rango de las lecturas


def test_sin_lecturas() -> None:
    g = rejilla([], B)
    assert g["valores"] == [] and g["min"] is None


class Fake:
    def __init__(self) -> None:
        cfg = server.CFG
        self.created = 1.0
        self.sims = [Simulation(alternative="F", seed=7, year=2025, config=cfg,
                                hourly_weather=synthesize_year(cfg["weather"], 2025, seed=2025),
                                weather_source="synthetic", patrol_dt_s=2.0)]
        for _ in range(60000):
            self.sims[0].step()
            if len(self.sims[0].incident_records) >= 15:
                break
        self.sims[0].external_event("real_detection", "x", "warn", bed=0, clase="Heliothis", confianza=0.9, fuente="camara_d1")


@pytest.fixture(scope="module")
def ses() -> Fake:
    return Fake()


@pytest.fixture()
def client(ses: Fake, tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.include_router(dashboard.make_router(lambda: [ses], lambda: ses, Acciones(tmp_path / "m.sqlite3"), load_dashboard_config()))
    return TestClient(app)


def test_endpoint_mapa(client: TestClient) -> None:
    r = client.get("/api/dashboard/mapa").json()
    geo = r["geometria"]
    b = geo["bounds"]
    assert geo["unidad"] == "m" and len(geo["camas"]) == 12 and len(geo["naves"]) == 4
    for campo in ("temperatura", "humedad"):
        g = r[campo]
        assert len(g["valores"]) == g["nx"] * g["ny"] and g["n_lecturas"] == r["lecturas"]["n"] > 0
        assert g["nx"] == round(b["x1"] - b["x0"]) or g["nx"] >= int(b["x1"] - b["x0"])
    assert r["lecturas"]["por_tipo"]["sensor_bloque"] == 12
    assert r["detecciones"]
    for d in r["detecciones"]:
        assert b["x0"] <= d["x"] <= b["x1"] and b["y0"] <= d["y"] <= b["y1"]
        # cada detección cae sobre una cama real
        assert any(abs(c["x"] - d["x"]) < 0.01 for c in geo["camas"])
        assert d["clase"] in ("sana", "oidio", "alternaria", "heliothis")
    d1 = [d for d in r["detecciones"] if d["fuente"] == "camara_d1"]
    assert d1 and d1[0]["foco_id"] is None or d1[0]["foco_id"]
    assert b["x0"] <= r["robot"]["x"] <= b["x1"] and r["robot"]["rastro"]
    assert len(r["riesgo"]) == 12


def test_lecturas_ventana(ses: Fake) -> None:
    sim = ses.sims[0]
    ahora = sim.t / 3600.0
    todo = lecturas(sim, 1e6, ahora)
    nada = lecturas(sim, 1e-6, ahora)
    assert len(nada) <= len(todo) and sum(1 for l in nada if l["tipo"] == "sensor_bloque") == 12
    assert geometria(sim)["bounds"]["x1"] > geometria(sim)["bounds"]["x0"]


def test_sin_sesion(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(dashboard.make_router(lambda: [], lambda: None, Acciones(tmp_path / "n.sqlite3"), load_dashboard_config()))
    assert TestClient(app).get("/api/dashboard/mapa").json() == {"sesion": None}
