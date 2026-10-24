#!/usr/bin/env python3
"""Modelo financiero del kit robot para AGRAR (Sabana Hack, reto "Berry Good Idea").

Contexto (RESPUESTAS_MENTOR.md): el cliente es AGRAR, empresa de automatización de
invernaderos (PLC y sensores por bloque ya instalados). Presupuesto por proyecto
90-110 M COP, margen mínimo de AGRAR 40 %, equilibrio del cliente final < 2 años,
~10 proyectos/año. Finca típica: 20-25 ha, ~40 bloques de 0,5 ha.

Qué calcula (todo con la biblioteca estándar; corre con `python3 -I agrar_roi.py`):
  1. BOM del kit por finca (D1 Ultra y variante D1 EDU) con costo puesto en Colombia.
  2. Economía de AGRAR: precio con margen >= 40 %, encaje en 90-110 M COP, recortes,
     ingreso/margen anual con 10 proyectos y suscripción recurrente.
  3. Economía del cliente final: valor de cosecha, pérdida, beneficio por puntos de
     pérdida evitados, ahorro de horas de monitoreo, payback y sensibilidad.
  4. Capacidad de un robot (geometría de naves, velocidad, batería, carga).
  5. Matriz de alternativas (6 criterios y 7 con Escalabilidad) y sensibilidades.
  6. Puente de costo/ha del híbrido frente a 430 / 722 / 820 USD/ha.
Escribe CSVs y RESUMEN.md en este mismo directorio.

Convención de marcas en PAR (campo `tipo`):
  FUENTE      verificado en una fuente citada (mentor, datos.gov.co, etc.)
  DERIVADO    calculado a partir de FUENTES
  SUPUESTO    decisión del analista/equipo, sin fuente; validar en piloto/cotización
  NO VERIFICADO  cifra recibida que no se pudo confirmar
"""
import csv
import itertools
import math
import os
import site
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
FIN = os.path.dirname(AQUI)  # datos/finanzas

# ----------------------------------------------------------------------------
# 0. PARÁMETROS (dict con valor, rango, tipo y fuente/nota)
# ----------------------------------------------------------------------------
PAR = {}


def par(nombre, v, tipo, nota="", lo=None, hi=None):
    PAR[nombre] = dict(v=v, lo=lo, hi=hi, tipo=tipo, nota=nota)


def V(nombre):
    return PAR[nombre]["v"]


# --- macro e importación -----------------------------------------------------
par("trm_cop_usd", 3185.01, "FUENTE",
    "TRM vigente el 2026-10-23 (datos.gov.co 32sa-8pi3); 3.158,43 rige 24-26 oct. "
    "lo/hi = mínimo/máximo de 12 meses (3.048,12 / 3.900,82).", 3048.12, 3900.82)
par("iva", 0.19, "FUENTE", "ET art. 468; base = valor aduanero + arancel (art. 459).")
par("arancel", 0.05, "FUENTE / NO VERIFICADO",
    "5 % para 8479.50 / 8479.89 (DIAN, Decreto 1881/2021); clasificación del cuadrúpedo sin confirmar "
    "(8543.70.90 pagaría 0 %).")
par("flete_usd_kg", 5.0, "SUPUESTO", "Aéreo México-Bogotá, kg tasable (igual a finanzas/parametros.yaml).")
par("flete_fijo_usd", 150.0, "SUPUESTO", "Documentación y manejo por embarque.")
par("seguro_frac", 0.01, "SUPUESTO", "1 % del FOB.")
par("agencia_transporte_usd", 350.0, "SUPUESTO", "Agencia de aduanas + bodegaje + transporte interno.")
par("iva_recuperable_agrar", True, "SUPUESTO / NO VERIFICADO",
    "AGRAR vende bienes gravados: se supone que descuenta el IVA de importación y de compras locales. "
    "Consultar contador. Si no, el IVA es costo (escenario 'IVA costo').")
par("factor_previo", 1.35, "SUPUESTO (equipo)", "Factor de importación previo; el cálculo da ~1,35-1,36.")

# --- negocio AGRAR (mentor) --------------------------------------------------
par("presupuesto_min_cop", 90e6, "FUENTE", "RESPUESTAS_MENTOR §2: inversión por proyecto 90-110 M COP ('dato al aire').")
par("presupuesto_max_cop", 110e6, "FUENTE", "Ídem.")
par("margen_min", 0.40, "FUENTE", "Margen mínimo de AGRAR. Se interpreta como margen bruto sobre el precio "
    "(SUPUESTO de lectura; si fuera recargo sobre costo, el precio baja un 17 %).")
par("proyectos_anio", 10, "FUENTE", "~10 proyectos/año (nicho, específicos de cada cliente).")
par("payback_max_meses", 24, "FUENTE", "Punto de equilibrio del cliente final < 2 años.")
par("precio_ref_ventilador_cop", 3.0e6, "FUENTE", "1,5-4,5 M COP por ventilador (referencia del mentor).")

# --- servicios (COP; son costo interno de AGRAR) -------------------------------
par("tarifa_hora_cop", 80000.0, "SUPUESTO",
    "Costo cargado de ingeniero ~12 M COP/mes / 160 h = 75 mil; ~25 USD/h a TRM base.")
par("horas_levantamiento", 60, "SUPUESTO", "Mapa de 40 bloques/naves/camas, marcadores y rutas del robot.")
par("horas_integracion_plc", 40, "SUPUESTO", "Modbus RTU / LoRaWAN hacia el controlador existente (protocolo abierto).")
par("horas_software", 50, "SUPUESTO", "Navegación por pasillo (el D1 no tiene ROS), captura, buffer y reenvío.")
par("horas_clasificador_panel", 40, "SUPUESTO", "Ajuste del detector con fotos de la finca, panel y alertas.")
par("horas_instalacion", 48, "SUPUESTO", "2 personas x 3 días x 8 h: puesta en marcha y capacitación.")
par("viaticos_cop", 1.9e6, "SUPUESTO", "Transporte y viáticos del equipo a la finca.")
par("nre_desarrollo_cop", 64e6, "SUPUESTO", "Desarrollo base reutilizable (~20.000 USD), amortizado entre los proyectos.")
par("proyectos_amortizacion", 30, "SUPUESTO", "3 años x 10 proyectos.")
par("garantia_frac", 0.05, "SUPUESTO", "Provisión de garantía/contingencia sobre el hardware puesto.")
par("horas_mult_adverso", 1.25, "SUPUESTO", "Sobrecosto de horas en el escenario adverso.")
par("horas_extra_2do_robot", 0.35, "SUPUESTO", "Fracción de horas adicionales por cada robot extra (levantamiento compartido).")

# --- hardware: precios FOB en USD y peso de envío -------------------------------
par("fob_d1_ultra", 7499.0, "NO VERIFICADO", "Hoja del equipo (FOB México). La tienda AgiBot lista 9.600 USD (2026-10-23).", 7499.0, 9600.0)
par("fob_d1_edu", 5999.0, "NO VERIFICADO", "Hoja del equipo; tienda AgiBot 6.080 USD.", 5999.0, 6080.0)
par("fob_bateria", 450.0, "NO VERIFICADO", "ESCALABILIDAD §2.7 (AgiBot no la vende en su tienda).")
par("fob_camara", 350.0, "SUPUESTO", "Cámara RGB 4K + iluminación (noche/amanecer).")
par("fob_jetson", 249.0, "SUPUESTO", "Jetson Orin Nano Super 8 GB; precio de lista anunciado ~249 USD, no reverificado hoy.")
par("fob_jetson_acc", 150.0, "SUPUESTO", "SSD NVMe, fuente DC-DC, caja con protección.")
par("fob_sensor_thr", 60.0, "SUPUESTO", "Sensor T/HR calibrado con filtro (clase SHT4x). Referencia: Dragino LLMS01 129 USD (hoja foliar).")
par("fob_lora", 80.0, "SUPUESTO", "Módulo LoRaWAN/Modbus RS485 + antena.")
par("peso_d1", 30.0, "SUPUESTO", "kg con caja (finanzas/parametros.yaml).")
par("fob_x2_ultra", 39999.0, "NO VERIFICADO", "Hoja del equipo (humanoide X2 Ultra, FOB).")
par("peso_x2", 80.0, "SUPUESTO", "kg de envío (finanzas/parametros.yaml).")
par("fob_amiga", 22500.0, "NO VERIFICADO", "Rango 20-25 mil USD (finanzas/parametros.yaml).")
par("peso_amiga", 250.0, "SUPUESTO", "kg de envío (finanzas/parametros.yaml).")
par("local_mastil_cop", 800000.0, "SUPUESTO", "Mástil y soporte estabilizado, fabricación local.")
par("local_base_carga_cop", 2200000.0, "SUPUESTO", "Base de carga: caseta techada, cargador, UPS y punto de acceso wifi para descarga.")
par("local_cableado_cop", 320000.0, "SUPUESTO", "Cableado, conectores y protección.")

# --- capacidad -------------------------------------------------------------------
par("area_bloque_ha", 0.5, "FUENTE", "Bloques de 0,5 ha (o 1 ha).")
par("nave_ancho_m", 6.8, "FUENTE", "Mentor: 6,8 m en invernadero (12,5-13 m en macrotúnel).")
par("nave_largo_m", 80.0, "FUENTE", "Mentor: unos 80 m.")
par("camas_por_nave", 2.5, "FUENTE", "Mentor: 2-3 camas por nave.", 2.0, 3.0)
par("naves_por_bloque", 9, "DERIVADO", "floor(5.000 m2 / (6,8 x 80 m)) = 9; el camino central de 5-6 m ya está fuera de este cálculo.")
par("pasillos_por_nave", "camas-1", "SUPUESTO", "El robot camina entre camas; las plantas crecen hacia el pasillo (mentor). Rango 1-2 pasillos por nave.")
par("overhead_recorrido", 1.3, "SUPUESTO", "Giros en cabeceras, paradas de captura (igual a finanzas).")
par("velocidad_m_s", 0.5, "SUPUESTO", "Velocidad efectiva de inspección con fotos útiles.", 0.4, 0.8)
par("velocidad_transito_m_s", 1.0, "SUPUESTO", "Traslado base-bloque por el camino central.")
par("dist_base_bloque_m", 250.0, "DERIVADO", "Finca de ~22,5 ha (~475 m de lado): 0,38 x lado = 181 m x 1,3 de trazado ~ 236, redondeado a 250 m (una vía).")
par("autonomia_h", 1.5, "FUENTE / SUPUESTO", "Ficha D1 Ultra: 1-2 h; con cámara y cómputo puede bajar.", 1.0, 2.0)
par("reserva_bateria", 0.20, "SUPUESTO", "Reserva de seguridad (ESCALABILIDAD §6.3).")
par("carga_min", 60.0, "FUENTE", "Carga ~1 h del 10 al 90 % (manual D1 Ultra).")
par("cambio_bateria_min", 5.0, "SUPUESTO", "Cambio manual con batería de repuesto (requiere una persona).")
par("ventana_noche_h", 8.0, "SUPUESTO", "Patrulla de riesgo de noche/amanecer, p. ej. 22:00-06:00 (operarios trabajan 6-14 h).")
par("noches_operacion_anio", 200, "SUPUESTO", "Noches con patrulla al año (lluvia fuerte, mantenimiento, noches sin riesgo); define el desgaste de baterías.")
par("vida_bateria_ciclos", 300, "SUPUESTO", "ESCALABILIDAD §2.7; la garantía de AgiBot cubre 200 ciclos.")
par("bloques_finca", 40, "FUENTE", "Finca típica de ~40 bloques.")
par("monitoreo_bloques_persona", (12, 15), "FUENTE", "Una persona monitorea 12-15 bloques en 4-5 días de jornada.")
par("monitoreo_dias_persona", (4, 5), "FUENTE", "Ídem (mentor, en papel).")

# --- suscripción (costos de servir, COP/año por finca) -------------------------
par("nube_usd_anio", 240.0, "SUPUESTO", "Almacenamiento y sincronización (finanzas/parametros.yaml).")
par("ingeniero_soporte_cop_mes", 7.0e6, "SUPUESTO", "Costo cargado de un ingeniero de soporte remoto.")
par("fincas_por_ingeniero", 25, "SUPUESTO", "Fincas atendidas por un ingeniero de soporte.")
par("repuestos_frac_hw", 0.04, "SUPUESTO", "Repuestos y reparaciones: 4 % del hardware puesto al año.")
par("retencion_suscripcion", 0.90, "SUPUESTO", "Fincas que renuevan cada año.")

# --- cliente final -------------------------------------------------------------
par("ha_finca", 22.5, "FUENTE", "20-25 ha (mentor).", 20.0, 25.0)
par("rend_t_ha_cons", 9.07, "FUENTE", "EVA 2025: 6.030,66 t / 664,72 ha cosechadas.")
par("rend_t_ha_central", 12.0, "FUENTE", "Forbes Colombia 26-may-2026 ('algunos cultivos rinden ~12 t/ha').")
par("precio_usd_kg_cons", 6.0, "SUPUESTO", "FOB implícito Colombia 2025 (5,2-6,1) y FOB Perú 6,22 (finanzas.md).")
par("precio_usd_kg_central", 8.0, "SUPUESTO", "Extremo bajo del rango Planasa 8-10 USD/kg en finca (fuente interesada, Forbes 2026).")
par("precio_usd_kg_alto", 10.0, "SUPUESTO", "Extremo alto de Planasa.")
par("perdida_frac", (0.10, 0.25), "FUENTE", "Mentor: pérdida fitosanitaria 10-25 % de lo cosechado.")
par("perdida_sin_prevencion", (0.30, 0.40), "FUENTE", "Mentor: 30-40 % sin manejo preventivo.")
par("puntos_evitados", (0.5, 1.0, 2.0, 3.0), "SUPUESTO",
    "Puntos porcentuales de pérdida que el sistema evita, a medir en piloto con camas testigo. "
    "AGRAR ya tiene un modelo predictivo en el PLC: el aporte incremental del robot es probablemente de 0,5-2 puntos.")
par("jornal_usd", 19.0, "SUPUESTO", "Jornal indicado por el equipo; finanzas.md calcula 23,82 USD con prestaciones (PL 504/2025).", 19.0, 23.82)
par("vueltas_anio", 26, "SUPUESTO", "Vueltas de monitoreo manual por año (quincenal). Rango 12-52.", 12, 52)
par("fraccion_monitoreo_sustituida", 0.5, "SUPUESTO", "Parte del recorrido en papel que el robot reemplaza (el resto verifica alertas).")
par("operador_robot_min_dia", 20.0, "SUPUESTO", "Operario del cliente: cambio de baterías y confirmación de alertas (ESCALABILIDAD §6.4).")
par("falsas_alarmas_ha_anio", 5.0, "SUPUESTO", "finanzas/parametros.yaml; reemplazar con la matriz de confusión.")
par("costo_falsa_alarma_usd", 30.0, "SUPUESTO", "Visita del agrónomo/operario a verificar.")
par("vida_util_anios", 3, "SUPUESTO (equipo)", "Para el costo anualizado por ha (línea recta, igual a finanzas).")

COP_M = 1e6
TRM = V("trm_cop_usd")


# ----------------------------------------------------------------------------
# Utilidades de formato
# ----------------------------------------------------------------------------
def fe(x, d=0):
    """Número con formato español: miles con punto, decimales con coma."""
    if x is None or (isinstance(x, float) and math.isinf(x)):
        return "n/a"
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fm(x, d=1):
    """COP -> millones de COP con formato español."""
    return fe(x / COP_M, d)


def tabla(cabecera, filas):
    out = ["| " + " | ".join(cabecera) + " |", "|" + "|".join("---" for _ in cabecera) + "|"]
    for f in filas:
        out.append("| " + " | ".join(str(c) for c in f) + " |")
    return "\n".join(out)


def csv_out(nombre, cabecera, filas):
    with open(os.path.join(AQUI, nombre), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(filas)


# ----------------------------------------------------------------------------
# 1. BOM y costo puesto en Colombia
# ----------------------------------------------------------------------------
def lineas_bom(robot):
    """Líneas del kit por robot. origen: import (USD FOB), local (COP), servicio (COP)."""
    fob_robot = V("fob_d1_ultra") if robot == "ultra" else V("fob_d1_edu")
    nom_robot = "Robot AgiBot D1 Ultra" if robot == "ultra" else "Robot AgiBot D1 EDU"
    pesos = dict(robot=V("peso_d1"), bat=3.0, cam=1.0, jet=1.0, jetacc=1.0, thr=0.2, lora=0.3)
    return [
        dict(k="robot", nombre=nom_robot, cat="Robot", origen="import", fob=fob_robot, peso=pesos["robot"],
             tipo="NO VERIFICADO", nota="Hoja del equipo (FOB México); tienda 9.600 (Ultra) / 6.080 (EDU)"),
        dict(k="bat", nombre="Batería de repuesto (1 por robot)", cat="Robot", origen="import", fob=V("fob_bateria"), peso=pesos["bat"],
             tipo="NO VERIFICADO", nota="ESCALABILIDAD §2.7"),
        dict(k="cam", nombre="Cámara RGB 4K con iluminación", cat="Visión", origen="import", fob=V("fob_camara"), peso=pesos["cam"],
             tipo="SUPUESTO", nota="Ve fruto/hoja a la altura del arbusto, de noche"),
        dict(k="jet", nombre="Cómputo de borde tipo Jetson Orin Nano Super", cat="Visión", origen="import", fob=V("fob_jetson"), peso=pesos["jet"],
             tipo="SUPUESTO", nota="Precio de lista ~249 USD, no reverificado"),
        dict(k="jetacc", nombre="SSD, fuente DC-DC y caja del cómputo", cat="Visión", origen="import", fob=V("fob_jetson_acc"), peso=pesos["jetacc"],
             tipo="SUPUESTO", nota=""),
        dict(k="thr", nombre="Sensor T/HR a bordo", cat="Sensado", origen="import", fob=V("fob_sensor_thr"), peso=pesos["thr"],
             tipo="SUPUESTO", nota="Requisito explícito del mentor (§5)"),
        dict(k="lora", nombre="Módulo LoRaWAN / Modbus RS485", cat="Comunicación", origen="import", fob=V("fob_lora"), peso=pesos["lora"],
             tipo="SUPUESTO", nota="Envío al PLC/controlador de AGRAR; buffer y reenvío al volver"),
        dict(k="mastil", nombre="Mástil y soporte de cámara (local)", cat="Mecánica", origen="local", cop=V("local_mastil_cop"),
             tipo="SUPUESTO", nota="Fabricación local"),
        dict(k="base", nombre="Base de carga (caseta, cargador, UPS, punto de acceso)", cat="Infraestructura", origen="local", cop=V("local_base_carga_cop"),
             tipo="SUPUESTO", nota="Descarga de datos con red de la finca"),
        dict(k="cable", nombre="Cableado, conectores y protección", cat="Infraestructura", origen="local", cop=V("local_cableado_cop"),
             tipo="SUPUESTO", nota=""),
    ]


def kit(robot="ultra", n=1, fob_robot=None, trm=None, iva_rec=None, horas_mult=1.0, bateria=True,
        nre=True, garantia=True, arancel=None, peso_robot=None):
    """Costo del kit por finca. Devuelve líneas y totales en COP."""
    trm = trm or TRM
    iva_rec = V("iva_recuperable_agrar") if iva_rec is None else iva_rec
    arancel = V("arancel") if arancel is None else arancel
    lin = lineas_bom(robot)
    if fob_robot is not None:
        lin[0]["fob"] = fob_robot
    if peso_robot is not None:
        lin[0]["peso"] = peso_robot
    if not bateria:
        lin = [l for l in lin if l["k"] != "bat"]
    for l in lin:
        l["cant"] = n
    # importación consolidada de un solo embarque
    imp = [l for l in lin if l["origen"] == "import"]
    fob_tot = sum(l["fob"] * l["cant"] for l in imp)
    peso_tot = sum(l["peso"] * l["cant"] for l in imp)
    flete = V("flete_usd_kg") * peso_tot + V("flete_fijo_usd")
    seguro = V("seguro_frac") * fob_tot
    cif = fob_tot + flete + seguro
    arancel_usd = arancel * cif
    iva_imp_usd = V("iva") * (cif + arancel_usd)
    agencia = V("agencia_transporte_usd")
    adders = flete + seguro + arancel_usd + agencia
    for l in imp:
        fob_l = l["fob"] * l["cant"]
        l["fob_total_usd"] = fob_l
        l["puesto_usd"] = fob_l * (1 + adders / fob_tot)
        l["puesto_cop"] = l["puesto_usd"] * trm
        l["iva_cop"] = iva_imp_usd * (fob_l / fob_tot) * trm
    for l in lin:
        if l["origen"] == "local":
            l["fob_total_usd"] = None
            l["puesto_cop"] = l["cop"] * l["cant"]
            l["puesto_usd"] = l["puesto_cop"] / trm
            l["iva_cop"] = l["puesto_cop"] * V("iva")
    hw_puesto = sum(l["puesto_cop"] for l in lin)
    iva_hw = sum(l["iva_cop"] for l in lin)

    # servicios
    h_base = (V("horas_levantamiento") + V("horas_integracion_plc") + V("horas_software")
              + V("horas_clasificador_panel") + V("horas_instalacion"))
    h_tot = h_base * horas_mult * (1 + V("horas_extra_2do_robot") * (n - 1))
    serv = []
    for nombre_h, clave in (("Levantamiento de finca y rutas (40 bloques)", "horas_levantamiento"),
                            ("Integración con PLC/controlador (Modbus / LoRaWAN)", "horas_integracion_plc"),
                            ("Software: navegación por pasillo, captura, buffer", "horas_software"),
                            ("Clasificador, panel y alertas", "horas_clasificador_panel"),
                            ("Instalación, pruebas y capacitación en sitio", "horas_instalacion")):
        h = V(clave) * horas_mult * (1 + V("horas_extra_2do_robot") * (n - 1))
        serv.append(dict(nombre=nombre_h, cat="Ingeniería", horas=h, cop=h * V("tarifa_hora_cop"),
                         tipo="SUPUESTO", nota=f"{fe(h,0)} h x {fe(V('tarifa_hora_cop'),0)} COP/h"))
    viaticos = V("viaticos_cop")
    nre_p = V("nre_desarrollo_cop") / V("proyectos_amortizacion") if nre else 0.0
    garantia_cop = V("garantia_frac") * hw_puesto if garantia else 0.0
    serv_cop = sum(s["cop"] for s in serv) + viaticos + nre_p + garantia_cop
    costo_sin_iva = hw_puesto + serv_cop
    iva_total = iva_hw
    costo = costo_sin_iva + (0 if iva_rec else iva_total)
    margen = V("margen_min")
    precio = costo / (1 - margen)
    return dict(
        lineas=lin, servicios=serv, viaticos=viaticos, nre=nre_p, garantia=garantia_cop,
        fob_tot=fob_tot, peso=peso_tot, flete=flete, seguro=seguro, cif=cif, arancel_usd=arancel_usd,
        iva_imp_usd=iva_imp_usd, agencia=agencia, hw_puesto=hw_puesto, iva_hw=iva_hw,
        horas=h_tot, serv_cop=serv_cop, costo_sin_iva=costo_sin_iva, costo=costo, precio=precio,
        precio_con_iva=precio * (1 + V("iva")), factor_import=(cif + arancel_usd + agencia) / fob_tot,
        factor_import_iva=(cif + arancel_usd + iva_imp_usd + agencia) / fob_tot,
        trm=trm, n=n, iva_rec=iva_rec, robot=robot)


def cabe(precio):
    if precio > V("presupuesto_max_cop"):
        return "NO (sobre 110 M)"
    if precio < V("presupuesto_min_cop"):
        return "SÍ (bajo 90 M)"
    return "SÍ"


K_ULTRA = kit("ultra")
K_EDU = kit("edu")

# ---- escenarios de precio de AGRAR ---------------------------------------------
ESCENARIOS_PRECIO = [
    ("Base (Ultra 7.499, IVA recuperable, TRM 3.185)", dict(robot="ultra")),
    ("Ultra a precio tienda 9.600", dict(robot="ultra", fob_robot=9600.0)),
    ("IVA como costo", dict(robot="ultra", iva_rec=False)),
    ("TRM 3.900 (máx. 12 m)", dict(robot="ultra", trm=PAR["trm_cop_usd"]["hi"])),
    ("Horas +25 %", dict(robot="ultra", horas_mult=V("horas_mult_adverso"))),
    ("ADVERSO: 9.600 + IVA costo + TRM 3.900 + horas +25 %",
     dict(robot="ultra", fob_robot=9600.0, iva_rec=False, trm=PAR["trm_cop_usd"]["hi"], horas_mult=V("horas_mult_adverso"))),
    ("D1 EDU (5.999)", dict(robot="edu")),
    ("D1 EDU, escenario ADVERSO (6.080)",
     dict(robot="edu", fob_robot=6080.0, iva_rec=False, trm=PAR["trm_cop_usd"]["hi"], horas_mult=V("horas_mult_adverso"))),
    ("2 robots D1 Ultra (finca exigente)", dict(robot="ultra", n=2)),
]
FILAS_PRECIO = []
for nom, kw in ESCENARIOS_PRECIO:
    k = kit(**kw)
    FILAS_PRECIO.append((nom, k))

# ---- recortes desde el escenario adverso ----------------------------------------
ADV = dict(robot="ultra", fob_robot=9600.0, iva_rec=False, trm=PAR["trm_cop_usd"]["hi"], horas_mult=V("horas_mult_adverso"))
RECORTES = []
acum = dict(ADV)
k0 = kit(**acum)
RECORTES.append(("Punto de partida: escenario ADVERSO", k0["costo"], k0["precio"], 0.0))
pasos = [
    ("1. D1 EDU en vez de D1 Ultra (6.080 USD)", dict(robot="edu", fob_robot=6080.0)),
    ("2. Horas -30 % (plantilla reutilizable de rutas y de integración PLC)", dict(horas_mult=V("horas_mult_adverso") * 0.7)),
    ("3. Pasar la amortización del desarrollo (NRE) a la suscripción", dict(nre=False)),
    ("4. Batería de repuesto como opcional (se factura aparte)", dict(bateria=False)),
    ("5. Garantía cubierta por la suscripción (sin provisión inicial)", dict(garantia=False)),
]
prev = k0
for nom, kw in pasos:
    acum.update(kw)
    k = kit(**acum)
    RECORTES.append((nom, k["costo"], k["precio"], prev["precio"] - k["precio"]))
    prev = k

# Recortes marginales desde la base (cuánto ahorra cada palanca en precio)
BASE_KW = dict(robot="ultra")
RECORTES_BASE = []
kb = kit(**BASE_KW)
for nom, kw in [("D1 EDU en vez de Ultra", dict(robot="edu")),
                ("Horas -30 %", dict(horas_mult=0.7)),
                ("Sin NRE en el precio inicial", dict(nre=False)),
                ("Batería de repuesto opcional", dict(bateria=False)),
                ("Sin provisión de garantía", dict(garantia=False)),
                ("Sin base de carga (usa un punto existente)", None)]:
    if kw is None:
        ahorro = (V("local_base_carga_cop") * (1 + V("garantia_frac"))) / (1 - V("margen_min"))
    else:
        ahorro = kb["precio"] - kit(**{**BASE_KW, **kw})["precio"]
    RECORTES_BASE.append((nom, ahorro))

# ---- suscripción -----------------------------------------------------------------


def capacidad(v=None, aut_h=None, modo="A", camas=None, naves=None, bloques=None, dist_base=None):
    v = v or V("velocidad_m_s")
    aut_h = aut_h or V("autonomia_h")
    camas = camas or V("camas_por_nave")
    naves = naves or V("naves_por_bloque")
    bloques = bloques or V("bloques_finca")
    dist_base = dist_base or V("dist_base_bloque_m")
    pasillos = camas - 1
    long_bloque = naves * pasillos * V("nave_largo_m")
    dist = long_bloque * V("overhead_recorrido")
    t_bloque = dist / v / 60.0
    utiles = aut_h * 60 * (1 - V("reserva_bateria"))
    transito = 2 * dist_base / V("velocidad_transito_m_s") / 60.0
    neta = max(utiles - transito, 0.0)
    bl_sesion = neta / t_bloque
    vent = V("ventana_noche_h") * 60
    if modo == "1":
        ses = 1
    elif modo == "A":
        ses = math.floor((vent + V("carga_min")) / (utiles + V("carga_min")))
    else:  # "B": batería de repuesto, cambio manual
        ses = math.floor((vent + V("cambio_bateria_min")) / (utiles + V("cambio_bateria_min")))
    bl_noche = ses * bl_sesion
    noches = bloques / bl_noche if bl_noche > 0 else math.inf
    return dict(v=v, aut_h=aut_h, modo=modo, camas=camas, pasillos=pasillos, long_bloque=long_bloque, dist_bloque=dist,
                t_bloque=t_bloque, utiles=utiles, transito=transito, neta=neta, bl_sesion=bl_sesion, ses=ses,
                bl_noche=bl_noche, noches=noches, ha_noche=bl_noche * V("area_bloque_ha"),
                ha_semana=bl_noche * V("area_bloque_ha") * 7, long_ha=naves * pasillos * V("nave_largo_m") / V("area_bloque_ha"),
                m_finca=long_bloque * bloques, horas_vuelta=t_bloque * bloques / 60)


CAP_PES = capacidad(v=0.4, aut_h=1.0, modo="A")
CAP_BASE = capacidad()
CAP_OPT = capacidad(v=0.8, aut_h=2.0, modo="B")
SESIONES_BASE = CAP_BASE["ses"]

# Persona: jornadas por vuelta completa
b_lo, b_hi = V("monitoreo_bloques_persona")
d_lo, d_hi = V("monitoreo_dias_persona")
bloques_f = V("bloques_finca")
JORNADAS_VUELTA_MIN = bloques_f / b_hi * d_lo
JORNADAS_VUELTA_MAX = bloques_f / b_lo * d_hi
JORNADAS_VUELTA_MED = bloques_f / ((b_lo + b_hi) / 2) * ((d_lo + d_hi) / 2)
BLOQUES_DIA_PERSONA = (b_lo / d_hi, b_hi / d_lo)

# ---- suscripción: costos de servir y precios --------------------------------------
bat_ratio = K_ULTRA["lineas"][1]["puesto_cop"] / K_ULTRA["lineas"][1]["cant"]  # COP puesto por batería
CICLOS_ANIO = V("noches_operacion_anio") * SESIONES_BASE
BAT_ANIO = CICLOS_ANIO / V("vida_bateria_ciclos")
COSTO_NUBE = V("nube_usd_anio") * TRM
COSTO_SOPORTE = V("ingeniero_soporte_cop_mes") * 12 / V("fincas_por_ingeniero")
COSTO_SUB_SOPORTE = COSTO_NUBE + COSTO_SOPORTE
COSTO_BAT = BAT_ANIO * bat_ratio
COSTO_REPUESTOS = V("repuestos_frac_hw") * K_ULTRA["hw_puesto"]
COSTO_SUB_CONS = COSTO_BAT + COSTO_REPUESTOS
precio_sub = lambda c: c / (1 - V("margen_min"))
PRECIO_SUB_SOPORTE = precio_sub(COSTO_SUB_SOPORTE)
PRECIO_SUB_CONS = precio_sub(COSTO_SUB_CONS)
# Se redondea hacia arriba a múltiplos de 0,5 M COP para presentar
redond = lambda x: math.ceil(x / 0.5e6) * 0.5e6
PRECIO_SUB_SOPORTE_R = redond(PRECIO_SUB_SOPORTE)
PRECIO_SUB_CONS_R = redond(PRECIO_SUB_CONS)
PRECIO_SUB_TOTAL = PRECIO_SUB_SOPORTE_R + PRECIO_SUB_CONS_R
COSTO_SUB_TOTAL = COSTO_SUB_SOPORTE + COSTO_SUB_CONS
MARGEN_SUB = 1 - COSTO_SUB_TOTAL / PRECIO_SUB_TOTAL

# ---- ingreso anual de AGRAR con 10 proyectos ----------------------------------------
N = V("proyectos_anio")
PRECIO = K_ULTRA["precio"]
COSTO = K_ULTRA["costo"]
ANIOS = []
ret = V("retencion_suscripcion")
for t in range(1, 6):
    activas = sum(N * ret ** (t - k - 1) for k in range(1, t))  # suscripción desde el año siguiente a la instalación
    ing_p = N * PRECIO
    cos_p = N * COSTO
    ing_s = activas * PRECIO_SUB_TOTAL
    cos_s = activas * COSTO_SUB_TOTAL
    ANIOS.append(dict(anio=t, proyectos=N, activas=activas, ing_proy=ing_p, ing_sub=ing_s, ing=ing_p + ing_s,
                      mb=(ing_p - cos_p) + (ing_s - cos_s), mb_pct=((ing_p - cos_p) + (ing_s - cos_s)) / (ing_p + ing_s)))

# ----------------------------------------------------------------------------
# 3. Cliente final
# ----------------------------------------------------------------------------
ESC_CULTIVO = [
    ("Conservador", V("rend_t_ha_cons"), V("precio_usd_kg_cons")),
    ("Central", V("rend_t_ha_central"), V("precio_usd_kg_central")),
    ("Alto", V("rend_t_ha_central"), V("precio_usd_kg_alto")),
]


def costos_anuales_cliente(ha, trm=TRM, kit_=None):
    """Costos recurrentes del cliente (COP/año)."""
    k = kit_ or K_ULTRA
    n = k["n"]
    sub = (PRECIO_SUB_TOTAL if n == 1 else
           redond(precio_sub(COSTO_SUB_SOPORTE + n * COSTO_SUB_CONS)))
    operador = (V("operador_robot_min_dia") * 365 / 60) * n * (V("jornal_usd") / 8) * trm
    falsas = V("falsas_alarmas_ha_anio") * ha * V("costo_falsa_alarma_usd") * trm
    return dict(sub=sub, operador=operador, falsas=falsas, total=sub + operador + falsas)


def horas_ahorro_cop(trm=TRM, jornal=None, vueltas=None):
    jornal = jornal or V("jornal_usd")
    vueltas = vueltas or V("vueltas_anio")
    jornadas = JORNADAS_VUELTA_MED * vueltas * V("fraccion_monitoreo_sustituida")
    return dict(jornadas=jornadas, cop=jornadas * jornal * trm)


def cliente(ha, rend, precio_kg, delta_pts, trm=TRM, kit_=None, iva_cliente=False, falsas=True,
            jornal=None, vueltas=None):
    k = kit_ or K_ULTRA
    inv = k["precio"] * ((1 + V("iva")) if iva_cliente else 1.0)
    valor = ha * rend * 1000 * precio_kg * trm
    ben_p = delta_pts / 100.0 * valor
    h = horas_ahorro_cop(trm, jornal, vueltas)
    c = costos_anuales_cliente(ha, trm, k)
    costos = c["total"] - (0 if falsas else c["falsas"])
    neto = ben_p + h["cop"] - costos
    pb = inv / neto * 12 if neto > 0 else math.inf
    return dict(ha=ha, valor=valor, ben_perdida=ben_p, ben_horas=h["cop"], jornadas=h["jornadas"], costos=costos,
                sub=c["sub"], operador=c["operador"], falsas=c["falsas"] if falsas else 0.0, neto=neto, inversion=inv,
                payback_meses=pb, roi_anual=neto / inv)


def puntos_para_payback(ha, rend, precio_kg, meses=24, trm=TRM, kit_=None, falsas=True):
    k = kit_ or K_ULTRA
    valor = ha * rend * 1000 * precio_kg * trm
    h = horas_ahorro_cop(trm)
    c = costos_anuales_cliente(ha, trm, k)
    costos = c["total"] - (0 if falsas else c["falsas"])
    neto_req = k["precio"] / (meses / 12.0)
    return (neto_req + costos - h["cop"]) / valor * 100.0


PUNTOS = V("puntos_evitados")
CLI_GRID = []  # filas largas para CSV
for nom, rend, pk in ESC_CULTIVO:
    for ha in (20.0, 22.5, 25.0):
        for d in PUNTOS:
            r = cliente(ha, rend, pk, d)
            CLI_GRID.append((nom, rend, pk, ha, d, r))

# sensibilidades adicionales
SENS = []
for etiqueta, kw in [
    ("Referencia (central, 22,5 ha, Ultra, jornal 19)", {}),
    ("Sin falsas alarmas", dict(falsas=False)),
    ("Jornal formal 23,82 USD", dict(jornal=23.82)),
    ("Vueltas de monitoreo semanales (52/año)", dict(vueltas=52)),
    ("Vueltas mensuales (12/año)", dict(vueltas=12)),
    ("Cliente no recupera IVA (inversión +19 %)", dict(iva_cliente=True)),
    ("D1 EDU", dict(kit_=K_EDU)),
    ("2 robots D1 Ultra", dict(kit_=kit("ultra", n=2))),
    ("Kit en escenario ADVERSO de AGRAR", dict(kit_=kit(**ADV))),
    ("TRM 3.900 (cosecha y kit se recalculan)", dict(trm=PAR["trm_cop_usd"]["hi"], kit_=kit("ultra", trm=PAR["trm_cop_usd"]["hi"]))),
    ("TRM 3.048 (cosecha y kit se recalculan)", dict(trm=PAR["trm_cop_usd"]["lo"], kit_=kit("ultra", trm=PAR["trm_cop_usd"]["lo"]))),
]:
    for d in (1.0, 2.0):
        r = cliente(22.5, V("rend_t_ha_central"), V("precio_usd_kg_central"), d, **kw)
        SENS.append((etiqueta, d, r))

# ----------------------------------------------------------------------------
# 5. Matriz de alternativas
# ----------------------------------------------------------------------------
CRITERIOS = ["Anticipa", "Ubica cama y ve arbusto", "Costo", "Encaje con la operación", "Robustez", "Registro"]
PESOS6 = [20, 20, 20, 15, 15, 10]
K_X2 = kit("ultra", fob_robot=V("fob_x2_ultra"), peso_robot=V("peso_x2"))
K_AMIGA = kit("ultra", fob_robot=V("fob_amiga"), peso_robot=V("peso_amiga"))
ALTS = ["A D1 Ultra solo", "B Red fija (ya existe en AGRAR)", "C Kit en aspersora", "D Humanoide X2 Ultra",
        "E Ruedas", "F Híbrido (PLC de AGRAR + D1)"]
ALT_COD = ["A", "B", "C", "D", "E", "F"]
PUNT = {
    "A": [3, 5, 3, 3, 3, 4],
    "B": [5, 1, 5, 5, 4, 2],
    "C": [2, 3, 4, 2, 3, 3],
    "D": [2, 4, 1, 1, 1, 4],
    "E": [3, 4, 2, 2, 2, 4],
    "F": [5, 5, 3, 5, 4, 5],
}
ESCAL = {"A": 2, "B": 4, "C": 3, "D": 1, "E": 2, "F": 4}
JUST = {
    "A": [
        "Visita por calendario; el T/HR a bordo solo mide en el instante de la ronda, sin vigilancia continua entre rondas.",
        "Cámara a la altura del arbusto y posición nave/cama conocida; ve daño de trips y polvo/mildiu como pidió el mentor.",
        "El kit cabe en 90-110 M, pero sin el PLC debe recorrer todo (vuelta de ~7 noches) y repite sensores que AGRAR ya tiene.",
        "Compatible con protocolos abiertos de AGRAR, pero ignora los PLC instalados: sin la red no sabe adónde ir primero.",
        "Sin ROS, IP54, batería de 1-2 h, línea de vista y reparación en fábrica (7 días hábiles); un solo punto de falla.",
        "Guarda cama + T/HR + foto y reenvía por LoRa o al volver a base; sin serie continua entre rondas."],
    "B": [
        "El modelo predictivo de AGRAR corre en el PLC con T/HR continuos por bloque: anticipa Botrytis y Alternaria de noche.",
        "Resuelve por bloque, no por cama, y no ve el arbusto: el mentor dijo que mildiu 'solo se sabe viéndolo'.",
        "Costo incremental ~0: la red ya existe (PLC por bloque); es la línea base del cliente.",
        "Es el producto de AGRAR: mismos PLC, LoRaWAN/Modbus y base de datos; sin cambios operativos.",
        "Sensores fijos sin partes móviles y ya probados por AGRAR; sufren por calibración y deriva.",
        "Serie T/HR continua por bloque, pero sin foto ni cama: no sirve de evidencia visual del daño."],
    "C": [
        "Solo ve cuando alguien asperja y AGRAR no asperja; llega después de la aplicación, no antes.",
        "La aspersora pasa por las camas, pero a la hora de aplicación (6-14 h) y en invernaderos de 6,8 m puede ser bomba de espalda (NO VERIFICADO).",
        "Kit barato (~5.700 USD en finanzas.md), aunque AGRAR tendría que integrarlo a equipos de terceros.",
        "AGRAR no hace aspersión: el manejo fitosanitario es del agrónomo de cada finca; no es su cliente ni su canal.",
        "Sin robot que falle, pero depende de que cada finca use el mismo tipo de aspersora (un soporte por modelo).",
        "Registra cama si hay GPS/marcadores, pero solo en días de aplicación."],
    "D": [
        "Misma función de patrulla que A con menor velocidad (0,4 m/s) y autonomía: cubre menos bloques por noche.",
        "A altura de humanoide ve el arbusto, pero con racimos colgando en pasillos estrechos puede dañar el fruto.",
        f"X2 Ultra a 39.999 USD FOB: con la misma estructura de costo el proyecto saldría en ~{K_X2['precio']/1e6:,.0f} M COP, muy fuera de 90-110 M.",
        "Plataforma de propósito general sin historial en invernadero; no encaja con el negocio de automatización de AGRAR.",
        "Sin historial en campo húmedo, baterías cortas y precio sin verificar; riesgo alto de caída.",
        "Puede registrar cama y T/HR, pero sin ROS ni ruta validada para ello."],
    "E": [
        "Patrulla sin red: misma limitación que A, con menor agilidad para cambiar de nave.",
        "Con mástil ve el arbusto; solo si el pasillo admite el ancho de la plataforma (a veces hay que pasar de lado).",
        f"Amiga ~22.500 USD FOB: con la misma estructura de costo el proyecto saldría en ~{K_AMIGA['precio']/1e6:,.0f} M COP, sobre el presupuesto.",
        "Pasillos de 6,8 m con 2-3 camas y plantas hacia el pasillo; la plataforma de ~250 kg pisa maceta y fruto.",
        "Terreno firme necesario; pesa ~250 kg con embalaje y es difícil de reparar/mover entre naves.",
        "Registra bien (cámara y T/HR fijos), pero la ruta por naves no está validada."],
    "F": [
        "El PLC de AGRAR marca el riesgo (humedad/temperatura) y el robot patrulla primero los bloques en riesgo.",
        "El robot confirma visualmente en la cama exacta, con posición y T/HR en el punto del hallazgo.",
        "Mismo kit que A (~100 M COP, dentro de 90-110 M) y sin costo extra de red; el payback < 2 años exige evitar ~1 punto (caso central) a ~1,8 (conservador).",
        "Usa lo que AGRAR ya vende (PLC, LoRaWAN/Modbus), se vende a los mismos grupos y patrulla de noche/amanecer.",
        "Si el robot falla (reparación de ~7 días hábiles) la red de PLC sigue protegiendo; el robot sigue siendo sin ROS e IP54.",
        "Cama + T/HR + foto del robot, más la serie continua del PLC: el registro más completo."],
}
JUST_ESC = {
    "A": "Un robot por finca, sin red para priorizar; logística de baterías y reparación; cuesta más por ha en fincas pequeñas.",
    "B": "Sirve a cualquier tamaño y cultivo con costo marginal bajo; AGRAR ya la vende (40-60 ventiladores/mes), pero no genera etiquetas visuales.",
    "C": "Bajo CAPEX y sin logística de robot, pero depende del equipo de aspersión de cada finca.",
    "D": "Alto costo por finca, plataforma de propósito general y precio sin verificar: no se puede vender a muchos productores.",
    "E": "Plataforma pesada que exige terreno firme y pasillos anchos; costo por ha alto en fincas pequeñas.",
    "F": "Menú: red en todas las fincas (ya instalada) y robot donde se paga; efecto de red de datos más fuerte. Baja a 2 si se vende como 'un robot por finca'.",
}


def totales(pesos, punt):
    """total = suma(puntaje x peso) / 5 (pesos que suman 100 -> escala 0-100)."""
    return {a: sum(s * w for s, w in zip(punt[a], pesos)) / 5.0 for a in ALT_COD}


def pesos7(pesos_costo=None):
    """Escalabilidad 15 % y los otros seis x 0,85."""
    return [w * 0.85 for w in PESOS6] + [15.0]


PUNT7 = {a: PUNT[a] + [ESCAL[a]] for a in ALT_COD}
T6 = totales(PESOS6, PUNT)
T7 = totales(pesos7(), PUNT7)
# sensibilidad: costo al 30 % (los otros se reescalan proporcionalmente)
resto6 = sum(PESOS6) - PESOS6[2]
P6_C30 = [w * (70.0 / resto6) if i != 2 else 30.0 for i, w in enumerate(PESOS6)]
T6_C30 = totales(P6_C30, PUNT)
w7 = pesos7()
resto7 = sum(w7) - w7[2]
P7_C30 = [w * (70.0 / resto7) if i != 2 else 30.0 for i, w in enumerate(w7)]
T7_C30 = totales(P7_C30, PUNT7)
# sensibilidad del documento (20/15/30/15/10/10)
P6_DOC = [20, 15, 30, 15, 10, 10]
T6_DOC = totales(P6_DOC, PUNT)


def barrido(n_crit, punt):
    """Pesos múltiplos de 5, mínimo 5, suma 100. Devuelve (n, F primero, B > F, A > F)."""
    total = 0
    f_prim = 0
    b_gt_f = 0
    paso = 5
    unidades = 100 // paso
    for comp in itertools.product(range(1, unidades), repeat=n_crit - 1):
        ultimo = unidades - sum(comp)
        if ultimo < 1:
            continue
        w = [c * paso for c in comp] + [ultimo * paso]
        t = totales(w, punt)
        total += 1
        if max(t, key=t.get) == "F":
            f_prim += 1
        if t["B"] > t["F"]:
            b_gt_f += 1
    return total, f_prim, b_gt_f


BAR6 = barrido(6, PUNT)
BAR7 = barrido(7, PUNT7)

# ----------------------------------------------------------------------------
# 6. Puente de costo/ha del híbrido
# ----------------------------------------------------------------------------


def leer_finanzas():
    ruta = os.path.join(FIN, "tabla_final_20ha.csv")
    try:
        with open(ruta, encoding="utf-8") as fh:
            filas = {r["opcion"]: r for r in csv.DictReader(fh)}
        return float(filas["F"]["costo_ha_anio_usd"]), float(filas["A"]["costo_ha_anio_usd"])
    except Exception:
        return 722.0, 820.0


COSTO_F_FIN, COSTO_A_FIN = leer_finanzas()
# Descomposición de F en 20 ha (verificacion-finanzas-robots-documento.md §2, cadena de F)
F_CAPEX, F_OPEX = 17489.14, 8615.0
RED_CAPEX, RED_OPEX = 6338.01, 2600.0  # nodos + gateway + instalación; OPEX nodos
F_FALSAS = 3000.0
VIDA = V("vida_util_anios")


def puente():
    pasos = []
    c0 = (F_CAPEX / VIDA + F_OPEX) / 20
    pasos.append(("F del modelo de finanzas (20 ha: 1 D1 + 20 nodos + gateway + mástil)", c0))
    c1 = ((F_CAPEX - RED_CAPEX) / VIDA + (F_OPEX - RED_OPEX)) / 20
    pasos.append(("(-) Quitar la red nueva: en AGRAR el PLC por bloque ya existe", c1))
    precio_usd = K_ULTRA["precio"] / TRM
    c2 = (precio_usd / VIDA + (F_OPEX - RED_OPEX)) / 20
    pasos.append(("(+) Pagar el precio de AGRAR (integración, software, base de carga y margen 40 %) en vez del equipo puesto en finca", c2))
    sub_usd = PRECIO_SUB_TOTAL / TRM
    oper_usd = costos_anuales_cliente(20.0)["operador"] / TRM
    c3 = (precio_usd / VIDA + sub_usd + oper_usd + F_FALSAS) / 20
    pasos.append(("(+/-) Cambiar nube + mantenimiento del modelo por suscripción + consumibles y operario", c3))
    ha = V("ha_finca")
    cc = costos_anuales_cliente(ha)
    c4 = (K_ULTRA["precio"] / VIDA + cc["total"]) / ha / TRM
    pasos.append(("(-) Diluir en 22,5 ha en vez de 20 ha (resultado final con falsas alarmas)", c4))
    c5 = (K_ULTRA["precio"] / VIDA + cc["total"] - cc["falsas"]) / ha / TRM
    pasos.append(("Mismo resultado sin falsas alarmas", c5))
    return pasos


PUENTE = puente()
COSTO_HA_FINAL_USD = PUENTE[4][1]
COSTO_HA_FINAL_SINFA_USD = PUENTE[5][1]
COSTO_HA_FINAL_COP = COSTO_HA_FINAL_USD * TRM

# ----------------------------------------------------------------------------
# Salidas CSV
# ----------------------------------------------------------------------------


def escribir_csvs():
    # parámetros
    filas = []
    for k, d in PAR.items():
        filas.append((k, d["v"], d["lo"], d["hi"], d["tipo"], d["nota"]))
    csv_out("parametros.csv", ["parametro", "base", "pesimista_o_min", "optimista_o_max", "tipo", "fuente_o_nota"], filas)

    # BOM
    for nombre, k in (("bom_d1_ultra.csv", K_ULTRA), ("bom_d1_edu.csv", K_EDU)):
        filas = []
        for l in k["lineas"]:
            filas.append((l["cat"], l["nombre"], l["cant"], l["origen"], l.get("fob"), l.get("fob_total_usd"),
                          round(l["puesto_cop"]), round(l["iva_cop"]), l["tipo"], l["nota"]))
        for s in k["servicios"]:
            filas.append((s["cat"], s["nombre"], 1, "servicio", None, None, round(s["cop"]), 0, s["tipo"], s["nota"]))
        filas.append(("Ingeniería", "Viáticos y transporte a la finca", 1, "servicio", None, None, round(k["viaticos"]), 0, "SUPUESTO", ""))
        filas.append(("Ingeniería", "Amortización del desarrollo base (NRE)", 1, "servicio", None, None, round(k["nre"]), 0, "SUPUESTO", "64 M COP / 30 proyectos"))
        filas.append(("Provisión", "Garantía y contingencia (5 % del hardware)", 1, "provisión", None, None, round(k["garantia"]), 0, "SUPUESTO", ""))
        filas.append(("TOTAL", "Costo de AGRAR sin IVA", None, "", None, None, round(k["costo_sin_iva"]), round(k["iva_hw"]), "", "IVA de importación y compras locales aparte"))
        filas.append(("TOTAL", f"Precio de venta con margen {int(V('margen_min')*100)} %", None, "", None, None, round(k["precio"]), None, "", "Antes de IVA"))
        csv_out(nombre, ["categoria", "item", "cantidad", "origen", "fob_usd_unitario", "fob_usd_total", "costo_puesto_cop_sin_iva", "iva_cop", "tipo", "nota"], filas)

    # AGRAR variantes
    filas = []
    for nom, k in FILAS_PRECIO:
        filas.append((nom, round(k["fob_tot"], 2), round(k["factor_import"], 3), round(k["costo"]), round(k["precio"]),
                      round(k["precio_con_iva"]), round(1 - k["costo"] / k["precio"], 3), cabe(k["precio"])))
    csv_out("agrar_precio_variantes.csv", ["escenario", "fob_import_usd", "factor_importacion", "costo_agrar_cop", "precio_cop_sin_iva",
                                            "precio_cop_con_iva", "margen_bruto", "cabe_90_110M"], filas)
    csv_out("agrar_recortes.csv", ["paso", "costo_cop", "precio_cop", "ahorro_en_precio_cop"],
            [(a, round(b), round(c), round(d)) for a, b, c, d in RECORTES])
    csv_out("agrar_recortes_desde_base.csv", ["palanca", "ahorro_en_precio_cop"], [(a, round(b)) for a, b in RECORTES_BASE])
    csv_out("agrar_suscripcion.csv", ["concepto", "costo_cop_anio", "precio_cop_anio"],
            [("Software + soporte (nube + soporte remoto)", round(COSTO_SUB_SOPORTE), PRECIO_SUB_SOPORTE_R),
             ("Consumibles (baterías + repuestos)", round(COSTO_SUB_CONS), PRECIO_SUB_CONS_R),
             ("TOTAL", round(COSTO_SUB_TOTAL), PRECIO_SUB_TOTAL)])
    csv_out("agrar_anual_10proyectos.csv",
            ["anio", "proyectos_nuevos", "suscripciones_activas", "ingreso_proyectos_cop", "ingreso_suscripcion_cop", "ingreso_total_cop",
             "margen_bruto_cop", "margen_bruto_pct"],
            [(a["anio"], a["proyectos"], round(a["activas"], 1), round(a["ing_proy"]), round(a["ing_sub"]), round(a["ing"]),
              round(a["mb"]), round(a["mb_pct"], 3)) for a in ANIOS])

    # cliente
    csv_out("cliente_payback.csv",
            ["escenario", "rend_t_ha", "precio_usd_kg", "ha", "puntos_evitados", "valor_cosecha_cop", "beneficio_perdida_cop",
             "ahorro_horas_cop", "costos_anuales_cop", "neto_anual_cop", "inversion_cop", "payback_meses", "cumple_menos_24m"],
            [(nom, rend, pk, ha, d, round(r["valor"]), round(r["ben_perdida"]), round(r["ben_horas"]), round(r["costos"]),
              round(r["neto"]), round(r["inversion"]), "" if math.isinf(r["payback_meses"]) else round(r["payback_meses"], 1),
              "sí" if r["payback_meses"] < 24 else "no") for nom, rend, pk, ha, d, r in CLI_GRID])
    csv_out("cliente_sensibilidad.csv",
            ["caso", "puntos_evitados", "beneficio_perdida_cop", "ahorro_horas_cop", "costos_cop", "neto_cop", "inversion_cop", "payback_meses"],
            [(e, d, round(r["ben_perdida"]), round(r["ben_horas"]), round(r["costos"]), round(r["neto"]), round(r["inversion"]),
              "" if math.isinf(r["payback_meses"]) else round(r["payback_meses"], 1)) for e, d, r in SENS])
    filas = []
    for nom, rend, pk in ESC_CULTIVO:
        for ha in (20.0, 22.5, 25.0):
            filas.append((nom, ha, round(puntos_para_payback(ha, rend, pk), 2), round(puntos_para_payback(ha, rend, pk, 18), 2),
                          round(puntos_para_payback(ha, rend, pk, 12), 2)))
    csv_out("cliente_puntos_equilibrio.csv", ["escenario", "ha", "puntos_para_24_meses", "puntos_para_18_meses", "puntos_para_12_meses"], filas)

    # capacidad
    filas = []
    for et, c in (("Pesimista (0,4 m/s; 1,0 h; carga 1 h)", CAP_PES), ("Base (0,5 m/s; 1,5 h; carga 1 h)", CAP_BASE),
                  ("Optimista (0,8 m/s; 2,0 h; batería de repuesto)", CAP_OPT)):
        filas.append((et, c["v"], c["aut_h"], c["modo"], round(c["long_bloque"]), round(c["dist_bloque"]), round(c["t_bloque"], 1),
                      round(c["utiles"], 1), round(c["transito"], 1), round(c["bl_sesion"], 2), c["ses"], round(c["bl_noche"], 2),
                      round(c["noches"], 1), round(c["ha_semana"], 1), round(c["horas_vuelta"], 1)))
    csv_out("capacidad.csv", ["escenario", "velocidad_m_s", "autonomia_h", "modo_carga", "m_pasillo_bloque", "m_recorridos_bloque",
                              "min_por_bloque", "min_utiles_sesion", "min_transito_sesion", "bloques_por_sesion", "sesiones_noche",
                              "bloques_por_noche", "noches_vuelta_40_bloques", "ha_por_semana", "horas_caminando_vuelta"], filas)
    filas = []
    for v in (0.4, 0.5, 0.6, 0.8):
        for aut in (1.0, 1.5, 2.0):
            for modo in ("1", "A", "B"):
                c = capacidad(v=v, aut_h=aut, modo=modo)
                filas.append((v, aut, modo, c["ses"], round(c["bl_noche"], 2), round(c["noches"], 1)))
    csv_out("capacidad_sensibilidad.csv", ["velocidad_m_s", "autonomia_h", "modo_carga(1=una sesión;A=carga 1 h;B=batería repuesto)",
                                           "sesiones_noche", "bloques_por_noche", "noches_vuelta_40_bloques"], filas)
    filas = []
    for camas in (2.0, 2.5, 3.0):
        c = capacidad(camas=camas)
        filas.append((camas, c["pasillos"], round(c["long_bloque"]), round(c["bl_noche"], 2), round(c["noches"], 1)))
    csv_out("capacidad_camas_por_nave.csv", ["camas_por_nave", "pasillos_por_nave", "m_pasillo_bloque", "bloques_por_noche", "noches_vuelta"], filas)

    # matriz
    csv_out("matriz_puntajes.csv", ["alternativa"] + CRITERIOS + ["Escalabilidad"],
            [[nom] + PUNT[a] + [ESCAL[a]] for a, nom in zip(ALT_COD, ALTS)])
    csv_out("matriz_totales.csv",
            ["alternativa", "total_6_criterios", "total_7_con_escalabilidad_15", "6_costo30", "7_costo30", "6_pesos_doc_20_15_30_15_10_10"],
            [(nom, round(T6[a], 2), round(T7[a], 2), round(T6_C30[a], 2), round(T7_C30[a], 2), round(T6_DOC[a], 2))
             for a, nom in zip(ALT_COD, ALTS)])
    filas = []
    for a, nom in zip(ALT_COD, ALTS):
        for i, c in enumerate(CRITERIOS):
            filas.append((nom, c, PUNT[a][i], JUST[a][i]))
        filas.append((nom, "Escalabilidad", ESCAL[a], JUST_ESC[a]))
    csv_out("matriz_justificaciones.csv", ["alternativa", "criterio", "puntaje", "justificacion"], filas)
    csv_out("matriz_barrido_pesos.csv", ["matriz", "combinaciones", "F_primero", "F_primero_pct", "B_sobre_F", "B_sobre_F_pct"],
            [("6 criterios", BAR6[0], BAR6[1], round(100 * BAR6[1] / BAR6[0], 1), BAR6[2], round(100 * BAR6[2] / BAR6[0], 1)),
             ("7 criterios (con escalabilidad)", BAR7[0], BAR7[1], round(100 * BAR7[1] / BAR7[0], 1), BAR7[2], round(100 * BAR7[2] / BAR7[0], 1))])

    # puente costo/ha
    csv_out("costo_ha_puente.csv", ["paso", "usd_ha_anio", "cop_millones_ha_anio"],
            [(n, round(c, 1), round(c * TRM / 1e6, 3)) for n, c in PUENTE])


# ----------------------------------------------------------------------------
# Gráfico opcional
# ----------------------------------------------------------------------------
def grafico():
    try:
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            sys.path.append(site.getusersitepackages())
            import matplotlib  # noqa: F401
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    xs = [0.25 * i for i in range(1, 17)]
    colores = {"Conservador": "#b45f06", "Central": "#2d6a4f", "Alto": "#1d4e89"}
    for nom, rend, pk in ESC_CULTIVO:
        ys = []
        for x in xs:
            pb = cliente(V("ha_finca"), rend, pk, x)["payback_meses"]
            ys.append(min(pb, 120))
        ax.plot(xs, ys, label=f"{nom} ({fe(rend,2)} t/ha, {fe(pk,0)} USD/kg)", color=colores[nom], lw=2)
    ax.axhline(24, color="#999", ls="--", lw=1)
    ax.text(3.9, 26, "límite 24 meses", ha="right", fontsize=8, color="#555")
    ax.set_xlabel("Puntos de pérdida evitados (puntos porcentuales de la cosecha)")
    ax.set_ylabel("Payback (meses)")
    ax.set_ylim(0, 120)
    ax.set_title("Payback del kit AGRAR en una finca de 22,5 ha", fontsize=11)
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(AQUI, "payback_vs_puntos.png"), dpi=140)
    plt.close(fig)
    return True


# ----------------------------------------------------------------------------
# RESUMEN.md
# ----------------------------------------------------------------------------
def resumen():
    L = []
    w = L.append
    ka = K_ULTRA
    ke = K_EDU
    pr = ka["precio"]
    ha = V("ha_finca")
    ref = {n: cliente(ha, r, p, 1.0) for n, r, p in ESC_CULTIVO}
    c_cent = cliente(ha, V("rend_t_ha_central"), V("precio_usd_kg_central"), 1.0)
    val_cent = c_cent["valor"]
    val_cons = ref["Conservador"]["valor"]
    pb = lambda r: "no paga" if math.isinf(r["payback_meses"]) else fe(r["payback_meses"], 0)

    w("# AGRAR: economía del kit robot (D1 + PLC existente)\n")
    w("Sabana Hack 2026, reto \"Berry Good Idea\". Fecha de corte: 2026-10-23. TRM usada: "
      f"**{fe(TRM,2)} COP/USD** (FUENTE: datos.gov.co, vigente el 23-oct-2026; rango 12 meses {fe(PAR['trm_cop_usd']['lo'],0)}-{fe(PAR['trm_cop_usd']['hi'],0)}). "
      "Todo sale de `agrar_roi.py` (`python3 -I agrar_roi.py`); los parámetros están en el dict `PAR` y en `parametros.csv` con su marca FUENTE / DERIVADO / SUPUESTO / NO VERIFICADO.\n")
    w("**Lectura rápida**\n")
    w(f"- El kit completo con D1 Ultra cuesta a AGRAR **{fm(ka['costo'])} M COP** puesto en Colombia y se vende a **{fm(pr)} M COP** con 40 % de margen: "
      f"**cabe en 90-110 M** (con IVA al cliente serían {fm(ka['precio_con_iva'])} M). Con el D1 EDU baja a {fm(ke['precio'])} M.")
    adv = [k for n, k in FILAS_PRECIO if n.startswith("ADVERSO")][0]
    w(f"- **El colchón es corto**: cada factor adverso por separado (D1 a precio de tienda 9.600, IVA como costo o TRM {fe(PAR['trm_cop_usd']['hi'],0)}) lleva el precio a 111-113 M, sobre el techo. "
      f"En el escenario adverso combinado sale a {fm(adv['precio'])} M; con EDU, horas -30 % y sin NRE/batería/garantía vuelve a ~{fm(RECORTES[-1][2])} M. "
      f"Una segunda unidad también lo saca del rango ({fm([k for n,k in FILAS_PRECIO if n.startswith('2 robots')][0]['precio'])} M).")
    w(f"- Con 10 proyectos al año AGRAR factura **{fm(N*pr,0)} M COP** y gana **{fm(N*(pr-ka['costo']),0)} M COP** de margen bruto; "
      f"la suscripción de {fm(PRECIO_SUB_TOTAL)} M COP/finca/año suma {fm(ANIOS[4]['ing_sub'],0)} M COP en el año 5.")
    w(f"- Para el cliente (finca de {fe(ha,1)} ha, caso central) el sistema paga en **~{pb(c_cent)} meses con 1 punto** de pérdida evitada (justo en el límite de 24) "
      f"y en {pb(cliente(ha, V('rend_t_ha_central'), V('precio_usd_kg_central'), 2.0))} meses con 2 puntos. "
      f"En el caso conservador necesita ~{fe(puntos_para_payback(ha, V('rend_t_ha_cons'), V('precio_usd_kg_cons')),1)} puntos para cumplir menos de 24 meses.")
    w(f"- **Un robot recorre las 40 parcelas en ~{fe(CAP_BASE['noches'],0)} noches** (rango {fe(CAP_OPT['noches'],0)}-{fe(CAP_PES['noches'],0)}), frente a "
      f"{fe(JORNADAS_VUELTA_MIN,0)}-{fe(JORNADAS_VUELTA_MAX,0)} jornadas de una persona con papel; no cubre los 40 bloques cada noche, así que depende de que el PLC priorice.")
    w(f"- **Cifra unificada del híbrido para el cliente: ~{fe(COSTO_HA_FINAL_USD,0)} USD/ha/año (~{fe(COSTO_HA_FINAL_COP/1e6,2)} M COP/ha/año)**, "
      f"{fe(COSTO_HA_FINAL_SINFA_USD,0)} USD sin contar falsas alarmas (sección 6).\n")

    # 1 BOM
    w("## 1. BOM del kit por finca\n")
    w(f"Un solo embarque consolidado desde México. Cadena de importación (igual a `finanzas/parametros.yaml`): flete {fe(V('flete_usd_kg'),0)} USD/kg + {fe(V('flete_fijo_usd'),0)} fijo, "
      f"seguro 1 %, arancel 5 % sobre CIF, IVA 19 % sobre CIF + arancel, agencia y transporte {fe(V('agencia_transporte_usd'),0)} USD. "
      f"Factor de importación calculado: **{fe(ka['factor_import_iva'],3)}** con IVA y {fe(ka['factor_import'],3)} sin IVA (previo: 1,35). Peso del embarque: {fe(ka['peso'],0)} kg. "
      "El IVA se muestra aparte porque se supone recuperable por AGRAR (SUPUESTO; consultar contador).\n")
    filas = []
    for l in ka["lineas"]:
        fob = "" if l["origen"] != "import" else fe(l["fob"], 0)
        filas.append((l["cat"], l["nombre"], l["cant"], "importado" if l["origen"] == "import" else "local", fob,
                      fm(l["puesto_cop"], 2), l["tipo"]))
    for s in ka["servicios"]:
        filas.append((s["cat"], s["nombre"], 1, "horas AGRAR", "", fm(s["cop"], 2), "SUPUESTO"))
    filas.append(("Ingeniería", "Viáticos y transporte", 1, "AGRAR", "", fm(ka["viaticos"], 2), "SUPUESTO"))
    filas.append(("Ingeniería", "Amortización del desarrollo base (64 M COP / 30 proyectos)", 1, "AGRAR", "", fm(ka["nre"], 2), "SUPUESTO"))
    filas.append(("Provisión", "Garantía y contingencia (5 % del hardware)", 1, "AGRAR", "", fm(ka["garantia"], 2), "SUPUESTO"))
    filas.append(("**TOTAL**", f"**Costo de AGRAR** ({fe(ka['horas'],0)} h de ingeniería)", "", "", fe(ka["fob_tot"], 0), f"**{fm(ka['costo'],2)}**", ""))
    filas.append(("**TOTAL**", "**Precio de venta (margen 40 %), antes de IVA**", "", "", "", f"**{fm(pr,2)}**", ""))
    w(tabla(["Categoría", "Ítem", "Cant.", "Origen", "FOB USD", "Costo puesto M COP (sin IVA)", "Marca"], filas))
    w("")
    w(f"Hardware puesto: {fm(ka['hw_puesto'],2)} M COP; servicios y provisión: {fm(ka['serv_cop'],2)} M COP ({fe(100*ka['serv_cop']/ka['costo_sin_iva'],0)} % del costo). "
      "**Las horas de ingeniería pesan casi tanto como el hardware**: el precio depende más de cuánto software y levantamiento se reutilice que del robot.\n")
    w("**Variante D1 EDU** (mismo kit, robot a 5.999 USD FOB; la ficha del EDU no declara IP y se supone IP54 según la guía SDK):\n")
    w(tabla(["Concepto", "D1 Ultra", "D1 EDU", "Diferencia"],
            [("FOB importado (USD)", fe(ka["fob_tot"], 0), fe(ke["fob_tot"], 0), fe(ke["fob_tot"] - ka["fob_tot"], 0)),
             ("Hardware puesto (M COP)", fm(ka["hw_puesto"], 2), fm(ke["hw_puesto"], 2), fm(ke["hw_puesto"] - ka["hw_puesto"], 2)),
             ("Costo de AGRAR (M COP)", fm(ka["costo"], 2), fm(ke["costo"], 2), fm(ke["costo"] - ka["costo"], 2)),
             ("Precio con 40 % (M COP)", fm(ka["precio"], 2), fm(ke["precio"], 2), fm(ke["precio"] - ka["precio"], 2))]))
    w("\nNota: el EDU no trae ROS ni cómputo libre, igual que el Ultra (guía SDK); la diferencia es de velocidad máxima, control remoto y acabado, y el equipo debe confirmar que su autonomía y carga útil bastan para el mástil con cámara.\n")

    # 2 AGRAR
    w("## 2. Economía de AGRAR\n")
    w("Margen = (precio − costo) / precio, es decir, margen bruto sobre el precio de venta (SUPUESTO de lectura del \"40 %\"). Precios antes de IVA.\n")
    filas = []
    for nom, k in FILAS_PRECIO:
        filas.append((nom, fm(k["costo"]), fm(k["precio"]), fm(k["precio_con_iva"]), cabe(k["precio"])))
    w(tabla(["Escenario", "Costo AGRAR (M COP)", "Precio 40 % (M COP)", "Con IVA 19 % (M COP)", "¿Cabe en 90-110 M?"], filas))
    w("")
    w(f"Para llegar a 110 M con margen del 40 %, el costo máximo es {fm(V('presupuesto_max_cop')*(1-V('margen_min')),1)} M COP; el costo base es {fm(ka['costo'],1)} M, "
      f"así que el colchón es de {fm(V('presupuesto_max_cop')*(1-V('margen_min'))-ka['costo'],1)} M COP de costo. Si los 90-110 M **incluyeran IVA**, el precio neto máximo sería "
      f"{fm(V('presupuesto_max_cop')/1.19,1)} M y el kit base ({fm(pr,1)} M) ya no cabría sin recortes.\n")
    w("**Qué recortar si no cabe.** Desde el escenario adverso, recortes en orden:\n")
    filas = [(a, fm(c, 2), fm(p, 2), fm(d, 2) if d else "", "sí" if p <= V("presupuesto_max_cop") else "no") for a, c, p, d in RECORTES]
    w(tabla(["Paso (acumulado)", "Costo (M COP)", "Precio (M COP)", "Ahorro del paso (M COP)", "¿≤ 110 M?"], filas))
    w("")
    w("Cuánto ahorra cada palanca desde el escenario **base** (en precio de venta):\n")
    w(tabla(["Palanca", "Ahorro en precio (M COP)"], [(a, fm(b)) for a, b in RECORTES_BASE]))
    w("")
    w("Lo que **no** se recorta: sensor T/HR y módulo LoRa (requisito del mentor) ni la cámara y el cómputo (el robot \"tiene que verlo\"). "
      "Con dos robots el precio sale del rango; la alternativa es 1 robot + patrulla priorizada por el PLC (sección 4) y un segundo robot como adicional.\n")
    w("**Ingreso y margen anual con 10 proyectos.** Suscripción desde el año siguiente a la instalación (el primer año va en garantía), retención 90 % (SUPUESTO).\n")
    w(tabla(["Año", "Proyectos nuevos", "Suscripciones activas", "Ingreso proyectos (M COP)", "Ingreso suscripción (M COP)", "Ingreso total (M COP)", "Margen bruto (M COP)", "Margen %"],
            [(a["anio"], a["proyectos"], fe(a["activas"], 1), fm(a["ing_proy"], 0), fm(a["ing_sub"], 0), fm(a["ing"], 0), fm(a["mb"], 0), fe(100 * a["mb_pct"], 0) + " %") for a in ANIOS]))
    w("")
    w(f"**Suscripción anual por finca** (ingreso recurrente, margen {fe(100*MARGEN_SUB,0)} % tras redondear al alza a múltiplos de 0,5 M COP):\n")
    w(tabla(["Plan", "Qué incluye", "Costo de servir (M COP/año)", "Precio (M COP/año)"],
            [("Software + soporte", f"Nube ({fe(V('nube_usd_anio'),0)} USD), actualizaciones de modelo y soporte remoto (1 ingeniero por {V('fincas_por_ingeniero')} fincas)", fm(COSTO_SUB_SOPORTE, 2), fm(PRECIO_SUB_SOPORTE_R, 1)),
             ("Consumibles", f"~{fe(BAT_ANIO,1)} baterías/año ({fe(CICLOS_ANIO,0)} ciclos / {V('vida_bateria_ciclos')}) y repuestos 4 % del hardware", fm(COSTO_SUB_CONS, 2), fm(PRECIO_SUB_CONS_R, 1)),
             ("**Total**", "", fm(COSTO_SUB_TOTAL, 2), f"**{fm(PRECIO_SUB_TOTAL, 1)}**")]))
    w(f"\nPor ha equivale a ~{fe(PRECIO_SUB_TOTAL/ha/TRM,0)} USD/ha/año para el cliente. El primer año va incluido (garantía). "
      "Es el ingreso que hace que el negocio no dependa de cerrar siempre proyectos nuevos; no incluye costos de estructura de AGRAR (solo margen bruto).\n")

    # 3 Cliente
    w("## 3. Economía del cliente final (finca de 20-25 ha)\n")
    w(f"Cálculo con {fe(ha,1)} ha (también en 20 y 25 ha en `cliente_payback.csv`). **Pérdida** = fracción del valor cosechado que se pierde por fitosanitarios; el mentor da 10-25 % y 30-40 % sin prevención. "
      "Lectura SUPUESTO: se aplica sobre el valor de lo cosechado. Rendimiento y precio son rangos, no puntos:\n")
    filas = []
    for nom, rend, pk in ESC_CULTIVO:
        v = ha * rend * 1000 * pk * TRM
        filas.append((nom, fe(rend, 2), fe(pk, 0), f"{fe(v/1e6,0)}", f"{fe(0.10*v/1e6,0)} - {fe(0.25*v/1e6,0)}", f"{fe(0.30*v/1e6,0)} - {fe(0.40*v/1e6,0)}"))
    w(tabla(["Escenario", "t/ha", "USD/kg", "Valor de cosecha (M COP/año)", "Pérdida 10-25 % (M COP)", "Sin prevención 30-40 % (M COP)"], filas))
    w("\nFuentes: 9,07 t/ha = EVA 2025 (FUENTE); 12 t/ha = Forbes 2026 (FUENTE); 6 USD/kg = FOB implícito (SUPUESTO); 8-10 USD/kg = Planasa vía Forbes (fuente interesada, SUPUESTO).\n")
    w(f"**Ahorro de horas de monitoreo.** Hoy una persona hace {fe(BLOQUES_DIA_PERSONA[0],1)}-{fe(BLOQUES_DIA_PERSONA[1],1)} bloques por jornada; una vuelta de {bloques_f} bloques son "
      f"{fe(JORNADAS_VUELTA_MIN,1)}-{fe(JORNADAS_VUELTA_MAX,1)} jornadas (medio: {fe(JORNADAS_VUELTA_MED,1)}). Con {V('vueltas_anio')} vueltas/año (quincenal, SUPUESTO), "
      f"el robot sustituye el {fe(100*V('fraccion_monitoreo_sustituida'),0)} % (SUPUESTO): {fe(horas_ahorro_cop()['jornadas'],0)} jornadas = **{fm(horas_ahorro_cop()['cop'])} M COP/año** "
      f"a {fe(V('jornal_usd'),0)} USD/jornal. Es un beneficio real pero pequeño (~{fe(100*horas_ahorro_cop()['cop']/c_cent['valor'],2)} % de la cosecha): "
      "**no justifica el sistema por sí solo**; lo justifica la pérdida evitada.\n")
    cc = costos_anuales_cliente(ha)
    w(f"**Costos anuales del cliente:** suscripción {fm(cc['sub'])} M + operario del robot ({fe(V('operador_robot_min_dia'),0)} min/día) {fm(cc['operador'],2)} M + falsas alarmas "
      f"({fe(V('falsas_alarmas_ha_anio'),0)}/ha x {fe(V('costo_falsa_alarma_usd'),0)} USD) {fm(cc['falsas'])} M = **{fm(cc['total'])} M COP/año**. Inversión inicial: {fm(pr)} M COP (precio antes de IVA).\n")
    w("**Beneficio neto anual y payback (meses)** según los puntos de pérdida que el sistema evita (neto = pérdida evitada + horas − costos anuales):\n")
    filas = []
    for d in PUNTOS:
        fila = [f"{fe(d,1)} pts"]
        for nom, rend, pk in ESC_CULTIVO:
            r = cliente(ha, rend, pk, d)
            fila.append(f"{fm(r['neto'],0)} M / **{pb(r)}** m")
        # reducción relativa respecto a pérdida del 15 %
        fila.append(f"{fe(100*d/15,0)} %")
        filas.append(fila)
    w(tabla(["Pérdida evitada", "Conservador: neto / payback", "Central: neto / payback", "Alto: neto / payback", "Reducción relativa si L = 15 %"], filas))
    w("")
    w("**Puntos mínimos para cumplir payback < 2 años** (22,5 ha):\n")
    filas = []
    for nom, rend, pk in ESC_CULTIVO:
        filas.append((nom, fe(puntos_para_payback(ha, rend, pk), 2), fe(puntos_para_payback(ha, rend, pk, 18), 2), fe(puntos_para_payback(ha, rend, pk, 12), 2),
                      fe(puntos_para_payback(ha, rend, pk, 24, falsas=False), 2)))
    w(tabla(["Escenario", "24 meses", "18 meses", "12 meses", "24 meses sin falsas alarmas"], filas))
    w("")
    w("**Sensibilidad (caso central, 22,5 ha, payback en meses):**\n")
    cas = {}
    for e, d, r in SENS:
        cas.setdefault(e, {})[d] = r
    filas = [(e, pb(v[1.0]), pb(v[2.0]), fm(v[1.0]["inversion"], 0)) for e, v in cas.items()]
    w(tabla(["Caso", "1 punto", "2 puntos", "Inversión (M COP)"], filas))
    w("")
    c20 = cliente(20.0, V("rend_t_ha_central"), V("precio_usd_kg_central"), 1.0)
    c25 = cliente(25.0, V("rend_t_ha_central"), V("precio_usd_kg_central"), 1.0)
    w(f"Por tamaño (central, 1 punto): 20 ha {pb(c20)} meses; 22,5 ha {pb(c_cent)}; 25 ha {pb(c25)}.\n")
    pc = {n: puntos_para_payback(ha, r, p) for n, r, p in ESC_CULTIVO}
    w(f"**¿Se cumple < 2 años?** Sí, si el sistema evita al menos {fe(pc['Alto'],1)} puntos (alto), {fe(pc['Central'],1)} (central) o {fe(pc['Conservador'],1)} (conservador, 9,07 t/ha y 6 USD/kg). "
      "Con 0,5 puntos no se cumple en ningún escenario. Honestidad sobre el dato: AGRAR **ya tiene** un modelo predictivo en el PLC, así que parte de esos puntos ya los captura la red; "
      "lo incremental del robot (ver el arbusto, ubicar la cama, T/HR en el punto) es **SUPUESTO y debe medirse en piloto con camas testigo**. Con 3 puntos el payback baja a ~"
      f"{pb(cliente(ha, V('rend_t_ha_central'), V('precio_usd_kg_central'), 3.0))} meses (central).\n")
    w("![Payback vs puntos](payback_vs_puntos.png)\n")

    # 4 Capacidad
    w("## 4. Capacidad: ¿un robot cubre 40 bloques?\n")
    w("**Geometría** (mentor: nave de 6,8 m x ~80 m, 2-3 camas por nave, camino central de 5-6 m). Una nave ocupa 544 m2; un bloque de 0,5 ha = 5.000 m2 / 544 = 9 naves (DERIVADO). "
      f"El robot camina los pasillos entre camas (pasillos = camas − 1; con 2,5 camas son 1,5 por nave; las plantas crecen hacia el pasillo). Longitud de pasillo por bloque: "
      f"{fe(CAP_BASE['long_bloque'],0)} m (rango {fe(capacidad(camas=2.0)['long_bloque'],0)}-{fe(capacidad(camas=3.0)['long_bloque'],0)} m); "
      f"con 30 % de sobrerrecorrido (giros, capturas) son {fe(CAP_BASE['dist_bloque'],0)} m por bloque, unos {fe(CAP_BASE['long_ha'],0)} m de pasillo por ha. "
      f"Una vuelta de 40 bloques son {fe(CAP_BASE['m_finca']/1000,1)} km de pasillo y ~{fe(CAP_BASE['horas_vuelta'],0)} h de caminata a {fe(V('velocidad_m_s'),1)} m/s. "
      "Si un bloque es de 1 ha el tiempo por ha es el mismo.\n")
    w(f"**Modelo de batería.** Autonomía {fe(CAP_BASE['aut_h'],1)} h (rango 1-2 h), reserva {fe(100*V('reserva_bateria'),0)} % -> {fe(CAP_BASE['utiles'],0)} min útiles; traslado base-bloque ida y vuelta "
      f"{fe(CAP_BASE['transito'],1)} min ({fe(V('dist_base_bloque_m'),0)} m a 1 m/s); ventana nocturna de {fe(V('ventana_noche_h'),0)} h. Modo A: el robot espera ~1 h de carga entre sesiones "
      f"(requiere base con carga automática, NO VERIFICADO, o una persona); modo B: batería de repuesto y cambio manual de 5 min.\n")
    filas = []
    for et, c in (("Pesimista", CAP_PES), ("**Base**", CAP_BASE), ("Optimista", CAP_OPT)):
        filas.append((et, f"{fe(c['v'],1)} m/s; {fe(c['aut_h'],1)} h; modo {c['modo']}", fe(c["t_bloque"], 0), fe(c["bl_sesion"], 2), c["ses"],
                      fe(c["bl_noche"], 1), fe(c["noches"], 1), fe(c["ha_semana"], 0)))
    w(tabla(["Escenario", "Velocidad; autonomía; carga", "Min por bloque", "Bloques por sesión", "Sesiones por noche", "Bloques por noche", "Noches por vuelta de 40", "ha por semana"], filas))
    w("")
    w("Con menos autonomía caben más sesiones de menor duración en la ventana (por eso el escenario pesimista tiene 5 sesiones y el base 4), pero el traslado a la base se come una parte mayor de cada una.\n")
    grid = []
    for v in (0.4, 0.5, 0.8):
        fila = [f"{fe(v,1)} m/s"]
        for modo in ("1", "A", "B"):
            c = capacidad(v=v, modo=modo)
            fila.append(f"{fe(c['bl_noche'],1)} / {fe(c['noches'],0)}")
        grid.append(fila)
    w("Sensibilidad a la velocidad y al modo de carga (autonomía 1,5 h; bloques por noche / noches por vuelta):\n")
    w(tabla(["Velocidad", "1 sesión por noche", "Modo A (carga 1 h)", "Modo B (batería de repuesto)"], grid))
    w("")
    w(f"**Frente a una persona:** {fe(BLOQUES_DIA_PERSONA[0],1)}-{fe(BLOQUES_DIA_PERSONA[1],1)} bloques por jornada, es decir {fe(JORNADAS_VUELTA_MIN,1)}-{fe(JORNADAS_VUELTA_MAX,1)} jornadas por vuelta de 40 bloques "
      f"(en papel, digitado después). El robot base hace {fe(CAP_BASE['bl_noche'],1)} bloques por noche: vuelta completa en ~{fe(CAP_BASE['noches'],0)} noches, "
      f"sin ocupar jornadas de operarios y con T/HR y posición en cada hallazgo. En 7 noches cubre ~{fe(CAP_BASE['ha_semana'],0)} ha/semana, dentro del rango de 16-36 ha por robot de ESCALABILIDAD §2.7.\n")
    w(f"**Respuesta:** un robot cubre una finca de 40 bloques **para una vuelta completa cada ~7 noches (3-12 según supuestos)** y para una ronda de riesgo de ~{fe(CAP_BASE['bl_noche'],0)} bloques por noche "
      f"({fe(100*CAP_BASE['bl_noche']/bloques_f,0)} % de la finca). No cubre los 40 bloques cada noche: si el cliente exige vuelta completa en ≤ 5 noches se necesitan {math.ceil(CAP_BASE['noches']/5)} robots, "
      "y la alternativa es priorizar con el PLC (sección 5, híbrido). Pendientes: el manual del D1 pide línea de vista (¿quién acompaña de noche?) y la carga automática no está verificada.\n")

    # 5 Matriz
    w("## 5. Matriz de alternativas recalculada\n")
    w("Pesos del equipo: Anticipa 20, Ubica cama y ve arbusto 20, Costo 20, Encaje 15, Robustez 15, Registro 10. Total = Σ(puntaje x peso) / 5 (escala 0-100). "
      "Versión de 7 criterios: Escalabilidad 15 % y los seis anteriores x 0,85 (17 / 17 / 17 / 12,75 / 12,75 / 8,5). "
      "Los puntajes cambian respecto a la matriz verificada (73/75/68/42/69/83) por el contexto nuevo: la red ya existe (costo de B y de la parte de red de F ~0), "
      "AGRAR no asperja (C), y los kits de D y E pasan del presupuesto.\n")
    cab = ["Alternativa"] + ["Anti.", "Ubica", "Costo", "Encaje", "Robust.", "Regist.", "Escal."] + ["Total 6 crit.", "Total 7 crit. (esc. 15 %)", "6, costo 30 %", "7, costo 30 %"]
    filas = []
    for a, nom in zip(ALT_COD, ALTS):
        filas.append([nom] + PUNT[a] + [ESCAL[a]] + [fe(T6[a], 1), fe(T7[a], 1), fe(T6_C30[a], 1), fe(T7_C30[a], 1)])
    w(tabla(cab, filas))
    w("")
    w(f"Sensibilidad \"costo al 30 %\": los demás pesos se reescalan proporcionalmente (6 criterios: {', '.join(fe(x,1) for x in P6_C30)}; "
      f"7 criterios: {', '.join(fe(x,1) for x in P7_C30)}). Con los pesos de sensibilidad del documento (20/15/30/15/10/10): "
      + "; ".join(f"{a} {fe(T6_DOC[a],1)}" for a in ALT_COD) + ".\n")
    mejor6 = max(T6, key=T6.get)
    mejor7 = max(T7, key=T7.get)
    w(f"**Lectura.** F queda primero ({fe(T6['F'],1)} en 6 criterios, {fe(T7['F'],1)} en 7, {fe(T6_C30['F'],1)} con costo al 30 %); B (la red existente) es segunda y por eso el híbrido se presenta como "
      "\"la red que AGRAR ya tiene + los ojos del robot\". Ojo: F incluye a B, así que casi siempre la supera; la matriz no prueba que el robot valga ~100 M, eso lo prueba el payback de la sección 3. "
      "Barrido de pesos (múltiplos de 5, mínimo 5): "
      f"6 criterios: F primero en {fe(100*BAR6[1]/BAR6[0],0)} % de {fe(BAR6[0],0)} combinaciones y B sobre F en {fe(100*BAR6[2]/BAR6[0],0)} %; "
      f"7 criterios: F primero en {fe(100*BAR7[1]/BAR7[0],0)} % de {fe(BAR7[0],0)} y B sobre F en {fe(100*BAR7[2]/BAR7[0],0)} %. "
      "B solo supera a F cuando casi todo el peso va a Costo y Encaje y casi nada a Ubica y Registro (en la matriz verificada anterior ocurría en el 25 %; ahora baja porque F gana en Encaje y Robustez por el contexto AGRAR y su red ya existe).\n")
    w("**Justificación de cada puntaje** (una línea por criterio):\n")
    for a, nom in zip(ALT_COD, ALTS):
        w(f"**{nom}**\n")
        for i, c in enumerate(CRITERIOS):
            w(f"- {c} = {PUNT[a][i]}: {JUST[a][i]}")
        w(f"- Escalabilidad = {ESCAL[a]}: {JUST_ESC[a]}")
        w("")
    w("Escalabilidad: puntajes de ESCALABILIDAD §10.2 (2/4/3/1/2/4), sin cambios.\n")

    # 6 costo/ha
    w("## 6. Cifra unificada de costo por ha del híbrido\n")
    w(f"**Usar: ~{fe(COSTO_HA_FINAL_USD,0)} USD/ha/año (~{fe(COSTO_HA_FINAL_COP/1e6,2)} M COP/ha/año) para el cliente de AGRAR en 22,5 ha**, con vida de 3 años en línea recta. "
      f"Incluye precio del proyecto ({fm(pr)} M COP), suscripción y consumibles ({fm(PRECIO_SUB_TOTAL)} M/año), operario y falsas alarmas. Sin falsas alarmas: ~{fe(COSTO_HA_FINAL_SINFA_USD,0)} USD/ha/año. "
      "Por separado, el precio de pago único es ~"
      f"{fe(pr/ha/TRM,0)} USD/ha (~{fm(pr/ha,1)} M COP/ha) y la parte recurrente ~{fe(PRECIO_SUB_TOTAL/ha/TRM,0)} USD/ha/año.\n")
    w("Cómo se relaciona con las cifras previas:\n")
    w(tabla(["Paso", "USD/ha/año"], [(n, fe(c, 0)) for n, c in PUENTE]))
    w("")
    w(f"- **430:** cifra del documento anterior al modelo de finanzas (híbrido sin falsas alarmas ni mantenimiento completo; era un costo, no un beneficio ni un precio). Queda **obsoleta**.\n"
      f"- **722:** costo del híbrido en el modelo de finanzas (20 ha) para un productor que **compra y arma todo**: 1 D1 + 20 nodos + gateway + falsas alarmas. Sigue válido para un cliente sin infraestructura (no AGRAR).\n"
      f"- **820:** opción A (D1 Ultra con mástil **sin red**, 2 robots por la cobertura semanal de 20 ha en filas de campo); no aplica al invernadero con pasillos más cortos y no es la oferta de AGRAR.\n"
      f"- **~{fe(COSTO_HA_FINAL_USD,0)}:** el híbrido de AGRAR para el cliente. Se quita la red nueva (−{fe(PUENTE[0][1]-PUENTE[1][1],0)} USD/ha), pero entran la ingeniería de integración y el software (que el modelo de finanzas no contaba), "
      f"la base de carga y el margen de 40 % dentro del precio, y la suscripción con consumibles reemplaza el mantenimiento genérico. El resultado queda ~{fe(100*(COSTO_HA_FINAL_USD/PUENTE[0][1]-1),0)} % sobre 722. "
      f"Las falsas alarmas ({fe(V('falsas_alarmas_ha_anio')*V('costo_falsa_alarma_usd'),0)} USD/ha) son la partida más incierta.\n"
      "- **520 USD/ha:** precio de servicio (RaaS) del modelo de negocio; es otro modelo y no se mezcla con esta cifra.\n")

    # 7 pitch
    w("## 7. Cinco frases para el pitch\n")
    d1 = cliente(ha, V("rend_t_ha_central"), V("precio_usd_kg_central"), 1.0)
    d2 = cliente(ha, V("rend_t_ha_central"), V("precio_usd_kg_central"), 2.0)
    w(f"1. \"AGRAR ya tiene los ojos ambientales en cada bloque, con PLC y sensores; nuestro robot es el par de ojos que va a la cama exacta donde el modelo marca riesgo y trae temperatura y humedad del punto del hallazgo.\"")
    w(f"2. \"El kit completo (D1 Ultra, cámara, cómputo, sensor T/HR, LoRa y base de carga) cuesta ~{fm(pr,0)} M COP, dentro de los 90-110 M del presupuesto, y deja a AGRAR el 40 % de margen que exige.\"")
    w(f"3. \"Un robot recorre las 40 parcelas en ~{fe(CAP_BASE['noches'],0)} noches, sin tocar la jornada de los operarios, frente a {fe(JORNADAS_VUELTA_MIN,0)}-{fe(JORNADAS_VUELTA_MAX,0)} jornadas de una persona con papel, y registra cada hallazgo digitalmente.\"")
    w(f"4. \"En una finca de {fe(ha,1)} ha que cosecha ~{fm(val_cent,0)} M COP al año, evitar 1 punto de pérdida paga el sistema en ~{pb(d1)} meses (el límite) y 2 puntos en ~{pb(d2)}; la meta es menos de 24.\"")
    w(f"5. \"Con 10 proyectos al año AGRAR factura ~{fm(N*pr,0)} M COP y suma una suscripción de ~{fm(PRECIO_SUB_TOTAL,0)} M COP por finca al año, que llega a ~{fm(ANIOS[4]['ing_sub'],0)} M COP en el año 5.\"\n")
    w("Cuidado en el pitch: los puntos de pérdida evitados y la sustitución de horas son SUPUESTOS a medir en piloto; la mejora que ya captura el modelo predictivo del PLC no es del robot.\n")

    # 8 pendientes
    w("## 8. Supuestos que más pesan y pendientes\n")
    w("- Cotización formal del D1 Ultra con entrega en Colombia (7.499 FOB hoja del equipo vs 9.600 en tienda) y de la batería de repuesto (450 USD NO VERIFICADO).\n"
      "- Horas de ingeniería (238 h) y costo de la hora (80.000 COP): son la mitad del costo. Medir con el primer proyecto.\n"
      "- IVA: confirmar con contador si AGRAR lo descuenta (base) y si los 90-110 M incluyen IVA.\n"
      "- Puntos de pérdida evitados (0,5-3), pérdida base L (10-25 %), rendimiento y precio: piloto con camas testigo.\n"
      "- Velocidad efectiva (0,4-0,8 m/s), autonomía con cámara y cómputo, carga automática en base, línea de vista del manual.\n"
      "- Geometría: pasillos por nave (camas − 1) y distancia a la base se deben medir en el levantamiento de cada finca.\n"
      "- Falsas alarmas toleradas por el cliente (pregunta abierta del mentor): 5/ha/año x 30 USD es el supuesto previo.\n"
      "- Clasificación arancelaria (5 % vs 0 %) y vida útil de 3 años del robot.\n")
    w("## 9. Archivos\n")
    w("`agrar_roi.py` (modelo y generador de este documento), `parametros.csv`, `bom_d1_ultra.csv`, `bom_d1_edu.csv`, `agrar_precio_variantes.csv`, `agrar_recortes.csv`, "
      "`agrar_recortes_desde_base.csv`, `agrar_suscripcion.csv`, `agrar_anual_10proyectos.csv`, `cliente_payback.csv`, `cliente_sensibilidad.csv`, `cliente_puntos_equilibrio.csv`, "
      "`capacidad.csv`, `capacidad_sensibilidad.csv`, `capacidad_camas_por_nave.csv`, `matriz_puntajes.csv`, `matriz_totales.csv`, `matriz_justificaciones.csv`, "
      "`matriz_barrido_pesos.csv`, `costo_ha_puente.csv`, `payback_vs_puntos.png`.\n")
    with open(os.path.join(AQUI, "RESUMEN.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main():
    escribir_csvs()
    ok = grafico()
    resumen()
    ka = K_ULTRA
    print(f"BOM Ultra: costo {ka['costo']/1e6:.1f} M, precio {ka['precio']/1e6:.1f} M, factor import {ka['factor_import']:.3f} sin IVA / {ka['factor_import_iva']:.3f} con IVA")
    print(f"X2: {K_X2['precio']/1e6:.0f} M; Amiga: {K_AMIGA['precio']/1e6:.0f} M")
    print(f"BOM EDU:   costo {K_EDU['costo']/1e6:.1f} M, precio {K_EDU['precio']/1e6:.1f} M")
    for n, k in FILAS_PRECIO:
        print(f"  {n}: {k['precio']/1e6:.1f} M  {cabe(k['precio'])}")
    print(f"Suscripción: costo {COSTO_SUB_TOTAL/1e6:.2f} M, precio {PRECIO_SUB_TOTAL/1e6:.1f} M, margen {MARGEN_SUB:.2f}")
    print(f"Capacidad base: {CAP_BASE['bl_noche']:.1f} bloques/noche, {CAP_BASE['noches']:.1f} noches; pes {CAP_PES['noches']:.1f}; opt {CAP_OPT['noches']:.1f}")
    print(f"Costo/ha final: {COSTO_HA_FINAL_USD:.0f} USD (sin FA {COSTO_HA_FINAL_SINFA_USD:.0f})")
    print("Matriz 6:", {a: round(v, 1) for a, v in T6.items()})
    print("Matriz 7:", {a: round(v, 1) for a, v in T7.items()})
    print("gráfico:", ok)


if __name__ == "__main__":
    main()
