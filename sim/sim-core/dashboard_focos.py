"""Focos: agrupa incidencias (alertas) cercanas y calcula su prioridad. Funciones puras (sin motor ni disco).

Prioridad (pesos en config/dashboard.yaml):
    prioridad = gravedad x plantas^p_plantas x riesgo_cama x antiguedad
    riesgo_cama = piso + (1 - piso) x riesgo combinado de la cama (0-1)
    antiguedad  = 1 + min(horas_sin_atender, tope) / escala
    puntaje     = 100 x prioridad / (prioridad + puntaje_ref)   (0-100)
"""
from __future__ import annotations

from typing import Any

NOMBRES = {"oidio": "Oídio", "alternaria": "Alternaria", "heliothis": "Heliothis", "desconocida": "Desconocida"}


def familia(clase: str, cfg: dict[str, Any]) -> str:
    return cfg["focos"]["familias"].get(clase, "otro")


def agrupar(incs: list[dict[str, Any]], cfg: dict[str, Any], semilla: Any = "") -> list[dict[str, Any]]:
    """Agrupa alertas en focos. Cada incidencia lleva nave, cama, planta, clase, t_h (horas del escenario)."""
    fc = cfg["focos"]
    gap, ventana = int(fc["max_gap_plantas"]), float(fc["ventana_h"])
    alertas = [i for i in incs if i.get("estado") == "Alerta" and i.get("planta") is not None]
    por_cama: dict[tuple[int, int, str], list[dict[str, Any]]] = {}
    for i in alertas:
        por_cama.setdefault((i["nave"], i["cama"], familia(i["clase"], cfg)), []).append(i)
    focos: list[dict[str, Any]] = []
    for (nave, cama, fam), lst in por_cama.items():
        lst.sort(key=lambda i: (i["planta"], i["t_h"]))
        grupos: list[list[dict[str, Any]]] = []
        for i in lst:  # barrido espacial: corta cuando la distancia entre plantas supera el hueco
            if grupos and i["planta"] - grupos[-1][-1]["planta"] <= gap:
                grupos[-1].append(i)
            else:
                grupos.append([i])
        for g in grupos:  # corte temporal: detecciones muy separadas en el tiempo son otro foco
            g.sort(key=lambda i: i["t_h"])
            sub = [[g[0]]]
            for i in g[1:]:
                if i["t_h"] - sub[-1][-1]["t_h"] <= ventana:
                    sub[-1].append(i)
                else:
                    sub.append([i])
            for s in sub:
                focos.append(_foco(nave, cama, fam, s, semilla))
    return focos


def _foco(nave: int, cama: int, fam: str, items: list[dict[str, Any]], semilla: Any) -> dict[str, Any]:
    first = min(items, key=lambda i: (i["t_h"], int(str(i["id"]).rsplit("-", 1)[-1]) if str(i["id"]).rsplit("-", 1)[-1].isdigit() else 0))
    plantas = sorted({i["planta"] for i in items})
    clases: dict[str, int] = {}
    for i in items:
        clases[i["clase"]] = clases.get(i["clase"], 0) + 1
    dom = max(clases, key=lambda c: clases[c])
    frames = [i for i in items if i.get("frame")]
    confs = [i["confianza"] for i in items if i.get("confianza") is not None]
    return {
        "id": f"S{semilla}-N{nave}C{cama}-{fam}-{first['id'].rsplit('-', 1)[-1]}",
        "nave": nave, "cama": cama, "familia": fam,
        "plantas": len(plantas), "planta_min": plantas[0], "planta_max": plantas[-1],
        "ubicacion": f"N{nave} C{cama} P{plantas[0]}" + (f"–P{plantas[-1]}" if plantas[-1] != plantas[0] else ""),
        "clase": dom, "clases": clases,
        "deteccion": NOMBRES.get(dom, dom) + (f" (+{len(clases) - 1})" if len(clases) > 1 else ""),
        "detecciones": len(items),
        "primera_h": first["t_h"], "ultima_h": max(i["t_h"] for i in items),
        "incidencias": [i["id"] for i in items],
        "fuentes": sorted({i["fuente"] for i in items}),
        "confianza_max": max(confs) if confs else None,
        "frame": frames[-1]["frame"] if frames else None,
        "_items": items,
    }


def numeros(f: dict[str, Any]) -> set[str]:
    """Números de registro de las incidencias de un foco (sin el id de sesión)."""
    return {str(i).rsplit("-", 1)[-1] for i in f["incidencias"]}


def adoptar_ids(focos: list[dict[str, Any]], registro: dict[str, set[str]]) -> None:
    """Mantiene estable el id de un foco aunque crezca o se fusione: hereda el id registrado con el que más
    incidencias comparte. `registro` (id -> incidencias) se actualiza en sitio. Un foco fusionado con otro que ya
    tenía acciones hereda el id del que comparte más incidencias."""
    usados: set[str] = set()
    for f in sorted(focos, key=lambda f: -f["plantas"]):
        mine = numeros(f)
        mejor, n = None, 0
        for k, inc in registro.items():
            if k in usados:
                continue
            o = len(inc & mine)
            if o > n:
                mejor, n = k, o
        if mejor is not None:
            f["id"] = mejor
        elif f["id"] in usados:
            f["id"] = f"{f['id']}b"
        usados.add(f["id"])
    for f in focos:
        registro[f["id"]] = numeros(f)


def serie_plantas(foco: dict[str, Any], now_h: float, puntos: int) -> list[int]:
    """Plantas afectadas acumuladas en `puntos` instantes repartidos entre la primera detección y ahora."""
    t0 = foco["primera_h"]
    span = max(now_h - t0, 1e-6)
    out = []
    for k in range(puntos):
        t = t0 + span * (k + 1) / puntos
        out.append(len({i["planta"] for i in foco["_items"] if i["t_h"] <= t + 1e-9}))
    return out


def enriquecer(foco: dict[str, Any], riesgo_cama: float, now_h: float, cfg: dict[str, Any],
               accion: dict[str, Any] | None = None) -> dict[str, Any]:
    fc, at = cfg["focos"], cfg["atencion"]
    w = fc["pesos"]
    accion = accion or {"estado": "nuevo", "resultado": None, "responsable": None, "verificado_sim_h": None}
    grav = max(float(fc["gravedad"].get(c, 0.5)) for c in foco["clases"])
    # Antigüedad sin atender: corre hasta la verificación en campo; después se congela.
    fin = accion.get("verificado_sim_h") if accion["estado"] in ("verificado", "tratado", "cerrado") else None
    sin_atender = max(0.0, (fin if fin is not None else now_h) - foco["primera_h"])
    antig = 1.0 + min(sin_atender, float(w["antig_tope_h"])) / float(w["antig_escala_h"])
    rc = float(w["riesgo_piso"]) + (1.0 - float(w["riesgo_piso"])) * max(0.0, min(1.0, riesgo_cama))
    prio = grav * (foco["plantas"] ** float(w["p_plantas"])) * rc * antig
    puntaje = round(100.0 * prio / (prio + float(w["puntaje_ref"])), 1)
    nivel = "alta" if puntaje >= fc["nivel_puntaje"]["alto"] else "media" if puntaje >= fc["nivel_puntaje"]["medio"] else "baja"
    abierto = accion["estado"] != "cerrado"
    atendido = accion["estado"] in ("verificado", "tratado", "cerrado")
    semaforo = "verde" if atendido else "rojo" if sin_atender >= at["rojo_h"] else "ambar" if sin_atender >= at["ambar_h"] else "verde"
    serie = serie_plantas(foco, now_h, int(fc["tendencia"]["puntos"]))
    vent = float(fc["tendencia"]["ventana_h"])
    nuevas = len({i["planta"] for i in foco["_items"] if i["t_h"] > now_h - vent}) - len({i["planta"] for i in foco["_items"] if i["t_h"] <= now_h - vent})
    if accion["estado"] in ("tratado", "cerrado") and nuevas <= 0:
        tend = "baja"
    elif nuevas >= int(fc["nuevas_para_crecer"]):
        tend = "crece"
    else:
        tend = "estable"
    porque = []
    if foco["plantas"] >= 5:
        porque.append(f"{foco['plantas']} plantas afectadas")
    if grav >= 0.9:
        porque.append("enfermedad/plaga de alta gravedad")
    if riesgo_cama >= 0.5:
        porque.append("el clima favorece que avance en esa cama")
    if sin_atender >= at["ambar_h"] and not atendido:
        porque.append(f"lleva {sin_atender:.0f} h sin atender")
    if tend == "crece":
        porque.append("sigue creciendo")
    if not porque:
        porque.append("foco pequeño y reciente")
    out = {k: v for k, v in foco.items() if k != "_items"}
    out.update(
        riesgo_cama=round(float(riesgo_cama), 3), gravedad=grav, prioridad=round(prio, 2), puntaje=puntaje, nivel=nivel,
        horas_sin_atender=round(sin_atender, 1), semaforo=semaforo, tendencia=tend, serie=serie, por_que=porque,
        estado=accion["estado"], resultado=accion.get("resultado"), responsable=accion.get("responsable"),
        tratamiento=accion.get("tratamiento"), abierto=abierto,
    )
    out["aviso"] = aviso_texto(out)
    return out


def aviso_texto(f: dict[str, Any]) -> str:
    """Texto corto listo para pantalla de oficina o mensajería (no se envía a ningún servicio)."""
    fuente = " (cámara D1)" if "camara_d1" in f.get("fuentes", []) else ""
    sem = {"rojo": "URGENTE", "ambar": "Atención", "verde": "Aviso"}.get(f.get("semaforo", "verde"), "Aviso")
    return (f"{sem}: {f['deteccion']} en {f['ubicacion']}{fuente}, {f['plantas']} plantas. "
            f"Prioridad {f['nivel']} ({f['puntaje']:.0f}/100), {f['horas_sin_atender']:.0f} h sin atender. "
            f"Estado: {f['estado']}" + (f" ({f['responsable']})" if f.get("responsable") else "") + ". Verificar en campo.")
