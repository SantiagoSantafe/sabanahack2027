"""Calcula TAM / SAM / SOM del rol mercado-go-to-market.

Uso:  python3 -I calc_mercado.py
Lee los JSON de EVA guardados en esta carpeta (consulta a
https://www.datos.gov.co/resource/uejq-wxrr.json, 2026-10-23) y aplica los
supuestos marcados abajo. Imprime tablas markdown listas para mercado.md.
Todo lo que dice SUPUESTO es una decision del equipo, no un dato publicado.
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def cargar(nombre):
    with open(os.path.join(AQUI, nombre), encoding="utf-8") as f:
        return json.load(f)


eva = cargar("eva_nacional_berries_2019_2025.json")
eva25 = {r["cultivo"]: float(r["sembrada"]) for r in eva if r["a_o"] == "2025"}
mun = cargar("eva_municipal_berries_2025.json")

# ---------- Superficie (ha). Fuente en mercado.md, seccion 1 ----------
AREA = {
    # (bajo, central, alto)
    "Arándano Colombia": (eva25["Arándano"], 1000.0, 1200.0),   # EVA 2025 / gremio 2025 / proyeccion 2026
    "Arándano Perú": (23344.0, 26786.0, 27000.0),               # SENASA certificadas / ProArandanos cultivada / >27 mil en produccion 2026-27
    "Arándano Chile": (14000.0, 15700.0, 18071.0),              # Odepa (cit. Comite) / estimacion Comite / Comite 2023
    "Arándano México": (7648.0, 11000.0, 11000.0),              # registradas a la fecha 25-26 / panel Aneberries 24-25
    "Fresa Colombia": (eva25["Fresa"],) * 3,
    "Mora Colombia": (eva25["Mora"],) * 3,
}

# ---------- Precio por plan, USD/ha/ano (SUPUESTO) ----------
PRECIO_CENTINELA = 430.0   # hibrido robot+sensores; cifra de costo del equipo (finca 20 ha)
PRECIO_VIGIA = 60.0        # SUPUESTO: sensores+modelos+alertas+registro, scouting con celular, sin robot
PLAN = {k: PRECIO_CENTINELA for k in AREA}
PLAN["Mora Colombia"] = PRECIO_VIGIA

# ---------- Filtros SAM y SOM (SUPUESTO) ----------
SAM_PCT = {
    "Arándano Colombia": 0.80,  # casi todo es tecnificado (inversion >= 1.200 M COP), quita lotes muy pequenos
    "Arándano Perú": 0.30,      # productores de 5-50 ha ("pequenos" segun Midagri 2024, ~30 % de la produccion) como proxy de area
    "Arándano Chile": 0.35,     # huertos en recambio varietal / mayor valor
    "Arándano México": 0.25,    # mercado dominado por integradoras con agronomia propia
    "Fresa Colombia": 0.25,     # fresa tecnificada (macrotunel / sustrato)
    "Mora Colombia": 0.15,      # productores en asociaciones, via Asohofrucol / gobernaciones
}
SOM_PCT = {  # cuota del SAM a 5 anos (fin etapa 3)
    "Arándano Colombia": 0.30,
    "Arándano Perú": 0.05,
    "Arándano Chile": 0.03,
    "Arándano México": 0.02,
    "Fresa Colombia": 0.15,
    "Mora Colombia": 0.10,
}
HA_POR_ROBOT = 20.0  # SUPUESTO heredado de la finca ejemplo de 20 ha


def fmt(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    print("| Segmento | ha bajo | ha central | ha alto | Plan | USD/ha/año | TAM central USD/año |")
    print("|---|---:|---:|---:|---|---:|---:|")
    tam_tot = 0.0
    for k, (lo, c, hi) in AREA.items():
        p = PLAN[k]
        tam = c * p
        tam_tot += tam
        nombre = "Vigía" if p == PRECIO_VIGIA else "Centinela"
        print(f"| {k} | {fmt(lo)} | {fmt(c)} | {fmt(hi)} | {nombre} | {fmt(p)} | {fmt(tam)} |")
    ha_tot = sum(v[1] for v in AREA.values())
    print(f"| **Total** |  | **{fmt(ha_tot)}** |  |  |  | **{fmt(tam_tot)}** |")
    print()
    print("| Segmento | % SAM | ha SAM | USD SAM/año | % SOM (del SAM) | ha SOM | USD SOM/año | Robots (20 ha c/u) |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    sam_ha = sam_usd = som_ha = som_usd = robots = 0.0
    for k, (lo, c, hi) in AREA.items():
        p = PLAN[k]
        s_ha = c * SAM_PCT[k]
        o_ha = s_ha * SOM_PCT[k]
        r = o_ha / HA_POR_ROBOT if p == PRECIO_CENTINELA else 0.0
        sam_ha += s_ha; sam_usd += s_ha * p; som_ha += o_ha; som_usd += o_ha * p; robots += r
        print(f"| {k} | {SAM_PCT[k]*100:.0f} % | {fmt(s_ha)} | {fmt(s_ha*p)} | {SOM_PCT[k]*100:.0f} % | {fmt(o_ha)} | {fmt(o_ha*p)} | {fmt(r)} |")
    print(f"| **Total** |  | **{fmt(sam_ha)}** | **{fmt(sam_usd)}** |  | **{fmt(som_ha)}** | **{fmt(som_usd)}** | **{fmt(robots)}** |")
    print()
    # Sensibilidad del TAM de arandano a los rangos de area
    ar = [k for k in AREA if k.startswith("Arándano")]
    for i, n in enumerate(["bajo", "central", "alto"]):
        ha = sum(AREA[k][i] for k in ar)
        print(f"Arándano 4 países, escenario {n}: {fmt(ha)} ha -> TAM {fmt(ha*PRECIO_CENTINELA)} USD/año")
    print()
    # Concentracion municipal arandano 2025 (EVA)
    a = sorted([r for r in mun if r["cultivo"] == "Arándano"], key=lambda r: -float(r["sembrada"]))
    tot = sum(float(r["sembrada"]) for r in a)
    top10 = sum(float(r["sembrada"]) for r in a[:10])
    n5 = sum(1 for r in a if float(r["sembrada"]) >= 5)
    print(f"Arándano EVA 2025: {len(a)} municipios, {fmt(tot,1)} ha; top-10 municipios = {top10/tot*100:.0f} %; municipios con >=5 ha: {n5}")
    for r in a[:10]:
        print(f"  {r['departamento']} / {r['municipio']}: {fmt(float(r['sembrada']),1)} ha")
    # Rendimientos EVA 2025
    for c in ("Arándano", "Fresa", "Mora"):
        r = [x for x in eva if x["cultivo"] == c and x["a_o"] == "2025"][0]
        y = float(r["produccion"]) / float(r["cosechada"]) if float(r["cosechada"]) else 0
        print(f"{c} 2025: sembrada {fmt(float(r['sembrada']))} ha, cosechada {fmt(float(r['cosechada']))} ha, produccion {fmt(float(r['produccion']))} t, rendimiento {fmt(y,1)} t/ha")


if __name__ == "__main__":
    main()
