#!/usr/bin/env python3
"""Economía unitaria del VENDEDOR de la solución "Berry Good Idea" (Sabana Hack 2026).

Qué calcula
  1. Cuántas hectáreas cubre un robot por semana (D1 Ultra dedicado, D1 Ultra en ruta,
     D1 MaxPro compartido), según la velocidad de inspección, la batería y la ventana de trabajo.
  2. CAPEX y costo anual de cada robot y de la red de sensores por finca.
  3. Valor por hectárea para el productor, precio máximo con el ROI objetivo y punto de equilibrio en kg/ha.
  4. Cinco modelos de negocio (venta de equipo, RaaS, SaaS + hardware, híbrido, MaxPro compartido)
     para 10, 50, 200 y 1.000 ha bajo contrato: flota, técnicos, ingresos, margen, CAPEX,
     payback del vendedor y ROI del productor.
  5. Ventana de precio por segmento, escala mínima rentable y sensibilidades.

Todos los parámetros están en unit_economics_parametros.yaml, cada uno con FUENTE o SUPUESTO.
Usa solo la biblioteca estándar. Si PyYAML está instalado lo usa; si no, usa un lector mínimo.

Uso:
  python3 -I unit_economics.py                 # imprime las tablas en markdown
  python3 -I unit_economics.py --fuentes       # además lista cada parámetro con su fuente
  python3 -I unit_economics.py --json salida.json
  python3 -I unit_economics.py --param otro.yaml
"""

import argparse
import copy
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
YAML_DEF = os.path.join(AQUI, "unit_economics_parametros.yaml")


# ---------------------------------------------------------------- lector YAML mínimo
def _quitar_comentario(linea):
    """Quita un comentario '#' que no esté dentro de comillas."""
    en_comillas = None
    for i, c in enumerate(linea):
        if c in ('"', "'"):
            if en_comillas is None:
                en_comillas = c
            elif en_comillas == c:
                en_comillas = None
        elif c == "#" and en_comillas is None and (i == 0 or linea[i - 1] in " \t"):
            return linea[:i]
    return linea


def _escalar(txt):
    t = txt.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ('"', "'"):
        return t[1:-1]
    if t.lower() in ("true", "yes"):
        return True
    if t.lower() in ("false", "no"):
        return False
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        return t


def leer_yaml_min(texto):
    """Lee el subconjunto de YAML que usa el archivo de parámetros: mapas anidados por
    sangría con valores escalares. No admite listas ni mapas en línea."""
    raiz = {}
    pila = [(-1, raiz)]
    for n, cruda in enumerate(texto.splitlines(), 1):
        linea = _quitar_comentario(cruda).rstrip()
        if not linea.strip():
            continue
        sangria = len(linea) - len(linea.lstrip(" "))
        clave, sep, valor = linea.strip().partition(":")
        if not sep:
            raise ValueError("línea %d sin ':' -> %r" % (n, cruda))
        while sangria <= pila[-1][0]:
            pila.pop()
        padre = pila[-1][1]
        if valor.strip() == "":
            nuevo = {}
            padre[clave.strip()] = nuevo
            pila.append((sangria, nuevo))
        else:
            padre[clave.strip()] = _escalar(valor)
    return raiz


def cargar_parametros(ruta):
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()
    try:
        import yaml  # noqa: WPS433 (opcional)
        return yaml.safe_load(texto), "PyYAML"
    except ImportError:
        return leer_yaml_min(texto), "lector mínimo incluido"


class Param:
    """Acceso por 'grupo.clave' al campo 'valor'. con() devuelve una copia con cambios."""

    def __init__(self, crudo):
        self.crudo = crudo

    def v(self, ruta):
        grupo, clave = ruta.split(".")
        return self.crudo[grupo][clave]["valor"]

    def con(self, cambios):
        nuevo = copy.deepcopy(self.crudo)
        for ruta, val in cambios.items():
            g, k = ruta.split(".")
            nuevo[g][k]["valor"] = val
        return Param(nuevo)

    def lista(self):
        for g, claves in self.crudo.items():
            for k, d in claves.items():
                yield g + "." + k, d["valor"], d.get("fuente", "")


# ---------------------------------------------------------------- formato
def fmt(x, dec=0):
    if x is None:
        return "-"
    if isinstance(x, str):
        return x
    if isinstance(x, float) and (math.isinf(x) or math.isnan(x)):
        return "n/a"
    s = "{:,.{d}f}".format(x, d=dec)
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(x, dec=0):
    return "-" if x is None else fmt(100.0 * x, dec) + " %"


def tabla(titulo, cab, filas, nota=None):
    out = ["", "### " + titulo, ""]
    out.append("| " + " | ".join(cab) + " |")
    out.append("|" + "|".join(["---"] * len(cab)) + "|")
    for f in filas:
        out.append("| " + " | ".join(str(c) for c in f) + " |")
    if nota:
        out.append("")
        out.append(nota)
    print("\n".join(out))


# ---------------------------------------------------------------- capacidad del robot
def horas_por_ha(p):
    """Horas de robot para recorrer todos los pasillos de 1 ha una vez."""
    m_pasillo = 10000.0 / p.v("geometria.distancia_entre_camas_m")
    return m_pasillo / p.v("inspeccion.velocidad_m_s") / 3600.0 * (1 + p.v("inspeccion.sobrecosto_giros_frac"))


def fraccion_trabajo_bateria(p, r):
    """Fracción de la ventana en que el robot camina (el resto es cambio o espera de batería)."""
    aut = p.v(r + ".autonomia_h")
    carga = p.v(r + ".carga_h")
    if not p.v(r + ".bateria_intercambiable"):
        return aut / (aut + carga)
    n_total = 1 + p.v(r + ".baterias_extra")
    espera = max(0.0, carga - (n_total - 1) * aut)  # si las de repuesto no alcanzan a cargarse
    return aut / (aut + p.v(r + ".cambio_bateria_h") + espera)


def horas_utiles_semana(p, r, modo):
    ventana = p.v(r + ".ventana_h_dia") - (p.v(r + ".traslado_ruta_h_dia") if modo == "ruta" else 0.0)
    return ventana * p.v(r + ".dias_semana") * fraccion_trabajo_bateria(p, r) * p.v(r + ".disponibilidad")


def ha_por_robot(p, r, modo):
    """Hectáreas que un robot mantiene inspeccionadas con la fracción de camas por semana."""
    return horas_utiles_semana(p, r, modo) / (horas_por_ha(p) * p.v("inspeccion.fraccion_camas_por_semana"))


def capex_robot(p, r):
    return (p.v(r + ".precio_usd") * (1 + p.v(r + ".importacion_frac")) + p.v(r + ".kit_percepcion_usd")
            + p.v(r + ".baterias_extra") * p.v(r + ".bateria_extra_usd") + p.v(r + ".cargador_y_estuche_usd"))


def baterias_ano(p, r):
    """Baterías que se reponen al año por robot, según horas de uso y ciclos de vida."""
    modo = "ruta" if r == "robot_maxpro" else "dedicado"
    ciclos = horas_utiles_semana(p, r, modo) * 52 / p.v(r + ".autonomia_h")
    return ciclos / p.v(r + ".ciclos_vida_bateria")


def costo_robot_ano(p, r):
    """(depreciación, caja) por robot al año. La caja incluye mantenimiento, seguro y reposición de baterías."""
    cap = capex_robot(p, r)
    dep = cap / p.v(r + ".vida_anos")
    caja = cap * (p.v(r + ".mantenimiento_frac_ano") + p.v(r + ".seguro_frac_ano")) \
        + baterias_ano(p, r) * p.v(r + ".bateria_extra_usd")
    return dep, caja


# ---------------------------------------------------------------- red de sensores por finca
def red_finca(p, tam_ha, pequena):
    nodos = max(p.v("red_sensores.nodos_min_finca"), math.ceil(tam_ha / p.v("red_sensores.ha_por_nodo") - 1e-9))
    comp = p.v("red_sensores.fincas_pequenas_por_gateway") if pequena else 1
    nodo_usd = (p.v("red_sensores.nodo_humectacion_usd") + p.v("red_sensores.nodo_temp_hr_usd")
                + p.v("red_sensores.instalacion_nodo_usd"))
    capex = nodos * nodo_usd + (p.v("red_sensores.gateway_usd") + p.v("red_sensores.estacion_referencia_usd")) / comp
    dep = capex / p.v("red_sensores.vida_anos")
    caja = capex * p.v("red_sensores.mantenimiento_frac_ano") + p.v("red_sensores.sim_usd_mes_por_gateway") * 12.0 / comp
    return {"nodos": nodos, "capex": capex, "dep": dep, "caja": caja}


# ---------------------------------------------------------------- personas
def costo_tecnico_ano(p):
    sal = p.v("operacion_vendedor.salario_tecnico_cop_mes") * p.v("general.factor_prestacional") * 12 / p.v("general.trm_cop_usd")
    return sal + p.v("operacion_vendedor.vehiculo_tecnico_usd_mes") * 12


def costo_operador_maxpro_ano(p):
    sal = p.v("operacion_vendedor.salario_tecnico_cop_mes") * p.v("general.factor_prestacional") * 12 / p.v("general.trm_cop_usd")
    return sal + p.v("robot_maxpro.vehiculo_usd_mes") * 12


def costo_agronomo_ano(p):
    return p.v("operacion_vendedor.salario_agronomo_cop_mes") * p.v("general.factor_prestacional") * 12 / p.v("general.trm_cop_usd")


def costo_hora_operario_finca(p):
    return (p.v("general.smmlv_2026_cop_mes") + p.v("general.auxilio_transporte_2026_cop_mes")) \
        * p.v("general.factor_prestacional") / p.v("productor.horas_laborales_mes") / p.v("general.trm_cop_usd")


def costo_operario_por_robot_ano(p, r):
    horas = p.v("productor.minutos_operario_dia_por_robot") / 60.0 * p.v(r + ".dias_semana") * 52
    return horas * costo_hora_operario_finca(p)


# ---------------------------------------------------------------- valor para el productor
def valor_productor_ha(p, con_robot):
    ingreso = p.v("productor.rendimiento_kg_ha") * p.v("productor.precio_usd_kg")
    if con_robot:
        perdida = p.v("productor.perdida_evitada_con_robot_frac")
        fung = p.v("productor.reduccion_fungicida_con_robot_frac")
        scout = p.v("productor.scouting_reemplazado_con_robot_frac")
    else:
        perdida = p.v("productor.perdida_evitada_solo_red_frac")
        fung = p.v("productor.reduccion_fungicida_solo_red_frac")
        scout = 0.0
    monitor_ha = (p.v("productor.salario_monitor_cop_mes") * p.v("general.factor_prestacional") * 12
                  / p.v("general.trm_cop_usd") / p.v("productor.ha_por_monitor"))
    partes = {
        "cosecha_salvada": ingreso * perdida,
        "fungicida_ahorrado": p.v("productor.gasto_fungicidas_usd_ha_ano") * fung,
        "scouting_ahorrado": monitor_ha * scout,
    }
    partes["total"] = sum(partes.values())
    return partes


# ---------------------------------------------------------------- un segmento con un plan
def _n_robots(x, enteros):
    return math.ceil(x - 1e-9) if enteros else x


def segmento(p, plan, ha, n_fincas, pequena, enteros=True):
    """Resultado anual de un segmento homogéneo (fincas del mismo tamaño) bajo un plan.
    Los técnicos y agrónomos salen fraccionarios; el agregado por escala los redondea.
    enteros=False reparte robots fraccionarios (flota bien usada) para ver sensibilidades sin saltos.
    El plan "saas_canal" es saas_hw vendido por un canal con kit autoinstalable."""
    if ha <= 0 or n_fincas <= 0:
        return None
    tam = ha / n_fincas
    red = red_finca(p, tam, pequena)
    contrato = p.v("operacion_vendedor.contrato_anos")
    if plan == "saas_canal":
        inst_cac = p.v("operacion_vendedor.instalacion_autoinstalable_usd") + p.v("operacion_vendedor.cac_canal_finca_usd")
        plan = "saas_hw"
    else:
        inst_cac = p.v("operacion_vendedor.instalacion_finca_usd") + p.v("operacion_vendedor.cac_finca_usd")
    margen_hw = p.v("precios.margen_hardware_frac")
    s = {"plan": plan, "ha": ha, "fincas": n_fincas, "tam": tam, "robots_ded": 0, "robots_ruta": 0,
         "robots_maxpro": 0, "robots_vendidos": 0, "tec_frac": 0.0, "oper_maxpro_frac": 0.0,
         "nodos": red["nodos"] * n_fincas,
         "comp": {"robot_dep": 0.0, "robot_mant_seguro": 0.0, "red_sensores": 0.0, "hw_vendido": 0.0,
                  "repuestos_soporte": 0.0, "instalacion_cac": 0.0}}
    comp = s["comp"]
    con_robot = plan in ("raas", "venta", "maxpro")
    s["valor_prod"] = valor_productor_ha(p, con_robot)["total"] * ha

    # --- red de sensores: la paga el vendedor (raas, maxpro) o se vende como kit (saas_hw, venta)
    red_capex = red["capex"] * n_fincas
    if plan in ("raas", "maxpro"):
        v_capex = red_capex
        v_dep = red["dep"] * n_fincas
        v_caja = red["caja"] * n_fincas
        ingreso_hw = 0.0
        costo_hw = 0.0
        prod_hw_ano = 0.0
        s["tec_frac"] += n_fincas / p.v("operacion_vendedor.fincas_por_tecnico_red")
        comp["red_sensores"] += v_dep + v_caja
    else:
        v_capex = 0.0
        v_dep = 0.0
        v_caja = 0.0
        ingreso_hw = red_capex * (1 + margen_hw) / p.v("red_sensores.vida_anos")   # anualizado
        costo_hw = red_capex / p.v("red_sensores.vida_anos")
        # el productor paga el kit y su mantenimiento
        prod_hw_ano = ingreso_hw + red_capex * (1 + margen_hw) * p.v("red_sensores.mantenimiento_frac_ano") \
            + p.v("red_sensores.sim_usd_mes_por_gateway") * 12.0 * n_fincas / (p.v("red_sensores.fincas_pequenas_por_gateway") if pequena else 1)
        s["tec_frac"] += n_fincas / (2 * p.v("operacion_vendedor.fincas_por_tecnico_red"))  # soporte remoto
        comp["hw_vendido"] += costo_hw

    v_capex += inst_cac * n_fincas
    v_amort_inst = inst_cac * n_fincas / contrato
    comp["instalacion_cac"] += v_amort_inst
    ingreso = 0.0
    prod_costo = prod_hw_ano

    if plan == "raas":
        r = "robot_ultra"
        if pequena:
            n_rob = _n_robots(ha / ha_por_robot(p, r, "ruta"), enteros)
            s["robots_ruta"] = n_rob
            s["tec_frac"] += n_rob / p.v("operacion_vendedor.robots_por_tecnico_ruta")
            precio = p.v("precios.raas_ruta_usd_ha_ano")
        else:
            n_rob = n_fincas * _n_robots(tam / ha_por_robot(p, r, "dedicado"), enteros)
            s["robots_ded"] = n_rob
            s["tec_frac"] += n_rob / p.v("operacion_vendedor.robots_por_tecnico_dedicado")
            precio = p.v("precios.raas_dedicado_usd_ha_ano")
        dep, caja = costo_robot_ano(p, r)
        v_capex += n_rob * capex_robot(p, r)
        v_dep += n_rob * dep
        v_caja += n_rob * caja
        comp["robot_dep"] += n_rob * dep
        comp["robot_mant_seguro"] += n_rob * caja
        ingreso += precio * ha
        prod_costo += precio * ha + n_rob * costo_operario_por_robot_ano(p, r)
    elif plan == "maxpro":
        r = "robot_maxpro"
        n_rob = _n_robots(ha / ha_por_robot(p, r, "ruta"), enteros)
        s["robots_maxpro"] = n_rob
        s["oper_maxpro_frac"] = n_rob / p.v("robot_maxpro.robots_por_operador")
        dep, caja = costo_robot_ano(p, r)
        v_capex += n_rob * capex_robot(p, r)
        v_dep += n_rob * dep
        v_caja += n_rob * caja
        comp["robot_dep"] += n_rob * dep
        comp["robot_mant_seguro"] += n_rob * caja
        precio = p.v("precios.maxpro_compartido_usd_ha_ano")
        ingreso += precio * ha
        prod_costo += precio * ha
    elif plan == "saas_hw":
        fee = max(p.v("precios.saas_usd_ha_ano") * tam, p.v("precios.saas_minimo_finca_usd_ano")) * n_fincas
        ingreso += fee + ingreso_hw
        v_caja += costo_hw
        prod_costo += fee
    elif plan == "venta":
        r = "robot_ultra"
        n_rob = n_fincas * _n_robots(tam / ha_por_robot(p, r, "dedicado"), enteros)
        s["robots_vendidos"] = n_rob
        cap = capex_robot(p, r)
        precio_kit = cap * (1 + margen_hw)
        vida = p.v(r + ".vida_anos")
        soporte = p.v("precios.soporte_venta_frac_hw_ano") * (precio_kit * n_rob + red_capex * (1 + margen_hw))
        licencia = p.v("precios.licencia_venta_usd_ha_ano") * ha
        ingreso += precio_kit * n_rob / vida + ingreso_hw + soporte + licencia
        # costo del vendedor: hardware vendido (anualizado), repuestos del contrato de soporte
        repuestos = cap * n_rob * p.v(r + ".mantenimiento_frac_ano") + red_capex * p.v("red_sensores.mantenimiento_frac_ano") \
            + n_rob * baterias_ano(p, r) * p.v(r + ".bateria_extra_usd")   # el soporte cubre baterías
        v_caja += cap * n_rob / vida + costo_hw + repuestos
        comp["hw_vendido"] += cap * n_rob / vida
        comp["repuestos_soporte"] += repuestos
        s["tec_frac"] += n_rob / p.v("operacion_vendedor.robots_por_tecnico_venta")
        # el productor paga robot anualizado + soporte + licencia + seguro + su operario
        prod_costo = (precio_kit * n_rob / vida + ingreso_hw + soporte + licencia
                      + cap * n_rob * p.v(r + ".seguro_frac_ano") + n_rob * costo_operario_por_robot_ano(p, r)
                      + p.v("red_sensores.sim_usd_mes_por_gateway") * 12.0 * n_fincas
                      / (p.v("red_sensores.fincas_pequenas_por_gateway") if pequena else 1))
    else:
        raise ValueError(plan)

    s.update({"ingreso": ingreso, "v_capex": v_capex, "v_dep": v_dep + v_amort_inst, "v_caja": v_caja,
              "prod_costo": prod_costo})
    return s


SEGMENTOS = (("pequena", "segmentos.tam_finca_pequena_ha", True),
             ("mediana", "segmentos.tam_finca_mediana_ha", False),
             ("grande", "segmentos.tam_finca_grande_ha", False))


def partir_escala(p, S):
    """Divide S ha en fincas pequeñas, medianas y grandes según el mix por escala.
    Devuelve [(segmento, ha, n_fincas, es_pequena), ...]."""
    pares = []
    for trozo in str(p.v("segmentos.mix_por_escala")).split(","):
        k, val = trozo.split(":")
        pares.append((float(k), [float(x) for x in val.split("/")]))
    pares.sort()
    fracs = pares[0][1]
    for k, val in pares:
        if S >= k:
            fracs = val
    out = []
    for (nombre, clave_tam, peq), fr in zip(SEGMENTOS, fracs):
        ha = S * fr / sum(fracs)
        n = math.ceil(ha / p.v(clave_tam) - 1e-9) if ha > 1e-9 else 0
        out.append((nombre, ha, n, peq))
    return out


# modelo -> (nombre, plan para fincas pequeñas, medianas, grandes)
PLANES = {
    "venta": ("Venta de equipo + licencia", ("venta", "venta", "venta")),
    "raas": ("RaaS por ha (robot en ruta / dedicado)", ("raas", "raas", "raas")),
    "saas_hw": ("SaaS por ha + kit de sensores", ("saas_hw", "saas_hw", "saas_hw")),
    "hibrido": ("Híbrido: pequeñas SaaS+kit por canal, medianas RaaS, grandes compra", ("saas_canal", "raas", "venta")),
    "maxpro": ("RaaS compartido con D1 MaxPro", ("maxpro", "maxpro", "maxpro")),
}


def evaluar_escala(p, S, clave):
    nombre, planes = PLANES[clave]
    partes = partir_escala(p, S)
    segs = [x for x in (segmento(p, pl, ha, n, peq) for pl, (_, ha, n, peq) in zip(planes, partes)) if x]
    tot = {k: sum(s[k] for s in segs) for k in ("ha", "fincas", "robots_ded", "robots_ruta", "robots_maxpro",
                                                  "robots_vendidos", "tec_frac", "oper_maxpro_frac", "nodos",
                                                  "ingreso", "v_capex", "v_dep", "v_caja", "prod_costo", "valor_prod")}
    ov = p.v
    # flota propia del vendedor: reserva de robots
    rob_propios = tot["robots_ded"] + tot["robots_ruta"]
    reserva = math.ceil(rob_propios * ov("operacion_vendedor.reserva_robots_frac")) if rob_propios >= ov("operacion_vendedor.reserva_desde_robots") else 0
    if reserva:
        dep, caja = costo_robot_ano(p, "robot_ultra")
        tot["v_capex"] += reserva * capex_robot(p, "robot_ultra")
        tot["v_dep"] += reserva * dep
        tot["v_caja"] += reserva * caja * 0.5  # en bodega se gasta la mitad
    res_mp = math.ceil(tot["robots_maxpro"] * ov("operacion_vendedor.reserva_robots_frac")) if tot["robots_maxpro"] >= ov("operacion_vendedor.reserva_desde_robots") else 0
    if res_mp:
        dep, caja = costo_robot_ano(p, "robot_maxpro")
        tot["v_capex"] += res_mp * capex_robot(p, "robot_maxpro")
        tot["v_dep"] += res_mp * dep
        tot["v_caja"] += res_mp * caja * 0.5
    tecnicos = max(1, math.ceil(tot["tec_frac"] - 1e-9))
    operadores = math.ceil(tot["oper_maxpro_frac"] - 1e-9)
    agro = max(ov("operacion_vendedor.agronomo_min_fte"), S / ov("operacion_vendedor.ha_por_agronomo"))
    personas = tecnicos * costo_tecnico_ano(p) + operadores * costo_operador_maxpro_ano(p) + agro * costo_agronomo_ano(p)
    nube = ov("operacion_vendedor.nube_fija_usd_mes") * 12 + ov("operacion_vendedor.nube_usd_ha_ano") * S
    caja_directa = tot["v_caja"] + personas + nube
    margen_bruto = tot["ingreso"] - caja_directa - tot["v_dep"]
    contrib_caja = tot["ingreso"] - caja_directa
    overhead = ov("operacion_vendedor.overhead_fijo_usd_mes") * 12
    ebit = margen_bruto - overhead
    payback = tot["v_capex"] / (contrib_caja / 12.0) if contrib_caja > 0 else float("inf")
    payback_oh = tot["v_capex"] / ((contrib_caja - overhead) / 12.0) if contrib_caja - overhead > 0 else float("inf")
    prod_ha = tot["prod_costo"] / S
    return {
        "escala_ha": S, "plan": clave, "nombre": nombre,
        "fincas": {nom: n for nom, _, n, _ in partes}, "fincas_total": sum(n for _, _, n, _ in partes),
        "robots_ultra": rob_propios + reserva, "robots_reserva": reserva + res_mp, "robots_maxpro": tot["robots_maxpro"] + res_mp,
        "robots_vendidos": tot["robots_vendidos"], "nodos": tot["nodos"],
        "tecnicos": tecnicos, "operadores_maxpro": operadores, "agronomos_fte": agro,
        "ingreso": tot["ingreso"], "costo_caja": caja_directa, "depreciacion": tot["v_dep"],
        "margen_bruto": margen_bruto, "margen_bruto_pct": margen_bruto / tot["ingreso"] if tot["ingreso"] else 0.0,
        "overhead": overhead, "ebit": ebit, "capex_vendedor": tot["v_capex"],
        "payback_meses": payback, "payback_con_overhead_meses": payback_oh,
        "costo_productor_ha": prod_ha, "valor_productor_ha": tot["valor_prod"] / S,
        "roi_productor": tot["valor_prod"] / tot["prod_costo"] if tot["prod_costo"] else 0.0,
        "equilibrio_kg_ha": prod_ha / ov("productor.precio_usd_kg"),
        "equilibrio_pct_cosecha": prod_ha / ov("productor.precio_usd_kg") / ov("productor.rendimiento_kg_ha"),
    }


# ---------------------------------------------------------------- costo unitario a escala (sin mínimos)
def costo_unitario(p, plan, tam, pequena, enteros=True):
    """Costo del vendedor por ha y año en régimen (técnicos y agrónomo fraccionarios, sin overhead fijo)."""
    n = 100  # 100 fincas iguales: evita el efecto de los mínimos
    s = segmento(p, plan, tam * n, n, pequena, enteros)
    personas = s["tec_frac"] * costo_tecnico_ano(p) + s["oper_maxpro_frac"] * costo_operador_maxpro_ano(p) \
        + (s["ha"] / p.v("operacion_vendedor.ha_por_agronomo")) * costo_agronomo_ano(p)
    nube = p.v("operacion_vendedor.nube_usd_ha_ano") * s["ha"]
    costo = s["v_caja"] + s["v_dep"] + personas + nube
    # en venta y saas_hw el costo de hardware ya va en v_caja; el ingreso incluye el hardware
    contrib_caja = s["ingreso"] - s["v_caja"] - personas - nube
    payback = s["v_capex"] / (contrib_caja / 12.0) if contrib_caja > 0 else float("inf")
    desg = dict(s["comp"])
    desg["tecnicos_operadores"] = s["tec_frac"] * costo_tecnico_ano(p) + s["oper_maxpro_frac"] * costo_operador_maxpro_ano(p)
    desg["agronomo"] = (s["ha"] / p.v("operacion_vendedor.ha_por_agronomo")) * costo_agronomo_ano(p)
    desg["nube"] = nube
    desg = {k: v / s["ha"] for k, v in desg.items()}
    return {"desglose_ha": desg, "costo_ha": costo / s["ha"], "ingreso_ha": s["ingreso"] / s["ha"], "prod_costo_ha": s["prod_costo"] / s["ha"],
            "valor_ha": s["valor_prod"] / s["ha"], "capex_finca": s["v_capex"] / n, "payback_meses": payback, "seg": s}


# ---------------------------------------------------------------- impresión
def imprimir(p, motor, fuentes):
    escalas = [int(x) for x in str(p.v("general.escalas_ha")).split(",")]
    print("# Economía unitaria del vendedor (salida de unit_economics.py)")
    print("")
    print("Parámetros: unit_economics_parametros.yaml (leído con %s). Moneda: USD/año salvo que se indique otra. "
          "TRM %s COP/USD. Los SUPUESTO están marcados en el YAML." % (motor, fmt(p.v("general.trm_cop_usd"), 2)))

    # 1. capacidad
    hha = horas_por_ha(p)
    filas = []
    for r, modo, etiqueta in (("robot_ultra", "dedicado", "D1 Ultra dedicado (finca >= 20 ha)"),
                              ("robot_ultra", "ruta", "D1 Ultra en ruta (fincas pequeñas)"),
                              ("robot_maxpro", "ruta", "D1 MaxPro compartido")):
        hs = horas_utiles_semana(p, r, modo)
        filas.append([etiqueta, fmt(hha, 2), fmt(fraccion_trabajo_bateria(p, r) * 100, 0) + " %", fmt(hs, 1),
                      fmt(hs / hha, 1), fmt(ha_por_robot(p, r, modo), 1)])
    tabla("1. Cuántas hectáreas cubre un robot por semana",
          ["Robot y modo", "h de robot por ha (1 pasada)", "% de la ventana caminando", "h útiles/semana",
           "ha/semana, 100 % de camas", "ha por robot con %s %% de camas por semana" % fmt(100 * p.v("inspeccion.fraccion_camas_por_semana"))],
          filas,
          "Pasillo por ha = 10.000 / %s m = %s m; velocidad %s m/s; +%s %% por giros y paradas. "
          "Con estos supuestos, los ~60 ha por MaxPro del contexto equivalen a inspeccionar el %s %% de las camas cada semana."
          % (fmt(p.v("geometria.distancia_entre_camas_m"), 1), fmt(10000 / p.v("geometria.distancia_entre_camas_m")),
             fmt(p.v("inspeccion.velocidad_m_s"), 1), fmt(100 * p.v("inspeccion.sobrecosto_giros_frac")),
             fmt(100 * horas_utiles_semana(p, "robot_maxpro", "ruta") / (hha * 60), 0)))

    # 2. capex robot
    filas = []
    for r, etiqueta, modo in (("robot_ultra", "D1 Ultra + mástil", "dedicado"), ("robot_maxpro", "D1 MaxPro + mástil", "ruta")):
        dep, caja = costo_robot_ano(p, r)
        hpr = ha_por_robot(p, r, modo)
        filas.append([etiqueta, fmt(p.v(r + ".precio_usd")), fmt(capex_robot(p, r)), fmt(p.v(r + ".vida_anos")),
                      fmt(dep), fmt(baterias_ano(p, r), 1), fmt(caja), fmt(dep + caja), fmt((dep + caja) / hpr)])
    tabla("2. CAPEX y costo anual de un robot",
          ["Robot", "Precio equipo", "CAPEX puesto en finca", "Vida (años)", "Depreciación/año", "Baterías repuestas/año",
           "Mant. + seguro + baterías/año", "Costo anual", "Costo por ha cubierta"], filas,
          "CAPEX = precio x (1 + importación) + kit de percepción + baterías extra + cargador/estuche. "
          "Baterías por año = horas de uso x 52 / autonomía / ciclos de vida.")

    # 3. red por finca
    filas = []
    for tam, peq, etiqueta in ((p.v("segmentos.tam_finca_pequena_ha"), True, "Finca pequeña (gateway y estación compartidos)"),
                               (p.v("segmentos.tam_finca_mediana_ha"), False, "Finca mediana")):
        red = red_finca(p, tam, peq)
        filas.append([etiqueta, fmt(tam), red["nodos"], fmt(red["capex"]), fmt(red["capex"] / tam),
                      fmt((red["dep"] + red["caja"]) / tam)])
    tabla("3. Red de sensores por finca", ["Finca", "ha", "Nodos", "CAPEX red", "CAPEX por ha", "Costo anual por ha"], filas)

    # 4. valor productor
    filas = []
    roi = p.v("productor.roi_objetivo")
    for con, etiqueta in ((True, "Con robot (red + robot)"), (False, "Solo red + SaaS")):
        v = valor_productor_ha(p, con)
        filas.append([etiqueta, fmt(v["cosecha_salvada"]), fmt(v["fungicida_ahorrado"]), fmt(v["scouting_ahorrado"]),
                      fmt(v["total"]), fmt(v["total"] / roi), fmt(v["total"] / p.v("productor.precio_usd_kg"))])
    tabla("4. Valor por ha para el productor y precio máximo que acepta",
          ["Paquete", "Cosecha salvada", "Fungicida ahorrado", "Scouting ahorrado", "Valor total/ha",
           "Precio máx./ha con ROI %sx" % fmt(roi, 1), "kg/ha que vale el paquete"], filas,
          "Supuestos: %s kg/ha a %s USD/kg; pérdida evitada %s (con robot) y %s (solo red). "
          "Precio máx. = valor / ROI objetivo. El punto de equilibrio del productor (ROI 1x) es el valor total."
          % (fmt(p.v("productor.rendimiento_kg_ha")), fmt(p.v("productor.precio_usd_kg"), 2),
             pct(p.v("productor.perdida_evitada_con_robot_frac"), 1), pct(p.v("productor.perdida_evitada_solo_red_frac"), 1)))

    # 5. ventana de precio por segmento
    mbo = p.v("operacion_vendedor.margen_bruto_objetivo")
    tp, tm, tg = (p.v("segmentos.tam_finca_pequena_ha"), p.v("segmentos.tam_finca_mediana_ha"), p.v("segmentos.tam_finca_grande_ha"))
    casos = (("raas", tp, True, "RaaS en ruta", "precios.raas_ruta_usd_ha_ano"),
             ("raas", tm, False, "RaaS dedicado", "precios.raas_dedicado_usd_ha_ano"),
             ("raas", tg, False, "RaaS dedicado", "precios.raas_dedicado_usd_ha_ano"),
             ("saas_hw", tp, True, "SaaS + kit", "precios.saas_usd_ha_ano"),
             ("saas_hw", tm, False, "SaaS + kit", "precios.saas_usd_ha_ano"),
             ("saas_canal", tp, True, "SaaS + kit por canal, autoinstalable", "precios.saas_usd_ha_ano"),
             ("venta", tp, True, "Venta + licencia", "precios.licencia_venta_usd_ha_ano"),
             ("venta", tm, False, "Venta + licencia", "precios.licencia_venta_usd_ha_ano"),
             ("venta", tg, False, "Venta + licencia", "precios.licencia_venta_usd_ha_ano"),
             ("maxpro", tm, False, "MaxPro compartido", "precios.maxpro_compartido_usd_ha_ano"))

    def fila_ventana(q, plan, tam, peq, etiqueta, precio_clave):
        cu = costo_unitario(q, plan, tam, peq)
        margen = (cu["ingreso_ha"] - cu["costo_ha"]) / cu["ingreso_ha"]
        roi_p = cu["valor_ha"] / cu["prod_costo_ha"]
        ok = "sí" if (margen >= mbo and roi_p >= roi) else ("parcial" if margen > 0 and roi_p >= 1 else "no")
        return [etiqueta + ", finca de %s ha" % fmt(tam), fmt(q.v(precio_clave)), fmt(cu["ingreso_ha"]), fmt(cu["costo_ha"]),
                pct(margen), fmt(cu["costo_ha"] / (1 - mbo)), fmt(cu["capex_finca"]), fmt(cu["payback_meses"], 0),
                fmt(cu["prod_costo_ha"]), fmt(roi_p, 1) + "x", fmt(cu["prod_costo_ha"] / q.v("productor.precio_usd_kg")), ok]

    cab5 = ["Segmento y plan", "Precio de lista/ha", "Ingreso vendedor/ha", "Costo vendedor/ha", "Margen bruto",
            "Ingreso mínimo/ha para margen %s" % pct(mbo), "CAPEX vendedor por finca", "Payback por finca (meses)",
            "Costo total productor/ha", "ROI productor", "Equilibrio productor kg/ha", "¿Margen y ROI %sx?" % fmt(roi, 0)]
    tabla("5. Ventana de precio por ha y año en régimen (muchas fincas iguales, sin overhead fijo)", cab5,
          [fila_ventana(p, *c) for c in casos],
          "El ingreso del vendedor en SaaS + kit y en Venta incluye el hardware anualizado (precio de lista + "
          "kit vendido / vida útil). El costo del productor suma el tiempo de su operario y, si compra, el hardware "
          "anualizado y su mantenimiento. Valor para el productor: %s USD/ha con robot y %s USD/ha solo con la red."
          % (fmt(valor_productor_ha(p, True)["total"]), fmt(valor_productor_ha(p, False)["total"])))

    # 5b. palancas para fincas pequeñas
    filas = []
    ov = "operacion_vendedor."
    sa = (("saas_hw", "SaaS + kit", "precios.saas_usd_ha_ano"),)
    ru = (("raas", "RaaS en ruta", "precios.raas_ruta_usd_ha_ano"),)
    canal = {ov + "cac_finca_usd": p.v(ov + "cac_canal_finca_usd")}
    auto = dict(canal, **{ov + "instalacion_finca_usd": p.v(ov + "instalacion_autoinstalable_usd")})
    palancas = (("Base", {}, sa + ru),
                ("Canal (asociación/exportadora): CAC %s" % fmt(p.v(ov + "cac_canal_finca_usd")), canal, sa + ru),
                ("Canal + kit autoinstalable", auto, sa),
                ("Canal + autoinstalable + SaaS a 160", dict(auto, **{"precios.saas_usd_ha_ano": 160}), sa),
                ("Canal + robot en ruta a 680", dict(canal, **{"precios.raas_ruta_usd_ha_ano": 680}), ru),
                ("Canal + 1 técnico por 10 robots en ruta", dict(canal, **{ov + "robots_por_tecnico_ruta": 10}), ru))
    for etiqueta, cambios, planes in palancas:
        q = p.con(cambios)
        for plan, nombre, pc in planes:
            f = fila_ventana(q, plan, tp, True, nombre, pc)
            filas.append([etiqueta] + f)
    tabla("5b. Palancas para la finca pequeña (%s ha), el segmento más caro de atender" % fmt(tp),
          ["Palanca"] + cab5, filas)

    # 5c. desglose del costo
    nombres = (("robot_dep", "Depreciación del robot"), ("robot_mant_seguro", "Mantenimiento y seguro del robot"),
               ("red_sensores", "Red de sensores (dep. + mant. + SIM)"), ("hw_vendido", "Hardware vendido (costo anualizado)"),
               ("repuestos_soporte", "Repuestos del contrato de soporte"), ("tecnicos_operadores", "Técnicos u operadores"),
               ("agronomo", "Agrónomo remoto"), ("nube", "Nube variable"), ("instalacion_cac", "Instalación + CAC (amortizados)"))
    casos_d = (("raas", tm, False, "RaaS dedicado %s ha" % fmt(tm)), ("raas", tp, True, "RaaS ruta %s ha" % fmt(tp)),
               ("saas_canal", tp, True, "SaaS canal %s ha" % fmt(tp)), ("venta", tg, False, "Venta %s ha" % fmt(tg)),
               ("maxpro", tm, False, "MaxPro %s ha" % fmt(tm)))
    des = [costo_unitario(p, c[0], c[1], c[2])["desglose_ha"] for c in casos_d]
    filas = [[etq] + [fmt(d[k]) for d in des] for k, etq in nombres]
    filas.append(["Total"] + [fmt(sum(d.values())) for d in des])
    tabla("5c. Desglose del costo del vendedor (USD por ha y año, en régimen)", ["Rubro"] + [c[3] for c in casos_d], filas)

    # 5d. (añadida por la verificación de negocio, 2026-10-23) margen del RaaS dedicado según el tamaño de la finca.
    # Con robots enteros el margen sube y baja en "dientes de sierra": cada robot nuevo entra casi vacío.
    filas = []
    q25 = p.con({"geometria.distancia_entre_camas_m": 2.5})
    pr = p.v("precios.raas_dedicado_usd_ha_ano")
    for tam in (15, 20, 25, 30, 35, 40, 50, 60, 70, 100, 120):
        c = costo_unitario(p, "raas", tam, False)
        c25 = costo_unitario(q25, "raas", tam, False)
        filas.append([fmt(tam), "%d" % round(c["seg"]["robots_ded"] / c["seg"]["fincas"]), fmt(c["costo_ha"]),
                      pct((pr - c["costo_ha"]) / pr), "%d" % round(c25["seg"]["robots_ded"] / c25["seg"]["fincas"]),
                      pct((pr - c25["costo_ha"]) / pr)])
    tabla("5d. Margen del RaaS dedicado a %s USD/ha según el tamaño de la finca (robots enteros, en régimen)" % fmt(pr),
          ["Finca (ha)", "Robots (camas a %s m)" % fmt(p.v("geometria.distancia_entre_camas_m"), 1), "Costo vendedor/ha",
           "Margen", "Robots (camas a 2,5 m)", "Margen (camas a 2,5 m)"], filas,
          "Una finca de 20 ha (la de referencia del equipo) usa ~56 % de un robot y deja margen negativo. "
          "Para no perder hay que cobrar un mínimo por robot instalado o compartir el robot entre fincas vecinas. "
          "La regla de robots enteros es estricta: con camas a 2,5 m un robot cubre 29,9 ha y la finca de 30 ha pasa a 2 robots; "
          "en la práctica bastaría bajar la fracción de camas de 60 % a 59,8 %. Con esa misma regla estricta, el RaaS y el "
          "híbrido no llegan a EBIT >= 0 en ninguna escala si las camas están a 2,5 m.")

    # 6. tablas por escala
    for S in escalas:
        filas = []
        for clave in ("venta", "raas", "saas_hw", "hibrido", "maxpro"):
            e = evaluar_escala(p, S, clave)
            flota = []
            if e["robots_ultra"]:
                flota.append("%d Ultra (%d reserva)" % (e["robots_ultra"], e["robots_reserva"] if not e["robots_maxpro"] else 0))
            if e["robots_maxpro"]:
                flota.append("%d MaxPro" % e["robots_maxpro"])
            if e["robots_vendidos"]:
                flota.append("%d Ultra vendidos" % e["robots_vendidos"])
            filas.append([e["nombre"], " + ".join(flota) or "sin robot", e["nodos"],
                          "%d téc. + %s agr." % (e["tecnicos"] + e["operadores_maxpro"], fmt(e["agronomos_fte"], 2)),
                          fmt(e["ingreso"]), fmt(e["costo_caja"] + e["depreciacion"]), pct(e["margen_bruto_pct"]),
                          fmt(e["ebit"]), fmt(e["capex_vendedor"]), fmt(e["payback_meses"], 0),
                          fmt(e["costo_productor_ha"]), fmt(e["roi_productor"], 1) + "x", fmt(e["equilibrio_kg_ha"])])
        desc = ", ".join("%d %s (%s ha)" % (n, {"pequena": "pequeñas", "mediana": "medianas", "grande": "grandes"}[nom], fmt(ha))
                         for nom, ha, n, _ in partir_escala(p, S) if n)
        tabla("6.%d. Escala %s ha bajo contrato: %s" % (escalas.index(S) + 1, fmt(S), desc),
              ["Modelo", "Flota", "Nodos", "Personal", "Ingreso", "Costo directo (caja + dep.)", "Margen bruto",
               "EBIT tras overhead", "CAPEX vendedor", "Payback CAPEX (meses)", "Costo productor/ha",
               "ROI productor", "Equilibrio kg/ha"], filas,
              "Overhead fijo: %s USD/año. El payback divide el CAPEX del vendedor (robots, red, instalación y CAC) "
              "por la contribución de caja mensual antes del overhead." % fmt(p.v("operacion_vendedor.overhead_fijo_usd_mes") * 12))

    # 7. escala mínima rentable
    filas = []
    for clave in ("venta", "raas", "saas_hw", "hibrido", "maxpro"):
        S = 10.0
        encontrado = None
        while S <= 100000:
            if evaluar_escala(p, S, clave)["ebit"] >= 0:
                # Se confirma que EBIT >= 0 en TODOS los puntos de la malla (pasos de 2 %) hasta 1,5x
                # esa escala, para evitar saltos por redondeo de técnicos y robots.
                # CORRECCIÓN (verificación de negocio, 2026-10-23): antes solo se probaba el punto 1,5x.
                # El RaaS salía en 1.071 ha aunque volvía a pérdida entre ~1.090 y ~1.350 ha.
                T = S * 1.02
                estable = evaluar_escala(p, S * 1.5, clave)["ebit"] >= 0
                while estable and T < S * 1.5:
                    if evaluar_escala(p, T, clave)["ebit"] < 0:
                        estable = False
                    T *= 1.02
                if estable:
                    encontrado = S
                    break
            S *= 1.02
        if encontrado:
            e = evaluar_escala(p, encontrado, clave)
            filas.append([PLANES[clave][0], fmt(encontrado), fmt(e["fincas_total"]),
                          pct(encontrado / p.v("mercado.ha_arandano_colombia")), fmt(e["capex_vendedor"])])
        else:
            filas.append([PLANES[clave][0], "> 100.000", "-", "-", "-"])
    tabla("7. Escala mínima para cubrir el overhead fijo (EBIT >= 0)",
          ["Modelo", "ha bajo contrato", "Fincas", "%% del arándano colombiano (%s ha)" % fmt(p.v("mercado.ha_arandano_colombia")),
           "CAPEX acumulado vendedor"], filas,
          "Si la escala mínima pasa del 30 % del arándano colombiano, el negocio necesita otros frutales u otros países.")

    # 8. sensibilidad capacidad y costo del robot
    filas = []
    for vel in (0.4, 0.5, 0.6, 0.8, 1.0):
        fila = ["%s m/s" % fmt(vel, 1)]
        for fr in (0.4, 0.6, 1.0):
            q = p.con({"inspeccion.velocidad_m_s": vel, "inspeccion.fraccion_camas_por_semana": fr})
            cu = costo_unitario(q, "raas", p.v("segmentos.tam_finca_mediana_ha"), False, enteros=False)
            fila.append("%s ha / %s USD/ha" % (fmt(ha_por_robot(q, "robot_ultra", "dedicado"), 1), fmt(cu["costo_ha"])))
        filas.append(fila)
    tabla("8. Sensibilidad: ha por D1 Ultra dedicado y costo del vendedor por ha (RaaS, finca de %s ha)" % fmt(p.v("segmentos.tam_finca_mediana_ha")),
          ["Velocidad", "40 % camas/semana", "60 % camas/semana", "100 % camas/semana"], filas,
          "Robots fraccionarios (flota bien usada entre fincas). En una finca real el costo sube a saltos, "
          "porque una finca de 30 ha necesita 1, 2 o 3 robots enteros.")

    filas = []
    base = costo_unitario(p, "raas", p.v("segmentos.tam_finca_mediana_ha"), False, enteros=False)["costo_ha"]
    for etiqueta, cambios in (("Base", {}),
                              ("D1 Ultra a precio de lista (9.600)", {"robot_ultra.precio_usd": p.v("robot_ultra.precio_lista_usd")}),
                              ("Vida del robot 4 años", {"robot_ultra.vida_anos": 4}),
                              ("Vida del robot 2 años", {"robot_ultra.vida_anos": 2}),
                              ("Batería NO intercambiable", {"robot_ultra.bateria_intercambiable": False}),
                              ("Camas a 2,0 m", {"geometria.distancia_entre_camas_m": 2.0}),
                              ("1 técnico por 8 robots", {"operacion_vendedor.robots_por_tecnico_dedicado": 8}),
                              ("Ventana 9 h/día", {"robot_ultra.ventana_h_dia": 9})):
        q = p.con(cambios)
        c = costo_unitario(q, "raas", p.v("segmentos.tam_finca_mediana_ha"), False, enteros=False)
        filas.append([etiqueta, fmt(ha_por_robot(q, "robot_ultra", "dedicado"), 1), fmt(c["costo_ha"]),
                      fmt(c["costo_ha"] - base), pct((p.v("precios.raas_dedicado_usd_ha_ano") - c["costo_ha"]) / p.v("precios.raas_dedicado_usd_ha_ano"))])
    tabla("9. Sensibilidad del costo RaaS dedicado (precio de lista %s USD/ha, robots fraccionarios)" % fmt(p.v("precios.raas_dedicado_usd_ha_ano")),
          ["Cambio", "ha por robot", "Costo vendedor/ha", "Diferencia vs. base", "Margen bruto al precio de lista"], filas)

    filas = []
    riesgos = (("Base", {}),
               ("Velocidad 0,4 m/s (base de operacion.md)", {"inspeccion.velocidad_m_s": 0.4}),
               ("Velocidad 0,6 m/s", {"inspeccion.velocidad_m_s": 0.6}),
               ("Batería de 200 ciclos (garantía del manual)", {"robot_ultra.ciclos_vida_bateria": 200}),
               ("Línea de vista: el monitor acompaña al robot 7 h/día y no se ahorra scouting",
                {"productor.minutos_operario_dia_por_robot": 420, "productor.scouting_reemplazado_con_robot_frac": 0.0}),
               ("Línea de vista, pero el monitor que acompaña ya estaba en nómina",
                {"productor.minutos_operario_dia_por_robot": 20, "productor.scouting_reemplazado_con_robot_frac": 0.0}),
               ("0,6 m/s + batería de 200 ciclos", {"inspeccion.velocidad_m_s": 0.6, "robot_ultra.ciclos_vida_bateria": 200}),
               # Filas añadidas por la verificación de negocio (2026-10-23): supuestos de otras fuentes del proyecto
               ("Entrecalle 2,5 m (ODEPA, base de finanzas/parametros.yaml)", {"geometria.distancia_entre_camas_m": 2.5}),
               ("Entrecalle 2,2 m (Peña et al. 2023, finca de 1 ha en Cundinamarca)", {"geometria.distancia_entre_camas_m": 2.2}),
               ("IVA de importación como costo (factor 1,359 de finanzas/importacion_factores.csv)",
                {"robot_ultra.importacion_frac": 0.359}),
               ("Operario 40 min/día (5 cambios de batería de 6 min + alertas)", {"productor.minutos_operario_dia_por_robot": 40}))
    for etiqueta, cambios in riesgos:
        q = p.con(cambios)
        c = costo_unitario(q, "raas", p.v("segmentos.tam_finca_mediana_ha"), False)
        cf = costo_unitario(q, "raas", p.v("segmentos.tam_finca_mediana_ha"), False, enteros=False)
        pr = q.v("precios.raas_dedicado_usd_ha_ano")
        filas.append([etiqueta, fmt(ha_por_robot(q, "robot_ultra", "dedicado"), 1),
                      "%d" % c["seg"]["robots_ded"] if c["seg"]["fincas"] == 0 else fmt(c["seg"]["robots_ded"] / c["seg"]["fincas"], 0),
                      fmt(c["costo_ha"]), pct((pr - c["costo_ha"]) / pr), pct((pr - cf["costo_ha"]) / pr),
                      fmt(c["prod_costo_ha"]), fmt(c["valor_ha"] / c["prod_costo_ha"], 1) + "x"])
    tabla("9b. Riesgos operativos del RaaS dedicado (finca de %s ha, precio %s USD/ha)" % (fmt(p.v("segmentos.tam_finca_mediana_ha")), fmt(p.v("precios.raas_dedicado_usd_ha_ano"))),
          ["Escenario", "ha por robot", "Robots en la finca", "Costo vendedor/ha", "Margen (robots enteros)",
           "Margen (flota repartida)", "Costo productor/ha", "ROI productor"], filas,
          "El manual del D1 Ultra pide 'Keep the robot within your line of sight'. Si eso aplica a la operación autónoma, "
          "una persona acompaña al robot.")

    filas = []
    for perd in (0.006, 0.01, 0.02, 0.04):
        fila = [pct(perd, 1)]
        for precio_kg in (4.0, 6.0):
            q = p.con({"productor.perdida_evitada_con_robot_frac": perd, "productor.precio_usd_kg": precio_kg})
            v = valor_productor_ha(q, True)["total"]
            fila.append("%s / %s" % (fmt(v), fmt(v / p.v("productor.roi_objetivo"))))
        filas.append(fila)
    tabla("10. Sensibilidad del productor con robot: valor/ha y precio máximo con ROI %sx" % fmt(p.v("productor.roi_objetivo"), 0),
          ["Pérdida evitada", "4 USD/kg", "6 USD/kg"], filas,
          "Cada celda muestra el valor por ha y luego el precio máximo por ha. Rendimiento %s kg/ha." % fmt(p.v("productor.rendimiento_kg_ha")))

    # 11. mercado
    filas = []
    total = 0.0
    for clave, etiqueta, plan_precio in (("ha_arandano_colombia", "Arándano Colombia", "precios.raas_dedicado_usd_ha_ano"),
                                         ("ha_fresa_colombia", "Fresa Colombia", "precios.raas_dedicado_usd_ha_ano"),
                                         ("ha_uchuva_colombia", "Uchuva Colombia", "precios.saas_usd_ha_ano"),
                                         ("ha_mora_colombia", "Mora Colombia", "precios.saas_usd_ha_ano"),
                                         ("ha_aguacate_hass_colombia", "Aguacate Hass Colombia (solo red + SaaS)", "precios.saas_usd_ha_ano"),
                                         ("ha_arandano_peru", "Arándano Perú", "precios.raas_dedicado_usd_ha_ano")):
        ha = p.v("mercado." + clave)
        adop = ha * p.v("mercado.adopcion_frac")
        ing = adop * p.v(plan_precio)
        total += ing
        filas.append([etiqueta, fmt(ha), "RaaS" if "raas" in plan_precio else "SaaS + kit", fmt(adop), fmt(ing)])
    filas.append(["Total", "", "", "", fmt(total)])
    tabla("11. Mercado alcanzable con %s de adopción (ingreso anual)" % pct(p.v("mercado.adopcion_frac")),
          ["Cultivo", "ha (EVA 2025 / Perú 2025)", "Plan supuesto", "ha con %s" % pct(p.v("mercado.adopcion_frac")), "Ingreso anual USD"], filas,
          "Fresa y Perú requieren validar el robot en otros sistemas (mesa alta, desierto costero). Que la uchuva y la mora usen SaaS es un SUPUESTO.")

    if fuentes:
        filas = [[k, fmt(v, 2) if isinstance(v, float) else str(v), f] for k, v, f in p.lista()]
        tabla("Anexo. Parámetros y fuentes", ["Parámetro", "Valor", "Fuente"], filas)
    n_sup = sum(1 for _, _, f in p.lista() if f.startswith("SUPUESTO") or "NO VERIFICADO" in f or f.startswith("PROPUESTA"))
    n_tot = sum(1 for _ in p.lista())
    print("")
    print("Parámetros: %d en total; %d son SUPUESTO, PROPUESTA o NO VERIFICADO." % (n_tot, n_sup))


def resultados_json(p):
    escalas = [int(x) for x in str(p.v("general.escalas_ha")).split(",")]
    out = {"capacidad_ha_por_robot": {
        "ultra_dedicado": ha_por_robot(p, "robot_ultra", "dedicado"),
        "ultra_ruta": ha_por_robot(p, "robot_ultra", "ruta"),
        "maxpro_compartido": ha_por_robot(p, "robot_maxpro", "ruta")},
        "capex_robot": {"ultra": capex_robot(p, "robot_ultra"), "maxpro": capex_robot(p, "robot_maxpro")},
        "valor_productor_ha": {"con_robot": valor_productor_ha(p, True), "solo_red": valor_productor_ha(p, False)},
        "escalas": [evaluar_escala(p, S, c) for S in escalas for c in PLANES]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--param", default=YAML_DEF, help="ruta del YAML de parámetros")
    ap.add_argument("--fuentes", action="store_true", help="imprime el anexo de parámetros y fuentes")
    ap.add_argument("--json", default=None, help="escribe los resultados en este archivo JSON")
    a = ap.parse_args(argv)
    crudo, motor = cargar_parametros(a.param)
    p = Param(crudo)
    imprimir(p, motor, a.fuentes)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(resultados_json(p), f, ensure_ascii=False, indent=2, default=lambda x: None)
        print("\nJSON escrito en " + a.json)


if __name__ == "__main__":
    sys.exit(main())
