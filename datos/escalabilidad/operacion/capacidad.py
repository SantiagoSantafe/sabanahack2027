"""Capacidad de inspeccion por robot y dimensionamiento de flota (rol operacion-escala).

Uso:  python3 -I capacidad.py
Salidas (misma carpeta): capacidad.csv, flota.csv, repuestos.csv

Cada parametro lleva su fuente o la marca SUPUESTO. Nada de este archivo es medicion de campo:
es aritmetica sobre supuestos declarados. El piloto de onboarding debe reemplazarlos.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, asdict
from pathlib import Path

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- geometria
# Densidad 5.000-5.500 plantas/ha (Asocolblue, citado en
# https://www.agronegocios.co/agricultura/las-exportaciones-de-arandanos-superaron-us-1-millon-durante-el-primer-semestre-3446716)
DENSIDAD_PLANTAS_HA = 5250          # punto medio del rango publicado
DIST_ENTRE_PLANTAS_M = 0.75         # SUPUESTO (referencia Argentina del prompt de simulacion, sin verificar en Colombia)
SOBRECOSTO_CABECERAS = 0.08         # SUPUESTO: giros y tramos de cabecera = 8 % del recorrido

M_CAMA_POR_HA = DENSIDAD_PLANTAS_HA * DIST_ENTRE_PLANTAS_M            # ~3.938 m de cama por ha
M_RECORRIDO_POR_HA = M_CAMA_POR_HA * (1 + SOBRECOSTO_CABECERAS)      # una pasada por pasillo ve las 2 caras vecinas


@dataclass
class Escenario:
    robot: str
    escenario: str
    v_insp_m_s: float        # velocidad efectiva de inspeccion, con paradas (SUPUESTO)
    autonomia_h: float       # horas por bateria en inspeccion
    carga_h: float           # horas de carga 10-90 %
    baterias: int            # baterias por robot (rotacion)
    cambio_bat_h: float      # tiempo de cambio de bateria (SUPUESTO)
    ventana_h_dia: float     # horas/dia con hoja seca, luz y sin lluvia (SUPUESTO)
    dias_semana: int         # SUPUESTO
    disponibilidad: float    # fraccion de tiempo sin fallas/pausas termicas (SUPUESTO)
    transito: float          # fraccion perdida en ir/volver de la caseta y leer marcadores (SUPUESTO)
    m_por_ha: float = M_RECORRIDO_POR_HA


# D1 Ultra: autonomia 1-2 h, carga ~1 h (10-90 %), alcance 6+-1 km, IP54, 0-40 C, carga util 5 kg.
#   https://store.agibot.com/products/d1-ultra  y manual
#   https://www.agibot.com/file/ueditor/php/upload/file/20260911/1789114774395970.pdf
# D1 MaxPro: 5,5 h sin carga / 2,5 h a carga plena, carga 4,5 h (rapida 2 h opcional), hot swap, IP67, 64 kg.
#   https://www.generationrobots.com/en/404440-agibot-d1-max-pro-quadruped-robot.html
ESCENARIOS = [
    Escenario("D1 Ultra", "conservador", 0.25, 1.0, 1.0, 1, 0.10, 5.0, 5, 0.85, 0.10),
    Escenario("D1 Ultra", "base",        0.40, 1.5, 1.0, 3, 0.10, 7.0, 6, 0.90, 0.10),
    Escenario("D1 Ultra", "optimista",   0.50, 2.0, 1.0, 3, 0.10, 9.0, 6, 0.95, 0.10),
    # Mismos supuestos que escalabilidad/unit_economics_parametros.yaml (rol modelo-negocio):
    # 0,8 m/s, 1,25 h, disponibilidad 0,80, camas a 3,0 m con 25 % de sobrecosto de giros.
    Escenario("D1 Ultra", "como_modelo_negocio", 0.80, 1.25, 1.0, 3, 0.10, 7.0, 6, 0.80, 0.0,
              m_por_ha=10000 / 3.0 * 1.25),
    # MaxPro: autonomia supuesta 4 h con mastil+camaras (< 50 kg de carga); carga rapida 2 h; hot swap 2 min.
    Escenario("D1 MaxPro", "base",       0.60, 4.0, 2.0, 2, 0.03, 7.0, 6, 0.90, 0.10),
    Escenario("D1 MaxPro", "optimista",  0.80, 4.0, 2.0, 2, 0.03, 10.0, 6, 0.95, 0.10),
]

# Politicas de revisita (visitas por cama por semana). SUPUESTO todas; el mentor debe validar.
POLITICAS = {
    "semanal_fija": 1.0,                       # toda cama 1 vez/semana (o 24 h antes de cada aspersion semanal)
    "por_riesgo": 0.30 * 1.0 + 0.70 * 0.5,     # 30 % de camas en riesgo alto 1/semana; resto cada 14 dias -> 0,65
}


def ciclo_util(e: Escenario) -> float:
    """Fraccion del tiempo de ventana en que el robot camina (no espera carga ni cambia bateria)."""
    if e.baterias <= 1:
        return e.autonomia_h / (e.autonomia_h + e.carga_h)
    # con n baterias, mientras una trabaja las otras n-1 cargan; si alcanzan, solo se pierde el cambio
    if (e.baterias - 1) * e.autonomia_h >= e.carga_h:
        return e.autonomia_h / (e.autonomia_h + e.cambio_bat_h)
    return ((e.baterias - 1) * e.autonomia_h) / ((e.baterias - 1) * e.autonomia_h + e.carga_h)


def capacidad(e: Escenario) -> dict:
    duty = ciclo_util(e)
    h_insp_dia = e.ventana_h_dia * duty * e.disponibilidad * (1 - e.transito)
    m_dia = e.v_insp_m_s * 3600 * h_insp_dia
    ha_dia = m_dia / e.m_por_ha
    ha_sem = ha_dia * e.dias_semana
    ciclos_bat_dia = (e.ventana_h_dia * duty * e.disponibilidad) / e.autonomia_h
    fila = asdict(e)
    fila.update(
        m_por_ha=round(e.m_por_ha),
        ciclo_util=round(duty, 3),
        h_inspeccion_dia=round(h_insp_dia, 2),
        km_dia=round(m_dia / 1000, 2),
        ha_dia=round(ha_dia, 2),
        ha_semana_pasadas=round(ha_sem, 1),
        ha_atendidas_semanal_fija=round(ha_sem / POLITICAS["semanal_fija"], 1),
        ha_atendidas_por_riesgo=round(ha_sem / POLITICAS["por_riesgo"], 1),
        robots_para_20ha_semanal=math.ceil(20 / (ha_sem / POLITICAS["semanal_fija"])),
        robots_para_20ha_por_riesgo=math.ceil(20 / (ha_sem / POLITICAS["por_riesgo"])),
        ciclos_bateria_dia=round(ciclos_bat_dia, 1),
        ciclos_bateria_anio=round(ciclos_bat_dia * e.dias_semana * 52),
    )
    return fila


def flota_itinerante(base: Escenario) -> list[dict]:
    """Cuadrilla itinerante: 1 tecnico-operador + vehiculo + k robots D1 Ultra en la misma finca el mismo dia."""
    filas = []
    duty = ciclo_util(base)
    for k in (1, 2, 3):
        for setup_h, viaje_en_ventana_h in ((1.0, 0.5), (1.0, 1.0)):   # SUPUESTO: montaje+bioseguridad 1 h; viaje que cae dentro de la ventana
            h_util = max(0.0, base.ventana_h_dia - setup_h - viaje_en_ventana_h)
            h_insp = h_util * duty * base.disponibilidad * (1 - base.transito)
            ha_dia_cuadrilla = k * base.v_insp_m_s * 3600 * h_insp / base.m_por_ha
            ha_sem = ha_dia_cuadrilla * base.dias_semana
            filas.append(dict(
                robots_por_cuadrilla=k,
                montaje_h=setup_h,
                viaje_en_ventana_h=viaje_en_ventana_h,
                ha_dia_cuadrilla=round(ha_dia_cuadrilla, 2),
                ha_semana_pasadas=round(ha_sem, 1),
                ha_atendidas_por_riesgo=round(ha_sem / POLITICAS["por_riesgo"], 1),
                fincas_de_3ha=int((ha_sem / POLITICAS["por_riesgo"]) // 3),
                fincas_de_5ha=int((ha_sem / POLITICAS["por_riesgo"]) // 5),
            ))
    return filas


def repuestos(n_robots: int, tasa_rma_anual: float = 0.30, semanas_fuera: float = 4.0) -> dict:
    """Pool de reserva con Poisson. tasa_rma_anual y semanas_fuera son SUPUESTO
    (el manual del D1 Ultra da 7 dias habiles de reparacion en el centro del fabricante, mas logistica a cargo del cliente)."""
    lam = n_robots * tasa_rma_anual * semanas_fuera / 52
    def p_mas_de(s: int) -> float:
        acum = sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(s + 1))
        return 1 - acum
    s = 0
    while p_mas_de(s) > 0.02:   # objetivo: <= 2 % de probabilidad de quedarse sin reserva
        s += 1
    return dict(robots=n_robots, robots_fuera_promedio=round(lam, 2), reservas_necesarias=s,
                prob_faltar=round(p_mas_de(s), 3), reservas_pct=round(100 * s / n_robots, 1))


def tecnicos(robots_fijos: int, fincas_nuevas_mes: float) -> dict:
    """Horas de tecnico de campo. Todas las horas son SUPUESTO salvo la jornada legal."""
    JORNADA_SEM_H = 42          # Ley 2101 de 2021, tope desde el 15-jul-2026 (prensa: publimetro.co, cronista.com)
    PRODUCTIVO = 0.75           # SUPUESTO: 25 % en traslados largos, informes, formacion
    h_mes_tecnico = JORNADA_SEM_H * 52 / 12 * PRODUCTIVO
    h_robot_mes = 3.0 + 4.0 / 3 + 1.5 + 2.25   # preventivo mensual + trimestral prorrateado + correctivo + viaje
    h_onboarding = 40.0                          # por finca nueva, repartidas en 8 semanas
    carga = robots_fijos * h_robot_mes + fincas_nuevas_mes * h_onboarding
    return dict(robots_fijos=robots_fijos, fincas_nuevas_mes=fincas_nuevas_mes,
                h_robot_mes=round(h_robot_mes, 2), h_disponibles_tecnico_mes=round(h_mes_tecnico),
                tecnicos=round(carga / h_mes_tecnico, 2),
                robots_por_tecnico_estable=round(h_mes_tecnico / h_robot_mes, 1),
                robots_por_tecnico_con_1_onboarding_mes=round((h_mes_tecnico - h_onboarding) / h_robot_mes, 1))


def costo_tecnico_por_ha() -> list[dict]:
    """Costo de mano de obra del tecnico de campo por ha atendida, en 3 modelos operativos.
    Excluye vehiculo, viaticos, repuestos y baterias."""
    SMMLV_2026 = 1_750_905      # COP, Decreto 1469 de 2025 (https://consultorsalud.com/aumento-del-salario-minimo-en-colombia-2026/)
    SALARIO_SMMLV = 2.0         # SUPUESTO: tecnico de campo gana 2 SMMLV
    FACTOR_PRESTACIONAL = 1.52  # SUPUESTO: seguridad social + prestaciones
    TRM = 3185.01               # COP/USD, 2026-10-23 (https://www.datos.gov.co/resource/32sa-8pi3.json)
    usd_anio = SMMLV_2026 * SALARIO_SMMLV * FACTOR_PRESTACIONAL * 12 / TRM
    h_mes = 42 * 52 / 12 * 0.75
    h_robot_mes = 3.0 + 4.0 / 3 + 1.5 + 2.25
    ha_robot_riesgo = 16.6      # D1 Ultra base, politica por riesgo (tabla de capacidad)
    filas = []
    # Modelo F: robot fijo; el operario de la finca hace lo diario, el tecnico solo preventivo/correctivo
    for rpt in (h_mes / h_robot_mes, (h_mes - 40) / h_robot_mes):
        ha = rpt * ha_robot_riesgo
        filas.append(dict(modelo="F robot fijo", robots_por_tecnico=round(rpt, 1), ha_por_tecnico=round(ha),
                          usd_tecnico_anio=round(usd_anio), usd_por_ha_anio=round(usd_anio / ha)))
    # Modelo I1: cuadrilla itinerante operada por el tecnico (2 robots); ver flota.csv
    for ha in (23.7, 26.1):
        filas.append(dict(modelo="I1 cuadrilla operada por tecnico (2 robots)", robots_por_tecnico=2,
                          ha_por_tecnico=ha, usd_tecnico_anio=round(usd_anio), usd_por_ha_anio=round(usd_anio / ha)))
    # Modelo I2: rotacion; el robot se queda 3 dias por finca y lo opera el operario de la finca.
    # Tecnico: 2 traslados/semana/robot x 2,5 h (SUPUESTO) + mantenimiento prorrateado.
    h_sem_robot = 2 * 2.5 + h_robot_mes * 12 / 52
    rpt = (h_mes * 12 / 52) / h_sem_robot
    ha_robot = 10.8 * (1 - 2 * 1.0 / (6 * 7.0)) / 0.65    # 2 montajes de 1 h por semana
    ha = rpt * ha_robot
    filas.append(dict(modelo="I2 rotacion 3 dias/finca, opera el operario", robots_por_tecnico=round(rpt, 1),
                      ha_por_tecnico=round(ha), usd_tecnico_anio=round(usd_anio), usd_por_ha_anio=round(usd_anio / ha)))
    return filas


def escribir(nombre: str, filas: list[dict]) -> None:
    with open(OUT / nombre, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


if __name__ == "__main__":
    cap = [capacidad(e) for e in ESCENARIOS]
    escribir("capacidad.csv", cap)
    base = next(e for e in ESCENARIOS if e.robot == "D1 Ultra" and e.escenario == "base")
    flo = flota_itinerante(base)
    escribir("flota.csv", flo)
    rep = [repuestos(n) for n in (5, 10, 20, 50, 100)]
    escribir("repuestos.csv", rep)
    tec = [tecnicos(n, m) for n, m in ((12, 1), (17, 0), (30, 2), (60, 3))]
    escribir("tecnicos.csv", tec)
    cos = costo_tecnico_por_ha()
    escribir("costo_tecnico_ha.csv", cos)
    for r in cos:
        print("costo", r)

    print(f"m de cama/ha = {M_CAMA_POR_HA:.0f}; m de recorrido/ha = {M_RECORRIDO_POR_HA:.0f}")
    for c in cap:
        print(c["robot"], c["escenario"], "| h insp/dia", c["h_inspeccion_dia"], "| km/dia", c["km_dia"],
              "| ha/sem", c["ha_semana_pasadas"], "| ha atendidas semanal", c["ha_atendidas_semanal_fija"],
              "| por riesgo", c["ha_atendidas_por_riesgo"], "| robots 20 ha", c["robots_para_20ha_semanal"],
              "/", c["robots_para_20ha_por_riesgo"], "| ciclos bat/anio", c["ciclos_bateria_anio"])
    for r in flo:
        print("flota", r)
    for r in rep:
        print("repuestos", r)
    for r in tec:
        print("tecnicos", r)
