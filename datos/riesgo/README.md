# riesgo/: modelos de riesgo ambiental de enfermedades del arándano

Sabana Hack, reto "Berry Good Idea". Esta carpeta es la capa ambiental del sistema híbrido. Convierte el clima horario (Open-Meteo hoy; la red fija de sensores mañana) en un índice de infección de 0 a 1 y en una clase bajo/medio/alto para cada enfermedad, con el motivo en texto para el agrónomo.

Etiquetas que se usan en el código y en este documento:

| Etiqueta | Significado |
|---|---|
| **PUBLICADO** | Coeficiente copiado de la fuente citada, que se abrió en esta sesión. |
| **APROXIMACION** | Curva o regla construida por el equipo a partir de datos publicados. |
| **SUPUESTO** | Valor elegido sin fuente directa. |
| **NO VERIFICADO** | Dato visto solo en un resumen secundario, porque la fuente original estaba bloqueada. |

## Archivos

| Archivo | Qué es |
|---|---|
| `risk.py` | Librería y CLI. El núcleo solo usa la librería estándar (Python 3.9 o superior); pandas es opcional. |
| `tests/test_risk.py` | 136 pruebas (135 + 1 de verificación) con pytest: casos de libro, monotonicidad, límites, mojadura, oídio, clasificación e integración. |
| `correr_2025.py` | Aplica los modelos al clima horario de 2025 de los 4 puntos y escribe las tablas en `salidas/`. |
| `graficas.py` | Dibuja `graficas/curvas_antracnosis_arandano.png` y `graficas/riesgo_diario_2025.png`. |
| `salidas/` | Eventos y resumen diario por punto, conteos por clase y por criterio de mojadura, alertas por año y `riesgo_actual.json` para la demo. |

## Cómo correrlo

```bash
PY=/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python
D=/Users/santiagosantafe/Downloads/SabanaHack/datos
$PY -I -m pytest $D/riesgo/tests -q -p no:cacheprovider        # 136 passed
$PY -I $D/riesgo/correr_2025.py                                 # tablas 2025 en salidas/
$PY -I $D/riesgo/graficas.py                                    # PNG en graficas/
$PY -I $D/riesgo/risk.py actual --fecha 2026-10-23 [--etapa floracion]       # riesgo 72 h (demo)
$PY -I $D/riesgo/risk.py evaluar --csv $D/clima/derivados/hoja_mojada_horaria_chia.csv --punto chia
```

Desde código:

```python
import sys; sys.path.insert(0, ".../datos/riesgo")
import risk as r
horas = r.horas_desde_csv(".../clima/cache/pronostico_chia_<ts>.csv")   # o r.horas_desde_df(df)
dias  = r.resumen_diario(horas, r.ConfigMojadura(), etapa="fruto_verde")
alerta = r.riesgo_ventana_72h(dias, fecha)   # dict: enfermedad -> indice, clase, motivo
```

`horas_desde_csv` lee dos formatos: el crudo de Open-Meteo (`time, temperature_2m, relative_humidity_2m, precipitation, leaf_wetness_probability`) y el derivado del equipo de clima (`time, T, HR, lluvia, LWP`). Una columna `riego` (0/1) marca como mojadas las horas con aspersor.

## 1. Mojadura foliar (entrada de todos los modelos menos el oídio)

- **Hora mojada**: `HR ≥ umbral_hr` **o** `lluvia ≥ umbral_lluvia_mm` **o** `riego = 1`. La probabilidad de mojadura LWP de Open-Meteo puede sumarse como criterio (`usar_lwp`).
- **Valores por defecto**: `umbral_hr = 90 %` y `umbral_lluvia_mm = 0,5 mm/h`. Es el "escenario central" del equipo de clima, que comparó IDEAM con Open-Meteo en 2025 (`reportes/clima-open-meteo.md`): Open-Meteo marca entre 1,7 y 4,5 veces más horas con lluvia que el pluviómetro. El "escenario de alerta" es `HR ≥ 85 %` o lluvia ≥ 0,5 mm/h, con una sensibilidad de unos 0,9 frente a HR_IDEAM ≥ 90 %.
- **Periodo de mojadura**: horas mojadas unidas cuando las interrumpe un hueco seco de **3 h o menos**. Cuatro horas secas cierran el periodo. Esta regla es PUBLICADA por NC State IPM ("an infection risk period is terminated by a minimum dry period of four hours") y se cambia con `max_interrupcion_h`. Las horas faltantes en la serie cuentan como secas.
- **LWD** = número de horas mojadas del periodo. Las horas secas del hueco no suman.
- **T** = temperatura media **solo de las horas mojadas**. NCSU lo publica así: "Only the temperatures during the time of leaf wetness are used".
- Un periodo que sigue abierto al final de la serie (pronóstico) queda marcado `abierto=True`.

## 2. Modelos por enfermedad

`logística(f) = e^f / (1 + e^f)`. **Sin mojadura (LWD = 0) todos los índices valen 0.**

### 2.1 Antracnosis (*Colletotrichum*)

**a) Wilson, Madden y Ellis 1990** (*Phytopathology* 80:111-116; fruto de fresa, *C. acutatum*). PUBLICADO, con los coeficientes que publica NC State IPM:

```
f = -3.7 + 0.33·LWD - 0.069·LWD·T + 0.005·LWD·T² - 9.3e-5·LWD·T³
índice = logística(f)
```

- **Uso en arándano**: es la ecuación del Strawberry Advisory System, y el Blueberry Advisory System de UF/IFAS la tomó tal cual para la antracnosis del arándano (Gama et al. 2022, EDIS PP366).
- **Validación en campo**: Gama et al. 2021 (*Plant Dis.* 105:1806-1813) la validaron en arándano en Florida. MSU la adaptó para Michigan en 2025 (hortidaily, 10-abr-2025).
- **Comprobación**: el código reproduce la gráfica de NCSU a 26,6 °C (0,15 a 7,0 h y 0,50 a 13,1 h).
- **Recorte frío (implementación nuestra)**: para T < 9,33 °C se usa la pendiente en 9,33 °C, que es el mínimo local del polinomio. El cúbico extrapolado volvería a subir hacia 0 °C. Con el recorte se reproduce la curva plana y baja que publica NCSU entre 0 y 10 °C (20,9 h a 0 °C da 0,06). Además coincide con Miles et al. 2013: crecimiento escaso o nulo a 5 °C.

**b) Aproximación calibrada en arándano (APROXIMACION).** Gillett y Schilder 2009 (*Acta Hortic.* 810:355-360), del mismo grupo que Miles et al. 2013, inocularon fruto de arándano 'Jersey'. Hallaron "aumento considerable" de la infección tras estos tiempos de mojadura:

| Temperatura | Mojadura |
|---|---|
| 20-25 °C | 12-18 h |
| 30 °C | 18-24 h |
| 15 °C | 24 h |
| 10 °C | 36-48 h |

A 6 h la infección era baja en todos los casos. Se toma el punto medio de cada rango como W50, la LWD a la que el índice vale 0,5, y se conserva la forma de Wilson:

```
g(T) = 3.7 / W50(T)       W50: 10 °C→42 h, 15→24, 20→15, 25→15, 30→21; g = 0 a 5 y 35 °C; lineal entre anclas
índice = logística(-3.7 + LWD·g(T))
```

Por qué se ancla en 0,5: a 20-25 °C la propia ecuación de Wilson llega a 0,5 entre 13,4 y 18 h, dentro del rango observado en arándano.

**c) Índice que usa el sistema: envolvente = máx(a, b).** Así se orienta a la sensibilidad. Hallazgo: en frío la ecuación de fresa subestima al arándano. A 15 °C Wilson necesita unas 35 h para llegar a 0,5; el arándano mostró infección considerable a 24 h. A 10 °C son unas 79 h frente a 36-48 h.

**d) Lo que no se pudo usar: Miles et al. 2013** (*Plant Pathology* 62:1238-1247, doi:10.1111/ppa.12061). Según el resumen de Crossref, ajustaron "ecuaciones gaussianas tridimensionales" de T y mojadura (R² = 0,86 en fruto inmaduro y 0,90 en maduro), con óptimo de 25 °C y aumento hasta 48 h. **Los coeficientes no se obtuvieron**: el artículo es de acceso cerrado (Unpaywall: closed), la copia de MSU está detrás de Incapsula y la tesis de MSU devuelve 403. No se intentó saltar esos bloqueos.

**e) GIM de NCSU para *C. acutatum*** (Tmin 7, Topt 27,5, Tmax 35 °C; LWDmin 6 h, LWDmax 36 h). Se calcula solo como comparación (`idx_antracnosis_gim`). A las temperaturas de la Sabana casi nunca se activa.

### 2.2 Botrytis (*B. cinerea*), con flor de fresa como proxy

**Bulger, Ellis y Madden 1987** (*Phytopathology* 77:1225-1230). PUBLICADO, con los coeficientes de NC State IPM:

```
f = -4.268 - 0.0901·LWD + 0.0294·LWD·T - 2.35e-5·LWD·T³
índice = logística(f)
```

- **Comprobación**: reproduce la gráfica de NCSU a 20,5 °C (0,50 a 13,8 h y 0,70 a 16,5 h). El óptimo analítico es 20,4 °C.
- **Umbral de acción**: 0,50, validado en campo por MacKenzie y Peres 2012 (*Plant Dis.* 96:529-536).
- **Rango experimental**: 5-30 °C y hasta 32 h, NO VERIFICADO directamente porque APS devolvió 403. Cada evento fuera de ese rango lleva la bandera `botrytis_fuera_de_rango`.
- **Qué modela**: infección de **flores** de fresa. Por eso el multiplicador de fenología la deja completa en floración.

### 2.3 Roya del arándano (*Thekopsora minima* = *Pucciniastrum minimum*). APROXIMACION

No hay un modelo publicado de T × mojadura para esta roya. Se usa el **modelo genérico de infección (GIM) de Magarey, Sutton y Thayer 2005** (*Phytopathology* 95:92-100). Según su resumen, el GIM está pensado justamente para patógenos sin datos epidemiológicos extensos y admite temperaturas cardinales estimadas. La forma es la que publica NCSU:

```
α   = ln2 / ln[(Tmax-Tmin)/(Topt-Tmin)]
f_T = [2(T-Tmin)^α (Topt-Tmin)^α - (T-Tmin)^(2α)] / (Topt-Tmin)^(2α)   (0 fuera de [Tmin, Tmax])
I   = LWD·f_T / LWDmin            (I = 0 si LWDmin/f_T > LWDmax: lectura nuestra de Magarey, NO VERIFICADO)
índice = 0.15^(3.5 · 0.15^(0.75·I))      (I = 1 → 0,20; I = 2 → 0,68, como en la nota y la curva de NCSU)
```

Parámetros:

| Parámetro | Valor | Fuente |
|---|---|---|
| Topt | 21,5 °C | Óptimo de germinación de urediniosporas (Pfister et al. 2004, *Plant Dis.* 88:359; trabajo en *Rhododendron*). Griffin y Anderson 2026 (*J. Fungi* 12:133) dan 19-23 °C como favorable. |
| Tmin | 8 °C | SUPUESTO. La germinación es "muy reducida" bajo 15 °C pero ocurre a 10 °C. |
| Tmax | 32 °C | SUPUESTO. A 30 °C caen los uredinios, pero no llegan a cero (Pfister 2004). |
| LWDmin | 8 h | SUPUESTO, tomado de las 4-8 h de otras royas (*Uromyces*). |
| LWDmax | 48 h | Evaluación EPPO resumida por DEFRA (2021): 15-25 °C y 48 h de mojadura. |

**Presión a 14 días**: `1 - Π(1 - índice_evento)` sobre los periodos de los últimos 14 días. Es un SUPUESTO de independencia entre eventos. Refleja el ciclo de 10-14 días: latencia de ~10 d a 20 °C según el PNW Handbook, de 10-10,7 d a 20-25 °C según Pfister 2004 y más cerca de 14 d a 15 °C.

### 2.4 Oídio: índice de Gubler-Thomas (UC Davis), de la **vid**. NO VALIDADO en arándano

Reglas PUBLICADAS por UC IPM (Thomas, Gubler y Leavitt 1994):

- **Arranque**: 3 días seguidos con al menos 6 h consecutivas entre 21,1 y 29,4 °C (70-85 °F). Cada uno de esos días suma +20.
- **Después del arranque**: +20 por cada día con esas 6 h y −10 por cada día sin ellas.
- **Calor**: −10 si alguna hora llega a 35 °C o más (95 °F).
- **Límites**: el índice va de 0 a 100 y el cambio diario va de −10 a +20.
- **Aplicación de fungicida**: vuelve el índice a 0 (`fechas_aplicacion`).
- **Escala**: el índice se divide por 100. Bajo es 30 o menos (< 0,40), medio es 40-50 y alto es 60 o más.
- **Datos horarios**: cualquier hora fuera del rango corta la racha. UC IPM habla de 45 min; con resolución horaria se aplica a la hora completa.

## 3. Clasificación y fenología

| Enfermedad | Medio desde | Alto desde | Fuente |
|---|---|---|---|
| Antracnosis | 0,15 | 0,50 | PUBLICADO: NCSU FLSAS y MacKenzie y Peres 2012a (captan si INF > 0,15; piraclostrobina si > 0,5) |
| Botrytis | 0,50 | 0,70 | PUBLICADO: NCSU FLSAS y MacKenzie y Peres 2012b (INF ≥ 0,50) |
| Roya | 0,20 | 0,50 | SUPUESTO: 0,20 equivale a 1 ciclo GIM (~20 % de incidencia) |
| Oídio | 0,40 | 0,60 | PUBLICADO para vid (UC IPM) |

**Multiplicador de fenología** (todo SUPUESTO; va de 0 a 1, y 1 deja intacto el índice publicado). Se aplica como `índice_ajustado = índice × m` y la clase se calcula sobre el ajustado. Sin `--etapa`, m = 1.

| Enfermedad | Vegetativo | Floración | Fruto verde | Maduración | Razón |
|---|---|---|---|---|---|
| Antracnosis | 0,2 | 0,6 | 1,0 | 1,0 | Infecta el fruto entre floración y cosecha; latente en fruto verde (MSU E-3039; Gillett y Schilder 2009) |
| Botrytis | 0,3 | 1,0 | 0,5 | 0,7 | Bulger modela flores; CT CAES: pétalos senescentes y brotes tiernos |
| Roya | 1,0 | 1,0 | 1,0 | 1,0 | Enfermedad de hoja; en el trópico la planta no defolia |
| Oídio | 1,0 | 0,8 | 0,8 | 0,6 | Cornell: los conidios infectan tejido emergente |

**Resumen diario.** Cada día D toma el máximo de cada periodo que lo toca, evaluado con la LWD acumulada hasta el final de D. Así un periodo de 3 días sube el riesgo día a día.

**Ventana de 72 h.** `riesgo_ventana_72h` toma el máximo de ayer, hoy y mañana, como el mapa de NCSU.

*[Cambio de verificacion-riesgo-clima, 23-oct-2026]* Si la fecha pedida queda fuera del pronóstico (p. ej. caché vencida el día de la demo), `riesgo_ventana_72h` devuelve `riesgo_global = "sin_datos"` con un campo `error`, en lugar del antiguo `"bajo"` silencioso; si solo hay 1 o 2 de los 3 días, agrega `advertencia`. Hay una prueba nueva (`test_ventana_72h_sin_datos_no_es_bajo`): ahora son 136 pruebas. Las salidas del 23-oct-2026 no cambian.

## 4. Evidencia

### 4.1 Casos de libro (todos en `tests/`)

| Caso | Publicado | Obtenido |
|---|---|---|
| Wilson a 26,6 °C | 0,15 a 7,0 h; 0,50 a 13,1 h | 0,151; 0,499 |
| Bulger a 20,5 °C | 0,50 a 13,8 h; 0,70 a 16,5 h | 0,503; 0,700 |
| Temperaturas óptimas (NCSU) | 26,6 / 20,5 °C | 26,5 / 20,4 °C |
| GIM | I = 1 → ~20 %; I = 2 → ~0,68 | 0,202; 0,680 |
| Aprox. arándano: W50 dentro de los rangos de Gillett y Schilder | — | Se cumple a 10, 15, 20, 25 y 30 °C |
| Aprox. arándano: índice a 6 h | < 0,15 | Se cumple |
| Wilson: W50 a 20 y 25 °C | 12-18 h observado en arándano | 18,0 h y 13,4 h |

### 4.2 Clima real 2025 (Open-Meteo horario, 365 días por punto)

Ejecutado con `correr_2025.py`. Durante los periodos de mojadura la temperatura mediana fue de 8,6 a 10,6 °C, según el punto.

**Días medio/alto con el criterio central** (HR ≥ 90 % o lluvia ≥ 0,5 mm/h):

| Punto | Antracnosis | Botrytis | Roya | Oídio |
|---|---|---|---|---|
| Chía | 36 / 6 | 11 / 16 | 20 / 6 | 0 / 0 |
| Guasca | 17 / 4 | 5 / 10 | 13 / 6 | 0 / 0 |
| Sotaquirá | 38 / 3 | 6 / 18 | 17 / 4 | 0 / 0 |
| Tausa | 20 / 3 | 6 / 17 | 2 / 0 | 0 / 0 |

**Sensibilidad al criterio de mojadura** (días en alto; antracnosis / Botrytis / roya):

| Punto | HR ≥ 85 % o lluvia ≥ 0,5 mm/h (alerta) | HR ≥ 95 % | HR ≥ 90 % o lluvia > 0 |
|---|---|---|---|
| Chía | 12 / 35 / 14 | 3 / 5 / 3 | 140 / 167 / 154 |
| Sotaquirá | 14 / 45 / 14 | 0 / 7 / 1 | 183 / 222 / 193 |

Con "lluvia > 0" la llovizna espuria del modelo encadena periodos de hasta 396 h, y el sistema pasaría casi la mitad del año en alerta. Por eso el umbral de 0,5 mm/h es necesario. Las tablas completas, incluidos LWP ≥ 50 y los 4 puntos, están en `salidas/resumen_dias_por_clase_2025.csv`.

**Alertas operativas** (periodos de mojadura que llegan a "alto", criterio central): entre 0 y 11 por año, por punto y enfermedad. Botrytis da 5-11 por año y antracnosis 2-5 por año (`salidas/alertas_por_periodo_2025.csv`).

**Estacionalidad**: el riesgo se concentra en feb-may, con el máximo en abril, y repunta en agosto y octubre. Sigue el patrón bimodal de la lluvia (`salidas/riesgo_mensual_2025.csv`, `graficas/riesgo_diario_2025.png`).

**Elección del modelo de antracnosis**: con la ecuación de fresa sola, **0 días en alto** en los 4 puntos (2-6 días en medio). Con la envolvente hay 3-6 días en alto y 17-38 en medio (`salidas/comparacion_modelos_antracnosis_2025.csv`). En la Sabana fría el modelo de fresa casi no ve la enfermedad.

**Oídio (Gubler-Thomas)**: **0 días** en todos los puntos. En la Sabana casi nunca hay 6 h seguidas entre 21 y 29 °C. Este índice de vid no sirve aquí; el oídio queda a cargo del clasificador visual.

## 5. Límites (léanse antes de presentar cifras)

1. **No hay validación con incidencia de campo en Colombia.** Las cifras de 4.2 son frecuencias de alerta, no aciertos. La meta de sensibilidad ≥ 90 % **no se puede verificar** con estos datos.
2. **La mojadura es un proxy** (HR y lluvia de un modelo meteorológico), no un sensor de hoja. El equipo de clima midió que Open-Meteo sobreestima las horas de lluvia entre 1,7 y 4,5 veces. Los resultados cambian mucho con el umbral (ver 4.2).
3. **Antracnosis**: la ecuación es de fresa. La aproximación de arándano se apoya en un resumen de 5 anclas cualitativas ("aumento considerable" se interpreta como índice 0,5). Los coeficientes de Miles 2013 no se obtuvieron. Fuera de 10-30 °C la curva es extrapolación.
4. **Botrytis**: es infección de flor de fresa en laboratorio. A 8-10 °C, la temperatura típica de la Sabana durante la mojadura, el modelo está en el borde frío de su rango. Los periodos de más de 32 h son extrapolación y van marcados con bandera.
5. **Roya**: Tmin, Tmax y LWDmin son SUPUESTOS. Pfister 2004 trabajó en *Rhododendron*. No hay curva de mojadura para *T. minima*. Los umbrales de clase también son SUPUESTO.
6. **Oídio**: el índice es de vid, para California; no está validado en arándano. Cornell indica que el oídio del arándano no necesita agua libre en la hoja, así que un índice de mojadura no lo representa.
7. **El multiplicador de fenología es SUPUESTO** en todos sus valores.
8. **Riego por aspersión**: suma mojadura (EDIS PP366 lo cita como fuente de mojadura). Solo se incluye si llega la columna `riego`. Sin ella, el riesgo en camas con aspersor está subestimado.
9. **Resolución horaria**: la regla de 45 min de Gubler-Thomas y la de 15 min a ≥ 35 °C se aplican a la hora completa. La precipitación horaria de Open-Meteo acumula la hora anterior; ese desfase de 1 h se ignora.

## 6. Fuentes abiertas en esta sesión

Las copias locales están en `raw/riesgo_*`.

- NC State IPM, "Development of Anthracnose and Botrytis Strawberry Fruit Infection Risk Models" (actualizada el 23-jul-2025). Contiene las ecuaciones FLSAS y GIM como imágenes, los umbrales, las gráficas, la regla de 4 h secas y la ventana de 72 h. https://ipm.ces.ncsu.edu/development-of-anthacnose-and-botrytis-strawberry-fruit-infection-risk-models (`raw/riesgo_ncsu_sas/`).
- Gama, Phillips, Cerbaro, Harmon, Fraisse y Peres 2022. *Blueberry Advisory System*. EDIS PP366, doi:10.32473/edis-PP366-2022. https://edis.ifas.ufl.edu/publication/PP366/pdf (`raw/riesgo_edis_pp366/`).
- Gama et al. 2021, *Plant Dis.* 105:1806-1813, doi:10.1094/PDIS-09-20-1961-RE. Resumen en Europe PMC, PMID 32954983 (`raw/riesgo_europepmc/`).
- MacKenzie y Peres 2012a, *Plant Dis.* 96:522-528, doi:10.1094/PDIS-03-11-0181, y 2012b, *Plant Dis.* 96:529-536, doi:10.1094/PDIS-03-11-0182. Resúmenes vía Crossref (`raw/riesgo_crossref/busquedas.jsonl`).
- Miles, Gillett, Jarosz y Schilder 2013, *Plant Pathol.* 62:1238-1247, doi:10.1111/ppa.12061. Solo el resumen, vía Crossref (`raw/riesgo_crossref/miles2013_ppa.12061.json`).
- Gillett y Schilder 2009, *Acta Hortic.* 810:355-360, doi:10.17660/ActaHortic.2009.810.46. Resumen en https://www.actahort.org/books/810/810_46.htm (`raw/riesgo_actahort_810_46/`).
- Pavan, Fraisse y Peres, *Strawberry Advisory System*, UF/IFAS AE450. https://ask.ifas.ufl.edu/publication/AE450 (`raw/riesgo_uf_ae450/`).
- hortidaily, 10-abr-2025: MSU adapta el modelo de UF al arándano en Michigan. https://hortidaily.com/article/9719902/us-blueberry-rot-risk-prediction-model-launched-for-michigan-growers
- Magarey, Sutton y Thayer 2005, *Phytopathology* 95:92-100. Resumen en Europe PMC, PMID 18943841.
- Pfister, Halik y Bergdahl 2004, *Plant Dis.* 88:359-362. Resumen en Europe PMC, PMID 30812614.
- Griffin y Anderson 2026, *J. Fungi* 12:133, CC BY (`raw/ciencia_mdpi_jof12_133/`).
- DEFRA 2021, resumen de la evaluación de riesgo de *T. minima* que cita a EPPO. https://planthealthportal.defra.gov.uk/assets/uploads/T.minima-summary-for-consultationMay21.pdf (`raw/riesgo_defra_tminima/`).
- PNW Plant Disease Handbook, Blueberry rust (`raw/paramsim_pnw_rust/`).
- Salazar y Buriticá 2012, *Rev. Fac. Nac. Agron. Medellín* 65(2):6697-6702 (`raw/ciencia_rfnam_royas2012/`). Registro de *T. minima* en Colombia.
- UC IPM, "Powdery mildew of grape" (modelo Gubler-Thomas). https://ipm.ucanr.edu/DISEASE/DATABASE/grapepowderymildew.html (`raw/riesgo_ucipm_gpm/`). Implementación de la Oregon State: https://hopper.science.oregonstate.edu/risk/grape_powdery_app
- Cornell, Blueberry Disease Fast Facts: Powdery Mildew (`raw/ciencia_cornell_oidio/`). CT CAES, Botrytis Blight of Blueberry (`raw/ciencia_caes_botrytis/`). MSU E-3039 (`raw/paramsim_msu_e3039_archive/`).
- Strawberry Center blog, "Classic Botrytis data from 1987": óptimo de 20 °C. https://strawberrycenterblog.com/2022/04/13/classic-botrytis-data-from-1987/

**Fuentes bloqueadas.** Estas respondieron con un desafío anti-bot o con 403. No se intentó saltar el bloqueo y cada carpeta tiene un `NOTA.txt`:

- MSU: PDF de Miles 2013, noticias de Enviroweather y tesis.
- APS: Bulger 1987, MacKenzie y Peres 2012 y UC Davis risk.
- Agriculture Victoria, UTAS y NSW DPI (roya).

Licencias: los artículos se citan y no se redistribuyen. Las copias en `raw/` son para trazabilidad interna.
