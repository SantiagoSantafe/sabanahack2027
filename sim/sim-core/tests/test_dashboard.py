"""Read-only dashboard feed: /api/dashboard/{incidencias,resumen,stream}."""
from __future__ import annotations

import json
from typing import Any

import pytest
from starlette.testclient import TestClient

import server
from engine import Simulation
from weather import synthesize_year

FIELDS = {"id", "ts", "dia", "hora", "ubicacion", "deteccion", "clase", "temperatura_c", "humedad_pct", "estado", "fuente", "confianza"}


class FakeSession:
    def __init__(self) -> None:
        cfg = server.CFG
        self.created = 1.0
        self.sims = [Simulation(alternative="F", seed=7, year=2025, config=cfg,
                                hourly_weather=synthesize_year(cfg["weather"], 2025, seed=2025),
                                weather_source="synthetic", patrol_dt_s=2.0)]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Any:
    s = FakeSession()
    sim = s.sims[0]
    for _ in range(40000):
        sim.step()
        if len(sim.incident_records) >= 3:
            break
    sim.external_event("real_detection", "x", "warn", bed=0, clase="sana", confianza=0.91, fuente="camara_d1")
    monkeypatch.setattr(server, "SESSIONS", {s})
    monkeypatch.setattr(server, "LAST_SESSION", s)
    return TestClient(server.app)


def test_incidencias_normalizadas(client: Any) -> None:
    r = client.get("/api/dashboard/incidencias?limit=200")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 4
    for it in items:
        assert FIELDS <= set(it)
        assert it["clase"] in ("sana", "oidio", "alternaria", "heliothis")
        assert it["estado"] == ("Saludable" if it["clase"] == "sana" else "Alerta")
        assert it["ubicacion"].startswith("N") and " C" in it["ubicacion"] and " P" in it["ubicacion"]
        assert it["fuente"] in ("simulacion", "camara_d1")
    d1 = [i for i in items if i["fuente"] == "camara_d1"]
    assert d1 and d1[0]["estado"] == "Saludable" and d1[0]["confianza"] == 0.91
    assert items[0]["id"] == d1[0]["id"]  # newest first


def test_limit(client: Any) -> None:
    assert len(client.get("/api/dashboard/incidencias?limit=2").json()["items"]) == 2
    assert client.get("/api/dashboard/incidencias?limit=0").status_code == 422


def test_resumen(client: Any) -> None:
    r = client.get("/api/dashboard/resumen").json()
    assert r["total"] >= 4 and 0 <= r["plantas_saludables_pct"] <= 100
    assert set(r["por_clase"]) >= {"sana", "oidio", "alternaria", "heliothis"}
    assert r["temperatura_promedio"] is not None and r["humedad_promedio"] is not None
    assert r["por_fuente"]["camara_d1"] == 1


def test_sin_sesion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "SESSIONS", set())
    monkeypatch.setattr(server, "LAST_SESSION", None)
    c = TestClient(server.app)
    assert c.get("/api/dashboard/incidencias").json()["items"] == []
    assert c.get("/api/dashboard/resumen").json()["conectado"] is False


def test_cors(client: Any) -> None:
    r = client.get("/api/dashboard/resumen", headers={"Origin": "http://localhost:5180"})
    assert r.headers["access-control-allow-origin"] in ("*", "http://localhost:5180")


def test_stream_contenido(client: Any) -> None:
    import asyncio
    import dashboard

    s = server.LAST_SESSION
    router = dashboard.make_router(lambda: [s], lambda: s)
    stream = next(rt for rt in router.routes if rt.path.endswith("/stream"))

    async def first() -> dict[str, Any]:
        resp = await stream.endpoint()
        chunk = await resp.body_iterator.__anext__()
        await resp.body_iterator.aclose()
        assert resp.media_type == "text/event-stream"
        assert chunk.startswith("event: update\ndata: ")
        return json.loads(chunk.split("data: ", 1)[1])

    body = asyncio.run(first())
    assert body["reset"] is True and len(body["nuevas"]) >= 4 and "resumen" in body


def test_supervisor_elige_bloque_desde_el_panel() -> None:
    import types
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import dashboard as dash

    class Ses:
        def __init__(self) -> None:
            self.bloque = 1
            self.sims = []
        def handle(self, msg):
            if msg.get("cmd") == "bloque":
                self.bloque = min(max(int(msg["value"]), 1), 2)

    ses = Ses()
    app = FastAPI()
    app.include_router(dash.make_router(lambda: [ses], lambda: ses))
    c = TestClient(app)
    r = c.post("/api/dashboard/bloque", json={"bloque": 2})
    assert r.status_code == 200 and r.json()["bloque"] == 2 and ses.bloque == 2
    r = c.post("/api/dashboard/bloque", json={"bloque": 9})
    assert r.json()["bloque"] == 2  # se limita a los bloques que existen
