#!/usr/bin/env python3
"""Matriz de alternativas con el criterio nuevo 'Escalabilidad'.

Uso: python3 -I matriz_escalabilidad.py

Puntajes de los 6 criterios originales y pesos base (20/20/20/15/15/10):
tomados de reportes/verificacion-finanzas-robots-documento.md §6 (documento del
equipo, revisión 22). Puntajes de Escalabilidad: PROPUESTA del integrador
(ESCALABILIDAD.md §10). Solo biblioteca estándar.
"""
from itertools import product

CRITERIOS = ["anticipa", "ubica", "costo", "encaje", "robustez", "registro"]
PESOS_BASE = [20, 20, 20, 15, 15, 10]
PUNTAJES = {
    "A D1 Ultra + mástil": [3, 5, 3, 4, 3, 4],
    "B Red fija":          [5, 1, 5, 5, 4, 2],
    "C Kit aspersora":     [2, 4, 5, 3, 3, 3],
    "D Humanoide":         [2, 4, 1, 1, 1, 4],
    "E Ruedas":            [3, 5, 2, 4, 3, 4],
    "F Híbrido":           [5, 5, 3, 4, 3, 5],
}
# PROPUESTA (justificación en ESCALABILIDAD.md §10)
ESCALA = {"A D1 Ultra + mástil": 2, "B Red fija": 4, "C Kit aspersora": 3,
          "D Humanoide": 1, "E Ruedas": 2, "F Híbrido": 4}


def total(p, w):
    return sum(pi * wi for pi, wi in zip(p, w)) / 5.0


def tabla(w_esc, esc=ESCALA):
    """Escalabilidad con peso w_esc; los 6 pesos originales se escalan en proporción."""
    f = (100 - w_esc) / 100.0
    w = [x * f for x in PESOS_BASE] + [w_esc]
    return {k: total(v + [esc[k]], w) for k, v in PUNTAJES.items()}


def barrido(n_crit, esc=None):
    """Pesos múltiplos de 5 (mínimo 5) que suman 100. Devuelve combos, F gana, B > F."""
    combos = gana_f = b_sobre_f = 0
    for w in product(range(5, 100, 5), repeat=n_crit - 1):
        ult = 100 - sum(w)
        if ult < 5:
            continue
        w = list(w) + [ult]
        if esc is None:
            t = {k: total(v, w) for k, v in PUNTAJES.items()}
        else:
            t = {k: total(v + [esc[k]], w) for k, v in PUNTAJES.items()}
        combos += 1
        mejor = max(t.values())
        if abs(t["F Híbrido"] - mejor) < 1e-9:
            gana_f += 1
        if t["B Red fija"] > t["F Híbrido"] + 1e-9:
            b_sobre_f += 1
    return combos, gana_f, b_sobre_f


if __name__ == "__main__":
    base = {k: total(v, PESOS_BASE) for k, v in PUNTAJES.items()}
    print("| Alternativa | Escalabilidad (1-5) | Total sin escalabilidad | Escalab. 10 % | Escalab. 15 % | Escalab. 20 % | Escalab. 15 %, B = 5 | Escalab. 15 %, F = 2 (robot en cada finca) |")
    print("|---|---|---|---|---|---|---|---|")
    t10, t15, t20 = tabla(10), tabla(15), tabla(20)
    esc_b5 = dict(ESCALA, **{"B Red fija": 5})
    t15b5 = tabla(15, esc_b5)
    t15f2 = tabla(15, dict(ESCALA, **{"F Híbrido": 2}))
    for k in PUNTAJES:
        print(f"| {k} | {ESCALA[k]} | {base[k]:.0f} | {t10[k]:.1f} | {t15[k]:.1f} | {t20[k]:.1f} | {t15b5[k]:.1f} | {t15f2[k]:.1f} |")
    print()
    for nombre, n, esc in [("6 criterios (sin escalabilidad)", 6, None),
                           ("7 criterios (con escalabilidad, puntajes propuestos)", 7, ESCALA),
                           ("7 criterios, si B = 5 en escalabilidad", 7, esc_b5)]:
        c, g, b = barrido(n, esc)
        print(f"{nombre}: {c} combinaciones; F primero en {g} ({100*g/c:.0f} %); B por encima de F en {b} ({100*b/c:.0f} %)")
