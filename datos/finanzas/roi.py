#!/usr/bin/env python3
"""ROI del sistema de detección temprana (Sabana Hack, reto "Berry Good Idea").

Lee parametros.yaml (mismo directorio) y escribe en el mismo directorio:
  importacion_factores.csv   costo puesto en finca por equipo vs. factor 1,35
  costo_ha_anio.csv          costo por ha y año por opción y tamaño de finca
  punto_equilibrio.csv       kg/ha y % de cosecha que hay que salvar para pagar
  roi_escenarios.csv         ROI pesimista / base / optimista
  tabla_final_20ha.csv       resumen para el reporte (finca de referencia)
  tornado_<op>_<area>ha.csv/.png   sensibilidad un-factor-a-la-vez
  derivados.csv              cifras derivadas (jornal, capacidad, umbral)

Modelo por ha y año:
  B = Y*P*L*f*mult_f + n*C_ap*mult_n + J*w*mult_J
  C = CAPEX/vida + OPEX     (y variante con factor de recuperación de capital)
  ROI = (B - C) / C

Ejecutar:  python3 -I roi.py      (o  ../.venv/bin/python -I roi.py)
"""
import csv
import math
import os
import site
import sys

try:  # con -I no se carga el site-packages de usuario; se añade explícitamente
    import yaml  # noqa: F401
    import matplotlib  # noqa: F401
except ImportError:
    sys.path.append(site.getusersitepackages())
import yaml
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(AQUI, "parametros.yaml"), encoding="utf-8") as fh:
    P = yaml.safe_load(fh)

ESCENARIOS = ("pes", "base", "opt")
NOMBRE_ESC = {"pes": "pesimista", "base": "base", "opt": "optimista"}


# ----------------------------------------------------------------------------
# Resolución de parámetros
# ----------------------------------------------------------------------------
def nodo(path):
    n = P
    for k in path.split("."):
        n = n[k]
    return n


def sel_escenario(esc):
    """Todos los parámetros en el escenario `esc` (salvo en_escenarios: false)."""
    def _s(path, nd):
        return "base" if nd.get("en_escenarios", True) is False else esc
    return _s


def sel_uno(paths, esc):
    """Solo los parámetros de `paths` en `esc`; el resto en base (tornado)."""
    paths = set(paths)

    def _s(path, nd):
        return esc if path in paths else "base"
    return _s


SEL_BASE = sel_escenario("base")


def v(path, sel=SEL_BASE):
    nd = nodo(path)
    if isinstance(nd, dict) and "base" in nd:
        return nd.get(sel(path, nd), nd["base"])
    return nd


def opv(op_id, clave, sel, defecto=None):
    """Parámetro de una opción (puede ser escalar o dict base/pes/opt)."""
    op = P["opciones"][op_id]
    if clave not in op:
        return defecto
    nd = op[clave]
    if isinstance(nd, dict) and "base" in nd:
        return v(f"opciones.{op_id}.{clave}", sel)
    return nd


# ----------------------------------------------------------------------------
# Bloques del modelo
# ----------------------------------------------------------------------------
def jornal_usd(sel=SEL_BASE):
    diario = v("macro.smmlv_2026_cop", sel) / 30.0
    return diario * (1 + v("macro.factor_prestacional_jornal", sel)) / v("macro.trm_cop_usd", sel)


def importacion(items, sel=SEL_BASE):
    """Costo puesto en finca de un embarque. items = [(clave_equipo, cantidad)]."""
    items = [(k, q) for k, q in items if q > 0]
    z = dict(fob=0, flete=0, seguro=0, cif=0, arancel=0, iva=0, iva_costo=0, fijos=0, total=0)
    if not items:
        return z
    fob = sum(v(f"equipos.{k}.fob_usd", sel) * q for k, q in items)
    peso = sum(P["equipos"][k]["peso_envio_kg"] * q for k, q in items)
    flete = peso * v("importacion.flete_usd_kg", sel) + v("importacion.flete_fijo_usd", sel)
    seguro = fob * v("importacion.seguro_frac_fob", sel)
    cif = fob + flete + seguro
    arancel = cif * v("importacion.arancel_frac", sel)
    iva = (cif + arancel) * v("importacion.iva_frac", sel)
    iva_costo = 0.0 if v("importacion.iva_recuperable", sel) else iva
    fijos = v("importacion.agencia_aduanas_usd", sel) + v("importacion.transporte_interno_usd", sel)
    total = cif + arancel + iva_costo + fijos
    return dict(fob=fob, flete=flete, seguro=seguro, cif=cif, arancel=arancel, iva=iva,
                iva_costo=iva_costo, fijos=fijos, total=total)


def capacidad_ha(op_id, sel=SEL_BASE):
    """Hectáreas que un robot revisa por ciclo de revisita."""
    op = P["opciones"][op_id]
    if "area_por_unidad_ha" in op:
        return float(op["area_por_unidad_ha"])
    if not op.get("robot") or "velocidad_m_s" not in op:
        return float("nan")
    vel = opv(op_id, "velocidad_m_s", sel)
    horas = opv(op_id, "horas_semana", sel)
    frac = op.get("fraccion_inspeccion", 1.0)
    m_por_ha = 10000.0 / v("operacion.entrecalle_m", sel) * v("operacion.overhead_recorrido", sel)
    horas_ciclo = horas * v("operacion.revisita_dias", sel) / 7.0
    return horas_ciclo * 3600.0 * vel / (m_por_ha * frac)


def crf(tasa, n):
    return tasa / (1 - (1 + tasa) ** (-n))


def costos(op_id, area, sel=SEL_BASE):
    op = P["opciones"][op_id]
    robot = op.get("robot")
    serv = op.get("servicio")
    vida = v("operacion.vida_util_anios", sel)
    factor_rc = crf(v("operacion.wacc", sel), vida)
    cap = capacidad_ha(op_id, sel)

    unidades = 0
    if robot and not serv:
        unidades = math.ceil(area / cap - 1e-9)
    items = [(robot, unidades)] if unidades else []
    nodos = gws = 0
    if op.get("red"):
        nodos = math.ceil(area * v("red_fija.nodos_por_ha", sel) - 1e-9)
        gws = math.ceil(area / v("red_fija.area_por_gateway_ha", sel) - 1e-9)
        items += [("nodo_sensor", nodos), ("gateway", gws)]
    imp = importacion(items, sel)

    capex = imp["total"] + nodos * v("red_fija.instalacion_usd_nodo", sel)
    if op.get("accesorios") and unidades:
        capex += unidades * v("equipos.accesorios_mastil_camara.costo_local_usd", sel)

    opex = v("operacion.nube_usd_anio_finca", sel)
    if unidades:
        if "mantenimiento_usd_anio_unidad" in op:
            opex += unidades * opv(op_id, "mantenimiento_usd_anio_unidad", sel)
        else:
            landed_robots = importacion([(robot, unidades)], sel)["total"]
            opex += op["mantenimiento_frac_capex"] * landed_robots
    opex += nodos * v("red_fija.opex_usd_nodo_anio", sel)

    fa = 0.0
    if op.get("falsas_alarmas"):
        fa = area * v("beneficio.falsas_alarmas_ha_anio", sel) * v("beneficio.costo_falsa_alarma_usd", sel)
    opex += fa

    tarifa = tarifa_crf = 0.0
    u_serv = 0
    if serv:  # el proveedor compra el robot y cobra por ha
        a_s = serv["area_servicio_ha"]
        u_serv = math.ceil(a_s / cap - 1e-9)
        capex_s = importacion([(robot, u_serv)], sel)["total"]
        fijo_s = (capex_s * op["mantenimiento_frac_capex"] + serv["operador_usd_anio"]["base"]
                  + serv["transporte_usd_anio"]["base"])
        margen = 1 + serv["margen_proveedor"]["base"]
        tarifa = (capex_s / vida + fijo_s) * margen / a_s
        tarifa_crf = (capex_s * factor_rc + fijo_s) * margen / a_s

    anual = capex / vida + opex + tarifa * area
    anual_crf = capex * factor_rc + opex + tarifa_crf * area
    return dict(unidades=unidades if not serv else u_serv, capacidad_ha=cap, nodos=nodos,
                capex=capex, opex=opex + tarifa * area, fa=fa, tarifa_servicio_ha=tarifa,
                anual=anual, anual_crf=anual_crf, costo_ha=anual / area,
                costo_ha_crf=anual_crf / area, capex_ha=capex / area,
                opex_ha=(opex + tarifa * area) / area)


def beneficio(op_id, sel=SEL_BASE):
    m = P["opciones"][op_id]["mult"]
    Y = v("cultivo.rendimiento_kg_ha", sel)
    Pr = v("cultivo.precio_usd_kg", sel)
    L = v("cultivo.perdida_base_frac", sel)
    f = v("beneficio.f_fraccion_evitada", sel)
    n = v("beneficio.n_aplicaciones_evitadas_ha_anio", sel)
    c_ap = v("beneficio.costo_aplicacion_usd_ha", sel)
    J = v("beneficio.jornales_ahorrados_ha_anio", sel)
    w = jornal_usd(sel)
    fruta = Y * Pr * L * min(1.0, f * m["f"])
    aplic = n * m["n"] * c_ap
    jorn = J * m["J"] * w
    return dict(Y=Y, P=Pr, f_eff=min(1.0, f * m["f"]), fruta=fruta, aplic=aplic,
                jornal=jorn, total=fruta + aplic + jorn)


def evaluar(op_id, area, sel=SEL_BASE):
    c = costos(op_id, area, sel)
    b = beneficio(op_id, sel)
    neto = b["total"] - c["costo_ha"]
    roi = neto / c["costo_ha"]
    caja = b["total"] - c["opex_ha"]
    payback = c["capex_ha"] / caja if caja > 0 else float("inf")
    no_fruta = b["aplic"] + b["jornal"]
    kg_eq = max(0.0, (c["costo_ha"] - no_fruta) / b["P"])
    return dict(c=c, b=b, neto=neto, roi=roi, payback=payback, kg_eq=kg_eq,
                pct_eq=100 * kg_eq / b["Y"],
                L_min=(100 * kg_eq / (b["Y"] * b["f_eff"]) if b["f_eff"] > 0 else float("inf")),
                kg_solo=c["costo_ha"] / b["P"], pct_solo=100 * c["costo_ha"] / b["P"] / b["Y"])


# ----------------------------------------------------------------------------
# Salidas
# ----------------------------------------------------------------------------
def r(x, d=2):
    if isinstance(x, float) and (math.isinf(x) or math.isnan(x)):
        return "inf" if math.isinf(x) else ""
    return round(x, d)


def escribir_csv(nombre, filas):
    ruta = os.path.join(AQUI, nombre)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    return ruta


OPS = list(P["opciones"].keys())
AREAS = P["operacion"]["areas_finca_ha"]
A_REF = P["operacion"]["area_referencia_ha"]
salidas = []

# 1) Factores de importación por equipo (1 unidad, escenario base)
filas = []
f_prev = v("importacion.factor_previo_equipo")
EMBARQUES = [(k, [(k, 1)]) for k, eq in P["equipos"].items() if "fob_usd" in eq]
EMBARQUES += [("red_20_nodos_1_gateway", [("nodo_sensor", 20), ("gateway", 1)]),
              ("D1_Ultra_mas_red_20ha", [("D1_Ultra", 1), ("nodo_sensor", 20), ("gateway", 1)])]
for k, items in EMBARQUES:
    b = importacion(items)
    sin_iva = importacion(items, sel_uno(["importacion.iva_recuperable"], "opt"))
    a0 = importacion(items, sel_uno(["importacion.arancel_frac"], "opt"))
    filas.append(dict(equipo=k, fob_usd=r(b["fob"]), flete_usd=r(b["flete"]), seguro_usd=r(b["seguro"]),
                      cif_usd=r(b["cif"]), arancel_usd=r(b["arancel"]), iva_usd=r(b["iva"]),
                      agencia_transporte_usd=r(b["fijos"]), total_finca_usd=r(b["total"]),
                      factor=r(b["total"] / b["fob"], 3),
                      factor_arancel_0=r(a0["total"] / a0["fob"], 3),
                      factor_iva_recuperable=r(sin_iva["total"] / sin_iva["fob"], 3),
                      diferencia_vs_factor_previo_usd=r(b["total"] - f_prev * b["fob"])))
salidas.append(escribir_csv("importacion_factores.csv", filas))

# 2) Costo por ha y año (base)
filas = []
for op in OPS:
    for a in AREAS:
        c = costos(op, a)
        filas.append(dict(opcion=op, nombre=P["opciones"][op]["nombre"], area_ha=a,
                          unidades_robot=c["unidades"], capacidad_ha_por_robot=r(c["capacidad_ha"], 1),
                          nodos=c["nodos"], capex_usd=r(c["capex"], 0), opex_usd_anio=r(c["opex"], 0),
                          costo_falsas_alarmas_usd_anio=r(c["fa"], 0),
                          costo_anual_usd=r(c["anual"], 0), costo_ha_anio_usd=r(c["costo_ha"], 1),
                          costo_ha_anio_crf_usd=r(c["costo_ha_crf"], 1)))
salidas.append(escribir_csv("costo_ha_anio.csv", filas))

# 3) Punto de equilibrio (base)
filas = []
for op in OPS:
    for a in AREAS:
        e = evaluar(op, a)
        filas.append(dict(opcion=op, area_ha=a, costo_ha_anio_usd=r(e["c"]["costo_ha"], 1),
                          beneficio_no_fruta_ha_usd=r(e["b"]["aplic"] + e["b"]["jornal"], 1),
                          kg_ha_equilibrio=r(e["kg_eq"], 1), pct_cosecha_equilibrio=r(e["pct_eq"], 3),
                          perdida_base_minima_pct=r(e["L_min"], 2),
                          kg_ha_equilibrio_solo_fruta=r(e["kg_solo"], 1),
                          pct_cosecha_solo_fruta=r(e["pct_solo"], 3)))
salidas.append(escribir_csv("punto_equilibrio.csv", filas))

# 4) ROI por escenario
filas = []
for op in OPS:
    for a in AREAS:
        for esc in ESCENARIOS:
            e = evaluar(op, a, sel_escenario(esc))
            filas.append(dict(opcion=op, area_ha=a, escenario=NOMBRE_ESC[esc],
                              unidades_robot=e["c"]["unidades"],
                              beneficio_ha_usd=r(e["b"]["total"], 1),
                              beneficio_fruta_ha_usd=r(e["b"]["fruta"], 1),
                              beneficio_aplicaciones_ha_usd=r(e["b"]["aplic"], 1),
                              beneficio_jornales_ha_usd=r(e["b"]["jornal"], 1),
                              costo_ha_usd=r(e["c"]["costo_ha"], 1), neto_ha_usd=r(e["neto"], 1),
                              roi=r(e["roi"], 3), payback_anios=r(e["payback"], 2)))
salidas.append(escribir_csv("roi_escenarios.csv", filas))

# 5) Tabla final (finca de referencia)
filas = []
for op in OPS:
    eb = evaluar(op, A_REF)
    fila = dict(opcion=op, nombre=P["opciones"][op]["nombre"], unidades_robot=eb["c"]["unidades"],
                capex_usd=r(eb["c"]["capex"], 0), costo_ha_anio_usd=r(eb["c"]["costo_ha"], 0),
                costo_ha_anio_crf_usd=r(eb["c"]["costo_ha_crf"], 0),
                beneficio_ha_base_usd=r(eb["b"]["total"], 0),
                kg_ha_equilibrio=r(eb["kg_eq"], 0), pct_cosecha_equilibrio=r(eb["pct_eq"], 2),
                kg_ha_solo_fruta=r(eb["kg_solo"], 0), pct_cosecha_solo_fruta=r(eb["pct_solo"], 2))
    for esc in ESCENARIOS:
        fila[f"roi_{NOMBRE_ESC[esc]}"] = r(evaluar(op, A_REF, sel_escenario(esc))["roi"], 2)
    fila["payback_base_anios"] = r(eb["payback"], 2)
    filas.append(fila)
# incremental híbrido vs red sola
eF, eB = evaluar("F", A_REF), evaluar("B", A_REF)
inc_c = eF["c"]["costo_ha"] - eB["c"]["costo_ha"]
inc_b = eF["b"]["total"] - eB["b"]["total"]
salidas.append(escribir_csv(f"tabla_final_{A_REF}ha.csv", filas))

# 6) Derivados
w_cop = v("macro.smmlv_2026_cop") / 30 * (1 + v("macro.factor_prestacional_jornal"))
Yb, Pb = v("cultivo.rendimiento_kg_ha"), v("cultivo.precio_usd_kg")
c_fa, c_fn = v("beneficio.costo_falsa_alarma_usd"), v("beneficio.costo_no_detectado_usd_ha_semana")
der = [
    dict(variable="smmlv_diario_cop", valor=r(v("macro.smmlv_2026_cop") / 30, 1), nota="Decreto 1469/2025 / 30"),
    dict(variable="jornal_cop", valor=r(w_cop, 0), nota="SMMLV diario x 1,30 (PL 504/2025)"),
    dict(variable="jornal_usd", valor=r(jornal_usd(), 2), nota="a TRM 2026-10-23"),
    dict(variable="ingreso_bruto_ha_anio_usd", valor=r(Yb * Pb, 0), nota="Y x P base"),
    dict(variable="costo_no_detectado_como_pct_ingreso_semanal", valor=r(100 * c_fn / (Yb * Pb), 2),
         nota="2.160 USD/ha/semana como % del ingreso anual"),
    dict(variable="umbral_bayes_prob_enfermedad", valor=r(c_fa / (c_fa + c_fn), 4),
         nota="alertar si P(enf) > C_FA/(C_FA+C_FN)"),
    dict(variable="incremental_F_vs_B_costo_ha", valor=r(inc_c, 1), nota="USD/ha/año, 20 ha"),
    dict(variable="incremental_F_vs_B_beneficio_ha", valor=r(inc_b, 1), nota="USD/ha/año, 20 ha"),
    dict(variable="roi_incremental_F_vs_B", valor=r((inc_b - inc_c) / inc_c, 3), nota="20 ha, base"),
]
for op in OPS:
    der.append(dict(variable=f"capacidad_ha_por_robot_{op}", valor=r(capacidad_ha(op), 1),
                    nota="revisita semanal, base"))
salidas.append(escribir_csv("derivados.csv", der))

# 7) Tornado
TORNADO = [
    ("Rendimiento Y (kg/ha)", ["cultivo.rendimiento_kg_ha"]),
    ("Precio P (USD/kg)", ["cultivo.precio_usd_kg"]),
    ("Pérdida base L", ["cultivo.perdida_base_frac"]),
    ("Fracción evitada f", ["beneficio.f_fraccion_evitada"]),
    ("Aplicaciones evitadas n", ["beneficio.n_aplicaciones_evitadas_ha_anio"]),
    ("Costo por aplicación (USD/ha)", ["beneficio.costo_aplicacion_usd_ha"]),
    ("Jornales ahorrados J", ["beneficio.jornales_ahorrados_ha_anio"]),
    ("Factor prestacional jornal", ["macro.factor_prestacional_jornal"]),
    ("TRM (COP/USD)", ["macro.trm_cop_usd"]),
    ("Falsas alarmas/ha/año", ["beneficio.falsas_alarmas_ha_anio"]),
    ("Costo por falsa alarma (USD)", ["beneficio.costo_falsa_alarma_usd"]),
    ("Precio robot (USD)", ["equipos.{robot}.fob_usd"]),
    ("Accesorios mástil/cámara (USD)", ["equipos.accesorios_mastil_camara.costo_local_usd"]),
    ("Mantenimiento robot (USD/año)", ["opciones.{op}.mantenimiento_usd_anio_unidad"]),
    ("Velocidad inspección (m/s)", ["opciones.{op}.velocidad_m_s"]),
    ("Entrecalle (m)", ["operacion.entrecalle_m"]),
    ("Vida útil (años)", ["operacion.vida_util_anios"]),
    ("OPEX por nodo (USD/año)", ["red_fija.opex_usd_nodo_anio"]),
    ("Precio nodo (USD)", ["equipos.nodo_sensor.fob_usd"]),
    ("Arancel (5 % / 0 %)", ["importacion.arancel_frac"]),
    ("IVA recuperable (no / sí)", ["importacion.iva_recuperable"]),
    ("Flete (USD/kg)", ["importacion.flete_usd_kg"]),
]

C_LOW, C_HIGH = "#eb6834", "#2a78d6"   # slot 2 (naranja) y slot 1 (azul) de la paleta de referencia
TXT1, TXT2, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"


def fmt_val(x):
    if isinstance(x, bool):
        return "sí" if x else "no"
    if isinstance(x, (int,)) or (isinstance(x, float) and x >= 100):
        return f"{x:,.0f}".replace(",", ".")
    return f"{x:g}".replace(".", ",")


def tornado(op_id, area, top=14):
    robot = P["opciones"][op_id].get("robot") or ""
    base = evaluar(op_id, area)["neto"]
    filas = []
    for etiqueta, paths in TORNADO:
        paths = [p.format(robot=robot, op=op_id) for p in paths]
        try:
            vals = {s: v(paths[0], sel_uno(paths, s)) for s in ("pes", "opt")}
        except KeyError:
            continue
        lo = evaluar(op_id, area, sel_uno(paths, "pes"))["neto"]
        hi = evaluar(op_id, area, sel_uno(paths, "opt"))["neto"]
        if abs(hi - lo) < 0.5:
            continue
        filas.append(dict(parametro=etiqueta, valor_pes=vals["pes"], valor_opt=vals["opt"],
                          neto_pes=lo, neto_opt=hi, rango=abs(hi - lo)))
    filas.sort(key=lambda d: d["rango"], reverse=True)
    escribir_csv(f"tornado_{op_id}_{area}ha.csv",
                 [dict(parametro=d["parametro"], valor_pesimista=d["valor_pes"],
                       valor_optimista=d["valor_opt"], neto_ha_pesimista=r(d["neto_pes"], 1),
                       neto_ha_optimista=r(d["neto_opt"], 1), neto_ha_base=r(base, 1),
                       rango=r(d["rango"], 1)) for d in filas])
    filas = filas[:top][::-1]

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, ax = plt.subplots(figsize=(9.5, 0.42 * len(filas) + 1.9), dpi=160)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    alto = 0.36
    for i, d in enumerate(filas):
        for val, col, dy in ((d["neto_pes"], C_LOW, alto / 2 + 0.02), (d["neto_opt"], C_HIGH, -alto / 2 - 0.02)):
            ax.barh(i + dy, val - base, left=base, height=alto, color=col, edgecolor=SURF, linewidth=1)
    etiquetas = [f'{d["parametro"]}  ({fmt_val(d["valor_pes"])} / {fmt_val(d["valor_opt"])})' for d in filas]
    ax.set_yticks(range(len(filas)))
    ax.set_yticklabels(etiquetas, color=TXT1)
    ax.axvline(base, color=TXT1, linewidth=1)
    xmin = min(min(d["neto_pes"], d["neto_opt"]) for d in filas)
    xmax = max(max(d["neto_pes"], d["neto_opt"]) for d in filas)
    if xmin < 0 < xmax:
        ax.axvline(0, color=TXT2, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(0, len(filas) - 0.35, " equilibrio (neto = 0)", color=TXT2, fontsize=8, va="bottom")
    ax.text(base, -0.95, f"base {base:,.0f}".replace(",", "."), color=TXT1, fontsize=8, ha="center", va="top")
    for d_i, d in enumerate(filas[-5:]):  # rótulos solo en los 5 de mayor impacto
        i = len(filas) - 5 + d_i
        for val, dy in ((d["neto_pes"], alto / 2 + 0.02), (d["neto_opt"], -alto / 2 - 0.02)):
            ax.text(val + (8 if val >= base else -8), i + dy, f"{val:,.0f}".replace(",", "."),
                    va="center", ha="left" if val >= base else "right", fontsize=7.5, color=TXT2)
    pad = 0.12 * (xmax - xmin)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(-1.2, len(filas) - 0.2)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors=TXT2)
    ax.set_xlabel("Beneficio neto (USD por ha y año) = B - C", color=TXT2)
    nombre = P["opciones"][op_id]["nombre"]
    ax.set_title(f"Sensibilidad del beneficio neto - {nombre}, finca de {area} ha",
                 loc="left", color=TXT1, fontsize=11, pad=22)
    ax.text(0, 1.02, "Un parámetro a la vez; el resto en valor base. Entre paréntesis: valor pesimista / optimista.",
            transform=ax.transAxes, color=TXT2, fontsize=8)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=C_LOW, label="parámetro en valor pesimista"),
                       Patch(color=C_HIGH, label="parámetro en valor optimista")],
              loc="lower right", frameon=False, fontsize=8, labelcolor=TXT1)
    fig.tight_layout()
    ruta = os.path.join(AQUI, f"tornado_{op_id}_{area}ha.png")
    fig.savefig(ruta, facecolor=SURF)
    plt.close(fig)
    return ruta


for op in ("F", "A"):
    salidas.append(tornado(op, A_REF))

# ----------------------------------------------------------------------------
print(f"Jornal: {w_cop:,.0f} COP = {jornal_usd():.2f} USD | TRM {v('macro.trm_cop_usd')}")
print(f"\nFinca de {A_REF} ha (base): costo/ha/año, equilibrio, ROI pes/base/opt")
for f in filas:
    print(f'  {f["opcion"]:>2} {f["nombre"]:<38} u={f["unidades_robot"]:<2} C/ha={f["costo_ha_anio_usd"]:>7} '
          f'B/ha={f["beneficio_ha_base_usd"]:>6} kg_eq={f["kg_ha_equilibrio"]:>6} ({f["pct_cosecha_equilibrio"]} %) '
          f'ROI={f["roi_pesimista"]}/{f["roi_base"]}/{f["roi_optimista"]}')
print(f"\nIncremental F vs B: +{inc_c:.0f} USD/ha costo, +{inc_b:.0f} USD/ha beneficio")
print("\nArchivos:")
for s in salidas:
    print("  " + s)
