"""
backtest_riesgo.py -- Backtest de los modelos de riesgo (riesgo/risk.py) sobre el clima horario 2025
(Open-Meteo, clima/cache/historico_2025_<punto>.csv) de los 4 puntos, y riesgo de HOY con el
pronostico en cache.

    /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
        /Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/backtest/backtest_riesgo.py

No descarga nada: solo lee clima/cache, clima/qc, raw/ideam_datosgov_2025 (como DATOS) y riesgo/risk.py.
Salidas en resultados/backtest/ (ver README del reporte: reportes/backtest-riesgo.md).

Etiquetas: SUPUESTO = valor elegido por el equipo sin fuente directa.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))          # .../datos
sys.path.insert(0, os.path.join(RAIZ, "riesgo"))
import risk as r  # noqa: E402

CACHE = os.path.join(RAIZ, "clima", "cache")
QC = os.path.join(RAIZ, "clima", "qc")
RAW_IDEAM = os.path.join(RAIZ, "raw", "ideam_datosgov_2025")
SAL = AQUI

ENF = ("antracnosis", "botrytis", "roya")
PUNTOS = ("sotaquira", "tausa", "guasca", "chia")
# Metadatos de los puntos: reportes/clima-open-meteo.md (EVA 2025, UPRA, datos.gov.co uejq-wxrr).
META = {
    "sotaquira": {"nombre": "Sotaquira (Boyaca)", "ha_eva_2025": 182, "rol": "productor (1.o del pais)"},
    "tausa": {"nombre": "Tausa (Cundinamarca)", "ha_eva_2025": 121, "rol": "productor (1.o de Cundinamarca)"},
    "guasca": {"nombre": "Guasca (Cundinamarca)", "ha_eva_2025": 57, "rol": "productor"},
    "chia": {"nombre": "Chia (Cundinamarca)", "ha_eva_2025": 0, "rol": "sitio de la demo (sin area en EVA)"},
}
# Criterios de hoja mojada: reportes/clima-open-meteo.md (calibracion IDEAM vs Open-Meteo 2025).
CRITERIOS = {
    "HR85": r.ConfigMojadura(umbral_hr=85, umbral_lluvia_mm=0.5),   # escenario de alerta
    "HR90": r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.5),   # escenario central (defecto de risk.py)
    "HR95": r.ConfigMojadura(umbral_hr=95, umbral_lluvia_mm=0.5),
}
CENTRAL = "HR90"
# Estaciones IDEAM con HR valida y pluviometro (reportes/clima-open-meteo.md, seccion 6). Guasca y Tunguavita
# se excluyen para la mojadura por sensor de HR que no satura; Guasca si se usa para la lluvia observada.
EST_RIESGO = {"2120500135": "chia", "2401500040": "tausa", "2403500041": "sotaquira"}
EST_LLUVIA = {"2120500135": "chia", "2401500040": "tausa", "2403500041": "sotaquira", "0021205700": "guasca"}
# Temporadas: reportes/ciencia-enfermedades.md seccion 8 (lluvias bimodales mar-may y sep-nov; secas dic-feb y jun-ago).
TEMPORADA = {12: "seca", 1: "seca", 2: "seca", 3: "lluviosa", 4: "lluviosa", 5: "lluviosa",
             6: "seca", 7: "seca", 8: "seca", 9: "lluviosa", 10: "lluviosa", 11: "lluviosa"}
HOY = date.today()


def escribir(filas, nombre):
    ruta = os.path.join(SAL, nombre)
    r.escribir_csv(filas, ruta)
    return ruta


def cargar_om(punto):
    return r.horas_desde_csv(os.path.join(CACHE, "historico_2025_%s.csv" % punto), {"modelo": "best_match"})


def episodios(clases):
    """Numero de rachas de dias consecutivos en 'alto' (una alerta operativa por racha)."""
    n, prev = 0, False
    for c in clases:
        a = c == "alto"
        if a and not prev:
            n += 1
        prev = a
    return n


# =====================================================================================
# 1-2. Dias por clase por mes, por punto, enfermedad y criterio
# =====================================================================================
def parte_mensual(horas_pt):
    mensual, anual, diarios = [], [], {}
    for p, horas in horas_pt.items():
        lluvia_mes = defaultdict(float)
        for h in horas:
            lluvia_mes[h.time.month] += h.lluvia
        for crit, cfg in CRITERIOS.items():
            dias = r.resumen_diario(horas, cfg)
            diarios[(p, crit)] = dias
            mojadas_mes = defaultdict(int)
            for h in horas:
                if r.hora_mojada(h, cfg):
                    mojadas_mes[h.time.month] += 1
            for enf in ENF:
                for mes in range(1, 13):
                    dm = [d for d in dias if d["fecha"].month == mes]
                    c = Counter(d["clase_" + enf] for d in dm)
                    # episodio que arranca en el mes (dia alto cuyo dia anterior no es alto)
                    por_fecha = {x["fecha"]: x["clase_" + enf] for x in dias}
                    ep = sum(1 for d in dm if d["clase_" + enf] == "alto"
                             and por_fecha.get(d["fecha"] - timedelta(days=1)) != "alto")
                    mensual.append({"punto": p, "criterio": crit, "mes": mes, "temporada": TEMPORADA[mes],
                                    "enfermedad": enf, "dias_mes": len(dm), "dias_bajo": c["bajo"],
                                    "dias_medio": c["medio"], "dias_alto": c["alto"], "episodios_alto": ep,
                                    "idx_max": round(max(d["idx_" + enf] for d in dm), 3),
                                    "lluvia_om_mm": round(lluvia_mes[mes], 1),
                                    "horas_mojadas": mojadas_mes[mes]})
                c = Counter(d["clase_" + enf] for d in dias)
                anual.append({"punto": p, "criterio": crit, "enfermedad": enf, "dias": len(dias),
                              "dias_bajo": c["bajo"], "dias_medio": c["medio"], "dias_alto": c["alto"],
                              "episodios_alto": episodios([d["clase_" + enf] for d in dias]),
                              "horas_mojadas_anio": sum(1 for h in horas if r.hora_mojada(h, cfg))})
            # cualquiera de las 3: un dia es "alto" si alguna enfermedad esta en alto (carga de alertas del agronomo)
            cual = ["alto" if any(d["clase_" + e] == "alto" for e in ENF) else
                    ("medio" if any(d["clase_" + e] == "medio" for e in ENF) else "bajo") for d in dias]
            c = Counter(cual)
            anual.append({"punto": p, "criterio": crit, "enfermedad": "cualquiera_de_las_3", "dias": len(dias),
                          "dias_bajo": c["bajo"], "dias_medio": c["medio"], "dias_alto": c["alto"],
                          "episodios_alto": episodios(cual),
                          "horas_mojadas_anio": sum(1 for h in horas if r.hora_mojada(h, cfg))})
    return mensual, anual, diarios


def reproducibilidad(anual):
    """Compara con riesgo/salidas/resumen_dias_por_clase_2025.csv (corrido por el equipo de riesgo desde
    clima/derivados). Deben coincidir: misma serie Open-Meteo best_match."""
    ruta = os.path.join(RAIZ, "riesgo", "salidas", "resumen_dias_por_clase_2025.csv")
    ref = {}
    if os.path.exists(ruta):
        for f in csv.DictReader(open(ruta, encoding="utf-8")):
            ref[(f["punto"], f["criterio_mojadura"], f["enfermedad"])] = f
    out = []
    for a in anual:
        if a["enfermedad"] not in ENF:
            continue
        k = (a["punto"], a["criterio"] + "_P05", a["enfermedad"])
        f = ref.get(k)
        fila = {"punto": a["punto"], "criterio": a["criterio"], "enfermedad": a["enfermedad"],
                "backtest_medio": a["dias_medio"], "backtest_alto": a["dias_alto"],
                "riesgo_salidas_medio": f["dias_medio"] if f else None,
                "riesgo_salidas_alto": f["dias_alto"] if f else None}
        fila["coincide"] = bool(f) and int(f["dias_medio"]) == a["dias_medio"] and int(f["dias_alto"]) == a["dias_alto"]
        out.append(fila)
    return out


def parte_sensibilidad(anual):
    idx = {(a["punto"], a["criterio"], a["enfermedad"]): a for a in anual}
    out = []
    for p in PUNTOS:
        for enf in ENF:
            fila = {"punto": p, "enfermedad": enf}
            for crit in CRITERIOS:
                a = idx[(p, crit, enf)]
                fila["dias_alto_" + crit] = a["dias_alto"]
                fila["dias_medio_o_alto_" + crit] = a["dias_medio"] + a["dias_alto"]
                fila["episodios_alto_" + crit] = a["episodios_alto"]
                fila["horas_mojadas_" + crit] = a["horas_mojadas_anio"]
            base = fila["dias_alto_HR90"]
            for crit in ("HR85", "HR95"):
                fila["cambio_alto_%s_vs_HR90_dias" % crit] = fila["dias_alto_" + crit] - base
                fila["cambio_alto_%s_vs_HR90_pct" % crit] = (
                    round(100.0 * (fila["dias_alto_" + crit] - base) / base, 0) if base else None)
            out.append(fila)
    return out


# =====================================================================================
# 3. Fenologia
# =====================================================================================
def parte_fenologia(horas_pt):
    """reportes/ciencia-enfermedades.md (seccion 0.8 y 8): produccion continua con picos por poda; floracion
    sin temporada fija; en una finca coexisten flor, fruto verde y fruto maduro. No hay calendario de
    floracion verificado (dias floracion->cosecha de Biloxi: NO VERIFICADO), asi que NO se aplica un
    calendario. Escenarios:
      produccion_continua (SUPUESTO derivado del estudio local): cada dia la finca tiene todas las etapas;
        el riesgo de finca es el maximo sobre etapas -> multiplicador efectivo = max(FENOLOGIA[enf]).
      etapa_unica_<etapa> (SUPUESTO, sensibilidad): una cama/bloque en una sola etapa todo el anio.
    Los multiplicadores son los de risk.FENOLOGIA (todos SUPUESTO)."""
    cfg = CRITERIOS[CENTRAL]
    out = []
    for p, horas in horas_pt.items():
        por_etapa = {e: r.resumen_diario(horas, cfg, etapa=e) for e in r.ETAPAS}
        sin = r.resumen_diario(horas, cfg)
        for enf in ENF:
            c0 = Counter(d["clase_" + enf] for d in sin)
            out.append({"punto": p, "escenario": "sin_fenologia (m=1)", "enfermedad": enf, "multiplicador": 1.0,
                        "dias_medio": c0["medio"], "dias_alto": c0["alto"], "etiqueta": "referencia"})
            # continua: maximo diario sobre etapas coexistentes
            clases = []
            for i in range(len(sin)):
                mx = max(por_etapa[e][i]["idx_" + enf] for e in r.ETAPAS)
                clases.append(r.clasificar(mx, enf))
            c = Counter(clases)
            out.append({"punto": p, "escenario": "produccion_continua", "enfermedad": enf,
                        "multiplicador": max(r.FENOLOGIA[enf].values()), "dias_medio": c["medio"],
                        "dias_alto": c["alto"], "etiqueta": "SUPUESTO (todas las etapas coexisten)"})
            for e in r.ETAPAS:
                c = Counter(d["clase_" + enf] for d in por_etapa[e])
                out.append({"punto": p, "escenario": "etapa_unica_" + e, "enfermedad": enf,
                            "multiplicador": r.FENOLOGIA[enf][e], "dias_medio": c["medio"], "dias_alto": c["alto"],
                            "etiqueta": "SUPUESTO (sensibilidad por cama)"})
    return out


# =====================================================================================
# 4. Riesgo de HOY (pronostico en cache)
# =====================================================================================
ACCION = {  # texto operativo; la recomendacion de posponer aspersion viene de reportes/ciencia-enfermedades.md
    "alto": "Priorizar estas camas en el proximo recorrido del robot (24 h) y posponer el aspersor si es posible.",
    "medio": "Incluir en la ronda normal y vigilar el pronostico.",
    "bajo": "Ronda normal.",
}


def ultimo_pronostico(punto):
    import glob
    rutas = sorted(glob.glob(os.path.join(CACHE, "pronostico_%s_*.csv" % punto)))
    return rutas[-1] if rutas else None


def parte_hoy():
    res = {
        "fecha": HOY.isoformat(),
        "niveles": ["bajo", "medio", "alto"],
        "generado": datetime.now().isoformat(timespec="seconds"),
        "ventana": "72 h: ayer, hoy y manana (maximo diario, como el mapa de NC State IPM)",
        "criterio_mojadura": "central: HR >= 90 % o lluvia >= 0,5 mm/h; alerta: HR >= 85 % o lluvia >= 0,5 mm/h",
        "fuente_clima": "Open-Meteo, pronostico horario en clima/cache (incluye 2 dias pasados del modelo, no observados)",
        "atribucion": "Weather data by Open-Meteo.com (CC BY 4.0)",
        "enfermedades": list(ENF),
        "nota_oidio": "El oidio lo cubre el clasificador visual; el indice ambiental de vid da 0 dias en 2025.",
        "advertencia": ("Indice de riesgo ambiental, no diagnostico. Modelos de fresa/genericos adaptados; "
                        "sin validacion con incidencia de campo en Colombia."),
        "puntos": [],
    }
    for p in PUNTOS:
        ruta = ultimo_pronostico(p)
        if not ruta:
            res["puntos"].append({"punto": p, "error": "sin pronostico en cache"})
            continue
        horas = r.horas_desde_csv(ruta)
        dias = {k: r.resumen_diario(horas, CRITERIOS[k]) for k in ("HR90", "HR85")}
        v = {k: r.riesgo_ventana_72h(dias[k], HOY) for k in dias}
        enfs = {}
        peor = "bajo"
        for enf in ENF:
            e90, e85 = v["HR90"]["enfermedades"][enf], v["HR85"]["enfermedades"][enf]
            pico = [d for d in dias["HR90"] if d["fecha"].isoformat() == e90["dia_pico"]][0]
            enfs[enf] = {"clase": e90["clase"], "indice": round(e90["indice"], 2), "dia_pico": e90["dia_pico"],
                         "pico_en_dia_pasado": e90["dia_pico"] < HOY.isoformat(),
                         "horas_mojadura_pico": pico.get(enf + "_lwd_h"), "t_media_mojadura_pico_C": pico.get(enf + "_t_media"),
                         "clase_criterio_alerta_HR85": e85["clase"], "indice_criterio_alerta_HR85": round(e85["indice"], 2),
                         "umbrales_medio_alto": e90["umbrales_medio_alto"], "modelo": e90["modelo"]}
            if r.CLASES.index(e90["clase"]) > r.CLASES.index(peor):
                peor = e90["clase"]
        peor85 = max((v["HR85"]["enfermedades"][e]["clase"] for e in ENF), key=r.CLASES.index)
        proximos = []
        for d in dias["HR90"]:
            if HOY <= d["fecha"] <= HOY + timedelta(days=6):
                proximos.append({"fecha": d["fecha"].isoformat(), "horas_mojadas": d["horas_mojadas_dia"],
                                 **{enf: d["clase_" + enf] for enf in ENF}})
        # [verificacion-riesgo-clima, 2a pasada, 2026-10-23] Antes el titular se elegia por indice/umbral_alto y
        # la roya (APROXIMACION GIM con Tmin = 8 C SUPUESTO; regla del equipo 19-25 C) salia como "Roya ALTO" a 14 C
        # en Sotaquira aunque Botrytis (Bulger, publicado) tambien estaba en alto. Ahora, a igual clase, la roya
        # nunca encabeza el mensaje; sigue en "enfermedades" con su clase e indice.
        principal = max(ENF, key=lambda e: (r.CLASES.index(enfs[e]["clase"]), e != "roya",
                                            enfs[e]["indice"] / r.UMBRALES[e][1]))
        ep = enfs[principal]
        if not ep["horas_mojadura_pico"]:
            mensaje = "Sin periodos de mojadura relevantes en 72 h"
        elif ep["clase"] == "bajo":
            mensaje = "Riesgo bajo: maximo %s %.2f (%s h de mojadura a %.1f C)" % (
                principal, ep["indice"], ep["horas_mojadura_pico"], ep["t_media_mojadura_pico_C"])
        else:
            mensaje = "%s %s: %s h de mojadura a %.1f C (indice %.2f)" % (
                principal.capitalize(), ep["clase"].upper(), ep["horas_mojadura_pico"], ep["t_media_mojadura_pico_C"],
                ep["indice"])
        # Politica del equipo: preferimos falsas alarmas a casos no detectados -> el nivel que muestra el tablero
        # es el mayor entre el criterio central (HR90) y el de alerta (HR85).
        nivel = max(peor, peor85, key=r.CLASES.index)
        if r.CLASES.index(peor85) > r.CLASES.index(peor):
            p85 = max(ENF, key=lambda e: (r.CLASES.index(enfs[e]["clase_criterio_alerta_HR85"]), e != "roya",
                                          enfs[e]["indice_criterio_alerta_HR85"] / r.UMBRALES[e][1]))
            mensaje = ("Criterio central %s; con el criterio de alerta (HR >= 85 %%) %s %s (indice %.2f)" % (
                peor.upper(), p85, enfs[p85]["clase_criterio_alerta_HR85"].upper(),
                enfs[p85]["indice_criterio_alerta_HR85"]))
        res["puntos"].append({
            "punto": p, "nombre": META[p]["nombre"], "ha_eva_2025": META[p]["ha_eva_2025"], "rol": META[p]["rol"],
            "nivel_alerta": nivel, "nivel_alerta_regla": "max(criterio central HR90, criterio alerta HR85)",
            "riesgo_global": peor, "riesgo_global_criterio_alerta_HR85": peor85,
            "enfermedad_principal": principal, "mensaje": mensaje, "accion_sugerida": ACCION[nivel],
            "enfermedades": enfs, "proximos_7_dias": proximos,
            "fuente_clima": os.path.relpath(ruta, RAIZ),
        })
    ruta = os.path.join(SAL, "riesgo_hoy.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


# =====================================================================================
# 5. Prueba de cordura
# =====================================================================================
def _serie(inicio, n_horas, fn):
    """fn(i, t) -> (T, HR, lluvia)."""
    out = []
    for i in range(n_horas):
        t = inicio + timedelta(hours=i)
        T, HR, ll = fn(i, t)
        out.append(r.Hora(t, T, HR, ll))
    return out


def _diurno(t, media, amp):
    # minimo a las 6 h, maximo a las 14 h aprox. (forma simple)
    return media + amp * math.sin(2 * math.pi * (t.hour - 8) / 24.0)


def casos_sinteticos():
    """Casos construidos (no datos reales). Expectativas definidas ANTES de correr (criterio del equipo)."""
    t0 = datetime(2025, 7, 1, 0, 0)
    casos = []

    def seco(i, t):
        T = _diurno(t, 13, 6)                     # 7-19 C
        HR = 65 - 15 * math.sin(2 * math.pi * (t.hour - 8) / 24.0)   # 50-80 %
        return T, HR, 0.0

    def rocio(i, t):
        T, HR, _ = seco(i, t)
        if t.hour in (0, 1, 2, 3, 4, 5):          # 6 h de rocio por noche
            return 9.0, 92.0, 0.0
        return T, HR, 0.0

    def chubasco(i, t):
        T, HR, _ = seco(i, t)
        if i in (50, 51, 52):
            return 15.0, 95.0, 2.0
        return T, HR, 0.0

    def semana_lluviosa(i, t):
        T = _diurno(t, 15, 2)                     # 13-17 C
        return T, 97.0, (1.5 if 8 <= t.hour <= 17 else 0.0)

    def aguacero_y_secado(i, t):
        if i < 24:
            return _diurno(t, 15, 2), 97.0, (2.0 if 6 <= t.hour <= 17 else 0.0)
        return seco(i, t)

    def semana_fria(i, t):
        T = _diurno(t, 8, 1)                      # 7-9 C (tipo Tausa)
        return T, 98.0, (1.0 if 10 <= t.hour <= 15 else 0.0)

    defin = [
        ("seco_14d", "14 d sin lluvia, HR 50-80 %, T 7-19 C", 14 * 24, seco, "bajo_todos"),
        ("seco_con_rocio_6h", "14 d secos con 6 h/noche de HR 92 % a 9 C", 14 * 24, rocio, "bajo_todos"),
        ("chubasco_3h", "1 chubasco de 3 h (2 mm/h, 15 C) en 7 d secos", 7 * 24, chubasco, "bajo_todos"),
        ("semana_lluviosa_15C", "7 d con HR 97 % y 10 h/d de lluvia 1,5 mm/h, T 13-17 C", 7 * 24, semana_lluviosa,
         "alto_todos"),
        ("aguacero_y_secado", "1 d de lluvia (15 C) y luego 6 d secos", 7 * 24, aguacero_y_secado,
         "alto_dia1_y_bajo_desde_dia3"),
        ("semana_lluviosa_fria_8C", "7 d mojados a 7-9 C (tipo Tausa)", 7 * 24, semana_fria, "informativo"),
    ]
    for nombre, desc, n, fn, esperado in defin:
        horas = _serie(t0, n, fn)
        for crit, cfg in CRITERIOS.items():
            dias = r.resumen_diario(horas, cfg)
            fila = {"caso": nombre, "descripcion": desc, "criterio": crit, "esperado": esperado}
            for enf in ENF:
                cl = [d["clase_" + enf] for d in dias]
                fila["dias_alto_" + enf] = cl.count("alto")
                fila["dias_medio_" + enf] = cl.count("medio")
                fila["idx_max_" + enf] = round(max(d["idx_" + enf] for d in dias), 3)
                fila["clases_" + enf] = "".join(c[0].upper() for c in cl)   # B/M/A por dia
            if esperado == "bajo_todos":
                ok = all(fila["dias_alto_" + e] == 0 and fila["dias_medio_" + e] == 0 for e in ENF)
            elif esperado == "alto_todos":
                ok = all(fila["dias_alto_" + e] >= 1 for e in ENF)
            elif esperado == "alto_dia1_y_bajo_desde_dia3":
                ok = all(fila["clases_" + e][0] == "A" and set(fila["clases_" + e][2:]) == {"B"}
                         for e in ("botrytis", "antracnosis")) and set(fila["clases_roya"][2:]) == {"B"}
            else:
                ok = None
            fila["resultado"] = "PASA" if ok else ("FALLA" if ok is False else "INFORMATIVO")
            casos.append(fila)
    return casos


def semanas_completas(diarios_df):
    d = diarios_df.copy()
    d["semana"] = d["fecha"].dt.to_period("W-SUN")
    g = d.groupby("semana")
    ok = g.size() == 7
    return d[d["semana"].isin(ok[ok].index)]


def cargar_ideam(var, codigo, offset_h):
    """Misma lectura que clima/scripts/analisis_clima.py (cargar_ideam). Archivos de raw/ tratados como DATOS."""
    f = os.path.join(RAW_IDEAM, "%s_%s_2025.json" % (var, codigo))
    if not os.path.exists(f):
        return None
    d = pd.DataFrame(json.load(open(f, encoding="utf-8")))
    if d.empty:
        return None
    d["t"] = pd.to_datetime(d["fechaobservacion"]) + pd.Timedelta(hours=offset_h)
    d["v"] = pd.to_numeric(d["valorobservado"], errors="coerce")
    d = d.drop_duplicates(subset=["t", "v"]).set_index("t").sort_index()
    if var == "precipitacion":
        s = d["v"].groupby(level=0).mean()
        hh = s.resample("h").agg(["sum", "count"])
        return hh[hh["count"] > 0]["sum"]
    s = d["v"].groupby(level=0).mean().resample("h").mean().dropna()
    lo, hi = (-10, 35) if var == "temperatura" else (0, 100)
    return s[(s >= lo) & (s <= hi)]


def offsets_ideam():
    q = pd.read_csv(os.path.join(QC, "ideam_vs_openmeteo_2025.csv"), dtype={"estacion": str})
    q = q[q["variante_OM"] == "best_match"]
    return dict(zip(q["estacion"], q["offset_aplicado_h"].astype(int)))


def parte_cordura(horas_pt, diarios):
    casos = casos_sinteticos()
    semanal, resumen, temporada = [], [], []
    offs = offsets_ideam()
    lluvia_obs = {}
    for cod, p in EST_LLUVIA.items():
        P = cargar_ideam("precipitacion", cod, offs.get(cod, -5))
        if P is not None:
            lluvia_obs[p] = (cod, P)
    for p in PUNTOS:
      for crit in (CENTRAL, "HR85"):
        dd = pd.DataFrame(diarios[(p, crit)])
        dd["fecha"] = pd.to_datetime(dd["fecha"])
        hh = pd.DataFrame({"time": [h.time for h in horas_pt[p]], "lluvia": [h.lluvia for h in horas_pt[p]],
                           "HR": [h.HR for h in horas_pt[p]]}).set_index("time")
        dd = dd.set_index("fecha")
        dd["lluvia_om_mm"] = hh["lluvia"].resample("D").sum()
        dd["hr_media"] = hh["HR"].resample("D").mean()
        if p in lluvia_obs:
            cod, P = lluvia_obs[p]
            Pd = P.resample("D").agg(["sum", "count"])
            dd["lluvia_ideam_mm"] = Pd["sum"]
            dd["horas_ideam"] = Pd["count"]
        dd = dd.reset_index()
        for enf in ENF:
            dd["alto_" + enf] = (dd["clase_" + enf] == "alto").astype(int)
            dd["medio_o_alto_" + enf] = (dd["clase_" + enf] != "bajo").astype(int)
        dd["alto_cualquiera"] = dd[["alto_" + e for e in ENF]].max(axis=1)
        dd["medio_o_alto_cualquiera"] = dd[["medio_o_alto_" + e for e in ENF]].max(axis=1)
        if crit == CENTRAL:
            dd.to_csv(os.path.join(SAL, "diario_%s_HR90.csv" % p), index=False,
                      columns=["fecha", "lluvia_om_mm"] + (["lluvia_ideam_mm", "horas_ideam"] if p in lluvia_obs else [])
                      + ["hr_media", "horas_mojadas_dia"] + ["idx_" + e for e in ENF] + ["clase_" + e for e in ENF]
                      + ["roya_presion_14d"])
        sw = semanas_completas(dd)
        agg = {"lluvia_om_mm": "sum", "horas_mojadas_dia": "sum", "alto_cualquiera": "sum",
               "medio_o_alto_cualquiera": "sum", **{"alto_" + e: "sum" for e in ENF},
               **{"idx_" + e: "max" for e in ENF}}
        if p in lluvia_obs:
            agg.update({"lluvia_ideam_mm": "sum", "horas_ideam": "sum"})
        w = sw.groupby("semana").agg(agg).reset_index()
        w["punto"] = p
        w["criterio"] = crit
        w["inicio"] = w["semana"].apply(lambda s: s.start_time.date().isoformat())
        semanal.append(w)
        n10 = 10
        refs = [("lluvia_om_mm", w)]
        if p in lluvia_obs:
            refs.append(("lluvia_ideam_mm", w[w["horas_ideam"] >= 0.8 * 168]))   # cobertura >= 80 %
        for col, ww in refs:
            if len(ww) < 2 * n10:
                continue
            ws = ww.sort_values([col, "horas_mojadas_dia"])
            secas, lluv = ws.head(n10), ws.tail(n10)
            rho = ww[col].rank().corr(ww["alto_cualquiera"].rank())
            rho_b = ww[col].rank().corr(ww["idx_botrytis"].rank())
            fila = {"punto": p, "criterio": crit, "referencia_lluvia": col, "semanas_validas": len(ww),
                    "secas_lluvia_mm_max": round(secas[col].max(), 1),
                    "secas_pct_semanas_sin_dia_alto": round(100 * (secas["alto_cualquiera"] == 0).mean(), 0),
                    "secas_pct_dias_bajo_las_3": round(100 * (1 - secas["medio_o_alto_cualquiera"].sum() / (7 * n10)), 0),
                    "lluviosas_lluvia_mm_min": round(lluv[col].min(), 1),
                    "lluviosas_pct_semanas_con_dia_alto": round(100 * (lluv["alto_cualquiera"] > 0).mean(), 0),
                    "lluviosas_pct_semanas_con_dia_medio_o_alto": round(100 * (lluv["medio_o_alto_cualquiera"] > 0).mean(), 0),
                    "lluviosas_dias_alto_media": round(lluv["alto_cualquiera"].mean(), 1),
                    "secas_dias_alto_media": round(secas["alto_cualquiera"].mean(), 1),
                    "lluviosas_horas_mojadas_media": round(lluv["horas_mojadas_dia"].mean(), 0),
                    "secas_horas_mojadas_media": round(secas["horas_mojadas_dia"].mean(), 0),
                    "spearman_lluvia_vs_dias_alto": round(rho, 2),
                    "spearman_lluvia_vs_idx_botrytis_max": round(rho_b, 2)}
            for enf in ENF:
                fila["lluviosas_pct_con_alto_" + enf] = round(100 * (lluv["alto_" + enf] > 0).mean(), 0)
            fila["pasa_secas (>=90% sin alto)"] = fila["secas_pct_semanas_sin_dia_alto"] >= 90
            fila["pasa_lluviosas (>=80% con alto)"] = fila["lluviosas_pct_semanas_con_dia_alto"] >= 80
            fila["pasa_spearman (>0)"] = rho > 0
            resumen.append(fila)
        if crit != CENTRAL:
            continue
        dd["temporada"] = dd["fecha"].dt.month.map(TEMPORADA)
        for tmp, g in dd.groupby("temporada"):
            fila = {"punto": p, "temporada": tmp, "dias": len(g), "lluvia_om_mm": round(g["lluvia_om_mm"].sum(), 0)}
            if "lluvia_ideam_mm" in g:
                fila["lluvia_ideam_mm (horas con dato)"] = "%.0f (%d)" % (g["lluvia_ideam_mm"].sum(), g["horas_ideam"].sum())
            for enf in ENF:
                fila["dias_alto_" + enf] = int(g["alto_" + enf].sum())
                fila["dias_alto_por_30d_" + enf] = round(30 * g["alto_" + enf].mean(), 1)
            temporada.append(fila)
    semanal_df = pd.concat(semanal, ignore_index=True)
    semanal_df["semana"] = semanal_df["semana"].astype(str)
    semanal_df.to_csv(os.path.join(SAL, "cordura_semanal_2025.csv"), index=False)
    return casos, resumen, temporada


# =====================================================================================
# 6. Concordancia de entrada: riesgo con estacion IDEAM vs riesgo con Open-Meteo (mismo sitio, mismas horas)
# =====================================================================================
def parte_estaciones():
    """No es validacion contra enfermedad: mide cuanto del riesgo que 'veria' una estacion real
    detecta el sistema alimentado con Open-Meteo (casos no detectados y falsas alarmas por error de entrada)."""
    offs = offsets_ideam()
    filas, anual = [], []
    # referencia principal: HR_IDEAM >= 90 o lluvia_IDEAM > 0 (la misma del equipo de clima);
    # variante de robustez: HR_IDEAM >= 90 o lluvia_IDEAM >= 0,5 mm/h (misma regla que el sistema).
    REFS = {"est_HR90_P>0": r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=1e-6),
            "est_HR90_P>=0.5": r.ConfigMojadura(umbral_hr=90, umbral_lluvia_mm=0.5)}
    for (cod, p), (ref_nombre, ref_cfg) in ((a, b) for a in EST_RIESGO.items() for b in REFS.items()):
        off = offs.get(cod, -5)
        T, H, P = (cargar_ideam(v, cod, off) for v in ("temperatura", "humedad", "precipitacion"))
        om = pd.read_csv(os.path.join(CACHE, "historico_2025_est_%s.csv" % cod), parse_dates=["time"])
        om = om[om["modelo"] == "best_match"].set_index("time")
        base = pd.concat([T.rename("T"), H.rename("HR"), P.rename("P"), om["temperature_2m"].rename("T_om"),
                          om["relative_humidity_2m"].rename("HR_om"), om["precipitation"].rename("P_om")],
                         axis=1, join="inner").dropna()
        base = base[base.index.year == 2025]
        h_est = [r.Hora(t.to_pydatetime(), x["T"], x["HR"], x["P"]) for t, x in base.iterrows()]
        h_om = [r.Hora(t.to_pydatetime(), x.T_om, x.HR_om, x.P_om) for t, x in base.iterrows()]
        cnt = base.groupby(base.index.date).size()
        completos = set(cnt[cnt == 24].index)
        d_est = {d["fecha"]: d for d in r.resumen_diario(h_est, ref_cfg) if d["fecha"] in completos}
        for crit, cfg in CRITERIOS.items():
            d_om = {d["fecha"]: d for d in r.resumen_diario(h_om, cfg) if d["fecha"] in completos}
            fechas = sorted(set(d_est) & set(d_om))
            for enf in ENF:
                ce = {f: d_est[f]["clase_" + enf] for f in fechas}
                co = {f: d_om[f]["clase_" + enf] for f in fechas}
                for nivel_om in ("alto", "medio_o_alto"):
                    ok_om = (lambda c: c == "alto") if nivel_om == "alto" else (lambda c: c != "bajo")
                    vp = sum(1 for f in fechas if ce[f] == "alto" and ok_om(co[f]))
                    fn = sum(1 for f in fechas if ce[f] == "alto" and not ok_om(co[f]))
                    fp = sum(1 for f in fechas if ce[f] != "alto" and ok_om(co[f]))
                    vn = len(fechas) - vp - fn - fp
                    fp_bajo = sum(1 for f in fechas if ce[f] == "bajo" and ok_om(co[f]))
                    # tolerancia +-1 dia (la alerta del tablero usa ventana de 72 h)
                    vp72 = sum(1 for f in fechas if ce[f] == "alto" and any(
                        ok_om(co.get(f + timedelta(days=k), "bajo")) for k in (-1, 0, 1)))
                    filas.append({"estacion": cod, "punto": p, "referencia": ref_nombre, "criterio_om": crit, "enfermedad": enf,
                                  "alerta_om_si": nivel_om, "dias_completos": len(fechas),
                                  "dias_alto_estacion": vp + fn, "dias_alerta_om": vp + fp,
                                  "VP": vp, "FN_no_detectados": fn, "FP_falsas_alarmas": fp, "VN": vn,
                                  "VP_ventana_72h": vp72, "FP_con_estacion_en_bajo": fp_bajo,
                                  "sensibilidad": round(vp / (vp + fn), 2) if vp + fn else None,
                                  "sensibilidad_ventana_72h": round(vp72 / (vp + fn), 2) if vp + fn else None,
                                  "precision": round(vp / (vp + fp), 2) if vp + fp else None,
                                  "tasa_falsa_alarma_pct_dias_no_alto": round(100 * fp / (fp + vn), 1) if fp + vn else None})
        anual.append({"estacion": cod, "punto": p, "referencia": ref_nombre, "horas_pareadas": len(base), "dias_completos": len(completos),
                      "horas_mojadas_estacion": sum(1 for h in h_est if r.hora_mojada(h, ref_cfg)),
                      **{"horas_mojadas_om_" + c: sum(1 for h in h_om if r.hora_mojada(h, cfg)) for c, cfg in CRITERIOS.items()},
                      **{"dias_alto_estacion_" + e: sum(1 for d in d_est.values() if d["clase_" + e] == "alto") for e in ENF}})
    return filas, anual


def main():
    global HOY
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=None, help="YYYY-MM-DD para riesgo_hoy.json (por defecto, hoy)")
    a = ap.parse_args()
    HOY = datetime.strptime(a.fecha, "%Y-%m-%d").date() if a.fecha else date.today()
    horas_pt = {p: cargar_om(p) for p in PUNTOS}
    for p, h in horas_pt.items():
        print(p, len(h), "horas", h[0].time, "->", h[-1].time)
    mensual, anual, diarios = parte_mensual(horas_pt)
    print("->", escribir(mensual, "dias_riesgo_mensual_2025.csv"))
    print("->", escribir(anual, "dias_riesgo_anual_2025.csv"))
    rep = reproducibilidad(anual)
    print("->", escribir(rep, "reproducibilidad_vs_riesgo_salidas.csv"),
          "coinciden %d/%d" % (sum(x["coincide"] for x in rep), len(rep)))
    print("->", escribir(parte_sensibilidad(anual), "sensibilidad_umbral_hr.csv"))
    print("->", escribir(parte_fenologia(horas_pt), "fenologia_escenarios.csv"))
    hoy = parte_hoy()
    for x in hoy["puntos"]:
        print("hoy", x["punto"], x.get("nivel_alerta"), x.get("riesgo_global"), {e: v["clase"] for e, v in x.get("enfermedades", {}).items()})
    casos, resumen, temporada = parte_cordura(horas_pt, diarios)
    print("->", escribir(casos, "cordura_casos_sinteticos.csv"),
          Counter(c["resultado"] for c in casos))
    print("->", escribir(resumen, "cordura_semanas_secas_vs_lluviosas.csv"))
    print("->", escribir(temporada, "cordura_temporadas.csv"))
    filas, anual_est = parte_estaciones()
    print("->", escribir(filas, "concordancia_estacion_vs_openmeteo.csv"))
    print("->", escribir(anual_est, "concordancia_estacion_resumen.csv"))
    # agregado de las 3 estaciones y las 3 enfermedades (cuenta cada dia-enfermedad)
    df = pd.DataFrame(filas)
    g = df.groupby(["referencia", "criterio_om", "alerta_om_si"])[
        ["dias_alto_estacion", "VP", "VP_ventana_72h", "FN_no_detectados", "FP_falsas_alarmas", "FP_con_estacion_en_bajo",
         "VN"]].sum().reset_index()
    g["sensibilidad"] = (g["VP"] / g["dias_alto_estacion"]).round(2)
    g["sensibilidad_ventana_72h"] = (g["VP_ventana_72h"] / g["dias_alto_estacion"]).round(2)
    g["precision"] = (g["VP"] / (g["VP"] + g["FP_falsas_alarmas"])).round(2)
    g.to_csv(os.path.join(SAL, "concordancia_estacion_agregado.csv"), index=False)
    print(g.to_string())


if __name__ == "__main__":
    main()
