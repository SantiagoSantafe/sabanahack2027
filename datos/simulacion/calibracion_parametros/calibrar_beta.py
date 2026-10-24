"""Calibra beta_max por enfermedad para que la tasa temprana r de la grilla iguale r_objetivo.

Uso (desde /Users/santiagosantafe/Downloads/SabanaHack/datos):
    .venv/bin/python -I simulacion/calibracion_parametros/calibrar_beta.py

Lee simulacion/parametros.yaml y escribe en simulacion/calibracion_parametros/:
    curvas_r_beta.csv   r medida para cada beta y cada enfermedad
    beta_calibrado.json beta que mejor reproduce r_objetivo (o el r máximo alcanzable)

Modelo (el mismo que describe parametros.yaml):
    p_inf_j = 1 - prod_i (1 - beta * w_ij) * (1 - p_fondo)        con riesgo = 1 constante
    S -> E (latente_dias, fijo) -> I (infeccioso_dias, fijo) -> R
    r = pendiente de ln(infectados acumulados) entre 10 y 250 plantas (0.2 % y 5 % de 1 ha).
Es una calibración de referencia: un foco central, riesgo constante, sin tratamiento ni detección.
"""
import csv
import json
import math
import os

import numpy as np
import yaml
from scipy.signal import fftconvolve

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "calibracion_parametros")
P = yaml.safe_load(open(os.path.join(BASE, "parametros.yaml")))

G = P["grilla"]
DX = G["distancia_entre_plantas_m"]["valor"]
DY = G["distancia_entre_hileras_m"]["valor"]
NR = G["camas_por_bloque"]["valor"]
NC = G["plantas_por_cama"]["valor"]
P_FONDO = P["riesgo_a_contagio"]["contagio_lejano_por_planta_dia"]["valor"]
N = NR * NC
UMBRAL_BAJO, UMBRAL_ALTO = 10, int(0.05 * N)
DIAS_MAX = 365
REPS = 8
BETAS = np.round(np.logspace(-2.5, 0, 16), 5)


def val(x):
    return x["valor"] if isinstance(x, dict) else x


def kernel(k):
    """Matriz de pesos w(dfila, dcol); w = 1 para la vecina inmediata en la misma cama."""
    tipo = k["tipo"]
    if tipo == "vecindad":
        W = np.zeros((3, 5))
        W[1, 1] = W[1, 3] = val(k["w_misma_cama_d1"])
        W[1, 0] = W[1, 4] = val(k["w_misma_cama_d2"])
        W[0, 1:4] = W[2, 1:4] = val(k["w_cama_vecina"])
        return W
    rmax = k["radio_max_m"]
    hr, hc = int(rmax // DY), int(rmax // DX)
    dr, dc = np.mgrid[-hr:hr + 1, -hc:hc + 1]
    d = np.hypot(dr * DY, dc * DX)
    if tipo == "exponencial":
        W = np.exp(-(d - DX) / val(k["lambda_m"]))
    elif tipo == "potencia":
        r0, b = val(k["r0_m"]), val(k["b"])
        W = ((r0 ** 2 + DX ** 2) / (r0 ** 2 + d ** 2)) ** (b / 2)
    else:
        raise ValueError(tipo)
    W = W * val(k["f_cruce_hilera"]) ** np.abs(dr)
    W[d > rmax] = 0.0
    W[hr, hc] = 0.0
    return np.minimum(W, 1.0)


def simular(W, beta, L, D, rng, p_fondo=P_FONDO):
    """Devuelve (serie de infectados acumulados, serie de distancia máxima del frente en la cama del foco)."""
    estado = np.zeros((NR, NC), dtype=np.int16)    # 0 = S, >0 = días desde la infección
    estado[NR // 2, NC // 2] = 1
    logW = np.log1p(-np.clip(beta * W, 0, 0.999999))
    acum, frente = [], []
    c0 = NC // 2
    for _ in range(DIAS_MAX):
        infeccioso = ((estado > L) & (estado <= L + D)).astype(float)
        if infeccioso.any():
            log_esc = np.minimum(fftconvolve(infeccioso, logW, mode="same"), 0.0)
        else:
            log_esc = np.zeros_like(infeccioso)
        p = 1.0 - np.exp(log_esc) * (1.0 - p_fondo)
        nuevos = (estado == 0) & (rng.random((NR, NC)) < p)
        estado[estado > 0] += 1
        estado[nuevos] = 1
        n = int((estado > 0).sum())
        acum.append(n)
        cols = np.where(estado[NR // 2] > 0)[0]
        frente.append(float(np.abs(cols - c0).max() * DX) if cols.size else 0.0)
        if n >= UMBRAL_ALTO and len(acum) > 5:
            break
        if (estado == 0).sum() == 0:
            break
    return np.array(acum), np.array(frente)


def tasa_r(acum):
    idx = np.where((acum >= UMBRAL_BAJO) & (acum <= UMBRAL_ALTO))[0]
    if idx.size < 4:
        return float("nan")
    t = idx.astype(float)
    return float(np.polyfit(t, np.log(acum[idx]), 1)[0])


def velocidad_frente(frente):
    idx = np.where((frente >= 5) & (frente <= 40))[0]
    if idx.size < 4:
        return float("nan")
    return float(np.polyfit(idx.astype(float), frente[idx], 1)[0])


def main():
    filas, resumen = [], {}
    for nombre, e in P["enfermedades"].items():
        if "kernel" not in e:
            continue
        W = kernel(e["kernel"])
        L = int(round(val(e["latente_dias"])))
        D = int(round(val(e["infeccioso_dias"])))
        objetivo = val(e["r_objetivo_por_dia"])
        rng = np.random.default_rng(20261023)
        curva = []
        for beta in BETAS:
            rs, vs = [], []
            for _ in range(REPS):
                acum, frente = simular(W, beta, L, D, rng)
                rs.append(tasa_r(acum))
                vs.append(velocidad_frente(frente))
            r_med = float(np.nanmedian(rs)) if np.isfinite(rs).any() else float("nan")
            v_med = float(np.nanmedian(vs)) if np.isfinite(vs).any() else float("nan")
            curva.append((float(beta), r_med, v_med))
            filas.append({"enfermedad": nombre, "beta": float(beta), "r_mediana": r_med,
                          "velocidad_frente_m_dia_con_fondo": v_med, "reps": REPS,
                          "suma_pesos_kernel": float(W.sum())})
        ok = [(b, r, v) for b, r, v in curva if math.isfinite(r)]
        r_max = max((r for _, r, _ in ok), default=float("nan"))
        if ok and r_max >= objetivo:
            # interpolación log-lineal entre los dos betas que encierran el objetivo
            pares = [(ok[i], ok[i + 1]) for i in range(len(ok) - 1) if ok[i][1] <= objetivo <= ok[i + 1][1]]
            if pares:
                (b1, r1, _), (b2, r2, _) = pares[0]
                f = 0.0 if r2 == r1 else (objetivo - r1) / (r2 - r1)
                beta_cal = float(math.exp(math.log(b1) + f * (math.log(b2) - math.log(b1))))
            else:
                beta_cal = ok[0][0]
            alcanzable = True
        else:
            beta_cal, alcanzable = (ok[-1][0] if ok else float("nan")), False
        # r con p_fondo x10 para ver cuánto pesa la infección de fondo
        rng = np.random.default_rng(7)
        r_fondo10 = float(np.nanmedian([tasa_r(simular(W, beta_cal, L, D, rng, P_FONDO * 10)[0]) for _ in range(REPS)]))
        resumen[nombre] = {
            "r_objetivo": objetivo, "beta_calibrado": round(beta_cal, 4), "alcanzable_con_beta_le_1": alcanzable,
            "r_max_en_rango_beta": round(r_max, 4) if math.isfinite(r_max) else None,
            "latente_dias": L, "infeccioso_dias": D, "suma_pesos_kernel": round(float(W.sum()), 3),
            "r_con_fondo_x10_en_beta_calibrado": round(r_fondo10, 4) if math.isfinite(r_fondo10) else None,
            "velocidad_frente_m_dia_en_beta_calibrado_sin_fondo": None,
        }
        # velocidad del frente en el beta calibrado
        rng = np.random.default_rng(11)
        # sin infección de fondo (p_fondo = 0): el fondo crea saltos lejanos que ensucian la medida del frente
        vs = [velocidad_frente(simular(W, beta_cal, L, D, rng, 0.0)[1]) for _ in range(REPS)]
        if np.isfinite(vs).any():
            resumen[nombre]["velocidad_frente_m_dia_en_beta_calibrado_sin_fondo"] = round(float(np.nanmedian(vs)), 3)
        print(nombre, json.dumps(resumen[nombre], ensure_ascii=False))
    with open(os.path.join(OUT, "curvas_r_beta.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    meta = {"grilla": {"camas": NR, "plantas_por_cama": NC, "dx_m": DX, "dy_m": DY},
            "p_fondo": P_FONDO, "reps": REPS, "dias_max": DIAS_MAX,
            "ventana_r_plantas": [UMBRAL_BAJO, UMBRAL_ALTO], "betas": BETAS.tolist(),
            "semillas": [20261023, 7, 11], "resultado": resumen}
    json.dump(meta, open(os.path.join(OUT, "beta_calibrado.json"), "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
