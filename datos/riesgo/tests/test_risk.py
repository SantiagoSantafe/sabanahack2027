"""Pruebas de riesgo/risk.py.

Correr:  /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I -m pytest \
             /Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/tests -q

Grupos:
  A. Casos de libro: puntos publicados (graficas/umbrales de NCSU IPM, resumen de Gillett & Schilder 2009,
     nota GIM de NCSU) que la implementacion debe reproducir.
  B. Monotonicidad (mas mojadura -> mas riesgo dentro del rango) y forma en temperatura.
  C. Limites (sin mojadura -> 0, fuera de rango termico, valores en [0, 1]).
  D. Deteccion de periodos de mojadura (interrupciones, huecos, T media solo de horas mojadas).
  E. Oidio Gubler-Thomas (reglas de UC IPM).
  F. Clasificacion, fenologia, resumen diario y ventana de 72 h.
  G. Integracion con los datos reales de clima/derivados (se salta si no existen).
"""
import glob
import math
import os
from datetime import date, datetime, timedelta

import pytest

import risk as r

T0 = datetime(2025, 1, 1, 0, 0)


def serie(patron, T=20.0, HR_mojada=95.0, HR_seca=60.0, lluvia=0.0, inicio=T0):
    """patron: cadena de '1' (hora mojada) y '0' (hora seca)."""
    out = []
    for i, c in enumerate(patron):
        temp = T[i] if isinstance(T, (list, tuple)) else T
        out.append(r.Hora(inicio + timedelta(hours=i), temp, HR_mojada if c == "1" else HR_seca, lluvia))
    return out


# --------------------------------------------------------------------------------------------
# A. Casos de libro
# --------------------------------------------------------------------------------------------

class TestCasosDeLibro:
    # NCSU IPM, grafica "Strawberry Fruit Anthracnose leaf wetness graph" a 26.6 C:
    # el indice cruza 0.15 a 7.0 h y 0.50 a 13.1 h.
    @pytest.mark.parametrize("lwd,esperado", [(7.0, 0.15), (13.1, 0.50)])
    def test_wilson_grafica_ncsu_26_6C(self, lwd, esperado):
        assert r.indice_antracnosis_wilson(lwd, 26.6) == pytest.approx(esperado, abs=0.005)

    # NCSU IPM, grafica "Strawberry fruit Grey Mold Rot leaf wetness graph" a 20.5 C:
    # cruza 0.50 a 13.8 h y 0.70 a 16.5 h.
    @pytest.mark.parametrize("lwd,esperado", [(13.8, 0.50), (16.5, 0.70)])
    def test_bulger_grafica_ncsu_20_5C(self, lwd, esperado):
        assert r.indice_botrytis_bulger(lwd, 20.5) == pytest.approx(esperado, abs=0.005)

    def test_temperaturas_optimas_ncsu(self):
        # NCSU marca 26.6 C (antracnosis) y 20.5 C (Botrytis) como optimos.
        assert r.WILSON_T_OPT == pytest.approx(26.6, abs=0.15)
        assert r.BULGER_T_OPT == pytest.approx(20.5, abs=0.15)

    def test_wilson_intercepto(self):
        # Con LWD -> 0+ el indice tiende a e^-3.7/(1+e^-3.7) = 0.024 (curva NCSU arranca en ~0.02).
        assert r.indice_antracnosis_wilson(1e-9, 20) == pytest.approx(0.0241, abs=0.001)

    def test_wilson_recorte_frio_reproduce_curva_ncsu(self):
        # Grafica NCSU "Strawberry Fruit Anthracnose temp graph": de 0 a ~10 C la curva es plana y
        # baja (20.9 h -> ~0.06; 13.1 h -> ~0.045; 7 h -> ~0.035).
        assert r.indice_antracnosis_wilson(20.9, 0.0) == pytest.approx(0.06, abs=0.01)
        assert r.indice_antracnosis_wilson(13.1, 0.0) == pytest.approx(0.045, abs=0.01)
        assert r.indice_antracnosis_wilson(7.0, 0.0) == pytest.approx(0.035, abs=0.01)
        # y es igual a 0, 5 y 9 C (plano)
        assert r.indice_antracnosis_wilson(20.9, 0.0) == pytest.approx(r.indice_antracnosis_wilson(20.9, 9.0))

    def test_umbrales_publicados(self):
        assert r.UMBRALES["antracnosis"] == (0.15, 0.50)   # NCSU FLSAS; MacKenzie & Peres 2012a
        assert r.UMBRALES["botrytis"] == (0.50, 0.70)      # NCSU FLSAS; MacKenzie & Peres 2012b
        assert r.UMBRALES["oidio"] == (0.40, 0.60)         # UC IPM (indice/100)

    def test_gim_nota_ncsu(self):
        # NCSU: "1 cycle ~ 20% disease incidence at LWDmin"; curva GIM: I=2 -> ~0.68.
        assert r.indice_gim_desde_ciclos(1.0) == pytest.approx(0.20, abs=0.01)
        assert r.indice_gim_desde_ciclos(2.0) == pytest.approx(0.68, abs=0.01)
        p = r.PARAMS_GIM["antracnosis"]
        assert r.f_temperatura_gim(p.t_opt, p) == pytest.approx(1.0)
        assert r.indice_gim(p.lwd_min, p.t_opt, p) == pytest.approx(0.20, abs=0.01)

    # Gillett & Schilder 2009 (arandano): aumento considerable tras 12-18 h a 20-25 C, 18-24 h a 30 C,
    # 24 h a 15 C, 36-48 h a 10 C; niveles bajos a 6 h.
    @pytest.mark.parametrize("T,lo,hi", [(10, 36, 48), (15, 23.9, 24.1), (20, 12, 18), (25, 12, 18), (30, 18, 24)])
    def test_aprox_arandano_w50_en_rangos_publicados(self, T, lo, hi):
        w50 = next(w / 10 for w in range(1, 1000) if r.indice_antracnosis_arandano_aprox(w / 10, T) >= 0.5)
        assert lo <= w50 <= hi

    @pytest.mark.parametrize("T", [10, 15, 20, 25, 30])
    def test_aprox_arandano_bajo_a_6h(self, T):
        assert r.indice_antracnosis_arandano_aprox(6, T) < r.UMBRALES["antracnosis"][0]

    def test_wilson_coincide_con_arandano_a_20_25C(self):
        # Validacion cruzada: la ecuacion de fresa llega a 0.5 dentro de 12-18 h a 20-25 C, igual que el
        # arandano (por eso el BAS puede usarla).
        for T in (20, 25):
            w50 = next(w / 10 for w in range(1, 1000) if r.indice_antracnosis_wilson(w / 10, T) >= 0.5)
            assert 12 <= w50 <= 18

    def test_wilson_subestima_frio_en_arandano(self):
        # Hallazgo documentado: a 15 C Wilson necesita ~35 h para 0.5; el arandano mostro infeccion
        # considerable a 24 h. La envolvente corrige hacia el lado sensible.
        assert r.indice_antracnosis_wilson(24, 15) < 0.5
        assert r.indice_antracnosis(24, 15, "envolvente") >= 0.5


# --------------------------------------------------------------------------------------------
# B. Monotonicidad y forma
# --------------------------------------------------------------------------------------------

LWDS = [0.5 * i for i in range(1, 97)]   # 0.5 .. 48 h


@pytest.mark.parametrize("T", [5, 10, 15, 20, 25, 30])
@pytest.mark.parametrize("modelo", ["wilson", "arandano_aprox", "envolvente", "gim"])
def test_antracnosis_monotona_en_lwd(T, modelo):
    vals = [r.indice_antracnosis(w, T, modelo) for w in LWDS]
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))


@pytest.mark.parametrize("T", [5, 10, 15, 20, 25, 30])   # rango experimental de Bulger
def test_botrytis_monotona_en_lwd(T):
    vals = [r.indice_botrytis_bulger(w, T) for w in LWDS]
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))


@pytest.mark.parametrize("T", [10, 15, 20, 25, 30])
def test_roya_monotona_en_lwd(T):
    vals = [r.indice_roya(w, T) for w in LWDS]
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))


def test_curvas_de_temperatura_tienen_un_maximo_interior():
    temps = [t / 2 for t in range(10, 71)]   # 5..35 C
    for f, lwd in ((r.indice_antracnosis_wilson, 13.1), (r.indice_botrytis_bulger, 16.5), (r.indice_roya, 16)):
        vals = [f(lwd, t) for t in temps]
        k = vals.index(max(vals))
        assert 0 < k < len(vals) - 1
        # sube hasta el maximo y baja despues (unimodal en 5-35 C, salvo la meseta fria de Wilson)
        assert all(b >= a - 1e-12 for a, b in zip(vals[:k], vals[1:k + 1]))
        assert all(b <= a + 1e-12 for a, b in zip(vals[k:], vals[k + 1:]))


def test_envolvente_es_maximo():
    for T in (8, 12, 18, 24, 29):
        for w in (6, 12, 24, 36):
            assert r.indice_antracnosis(w, T) == max(r.indice_antracnosis_wilson(w, T),
                                                     r.indice_antracnosis_arandano_aprox(w, T))


# --------------------------------------------------------------------------------------------
# C. Limites
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("f", [r.indice_antracnosis_wilson, r.indice_antracnosis_arandano_aprox,
                               r.indice_antracnosis, r.indice_botrytis_bulger, r.indice_roya])
@pytest.mark.parametrize("T", [-5, 0, 10, 20, 30, 45])
def test_sin_mojadura_es_cero(f, T):
    assert f(0, T) == 0.0
    assert f(-3, T) == 0.0


@pytest.mark.parametrize("f", [r.indice_antracnosis_wilson, r.indice_antracnosis_arandano_aprox,
                               r.indice_botrytis_bulger, r.indice_roya])
def test_temperatura_faltante_es_cero(f):
    assert f(12, float("nan")) == 0.0


def test_indices_en_rango_0_1():
    for T in range(-5, 46, 3):
        for w in (1, 6, 12, 24, 48, 120):
            for v in r.indices_evento(w, T).values():
                assert 0.0 <= v <= 1.0


def test_extremos_termicos_bajan_el_riesgo():
    assert r.indice_roya(48, 5) == 0.0          # bajo Tmin
    assert r.indice_roya(48, 35) == 0.0         # sobre Tmax
    assert r.indice_botrytis_bulger(24, 40) < 0.01
    assert r.indice_antracnosis_wilson(24, 42) < 0.01
    assert r.indice_antracnosis_arandano_aprox(48, 36) == pytest.approx(0.0241, abs=0.001)


def test_gim_lwd_max():
    p = r.PARAMS_GIM["roya"]
    # si la mojadura requerida LWDmin/fT supera LWDmax no hay infeccion
    t_frio = 8.5
    assert p.lwd_min / r.f_temperatura_gim(t_frio, p) > p.lwd_max
    assert r.indice_roya(200, t_frio) == 0.0


def test_fuera_de_rango_bulger():
    assert r._fuera_rango_bulger(40, 20)
    assert r._fuera_rango_bulger(10, 2)
    assert not r._fuera_rango_bulger(10, 20)


# --------------------------------------------------------------------------------------------
# D. Deteccion de periodos de mojadura
# --------------------------------------------------------------------------------------------

class TestPeriodos:
    def test_sin_mojadura_no_hay_periodos(self):
        assert r.detectar_periodos(serie("0" * 48)) == []
        dias = r.resumen_diario(serie("0" * 48))
        assert all(d["idx_antracnosis"] == 0 and d["idx_botrytis"] == 0 and d["idx_roya"] == 0 for d in dias)

    def test_interrupcion_corta_no_corta(self):
        ps = r.detectar_periodos(serie("11111" + "000" + "1111" + "0000"))
        assert len(ps) == 1
        p = ps[0]
        assert p.horas_mojadas == 9                      # las horas secas no suman LWD
        assert p.duracion_total_h == 12
        assert p.n_interrupciones == 1
        assert not p.abierto

    def test_cuatro_horas_secas_cortan(self):
        # NCSU: un periodo termina con un periodo seco minimo de 4 h
        ps = r.detectar_periodos(serie("11111" + "0000" + "1111" + "0000"))
        assert [p.horas_mojadas for p in ps] == [5, 4]

    def test_interrupcion_configurable(self):
        cfg = r.ConfigMojadura(max_interrupcion_h=0)
        ps = r.detectar_periodos(serie("11011"), cfg)
        assert [p.horas_mojadas for p in ps] == [2, 2]

    def test_horas_faltantes_cuentan_como_secas(self):
        hs = serie("111") + serie("111", inicio=T0 + timedelta(hours=8))   # hueco de 5 h sin datos
        assert len(r.detectar_periodos(hs)) == 2
        hs = serie("111") + serie("111", inicio=T0 + timedelta(hours=5))   # hueco de 2 h
        assert len(r.detectar_periodos(hs)) == 1

    def test_t_media_solo_horas_mojadas(self):
        temps = [10, 10, 30, 30, 30, 10, 10]
        ps = r.detectar_periodos(serie("1100011", T=temps))
        assert ps[0].t_media == pytest.approx(10.0)

    def test_lluvia_o_lwp_o_riego_mojan(self):
        h_lluvia = r.Hora(T0, 18, 70, lluvia=0.5)
        assert not r.hora_mojada(r.Hora(T0, 18, 70, lluvia=0.4), r.ConfigMojadura())   # llovizna < 0.5 mm/h
        assert r.hora_mojada(r.Hora(T0, 18, 70, lluvia=0.4), r.ConfigMojadura(umbral_lluvia_mm=0.1))
        h_lwp = r.Hora(T0, 18, 70, lluvia=0.0, lwp=80)
        h_riego = r.Hora(T0, 18, 60, riego=True)
        cfg = r.ConfigMojadura()
        assert r.hora_mojada(h_lluvia, cfg)
        assert not r.hora_mojada(h_lwp, cfg)
        assert r.hora_mojada(h_lwp, r.ConfigMojadura(usar_lwp=True))
        assert r.hora_mojada(h_riego, cfg)
        assert not r.hora_mojada(r.Hora(T0, 18, 89.9), cfg)
        assert r.hora_mojada(r.Hora(T0, 18, 90.0), cfg)
        assert not r.hora_mojada(r.Hora(T0, 18, float("nan")), cfg)

    def test_periodo_abierto_al_final(self):
        ps = r.detectar_periodos(serie("0011100"))
        assert ps[0].abierto
        ps = r.detectar_periodos(serie("001110000"))
        assert not ps[0].abierto

    def test_desordenado_igual_que_ordenado(self):
        hs = serie("1110001111000011")
        assert [p.horas_mojadas for p in r.detectar_periodos(list(reversed(hs)))] == \
               [p.horas_mojadas for p in r.detectar_periodos(hs)]


# --------------------------------------------------------------------------------------------
# E. Oidio Gubler-Thomas
# --------------------------------------------------------------------------------------------

def dias_oidio(perfiles):
    """perfiles: lista de listas de 24 temperaturas."""
    hs = []
    for d, temps in enumerate(perfiles):
        for h, t in enumerate(temps):
            hs.append(r.Hora(T0 + timedelta(days=d, hours=h), t, 60))
    return r.indice_oidio_gubler_thomas(hs)


FAV = [15] * 10 + [25] * 8 + [15] * 6          # 8 h seguidas en 21-29 C
NOFAV = [15] * 10 + [25] * 5 + [15] * 9        # solo 5 h
CALIENTE_FAV = [15] * 6 + [25] * 8 + [36] + [15] * 9
CALIENTE_NOFAV = [15] * 10 + [36] + [15] * 13


class TestOidio:
    def test_arranque_tres_dias(self):
        assert [d.indice for d in dias_oidio([FAV, FAV, FAV])] == [0, 0, 60]

    def test_dos_dias_no_arrancan(self):
        assert [d.indice for d in dias_oidio([FAV, FAV, NOFAV, FAV, FAV])] == [0] * 5

    def test_suma_y_resta(self):
        idx = [d.indice for d in dias_oidio([FAV] * 3 + [FAV, NOFAV, CALIENTE_FAV, CALIENTE_NOFAV])]
        # 60 -> +20=80 -> -10=70 -> (+20-10)=80 -> (-10-10 limitado a -10)=70
        assert idx == [0, 0, 60, 80, 70, 80, 70]

    def test_limites_0_100(self):
        idx = [d.indice for d in dias_oidio([FAV] * 10)]
        assert max(idx) == 100
        idx = [d.indice for d in dias_oidio([FAV] * 3 + [NOFAV] * 12)]
        assert min(idx) == 0 and idx[-1] == 0

    def test_hora_fuera_de_rango_corta_racha(self):
        perfil = [15] * 8 + [25] * 4 + [20] + [25] * 4 + [15] * 7   # 4 + 4 con corte
        assert dias_oidio([perfil])[0].racha_max_h == 4

    def test_reset_por_aplicacion(self):
        hs = []
        for d in range(5):
            for h, t in enumerate(FAV):
                hs.append(r.Hora(T0 + timedelta(days=d, hours=h), t, 60))
        idx = [x.indice for x in r.indice_oidio_gubler_thomas(hs, fechas_aplicacion=[date(2025, 1, 4)])]
        assert idx == [0, 0, 60, 0, 20]

    def test_clima_frio_no_activa(self):
        # Perfil tipico de la Sabana (max ~19 C): nunca hay 6 h en 21-29 C
        frio = [8] * 8 + [14, 16, 18, 19, 19, 18, 16, 14] + [10] * 8
        assert all(d.indice == 0 for d in dias_oidio([frio] * 20))


# --------------------------------------------------------------------------------------------
# F. Clasificacion, fenologia, resumen diario
# --------------------------------------------------------------------------------------------

class TestClasificacion:
    @pytest.mark.parametrize("enf,idx,clase", [
        ("antracnosis", 0.149, "bajo"), ("antracnosis", 0.15, "medio"), ("antracnosis", 0.4999, "medio"),
        ("antracnosis", 0.50, "alto"), ("botrytis", 0.49, "bajo"), ("botrytis", 0.5, "medio"),
        ("botrytis", 0.7, "alto"), ("oidio", 0.3, "bajo"), ("oidio", 0.5, "medio"), ("oidio", 0.6, "alto"),
        ("roya", 0.19, "bajo"), ("roya", 0.2, "medio"), ("roya", 0.5, "alto"), ("roya", float("nan"), "bajo"),
    ])
    def test_cortes(self, enf, idx, clase):
        assert r.clasificar(idx, enf) == clase

    def test_fenologia_en_0_1_y_sin_etapa_es_1(self):
        for enf in r.ENFERMEDADES:
            assert r.multiplicador_fenologia(enf, None) == 1.0
            for e in r.ETAPAS:
                assert 0.0 <= r.multiplicador_fenologia(enf, e) <= 1.0
            assert max(r.FENOLOGIA[enf].values()) == 1.0
        with pytest.raises(ValueError):
            r.multiplicador_fenologia("botrytis", "cosecha")

    def test_fenologia_reduce_clase(self):
        hs = serie("1" * 16 + "0" * 8, T=20.5)        # Bulger 16 h a 20.5 C -> ~0.67 (medio)
        ev_flor = r.evaluar_eventos(hs, etapa="floracion")[0]
        ev_veg = r.evaluar_eventos(hs, etapa="vegetativo")[0]
        assert ev_flor["clase_botrytis"] == "medio"
        assert ev_veg["idx_aj_botrytis"] == pytest.approx(ev_flor["idx_aj_botrytis"] * 0.3, abs=1e-3)
        assert ev_veg["clase_botrytis"] == "bajo"


class TestResumenDiario:
    def test_periodo_multidia_sube_dia_a_dia(self):
        hs = serie("0" * 12 + "1" * 36 + "0" * 24, T=18)   # 12 h mojadas el dia 1 y 24 h el dia 2
        dias = r.resumen_diario(hs)
        assert [d["antracnosis_lwd_h"] for d in dias[:2]] == [12, 36]
        assert dias[1]["idx_antracnosis"] > dias[0]["idx_antracnosis"]
        assert dias[2]["idx_antracnosis"] == 0.0

    def test_motivo_y_global(self):
        hs = serie("1" * 20 + "0" * 4, T=22)
        d = r.resumen_diario(hs)[0]
        assert d["riesgo_global"] == "alto"
        assert "antracnosis ALTO" in d["motivo"] and "20 h" in d["motivo"]

    def test_ventana_72h(self):
        hs = serie("0" * 24 + "1" * 20 + "0" * 4 + "0" * 24, T=22)
        dias = r.resumen_diario(hs)
        v = r.riesgo_ventana_72h(dias, date(2025, 1, 3))   # incluye ayer (dia 2, alto)
        assert v["enfermedades"]["antracnosis"]["clase"] == "alto"
        v = r.riesgo_ventana_72h(dias, date(2025, 1, 4))   # dia 2 ya no esta en la ventana
        assert v["enfermedades"]["antracnosis"]["clase"] == "bajo"

    def test_ventana_72h_sin_datos_no_es_bajo(self):
        # [verificacion-riesgo-clima] fecha fuera del pronostico: no debe responder "bajo" en silencio
        hs = serie("1" * 20 + "0" * 4, T=22)
        dias = r.resumen_diario(hs)
        v = r.riesgo_ventana_72h(dias, date(2025, 2, 1))
        assert v["riesgo_global"] == "sin_datos" and "error" in v and v["enfermedades"] == {}
        v = r.riesgo_ventana_72h(dias, date(2025, 1, 2))   # solo 1 de 3 dias
        assert "advertencia" in v and v["riesgo_global"] == "alto"

    def test_presion_roya_14d(self):
        evento = "1" * 16 + "0" * 8
        hs = serie((evento + "0" * 24 * 2) * 3, T=21.5)
        dias = r.resumen_diario(hs)
        p = [d["roya_presion_14d"] for d in dias]
        assert p[0] > 0 and p[-1] > p[0]
        assert all(0 <= x <= 1 for x in p)


# --------------------------------------------------------------------------------------------
# G. Integracion con datos reales (si existen)
# --------------------------------------------------------------------------------------------

DERIVADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "clima", "derivados")


@pytest.mark.skipif(not glob.glob(os.path.join(DERIVADOS, "hoja_mojada_horaria_*.csv")),
                    reason="no hay datos de clima derivados")
def test_integracion_datos_reales():
    ruta = sorted(glob.glob(os.path.join(DERIVADOS, "hoja_mojada_horaria_*.csv")))[0]
    hs = r.horas_desde_csv(ruta)
    assert len(hs) > 1000
    dias = r.resumen_diario(hs[: 24 * 60])
    assert len(dias) == 60
    for d in dias:
        for enf in r.ENFERMEDADES:
            assert 0.0 <= d["idx_" + enf] <= 1.0
            assert d["clase_" + enf] in r.CLASES


# --------------------------------------------------------------------------------------------
# H. Lectura de formatos
# --------------------------------------------------------------------------------------------

def test_lee_csv_crudo_open_meteo(tmp_path):
    ruta = tmp_path / "pronostico.csv"
    ruta.write_text(
        "punto,descargado_utc,time,temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,"
        "wind_speed_10m,leaf_wetness_probability,precipitation_probability\n"
        "chia,2026-10-23T22:03:13Z,2026-10-21T00:00,11.6,100,11.6,0.0,2.7,66,20\n"
        "chia,2026-10-23T22:03:13Z,2026-10-21T01:00,12.0,97,11.5,,3.7,70,12\n"
        "chia,2026-10-23T22:03:13Z,2026-10-21T01:00,12.0,97,11.5,0.0,3.7,70,12\n", encoding="utf-8")
    hs = r.horas_desde_csv(str(ruta))
    assert len(hs) == 2                       # timestamp repetido descartado
    assert hs[0].time == datetime(2026, 10, 21, 0) and hs[0].HR == 100 and hs[0].lwp == 66
    assert hs[1].lluvia == 0.0                # lluvia vacia -> 0


def test_lee_dataframe():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"time": pd.date_range("2025-01-01", periods=30, freq="h"),
                       "T": [18.0] * 30, "HR": [95.0] * 20 + [60.0] * 10, "lluvia": [0.0] * 30})
    hs = r.horas_desde_df(df)
    ps = r.detectar_periodos(hs)
    assert len(ps) == 1 and ps[0].horas_mojadas == 20
