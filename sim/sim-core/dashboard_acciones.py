"""Ciclo de acción por foco: Nuevo -> Asignado -> Verificado -> Tratado -> Cerrado, con historial en SQLite.

El estado de un foco es el resultado de reproducir su historial (solo se añaden filas, nunca se editan).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

ESTADOS = ("nuevo", "asignado", "verificado", "tratado", "cerrado")
ACCIONES = ("asignar", "verificar", "tratar", "cerrar", "nota")
RESULTADOS = ("confirmado", "falsa_alarma")


class AccionInvalida(ValueError):
    """Transición o datos no válidos (el endpoint responde 409/422)."""


def siguiente(estado: str, resultado: str | None, accion: str, datos: dict[str, Any]) -> tuple[str, str | None]:
    """(estado, resultado) tras aplicar `accion`, o AccionInvalida."""
    if accion not in ACCIONES:
        raise AccionInvalida(f"acción desconocida: {accion}")
    if accion == "nota":
        if not (datos.get("nota") or "").strip():
            raise AccionInvalida("la nota no puede estar vacía")
        return estado, resultado
    if estado == "cerrado":
        raise AccionInvalida("el foco ya está cerrado")
    if accion == "asignar":
        if estado not in ("nuevo", "asignado"):
            raise AccionInvalida(f"no se puede asignar desde '{estado}'")
        if not (datos.get("responsable") or "").strip():
            raise AccionInvalida("indica a quién se asigna")
        return "asignado", None
    if accion == "verificar":
        if estado != "asignado":
            raise AccionInvalida("primero asigna el foco a alguien")
        if datos.get("resultado") not in RESULTADOS:
            raise AccionInvalida("resultado debe ser 'confirmado' o 'falsa_alarma'")
        return "verificado", datos["resultado"]
    if accion == "tratar":
        if estado != "verificado" or resultado != "confirmado":
            raise AccionInvalida("solo se trata un foco verificado y confirmado")
        if not (datos.get("detalle") or "").strip():
            raise AccionInvalida("describe qué se hizo")
        return "tratado", resultado
    # cerrar
    if estado == "tratado" or (estado == "verificado" and resultado == "falsa_alarma"):
        return "cerrado", resultado
    raise AccionInvalida(f"no se puede cerrar desde '{estado}'" + (" (falta tratarlo)" if estado == "verificado" else ""))


class Acciones:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS acciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT, foco_id TEXT NOT NULL, accion TEXT NOT NULL,
                estado TEXT NOT NULL, resultado TEXT, responsable TEXT, detalle TEXT, nota TEXT,
                ts REAL NOT NULL, sim_h REAL, incs TEXT)"""
            )
            cols = {r[1] for r in c.execute("PRAGMA table_info(acciones)")}
            if "incs" not in cols:  # bases creadas antes de esta columna
                c.execute("ALTER TABLE acciones ADD COLUMN incs TEXT")
            c.execute("CREATE INDEX IF NOT EXISTS ix_foco ON acciones(foco_id)")

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=5)
        c.row_factory = sqlite3.Row
        return c

    def historial(self, foco_id: str) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM acciones WHERE foco_id=? ORDER BY id", (foco_id,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def estado_de(hist: list[dict[str, Any]]) -> dict[str, Any]:
        """Estado actual reproducido desde el historial."""
        st: dict[str, Any] = {"estado": "nuevo", "resultado": None, "responsable": None, "verificado_sim_h": None,
                              "tratamiento": None, "ts_estado": None, "pasos": len(hist)}
        for h in hist:
            if h["accion"] == "nota":
                continue
            st.update(estado=h["estado"], resultado=h["resultado"], ts_estado=h["ts"])
            if h["accion"] == "asignar":
                st["responsable"] = h["responsable"]
            if h["accion"] == "verificar":
                st["verificado_sim_h"] = h["sim_h"]
            if h["accion"] == "tratar":
                st["tratamiento"] = h["detalle"]
        return st

    def estado(self, foco_id: str) -> dict[str, Any]:
        return self.estado_de(self.historial(foco_id))

    def estados(self) -> dict[str, dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM acciones ORDER BY id").fetchall()
        por: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            por.setdefault(r["foco_id"], []).append(dict(r))
        return {k: self.estado_de(v) for k, v in por.items()}

    def aplicar(self, foco_id: str, accion: str, datos: dict[str, Any], sim_h: float | None = None,
               incs: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            hist = self.historial(foco_id)
            cur = self.estado_de(hist)
            nuevo, resultado = siguiente(cur["estado"], cur["resultado"], accion, datos)
            with self._conn() as c:
                c.execute(
                    "INSERT INTO acciones(foco_id,accion,estado,resultado,responsable,detalle,nota,ts,sim_h,incs) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (foco_id, accion, nuevo, resultado, (datos.get("responsable") or "").strip() or None,
                     (datos.get("detalle") or "").strip() or None, (datos.get("nota") or "").strip() or None,
                     time.time(), sim_h, json.dumps(sorted(incs)) if incs else None),
                )
        return self.estado(foco_id)

    def incs_por_foco(self) -> dict[str, set[str]]:
        """Incidencias (números de registro) que tenía cada foco cuando se actuó sobre él: sirve para reconocerlo
        aunque cambie su id al crecer o fusionarse con otro foco."""
        with self._conn() as c:
            rows = c.execute("SELECT foco_id, incs FROM acciones WHERE incs IS NOT NULL").fetchall()
        out: dict[str, set[str]] = {}
        for r in rows:
            out.setdefault(r["foco_id"], set()).update(json.loads(r["incs"]))
        return out

    def etiquetas(self) -> dict[str, Any]:
        """Verificaciones en campo = etiquetas para mejorar el modelo (confirmado vs falsa alarma)."""
        est = self.estados()
        conf = sum(1 for s in est.values() if s["resultado"] == "confirmado")
        falsa = sum(1 for s in est.values() if s["resultado"] == "falsa_alarma")
        tot = conf + falsa
        return {"total": tot, "confirmadas": conf, "falsas_alarma": falsa, "pct_falsas": round(100 * falsa / tot, 1) if tot else None}
