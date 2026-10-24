# Capa ambiental global: riesgo desde el día 1 en cualquier finca

Rol: clima-global. Sabana Hack 2026, reto "Berry Good Idea". Fecha: 2026-10-23.

La organización quiere vender la solución a muchos productores y en otros frutales. Por eso la capa ambiental no puede depender de la Sabana de Bogotá ni de que cada finca compre una estación. La Sabana se queda como ejemplo de la demo y como banco de prueba: ahí hay estaciones IDEAM contra las cuales medir.

Cómo citamos las cifras. **CALCULADO** quiere decir que la cifra sale de nuestros scripts sobre datos abiertos; el archivo correspondiente está en la sección 9. **SUPUESTO** es un valor nuestro que todavía no tiene fuente. **NO VERIFICADO** es algo que solo vimos en un resumen de búsqueda, sin abrir la página. Las demás cifras llevan la URL de la página que abrimos.

---

## 0. Resumen

1. **El día 1 basta con la coordenada y el cultivo.** El pronóstico global (Open-Meteo, que en los 6 puntos colombianos probados sirvió en 2025 ECMWF IFS a 9 km) corregido por altura con un DEM de 90 m da la temperatura horaria con un error medio absoluto de 1,15 a 1,58 °C en 6 estaciones IDEAM de 2025 (CALCULADO). Probamos el mismo código, en una sola petición, con 7 puntos de Colombia, Perú, Chile y México. Tardó 2,2 s (CALCULADO).
2. **La variable que decide es la hoja mojada, y ningún producto global la mide.** El proxy HR ≥ 90 % calculado con el modelo se equivoca en promedio entre 3,0 y 4,8 h/día frente a la estación. En Duitama el modelo subestima la HR en 10 puntos y pierde 4,3 h de mojado al día (CALCULADO). La "probabilidad de hoja mojada" horaria de Open-Meteo, que no está documentada, concuerda poco con el proxy de estación: con umbral de 50 % detecta entre 7 % y 71 % de las horas mojadas (CALCULADO).
3. **Con 2 a 4 semanas de sensor se arregla casi todo.** La corrección por hora del día y el ajuste del umbral de HR por cuantiles bajan el error de horas mojadas en Duitama de 4,80 a 2,89 h/día y el sesgo de −4,25 a −0,62 h/día. La detección de días favorables sube de 50 % a 75 % (CALCULADO). Con 7 días no alcanza. Con 14 días se obtiene casi todo lo que dan 28 o 42. [Verificación técnica 2026-10-23, releyendo `resultados/calibracion_resumen.csv`: la calibración corrige sobre todo el **sesgo**. Juntando las 4 estaciones, el error medio de horas mojadas solo baja de 4,1 a 3,4 h/día y las falsas alarmas de días favorables siguen en ~0,42. En Cucunubá, Chía y Salitre el MAE casi no cambia. "Se arregla casi todo" vale para el sesgo de Duitama, no para el error hora a hora. Para Botrytis y antracnosis, que cambian de nivel con 3 h de mojado, hace falta sensor de hoja mojada.]
4. **La corrección de una finca no sirve para otra.** Si a Duitama le aplicamos el promedio de las correcciones de las otras estaciones, el sesgo empeora a −5,66 h/día (CALCULADO). El microclima es local. Por eso la calibración se hace finca por finca, y por eso el negocio necesita un **kit de calibración itinerante** en lugar de una estación permanente por finca.
5. **Bajo macrotúnel o invernadero el reanálisis no sirve sin sensor.** Bajo túnel, en arándano, la máxima sube 10 a 12 °C y la mínima 2 a 5 °C ([Retamal-Salgado et al. 2015](https://revistaschilenas.uchile.cl/handle/2250/56061)). El riego por aspersión también moja la hoja sin que ningún modelo lo vea. Esos casos exigen sensor permanente o el calendario de riego.
6. **Para vender hay que pagar los datos o alojarlos.** La API gratuita de Open-Meteo es solo para uso no comercial ([términos](https://open-meteo.com/en/terms)). Para cobrarle al productor necesitamos un plan comercial o un servidor propio. El servidor es AGPLv3 y los datos son CC BY 4.0 ([precios](https://open-meteo.com/en/pricing)).

---

## 1. Qué necesita la capa ambiental

Los modelos de riesgo del equipo (antracnosis: Wilson 1990 adaptado a arándano, no Miles 2013 [verificación técnica 2026-10-23]; Botrytis de Bulger 1987; roya) usan casi las mismas entradas: **duración del mojado foliar**, **temperatura durante el mojado**, **lluvia** (salpique y lavado de fungicida) y, para oídio, **horas húmedas sin agua libre**. El motor de clima entrega esas series por finca y por hora. El modelo de cada enfermedad se conecta encima a través de un **perfil de cultivo** (`perfiles/*.json`), así que cambiar de arándano a fresa o mora no toca la capa de clima.

| Entrada | Cómo se obtiene | Problema al escalar |
|---|---|---|
| T horaria | pronóstico o reanálisis, corregido por altura | la altura de la celda difiere de la de la finca en cientos de metros (sección 2.3) |
| Horas mojadas | proxy HR ≥ 90 % o sensor de hoja mojada | ningún producto global la mide; el umbral óptimo cambia por sitio |
| Lluvia | modelo o pluviómetro | la correlación diaria entre modelo y estación es baja (sección 2.4) |
| Mojado por aspersión | calendario de riego de la finca | ningún modelo lo ve; el robot recorre las camas delante del aspersor |
| Microclima bajo cubierta | sensor dentro del túnel | el reanálisis representa campo abierto |

---

## 2. Fuentes globales y locales

### 2.1 Comparación de fuentes

| Fuente | Resolución | Periodo | Retraso | Variables útiles | Acceso y licencia | Uso que proponemos |
|---|---|---|---|---|---|---|
| **Open-Meteo Forecast** (best_match: ICON, GFS e IFS como base global) | 9 a 25 km según el modelo (IFS); 2 a 11 km (ICON); 3 a 25 km (GFS) | `past_days` hasta 92; pronóstico hasta 15 a 16 días | IFS se actualiza cada 6 h; GFS cada hora | T, HR, Td, lluvia, prob. de lluvia, VPD, ET0, humedad de suelo; "Mean Leaf Wetness Probability" solo diaria | [docs](https://open-meteo.com/en/docs). API gratuita no comercial, 10.000 llamadas/día ([precios](https://open-meteo.com/en/pricing)) | **riesgo operativo diario** |
| **Open-Meteo Historical Forecast** | la del modelo (IFS 9 km; ICON 11 km; GFS 13 km) | desde 2021 o 2022 | — | iguales a las del pronóstico | [docs](https://open-meteo.com/en/docs/historical-forecast-api) | **calibrar** contra el mismo flujo que se usa en operación |
| **ECMWF IFS (archivo en Open-Meteo)** | 9 km, horario | 2017 a hoy | "sin retraso" | T, HR, Td, lluvia, VPD, suelo | [docs](https://open-meteo.com/en/docs/historical-weather-api) | en 2025 fue la misma serie que best_match y que el histórico de pronósticos (CALCULADO, sección 2.2) |
| **ERA5** | 0,25° (~25 km), horario | 1940 a hoy | 5 días | T, HR, Td, lluvia, VPD, suelo | vía Open-Meteo sin cuenta. En el CDS de Copernicus, CC-BY | climatología larga |
| **ERA5-Land** | 0,1° (~9 a 11 km), horario | 1950 a hoy | 5 días | T, HR, Td, VPD, suelo. La lluvia viene del forzamiento ERA5 y Open-Meteo no la devuelve | [CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview), CC-BY | **climatología del día 1** ("esta semana frente a lo normal del mes") |
| **NASA POWER** | ½° × ⅝° (~55 × 70 km) | MERRA-2 desde 1981; GEOS para lo reciente | MERRA-2 "a varios meses"; GEOS "a varios días" | T2M, RH2M, T2MDEW, PRECTOTCORR (horario) | [metodología](https://power.larc.nasa.gov/docs/methodology/), API pública | **solo de respaldo**: la celda es demasiado gruesa para montaña (sección 2.2) |
| **IDEAM (datos.gov.co)** | estación puntual; T y HR horarias, lluvia cada 10 min | según estación | actualización "Diaria"; último dato de Chía: 2026-10-22 23:00 UTC, consultado el 2026-10-23 | T, HR, lluvia | CC BY-SA 4.0; "control de calidad básico" OMM ([metadatos T](https://www.datos.gov.co/api/views/sbwg-7ju4.json), [HR](https://www.datos.gov.co/api/views/uext-mhny.json), [lluvia](https://www.datos.gov.co/api/views/s54a-sgyg.json)) | **validación y calibración regional en Colombia**; no sirve como fuente operativa única |
| **Estación propia** (p. ej. Metos) | la finca | desde que se instala | minutos | T, HR, **hoja mojada**, lluvia | Metos 5 200: 3.980 AUD; Metos 5 250: 4.630 AUD; modelos de enfermedad: 15 AUD por cultivo, estación y mes ([catálogo NSW DPIRD](https://www.agtech.dpird.nsw.gov.au/collections/vendor-metos-anz)) | **kit de calibración itinerante** y sensor permanente bajo cubierta |
| Redes de otros países: INIA Chile (agromet.inia.cl), INIFAP México (clima.inifap.gob.mx), SENAMHI Perú | estación | — | — | — | NO VERIFICADO ([INIA](https://www.portalfruticola.com/noticias/agrotecnia/descripcion-y-usos-de-la-red-de-agrometeorologia-inia), [INIFAP](https://www.redalyc.org/pdf/2631/263140688009.pdf); SENAMHI sin consultar) | conectores por país, en el mismo papel que IDEAM |

**Densidad de IDEAM.** En octubre de 2026 reportaron HR horaria en datos.gov.co **325 estaciones**. El catálogo tiene 5.655 estaciones activas, de las cuales 1.800 son automáticas con telemetría (1.480 + 320) (CALCULADO con consultas SoQL a [uext-mhny](https://www.datos.gov.co/resource/uext-mhny.json) y [hp9r-jxuu](https://www.datos.gov.co/resource/hp9r-jxuu.json)). Con 1.141.748 km² de superficie nacional (dato conocido, NO VERIFICADO en esta sesión), toca una estación con HR cada ~3.500 km², es decir, una separación media de ~59 km (CALCULADO). Para la mayoría de las fincas la estación más cercana está más lejos que la celda del modelo.

### 2.2 Validación contra 6 estaciones IDEAM (2025, horario)

**Método.** Comparamos con datos horarios de 2025 de las estaciones Guasca, U. de La Sabana (Chía), Duitama, Tunguavita (Paipa), Cucunubá y Salitre (Tausa). Cada serie de modelo se descargó en la coordenada de la estación según el catálogo IDEAM. Antes de comparar aplicamos el control de calidad de la sección 2.3. Script: `clima_global/scripts/validar_y_calibrar.py`.

Mediana entre estaciones, con el rango entre paréntesis (CALCULADO, `resultados/validacion_fuentes.csv`):

| Fuente | Sesgo T (°C) | MAE T (°C) | Sesgo HR (pts) | MAE HR (pts) | Sesgo horas mojadas (h/día) | MAE horas mojadas (h/día) |
|---|---|---|---|---|---|---|
| **IFS 9 km con corrección por altura** (= best_match = histórico de pronósticos) | +0,48 (−0,58 a +0,76) | 1,33 (1,15 a 1,58) | −2,9 (−10,4 a +1,1) | 7,3 (7,1 a 11,6) | +0,3 (−4,3 a +2,8) | 4,1 (3,0 a 4,8) |
| ERA5-Land 0,1° con corrección por altura | +0,09 (−0,33 a +1,24) | 1,25 (1,12 a 2,12) | −0,1 (−2,0 a +1,1) | 6,7 (6,1 a 9,3) | +1,7 (−1,7 a +2,9) | 3,6 (3,0 a 6,6) |
| ERA5 0,25° | +0,62 (−0,08 a +2,21) | 1,80 (1,40 a 3,15) | −1,3 (−3,3 a +1,7) | 7,0 (5,5 a 9,1) | −2,0 (−4,1 a +0,7) | 3,9 (2,9 a 5,4) |
| NASA POWER ½° | +0,31 (−0,34 a **+4,51**) | 1,82 (1,41 a 4,51) | **+3,8** (+2,9 a +7,2) | 8,3 (7,0 a 9,0) | **+3,6** (+1,4 a +5,6) | 4,7 (2,4 a 5,8) |

En las 4 estaciones con HR válida, el índice ilustrativo de "día favorable" (≥ 10 h mojadas con T de mojado entre 10 y 25 °C, SUPUESTO) marcó **373 días** con datos de estación. Con IFS marcó **301**, con ERA5-Land **480** y con NASA POWER **934**, 2,5 veces lo observado (CALCULADO).

**Efecto de la corrección por altura.** Open-Meteo baja la celda a la altura del DEM de 90 m salvo que se pida `elevation=nan` ([docs](https://open-meteo.com/en/docs/historical-weather-api)) (CALCULADO):

| Estación | Altura del catálogo (m) | DEM en la coordenada (m) | Celda IFS sin corregir (m) | Sesgo T IFS sin corrección (°C) | Sesgo T IFS con corrección (°C) | Sesgo T NASA POWER (celda de 2.476 a 2.516 m) |
|---|---|---|---|---|---|---|
| Duitama | 2.492 | 2.489 | 2.788 | −1,85 | **+0,76** | −0,21 |
| Guasca | 2.750 | 2.673 | 2.918 | −1,33 | **+0,56** | +0,72 |
| Cucunubá | 2.818 | 2.807 | 2.704 | +0,12 | −0,58 | +1,33 |
| Salitre (Tausa) | **2.637** | **3.284** | 3.200 | +0,54 | +0,54 | **+4,51** |
| Chía (U. Sabana) | 2.548 | 2.547 | 2.569 | +0,01 | +0,01 | −0,11 |

La corrección por altura es obligatoria en montaña. NASA POWER, que no la hace, falla por 4,5 °C en Salitre. En el caso de Salitre, el catálogo IDEAM dice 2.637 m pero el modelo a 3.284 m (altura del DEM) acierta con +0,54 °C. Lo más probable es que la altura del catálogo esté mal y no la coordenada. **Lección para el alta de fincas:** se toma la coordenada con GPS, se lee la altura del DEM y el sistema avisa si la altura declarada difiere más de 100 m. 100 m equivalen a ~0,65 °C con el gradiente estándar de 6,5 °C/km (SUPUESTO de gradiente).

### 2.3 Problemas de calidad que encontramos en los datos de estación

Cualquier finca que conecte su propio sensor va a traer los mismos problemas. El sistema tiene que detectarlos solo; lo hace la función `qc_sensor()` de `clima_global.py`.

| Problema | Dónde | Cómo se detecta | Qué pasa si no se detecta |
|---|---|---|---|
| `fechaobservacion` en **UTC** en las estaciones IDEAM y en **hora local** en la de la CAR (Salitre) | 5 de 6 estaciones | desfase que maximiza la correlación horaria de T con el modelo. La r pasa de 0,41–0,49 (sin desfase) a 0,74–0,79 (con 5 h) | sin corregir, el MAE de T con IFS era 3,6 a 4,6 °C en lugar de 1,2 a 1,6 °C (CALCULADO) |
| Filas duplicadas | Chía, Duitama, Cucunubá, Guasca (374 a 1.540 por estación) | agrupar por hora | se cuentan dos veces las horas mojadas |
| HR que nunca llega a saturación | Tunguavita (p99 = 86 %, máx. 91 %), Guasca (p99 = 93 %) | p99 de HR < 95 % (SUPUESTO de umbral) | la finca nunca tendría "hoja mojada" y no saldría ninguna alerta |
| Etiqueta errónea | en el JSON de HR 2025 el campo `descripcionsensor` dice "HUMEDAD DEL SUELO A 1 m Ó MAS", pero los valores son HR del aire (ciclo diario de 79 a 100 %) | revisión del ciclo diario | se descartaría una serie válida |
| Caída de la red | febrero de 2025: solo 92 a 93 h válidas en Chía, Duitama y Cucunubá | cobertura mensual | un modelo que dependa solo de IDEAM se queda ciego un mes |
| Altura del catálogo | Salitre (2.637 m frente a 3.284 m del DEM) | DEM frente a altura declarada | 4 °C de error si se fuerza la altura equivocada |

(CALCULADO, `resultados/qc_estaciones.csv`. Otro agente encontró por su cuenta el mismo desfase UTC en `clima/scripts/analisis_clima.py`.)

### 2.4 Lluvia: hace falta pluviómetro

En la estación Guasca usamos 127 días completos de 2025, con 259 mm en total (CALCULADO, `resultados/precip_guasca.txt`):

| Fuente | r diaria | Sesgo (mm/día) | Días con lluvia ≥ 1 mm (obs = 55) | Detección | Falsas alarmas |
|---|---|---|---|---|---|
| IFS (best_match) | 0,33 | +1,35 | 78 | 0,71 | 0,50 |
| ERA5 | 0,23 | +1,94 | 95 | 0,91 | 0,47 |
| NASA POWER | 0,20 | +3,32 | 100 | 0,93 | 0,49 |
| ERA5-Land | — | — | 0 (Open-Meteo no devuelve su lluvia) | — | — |

En montaña ningún modelo reproduce la lluvia día a día: la mitad de los días que marcan como lluviosos no lo fueron. Un pluviómetro de balancín es el sensor más barato y el que más mejora la regla de salpique de antracnosis y el aviso de lavado de fungicida.

### 2.5 Probabilidad de hoja mojada de Open-Meteo

La API devuelve `leaf_wetness_probability` horaria aunque la documentación solo la lista como variable diaria ([docs](https://open-meteo.com/en/docs)). La comparamos con el proxy HR ≥ 90 % de estación (CALCULADO, `resultados/lwp_vs_hr90.csv`):

| Estación | Detección con LWP ≥ 50 % | Falsas alarmas con LWP ≥ 50 % | Detección con LWP ≥ 30 % | Falsas alarmas con LWP ≥ 30 % |
|---|---|---|---|---|
| Chía | 0,65 | 0,54 | 0,89 | 0,54 |
| Duitama | 0,71 | 0,21 | 0,95 | 0,24 |
| Cucunubá | 0,30 | 0,46 | 0,78 | 0,46 |
| Salitre | 0,07 | 0,73 | 0,44 | 0,70 |

La usamos como variable auxiliar y no como entrada principal. Por otro lado, el proxy HR ≥ 90 % medido en estación acierta 87 a 92 % de las horas frente a sensores de mojado, y calibrar el umbral por sitio lleva el error a 1,2 a 1,9 h ([estudio en 4 sitios, Agric. For. Meteorol. 2008, ficha CNR](https://explore.cnr.it/resource/item/58890)). Eso sostiene la calibración de umbral por finca de la sección 4.

---

## 3. ¿Cuándo basta el reanálisis y cuándo hace falta sensor en la finca?

| Situación de la finca | Qué basta | Por qué | Confianza que muestra la app |
|---|---|---|---|
| Campo abierto, día 1, sin sensor | pronóstico IFS/best_match + corrección por altura con DEM + climatología ERA5-Land | T con MAE de ~1,2 a 1,6 °C; el mojado tiene sesgo desconocido de hasta ±4 h/día | **baja**: umbrales conservadores; se pide calibrar |
| Campo abierto calibrado (≥ 14 días de kit) | pronóstico + corrección de la finca | el sesgo de mojado baja a menos de 1 h/día en 3 de 4 estaciones (sección 4) | **media** |
| Ladera, cañón, cerca de cuerpos de agua, o altura declarada que difiere > 100 m del DEM | calibración obligatoria antes de alertar | la altura y el relieve dominan el sesgo (Duitama, Salitre) | baja hasta calibrar |
| **Macrotúnel / invernadero** | **sensor permanente dentro** (T, HR y hoja mojada) | Tmax +10 a 12 °C y Tmin +2 a 5 °C bajo túnel ([Retamal-Salgado 2015](https://revistaschilenas.uchile.cl/handle/2250/56061)); no llueve dentro; el mojado viene de condensación y riego | **muy baja** sin sensor; el sistema no emite alerta "alta" solo con reanálisis |
| Riego por aspersión | calendario de riego (integración o carga manual) + sensor de mojado | el aspersor moja sin que lo vea ningún modelo | se marca "mojado por riego" |
| Modelo que exige duración exacta de mojado (Botrytis, antracnosis) | sensor de hoja mojada al menos durante la calibración | el proxy HR tiene error propio de 1 a 2 h aun calibrado ([CNR](https://explore.cnr.it/resource/item/58890)) | — |
| Zona con estación oficial a pocos km y en la misma altura | puede reemplazar el kit para calibrar T (no el mojado) | la estación no está dentro del cultivo | media para T |

---

## 4. Calibración por finca: pocas semanas de sensor y corrección del pronóstico

### 4.1 El esquema

1. **Kit itinerante** (de la empresa que vende el servicio): sensor de T y HR ventilado a la altura del dosel, sensor de hoja mojada, pluviómetro y datalogger con conexión celular o LoRa. Se instala de 2 a 4 semanas y se mueve a la siguiente finca.
2. **QC automático** (`qc_sensor`): detección de zona horaria (desfase de −12 a +12 h contra el modelo), duplicados, rangos, valores congelados y HR truncada.
3. **Ajuste, 49 parámetros por finca** (`ajustar` + umbral):
   - ΔT por hora del día (24 valores);
   - Δ punto de rocío por hora del día (24 valores), con la HR recalculada por Magnus;
   - **umbral de HR equivalente**: el umbral del modelo que reproduce la fracción de horas mojadas medida (mapeo por cuantiles).
4. **Validación** con el último 30 % del periodo. La corrección se acepta solo si mejora.
5. **Vigencia**: recalibrar por temporada o mantener un sensor barato permanente. En Duitama el umbral equivalente varió de 63 a 91 % según el mes de entrenamiento (CALCULADO), así que una sola calibración no sirve todo el año. También hay que recalibrar si cambia la cubierta o la versión del modelo (SUPUESTO: cada 6 meses).

Calibramos contra el **histórico de pronósticos** y no contra ERA5, porque en operación el sistema ve el pronóstico. ERA5 tiene 5 días de retraso y no sirve para dar alertas.

### 4.2 Experimento: 4 estaciones con HR válida, ventanas de entrenamiento al inicio de cada mes de 2025, prueba en el resto del año

Usamos el flujo operativo (IFS/best_match). Cada valor es la mediana entre ventanas (CALCULADO, `resultados/calibracion_por_estacion.csv`):

| Estación | Método | MAE T (°C) | Sesgo HR (pts) | MAE horas mojadas (h/día) | Sesgo horas mojadas (h/día) | Detección de días favorables | Falsas alarmas |
|---|---|---|---|---|---|---|---|
| **Duitama** | sin corrección | 1,58 | −10,4 | 4,80 | −4,25 | 0,50 | 0,25 |
| | promedio de las otras 5 estaciones | 1,74 | −9,4 | 6,02 | **−5,66** | 0,36 | 0,17 |
| | sensor 7 días | 1,81 | −7,8 | 3,88 | −3,05 | 0,65 | 0,26 |
| | **sensor 14 días** | 1,64 | −1,2 | **2,89** | **−0,62** | **0,75** | 0,27 |
| | sensor 28 días | 1,64 | −1,1 | 3,09 | −0,36 | 0,71 | 0,25 |
| **Cucunubá** | sin corrección | 1,22 | −3,4 | 3,93 | −0,73 | 0,17 | 0,47 |
| | sensor 14 días | 1,09 | −2,9 | 3,87 | −0,36 | 0,53 | 0,45 |
| **Chía** | sin corrección | 1,16 | −2,4 | 2,98 | +1,40 | 0,88 | 0,42 |
| | sensor 14 días | 1,14 | −2,4 | 2,99 | +1,41 | 0,92 | 0,44 |
| | sensor 28 días | 1,14 | −3,4 | 2,99 | +0,66 | 0,86 | 0,39 |
| **Salitre** | sin corrección | 1,15 | +1,1 | 4,35 | +2,78 | n/d (ningún día favorable: T de mojado < 10 °C) | n/d |
| | sensor 14 días | 1,02 | −4,0 | 4,20 | +0,24 | n/d | n/d |

Lo que muestra el experimento:

- **El beneficio depende de cuánto sesgo tenga la finca, y ese sesgo no se conoce sin medir.** En Duitama la calibración casi elimina el sesgo de mojado. En Chía el modelo ya estaba bien y la calibración no cambia nada. Eso es lo que queremos: si no hay sesgo, no se corrige.
- **El promedio de correcciones de estaciones vecinas empeora las cosas** (Duitama −5,66 h/día). La calibración no se puede regionalizar con 6 estaciones. Con cientos de fincas calibradas podría aprenderse una corrección en función de la altura, la pendiente y el sistema de cultivo. Es una hipótesis que hoy no tenemos cómo probar.
- **Con 14 días se obtiene casi todo.** Con 7 días queda sesgo (−3,05 h/día en Duitama). Con 28 o 42 días mejora poco más. Recomendamos **14 días como mínimo y 28 días como estándar del kit**.
- La T casi no cambia, porque la corrección por altura ya trabaja bien. **Lo que la calibración arregla es la humedad y el mojado.**

Prueba de punta a punta: `clima_global.py calibrar --ideam 2120500135 ...` toma 28 días de octubre de 2025 de la estación de Chía como si fuera el sensor de la finca. Detecta sola el desfase UTC de 5 h (r = 0,89) y guarda `resultados/calibracion_ideam_2120500135.json`. En el 30 % de validación de ese caso, el MAE de HR pasa de 6,63 a 6,22 pts y el sesgo de mojado de +1,22 a +1,67 h/día. Es el caso de "modelo ya bueno" y la corrección no ayuda; la regla de aceptación del paso 4 la descartaría (CALCULADO).

---

## 5. Arranque el día 1: lat/lon + perfil de cultivo

```
ALTA DE FINCA (5 min, desde el celular)
  lat/lon por GPS · cultivo · sistema (campo/macrotúnel/invernadero) · altura declarada (opcional)
  · tipo de riego y horario (opcional)
        │
        ▼
GEOSERVICIO (1 llamada por lote de hasta 100 fincas)
  DEM GLO-90 → altura; aviso si difiere > 100 m · zona horaria automática (timezone=auto)
        │
        ▼
INGESTA (cada 6 h, alineada con IFS; 1 petición por lote de fincas, coordenadas separadas por coma)
  pronóstico best_match: 7 días pasados + 7 de pronóstico, solo las variables del perfil
  una sola vez por finca: climatología ERA5-Land 2016-2025 (horas mojadas normales por mes)
        │
        ▼
CORRECCIÓN DE LA FINCA (si existe calibración vigente; si no, pasa sin cambios)
        │
        ▼
MOTOR DE RIESGO (perfil de cultivo JSON: enfermedades, tipo de regla o modelo, umbrales)
  → por día: horas mojadas, T de mojado, lluvia, nivel bajo/medio/alto por enfermedad
        │
        ▼
SALIDA: riesgo por enfermedad + CONFIANZA (muy baja / baja / media / alta) + avisos
  → decide qué bloques recorre primero el robot y qué hallazgos visuales se priorizan
```

**Niveles de confianza.** El vendedor puede ofrecer el producto desde el primer día sin prometer de más:

| Nivel | Condición | Qué se permite |
|---|---|---|
| muy baja | bajo cubierta sin sensor | solo "vigilar"; nunca alerta alta automática |
| baja | campo abierto, sin calibrar | alertas con umbral conservador; la visión del robot confirma |
| media | calibrado ≥ 14 días | alertas normales |
| alta | sensor en vivo en la finca (T, HR, mojado) | alertas en tiempo real; el modelo de infección puede usar duración de mojado medida |

**Demo multi-país.** `clima_global.py lote perfiles/fincas_demo.json` corre 7 puntos de referencia (Sotaquirá, Tausa, Guasca y Chía en Colombia; Virú en Perú; Los Ángeles en Chile; Zapotlán en México) con perfiles de arándano, fresa y mora y sistemas de campo abierto y macrotúnel. Usa una petición de pronóstico y una de elevación y tarda 2,2 s. Resolvió solas las zonas horarias America/Bogota, America/Lima, America/Santiago y America/Mexico_City y alturas de 73 a 2.997 m (CALCULADO, `resultados/lote_ultimo.json`). Las coordenadas fuera de Colombia son aproximadas (SUPUESTO) y no corresponden a fincas reales.

**Otros frutales.** Agregar un cultivo es escribir un JSON. `perfiles/fresa.json` y `perfiles/mora.json` reutilizan las mismas entradas (horas mojadas, T de mojado, horas húmedas sin lluvia) con otros patógenos: oídio por *Podosphaera aphanis* en fresa y mildeo velloso por *Peronospora sparsa* en mora. **Todos los umbrales de los perfiles son ilustrativos (SUPUESTO).** El equipo de riesgo los reemplaza por sus modelos.

---

## 6. Qué cambia al venderlo a muchos productores

### 6.1 Licencia y costo de datos

| Opción | Condición | Escala | Fuente |
|---|---|---|---|
| API gratuita de Open-Meteo | **solo no comercial**; un producto con suscripción es uso comercial | 10.000 llamadas/día | [términos](https://open-meteo.com/en/terms), [precios](https://open-meteo.com/en/pricing) |
| Plan Standard / Professional / Enterprise | licencia comercial, clave en `customer-api.open-meteo.com` | 1 M / 5 M / > 50 M llamadas por mes; **la página no muestra los precios** (NO VERIFICADO) | [precios](https://open-meteo.com/en/pricing) |
| Servidor propio | código AGPLv3; datos CC BY 4.0 con atribución obligatoria | Open-Meteo lo recomienda para cargas "en los miles de millones" | [precios](https://open-meteo.com/en/pricing) |
| IDEAM | CC BY-SA 4.0 (la obra derivada debe compartirse igual) | gratis | [metadatos](https://www.datos.gov.co/api/views/uext-mhny.json) |

**Llamadas por mes.** Open-Meteo cuenta una llamada por ubicación con ≤ 10 variables y ≤ 2 semanas. Más variables o más días cuentan fracciones adicionales ([precios](https://open-meteo.com/en/pricing)). No está documentado si una petición con varias coordenadas cuenta como una llamada por ubicación; suponemos que sí (NO VERIFICADO). Con 4 refrescos al día de 14 días × 5 variables:

| Fincas | Llamadas/mes (= fincas × 4 × 30) | Plan que alcanza | Única vez: climatología de 10 años (~261 llamadas/finca) |
|---|---|---|---|
| 100 | 12.000 | Standard | 26.100 |
| 1.000 | 120.000 | Standard | 261.000 |
| 10.000 | 1.200.000 | Professional | 2,6 M (conviene servidor propio o menos años) |

(CALCULADO: 10 años ÷ 2 semanas ≈ 261.)

El cliente actual refresca cada hora (24 al día). Para IFS eso es 6 veces más llamadas de las necesarias, porque el modelo se actualiza cada 6 h.

### 6.2 Kit itinerante frente a estación por finca

| Concepto | Estación permanente por finca | Kit itinerante + pronóstico corregido |
|---|---|---|
| Equipo | 3.980 a 4.630 AUD por finca ([NSW DPIRD](https://www.agtech.dpird.nsw.gov.au/collections/vendor-metos-anz)) | el mismo equipo repartido entre ~10 fincas/año (SUPUESTO: 4 semanas instalado + 1 de traslado) |
| Modelos de enfermedad | 15 AUD por cultivo, estación y mes = 180 AUD/año por cultivo (CALCULADO, misma fuente) | motor propio |
| Costo por finca | ~4.600 AUD + 180 AUD/año | ~4.630 AUD ÷ 30 fincas (10/año × 3 años de vida, SUPUESTO) ≈ **155 AUD por finca** (CALCULADO), más el traslado |
| Por ha (finca de 20 ha) | ~240 AUD/ha el primer año (CALCULADO) | ~7,7 AUD/ha una sola vez (CALCULADO) |
| Bajo cubierta | sí sirve | no basta: hace falta un sensor permanente por bloque bajo cubierta |

Frente al ROI del híbrido (~430 USD/ha/año, dato del equipo), la capa ambiental calibrada cuesta poco. **Lo que hace escalable el modelo es que la estación permanente deja de ser obligatoria.** La red fija del híbrido se reduce a lo que de verdad lo necesita: bloques bajo cubierta y zonas de microclima propio. Una hipótesis que no hemos probado: el mástil del D1 lleva T y HR a la altura del dosel y mide la variación cama por cama mientras recorre; no reemplaza la duración nocturna del mojado si el robot no opera de noche.

**Competencia.** Pessl/Metos ya vende estación + modelos de enfermedad por suscripción. Nuestra diferencia es que no exigimos estación el día 1 y que el robot confirma visualmente cama por cama. Si la finca ya tiene estación, se usa como sensor de calibración. La integración por API con FieldClimate está NO VERIFICADA.

---

## 7. Revisión de `clima/clima_client.py`: qué cambiar para que sea agnóstico a ubicación y multi-finca

Revisión de solo lectura del archivo de otro agente. `clima_global/clima_global.py` es un prototipo que ya aplica la mayoría de estos cambios, sin tocar el original.

| # | Hoy (línea aprox.) | Problema al escalar | Cambio propuesto | Prioridad |
|---|---|---|---|---|
| 1 | `PUNTOS` fijo con 4 municipios colombianos y área de arándano (l. 68-78) | lugares y datos de negocio dentro del cliente | registro de fincas (BD o JSON): `id, lat, lon, elev_m, cultivo, sistema, riego, calibración`; `_punto()` recibe un objeto `Finca` | alta |
| 2 | `TZ = "America/Bogota"` (l. 52) y `_a_df` "UTC-5, sin DST" (l. 229) | falla en Chile y México (tienen horario de verano) | `timezone=auto` por finca, o UTC interno y `utc_offset_seconds` en la salida | alta |
| 3 | URL fija `api.open-meteo.com` sin `apikey` | la API gratis no permite uso comercial | URL base y `OM_APIKEY` por variable de entorno, con el prefijo `customer-` | alta (para vender) |
| 4 | el sobre de caché guarda `"params": params` en disco (l. 156) | si se agrega `apikey` a `params`, la clave queda escrita en la caché | mantener la clave fuera de `params` y de la clave de caché; agregarla solo a la URL de salida | alta |
| 5 | no hay QC ni calibración | los sensores de finca llegan con UTC, duplicados o HR truncada (sección 2.3) | `qc_sensor()` + `aplicar_calibracion(finca)` después de descargar | alta |
| 6 | una petición por punto | N fincas → N peticiones | coordenadas separadas por coma (la respuesta es una lista), lotes de ≤ 50 | media |
| 7 | `TTL_PRONOSTICO_S = 3600` (l. 80) | 24 refrescos al día; IFS cambia cada 6 h | TTL de 3 a 6 h alineado con las corridas | media |
| 8 | histórico con `ttl_s=None` (l. 219) | los últimos días del archivo se revisan (ERA5 tiene 5 días de retraso; los días recientes vienen de IFS) y quedarían congelados | TTL de 7 días si `fin` cae en los últimos 10 días; nunca vence si es más antiguo | media |
| 9 | `models` vacío por defecto | best_match puede cambiar de modelo sin aviso | fijar `models=best_match` (o `ecmwf_ifs`) y guardar el modelo, la celda y la `elevation` que devuelve la API | media |
| 10 | `VARS_HORARIAS` fijas, con `leaf_wetness_probability` | variable no documentada y que concuerda poco (sección 2.5) | variables tomadas del perfil de cultivo; LWP solo como auxiliar | media |
| 11 | `elevacion` opcional solo en el histórico | el pronóstico usa la altura del DEM y no la de la finca | pasar siempre la altura verificada de la finca, también al pronóstico, y avisar si difiere del DEM | media |
| 12 | caché en disco local por proceso (`clima/cache/json`) | varios servidores o workers no la comparten | caché compartida (objeto o Redis) con clave (modelo, celda, altura) | baja |
| 13 | reintentos 2-4-6 s; 429 sin trato especial | límites por minuto con muchas fincas | backoff exponencial y respetar `Retry-After` en 429 | baja |
| 14 | `cache_ultimo_pronostico` ignora los parámetros | sin red podría usarse un pronóstico viejo sin aviso | exponer la edad del dato y bajar la confianza de la alerta | baja |

---

## 8. Límites y supuestos

- La validación usa **6 estaciones en una sola región**, todas entre 2.490 y 3.300 m, y **un solo año (2025)**. Hay HR válida en 4. No probamos tierras bajas, costa, Perú, Chile ni México. Allí la demo solo comprueba que el código corre.
- **El "mojado" de referencia es HR ≥ 90 % medida en estación a 2 m, no un sensor de hoja mojada en el dosel.** El error real frente a la hoja es mayor (sección 2.5).
- El índice de "día favorable" y todos los umbrales de los perfiles son **ilustrativos (SUPUESTO)**. Sirven para comparar fuentes, no para predecir enfermedad.
- Calibrar con la estación y probar en esa misma estación es optimista: un kit en la finca tendría su propio error de instalación.
- Los precios de Metos están en AUD, vienen de un catálogo australiano y no sabemos de qué fecha son. Los precios de los planes comerciales de Open-Meteo no están publicados en la página.
- La calibración de Chía de 2025 se aplica en la demo a un punto cercano en 2026. Solo ilustra el flujo; en un caso real se recalibra.
- La API gratuita de Open-Meteo se usó con fines de investigación y demo (no comercial).

---

## 9. Archivos y cómo reproducir

Todo está en `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global/`:

| Archivo | Qué es |
|---|---|
| `clima_global.py` | prototipo: `dia1`, `lote`, `calibrar` (QC, corrección por altura, lotes, calibración, perfiles, niveles de confianza) |
| `perfiles/arandano.json`, `fresa.json`, `mora.json` | perfiles de cultivo (umbrales SUPUESTO) |
| `perfiles/fincas_demo.json` | 7 puntos de referencia de 4 países |
| `scripts/descargar_validacion.py` | descarga Open-Meteo (5 modelos), NASA POWER, catálogo IDEAM |
| `scripts/validar_y_calibrar.py` | QC, validación y experimento de calibración |
| `resultados/validacion_fuentes.csv` | métricas por estación y fuente |
| `resultados/qc_estaciones.csv` | desfase horario, HR descartada, duplicados |
| `resultados/calibracion_detalle.csv`, `calibracion_por_estacion.csv`, `calibracion_resumen.csv` | experimento de calibración |
| `resultados/lwp_vs_hr90.csv`, `precip_guasca.txt` | hoja mojada de Open-Meteo y lluvia |
| `resultados/calibracion_ideam_2120500135.json`, `lote_ultimo.json`, `dia1_ultima.json` | salidas del prototipo |
| `cache/` | respuestas crudas de las API (2025) |

```bash
PY=/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python
cd /Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global
$PY -I scripts/descargar_validacion.py && PASADA=2 $PY -I scripts/descargar_validacion.py
$PY -I -W ignore scripts/validar_y_calibrar.py
$PY -I -W ignore clima_global.py dia1 --lat 5.76483 --lon -73.24758 --cultivo arandano --climatologia
$PY -I -W ignore clima_global.py lote perfiles/fincas_demo.json
$PY -I -W ignore clima_global.py calibrar --ideam 2120500135 --lat 4.85414 --lon -74.03269 --desde 2025-10-01 --dias 28
```

Los datos de temperatura, HR y lluvia de IDEAM se leen de `datos/raw/ideam_datosgov_2025/`, que descargó otro agente y que no modificamos.

## 10. Fuentes consultadas

- Open-Meteo: [Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) · [Forecast API](https://open-meteo.com/en/docs) · [Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) · [Elevation API](https://open-meteo.com/en/docs/elevation-api) · [Precios](https://open-meteo.com/en/pricing) · [Términos](https://open-meteo.com/en/terms)
- Copernicus: [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview)
- NASA POWER: [Metodología](https://power.larc.nasa.gov/docs/methodology/)
- IDEAM en datos.gov.co: [Temperatura](https://www.datos.gov.co/api/views/sbwg-7ju4.json) · [Humedad](https://www.datos.gov.co/api/views/uext-mhny.json) · [Precipitación](https://www.datos.gov.co/api/views/s54a-sgyg.json) · [Catálogo de estaciones](https://www.datos.gov.co/resource/hp9r-jxuu.json)
- Metos ANZ: [catálogo NSW DPIRD AgTech](https://www.agtech.dpird.nsw.gov.au/collections/vendor-metos-anz)
- Microclima bajo túnel: [Retamal-Salgado et al., Chilean J. Agric. Res. 2015](https://revistaschilenas.uchile.cl/handle/2250/56061)
- HR como estimador de mojado: [Agric. For. Meteorol. 2008, ficha CNR](https://explore.cnr.it/resource/item/58890)
- NO VERIFICADO (solo resumen de búsqueda): [red INIA Chile](https://www.portalfruticola.com/noticias/agrotecnia/descripcion-y-usos-de-la-red-de-agrometeorologia-inia) · [red INIFAP México](https://www.redalyc.org/pdf/2631/263140688009.pdf) · [Bulger et al. 1987, resumen APS](https://apsnet.org/publications/phytopathology/backissues/Documents/1987Abstracts/Phyto77_1225.htm) (la ecuación no se pudo abrir: HTTP 403)
