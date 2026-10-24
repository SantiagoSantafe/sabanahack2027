"""Verificacion adversaria (3): (a) desfase horario de las estaciones IDEAM de datos.gov.co,
(b) recalculo independiente de la sensibilidad del proxy de hoja mojada de Open-Meteo frente a la estacion.

Lee raw/ideam_datosgov_2025/*.json SOLO como datos. No descarga nada.
Uso: .venv/bin/python -I reportes/verificacion-riesgo-clima_scripts/v3_ideam_utc_y_proxy.py
"""
import json
import os

import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(RAIZ, "raw", "ideam_datosgov_2025")
CACHE = os.path.join(RAIZ, "clima", "cache")
EST = ["2120500135", "2401500040", "2403500041", "0021205700", "0024035430", "0021205518"]


def cargar(var, cod):
    f = os.path.join(RAW, "%s_%s_2025.json" % (var, cod))
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    if not d:
        return None
    df = pd.DataFrame(d)[["fechaobservacion", "valorobservado"]]
    df["t"] = pd.to_datetime(df["fechaobservacion"])
    df["v"] = pd.to_numeric(df["valorobservado"], errors="coerce")
    df = df.drop_duplicates(["t", "v"])
    return df


def horario(df, how):
    h = df.set_index("t")["v"].resample("1h")
    return h.mean() if how == "mean" else h.sum(min_count=1)


def main():
    filas = []
    for cod in EST:
        om = pd.read_csv(os.path.join(CACHE, "historico_2025_est_%s.csv" % cod))
        om = om[om["modelo"] == "best_match"] if "modelo" in om else om
        om["t"] = pd.to_datetime(om["time"])
        om = om.set_index("t")
        T = cargar("temperatura", cod)
        Th = horario(T, "mean")
        prof = Th.groupby(Th.index.hour).mean()
        res = {"estacion": cod, "hora_min_T_cruda": int(prof.idxmin()), "hora_max_T_cruda": int(prof.idxmax())}
        for lag in (0, -4, -5, -6):
            s = Th.copy()
            s.index = s.index + pd.Timedelta(hours=lag)
            j = pd.concat([s.rename("ideam"), om["temperature_2m"].rename("om")], axis=1).dropna()
            res["r_T_lag%+d" % lag] = round(j["ideam"].corr(j["om"]), 3)
        # proxy de hoja mojada con desfase -5 h (0 h para la CAR)
        off = 0 if cod == "0021205518" else -5
        H = cargar("humedad", cod)
        Hh = horario(H, "mean")
        Hh.index = Hh.index + pd.Timedelta(hours=off)
        P = cargar("precipitacion", cod)
        if P is not None:
            Ph = horario(P, "sum")
            Ph.index = Ph.index + pd.Timedelta(hours=off)
        else:
            Ph = None
        j = pd.concat([Hh.rename("hr_i"), om["relative_humidity_2m"].rename("hr_o"),
                       om["precipitation"].rename("p_o")] + ([Ph.rename("p_i")] if Ph is not None else []), axis=1)
        j = j.dropna(subset=["hr_i", "hr_o"] + (["p_i"] if Ph is not None else []))
        ref = (j["hr_i"] >= 90) | ((j["p_i"] > 0) if Ph is not None else False)
        ref_hr = j["hr_i"] >= 90
        res["horas_pareadas"] = len(j)
        res["HR_max_ideam"] = round(float(j["hr_i"].max()), 1)
        for u in (85, 90):
            pred = (j["hr_o"] >= u) | (j["p_o"] >= 0.5)
            res["sens_HR%d_P05_vs_ref(HR90|lluvia>0)" % u] = round((pred & ref).sum() / max(1, ref.sum()), 3)
            res["razon_horas_OM/ref_HR%d_P05" % u] = round(pred.sum() / max(1, ref.sum()), 2)
            pred_hr = j["hr_o"] >= u
            res["sens_soloHR%d_vs_ref(HR90)" % u] = round((pred_hr & ref_hr).sum() / max(1, ref_hr.sum()), 3)
        if Ph is not None:
            res["horas_lluvia_ideam"] = int((j["p_i"] > 0).sum())
            res["horas_lluvia_om"] = int((j["p_o"] > 0).sum())
            res["razon_horas_lluvia_OM/IDEAM"] = round(res["horas_lluvia_om"] / max(1, res["horas_lluvia_ideam"]), 2)
            # lluvia horaria de Open-Meteo = suma de la hora PREVIA; probar desplazamiento de 1 h
            for sh in (0, 1, -1):
                po = j["p_o"].shift(sh)
                ok = po.notna()
                res["r_lluvia_shift%+d" % sh] = round(np.corrcoef(po[ok], j["p_i"][ok])[0, 1], 3)
        filas.append(res)
    out = pd.DataFrame(filas)
    pd.set_option("display.width", 250)
    print(out.T.to_string())
    out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida_v3_ideam.csv"), index=False)


if __name__ == "__main__":
    main()
