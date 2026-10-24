"""Chequeos complementarios a calibrar_beta.py (mismo modelo y misma grilla).

1) Antracnosis: con kernel de salpicadura local no se alcanza r_objetivo ni con beta = 1.
   Se busca la infección de fondo (p_fondo) que, con beta en {0.1, 0.2, 0.3, 0.5}, da r = r_objetivo.
2) Oídio: velocidad del frente según lambda (3, 5, 8 m), recalibrando beta a r_objetivo en cada caso,
   para comparar con 1.65 m/día (Aldrighetti et al. 2025, fresa en macrotúnel).

Uso: .venv/bin/python -I simulacion/calibracion_parametros/calibracion_complementaria.py
Escribe calibracion_complementaria.json en la misma carpeta.
"""
import copy
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calibrar_beta as cb  # noqa: E402

REPS = 8


def r_mediana(W, beta, L, D, p_fondo, semilla):
    rng = np.random.default_rng(semilla)
    rs = [cb.tasa_r(cb.simular(W, beta, L, D, rng, p_fondo)[0]) for _ in range(REPS)]
    return float(np.nanmedian(rs)) if np.isfinite(rs).any() else float("nan")


def interpolar(xs, ys, objetivo):
    for i in range(len(xs) - 1):
        if math.isfinite(ys[i]) and math.isfinite(ys[i + 1]) and ys[i] <= objetivo <= ys[i + 1]:
            f = 0.0 if ys[i + 1] == ys[i] else (objetivo - ys[i]) / (ys[i + 1] - ys[i])
            return float(math.exp(math.log(xs[i]) + f * (math.log(xs[i + 1]) - math.log(xs[i]))))
    return None


def main():
    out = {}
    e = cb.P["enfermedades"]["antracnosis"]
    W = cb.kernel(e["kernel"])
    L, D = int(cb.val(e["latente_dias"])), int(cb.val(e["infeccioso_dias"]))
    obj = cb.val(e["r_objetivo_por_dia"])
    fondos = [1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4]
    res = {}
    for beta in [0.1, 0.2, 0.3, 0.5]:
        rs = [r_mediana(W, beta, L, D, pf, 101) for pf in fondos]
        res[str(beta)] = {"r_por_p_fondo": dict(zip(map(str, fondos), [round(r, 4) for r in rs])),
                          "p_fondo_para_r_objetivo": interpolar(fondos, rs, obj)}
        print("antracnosis beta", beta, res[str(beta)])
    out["antracnosis_fondo"] = {"r_objetivo": obj, "resultado": res}

    e = cb.P["enfermedades"]["oidio"]
    L, D = int(cb.val(e["latente_dias"])), int(cb.val(e["infeccioso_dias"]))
    obj = cb.val(e["r_objetivo_por_dia"])
    betas = np.round(np.logspace(-2.5, -0.5, 12), 5)
    res = {}
    for lam in [3.0, 5.0, 8.0]:
        k = copy.deepcopy(e["kernel"])
        k["lambda_m"] = lam
        k["radio_max_m"] = max(15.0, 4 * lam)
        W = cb.kernel(k)
        rs = [r_mediana(W, b, L, D, cb.P_FONDO, 202) for b in betas]
        beta_cal = interpolar(list(betas), rs, obj)
        v = None
        if beta_cal:
            rng = np.random.default_rng(303)
            vs = [cb.velocidad_frente(cb.simular(W, beta_cal, L, D, rng, 0.0)[1]) for _ in range(REPS)]  # sin fondo
            v = round(float(np.nanmedian(vs)), 3) if np.isfinite(vs).any() else None
        res[str(lam)] = {"beta_calibrado": round(beta_cal, 4) if beta_cal else None, "velocidad_frente_m_dia": v}
        print("oidio lambda", lam, res[str(lam)])
    out["oidio_lambda_vs_frente"] = {"r_objetivo": obj, "referencia_m_dia": 1.65, "resultado": res}
    json.dump(out, open(os.path.join(cb.OUT, "calibracion_complementaria.json"), "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
