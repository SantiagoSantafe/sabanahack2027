#!/usr/bin/env python3
"""
Motor genérico de perfiles de cultivo (prueba de concepto de escalabilidad).

Qué demuestra: un cultivo nuevo se agrega con un YAML, sin tocar este código.
  1. Carga perfiles con herencia (hereda_de) y los valida contra el esquema v0.1.
  2. Revisa que el robot quepa en la geometría del cultivo (pasillo, pendiente).
  3. Corre todos los modelos de riesgo con 6 motores genéricos:
       logit_polinomico, gim_magarey2005, indice_gubler_thomas,
       regla_umbral, acumulado_ventana, referencia_externa (usa su respaldo).
  4. Verifica las ecuaciones contra puntos de control calculados a mano.

El escenario de clima es SINTÉTICO (10 días, ciclo diario tipo altiplano). Sirve para
probar el motor, NO es una predicción ni un dato de campo.

Uso:
  /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
      /Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/motor_perfiles.py
Salida: escalabilidad/validacion_perfiles.json
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent
PERFILES = BASE / "perfiles"
SALIDA = BASE / "validacion_perfiles.json"

ESTADOS = {"VERIFICADO", "CALCULO", "SUPUESTO", "NO_VERIFICADO"}
MOTORES = {"logit_polinomico", "gim_magarey2005", "indice_gubler_thomas",
           "regla_umbral", "acumulado_ventana", "referencia_externa"}
REQUERIDOS = ["esquema", "id", "version", "nombre_comun", "especie", "fuentes",
              "geometria.sistema", "geometria.unidad_de_inspeccion", "fenologia.modo",
              "modelos_riesgo", "clases_visuales.clases", "captura.plataforma",
              "captura.idoneidad_cuadrupedo"]


# ----------------------------------------------------------------------------- carga
def fusionar(padre: dict, hijo: dict) -> dict:
    """Herencia: dict se fusiona recursivamente; listas y escalares del hijo reemplazan."""
    out = copy.deepcopy(padre)
    for k, v in hijo.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = fusionar(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# Solo se hereda lo OPERATIVO (plataforma, sensores, alertas, registro, fuentes).
# Lo AGRONÓMICO (geometría, fenología, modelos, clases, mercado) es siempre propio del
# cultivo: heredarlo metería, por ejemplo, la altura del arándano en la fresa.
HEREDABLES = ("fuentes", "sensores_ambientales", "captura", "alertas", "registro_incidencia")


def cargar(id_perfil: str, _visto=None) -> dict:
    _visto = _visto or set()
    if id_perfil in _visto:
        raise ValueError(f"herencia circular en {id_perfil}")
    _visto.add(id_perfil)
    crudo = yaml.safe_load((PERFILES / f"{id_perfil}.yaml").read_text(encoding="utf-8"))
    padre = crudo.get("hereda_de")
    if padre:
        base = cargar(padre, _visto)
        base = {k: v for k, v in base.items() if k in HEREDABLES}
        return fusionar(base, crudo)
    return crudo


def obtener(d: dict, ruta: str):
    cur = d
    for parte in ruta.split("."):
        if not isinstance(cur, dict) or parte not in cur:
            return None
        cur = cur[parte]
    return cur


def recorrer(obj, ruta=""):
    if isinstance(obj, dict):
        yield ruta, obj
        for k, v in obj.items():
            yield from recorrer(v, f"{ruta}.{k}" if ruta else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from recorrer(v, f"{ruta}[{i}]")


# ----------------------------------------------------------------------------- validación
def validar(p: dict) -> dict:
    errores, avisos = [], []
    for r in REQUERIDOS:
        if obtener(p, r) in (None, [], {}):
            errores.append(f"falta '{r}'")
    fuentes = set((p.get("fuentes") or {}).keys())
    conteo_estados = {e: 0 for e in ESTADOS}
    for ruta, nodo in recorrer(p):
        if "estado" in nodo and isinstance(nodo["estado"], str) and nodo["estado"].isupper():
            if nodo["estado"] not in ESTADOS:
                errores.append(f"{ruta}: estado desconocido '{nodo['estado']}'")
            else:
                conteo_estados[nodo["estado"]] += 1
        for clave in ("fuente", "datos_originales", "referencia"):
            ref = nodo.get(clave)
            if isinstance(ref, str) and ref not in fuentes and not ref.startswith("http"):
                errores.append(f"{ruta}: fuente '{ref}' no está en 'fuentes'")
        if "motor" in nodo and nodo["motor"] not in MOTORES:
            errores.append(f"{ruta}: motor desconocido '{nodo['motor']}'")
    ids_clases = [c.get("id") for c in (obtener(p, "clases_visuales.clases") or [])]
    if "desconocido" not in ids_clases:
        errores.append("clases_visuales debe incluir la clase 'desconocido' (fuera de distribución)")

    # ¿Cabe el robot en el cultivo?  (la geometría manda sobre la plataforma)
    dim = obtener(p, "captura.dimensiones_robot_mm") or {}
    ancho_robot = (dim.get("ancho") or 0) / 1000
    holgura = (obtener(p, "captura.holgura_lateral_min_m") or {}).get("valor", 0.1)
    pasillo = obtener(p, "geometria.ancho_pasillo_libre_m") or {}
    necesario = ancho_robot + 2 * holgura
    if pasillo and ancho_robot:
        if pasillo.get("max", 9) < necesario:
            errores.append(f"el robot no cabe: pasillo máx {pasillo.get('max')} m < {necesario:.2f} m")
        elif pasillo.get("min", 9) < necesario:
            avisos.append(f"pasillo mínimo {pasillo.get('min')} m < {necesario:.2f} m necesarios: "
                          "en lotes con dosel cerrado el robot no pasa; marcar camas no aptas")
    pend = (obtener(p, "geometria.pendiente_tipica_grados") or {}).get("max")
    if pend is not None and pend > 30:
        avisos.append(f"pendiente {pend}° > 30° (límite estándar del D1 Ultra)")
    dosel = obtener(p, "geometria.altura_dosel_m") or obtener(p, "geometria.altura_dosel_sobre_suelo_m") or {}
    alturas_cam = [c.get("altura_m", 0) for c in (obtener(p, "captura.camaras") or [])]
    if dosel and alturas_cam and max(alturas_cam) < 0.6 * dosel.get("max", 0):
        avisos.append(f"cámara más alta {max(alturas_cam)} m vs dosel {dosel.get('max')} m: "
                      "tercio superior sin cubrir")
    return {"errores": errores, "avisos": avisos, "conteo_estados": conteo_estados,
            "n_modelos": len(p.get("modelos_riesgo") or []), "n_clases": len(ids_clases)}


# ----------------------------------------------------------------------------- clima sintético
def escenario_sintetico(dias=10, tipo="humedo"):
    """Horas con T (°C), HR (%), mojado (bool), lluvia (mm), suelo saturado (bool). SINTÉTICO.
    humedo: rocío todas las noches y 4 días de lluvia; seco: sin rocío ni lluvia."""
    horas = []
    for d in range(dias):
        lluvioso = tipo == "humedo" and d in (3, 4, 5, 8)
        for h in range(24):
            # ciclo diario: mínimo 8 °C a las 5 h, máximo 21 °C a las 14 h
            t = 14.5 + 6.5 * math.sin((h - 8) / 24 * 2 * math.pi)
            if lluvioso:
                t -= 1.5
            hr = (96.0 if tipo == "humedo" else 88.0) if (h >= 20 or h <= 7) else 70.0
            if lluvioso and 13 <= h <= 19:
                hr = 97.0
            mojado = hr >= 95.0
            lluvia = 2.0 if (lluvioso and 14 <= h <= 18) else 0.0
            horas.append({"dia": d, "hora": h, "T": round(t, 2), "HR": hr, "mojado": mojado,
                          "lluvia": lluvia, "suelo_saturado": lluvioso})
    return horas


def eventos_humectacion(horas, corte_seco_h=4, hr_humeda=None):
    """Agrupa horas mojadas; un periodo seco >= corte_seco_h cierra el evento (regla FLSAS/UC IPM)."""
    eventos, actual, secas = [], None, 0
    for i, x in enumerate(horas):
        moj = x["mojado"] or (hr_humeda is not None and x["HR"] >= hr_humeda)
        if moj:
            if actual is None:
                actual = {"inicio": i, "fin": i, "T": [], "HR": []}
            actual["fin"] = i
            actual["T"].append(x["T"])
            actual["HR"].append(x["HR"])
            secas = 0
        elif actual is not None:
            secas += 1
            if secas >= corte_seco_h:
                eventos.append(actual)
                actual, secas = None, 0
    if actual is not None:
        eventos.append(actual)
    for e in eventos:
        e["W"] = len(e["T"])
        e["Tm"] = sum(e["T"]) / len(e["T"])
        e["HRm"] = sum(e["HR"]) / len(e["HR"])
        e["dia"] = horas[e["inicio"]]["dia"]
    return eventos


def nivel(valor, umbrales):
    if valor is None:
        return "sin_dato"
    orden = [("alto", umbrales.get("alto")), ("moderado", umbrales.get("moderado"))]
    for nombre, u in orden:
        if u is not None and valor >= u:
            return nombre
    return "bajo"


# ----------------------------------------------------------------------------- motores
def m_logit(modelo, horas):
    reglas = modelo.get("reglas_entrada", {})
    evs = eventos_humectacion(horas, reglas.get("corte_seco_h", 4), reglas.get("HR_humeda_pct"))
    peor = None
    for e in evs:
        T = min(max(e["Tm"], reglas.get("T_min_C", -99)), reglas.get("T_max_C", 99))
        f = sum(t["coef"] * (e["W"] ** t["w"]) * (T ** t["t"]) for t in modelo["terminos"])
        val = 1 / (1 + math.exp(-f)) if modelo.get("salida") == "probabilidad_logistica" else f
        if peor is None or val > peor["valor"]:
            peor = {"valor": round(val, 3), "W_h": e["W"], "T_C": round(T, 1), "dia": e["dia"]}
    return {"max": peor, "nivel": nivel(peor["valor"], modelo.get("umbrales", {})) if peor else "bajo",
            "n_eventos": len(evs)}


def f_temp_yin(T, Tmin, Topt, Tmax):
    if T < Tmin or T > Tmax:
        return 0.0
    return ((Tmax - T) / (Tmax - Topt)) * ((T - Tmin) / (Topt - Tmin)) ** ((Topt - Tmin) / (Tmax - Topt))


def m_gim(modelo, horas):
    pr = modelo["parametros"]
    evs = eventos_humectacion(horas)
    peor = None
    for e in evs:
        f = f_temp_yin(e["Tm"], pr["Tmin"], pr["Topt"], pr["Tmax"])
        if f <= 0:
            continue
        w_req = min(pr["Wmin"] / f, pr["Wmax"])            # Magarey 2005, ec. 1
        ciclos = e["W"] / w_req
        if peor is None or ciclos > peor["valor"]:
            peor = {"valor": round(ciclos, 2), "W_h": e["W"], "W_requerida_h": round(w_req, 1),
                    "T_C": round(e["Tm"], 1), "dia": e["dia"]}
    # 1 ciclo = umbral crítico de Magarey (20 % incidencia); 0,5 = moderado (SUPUESTO)
    return {"max": peor, "nivel": nivel(peor["valor"], {"moderado": 0.5, "alto": 1.0}) if peor else "bajo",
            "n_eventos": len(evs)}


def m_gubler(modelo, horas):
    pr = modelo["parametros"]
    lo, hi = pr["ventana_C"]
    indice, racha, iniciado, historial = 0, 0, False, []
    for d in sorted({x["dia"] for x in horas}):
        dia = [x for x in horas if x["dia"] == d]
        mejor = cur = 0
        for x in dia:
            cur = cur + 1 if lo <= x["T"] <= hi else 0
            mejor = max(mejor, cur)
        favorable = mejor >= pr["horas_continuas_min"]
        letal = any(x["T"] >= pr["temp_letal_C"] for x in dia)
        if not iniciado:
            racha = racha + 1 if favorable else 0
            if racha >= pr["dias_consecutivos_para_iniciar"]:
                iniciado, indice = True, pr["puntos_dia_favorable"] * racha
        else:
            delta = pr["puntos_dia_favorable"] if favorable else pr["puntos_dia_desfavorable"]
            if letal:
                delta += pr["puntos_dia_desfavorable"]
            indice += delta
        indice = max(pr["indice_min"], min(pr["indice_max"], indice))
        historial.append(indice)
    return {"max": {"valor": max(historial)}, "final": historial[-1], "serie": historial,
            "nivel": nivel(historial[-1], modelo.get("umbrales", {}))}


def agregados_diarios(horas):
    out = {}
    dias = sorted({x["dia"] for x in horas})
    racha_lluvia = 0
    for d in dias:
        dia = [x for x in horas if x["dia"] == d]
        moj = [x for x in dia if x["mojado"]]
        racha_lluvia = racha_lluvia + 1 if sum(x["lluvia"] for x in dia) > 0 else 0
        ult7 = [x for x in horas if d - 6 <= x["dia"] <= d]
        ult2 = [x for x in horas if d - 1 <= x["dia"] <= d]
        out[d] = {
            "horas_humectacion_dia": len(moj),
            "temp_media_humectacion_C": sum(x["T"] for x in moj) / len(moj) if moj else None,
            "hr_media_dia_pct": sum(x["HR"] for x in dia) / len(dia),
            "temp_media_dia_C": sum(x["T"] for x in dia) / len(dia),
            "temp_media_C": sum(x["T"] for x in dia) / len(dia),
            "lluvia_dias_consecutivos": racha_lluvia,
            "lluvia_mm_24_48h": sum(x["lluvia"] for x in ult2),
            "horas_suelo_saturado_7d": sum(1 for x in ult7 if x["suelo_saturado"]),
        }
    return out


def cumple(valor, op, ref):
    if valor is None:
        return None
    if op == ">=":
        return valor >= ref
    if op == ">":
        return valor > ref
    if op == "<=":
        return valor <= ref
    if op == "<":
        return valor < ref
    if op == "entre":
        return ref[0] <= valor <= ref[1]
    raise ValueError(op)


def m_regla(modelo, horas):
    conds = modelo["condiciones"].get("todas", [])
    diarios = agregados_diarios(horas)
    eventos = eventos_humectacion(horas)
    usa_evento = any(c["variable"].endswith("_evento") for c in conds)
    filas = []
    if usa_evento:
        for e in eventos:
            vals = {"horas_humectacion_evento": e["W"], "hr_media_evento_pct": e["HRm"],
                    "temp_media_evento_C": e["Tm"]}
            vals.update(diarios[e["dia"]])
            filas.append((e["dia"], vals))
    else:
        filas = list(diarios.items())
    dias_ok, faltantes = [], set()
    for d, vals in filas:
        res = []
        for c in conds:
            r = cumple(vals.get(c["variable"]), c["operador"], c["valor"])
            if r is None:
                faltantes.add(c["variable"])
            res.append(bool(r))
        if all(res):
            dias_ok.append(d)
    persist = modelo.get("persistencia_dias", 1)
    seguidos = mejor = 0
    for d in sorted(set(dias_ok)):
        seguidos = seguidos + 1 if (d - 1) in dias_ok else 1
        mejor = max(mejor, seguidos)
    nivel_r = "alto" if mejor >= persist and dias_ok else "bajo"
    return {"dias_que_cumplen": sorted(set(dias_ok)), "nivel": nivel_r,
            "datos_faltantes": sorted(faltantes)}


def m_acumulado(modelo, horas):
    pr = modelo["parametros"]
    diarios = agregados_diarios(horas)
    dias = sorted(diarios)
    ult = dias[-pr["ventana_dias"]:]
    prom = sum(diarios[d]["horas_humectacion_dia"] for d in ult) / len(ult)
    return {"max": {"valor": round(prom, 2)}, "nivel": "alto" if prom >= pr["umbral_promedio_horas_dia"] else "bajo"}


def correr(modelo, horas):
    motor = modelo["motor"]
    if motor == "referencia_externa":
        resp = modelo.get("respaldo_generico")
        if not resp:
            return {"nivel": "sin_motor_local"}
        r = correr({**resp, "umbrales": modelo.get("umbrales", {})}, horas)
        r["nota"] = "respaldo genérico (modelo externo no disponible)"
        return r
    return {"logit_polinomico": m_logit, "gim_magarey2005": m_gim,
            "indice_gubler_thomas": m_gubler, "regla_umbral": m_regla,
            "acumulado_ventana": m_acumulado}[motor](modelo, horas)


# ----------------------------------------------------------------------------- controles
def puntos_de_control():
    """Valores calculados a mano con las ecuaciones publicadas (ver cultivos.md, sección 5)."""
    def logit(terms, W, T):
        return sum(c * W ** w * T ** t for c, w, t in terms)
    wilson = [(-3.7, 0, 0), (0.33, 1, 0), (-0.069, 1, 1), (0.005, 1, 2), (-9.3e-5, 1, 3)]
    bulger = [(-4.268, 0, 0), (-0.0901, 1, 0), (0.0294, 1, 1), (-2.35e-5, 1, 3)]
    broome = [(-2.647866, 0, 0), (-0.374927, 1, 0), (0.061601, 1, 1), (-0.001511, 1, 2)]
    pruebas = {
        "wilson_W12_T25_logit": (logit(wilson, 12, 25), -0.3775),
        "bulger_W16_T20_logit": (logit(bulger, 16, 20), 0.6904),
        "broome_W12_T20_indice": (logit(broome, 12, 20), 0.3840),
        "gim_f(Topt)=1": (f_temp_yin(27.5, 7, 27.5, 35), 1.0),
        "gim_f(Tmin)=0": (f_temp_yin(7, 7, 27.5, 35), 0.0),
    }
    out, ok = {}, True
    for k, (calc, esperado) in pruebas.items():
        bien = abs(calc - esperado) < 1e-3
        ok &= bien
        out[k] = {"calculado": round(calc, 4), "esperado": esperado, "ok": bien}
    return ok, out


# ----------------------------------------------------------------------------- main
def main():
    ok_ctrl, ctrl = puntos_de_control()
    escenarios = {"humedo": escenario_sintetico(tipo="humedo"), "seco": escenario_sintetico(tipo="seco")}
    resultado = {"escenario": "SINTÉTICOS (humedo y seco), 10 días; solo prueban el motor",
                 "puntos_de_control": ctrl, "perfiles": {}, "catalogo_otros_cultivos": {}}
    hay_error = not ok_ctrl
    for ruta in sorted(PERFILES.glob("*.yaml")):
        if ruta.name.startswith("_"):
            continue
        pid = ruta.stem
        p = cargar(pid)
        v = validar(p)
        riesgos = {m["id"]: {esc: correr(m, h) for esc, h in escenarios.items()}
                   for m in p.get("modelos_riesgo", [])}
        resultado["perfiles"][pid] = {"validacion": v, "riesgo_escenario_sintetico": riesgos}
        hay_error |= bool(v["errores"])
    cat = yaml.safe_load((PERFILES / "_modelos_otros_cultivos.yaml").read_text(encoding="utf-8"))
    fuentes_cat = set(cat.get("fuentes", {}))
    for cultivo, modelos in cat.items():
        if cultivo in ("esquema", "fuentes"):
            continue
        for m in modelos:
            if m["motor"] not in MOTORES:
                hay_error = True
            if m.get("fuente") and m["fuente"] not in fuentes_cat:
                hay_error = True
            resultado["catalogo_otros_cultivos"][f"{cultivo}.{m['id']}"] = {
                esc: correr(m, h) for esc, h in escenarios.items()}
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Puntos de control de ecuaciones:", "OK" if ok_ctrl else "FALLA")
    for k, v in ctrl.items():
        print(f"  {k:28s} calc={v['calculado']:>8} esperado={v['esperado']:>8} {'ok' if v['ok'] else 'FALLA'}")
    print("\nPerfiles (escenario SINTÉTICO, no es predicción):")
    for pid, r in resultado["perfiles"].items():
        v = r["validacion"]
        print(f"- {pid}: {v['n_modelos']} modelos, {v['n_clases']} clases, errores={len(v['errores'])}, "
              f"avisos={len(v['avisos'])}, estados={v['conteo_estados']}")
        for e in v["errores"]:
            print("    ERROR:", e)
        for a in v["avisos"]:
            print("    aviso:", a)
        for mid, rr in r["riesgo_escenario_sintetico"].items():
            print(f"    {mid:40s} húmedo={rr['humedo'].get('nivel'):9s} seco={rr['seco'].get('nivel'):9s} "
                  f"max_húmedo={rr['humedo'].get('max')}")
    print("\nCatálogo de otros cultivos:")
    for mid, rr in resultado["catalogo_otros_cultivos"].items():
        print(f"    {mid:45s} húmedo={rr['humedo'].get('nivel'):9s} seco={rr['seco'].get('nivel'):9s}")
    print(f"\nGuardado: {SALIDA}")
    return 1 if hay_error else 0


if __name__ == "__main__":
    sys.exit(main())
