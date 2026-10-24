"""
analisis_clima.py -- QC de Open-Meteo 2025, resumen mensual, proxy de hoja mojada y comparación con IDEAM.
Ejecutar:  /usr/bin/python3 -I /Users/santiagosantafe/Downloads/SabanaHack/datos/clima/scripts/analisis_clima.py
(-I excluye site-packages de usuario; se agregan explícitamente porque ahí están pandas/matplotlib del sistema).
Salidas: clima/qc/, clima/derivados/, clima/graficas/
"""
import site
import sys

sys.path.append(site.getusersitepackages())
import warnings  # noqa: E402

warnings.filterwarnings("ignore")
import glob  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BASE = "/Users/santiagosantafe/Downloads/SabanaHack/datos/clima"
CACHE = os.path.join(BASE, "cache")
QC = os.path.join(BASE, "qc")
DER = os.path.join(BASE, "derivados")
GRAF = os.path.join(BASE, "graficas")
RAW_IDEAM = "/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/ideam_datosgov_2025"
for d in (QC, DER, GRAF):
    os.makedirs(d, exist_ok=True)
sys.path.insert(0, BASE)
from clima_client import PUNTOS  # noqa: E402

UMBRALES = (85, 90, 95)
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# ---------------------------------------------------------------- estilo (skill dataviz, paleta de referencia)
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
SEQ = {85: "#86b6ef", 90: "#2a78d6", 95: "#104281"}
COL_PUNTO = {k: CAT[i] for i, k in enumerate(PUNTOS)}
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "legend.frameon": False,
})


def guardar_fig(fig, nombre):
    ruta = os.path.join(GRAF, nombre)
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return ruta


# ---------------------------------------------------------------- utilidades
def amanecer_local_h(fechas, lat, lon, tz_h=-5.0):
    """Hora local de salida del sol (algoritmo NOAA simplificado)."""
    n = np.asarray(fechas.dayofyear, dtype=float)
    g = 2 * np.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    la = math.radians(lat)
    ha = np.degrees(np.arccos(np.cos(np.radians(90.833)) / (np.cos(la) * np.cos(decl)) - np.tan(la) * np.tan(decl)))
    sunrise_utc_min = 720 - 4 * (lon + ha) - eqt
    return (sunrise_utc_min + tz_h * 60) / 60.0


def cargar_om(nombre, modelo=None):
    suf = f"_{modelo}" if modelo else ""
    df = pd.read_csv(os.path.join(CACHE, f"historico_2025_{nombre}{suf}.csv"), parse_dates=["time"])
    return df


def hora_extremos(df, col="temperature_2m"):
    d = df.set_index("time")[col].dropna()
    g = d.groupby(d.index.date)
    hmin = g.idxmin().map(lambda t: t.hour)
    hmax = g.idxmax().map(lambda t: t.hour)
    return hmin, hmax


RANGOS = {  # rangos físicos plausibles para 2.400-3.300 m en los Andes colombianos (criterio propio)
    "temperature_2m": (-10, 35), "relative_humidity_2m": (0, 100), "dew_point_2m": (-25, 25),
    "precipitation": (0, 80), "wind_speed_10m": (0, 120), "leaf_wetness_probability": (0, 100),
}


# ================================================================ 1. QC Open-Meteo
def qc_openmeteo():
    filas = []
    perfiles = {}
    hmins = {}
    for nombre, p in PUNTOS.items():
        for modelo in (None, "era5_land", "era5"):
            df = cargar_om(nombre, modelo)
            esperado = pd.date_range("2025-01-01 00:00", "2025-12-31 23:00", freq="h")
            t = df["time"]
            faltantes = len(esperado.difference(pd.DatetimeIndex(t)))
            dup = int(t.duplicated().sum())
            paso = t.diff().dropna().value_counts()
            r = {"punto": nombre, "modelo": modelo or "best_match", "filas": len(df), "esperadas": len(esperado),
                 "timestamps_faltantes": faltantes, "duplicados": dup,
                 "paso_unico_1h": bool(len(paso) == 1 and paso.index[0] == pd.Timedelta("1h"))}
            for c, (lo, hi) in RANGOS.items():
                s = df[c]
                r[f"nan_{c}"] = int(s.isna().sum())
                r[f"fuera_rango_{c}"] = int(((s < lo) | (s > hi)).sum())
            r["td_mayor_que_t"] = int((df["dew_point_2m"] > df["temperature_2m"] + 0.2).sum())
            hmin, hmax = hora_extremos(df)
            r["hora_moda_Tmin"] = int(hmin.mode().iloc[0])
            r["pct_dias_Tmin_entre_4y7h"] = round(100 * hmin.between(4, 7).mean(), 1)
            r["hora_moda_Tmax"] = int(hmax.mode().iloc[0])
            dias = pd.DatetimeIndex(pd.to_datetime(hmin.index))
            sr = amanecer_local_h(dias, p["lat"], p["lon"])
            r["amanecer_medio_local_h"] = round(float(np.mean(sr)), 2)
            r["mediana_hTmin_menos_amanecer_h"] = round(float(np.median(hmin.values - sr)), 2)
            filas.append(r)
            if modelo is None:
                d = df.set_index("time")["temperature_2m"]
                perfiles[nombre] = (d - d.groupby(d.index.date).transform("mean")).groupby(d.index.hour).mean()
                hmins[nombre] = hmin
    q = pd.DataFrame(filas)
    q.to_csv(os.path.join(QC, "qc_openmeteo.csv"), index=False)

    # zona horaria declarada por la API
    offs = {}
    for f in glob.glob(os.path.join(CACHE, "json", "*.json")):
        try:
            j = json.load(open(f))
            offs[(j["json"].get("timezone"), j["json"].get("utc_offset_seconds"))] = offs.get(
                (j["json"].get("timezone"), j["json"].get("utc_offset_seconds")), 0) + 1
        except Exception:
            pass

    # Gráfica ciclo diario
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    ax = axs[0]
    sr_med = np.mean([amanecer_local_h(pd.date_range("2025-01-01", "2025-12-31"), p["lat"], p["lon"]).mean()
                      for p in PUNTOS.values()])
    ax.axvspan(sr_med - 0.25, sr_med + 0.25, color=GRID, alpha=0.9, lw=0)
    ax.text(sr_med + 0.4, 5.6, "amanecer medio\n~%.1f h local" % sr_med, color=INK2, fontsize=8)
    for nombre, prof in perfiles.items():
        ax.plot(prof.index, prof.values, color=COL_PUNTO[nombre], label=PUNTOS[nombre]["nombre"].split(" (")[0])
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hora local (America/Bogota, UTC-5)")
    ax.set_ylabel("T - media diaria (°C)")
    ax.set_title("Ciclo diario medio de temperatura 2025")
    ax.legend(fontsize=8, loc="upper left")
    ax = axs[1]
    w = 0.2
    for i, (nombre, hm) in enumerate(hmins.items()):
        cnt = hm.value_counts().reindex(range(24), fill_value=0)
        ax.bar(np.arange(24) + (i - 1.5) * w, cnt.values, width=w, color=COL_PUNTO[nombre],
               label=PUNTOS[nombre]["nombre"].split(" (")[0])
    ax.set_xlim(-0.5, 12.5)
    ax.set_xticks(range(0, 13))
    ax.set_xlabel("Hora local de la T mínima diaria")
    ax.set_ylabel("Días (de 365)")
    ax.set_title("¿Cuándo ocurre la mínima? (control de zona horaria)")
    ax.legend(fontsize=8)
    guardar_fig(fig, "qc_ciclo_diario_temperatura.png")
    return q, offs


# ================================================================ 2. Resumen mensual
def resumen_mensual():
    todos = []
    for nombre in PUNTOS:
        df = cargar_om(nombre).set_index("time")
        m = df.index.month
        daily = df["temperature_2m"].resample("D").agg(["min", "max"])
        r = pd.DataFrame({
            "T_media": df["temperature_2m"].groupby(m).mean(),
            "Tmin_media_diaria": daily["min"].groupby(daily.index.month).mean(),
            "Tmax_media_diaria": daily["max"].groupby(daily.index.month).mean(),
            "HR_media": df["relative_humidity_2m"].groupby(m).mean(),
            "lluvia_mm": df["precipitation"].groupby(m).sum(),
            "horas_lluvia_gt0": (df["precipitation"] > 0).groupby(m).sum(),
            "viento_medio_kmh": df["wind_speed_10m"].groupby(m).mean(),
            "LWP_media_pct": df["leaf_wetness_probability"].groupby(m).mean(),
        })
        for u in UMBRALES:
            r[f"horas_HR_ge{u}"] = (df["relative_humidity_2m"] >= u).groupby(m).sum()
        r.index.name = "mes"
        r = r.reset_index()
        r.insert(0, "punto", nombre)
        todos.append(r)
    res = pd.concat(todos, ignore_index=True).round(2)
    res.to_csv(os.path.join(QC, "resumen_mensual_openmeteo_2025.csv"), index=False)
    anual = res.groupby("punto").agg(T_media=("T_media", "mean"), HR_media=("HR_media", "mean"),
                                     lluvia_mm=("lluvia_mm", "sum"), h_HR85=("horas_HR_ge85", "sum"),
                                     h_HR90=("horas_HR_ge90", "sum"), h_HR95=("horas_HR_ge95", "sum"),
                                     h_lluvia=("horas_lluvia_gt0", "sum")).round(1)
    anual.to_csv(os.path.join(QC, "resumen_anual_openmeteo_2025.csv"))

    fig, axs = plt.subplots(2, 2, figsize=(12, 7.5), sharex=True)
    specs = [("T_media", "Temperatura media (°C)"), ("HR_media", "Humedad relativa media (%)"),
             ("lluvia_mm", "Lluvia mensual (mm)"), ("horas_HR_ge90", "Horas con HR ≥ 90 % por mes")]
    for ax, (col, tit) in zip(axs.flat, specs):
        if col == "lluvia_mm":
            w = 0.2
            for i, nombre in enumerate(PUNTOS):
                s = res[res.punto == nombre]
                ax.bar(s["mes"] + (i - 1.5) * w, s[col], width=w, color=COL_PUNTO[nombre],
                       label=PUNTOS[nombre]["nombre"].split(" (")[0])
        else:
            for nombre in PUNTOS:
                s = res[res.punto == nombre]
                ax.plot(s["mes"], s[col], marker="o", ms=4, color=COL_PUNTO[nombre],
                        label=PUNTOS[nombre]["nombre"].split(" (")[0])
        ax.set_title(tit)
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES)
    axs[0, 0].legend(fontsize=8, ncol=2)
    fig.suptitle("Open-Meteo histórico 2025 (best_match), hora local", color=INK2, fontsize=10, y=1.0)
    fig.tight_layout()
    guardar_fig(fig, "resumen_mensual_2025.png")
    return res, anual


# ================================================================ 3. Proxy de hoja mojada
def eventos(serie_bool, temp):
    """Corridas consecutivas de horas mojadas (sin tolerancia a interrupciones)."""
    s = serie_bool.astype(int)
    grp = (s.diff() != 0).cumsum()
    ev = []
    for _, g in s.groupby(grp):
        if g.iloc[0] == 1:
            ev.append({"inicio": g.index[0], "fin": g.index[-1], "duracion_h": len(g),
                       "T_media_evento": round(float(temp.loc[g.index].mean()), 2)})
    return pd.DataFrame(ev)


def hoja_mojada():
    mens, conf, ev_all, dia_all = [], [], [], []
    rh_lwp = {}
    for nombre in PUNTOS:
        df = cargar_om(nombre).set_index("time")
        rh, pr, lwp, t = (df["relative_humidity_2m"], df["precipitation"],
                          df["leaf_wetness_probability"], df["temperature_2m"])
        h = pd.DataFrame({"T": t, "HR": rh, "lluvia": pr, "LWP": lwp})
        for u in UMBRALES:
            h[f"mojada_HR{u}"] = ((rh >= u) | (pr > 0)).astype(int)
            h[f"solo_HR{u}"] = (rh >= u).astype(int)
        h["mojada_lluvia"] = (pr > 0).astype(int)
        # Definiciones RECOMENDADAS tras validar con IDEAM (lluvia >= 0,5 mm evita la llovizna espuria del modelo)
        for u in (85, 90):
            h[f"mojada_HR{u}_P05"] = ((rh >= u) | (pr >= 0.5)).astype(int)
        for k in (30, 50, 70):
            h[f"mojada_LWP{k}"] = (lwp >= k).astype(int)
        h.to_csv(os.path.join(DER, f"hoja_mojada_horaria_{nombre}.csv"))

        mm = h.groupby(h.index.month)[[c for c in h.columns if c.startswith(("mojada", "solo"))]].sum()
        mm.index.name = "mes"
        mm = mm.reset_index()
        mm.insert(0, "punto", nombre)
        mens.append(mm)

        # concordancia horaria proxy vs LWP>=50 (LWP es otro producto de modelo, NO observación)
        ref = h["mojada_LWP50"] == 1
        for u in UMBRALES:
            pro = h[f"mojada_HR{u}"] == 1
            tp, fp = int((pro & ref).sum()), int((pro & ~ref).sum())
            fn, tn = int((~pro & ref).sum()), int((~pro & ~ref).sum())
            n = tp + fp + fn + tn
            po = (tp + tn) / n
            pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / n ** 2
            corr_m = np.corrcoef(h[f"mojada_HR{u}"].groupby(h.index.month).sum(),
                                 h["mojada_LWP50"].groupby(h.index.month).sum())[0, 1]
            conf.append({"punto": nombre, "umbral_HR": u, "horas_proxy": tp + fp, "horas_LWP50": tp + fn,
                         "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                         "sensibilidad_vs_LWP50": round(tp / (tp + fn), 3) if tp + fn else None,
                         "precision_vs_LWP50": round(tp / (tp + fp), 3) if tp + fp else None,
                         "exactitud": round(po, 3), "kappa": round((po - pe) / (1 - pe), 3),
                         "r_mensual": round(float(corr_m), 3),
                         "pct_horas_mojadas_solo_por_lluvia": round(
                             100 * float(((pr > 0) & (rh < u)).sum()) / max(1, int(pro.sum())), 1)})

        # eventos y resumen diario (insumo para modelos de infección: duración de mojadura + T)
        crit = {f"HR{u}": h[f"mojada_HR{u}"] == 1 for u in UMBRALES}
        crit["LWP50"] = h["mojada_LWP50"] == 1
        crit["HR85_P05"] = h["mojada_HR85_P05"] == 1
        crit["HR90_P05"] = h["mojada_HR90_P05"] == 1
        for k, b in crit.items():
            e = eventos(b, t)
            if len(e):
                e.insert(0, "criterio", k)
                e.insert(0, "punto", nombre)
                ev_all.append(e)
        dd = pd.DataFrame({
            "T_media": t.resample("D").mean(), "T_min": t.resample("D").min(), "T_max": t.resample("D").max(),
            "HR_media": rh.resample("D").mean(), "lluvia_mm": pr.resample("D").sum(),
            "LWP_media": lwp.resample("D").mean(),
        })
        for u in UMBRALES:
            dd[f"horas_mojadas_HR{u}"] = h[f"mojada_HR{u}"].resample("D").sum()
        dd["horas_mojadas_LWP50"] = h["mojada_LWP50"].resample("D").sum()
        for u in (85, 90):
            dd[f"horas_mojadas_HR{u}_P05"] = h[f"mojada_HR{u}_P05"].resample("D").sum()
            dd[f"horas_soloHR{u}"] = h[f"solo_HR{u}"].resample("D").sum()
        w90 = h["mojada_HR90"] == 1
        dd["T_media_horas_mojadas_HR90"] = t.where(w90).resample("D").mean()
        dd.index.name = "fecha"
        dd = dd.reset_index()
        dd.insert(0, "punto", nombre)
        dia_all.append(dd)
        rh_lwp[nombre] = h

    mens = pd.concat(mens, ignore_index=True)
    mens.to_csv(os.path.join(DER, "hoja_mojada_mensual_2025.csv"), index=False)
    conf = pd.DataFrame(conf)
    conf.to_csv(os.path.join(DER, "proxy_vs_LWP50_concordancia.csv"), index=False)
    ev = pd.concat(ev_all, ignore_index=True)
    ev.to_csv(os.path.join(DER, "eventos_mojadura_2025.csv"), index=False)
    dia = pd.concat(dia_all, ignore_index=True).round(2)
    dia.to_csv(os.path.join(DER, "clima_diario_mojadura_2025.csv"), index=False)

    # sensibilidad: cuántas horas/mes cambian entre umbrales
    sens = []
    for nombre in PUNTOS:
        s = mens[mens.punto == nombre].set_index("mes")
        for a, b in ((85, 90), (90, 95), (85, 95)):
            dif = s[f"mojada_HR{a}"] - s[f"mojada_HR{b}"]
            sens.append({"punto": nombre, "de": a, "a": b,
                         "horas_mes_media_umbral_bajo": round(s[f"mojada_HR{a}"].mean(), 1),
                         "horas_mes_media_umbral_alto": round(s[f"mojada_HR{b}"].mean(), 1),
                         "dif_media_h_mes": round(dif.mean(), 1), "dif_min_h_mes": int(dif.min()),
                         "dif_max_h_mes": int(dif.max()),
                         "cambio_relativo_pct": round(100 * dif.sum() / s[f"mojada_HR{a}"].sum(), 1)})
        ev_n = ev[(ev.punto == nombre)]
        for k in ["HR85", "HR90", "HR95", "LWP50"]:
            e = ev_n[ev_n.criterio == k]
            sens.append({"punto": nombre, "de": k, "a": "eventos",
                         "horas_mes_media_umbral_bajo": len(e), "horas_mes_media_umbral_alto": None,
                         "dif_media_h_mes": round(e.duracion_h.median(), 1) if len(e) else None,
                         "dif_min_h_mes": int((e.duracion_h >= 6).sum()), "dif_max_h_mes": int((e.duracion_h >= 12).sum()),
                         "cambio_relativo_pct": None})
    sens = pd.DataFrame(sens)
    sens.to_csv(os.path.join(DER, "sensibilidad_umbral_mojadura.csv"), index=False)

    # sensibilidad al umbral de lluvia (Open-Meteo reparte llovizna de 0,1 mm en muchas horas)
    sl = []
    for nombre in PUNTOS:
        h = rh_lwp[nombre]
        for u in UMBRALES:
            for pth in (0.0, 0.2, 0.5, 1.0):
                w = (h["HR"] >= u) | (h["lluvia"] > pth if pth == 0 else h["lluvia"] >= pth)
                sl.append({"punto": nombre, "umbral_HR": u, "umbral_lluvia_mm": f">{pth}" if pth == 0 else f">={pth}",
                           "horas_mojadas_anio": int(w.sum()), "horas_mes_media": round(w.sum() / 12, 1),
                           "horas_lluvia_sobre_umbral": int((h["lluvia"] > 0).sum() if pth == 0 else (h["lluvia"] >= pth).sum())})
    sl = pd.DataFrame(sl)
    sl.to_csv(os.path.join(DER, "sensibilidad_umbral_lluvia.csv"), index=False)
    print("== Sensibilidad lluvia\n", sl.pivot_table(index=["punto", "umbral_HR"], columns="umbral_lluvia_mm",
                                                   values="horas_mes_media").to_string())

    # Gráfica 1: horas mojadas por mes según criterio (small multiples por punto)
    fig, axs = plt.subplots(2, 2, figsize=(12, 7.5), sharex=True, sharey=True)
    for ax, nombre in zip(axs.flat, PUNTOS):
        s = mens[mens.punto == nombre]
        for u in UMBRALES:
            ax.plot(s["mes"], s[f"mojada_HR{u}"], color=SEQ[u], marker="o", ms=4, label=f"HR ≥ {u} % o lluvia > 0")
        ax.plot(s["mes"], s["mojada_LWP50"], color=CAT[1], ls="--", label="Open-Meteo LWP ≥ 50 %")
        ax.plot(s["mes"], s["mojada_lluvia"], color=INK2, ls=":", lw=1.5, label="solo lluvia > 0")
        ax.set_title(PUNTOS[nombre]["nombre"].split(" - ")[0])
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES, fontsize=8)
    axs[0, 0].set_ylabel("Horas de hoja mojada por mes")
    axs[1, 0].set_ylabel("Horas de hoja mojada por mes")
    axs[0, 0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Proxy de hoja mojada 2025: sensibilidad al umbral de HR (Open-Meteo best_match)", y=1.0)
    fig.tight_layout()
    guardar_fig(fig, "hoja_mojada_sensibilidad_umbral.png")

    # Gráfica 2: relación HR -> LWP (todas las horas, todos los puntos)
    allh = pd.concat(rh_lwp.values())
    bins = list(range(40, 101, 5))
    allh["HR_bin"] = pd.cut(allh["HR"], bins=bins, right=False, include_lowest=True)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for lab, sub, col in (("sin lluvia", allh[allh.lluvia == 0], CAT[0]), ("con lluvia > 0", allh[allh.lluvia > 0], CAT[1])):
        g = sub.groupby("HR_bin")["LWP"]
        x = [b.left + 2.5 for b in g.mean().index]
        ax.plot(x, g.mean().values, marker="o", ms=5, color=col, label=f"LWP medio, {lab}")
        ax.fill_between(x, g.quantile(0.25).values, g.quantile(0.75).values, color=col, alpha=0.15, lw=0)
    for u in UMBRALES:
        ax.axvline(u, color=SEQ[u], lw=1.2, ls="--")
        ax.text(u + 0.3, 3, f"{u} %", color=INK2, fontsize=8)
    ax.set_xlabel("Humedad relativa horaria (%)")
    ax.set_ylabel("leaf_wetness_probability (%)")
    ax.set_title("HR horaria vs leaf_wetness_probability de Open-Meteo (banda P25-P75)")
    fig.text(0.5, -0.06, "Con HR > 80 % la LWP baja: la fórmula de Open-Meteo multiplica por un factor de temperatura "
             "(0 a 5 °C, 1 a 15 °C)\ny las horas más húmedas son las noches frías de altiplano (T media en horas HR ≥ 90 %: 8,3-10,4 °C). "
             "4 puntos, 8.760 h c/u, 2025.", ha="center", color=INK2, fontsize=8)
    ax.legend(fontsize=8, loc="upper left")
    guardar_fig(fig, "hoja_mojada_HR_vs_LWP.png")
    return mens, conf, sens, ev


# ================================================================ 4. Comparación IDEAM
EST_PUNTO = {"0021205700": "guasca", "2120500135": "chia", "2403500041": "sotaquira",
             "0024035430": "sotaquira", "2401500040": "tausa", "0021205518": "tausa"}


def offset_ideam_h(entidad):
    """Desfase aplicado a fechaobservacion para llevarla a hora local (UTC-5).
    Hallazgo empírico (este análisis): en estaciones de la entidad IDEAM la correlación con Open-Meteo
    y la hora de la T mínima solo cuadran si fechaobservacion se interpreta como UTC (-5 h);
    en la estación de la CAR (Salitre) ya viene en hora local. Los metadatos del dataset no lo dicen."""
    return -5 if "INSTITUTO DE HIDROLOG" in entidad.upper() else 0


def cargar_ideam(var, codigo, offset_h=0):
    f = os.path.join(RAW_IDEAM, f"{var}_{codigo}_2025.json")
    if not os.path.exists(f):
        return None, {}
    d = pd.DataFrame(json.load(open(f)))
    if d.empty:
        return None, {"filas": 0}
    info = {"filas_crudas": len(d), "sensores": "; ".join(sorted(set(d["descripcionsensor"].astype(str)))),
            "coords": "; ".join(sorted(set(d["latitud"].astype(str) + "," + d["longitud"].astype(str))))}
    d["t"] = pd.to_datetime(d["fechaobservacion"]) + pd.Timedelta(hours=offset_h)
    d["v"] = pd.to_numeric(d["valorobservado"], errors="coerce")
    n0 = len(d)
    d = d.drop_duplicates(subset=["t", "v"])
    info["duplicados_exactos"] = n0 - len(d)
    info["duplicados_conflictivos"] = int(d["t"].duplicated().sum())
    minutos = d["t"].dt.minute
    info["minutos_distintos"] = int(minutos.nunique())
    d = d.set_index("t").sort_index()
    if var == "precipitacion":
        paso = d.index.to_series().diff().dropna().dt.total_seconds().div(60).mode()
        info["paso_min_moda"] = float(paso.iloc[0]) if len(paso) else None
        # medias por marca de tiempo (duplicados conflictivos) y luego suma horaria
        s = d["v"].groupby(level=0).mean()
        hh = s.resample("h").agg(["sum", "count"])
        hh = hh[hh["count"] > 0]
        out = hh["sum"]
        info["obs_por_hora_mediana"] = float(hh["count"].median())
    else:
        out = d["v"].groupby(level=0).mean().resample("h").mean().dropna()
    info["horas_con_dato"] = int(out.notna().sum())
    return out, info


GRILLA = []
# Estaciones con sensor de HR que no llega a saturación (máx. < 95 %): sesgan el conteo de horas húmedas.
EST_SOSPECHOSAS_HR = ["0024035430", "0021205700"]


def comparar_ideam():
    cat = {e["codigo"]: e for e in json.load(open(os.path.join(RAW_IDEAM, "catalogo_estaciones.json")))}
    filas, mens, horarios = [], [], {}
    for cod, punto in EST_PUNTO.items():
        off = offset_ideam_h(cat[cod]["entidad"])
        T, iT = cargar_ideam("temperatura", cod, off)
        H, iH = cargar_ideam("humedad", cod, off)
        P, iP = cargar_ideam("precipitacion", cod, off)
        om = pd.read_csv(os.path.join(CACHE, f"historico_2025_est_{cod}.csv"), parse_dates=["time"]).set_index("time")
        # diagnóstico: desfase (h) que maximiza la correlación horaria de T con Open-Meteo, sobre datos crudos
        T0, _ = cargar_ideam("temperatura", cod, 0)
        lag_best, r_best, r_lag0 = None, -2, None
        if T0 is not None:
            for lag in range(-8, 9):
                ss = T0.copy()
                ss.index = ss.index + pd.Timedelta(hours=lag)
                jj = pd.concat([ss.rename("o"), om["temperature_2m"].rename("m")], axis=1, join="inner").dropna()
                rr = jj.corr().iloc[0, 1]
                if lag == 0:
                    r_lag0 = round(rr, 3)
                if rr > r_best:
                    lag_best, r_best = lag, rr
        variantes = [("best_match", om)]
        f_elev = os.path.join(CACHE, f"historico_2025_est_{cod}_elevest.csv")
        if os.path.exists(f_elev):
            variantes.append(("best_match_elev_estacion",
                              pd.read_csv(f_elev, parse_dates=["time"]).set_index("time")))
        for vname, omv in variantes:
            r = {"estacion": cod, "nombre": cat[cod]["nombre"], "punto_asociado": punto, "variante_OM": vname,
                 "alt_estacion_m": float(cat[cod]["altitud"]), "tecnologia": cat[cod]["tecnologia"],
                 "entidad": cat[cod]["entidad"], "offset_aplicado_h": off,
                 "diag_lag_optimo_h": lag_best, "diag_r_T_lag_optimo": round(r_best, 3), "diag_r_T_sin_desfase": r_lag0}
            for var, s, info, col in (("T", T, iT, "temperature_2m"), ("HR", H, iH, "relative_humidity_2m")):
                if s is None:
                    continue
                lo, hi = (-10, 35) if var == "T" else (0, 100)
                fuera = int(((s < lo) | (s > hi)).sum())
                s = s[(s >= lo) & (s <= hi)]
                j = pd.concat([s.rename("obs"), omv[col].rename("om")], axis=1, join="inner").dropna()
                e = j["om"] - j["obs"]
                r.update({f"{var}_horas_pareadas": len(j), f"{var}_fuera_rango_ideam": fuera,
                          f"{var}_sesgo_OM_menos_IDEAM": round(e.mean(), 2), f"{var}_MAE": round(e.abs().mean(), 2),
                          f"{var}_RMSE": round(float(np.sqrt((e ** 2).mean())), 2),
                          f"{var}_r": round(j.corr().iloc[0, 1], 3),
                          f"{var}_sensor": info.get("sensores"), f"{var}_dup_exactos": info.get("duplicados_exactos"),
                          f"{var}_dup_conflictivos": info.get("duplicados_conflictivos")})
                if var == "T":
                    jd = j.resample("D").agg(["min", "max", "count"])
                    jd = jd[jd[("obs", "count")] >= 20]
                    r["Tmin_sesgo"] = round((jd[("om", "min")] - jd[("obs", "min")]).mean(), 2)
                    r["Tmax_sesgo"] = round((jd[("om", "max")] - jd[("obs", "max")]).mean(), 2)
                    hmin = s.groupby(s.index.date).idxmin().map(lambda x: x.hour)
                    cnt = s.groupby(s.index.date).count()
                    hmin = hmin[cnt >= 20]
                    r["IDEAM_hora_moda_Tmin"] = int(hmin.mode().iloc[0]) if len(hmin) else None
                if var == "HR" and T is not None:
                    jj = pd.concat([s.rename("hr"), T.rename("t")], axis=1, join="inner").dropna()
                    r["IDEAM_corr_HR_vs_T"] = round(jj.corr().iloc[0, 1], 3)
                    r["HR_horas_ge90_IDEAM"] = int((j["obs"] >= 90).sum())
                    r["HR_horas_ge90_OM"] = int((j["om"] >= 90).sum())
                    r["HR_max_IDEAM"] = float(s.max())
            if P is not None:
                j = pd.concat([P.rename("obs"), omv["precipitation"].rename("om")], axis=1, join="inner").dropna()
                r.update({"P_horas_pareadas": len(j), "P_paso_min": iP.get("paso_min_moda"),
                          "P_obs_por_hora_mediana": iP.get("obs_por_hora_mediana"),
                          "P_total_IDEAM_mm": round(j["obs"].sum(), 1), "P_total_OM_mm": round(j["om"].sum(), 1),
                          "P_horas_lluvia_IDEAM": int((j["obs"] > 0).sum()), "P_horas_lluvia_OM": int((j["om"] > 0).sum())})
            # concordancia del proxy de mojadura (HR>=90 o lluvia>0), IDEAM como referencia
            if H is not None:
                hh = H[(H >= 0) & (H <= 100)]
                base = pd.concat([hh.rename("hr_o"), omv["relative_humidity_2m"].rename("hr_m"),
                                  omv["precipitation"].rename("p_m")], axis=1, join="inner").dropna()
                if P is not None:
                    base = base.join(P.rename("p_o"), how="inner")
                else:
                    base["p_o"] = 0.0
                for u in UMBRALES:
                    o = (base.hr_o >= u) | (base.p_o > 0)
                    m = (base.hr_m >= u) | (base.p_m > 0)
                    tp, fp, fn = int((o & m).sum()), int((~o & m).sum()), int((o & ~m).sum())
                    r[f"mojada{u}_horas_IDEAM"] = int(o.sum())
                    r[f"mojada{u}_horas_OM"] = int(m.sum())
                    r[f"mojada{u}_sensibilidad_OM"] = round(tp / (tp + fn), 3) if tp + fn else None
                    r[f"mojada{u}_precision_OM"] = round(tp / (tp + fp), 3) if tp + fp else None
                r["mojada_horas_pareadas"] = len(base)
                r["mojada_incluye_lluvia_IDEAM"] = P is not None
                # Grilla: qué definición del proxy en Open-Meteo reproduce mejor el proxy observado
                # (referencia = IDEAM HR>=90 % o lluvia>0; sin pluviómetro, solo HR>=90 en ambos lados)
                ref = (base.hr_o >= 90) | (base.p_o > 0)
                for u in (80, 85, 88, 90, 92, 95):
                    for pth in ((0.0, 0.2, 0.5, 1.0, None) if P is not None else (None,)):
                        if pth is None:
                            m = base.hr_m >= u
                            refx = base.hr_o >= 90
                        else:
                            m = (base.hr_m >= u) | ((base.p_m > 0) if pth == 0 else (base.p_m >= pth))
                            refx = ref
                        tp, fp, fn = int((refx & m).sum()), int((~refx & m).sum()), int((refx & ~m).sum())
                        GRILLA.append({"estacion": cod, "variante_OM": vname, "OM_umbral_HR": u,
                                       "OM_umbral_lluvia": "sin lluvia" if pth is None else (">0" if pth == 0 else f">={pth}"),
                                       "ref_IDEAM": "HR>=90 o lluvia>0" if pth is not None else "HR>=90",
                                       "horas": len(base), "h_ref": int(refx.sum()), "h_OM": int(m.sum()),
                                       "razon_OM_ref": round(m.sum() / max(1, refx.sum()), 2),
                                       "sensibilidad": round(tp / max(1, tp + fn), 3),
                                       "precision": round(tp / max(1, tp + fp), 3),
                                       "F1": round(2 * tp / max(1, 2 * tp + fp + fn), 3)})
            filas.append(r)
            if vname != "best_match":
                continue
            # mensual
            for var, s, col in (("T", T, "temperature_2m"), ("HR", H, "relative_humidity_2m")):
                if s is None:
                    continue
                lo, hi = (-10, 35) if var == "T" else (0, 100)
                s = s[(s >= lo) & (s <= hi)]
                j = pd.concat([s.rename("obs"), om[col].rename("om")], axis=1, join="inner").dropna()
                g = j.groupby(j.index.month)
                mm = pd.DataFrame({"n_horas": g.size(), "IDEAM_media": g["obs"].mean(), "OM_media": g["om"].mean()})
                mm["sesgo"] = mm["OM_media"] - mm["IDEAM_media"]
                mm["MAE"] = g.apply(lambda x: (x["om"] - x["obs"]).abs().mean())
                if var == "HR":
                    mm["h_ge90_IDEAM"] = g.apply(lambda x: int((x["obs"] >= 90).sum()))
                    mm["h_ge90_OM"] = g.apply(lambda x: int((x["om"] >= 90).sum()))
                mm.index.name = "mes"
                mm = mm.reset_index()
                mm.insert(0, "variable", var)
                mm.insert(0, "estacion", cod)
                mens.append(mm)
            if P is not None:
                j = pd.concat([P.rename("obs"), om["precipitation"].rename("om")], axis=1, join="inner").dropna()
                g = j.groupby(j.index.month)
                mm = pd.DataFrame({"n_horas": g.size(), "IDEAM_media": g["obs"].sum(), "OM_media": g["om"].sum()})
                mm["sesgo"] = mm["OM_media"] - mm["IDEAM_media"]
                mm.index.name = "mes"
                mm = mm.reset_index()
                mm.insert(0, "variable", "P_total_mm")
                mm.insert(0, "estacion", cod)
                mens.append(mm)
            horarios[cod] = (T, H, P, om)
    comp = pd.DataFrame(filas)
    comp.to_csv(os.path.join(QC, "ideam_vs_openmeteo_2025.csv"), index=False)
    grilla = pd.DataFrame(GRILLA)
    grilla.to_csv(os.path.join(QC, "ideam_grilla_proxy_mojadura.csv"), index=False)
    # Gráfica: umbral de HR en Open-Meteo que reproduce las horas HR>=90 % observadas (solo HR, sin lluvia)
    g = grilla[(grilla.variante_OM == "best_match") & (grilla.OM_umbral_lluvia == "sin lluvia")]
    g = g[~g.estacion.isin(EST_SOSPECHOSAS_HR)]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    for i, cod in enumerate(EST_PUNTO):
        s_ = g[g.estacion == cod]
        if not len(s_):
            continue
        lab = cat[cod]["nombre"].split(" [")[0].replace("  - AUT", "").replace(" - AUT", "")
        axs[0].plot(s_.OM_umbral_HR, s_.sensibilidad, marker="o", ms=4, color=CAT[i], label=lab)
        axs[1].plot(s_.OM_umbral_HR, s_.razon_OM_ref, marker="o", ms=4, color=CAT[i], label=lab)
    axs[0].axhline(0.9, color=INK2, lw=1, ls="--")
    axs[0].text(91.0, 0.91, "objetivo de sensibilidad 0,90", color=INK2, fontsize=8)
    axs[0].set_title("Sensibilidad: horas HR ≥ 90 % observadas que Open-Meteo marca")
    axs[0].set_ylabel("Sensibilidad")
    axs[1].axhline(1.0, color=INK2, lw=1, ls="--")
    axs[1].set_title("Horas mojadas Open-Meteo / horas HR ≥ 90 % IDEAM")
    axs[1].set_ylabel("Razón (1 = mismas horas)")
    for ax in axs:
        ax.set_xlabel("Umbral de HR aplicado a Open-Meteo (%)")
        ax.set_xticks([80, 85, 88, 90, 92, 95])
    axs[0].legend(fontsize=8)
    fig.text(0.5, -0.02, "2025, horas pareadas. Excluye estaciones con HR sospechosa: " + ", ".join(EST_SOSPECHOSAS_HR) +
             ". Referencia IDEAM: HR ≥ 90 % (solo humedad).", ha="center", color=INK2, fontsize=8)
    fig.tight_layout()
    guardar_fig(fig, "ideam_umbral_HR_openmeteo.png")
    mens = pd.concat(mens, ignore_index=True).round(2) if mens else pd.DataFrame()
    mens.to_csv(os.path.join(QC, "ideam_vs_openmeteo_mensual_2025.csv"), index=False)

    # Gráfica: un mes, estación U. de La Sabana (Chía) y Guasca
    for cod, mes in (("2120500135", 10), ("0021205700", 10)):
        if cod not in horarios:
            continue
        T, H, P, om = horarios[cod]
        ini, fin = pd.Timestamp(2025, mes, 1), pd.Timestamp(2025, mes + 1, 1) - pd.Timedelta("1h")
        fig, axs = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
        for ax, s, col, lab in ((axs[0], T, "temperature_2m", "Temperatura 2 m (°C)"),
                                (axs[1], H, "relative_humidity_2m", "Humedad relativa (%)")):
            if s is not None:
                ss = s[ini:fin].reindex(pd.date_range(ini, fin, freq="h"))  # deja huecos visibles
                ax.plot(ss.index, ss.values, color=CAT[0], lw=1.5, label="IDEAM (observado)")
            o = om.loc[ini:fin, col]
            ax.plot(o.index, o.values, color=CAT[1], lw=1.5, label="Open-Meteo best_match")
            ax.set_ylabel(lab)
        axs[1].axhline(90, color=INK2, lw=1, ls="--")
        axs[1].text(fin + pd.Timedelta("6h"), 90, "HR 90 %", color=INK2, fontsize=8, va="center")
        axs[0].legend(fontsize=8, loc="upper right", ncol=2)
        nom = cat[cod]["nombre"].split(" [")[0].strip()
        axs[0].set_title(f"{nom} ({cod}) vs Open-Meteo en sus coordenadas - {MESES[mes - 1]} 2025, hora local")
        fig.tight_layout()
        guardar_fig(fig, f"ideam_vs_openmeteo_{cod}_2025-{mes:02d}.png")

    # Gráfica: sesgo mensual T y HR por estación
    if len(mens):
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
        for ax, var, lab in ((axs[0], "T", "Sesgo T (°C), Open-Meteo − IDEAM"),
                             (axs[1], "HR", "Sesgo HR (puntos %), Open-Meteo − IDEAM")):
            for i, cod in enumerate(EST_PUNTO):
                s = mens[(mens.estacion == cod) & (mens.variable == var) & (mens.n_horas >= 200)]
                if len(s):
                    s = s.set_index("mes").reindex(range(1, 13)).reset_index()  # huecos visibles (p. ej. febrero)
                    ax.plot(s["mes"], s["sesgo"], marker="o", ms=4, color=CAT[i],
                            label=cat[cod]["nombre"].split(" [")[0].replace("  - AUT", "").replace(" - AUT", ""))
            ax.axhline(0, color=INK2, lw=1)
            ax.set_title(lab)
            ax.set_xticks(range(1, 13))
            ax.set_xticklabels(MESES, fontsize=8)
        axs[0].legend(fontsize=7, ncol=2)
        fig.text(0.5, -0.02, "Solo meses con ≥ 200 horas pareadas. Open-Meteo pedido en las coordenadas del catálogo IDEAM.",
                 ha="center", color=INK2, fontsize=8)
        fig.tight_layout()
        guardar_fig(fig, "ideam_vs_openmeteo_sesgo_mensual.png")
    return comp, mens


# ================================================================ 5. Sensibilidad al modelo de Open-Meteo
def comparar_modelos():
    filas = []
    for nombre in PUNTOS:
        for modelo in (None, "era5_land", "era5"):
            df = cargar_om(nombre, modelo)
            filas.append({"punto": nombre, "modelo": modelo or "best_match",
                          "T_media": round(df.temperature_2m.mean(), 2),
                          "HR_media": round(df.relative_humidity_2m.mean(), 1),
                          "h_HR_ge90": int((df.relative_humidity_2m >= 90).sum()),
                          "lluvia_mm": round(df.precipitation.sum(), 1) if df.precipitation.notna().any() else None,
                          "LWP_media": round(df.leaf_wetness_probability.mean(), 1),
                          "h_LWP_ge50": int((df.leaf_wetness_probability >= 50).sum())})
    m = pd.DataFrame(filas)
    m.to_csv(os.path.join(QC, "sensibilidad_modelo_openmeteo.csv"), index=False)
    return m


def verificar_formula_lwp():
    """Reproduce leaf_wetness_probability con la fórmula del código fuente de Open-Meteo
    (Sources/App/Helper/FaoEvapotranspiration.swift, leafwetnessPorbability; VPD de Meteorology.swift):
    si lluvia > 1 mm: min(80 + 2*lluvia, 100); si no: clip((T-5)/10, 0, 1) * clip(1 - (VPD-0.1)*1.25, 0, 1) * 100."""
    filas = []
    for nombre in PUNTOS:
        d = cargar_om(nombre)
        T, Td, P = d.temperature_2m, d.dew_point_2m, d.precipitation
        es = lambda x: 0.6108 * np.exp(17.27 * x / (x + 237.3))  # noqa: E731
        vpd = (es(T) - es(Td)).clip(lower=0)
        lwp = np.where(P > 1, np.minimum(80 + 2 * P, 100),
                       (((T - 5) / 10).clip(0, 1) * (1 - (vpd - 0.1) * 1.25).clip(0, 1) * 100).clip(0, 100))
        e = np.abs(lwp - d.leaf_wetness_probability)
        w = d.relative_humidity_2m >= 90
        filas.append({"punto": nombre, "MAE_formula_vs_API": round(float(e.mean()), 3), "max_abs": round(float(e.max()), 2),
                      "T_media_horas_HR90": round(float(T[w].mean()), 2),
                      "pct_horas_HR90_con_T_lt10": round(100 * float((T[w] < 10).mean()), 1),
                      "LWP_media_horas_HR90_sin_lluvia": round(float(d.leaf_wetness_probability[w & (P == 0)].mean()), 1)})
    v = pd.DataFrame(filas)
    v.to_csv(os.path.join(QC, "verificacion_formula_lwp.csv"), index=False)
    return v


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    q, offs = qc_openmeteo()
    print("== QC Open-Meteo\n", q.T.to_string())
    print("zonas horarias en cache:", offs)
    res, anual = resumen_mensual()
    print("== Anual\n", anual.to_string())
    mens, conf, sens, ev = hoja_mojada()
    print("== Concordancia proxy vs LWP50\n", conf.to_string())
    print("== Sensibilidad\n", sens.to_string())
    m = comparar_modelos()
    print("== Modelos\n", m.to_string())
    print("== Verificación fórmula LWP\n", verificar_formula_lwp().to_string())
    comp, cm = comparar_ideam()
    print("== IDEAM\n", comp.T.to_string())
