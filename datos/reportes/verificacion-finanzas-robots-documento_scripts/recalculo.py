#!/usr/bin/env python3
"""Recalculo independiente (verificador adversario finanzas-robots-documento).

No importa roi.py ni lee parametros.yaml: los valores se escriben a mano a
partir de parametros.yaml / del documento del equipo (rev 22) para comprobar
que las salidas publicadas cuadran. Ejecutar:  python3 -I recalculo.py
"""
import math


def landed(items, fob, peso, flete_kg=5.0, flete_fijo=150, seguro=0.01, arancel=0.05,
           iva=0.19, iva_costo=True, fijos=350):
    f = sum(fob[k] * q for k, q in items)
    kg = sum(peso[k] * q for k, q in items)
    flete = kg * flete_kg + flete_fijo
    cif = f + flete + seguro * f
    ar = cif * arancel
    iv = (cif + ar) * iva
    return cif + ar + (iv if iva_costo else 0) + fijos, f


FOB = dict(D1=7499, nodo=186, gw=500, MaxPro=67999)
PESO = dict(D1=30, nodo=0.5, gw=2, MaxPro=120)
jornal_usd = 1750905 / 30 * 1.30 / 3185.01

print("== Jornal ==")
print(f"SMMLV diario {1750905/30:.1f} COP; jornal {1750905/30*1.3:.0f} COP = {jornal_usd:.3f} USD")
print(f"Aumento SMMLV 2026 vs 2025: {100*(1750905/1423500-1):.2f} %  (no 23,7 %)")


def capacidad(vel, horas, entrecalle, overhead=1.3, frac=1.0):
    return horas * 3600 * vel / (10000 / entrecalle * overhead * frac)


def fila(nombre, area, robots, red, fa_on, mult, accesorio=1500, mant=2775, fob=FOB,
         Y=12000, P=6.0, L=0.10, f=0.25, n=6, cap=95, J=3, fa_ha=5, c_fa=30, vida=3,
         opex_nodo=130, flete_kg=5.0, nube=240):
    items = []
    if robots:
        items.append(("D1", robots))
    nodos = gws = 0
    if red:
        nodos, gws = math.ceil(area * 1), math.ceil(area / 100)
        items += [("nodo", nodos), ("gw", gws)]
    tot, _ = landed(items, fob, PESO, flete_kg=flete_kg)
    capex = tot + 20 * nodos + accesorio * robots
    opex = nube + mant * robots + opex_nodo * nodos + (area * fa_ha * c_fa if fa_on else 0)
    costo_ha = (capex / vida + opex) / area
    w = 1750905 / 30 * 1.30 / 3185.01 if J else 0
    b = Y * P * L * min(1, f * mult[0]) + n * mult[1] * cap + J * mult[2] * w
    roi = (b - costo_ha) / costo_ha
    payback = (capex / area) / (b - opex / area)
    kg_eq = max(0, (costo_ha - n * mult[1] * cap - J * mult[2] * w) / P)
    print(f"{nombre:<34} capex={capex:9.2f} costo/ha={costo_ha:8.2f} B/ha={b:8.2f} "
          f"ROI={roi:6.3f} payback={payback:5.2f} kg_eq={kg_eq:6.1f} kg_solo={costo_ha/P:6.1f}")
    return costo_ha, b


print("\n== Filas recalculadas a mano (20 ha, base) ==")
print("capacidad D1 (A, frac 1):", round(capacidad(0.5, 36, 2.5), 2), "ha/semana")
print("capacidad D1 (F, frac 0,5):", round(capacidad(0.5, 36, 2.5, frac=0.5), 2), "ha/semana")
cF, bF = fila("F hibrido red + 1 D1 Ultra", 20, 1, True, True, (1.0, 1.0, 1.0))
cB, bB = fila("B red fija", 20, 0, True, False, (0.4, 1.0, 0.0), accesorio=0, mant=0)
cA, bA = fila("A 2 D1 Ultra + mastil", 20, 2, False, True, (0.7, 0.3, 1.0))
print(f"Incremental F-B: costo {cF-cB:.1f}, beneficio {bF-bB:.1f}, ROI inc {(bF-bB-(cF-cB))/(cF-cB):.3f}")

print("\n== F pesimista (escenario conjunto) ==")
print("capacidad D1 pes (0,3 m/s, entrecalle 2 m, frac 0,5):",
      round(capacidad(0.3, 36, 2.0, frac=0.5), 2), "ha -> 2 robots")
fob_p = dict(FOB, D1=9600, nodo=250)
w_p = 1750905 / 30 * 1.0 / 3900.82
tot, _ = landed([("D1", 2), ("nodo", 20), ("gw", 1)], fob_p, PESO, flete_kg=8.0)
capex = tot + 400 + 2 * 2000
opex = 240 + 2 * 3250 + 20 * 155 + 20 * 12 * 40
c = (capex / 3 + opex) / 20
b = 8000 * 4 * 0.05 * 0.10 + 2 * 60 + 0 * w_p
print(f"F pes: capex={capex:.0f} costo/ha={c:.1f} B={b:.1f} ROI={(b-c)/c:.3f}")

print("\n== Sensibilidades que el verificador agrega (F y B, 20 ha) ==")
fila("F con Y = 9.070 kg/ha (EVA 2025)", 20, 1, True, True, (1.0, 1.0, 1.0), Y=9070)
fila("B con Y = 9.070 kg/ha (EVA 2025)", 20, 0, True, False, (0.4, 1.0, 0.0), accesorio=0, mant=0, Y=9070)
fila("F con D1 a 9.600 (tienda) como base", 20, 1, True, True, (1.0, 1.0, 1.0), fob=dict(FOB, D1=9600))
fila("B pagando falsas alarmas (5/ha x 30)", 20, 0, True, True, (0.4, 1.0, 0.0), accesorio=0, mant=0)

print("\n== Factor de importacion D1 Ultra ==")
t, f0 = landed([("D1", 1)], FOB, PESO)
t0, _ = landed([("D1", 1)], FOB, PESO, arancel=0.0)
ti, _ = landed([("D1", 1)], FOB, PESO, iva_costo=False)
print(f"factor {t/f0:.3f}; arancel 0 -> {t0/f0:.3f}; IVA recuperable -> {ti/f0:.3f}")

print("\n== Matriz de alternativas (documento rev 22) ==")
S = {"A": [3, 5, 3, 4, 3, 4], "B": [5, 1, 5, 5, 4, 2], "C": [2, 4, 5, 3, 3, 3],
     "D": [2, 4, 1, 1, 1, 4], "E": [3, 5, 2, 4, 3, 4], "F": [5, 5, 3, 4, 3, 5]}


def tot(w):
    assert sum(w) == 100, w
    return {k: sum(s * x for s, x in zip(v, w)) / 5 for k, v in S.items()}


print("pesos base 20/20/20/15/15/10:", tot([20, 20, 20, 15, 15, 10]))
print("sens. documento 20/15/30/15/10/10:", tot([20, 15, 30, 15, 10, 10]))
for w in ([20, 10, 30, 15, 15, 10], [15, 15, 30, 15, 15, 10], [20, 20, 30, 15, 10, 5],
          [20, 10, 40, 15, 5, 10], [10, 20, 30, 15, 15, 10]):
    t = tot(w)
    print("  ", w, "B", t["B"], "F", t["F"], "ganador", max(t, key=t.get))
SF = dict(S)
SF["F"] = [5, 5, 2, 4, 3, 5]
print("F con costo=2:", sum(s * x for s, x in zip(SF["F"], [20, 20, 20, 15, 15, 10])) / 5)
# barrido: cuantas combinaciones de pesos (multiplos de 5, cada peso >=5) hacen ganar a B sobre F
gana_B = tot_comb = 0
for a in range(5, 70, 5):
    for u in range(5, 70, 5):
        for co in range(5, 70, 5):
            for e in range(5, 70, 5):
                for r in range(5, 70, 5):
                    g = 100 - a - u - co - e - r
                    if g < 5:
                        continue
                    w = [a, u, co, e, r, g]
                    t = tot(w)
                    tot_comb += 1
                    gana_B += t["B"] > t["F"]
print(f"barrido de pesos (multiplos de 5, minimo 5): B > F en {gana_B} de {tot_comb} combinaciones")
# condicion analitica: F - B = (0*a + 4u - 2co - 1e - 1r + 3g)/5
print("F - B = (4*ubica - 2*costo - encaje - robustez + 3*registro)/5  (anticipa se cancela)")

print("\n== Cifras del documento y del revisor ==")
B_doc = lambda Y, P, L, f, n, C, J, w: Y * P * L * f + n * C + J * w
print("B doc pes/base/opt:", B_doc(12000, 4, .03, .10, 0, 60, 0, 19), B_doc(12000, 6, .08, .25, 2, 100, 10, 19),
      B_doc(12000, 8, .15, .40, 4, 150, 20, 19))
print("B doc con jornal 75.900/3.185,01:", round(B_doc(12000, 6, .08, .25, 2, 100, 10, 75900 / 3185.01), 1))
print("B doc con Y=9.070:", round(B_doc(9070, 6, .08, .25, 2, 100, 10, 19), 1))
print("MaxPro 20 ha: O&M implicito en 2.100 USD/ha =", round(2100 * 20 - (67999 * 1.35 + 1500) / 3),
      "USD/ano =", round(100 * (2100 * 20 - (67999 * 1.35 + 1500) / 3) / (67999 * 1.35 + 1500), 1), "% del capex")
print("MaxPro 60 ha servicio 700*60 =", 700 * 60, " = 2.100*20 =", 2100 * 20)
print("Genie G1: O&M implicito en 2.200 =", round(2200 * 20 - (75199 * 1.35 + 1500) / 3))
print("Peru FOB implicito Gestion 14-ene-2026: 2563/412.239 =", round(2563e6 / 412239e3, 3),
      "; Gestion 16-feb-2026 (Midagri): 2457/373.514 =", round(2457e6 / 373514e3, 3))
print("Colombia FOB implicito (El Tiempo): 3,0-3,5 MUSD / 574.607 kg =",
      round(3e6 / 574607, 2), "-", round(3.5e6 / 574607, 2))
print("EVA 2025 rendimiento: 6030,66 / 664,72 =", round(6030.66 / 664.72, 2), "t/ha cosechada")
print("Clopper-Pearson 8/8, limite inferior 95 %:", round(0.025 ** (1 / 8), 3))
print("Umbral Bayes 30/(30+2160) =", round(30 / 2190, 4))
