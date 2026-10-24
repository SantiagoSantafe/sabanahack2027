"""Descarga Open-Meteo histórico 2025 (best_match) en las coordenadas exactas de las estaciones IDEAM
(catálogo hp9r-jxuu) para comparar punto a punto. Salida: clima/cache/historico_2025_est_<codigo>.csv"""
import json, os, sys
CLIMA = "/Users/santiagosantafe/Downloads/SabanaHack/datos/clima"
sys.path.insert(0, CLIMA)
from clima_client import ClimaClient  # noqa: E402
CAT = "/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/ideam_datosgov_2025/catalogo_estaciones.json"
c = ClimaClient(verbose=True)
for e in json.load(open(CAT)):
    lat, lon = float(e["latitud"]), float(e["longitud"])
    env = c.historico((lat, lon), "2025-01-01", "2025-12-31")
    ruta = os.path.join(CLIMA, "cache", f"historico_2025_est_{e['codigo']}.csv")
    c.guardar_csv(env, ruta, {"estacion": e["codigo"], "modelo": "best_match"})
    print(e["codigo"], e["nombre"], "alt_est", e["altitud"], "elev_OM", env["json"].get("elevation"),
          "celda", env["json"].get("latitude"), env["json"].get("longitude"), env["origen"])

# Salitre: el DEM de Open-Meteo en las coordenadas del catálogo da 3284 m vs 2637 m de la estación
# (coordenadas probablemente imprecisas). Se pide también forzando la elevación de la estación.
for e in json.load(open(CAT)):
    if e["codigo"] != "0021205518":
        continue
    env = c.historico((float(e["latitud"]), float(e["longitud"])), "2025-01-01", "2025-12-31",
                      elevacion=float(e["altitud"]))
    ruta = os.path.join(CLIMA, "cache", f"historico_2025_est_{e['codigo']}_elevest.csv")
    c.guardar_csv(env, ruta, {"estacion": e["codigo"], "modelo": "best_match_elev_estacion"})
    print("Salitre con elevation=", e["altitud"], "->", env["json"].get("elevation"), ruta)
