# Reporte: backtest-riesgo

Fecha: 2026-10-23. Rol: correr los modelos de riesgo (`riesgo/risk.py`) sobre el clima horario real de 2025 en los 4 puntos, medir la sensibilidad al umbral de hoja mojada, revisar la fenología, calcular el riesgo de hoy para el tablero y hacer una prueba de cordura.

Convenciones: **SUPUESTO** = valor elegido por el equipo sin fuente directa. Todas las cifras de este reporte salen de los CSV de `resultados/backtest/`. Ninguna cifra es un acierto frente a la enfermedad: **no hay datos de incidencia de campo**.

## Resumen

- **Reproducible:** el backtest lee directamente `clima/cache/historico_2025_<punto>.csv` y coincide en 36 de 36 conteos con lo que ya había publicado el equipo de riesgo (`reproducibilidad_vs_riesgo_salidas.csv`).
- **Carga de alertas (criterio central, HR ≥ 90 % o lluvia ≥ 0,5 mm/h):**
  - Días en alto por año y punto: antracnosis 3–6, Botrytis 10–18, roya 0–6.
  - Episodios de alerta alta (rachas de días seguidos en alto, cualquier enfermedad): **5–10 por año y punto**.
  - Botrytis domina: todos los días en alto de antracnosis y de roya caen en días en que Botrytis ya está en alto.
- **Estacionalidad:** el 67 % de los días-enfermedad en alto (62 de 93) cae entre febrero y mayo, con repuntes en agosto (8) y octubre (11). Septiembre, noviembre y diciembre tienen 0.
- **El umbral de humedad es la perilla que más pesa.** Al bajar de HR 90 % a 85 %, los días en alto se multiplican por 2,2 (Botrytis), 2,8 (antracnosis) y 3,0 (roya). Al subir a 95 % caen entre 69 y 81 %.
- **Fenología:** el reporte de ciencia indica producción continua, sin temporada fija de floración. En ese escenario (SUPUESTO) el riesgo de la finca es igual al riesgo sin fenología. Encontré un problema de diseño: con los multiplicadores actuales, **Botrytis no puede llegar nunca a "alto" en fruto verde ni en maduración**.
- **Riesgo de hoy (23-oct-2026):** nivel de alerta **alto en los 4 puntos**. En Tausa solo sale alto con el criterio de alerta (HR ≥ 85 %); con el central queda bajo.
- **Prueba de cordura:**
  - Casos sintéticos: 15 de 15 PASAN, más 3 informativos.
  - Semanas secas: en 39 de las 40 semanas más secas (10 por punto) **no hubo ningún día en alto**. PASA.
  - Semanas lluviosas: solo el 30–60 % de las 10 más lluviosas de cada punto tiene algún día en alto con el criterio central. **NO PASA** el criterio que fijé antes de correr (≥ 80 %). Con "medio o alto" sube a 60–100 %.
- **Hallazgo nuevo (extra): casos no detectados por error del clima de entrada.** Comparé el riesgo calculado con el clima de Open-Meteo contra el calculado con datos medidos en 3 estaciones del IDEAM:
  - En la U. de La Sabana (Chía), el sistema ve **34 de 39** días-enfermedad en alto que vería la estación.
  - En Cucunubá (Tausa) ve **2 de 34**.
  - Agregado de las 3 estaciones: **48 %**.
  - Esto argumenta a favor de la red fija de sensores de la propuesta.
- **Re-ejecución tras la verificación (23-oct-2026, sección 7):**
  - Volví a correr todo con el `risk.py` corregido por el verificador (`riesgo_ventana_72h`). Los 16 CSV salen idénticos byte a byte, `riesgo_hoy.json` también (salvo `generado`) y las pruebas pasan: 136 de 136.
  - Añadí `robustez_backtest.py`. Con un error de ±1 °C en la temperatura, los días en alto (suma de 4 puntos) van de 7 a 27 en antracnosis, de 45 a 70 en Botrytis y de 5 a 38 en roya. Con la Tmin de roya en 12 °C o más, la roya queda en **0 días**. Si Botrytis alertara desde 0,50, el umbral validado, pasaría de 61 a 89 días.
  - Conclusión: los conteos son un **orden de magnitud con rango**, no cifras exactas. La roya se presenta como **regla de vigilancia**, sin conteo de días.

## Frases para el pitch

1. "Con el clima real de 2025, el sistema habría emitido entre 5 y 10 alertas altas por finca al año con el criterio central, y entre 11 y 19 con el criterio de alerta que usa el tablero; dos de cada tres entre febrero y mayo. Es una carga que un agrónomo puede atender." [verificacion-riesgo-clima, 2.ª pasada: el tablero muestra `nivel_alerta` = máx(HR 90, HR 85), así que su carga real de alertas es la de HR 85 (11–19 episodios, `dias_riesgo_anual_2025.csv`), no la de HR 90]
2. "No alarma por todo: en 39 de las 40 semanas más secas de los cuatro puntos no marcó ni un día de riesgo alto."
3. "La perilla que más pesa es el umbral de hoja mojada. Bajar la humedad de 90 a 85 % duplica o triplica las alertas. Por eso lo calibramos con estaciones del IDEAM y elegimos el criterio orientado a no perder casos."
4. "Medimos nuestros propios casos no detectados. Frente al riesgo que calcularía una estación del IDEAM, el clima de modelo ve 34 de 39 días de alto riesgo en Chía, pero solo 2 de 34 en Cucunubá, cerca de Tausa: el 48 % en total. Por eso la propuesta lleva sensores fijos en la finca: cierran ese hueco."
5. "Hoy, 23 de octubre, el pronóstico pone en alerta alta a Sotaquirá, Guasca y Chía por Botrytis, y a Tausa con el criterio de alerta. El robot empieza por esas camas y el sistema sugiere aplazar el aspersor."

Advertencia para quien presente: no digas "sensibilidad del 90 %". Ese número es por **hora** de hoja mojada; por **día de alerta** frente a una estación es del 28–48 %, y frente a la enfermedad real no está medido. Si muestras días de roya, di que dependen de un parámetro SUPUESTO.

## Qué hice

1. Escribí `resultados/backtest/backtest_riesgo.py`, que solo usa `riesgo/risk.py`, pandas y archivos locales, sin red:
   - Clima: Open-Meteo horario 2025 (`best_match`), 8.760 h por punto, desde `clima/cache/`.
   - Tres criterios de hoja mojada: HR ≥ 85/90/95 %, siempre "o lluvia ≥ 0,5 mm/h".
   - Conteo de días bajo/medio/alto por mes, punto y enfermedad (antracnosis, Botrytis y roya). El oídio queda fuera: es visual y el índice de vid da 0 días.
   - Escenarios de fenología, riesgo de hoy con el pronóstico en caché, prueba de cordura y comparación con estaciones del IDEAM.
2. Escribí `resultados/backtest/graficas_backtest.py`: 11 PNG en 16:9 para diapositiva. Usan la paleta de referencia del skill de visualización, validada con su script: rampa ordinal azul PASS y 3 categóricos PASS. Rojo y amarillo de estado = alto y medio, siempre con leyenda. Atribución "Weather data by Open-Meteo.com" en cada gráfica, como pide la licencia CC BY 4.0 (citada en `reportes/clima-open-meteo.md`).
3. Volví a correr las 135 pruebas de `riesgo/tests`: siguen pasando. No modifiqué `risk.py`.

Para reproducir:

```bash
PY=/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python
D=/Users/santiagosantafe/Downloads/SabanaHack/datos
$PY -I $D/resultados/backtest/backtest_riesgo.py [--fecha 2026-10-23]   # CSV + riesgo_hoy.json (~3 s)
$PY -I $D/resultados/backtest/graficas_backtest.py                      # PNG en graficas/
$PY -I $D/resultados/backtest/robustez_backtest.py                       # robustez + g6 (~5 s)
```

## Archivos producidos

Todos en `/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/backtest/`:

| Archivo | Contenido |
|---|---|
| `backtest_riesgo.py`, `graficas_backtest.py` | Scripts |
| `dias_riesgo_mensual_2025.csv` | Días bajo/medio/alto, episodios en alto e índice máximo por punto × criterio × mes × enfermedad, más lluvia y horas mojadas del mes |
| `dias_riesgo_anual_2025.csv` | Lo mismo por año, incluida la fila `cualquiera_de_las_3` (carga de alertas) |
| `sensibilidad_umbral_hr.csv` | Días en alto, días medio o alto y episodios con HR 85/90/95 %, con el cambio frente a 90 % |
| `fenologia_escenarios.csv` | Sin fenología, producción continua y una sola etapa todo el año (4 etapas) |
| `riesgo_hoy.json` | **Para el tablero**: nivel de alerta por punto, mensaje, acción sugerida, detalle por enfermedad y próximos 7 días |
| `cordura_casos_sinteticos.csv` | 6 casos construidos × 3 criterios, con resultado esperado y obtenido |
| `cordura_semanas_secas_vs_lluviosas.csv`, `cordura_semanal_2025.csv`, `cordura_temporadas.csv` | Prueba de cordura con datos reales |
| `diario_<punto>_HR90.csv` | Serie diaria: lluvia de Open-Meteo y del IDEAM, índices y clases |
| `concordancia_estacion_vs_openmeteo.csv`, `concordancia_estacion_agregado.csv`, `concordancia_estacion_resumen.csv` | Riesgo con estación IDEAM frente a riesgo con Open-Meteo |
| `reproducibilidad_vs_riesgo_salidas.csv` | 36 de 36 coincidencias con `riesgo/salidas/` |
| `robustez_backtest.py`, `robustez_dias_alto_2025.csv` | Días en alto y medio o alto con T ± 1 °C, Botrytis con alerta desde 0,50 y roya con Tmin de 10, 12 y 15 °C (sección 7) |

Gráficas en `graficas/`. Las tres primeras son las recomendadas para diapositiva:

- `g1_heatmap_dias_alto_mensual_2025.png`: días en alto por mes, punto y enfermedad (**diapositiva principal**).
- `g3_sensibilidad_umbral_hr.png`: sensibilidad al umbral de HR.
- `g5_concordancia_estacion_vs_openmeteo.png`: casos no detectados frente a estación.
- `g2_mensual_medio_alto_<punto>.png` (4) y `g2_mensual_medio_alto_todos.png`: días medio y alto por mes.
- `g4_cordura_serie_{chia,tausa,sotaquira}.png`: lluvia diaria frente a la clase de riesgo.
- `g6_robustez_temperatura.png`: días en alto con T − 1 °C, publicado y T + 1 °C (recomendada para la diapositiva de evidencia, junto a g3).

## Resultados

### 1. Días de riesgo por mes (criterio central HR ≥ 90 % o lluvia ≥ 0,5 mm/h)

Días en **alto** por mes, sumando los 4 puntos y las 3 enfermedades (`dias_riesgo_mensual_2025.csv`):

| Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | Año |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 14 | 13 | 20 | 15 | 8 | 2 | 8 | 0 | 11 | 0 | 0 | 93 |

Por año y punto (alto / medio):

| Punto | Antracnosis | Botrytis | Roya | Días con alguna en alto | Episodios en alto |
|---|---|---|---|---|---|
| Sotaquirá (182 ha) | 3 / 38 | 18 / 6 | 4 / 17 | 18 | 10 |
| Tausa (121 ha) | 3 / 20 | 17 / 6 | 0 / 2 | 17 | 10 |
| Guasca (57 ha) | 4 / 17 | 10 / 5 | 6 / 13 | 10 | 5 |
| Chía (demo) | 6 / 36 | 16 / 11 | 6 / 20 | 16 | 10 |

- Botrytis concentra el riesgo alto. La antracnosis se queda casi siempre en "medio" por el frío: la temperatura mediana durante la mojadura es de 8,6 a 10,6 °C (`reportes/modelos-riesgo.md`).
- Abril es el pico en Tausa: 6 días de Botrytis en alto.
- Noviembre es lluvioso según el reporte de ciencia, pero no tiene días en alto en ningún punto.

### 2. Sensibilidad al umbral de hoja mojada

Días en alto por año, sumando los 4 puntos (`sensibilidad_umbral_hr.csv`):

| Enfermedad | HR ≥ 85 % | HR ≥ 90 % (central) | HR ≥ 95 % | 85 frente a 90 | 95 frente a 90 |
|---|---|---|---|---|---|
| Antracnosis | 45 | 16 | 3 | ×2,8 | −81 % |
| Botrytis | 133 | 61 | 19 | ×2,2 | −69 % |
| Roya | 48 | 16 | 4 | ×3,0 | −75 % |

- **Por punto:**
  - Botrytis: 22–45 días con HR 85 % frente a 10–18 con HR 90 %.
  - Episodios en alto (cualquier enfermedad): 11–19 por año con 85 % frente a 5–10 con 90 %.
- **Lectura:** el resultado depende más del umbral de hoja mojada que de la ecuación de cada enfermedad. Por eso el equipo de clima calibró el umbral contra estaciones del IDEAM: con 85 %, la sensibilidad por hora es de ~0,9 en 3 de 4 estaciones (`reportes/clima-open-meteo.md`).
- **Costo de las alertas (SUPUESTO):** si cada episodio en alto fuera una falsa alarma de ~30 USD (supuesto de costo del equipo), el tope sería ≤ 300 USD/año por punto con HR 90 % y ≤ 570 USD/año con HR 85 %.

### 3. Fenología

- **Qué dice el reporte de ciencia** (`reportes/ciencia-enfermedades.md`, secciones 0.8 y 8):
  - La producción es continua, con picos inducidos por poda, y la floración no tiene temporada fija. Cortés-Rojas 2016 registró 28 semanas de cosecha continua en Guasca; la tesis de Sopó, floración escalonada.
  - El intervalo de floración a cosecha de Biloxi está **NO VERIFICADO**.
  - Por eso **no apliqué ningún calendario de floración**.
- **Escenario "producción continua" (SUPUESTO derivado del estudio local):**
  - Cada día la finca tiene todas las etapas a la vez, así que el riesgo de la finca es el máximo entre etapas.
  - Con los multiplicadores de `risk.FENOLOGIA` ese máximo vale 1,0 para las tres enfermedades. Resultado: **idéntico a no usar fenología** (`fenologia_escenarios.csv`).
- **Sensibilidad por cama** (una cama en una sola etapa todo el año; SUPUESTO). Días en alto en Sotaquirá / Tausa / Guasca / Chía:

| Etapa de la cama | Antracnosis | Botrytis | Roya |
|---|---|---|---|
| Sin fenología o producción continua | 3 / 3 / 4 / 6 | 18 / 17 / 10 / 16 | 4 / 0 / 6 / 6 |
| Vegetativo | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 4 / 0 / 6 / 6 |
| Floración | 0 / 0 / 1 / 0 | 18 / 17 / 10 / 16 | 4 / 0 / 6 / 6 |
| Fruto verde | 3 / 3 / 4 / 6 | **0 / 0 / 0 / 0** | 4 / 0 / 6 / 6 |
| Maduración | 3 / 3 / 4 / 6 | **0 / 0 / 0 / 0** | 4 / 0 / 6 / 6 |

- **Problema de diseño para el equipo de riesgo.** Botrytis pasa a "alto" con un índice de 0,70.
  - En maduración el multiplicador es 0,7, así que el índice ajustado solo llegaría a 0,70 con un índice bruto de 1,0: en la práctica, nunca.
  - En fruto verde (multiplicador 0,5) es imposible.
  - Esto choca con lo que cita el reporte de ciencia: Rivera et al. 2013 señalan la plena floración y el **fruto maduro** como las etapas más susceptibles a Botrytis.
  - Recomendación: subir el multiplicador de Botrytis en maduración a 1,0, o aplicar la fenología a los umbrales y no al índice.

### 4. Riesgo de hoy (`riesgo_hoy.json`)

- **Datos:** pronóstico de Open-Meteo descargado el 23-oct-2026 a las 22:03 UTC. Cubre del 21 al 29 de octubre: los 2 primeros días son datos del modelo, no observados.
- **Ventana:** 72 h (ayer, hoy y mañana), tomando el máximo diario como el mapa de NC State, igual que `risk.riesgo_ventana_72h`.
- **Nivel que muestra el tablero:** `nivel_alerta` = el mayor entre el criterio central y el de alerta, por la política del equipo de preferir falsas alarmas.

| Punto | Nivel de alerta | Central (HR 90) | Alerta (HR 85) | Detalle (criterio central) |
|---|---|---|---|---|
| Sotaquirá | **alto** | alto | alto | Botrytis 0,98, antracnosis 0,66, roya 0,79 (APROXIMACION); pico el 24-oct: 31 h de mojadura a 14,0 °C. [verificacion-riesgo-clima, 2.ª pasada: el `mensaje` decía "Roya ALTO"; ahora dice "Botrytis ALTO", porque a igual clase la roya ya no encabeza el titular] |
| Tausa | **alto** | bajo | alto | Central: Botrytis 0,40 (20 h a 10,6 °C). Con HR 85: Botrytis 0,95 |
| Guasca | **alto** | alto | alto | Botrytis 0,95, roya 0,67, antracnosis 0,55; pico el 22-oct (día pasado del modelo) |
| Chía (demo) | **alto** | alto | alto | Botrytis 0,93, roya 0,54, antracnosis 0,47 (medio); pico el 22-oct |

- **Campos de cada punto en el JSON:**
  - `nivel_alerta`, `mensaje` y `accion_sugerida`. Ante alto se sugiere "priorizar camas en el próximo recorrido y posponer el aspersor"; lo del aspersor viene de las recomendaciones de CT CAES y MSU citadas en el reporte de ciencia.
  - `enfermedades`: clase, índice, día pico, horas de mojadura, T media y clase con HR 85.
  - `proximos_7_dias`.
- **Fechas:** el script toma la fecha de hoy. Para fijar otra, `--fecha AAAA-MM-DD`.

### 5. Prueba de cordura

**a) Casos sintéticos** (`cordura_casos_sinteticos.csv`; las expectativas se fijaron antes de correr):

| Caso | Esperado | Resultado (3 criterios) |
|---|---|---|
| 14 días secos (HR 50–80 %, sin lluvia) | todo bajo | PASA |
| 14 días secos con 6 h de rocío por noche (HR 92 %, 9 °C) | todo bajo | PASA (índice máximo 0,04) |
| Un chubasco de 3 h (2 mm/h, 15 °C) | todo bajo | PASA |
| Semana lluviosa a 13–17 °C | alto en las 3 | PASA (alto los 7 días) |
| 1 día de lluvia y luego 6 días secos | alto el día 1 y bajo desde el día 3 | PASA (el riesgo baja al secarse; antracnosis queda justo en el umbral, 0,50) |
| Semana mojada a 7–9 °C (tipo Tausa) | informativo | Botrytis alto desde el día 2, antracnosis alto desde el día 3, roya bajo |

El último caso muestra que, en frío y con mojadura de varios días, Bulger y Wilson extrapolan fuera de su rango experimental y marcan alto. Gillett y Schilder midieron hasta 10 °C. Esos eventos ya llevan la bandera `botrytis_fuera_de_rango` en `risk.py`.

**b) Semanas reales de 2025.** Semanas completas de lunes a domingo; 10 más secas frente a 10 más lluviosas por punto. Criterio de éxito fijado antes de correr (SUPUESTO): ≥ 90 % de las semanas secas sin días en alto y ≥ 80 % de las lluviosas con al menos un día en alto. Datos en `cordura_semanas_secas_vs_lluviosas.csv`.

| Punto | Lluvia de referencia | Secas sin alto (HR 90) | Lluviosas con alto (HR 90) | Lluviosas con medio o alto (HR 90) | Lluviosas con alto (HR 85) | Spearman lluvia–índice máx. Botrytis |
|---|---|---|---|---|---|---|
| Sotaquirá | Open-Meteo | 100 % | 50 % | 100 % | 80 % | 0,80 |
| Sotaquirá | pluviómetro Duitama | 100 % | 30 % | 70 % | 70 % | 0,66 |
| Tausa | Open-Meteo | 100 % | 60 % | 60 % | 60 % | 0,71 |
| Tausa | pluviómetro Cucunubá | 100 % | 20 % | 20 % | 50 % | 0,40 |
| Guasca | Open-Meteo | 100 % | 30 % | 80 % | 70 % | 0,77 |
| Chía | Open-Meteo | 90 % | 50 % | 90 % | 70 % | 0,62 |
| Chía | pluviómetro U. Sabana | 90 % | 30 % | 80 % | 50 % | 0,37 |

- **"Seco → bajo": PASA** en todos los puntos.
- **"Lluvioso → alto": NO PASA.**
- **Por qué no pasa:**
  - Los modelos piden mojadura **continua**, no lluvia acumulada.
  - Según la ecuación de Bulger, Botrytis llega a 0,70 con ~28 h seguidas de mojadura a 10 °C y ~23 h a 12 °C. Lo calculé con los coeficientes de `risk.py`.
  - Una semana con aguaceros por la tarde y mañanas secas suma mucha lluvia pero corta los periodos: queda en "medio".
  - Esto concuerda con lo que el reporte de ciencia cita para arándano silvestre (Nueva Escocia): ~24 h a 12 °C para infección alta.
  - **Consecuencia:** si el agrónomo espera "semana lluviosa = alerta", el criterio central lo sorprenderá. El criterio de alerta (HR 85) o la clase "medio" acercan el resultado a esa expectativa.
- **Temporadas** (`cordura_temporadas.csv`): Botrytis tiene 1,3–1,8 días en alto por cada 30 días en temporada lluviosa (mar–may y sep–nov) frente a 0,3–1,2 en seca. En Chía la antracnosis y la roya no cambian entre temporadas.
- **Series diarias:** `g4_cordura_serie_*.png`.

### 6. Extra: riesgo con estación IDEAM frente a riesgo con Open-Meteo (casos no detectados por error de entrada)

**Método:**

- **Estaciones:** las 3 con HR válida y pluviómetro según el equipo de clima: U. de La Sabana (Chía, 3 km), Cucunubá (Tausa, 12 km) y Duitama (Sotaquirá, 22 km).
- **Horas comparadas:** las mismas en los dos lados, y solo días con 24 h de datos (294, 256 y 269 días).
- **Hora:** a la fecha del IDEAM le resté 5 h, como encontró el equipo de clima.
- **Referencia:** risk.py con datos de la estación y hoja mojada = HR ≥ 90 % o lluvia > 0.
- **Sistema:** risk.py con Open-Meteo en las coordenadas de la estación.
- **Qué mide:** el error que mete el clima de entrada, **no** la enfermedad.

Días-enfermedad en alto según la estación que el sistema detecta (alerta si medio o alto con HR ≥ 85 %, tolerancia ±1 día como la ventana de 72 h). Datos en `concordancia_estacion_agregado.csv` y `concordancia_estacion_vs_openmeteo.csv`:

| Estación | Días-enfermedad en alto (estación) | Detectados | Falsas alarmas relativas (estación en bajo) |
|---|---|---|---|
| U. de La Sabana (Chía) | 39 | **34 (87 %)** | 128 |
| Cucunubá (Tausa) | 34 | **2 (6 %)** | 21 |
| Duitama (Sotaquirá) | 2 | 0 | 29 |
| Total | 75 | 36 (48 %) | 178 |

- **Con el criterio central** (HR 90, alerta solo si alto, sin tolerancia) se detectan 21 de 75 (28 %).
- **Robustez:** si la referencia usa lluvia ≥ 0,5 mm/h, el agregado sube a 30 de 53 (57 %).
- **Por qué falla en Cucunubá:** la estación registra periodos de mojadura de 24 a 66 h a 10–12 °C (de mayo a agosto y entre el 30-nov y el 2-dic). Open-Meteo, en el mismo sitio, los corta en 12–18 h. Lo verifiqué día por día con un script de depuración.
- **Lectura para el jurado:**
  - En la Sabana (Chía), el clima de modelo con el criterio de alerta se acerca a la meta de sensibilidad del 90 % frente a la estación: 87 %.
  - En el altiplano de Tausa el modelo meteorológico no ve los eventos largos.
  - Es evidencia cuantitativa a favor de la **red fija de sensores** de la propuesta, y su costo son las falsas alarmas relativas.

### 7. Re-ejecución y robustez (después de la verificación adversaria)

**Re-ejecución.** El verificador (`reportes/verificacion-riesgo-clima.md`) cambió `riesgo_ventana_72h` en `risk.py` para que una fecha fuera del pronóstico ya no dé "bajo" en silencio. Volví a correr todo con esa versión, comparando contra una copia previa:

- Los 16 CSV salen **idénticos byte a byte**, y `riesgo_hoy.json` también, salvo el campo `generado`.
- Las 11 gráficas se regeneraron. Las pruebas de `riesgo/tests` pasan: **136 de 136**.

**Robustez** (`robustez_backtest.py` y `robustez_dias_alto_2025.csv`, criterio central). Responde a las secciones 5.1, 5.3 y 5.4 del verificador; reproduje sus cifras con un script propio.

Días en alto en 2025, suma de los 4 puntos:

| Escenario | Antracnosis | Botrytis | Roya |
|---|---|---|---|
| T − 1 °C | 7 | 45 | 5 |
| **Publicado (Open-Meteo best_match)** | **16** | **61** | **16** |
| T + 1 °C | 27 | 70 | 38 |
| Botrytis alerta desde 0,50 (umbral validado en fresa, MacKenzie y Peres 2012b) | — | 89 (24 / 23 / 15 / 27) | — |
| Roya con Tmin = 10 °C | — | — | 5 (0 / 0 / 3 / 2) |
| Roya con Tmin = 12 o 15 °C | — | — | **0** |

Los paréntesis son Sotaquirá / Tausa / Guasca / Chía.

- **±1 °C es un error realista:** el error medio de la temperatura de Open-Meteo frente al IDEAM es de 1,2–1,6 °C (`reportes/clima-open-meteo.md`). Por eso los días en alto se deben presentar como rango: antracnosis 7–27, Botrytis 45–70 y roya 5–38.
- **Roya:** los conteos dependen por completo de Tmin = 8 °C, que es SUPUESTO. Con 12 °C, o con los 15 °C de EPPO/DEFRA, salen 0 días. Recomiendo mostrar la roya como **regla de vigilancia** (mojadura prolongada a 19–25 °C, revisión visual a los 10–14 días) y no con días.
- **Botrytis desde 0,50:** sube de 61 a 89 días (+46 %). Es coherente con la política de preferir falsas alarmas, pero la decisión es del equipo; no cambié el umbral de `risk.py`.
- **Lo que no cambia:** en los tres escenarios de temperatura, el 64–67 % de los días-enfermedad en alto cae entre febrero y mayo, con abril como pico. Septiembre, noviembre y diciembre siguen en 0, y Botrytis sigue siendo la enfermedad con más días. Lo comprobé con el mismo cálculo; no queda en un CSV aparte.

## Fuentes

En esta tarea no abrí URLs. Usé solo productos locales de otros agentes, y las fuentes primarias van citadas en sus reportes:

- **Clima horario 2025 y pronóstico:** Open-Meteo, CC BY 4.0. Atribución "Weather data by Open-Meteo.com". Licencia en https://open-meteo.com/en/licence, citada en `reportes/clima-open-meteo.md`. Archivos: `clima/cache/historico_2025_*.csv`, `historico_2025_est_*.csv` y `pronostico_*_20261023T22*.csv`.
- **Estaciones del IDEAM:** datos.gov.co, CC BY-SA 4.0. Son datos crudos "no validados por el IDEAM", con la hora en UTC. Están en `raw/ideam_datosgov_2025/` y los leí como datos con `python -I`. El desfase de cada estación sale de `clima/qc/ideam_vs_openmeteo_2025.csv`.
- **Modelos, umbrales y multiplicadores:** `riesgo/risk.py` y `riesgo/README.md` (Wilson et al. 1990, Bulger et al. 1987, Magarey et al. 2005, Gillett y Schilder 2009, NC State IPM, MacKenzie y Peres 2012).
- **Fenología y temporadas:** `reportes/ciencia-enfermedades.md`, sección 8 (Cortés-Rojas 2016, tesis de Sopó, Valbuena-Gaona 2025). De ahí también Rivera et al. 2013 para la susceptibilidad del fruto maduro y la recomendación de posponer el aspersor (CT CAES y MSU).
- **Área por municipio:** EVA 2025 (UPRA), vía `reportes/clima-open-meteo.md`.

## Límites

1. **No hay validación con enfermedad.** "Detectado" y "falsa alarma" se miden contra el riesgo que calcularía una estación, no contra incidencia observada. La meta de sensibilidad ≥ 90 % en enfermedades sigue **sin verificar**.
2. **Comparación con estaciones:**
   - Solo hay 3 estaciones válidas, a 3–22 km de los puntos y con desniveles. Faltan datos (febrero de 2025 casi vacío) y solo cuentan los días con 24 h de datos.
   - La referencia también usa un proxy de mojadura (HR ≥ 90 % o lluvia), porque no hay sensor de hoja.
3. **Los conteos son de un solo año (2025).** No hay variabilidad entre años.
4. **Las coordenadas son de las cabeceras municipales**, no de fincas reales.
5. **Lo que no sabemos de los criterios:**
   - El umbral de cordura (90 % y 80 %) y el costo por falsa alarma (~30 USD) son SUPUESTOS.
   - El nivel de alerta del tablero (máximo de HR 85 y HR 90) es una decisión de política, no un resultado.
6. **Fenología:** todos los multiplicadores son SUPUESTO. El escenario de producción continua no cambia nada porque el máximo entre etapas vale 1.
7. **Riego por aspersión:** no está incluido, porque no hay columna `riego`. En camas con aspersor el riesgo está subestimado.
8. **Robustez:** los días en alto cambian mucho con ±1 °C en la temperatura de entrada (sección 7). Además, según el verificador, los días en alto de antracnosis salen solo de la aproximación del equipo, y la mitad de los de Botrytis (30 de 61) vienen de periodos de más de 32 h, fuera del rango de Bulger (NO VERIFICADO).

## Pendientes

1. **Equipo de riesgo:** corregir el multiplicador de Botrytis en maduración (0,7 hace inalcanzable el "alto"). También conviene evaluar la regla de arándano de Rivera 2013 (> 6 h de mojadura entre 14 y 25 °C) que propone el reporte de ciencia.
2. **Tablero:** usar `resultados/backtest/riesgo_hoy.json` (campo `nivel_alerta`) y mostrar "Weather data by Open-Meteo.com".
3. **Equipo de finanzas:** las cifras de carga de alertas (5–10 episodios al año con HR 90 y 11–19 con HR 85) y de casos no detectados por el clima de entrada (52 % en el agregado) sirven para el caso de negocio de los sensores fijos.
4. **Evidencia de campo:** con un piloto (sensores y registro del operario) se puede rehacer la sección 6 contra incidencia real.
5. **Antes del pitch:** volver a correr `backtest_riesgo.py` con el pronóstico más reciente si se actualiza la caché.
6. **Decisiones del equipo:** si Botrytis alerta desde 0,50 (89 días frente a 61) y cómo se presenta la roya (regla de vigilancia sin conteo, o una Tmin con fuente).
