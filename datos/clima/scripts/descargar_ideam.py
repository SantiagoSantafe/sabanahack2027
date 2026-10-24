"""Descarga observaciones IDEAM 2025 (datos.gov.co, API Socrata pública, sin login)
para estaciones cercanas a los puntos de arándano. Salida: raw/ideam_datosgov_2025/.
Uso: python3 -I descargar_ideam.py"""
import json, os, sys, time, urllib.parse, urllib.request

OUT = "/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/ideam_datosgov_2025"
DATASETS = {  # id Socrata -> variable
    "sbwg-7ju4": "temperatura",
    "uext-mhny": "humedad",
    "s54a-sgyg": "precipitacion",
}
STATIONS = {
    "0021205700": "GUASCA",
    "2120500135": "UNIVERSIDAD DE LA SABANA",
    "2403500041": "DUITAMA (Paipa)",
    "0024035430": "TUNGUAVITA (Paipa)",
    "2401500040": "CUCUNUBA",
    "0021205518": "SALITRE (Tausa)",
}
PAGE = 50000

def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa
            print("  reintento", i + 1, type(e).__name__, e, flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError("fallo " + url)

def main():
    only = sys.argv[1:]  # opcional: lista de codigos
    for ds, var in DATASETS.items():
        for code, name in STATIONS.items():
            if only and code not in only:
                continue
            fn = os.path.join(OUT, f"{var}_{code}_2025.json")
            if os.path.exists(fn):
                print("ya existe", fn); continue
            rows, off = [], 0
            while True:
                q = {
                    "$where": f"codigoestacion='{code}' and fechaobservacion between '2025-01-01T00:00:00' and '2025-12-31T23:59:59'",
                    "$order": "fechaobservacion",
                    "$limit": str(PAGE), "$offset": str(off),
                }
                url = f"https://www.datos.gov.co/resource/{ds}.json?" + urllib.parse.urlencode(q)
                t0 = time.time()
                part = get(url)
                rows += part
                print(f"{var} {code} {name}: +{len(part)} filas ({time.time()-t0:.0f}s)", flush=True)
                if len(part) < PAGE:
                    break
                off += PAGE
            with open(fn, "w") as f:
                json.dump(rows, f)
            print("guardado", fn, len(rows), flush=True)

if __name__ == "__main__":
    main()
