"""Verificacion adversaria (2): QC independiente del clima Open-Meteo 2025 y recalculo independiente
de los dias por clase de riesgo (sin importar risk.py) para compararlos con
riesgo/salidas/resumen_dias_por_clase_2025.csv y resultados/backtest/dias_riesgo_anual_2025.csv.

Uso: .venv/bin/python -I reportes/verificacion-riesgo-clima_scripts/v2_qc_y_recalculo_2025.py
"""
import math
import os

import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUNTOS = ["sotaquira", "tausa", "guasca", "chia"]


def logit_inv(z):
    return 1.0 / (1.0 + math.exp(-z))


T_GMIN = 9.3329  # minimo local de g(T) en Wilson


def wilson(w, t):
    t = max(t, T_GMIN)
    return logit_inv(-3.7 + w * (0.33 - 0.069 * t + 0.005 * t ** 2 - 9.3e-5 * t ** 3))


TABLA = [(5.0, 0.0), (10.0, 3.7 / 42), (15.0, 3.7 / 24), (20.0, 3.7 / 15), (25.0, 3.7 / 15), (30.0, 3.7 / 21), (35.0, 0.0)]


def g_ar(t):
    return float(np.interp(t, [a for a, _ in TABLA], [b for _, b in TABLA]))


def antr(w, t):
    return max(wilson(w, t), logit_inv(-3.7 + w * g_ar(t)))


def bulger(w, t):
    return logit_inv(-4.268 - 0.0901 * w + 0.0294 * w * t - 2.35e-5 * w * t ** 3)


def roya(w, t, tmin=8.0, topt=21.5, tmax=32.0, wmin=8.0, wmax=48.0):
    if t < tmin or t > tmax:
        return 0.0
    a = math.log(2) / math.log((tmax - tmin) / (topt - tmin))
    ft = (2 * (t - tmin) ** a * (topt - tmin) ** a - (t - tmin) ** (2 * a)) / (topt - tmin) ** (2 * a)
    ft = min(1.0, max(0.0, ft))
    if ft <= 0 or wmin / ft > wmax:
        return 0.0
    i = w * ft / wmin
    return 0.15 ** (3.5 * 0.15 ** (0.75 * i))


UMB = {"antracnosis": (0.15, 0.5), "botrytis": (0.5, 0.7), "roya": (0.2, 0.5)}


def clase(x, enf):
    m, a = UMB[enf]
    return "alto" if x >= a else ("medio" if x >= m else "bajo")


def periodos(df, umbral_hr, umbral_ll, max_int=3):
    """Periodos de mojadura: hora mojada si HR>=u o lluvia>=p; <=3 h secas no cortan; LWD = horas mojadas."""
    moj = ((df["HR"] >= umbral_hr) | (df["lluvia"] >= umbral_ll)).values
    out, act, ult = [], None, None
    for i in np.flatnonzero(moj):
        if act is not None and i - ult - 1 > max_int:
            out.append(act)
            act = None
        if act is None:
            act = []
        act.append(i)
        ult = i
    if act:
        out.append(act)
    return out


def dias_por_clase(df, umbral_hr, umbral_ll):
    fechas = df["time"].dt.date.values
    T = df["T"].values
    mejor = {}
    for idx in periodos(df, umbral_hr, umbral_ll):
        n, s = 0, 0.0
        for i in idx:
            n += 1
            s += T[i]
            d = fechas[i]
            tm = s / n
            v = {"antracnosis": antr(n, tm), "botrytis": bulger(n, tm), "roya": roya(n, tm)}
            m = mejor.setdefault(d, {k: 0.0 for k in v})
            for k in v:
                m[k] = max(m[k], v[k])
    dias = sorted(set(fechas))
    res = {}
    for enf in UMB:
        cls = [clase(mejor.get(d, {}).get(enf, 0.0), enf) for d in dias]
        res[enf] = {c: cls.count(c) for c in ("bajo", "medio", "alto")}
    alto_any = sum(1 for d in dias if any(clase(mejor.get(d, {}).get(e, 0.0), e) == "alto" for e in UMB))
    res["algun_alto"] = alto_any
    return res, periodos(df, umbral_hr, umbral_ll)


def main():
    print("== QC independiente Open-Meteo 2025 (best_match) ==")
    qc = []
    datos = {}
    for p in PUNTOS:
        raw = pd.read_csv(os.path.join(RAIZ, "clima", "cache", "historico_2025_%s.csv" % p))
        raw["time"] = pd.to_datetime(raw["time"])
        modelos = raw["modelo"].unique().tolist()
        df = raw[raw["modelo"] == "best_match"].copy()
        paso = df["time"].diff().dropna().dt.total_seconds().unique()
        hmin = df.loc[df.groupby(df["time"].dt.date)["temperature_2m"].idxmin(), "time"].dt.hour
        hmax = df.loc[df.groupby(df["time"].dt.date)["temperature_2m"].idxmax(), "time"].dt.hour
        fila = {
            "punto": p, "modelos_en_csv": ",".join(modelos), "n": len(df),
            "dup": int(df["time"].duplicated().sum()), "pasos_distintos_s": ",".join(str(int(x)) for x in paso),
            "nan": int(df[["temperature_2m", "relative_humidity_2m", "precipitation"]].isna().sum().sum()),
            "inicio": str(df["time"].min()), "fin": str(df["time"].max()),
            "T_media": round(df["temperature_2m"].mean(), 2),
            "HR_media": round(df["relative_humidity_2m"].mean(), 1),
            "lluvia_total_mm": round(df["precipitation"].sum(), 0),
            "Td_gt_T": int((df["dew_point_2m"] > df["temperature_2m"] + 1e-9).sum()),
            "HR_fuera_0_100": int(((df["relative_humidity_2m"] < 0) | (df["relative_humidity_2m"] > 100)).sum()),
            "hora_moda_Tmin": int(hmin.mode().iloc[0]), "hora_moda_Tmax": int(hmax.mode().iloc[0]),
            "h_HR85": int((df["relative_humidity_2m"] >= 85).sum()),
            "h_HR90": int((df["relative_humidity_2m"] >= 90).sum()),
            "h_HR95": int((df["relative_humidity_2m"] >= 95).sum()),
            "h_lluvia_gt0": int((df["precipitation"] > 0).sum()),
            "h_lluvia_ge05": int((df["precipitation"] >= 0.5).sum()),
            "frac_mojada_HR90_P0": round(((df["relative_humidity_2m"] >= 90) | (df["precipitation"] > 0)).mean(), 3),
            "frac_mojada_HR90_P05": round(((df["relative_humidity_2m"] >= 90) | (df["precipitation"] >= 0.5)).mean(), 3),
        }
        qc.append(fila)
        datos[p] = df.rename(columns={"temperature_2m": "T", "relative_humidity_2m": "HR", "precipitation": "lluvia"})
    qc = pd.DataFrame(qc)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 50)
    print(qc.T.to_string())

    print("\n== Recalculo independiente de dias por clase 2025 vs riesgo/salidas ==")
    ref = pd.read_csv(os.path.join(RAIZ, "riesgo", "salidas", "resumen_dias_por_clase_2025.csv"))
    filas = []
    for crit, (u, ll) in {"HR85_P05": (85, 0.5), "HR90_P05": (90, 0.5), "HR95_P05": (95, 0.5), "HR90_P0": (90, 1e-9)}.items():
        for p in PUNTOS:
            res, per = dias_por_clase(datos[p], u, ll)
            largo = max(len(x) for x in per)
            for enf in UMB:
                r = ref[(ref.punto == p) & (ref.criterio_mojadura == crit) & (ref.enfermedad == enf)]
                filas.append({"criterio": crit, "punto": p, "enfermedad": enf,
                              "medio_mio": res[enf]["medio"], "alto_mio": res[enf]["alto"],
                              "medio_ref": int(r.dias_medio.iloc[0]) if len(r) else None,
                              "alto_ref": int(r.dias_alto.iloc[0]) if len(r) else None,
                              "n_periodos": len(per), "periodo_max_horas_mojadas": largo,
                              "dias_algun_alto": res["algun_alto"]})
    out = pd.DataFrame(filas)
    out["coincide"] = (out.medio_mio == out.medio_ref) & (out.alto_mio == out.alto_ref)
    print(out.to_string(index=False))
    print("Coincidencias: %d de %d" % (out.coincide.sum(), len(out)))
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida_v2_recalculo.csv")
    out.to_csv(destino, index=False)
    qc.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida_v2_qc.csv"), index=False)
    print("->", destino)


if __name__ == "__main__":
    main()
