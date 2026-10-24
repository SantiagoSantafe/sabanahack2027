"""Verificacion adversaria de rutas, bateria y operacion (rol: verificacion-tecnica).

Uso:  python3 -I verificacion_rutas.py
Salida: verificacion_rutas.csv (misma carpeta) y tablas en pantalla.

No es medicion de campo. Reutiliza los parametros de escalabilidad/operacion/capacidad.py
(escenario base) y prueba que pasa si se relajan los supuestos mas optimistas.
Cada valor nuevo lleva la marca SUPUESTO o su fuente.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent

# --- Parametros del escenario base de operacion/capacidad.py (copiados, no inventados)
V_INSP = 0.40            # m/s, SUPUESTO de operacion.md
VENTANA_H = 7.0          # h/dia con hoja seca, SUPUESTO de operacion.md
DISPONIBILIDAD = 0.90    # SUPUESTO de operacion.md
CAMBIO_BAT_H = 0.10      # SUPUESTO de operacion.md
CARGA_H = 1.0            # manual D1: ~1 h del 10 al 90 %
N_BAT = 3                # operacion.md
M_POR_HA = 5250 * 0.75 * 1.08   # 4.252 m de recorrido por ha (operacion.md)
RESERVA = 0.20           # restriccion dura 5 de operacion.md: maximo 80 % de la autonomia por tour

# --- Supuestos nuevos de esta verificacion
V_TRANSITO = (0.5, 1.0)          # m/s caminando por pasillos y cabeceras hacia la caseta (SUPUESTO)
AUTONOMIAS_H = {                 # horas por bateria
    "ficha 1,5 h (base operacion)": 1.5,
    "con kit en el mastil -25 %": 1.125,   # SUPUESTO: computo + camaras + luces alimentados por la bateria del robot
    "a carga plena (proporcion MaxPro 2,5/5,5)": 1.5 * 2.5 / 5.5,  # SUPUESTO: misma caida relativa que el MaxPro
}
AREAS_CASETA_HA = (5, 10, 20)    # area que atiende una caseta (operacion.md propone 1 por ~20 ha)


def duty(aut_util_h: float) -> float:
    if (N_BAT - 1) * aut_util_h >= CARGA_H:
        return aut_util_h / (aut_util_h + CAMBIO_BAT_H)
    return ((N_BAT - 1) * aut_util_h) / ((N_BAT - 1) * aut_util_h + CARGA_H)


def transito(area_ha: float, v_tr: float, aut_util_h: float) -> tuple[float, float]:
    """Fraccion del tiempo de cada bateria gastada en ir y volver de la caseta.
    Caseta en el centro de un cuadrado; distancia por pasillos (Manhattan).
    Promedio: ida a un punto al azar + vuelta desde otro = L. Peor caso (esquina): 2L."""
    lado = math.sqrt(area_ha * 10_000)
    t_ciclo_s = aut_util_h * 3600
    return (lado / v_tr) / t_ciclo_s, (2 * lado / v_tr) / t_ciclo_s


def main() -> None:
    filas = []
    print("\n1) Transito caseta <-> camas (promedio / peor caso) y capacidad resultante")
    print(f"{'autonomia':45s} {'ha/caseta':>9s} {'v_tr':>5s} {'transito prom':>13s} {'peor':>6s} {'ha/dia':>7s} {'ciclos/dia':>10s} {'ciclos/anio':>11s}")
    for nombre, aut in AUTONOMIAS_H.items():
        util = aut * (1 - RESERVA)
        d = duty(util)
        for area in AREAS_CASETA_HA:
            for v in V_TRANSITO:
                t_prom, t_peor = transito(area, v, util)
                h_insp = VENTANA_H * d * DISPONIBILIDAD * (1 - t_prom)
                ha_dia = V_INSP * 3600 * h_insp / M_POR_HA
                ciclos_dia = VENTANA_H * d * DISPONIBILIDAD / util
                fila = dict(autonomia=nombre, autonomia_h=round(aut, 2), autonomia_util_h=round(util, 2),
                            ha_por_caseta=area, v_transito_m_s=v,
                            transito_promedio=round(t_prom, 3), transito_peor=round(t_peor, 3),
                            ha_dia=round(ha_dia, 2), ha_semana_6d=round(6 * ha_dia, 1),
                            ciclos_bateria_dia=round(ciclos_dia, 1),
                            ciclos_bateria_anio=round(ciclos_dia * 6 * 52))
                filas.append(fila)
                print(f"{nombre:45s} {area:9d} {v:5.1f} {t_prom:13.0%} {t_peor:6.0%} {ha_dia:7.2f} {ciclos_dia:10.1f} {ciclos_dia*6*52:11.0f}")

    radio = 150
    print(f"\n   Una caseta a <= {radio} m por pasillos (Manhattan) alcanza {2*radio**2/10_000:.1f} ha;"
          f" en linea recta, {math.pi*radio**2/10_000:.1f} ha. operacion.md pide <=150 m y 1 caseta por ~20 ha: no cuadra.")

    print("\n2) 'Siempre delante del aspersor': cuantas ha/dia puede asperjar la finca")
    ha_dia_robot = 1.80   # operacion/capacidad.csv, D1 Ultra base
    for robots in (1, 2, 3):
        cap = robots * ha_dia_robot
        print(f"   {robots} robot(s): inspecciona {cap:.1f} ha/dia -> la aspersion no puede pasar de {cap:.1f} ha/dia"
              f" (20 ha repartidas en >= {20/cap:.1f} dias). Si se asperjan 20 ha en 1 dia: {cap/20:.0%} inspeccionado antes;"
              f" en 2 dias: {min(1, 2*cap/20):.0%}")

    print("\n3) Si se cumple la linea de vista del manual: costo del operario que acompana")
    SMMLV = 1_750_905; FACTOR = 1.52; TRM = 3185.01   # mismos valores de operacion/capacidad.py
    usd_operario = SMMLV * 1.0 * FACTOR * 12 / TRM     # SUPUESTO: operario rural a 1 SMMLV
    for frac in (1.0, 0.5, 20 / 60 / 8):
        print(f"   operario dedicado {frac:5.0%} de su jornada a 2 robots en 20 ha -> {usd_operario*frac/20:6.0f} USD/ha/anio"
              f" (frente a ~430 USD/ha/anio de costo total del hibrido que usa la propuesta)")

    with open(OUT / "verificacion_rutas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"\nGuardado: {OUT / 'verificacion_rutas.csv'}")


if __name__ == "__main__":
    main()
