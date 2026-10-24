# Reporte: clima-open-meteo (datos climáticos reales para el riesgo ambiental)

Agente: clima-open-meteo. Fecha de trabajo: 2026-10-23 (descargas entre 21:58 y 22:20 UTC).
Carpeta: `/Users/santiagosantafe/Downloads/SabanaHack/datos/clima/` (más `raw/ideam_datosgov_2025/` y `raw/eva_upra_arandano/`).

## Lo esencial

1. **Puntos (4).** Elegí 3 puntos productores, que son los municipios de Cundinamarca y Boyacá con más área de arándano según la EVA oficial de 2025: **Sotaquirá** (182 ha, 1.º del país), **Tausa** (121 ha, 1.º de Cundinamarca) y **Guasca** (57 ha). Los tres suman 360 de 906,7 ha nacionales, es decir **el 39,7 %**. Agregué **Chía** solo como sitio de la demo (U. de La Sabana). Chía **no tiene área de arándano** reportada en la EVA 2019–2025.
2. **Histórico 2025 de Open-Meteo (horario, America/Bogota).** Bajé 8.760 h por punto. QC: **0 huecos, 0 duplicados, 0 valores fuera de rango**, y la zona horaria es correcta. La mínima de T cae a las 6 h locales (moda; mediana 5 h), es decir **en torno al amanecer calculado (≈5,9 h; mediana de la diferencia −0,7 h)**. [verificacion-riesgo-clima, 2.ª pasada: decía "6 h, es decir ~0,7 h antes del amanecer", que mezclaba la moda con la mediana]
3. **`leaf_wetness_probability` (LWP)** también sale en la API de archivo, aunque no está documentada ahí. **No sirve en altiplano.** Es una fórmula heurística de Open-Meteo (la reproduje con un error medio ≤0,23 puntos) que multiplica por un factor de temperatura: 0 a 5 °C y 1 a 15 °C. Las horas más húmedas son noches de 8–10 °C, así que la LWP **baja cuando la HR pasa del 80 %**.
4. **Validación con 6 estaciones públicas (datos.gov.co, sin login).**
   - Temperatura: MAE de 1,2–1,6 °C, r = 0,85–0,92.
   - Humedad relativa: MAE de 7–12 puntos, r = 0,75–0,88.
   - Este resultado depende de un hallazgo: **las fechas de las estaciones del IDEAM vienen en UTC**. Sin corregir −5 h, la correlación de T es aprox. 0. Los metadatos no lo dicen.
   - **La lluvia de Open-Meteo no es confiable a escala de finca.** Marca entre 1,7 y 4,5 veces más horas con lluvia que el pluviómetro (llovizna espuria).
5. **Proxy de hoja mojada recomendado para el equipo de riesgo:**
   - **Alerta (orientada a sensibilidad):** `HR_OpenMeteo ≥ 85 % o lluvia ≥ 0,5 mm/h`. Detecta el 87–89 % de las horas observadas con HR ≥ 90 % en 2 de las 3 estaciones válidas con pluviómetro (en Duitama solo el 72 %).
   - **Estimación central:** `HR ≥ 90 % o lluvia ≥ 0,5 mm/h`.
   - **No usar** `lluvia > 0`: con `HR ≥ 90 % o lluvia > 0`, Open-Meteo marca como mojadas entre el 55 y el 74 % de las horas del año.
   - **No usar** LWP.

## 1. Puntos elegidos y por qué

| Punto | Coordenadas (cabecera) | Elev. (m) | Área de arándano 2025 (ha) | Rol |
|---|---|---|---|---|
| sotaquira | 5.76483, −73.24758 | 2.677 | 182 | Mayor área del país (EVA 2025) |
| tausa | 5.19903, −73.89128 | 2.992 | 121 | Mayor área de Cundinamarca |
| guasca | 4.86601, −73.87748 | 2.681 | 57 | Oriente de la Sabana; estación IDEAM a 2 km |
| chia | 4.85876, −74.05866 | 2.557 | 0 | Solo sitio de la demo (U. de La Sabana) |

- **Fuente del área:** Evaluaciones Agropecuarias Municipales – EVA 2019–2025, Base Agrícola (UPRA/MinAgricultura), datos.gov.co, dataset `uejq-wxrr`, licencia CC BY-SA 4.0. Consulta: `cultivo like '%ARÁNDANO%'`, 289 filas, guardadas en `raw/eva_upra_arandano/eva_arandano_2019_2025.json`.
  - Total nacional 2025: 906,7 ha (Boyacá 437,4 y Cundinamarca 419,7).
  - Ranking 2025: Sotaquirá 182, Tausa 121, Cómbita 85, Ventaquemada 59, Guasca 57, Sopó 31.
- **Coordenadas y elevación:** geocodificador de Open-Meteo (`geocoding-api.open-meteo.com`).
- **Contexto (prensa del sector, no oficial):**
  - Portal Frutícola (23-feb-2026, Asocolblue): Cundinamarca y Boyacá concentran ~90 % de la producción, en cultivos de montaña entre 2.200 y 2.900 m.
  - Agronegocios (11-feb-2026, Asocolblue): ~1.000 ha, mitad Boyacá y mitad Cundinamarca.
  - Estas cifras gremiales (~1.000 ha) son mayores que las de la EVA (906,7 ha). Para cálculos usar la EVA.
- **Límite:** las coordenadas son de la cabecera municipal, no de fincas reales (NO VERIFICADO dónde están las fincas). La cabecera de Tausa (2.992 m) está algo por encima del rango típico.

## 2. Descargas de Open-Meteo

- **Histórico:** `https://archive-api.open-meteo.com/v1/archive`, del 2025-01-01 al 2025-12-31, `timezone=America/Bogota`, modelo `best_match` (por defecto; según la documentación combina ECMWF IFS 9 km, ERA5 y ERA5-Land).
  - Variables: `temperature_2m, relative_humidity_2m, dew_point_2m, precipitation, wind_speed_10m, leaf_wetness_probability`.
  - Unidades: °C, %, mm/h y km/h.
  - Para medir la sensibilidad al modelo bajé también `era5_land` y `era5`. **ERA5-Land no devuelve lluvia ni viento en 2025** (100 % NaN).
- **Pronóstico:** `https://api.open-meteo.com/v1/forecast`, `forecast_days=7`, `past_days=2`, las mismas variables más `precipitation_probability`. Cubre del 2026-10-21 al 2026-10-29: 216 h por punto.
- **Para comparar con el IDEAM:** el mismo histórico en las coordenadas exactas de cada estación (`historico_2025_est_<código>.csv`).
- **Mojadura de hoja:** la documentación solo lista una LWP diaria (`leaf_wetness_probability_mean`), pero la variable horaria `leaf_wetness_probability` funciona en forecast, archive e historical-forecast (verificado el 2026-10-23).
- **Licencia:** Open-Meteo, CC BY 4.0. Hay que poner "Weather data by Open-Meteo.com" junto a cualquier dato mostrado (página de licencia). Fuentes de los datos: ECMWF IFS y Copernicus ERA5.

**Archivos** (`clima/cache/`):
- `historico_2025_<punto>.csv`, más `_era5_land.csv` y `_era5.csv`.
- `historico_2025_est_<código>.csv` (6 estaciones), más `historico_2025_est_0021205518_elevest.csv`.
- `pronostico_<punto>_20261023T22xxxxZ.csv`.
- `parquet/`: los mismos 23 CSV convertidos con polars del `.venv` (`scripts/csv_a_parquet.py`).
- `json/`: caché cruda del cliente, más `_indice.csv` (clave → URL y parámetros).

## 3. Cliente `clima/clima_client.py`

- Usa solo librería estándar (urllib y json); pandas es opcional. Funciona con `python3 -I`.
- **Caché en disco:** cada respuesta se guarda como `cache/json/<sha1(endpoint+params)>.json` con la hora de descarga.
  - Histórico: la caché no vence.
  - Pronóstico: vence a la hora (TTL 1 h).
  - Además guarda `pronostico_<punto>_ultimo.json`.
- **Sin internet**, o con `CLIMA_OFFLINE=1`:
  - Devuelve la caché aunque esté vencida.
  - Si los parámetros no están en caché, devuelve el último pronóstico del punto.
  - El campo `origen` dice de dónde vino el dato: `red`, `cache`, `cache_vencida` o `cache_ultimo_pronostico`.
- **API:**
  - `ClimaClient().pronostico("chia")` y `pronostico_df(...)`.
  - `historico("guasca", "2025-01-01", "2025-12-31", modelo=None, elevacion=None)` e `historico_df(...)`.
  - Acepta `(lat, lon)` en lugar del nombre del punto.
- **CLI:** `descargar-todo`, `pronostico <punto>`, `offline-test`.
- **Prueba sin red (`offline-test`):** OK en los 4 puntos (216 h de pronóstico y 8.760 h de histórico). El fallback con parámetros no cacheados también funciona.

## 4. Control de calidad (Open-Meteo `best_match`, 2025)

Archivo: `clima/qc/qc_openmeteo.csv`. Gráfica: `graficas/qc_ciclo_diario_temperatura.png`.

- **Completitud:** 8.760 de 8.760 h en los 4 puntos y los 3 modelos. 0 marcas faltantes, 0 duplicadas, paso único de 1 h.
- **Rangos físicos** (criterio propio: T de −10 a 35 °C, HR de 0 a 100 %, Td de −25 a 25 °C, lluvia de 0 a 80 mm/h, viento de 0 a 120 km/h): 0 valores fuera de rango. Nunca Td > T. *[Precisión de verificacion-riesgo-clima, 23-oct-2026: el chequeo usa una tolerancia de 0,2 °C (`analisis_clima.py`, línea 116). Sin tolerancia hay 15 h con Td = T + 0,1 °C, todas con HR = 100 % (9 en Sotaquirá y 6 en Chía): es redondeo, no un error de datos.]*
- **Zona horaria:** las 27 respuestas en caché dicen `America/Bogota` con `utc_offset_seconds = −18000`.
- **Ciclo diario:**
  - Hora modal de la T mínima: **6 h local** en los 4 puntos.
  - Entre el 58 y el 74 % de los días tienen la mínima entre las 4 y las 7 h.
  - Mediana de (hora de la mínima − amanecer NOAA) = **−0,7 h**, con amanecer medio de 5,82–5,88 h local.
  - Máxima a las 12–14 h.
  - Si la serie estuviera en UTC, la mínima caería hacia las 11 h. **Conclusión: la hora local es correcta.**

**Resumen anual** (de `qc/resumen_mensual_openmeteo_2025.csv` y `qc/resumen_anual_openmeteo_2025.csv`):

| Punto | T media | Tmín/Tmáx medias diarias | HR media | Lluvia OM (mm) | h HR ≥ 85 | h HR ≥ 90 | h HR ≥ 95 |
|---|---|---|---|---|---|---|---|
| Sotaquirá | 13,0 | 8,6 / 19,8 | 81,6 | 1.365 | 5.153 | 4.741 | 4.080 |
| Tausa | 10,6 | 6,7 / 15,7 | 83,0 | 1.269 | 5.044 | 4.184 | 2.629 |
| Guasca | 13,5 | 8,8 / 19,4 | 75,5 | 1.155 | 4.129 | 3.106 | 1.392 |
| Chía | 13,0 | 8,6 / 18,9 | 81,0 | 1.453 | 4.797 | 4.174 | 2.821 |

- Patrón de lluvia bimodal: picos en mar–may y oct; mínimos en ene y dic (`graficas/resumen_mensual_2025.png`).
- **Sensibilidad al modelo** (`qc/sensibilidad_modelo_openmeteo.csv`): para el mismo punto la T media cambia hasta 1,5 °C (Sotaquirá: 13,0 en best_match y 14,6 en ERA5) y las horas con HR ≥ 90 % cambian hasta 1,8× (de 2.627 a 4.741). Por eso hace falta validar con estaciones.

## 5. Proxy de hoja mojada y sensibilidad al umbral

Archivos: `clima/derivados/`. Gráficas: `graficas/hoja_mojada_sensibilidad_umbral.png` y `graficas/hoja_mojada_HR_vs_LWP.png`.

**Definición pedida:** `mojada = HR ≥ u o lluvia > 0`, con u = 85, 90 o 95.

**Horas por mes que cambian según el umbral** (media del año; entre paréntesis, el mínimo y máximo mensual):

| Punto | 85 → 90 | 90 → 95 | 85 → 95 | Cambio relativo 85 → 95 |
|---|---|---|---|---|
| Sotaquirá | −25 (16–38) | −41 (23–61) | −66 | −12 % |
| Tausa | −54 (15–90) | −108 (56–158) | −162 | −28 % |
| Guasca | −73 (43–110) | −120 (68–164) | −194 | −41 % |
| Chía | −42 (18–84) | −97 (49–177) | −139 | −26 % |

**Sensibilidad al umbral de lluvia** (`derivados/sensibilidad_umbral_lluvia.csv`; HR ≥ 90 %, h/mes):

| Punto | lluvia > 0 | ≥ 0,2 mm | ≥ 0,5 mm | ≥ 1 mm |
|---|---|---|---|---|
| Chía | 488 | 418 | 378 | 368 |
| Guasca | 403 | 334 | 281 | 268 |
| Sotaquirá | 537 | 476 | 422 | 410 |
| Tausa | 523 | 452 | 381 | 363 |

- Con `lluvia > 0`, entre el 24 y el 59 % de las horas mojadas lo son **solo por lluvia**.
- Open-Meteo da lluvia ≥ 0,1 mm en 2.427–2.882 h/año.

**Proxy frente a la LWP de Open-Meteo (LWP ≥ 50 %)** (`derivados/proxy_vs_LWP50_concordancia.csv`):
- Concordancia baja: kappa de 0,03 a 0,24.
- La LWP marca muchas menos horas (Tausa: 1.634 h/año frente a 4.987–6.931 del proxy).
- Esto **no** indica que el proxy esté mal. Al reproducir la fórmula del código fuente de Open-Meteo (`qc/verificacion_formula_lwp.csv`, MAE 0,12–0,23 puntos frente a la API) se ve por qué:
  - Si lluvia > 1 mm: LWP = min(80 + 2·lluvia, 100).
  - Si no: LWP = clip((T − 5)/10, 0, 1) × clip(1 − (VPD − 0,1)·1,25, 0, 1) × 100.
  - En las horas con HR ≥ 90 % la T media es de 8,3–10,4 °C. En Tausa, el 88,5 % de esas horas tiene T < 10 °C.
  - Por eso la LWP media en horas saturadas sin lluvia es solo del 30–50 %.
  - **Es un artefacto de una fórmula pensada para climas templados. No usar la LWP como referencia en el altiplano.**

**Eventos de mojadura** (`derivados/eventos_mojadura_2025.csv`):
- Contiene horas mojadas consecutivas, sin tolerar interrupciones, con duración y T media del evento.
- Criterios: HR85, HR90, HR95, LWP50, HR85_P05 y HR90_P05.
- Ejemplo con HR90_P05: entre 551 y 591 eventos al año por punto, mediana de 5–12 h, y 91–286 eventos ≥ 12 h.
- **Insumo diario para los modelos de infección** (Miles 2013 antracnosis; Bulger 1987 Botrytis) *[Corrección de verificacion-riesgo-clima: `riesgo/risk.py` no implementa Miles 2013, cuyos coeficientes no se obtuvieron; usa Wilson et al. 1990 más una aproximación de arándano (Gillett y Schilder 2009). Además lee la serie horaria, no este archivo diario]*: `derivados/clima_diario_mojadura_2025.csv`. Tiene T media/mín/máx, HR, lluvia, horas mojadas por criterio y T media durante las horas mojadas.
- Serie horaria con todas las banderas: `derivados/hoja_mojada_horaria_<punto>.csv`.

## 6. Comparación con estaciones públicas (datos.gov.co, sin login)

**Fuentes** (IDEAM, licencia CC BY-SA 4.0; datos crudos "no validados por el IDEAM" según la descripción del dataset):
- `sbwg-7ju4`: temperatura del aire a 2 m, horaria.
- `uext-mhny`: humedad del aire, horaria.
  - La columna se llama "Humedad del aire, %", pero cada fila dice "HUMEDAD DEL SUELO A 1 m Ó MAS". Es un error de etiqueta: los valores se comportan como HR del aire (r con T de −0,79 a −0,92).
- `s54a-sgyg`: precipitación cada 10 min.
- `hp9r-jxuu`: catálogo de estaciones.

Descarga: `clima/scripts/descargar_ideam.py` → `raw/ideam_datosgov_2025/`, 103 MB. Comparación: `clima/scripts/analisis_clima.py`, sección 4.

**Hallazgo crítico de zona horaria.** En las estaciones de la entidad IDEAM, `fechaobservacion` está en **UTC**:
- Sin corrección, la correlación horaria de T con Open-Meteo va de −0,02 a 0,18 y la mínima de T cae a las 11 h.
- Con −5 h, r = 0,87–0,92, la mínima cae a las 6 h, y el desfase de r máximo es −5 h en 4 de las 5 estaciones (−6 h en Guasca).
- La estación de la CAR (Salitre) ya viene en hora local (desfase óptimo de 0 h).
- **Quien use datos IDEAM de datos.gov.co debe aplicar esta corrección.**

**Métricas 2025** (horas pareadas; Open-Meteo `best_match` en las coordenadas del catálogo; sesgo = OM − IDEAM). Archivo: `qc/ideam_vs_openmeteo_2025.csv`.

| Estación (código, alt.) | Punto asociado (dist.) | h pareadas T | T: sesgo / MAE / r | HR: sesgo / MAE / r | Lluvia IDEAM / OM (mm) · horas con lluvia IDEAM / OM | Observaciones |
|---|---|---|---|---|---|---|
| GUASCA (0021205700, 2.750 m) | Guasca (2 km) | 6.855 | +0,56 / 1,52 / 0,87 | −4,4 / 10,1 / 0,79 | 420 / 559 · 467 / 1.138 | HR máx. 94,8 %: el sensor no satura |
| U. DE LA SABANA (2120500135, 2.548 m) | Chía (3 km) | 7.497 | +0,01 / 1,16 / 0,92 | −2,4 / 7,1 / 0,86 | 711 / 2.145 · 653 / 2.948 | Mejor ajuste en T y HR |
| DUITAMA AUT (2403500041, 2.492 m) | Sotaquirá (22 km) | 7.418 | +0,76 / 1,58 / 0,91 | −10,4 / 11,6 / 0,87 | 782 / 857 · 447 / 1.683 | Open-Meteo bastante más seco |
| TUNGUAVITA AUT (0024035430, 2.521 m) | Sotaquirá (15 km) | 5.356 | +0,42 / 1,44 / 0,92 | +3,5 / 9,4 / 0,88 | 648 / 644 · 659 / 1.146 | HR máx. 91 %: sensor de HR inválido para mojadura |
| CUCUNUBÁ AUT (2401500040, 2.818 m) | Tausa (12 km) | 6.441 | −0,58 / 1,22 / 0,90 | −3,5 / 7,2 / 0,85 | 751 / 452 · 673 / 1.414 | |
| SALITRE AUT, CAR (0021205518, 2.637 m) | Tausa (14 km) | 3.392 | +0,54 / 1,15 / 0,85 | +1,1 / 7,5 / 0,75 | sin pluviómetro en el dataset | Solo jun–dic; ver nota abajo |

- **Salitre:** las coordenadas del catálogo caen en un DEM de 3.284 m. Forzar `elevation=2637` empeora (sesgo de T de +4,2 °C), así que la altitud o las coordenadas del catálogo son inconsistentes.
- **Huecos:** febrero de 2025 tiene solo 98 h en todas las estaciones (hueco de la red en datos.gov.co).
- **Duplicados:** se eliminaron duplicados exactos (hasta 770 por estación). No hubo duplicados conflictivos.

**Un mes completo, octubre de 2025** (`qc/ideam_vs_openmeteo_mensual_2025.csv`; gráficas `ideam_vs_openmeteo_2120500135_2025-10.png` y `ideam_vs_openmeteo_0021205700_2025-10.png`):

| Estación | T (°C): sesgo / MAE | HR (puntos): sesgo / MAE | h HR ≥ 90 IDEAM / OM | Lluvia IDEAM / OM (mm) |
|---|---|---|---|---|
| U. de La Sabana | +0,09 / 1,28 | −2,9 / 7,1 | 321 / 339 | 114 / 257 |
| Guasca | +0,75 / 1,57 | −4,4 / 10,8 | 164 / 253 | 77 / 174 |
| Cucunubá | −0,80 / 1,31 | −2,2 / 6,6 | 323 / 353 | 90 / 54 |
| Duitama | +0,97 / 1,56 | −10,6 / 11,4 | 391 / 275 | 95 / 116 |

**Calibración del umbral** (`qc/ideam_grilla_proxy_mojadura.csv`, `graficas/ideam_umbral_HR_openmeteo.png`).

Referencia observada: HR_IDEAM ≥ 90 % (más lluvia_IDEAM > 0 si hay pluviómetro). Se excluyen Tunguavita y Guasca por el sensor de HR. Sensibilidad, es decir, la fracción de horas mojadas observadas que Open-Meteo también marca:

| Umbral en Open-Meteo | U. Sabana | Cucunubá | Duitama | Salitre (solo HR) | Razón de horas OM/IDEAM |
|---|---|---|---|---|---|
| HR ≥ 80 % (solo HR) | 0,96 | 0,94 | 0,82 | 0,93 | 0,92–1,69 |
| HR ≥ 85 % (solo HR) | 0,92 | 0,91 | 0,73 | 0,89 | 0,80–1,51 |
| HR ≥ 90 % (solo HR) | 0,82 | 0,74 | 0,59 | 0,83 | 0,64–1,31 |
| HR ≥ 85 % o lluvia ≥ 0,5 mm | 0,87 | 0,89 | 0,72 | – | 0,81–1,41 |
| HR ≥ 90 % o lluvia ≥ 0,5 mm | 0,78 | 0,73 | 0,59 | – | 0,66–1,18 |

- **Recomendación** (coherente con preferir falsas alarmas):
  - Alerta: **HR_OM ≥ 85 % o lluvia ≥ 0,5 mm/h**. La sensibilidad es de ~0,9 en 3 de 4 estaciones, al costo de un 14–51 % más de horas marcadas.
  - En zonas tipo Duitama, donde Open-Meteo es más seco, ni 80 % llega a 0,9.
- **El umbral del IDEAM ≥ 90 % como referencia** se apoya en Sentelhas et al. (2008), *Agric. For. Meteorol.* 148:392–400 (resumen en explore.cnr.it):
  - Compararon HR constante ≥ 90 %, DPD y EXT_RH en Ames, Elora, Florencia y Piracicaba.
  - HR ≥ 90 % fue el mejor de los tres, con fracción de aciertos de 0,87–0,92, y ajustar el umbral al sitio mejoró la precisión.
  - **NO VERIFICADO en los Andes:** no hay sensores de mojadura en estas estaciones.

## 7. Fuentes que abrí

- **Documentación de Open-Meteo:**
  - https://open-meteo.com/en/docs/historical-weather-api
  - https://open-meteo.com/en/docs
  - https://open-meteo.com/en/docs/historical-forecast-api
  - Licencia: https://open-meteo.com/en/licence
- **Endpoints usados:** `archive-api.open-meteo.com/v1/archive`, `api.open-meteo.com/v1/forecast`, `historical-forecast-api.open-meteo.com/v1/forecast` y `geocoding-api.open-meteo.com/v1/search`.
- **Código fuente de Open-Meteo** (solo para entender la LWP; no se copió):
  - https://raw.githubusercontent.com/open-meteo/open-meteo/main/Sources/App/Helper/FaoEvapotranspiration.swift
  - https://raw.githubusercontent.com/open-meteo/open-meteo/main/Sources/App/Helper/Meteorology.swift
  - https://raw.githubusercontent.com/open-meteo/open-meteo/main/Sources/App/Controllers/VariableHourly.swift
- **datos.gov.co (API Socrata pública):**
  - https://www.datos.gov.co/d/uejq-wxrr (EVA)
  - https://www.datos.gov.co/resource/sbwg-7ju4.json
  - https://www.datos.gov.co/resource/uext-mhny.json
  - https://www.datos.gov.co/resource/s54a-sgyg.json
  - https://www.datos.gov.co/resource/hp9r-jxuu.json
  - Metadatos en `https://www.datos.gov.co/api/views/<id>.json`
- **Prensa del sector:**
  - https://www.portalfruticola.com/noticias/2026/02/23/arandanos-colombianos-tecnificacion-crecimiento-exportador/
  - https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623
- **Sentelhas et al. 2008:**
  - https://explore.cnr.it/resource/item/58890 (resumen)
  - https://repositorio.usp.br/item/001654141 (ficha)
  - DOI 10.1016/j.agrformet.2007.09.011
- **No se pudieron abrir:**
  - Ficha técnica del ICA de 2020 sobre arándano (redirige a 404). Lo que dice sobre Sotaquirá y Guasca queda NO VERIFICADO.
  - cundinamarca.gov.co (HTTP 402).
  - las2orillas (403).

## 8. Límites

- **Open-Meteo:** es un modelo o reanálisis de ~9–25 km con corrección por altura, no una medición en la cama.
  - Error horario frente a estación: T ±1,2–1,6 °C (MAE); HR ±7–12 puntos.
  - Las noches frías de valle (inversiones) están suavizadas. En Guasca la estación baja a 5 °C cuando Open-Meteo da 8 °C.
- **Lluvia:** Open-Meteo sobreestima la frecuencia de lluvia (1,7–4,5 veces más horas). El total anual varía entre 0,6 y 3,0 veces lo observado según la celda. Ejemplo: en la celda de la U. de La Sabana da 2.145 mm, y en la de la cabecera de Chía, a 3 km, 1.453 mm. No usar la lluvia horaria del modelo como evidencia de campo.
- **IDEAM:**
  - Son datos crudos.
  - Tienen el desfase UTC sin documentar.
  - Las etiquetas de sensor son erróneas.
  - Los sensores de HR de Guasca y Tunguavita no saturan.
  - Hay un hueco en febrero.
  - Salitre tiene coordenadas o altitud inconsistentes y no tiene lluvia.
  - La estación más cercana a Sotaquirá está a 15–22 km y 150–190 m más abajo.
- **Representatividad:** un solo año (2025). Hay 3 municipios productores (40 % del área de la EVA). Faltan Cómbita y Ventaquemada (Boyacá) y Antioquia.
- **Mojadura real:** no hay sensores de mojadura de hoja. Todos los proxies son de HR o lluvia, así que la "sensibilidad" de la sección 6 compara un proxy contra otro proxy observado, no contra hojas mojadas reales.
- **Eventos:** los que cruzan el 1 de enero quedan truncados.

## 9. Pendientes y sugerencias para el equipo

1. **Equipo de riesgo:** usar `derivados/clima_diario_mojadura_2025.csv` o los eventos con el criterio `HR85_P05` para la alerta y `HR90_P05` como escenario central. Documentar ambos en la diapositiva de evidencia.
2. **Demo:**
   - `ClimaClient().pronostico("chia")` funciona sin red; ya está la caché del 2026-10-23.
   - Refrescar el pronóstico el día de la demo con `python3 -I clima/clima_client.py descargar-todo`, o solo `pronostico chia`.
   - Mostrar "Weather data by Open-Meteo.com".
3. **Si hay tiempo:** repetir la comparación con 2024; añadir Cómbita y Ventaquemada como puntos; pedir a Asocolblue o a una finca un registro de mojadura o un sensor para calibrar el umbral.
4. **API key de Roboflow:** no se usó en este rol y no aparece en ningún archivo de `clima/`.

## Cómo reproducir

```
/usr/bin/python3 -I /Users/santiagosantafe/Downloads/SabanaHack/datos/clima/clima_client.py descargar-todo
/usr/bin/python3 -I /Users/santiagosantafe/Downloads/SabanaHack/datos/clima/scripts/descargar_om_estaciones.py
/usr/bin/python3 -I /Users/santiagosantafe/Downloads/SabanaHack/datos/clima/scripts/descargar_ideam.py   # ~20 min (lluvia cada 10 min)
/usr/bin/python3 -I /Users/santiagosantafe/Downloads/SabanaHack/datos/clima/scripts/analisis_clima.py
/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I /Users/santiagosantafe/Downloads/SabanaHack/datos/clima/scripts/csv_a_parquet.py
```

Con `-I` no se cargan los paquetes del sitio de usuario, donde están pandas y matplotlib del sistema. Por eso `analisis_clima.py` agrega `site.getusersitepackages()` de forma explícita, y `clima_client.py` no necesita pandas.
