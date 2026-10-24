"""
clima_client.py -- Cliente Open-Meteo con caché en disco (Sabana Hack, reto "Berry Good Idea").

Qué hace
--------
* Pronóstico horario  : https://api.open-meteo.com/v1/forecast
* Histórico horario   : https://archive-api.open-meteo.com/v1/archive
* Cada respuesta JSON se guarda en  clima/cache/json/<clave>.json  (clave = hash de endpoint+parámetros)
  con metadatos (url, hora de descarga UTC). Además se mantiene un "último pronóstico" por punto
  (cache/json/pronostico_<punto>_ultimo.json) para que la demo funcione SIN internet.
* Sin internet: devuelve la caché (aunque esté vencida) e indica el origen en el campo `origen`
  ("red", "cache", "cache_vencida", "cache_ultimo_pronostico").

Dependencias: solo librería estándar (urllib, json). pandas es OPCIONAL (para obtener DataFrame).
Funciona con `python3 -I` (sin site-packages de usuario).

Uso rápido
----------
    from clima_client import ClimaClient, PUNTOS
    c = ClimaClient()
    datos = c.pronostico("chia")                 # dict {"origen":..., "json":..., "filas":[...]}
    df    = c.pronostico_df("chia")              # pandas.DataFrame (si pandas está instalado)
    hist  = c.historico_df("guasca", "2025-01-01", "2025-12-31")

CLI
---
    python3 -I clima_client.py descargar-todo        # histórico 2025 + pronóstico de todos los puntos
    python3 -I clima_client.py pronostico chia       # imprime resumen del pronóstico (usa caché si no hay red)
    python3 -I clima_client.py offline-test          # simula sin red y verifica que la caché responde

Licencia de datos: Open-Meteo (CC BY 4.0, uso no comercial gratuito). Citar "Weather data by Open-Meteo.com"
y las fuentes (ECMWF IFS / Copernicus ERA5). Ver reportes/clima-open-meteo.md.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR_DEFAULT = os.path.join(AQUI, "cache")

URL_FORECAST = "https://api.open-meteo.com/v1/forecast"
URL_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
TZ = "America/Bogota"

# Variables horarias pedidas. leaf_wetness_probability NO aparece en la documentación del histórico,
# pero la API de archivo la devuelve (verificado 2026-10-23); en ERA5/ERA5-Land puede venir vacía.
VARS_HORARIAS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "wind_speed_10m",
    "leaf_wetness_probability",
]
VARS_PRONOSTICO_EXTRA = ["precipitation_probability"]

# Puntos: cabecera municipal (coordenadas y elevación del geocodificador de Open-Meteo, 2026-10-23).
# Área sembrada 2025 de arándano: EVA (UPRA/MinAgricultura), datos.gov.co dataset uejq-wxrr.
PUNTOS = {
    "sotaquira": {"nombre": "Sotaquirá (Boyacá)", "lat": 5.76483, "lon": -73.24758, "elev_ref_m": 2677,
                  "ha_arandano_2025": 182.0, "rol": "mayor área de arándano del país (EVA 2025)"},
    "tausa":     {"nombre": "Tausa (Cundinamarca)", "lat": 5.19903, "lon": -73.89128, "elev_ref_m": 2992,
                  "ha_arandano_2025": 121.0, "rol": "mayor área de Cundinamarca (EVA 2025)"},
    "guasca":    {"nombre": "Guasca (Cundinamarca)", "lat": 4.86601, "lon": -73.87748, "elev_ref_m": 2681,
                  "ha_arandano_2025": 57.0, "rol": "Sabana/oriente de Bogotá, estación IDEAM a 2 km"},
    "chia":      {"nombre": "Chía (Cundinamarca) - sede demo U. de La Sabana", "lat": 4.85876, "lon": -74.05866,
                  "elev_ref_m": 2557, "ha_arandano_2025": 0.0,
                  "rol": "solo sitio de la demo; sin área de arándano reportada en EVA 2019-2025"},
}

TTL_PRONOSTICO_S = 3600          # 1 h: pasado esto se intenta refrescar
TIMEOUT_S = 60


def _ahora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ClimaClient:
    def __init__(self, cache_dir: str = CACHE_DIR_DEFAULT, offline: bool | None = None, verbose: bool = False):
        self.cache_dir = cache_dir
        self.json_dir = os.path.join(cache_dir, "json")
        os.makedirs(self.json_dir, exist_ok=True)
        # offline=True fuerza a no usar la red (útil para la demo). También con env CLIMA_OFFLINE=1
        if offline is None:
            offline = os.environ.get("CLIMA_OFFLINE", "0") == "1"
        self.offline = offline
        self.verbose = verbose

    # ------------------------------------------------------------------ utilidades
    @staticmethod
    def _clave(url: str, params: dict) -> str:
        canon = url + "?" + urllib.parse.urlencode(sorted((k, str(v)) for k, v in params.items()))
        return hashlib.sha1(canon.encode()).hexdigest()[:16]

    def _ruta(self, nombre: str) -> str:
        return os.path.join(self.json_dir, nombre + ".json")

    def _leer(self, ruta: str):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _escribir(self, ruta: str, obj) -> None:
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, ruta)  # escritura atómica

    def _descargar(self, url: str, params: dict) -> dict:
        full = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(full, headers={"User-Agent": "SabanaHack-BerryGoodIdea/1.0"})
        ultimo_error = None
        for intento in range(3):
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                    data = json.loads(r.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("error"):
                    raise RuntimeError("Open-Meteo error: " + str(data.get("reason")))
                return data
            except urllib.error.HTTPError as e:
                cuerpo = e.read().decode("utf-8", "replace")[:300]
                ultimo_error = RuntimeError(f"HTTP {e.code}: {cuerpo}")
                if e.code in (400, 404):
                    break
            except Exception as e:  # red caída, timeout, DNS...
                ultimo_error = e
            time.sleep(2 * (intento + 1))
        raise ConnectionError(f"No se pudo descargar {url}: {ultimo_error}")

    def _obtener(self, url: str, params: dict, ttl_s: float | None, alias: str | None = None) -> dict:
        """Devuelve {"origen", "descargado_utc", "url", "params", "json"}.
        ttl_s=None -> la caché nunca vence (histórico)."""
        clave = self._clave(url, params)
        ruta = self._ruta(clave)
        cache = self._leer(ruta)
        if cache is not None:
            edad = time.time() - cache.get("t_epoch", 0)
            if ttl_s is None or edad < ttl_s or self.offline:
                cache["origen"] = "cache" if (ttl_s is None or edad < ttl_s) else "cache_vencida"
                return cache
        if not self.offline:
            try:
                data = self._descargar(url, params)
                env = {"origen": "red", "descargado_utc": _ahora_utc(), "t_epoch": time.time(),
                       "url": url, "params": params, "json": data}
                self._escribir(ruta, env)
                if alias:
                    self._escribir(self._ruta(alias), env)
                self._indexar(clave, env)
                return env
            except ConnectionError as e:
                if self.verbose:
                    print("[clima_client] sin red:", e, file=sys.stderr)
        if cache is not None:
            cache["origen"] = "cache_vencida"
            return cache
        if alias:
            ult = self._leer(self._ruta(alias))
            if ult is not None:
                ult["origen"] = "cache_ultimo_pronostico"
                return ult
        raise ConnectionError("Sin red y sin caché para " + url + " " + json.dumps(params))

    def _indexar(self, clave: str, env: dict) -> None:
        """Índice legible de la caché: cache/json/_indice.csv (clave, descarga, url, parámetros)."""
        ruta = os.path.join(self.json_dir, "_indice.csv")
        nuevo = not os.path.exists(ruta)
        try:
            with open(ruta, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if nuevo:
                    w.writerow(["clave", "descargado_utc", "url", "params_json"])
                w.writerow([clave, env.get("descargado_utc"), env.get("url"),
                            json.dumps(env.get("params"), ensure_ascii=False, sort_keys=True)])
        except OSError:
            pass

    @staticmethod
    def _punto(punto):
        if isinstance(punto, str):
            if punto not in PUNTOS:
                raise KeyError(f"Punto desconocido {punto!r}. Opciones: {list(PUNTOS)}")
            p = PUNTOS[punto]
            return punto, p["lat"], p["lon"]
        lat, lon = punto
        return f"{lat:.4f}_{lon:.4f}", float(lat), float(lon)

    @staticmethod
    def filas(env: dict) -> list:
        """Convierte el bloque 'hourly' a lista de dicts [{time, var1, ...}]."""
        h = env["json"].get("hourly", {})
        claves = list(h.keys())
        n = len(h.get("time", []))
        return [{k: h[k][i] for k in claves} for i in range(n)]

    # ------------------------------------------------------------------ API pública
    def pronostico(self, punto, dias: int = 7, past_days: int = 2, variables=None) -> dict:
        nombre, lat, lon = self._punto(punto)
        params = {
            "latitude": lat, "longitude": lon, "timezone": TZ,
            "hourly": ",".join(variables or (VARS_HORARIAS + VARS_PRONOSTICO_EXTRA)),
            "forecast_days": dias, "past_days": past_days,
        }
        env = self._obtener(URL_FORECAST, params, TTL_PRONOSTICO_S, alias=f"pronostico_{nombre}_ultimo")
        env["filas"] = self.filas(env)
        env["punto"] = nombre
        return env

    def historico(self, punto, inicio: str, fin: str, variables=None, modelo: str | None = None,
                  elevacion: float | None = None) -> dict:
        """elevacion (m): fuerza la corrección por altura de Open-Meteo a esa cota (p. ej. la de una estación)."""
        nombre, lat, lon = self._punto(punto)
        params = {
            "latitude": lat, "longitude": lon, "timezone": TZ,
            "start_date": inicio, "end_date": fin,
            "hourly": ",".join(variables or VARS_HORARIAS),
        }
        if modelo:
            params["models"] = modelo
        if elevacion is not None:
            params["elevation"] = elevacion
        env = self._obtener(URL_ARCHIVE, params, ttl_s=None)
        env["filas"] = self.filas(env)
        env["punto"] = nombre
        return env

    # DataFrames (pandas opcional) --------------------------------------
    @staticmethod
    def _a_df(env: dict):
        import pandas as pd  # import tardío: el cliente funciona sin pandas
        df = pd.DataFrame(env["json"]["hourly"])
        df["time"] = pd.to_datetime(df["time"])  # hora LOCAL America/Bogota (UTC-5, sin DST)
        df = df.set_index("time")
        df.attrs.update({"origen": env.get("origen"), "descargado_utc": env.get("descargado_utc"),
                         "elevation": env["json"].get("elevation"), "punto": env.get("punto")})
        return df

    def pronostico_df(self, punto, **kw):
        return self._a_df(self.pronostico(punto, **kw))

    def historico_df(self, punto, inicio, fin, **kw):
        return self._a_df(self.historico(punto, inicio, fin, **kw))

    # Export CSV sin pandas ------------------------------------------------
    @staticmethod
    def guardar_csv(env: dict, ruta: str, extra: dict | None = None) -> str:
        filas = ClimaClient.filas(env)
        if not filas:
            raise ValueError("respuesta sin datos horarios")
        extra = extra or {}
        cols = list(extra.keys()) + list(filas[0].keys())
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in filas:
                r2 = dict(extra); r2.update(r)
                w.writerow(r2)
        return ruta


# ---------------------------------------------------------------------- CLI
def _descargar_todo(c: ClimaClient, anio: int = 2025):
    out = c.cache_dir
    for nombre, p in PUNTOS.items():
        # 1) histórico best_match (por defecto de Open-Meteo)
        env = c.historico(nombre, f"{anio}-01-01", f"{anio}-12-31")
        meta = {"punto": nombre, "modelo": "best_match"}
        ruta = c.guardar_csv(env, os.path.join(out, f"historico_{anio}_{nombre}.csv"), meta)
        j = env["json"]
        print(f"[hist] {nombre}: {len(env['filas'])} h, celda {j.get('latitude')},{j.get('longitude')} "
              f"elev {j.get('elevation')} m, origen={env['origen']} -> {ruta}")
        # 2) modelos alternativos para sensibilidad (ERA5-Land 0.1°, ERA5 0.25°)
        for modelo in ("era5_land", "era5"):
            try:
                envm = c.historico(nombre, f"{anio}-01-01", f"{anio}-12-31", modelo=modelo)
                rutam = c.guardar_csv(envm, os.path.join(out, f"historico_{anio}_{nombre}_{modelo}.csv"),
                                      {"punto": nombre, "modelo": modelo})
                print(f"[hist-{modelo}] {nombre}: elev {envm['json'].get('elevation')} -> {rutam}")
            except Exception as e:
                print(f"[hist-{modelo}] {nombre}: ERROR {e}")
        # 3) pronóstico actual
        envf = c.pronostico(nombre, dias=7, past_days=2)
        stamp = (envf.get("descargado_utc") or _ahora_utc()).replace(":", "").replace("-", "")
        rutaf = c.guardar_csv(envf, os.path.join(out, f"pronostico_{nombre}_{stamp}.csv"),
                              {"punto": nombre, "descargado_utc": envf.get("descargado_utc")})
        print(f"[pron] {nombre}: {len(envf['filas'])} h origen={envf['origen']} -> {rutaf}")


def _resumen_pronostico(env: dict):
    filas = env["filas"]
    print(f"Punto {env['punto']}  origen={env['origen']}  descargado_utc={env.get('descargado_utc')}")
    print("time              T(°C)  HR(%)  Td(°C)  lluvia(mm)  LWP(%)")
    for r in filas[::6][:30]:
        print(f"{r['time']}  {r.get('temperature_2m')!s:>5}  {r.get('relative_humidity_2m')!s:>5}  "
              f"{r.get('dew_point_2m')!s:>6}  {r.get('precipitation')!s:>9}  {r.get('leaf_wetness_probability')!s:>5}")


def _offline_test():
    c = ClimaClient(offline=True)
    ok = True
    for nombre in PUNTOS:
        try:
            e1 = c.pronostico(nombre)
            e2 = c.historico(nombre, "2025-01-01", "2025-12-31")
            print(f"OK sin red {nombre}: pronostico {len(e1['filas'])} h ({e1['origen']}), "
                  f"historico {len(e2['filas'])} h ({e2['origen']})")
        except ConnectionError as e:
            ok = False
            print("FALLA", nombre, e)
    # parámetros distintos a los cacheados -> debe caer al último pronóstico del punto
    e3 = c.pronostico("chia", dias=3, past_days=0)
    print("Fallback con parámetros no cacheados:", e3["origen"], len(e3["filas"]), "h")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ayuda"
    if cmd == "descargar-todo":
        _descargar_todo(ClimaClient(verbose=True))
    elif cmd == "pronostico":
        _resumen_pronostico(ClimaClient(verbose=True).pronostico(sys.argv[2] if len(sys.argv) > 2 else "chia"))
    elif cmd == "offline-test":
        sys.exit(0 if _offline_test() else 1)
    else:
        print(__doc__)
