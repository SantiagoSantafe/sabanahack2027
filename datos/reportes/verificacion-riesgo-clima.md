# Verificación adversaria: riesgo y clima

Fecha: 2026-10-23. Rol: verificador adversario de los resultados de tres agentes: `clima-open-meteo`, `modelos-riesgo` y `backtest-riesgo`. Partí de que había errores y traté de refutar cada afirmación: reabrí las fuentes, reimplementé los modelos desde cero, recalculé las cifras y volví a correr el código.

Convenciones: **CONFIRMADO** = lo comprobé con datos o con la fuente. **REFUTADO** = es falso o está mal atribuido. **MATIZ** = es cierto, pero se presenta de forma que puede engañar. **SUPUESTO / NO VERIFICADO** = como en el resto del proyecto.

## Segunda pasada (23-oct-2026, después de la re-ejecución del backtest de las 18:36)

Volví a verificar los tres resúmenes, incluido lo nuevo del backtest (`robustez_backtest.py`, sección 7 y frases del pitch). Esta vez reimplementé el conteo de días **sin importar `risk.py`** con un código distinto al de la primera pasada (`v6_segunda_pasada.py`).

**Confirmado:**

- **Pruebas:** `.venv/bin/python -I -m pytest riesgo -q` da **136 de 136** antes y después de mis cambios.
- **Coeficientes:** volví a abrir las imágenes de NC State (`raw/riesgo_ncsu_sas/`).
  - Wilson (−3,7; 0,33; −0,069; 0,005; −9,3e-5) y Bulger (−4,268; −0,0901; 0,0294; −2,35e-5) coinciden con ellas.
  - Puntos de control: Wilson 0,151, 0,499 y 0,900 a 26,6 °C; Bulger 0,503, 0,700 y 0,899 a 20,5 °C.
  - La forma del GIM también coincide, y 1 ciclo da 0,202.
  - La gráfica de temperatura de NCSU es plana, en ~0,06, entre 0 y 10 °C con 20,9 h. Eso respalda el recorte frío de Wilson, que da 0,061.
- **Citas:** Crossref confirma Wilson et al. 1990 (*Phytopathology* 80:111) y Miles et al. 2013 (*Plant Pathol.* 62(6):1238–1247). Semantic Scholar confirma Bulger, Ellis y Madden 1987.
  - **Miles 2013 sigue sin coeficientes.** OpenAlex y Semantic Scholar lo marcan como `closed` y sin copia en repositorio (`raw/verif2_riesgo_miles2013_oa/`).
  - **El abstract de Bulger está eliminado por la editorial** en Semantic Scholar, y Crossref no lo trae (`raw/verif2_riesgo_bulger1987/`). El rango de "hasta 32 h" sigue NO VERIFICADO.
  - **Pfister 2004:** el abstract de Europe PMC confirma el óptimo de 21,5 °C y una germinación "reduced greatly" a 30 °C y por debajo de 15 °C. Midió la eficiencia de infección solo entre 15 y 30 °C, en *Rhododendron*.
- **Ningún coeficiente inventado.** Todo lo que no tiene fuente está rotulado SUPUESTO o APROXIMACION en el código. Las salvedades de la primera pasada se mantienen: la Wmax de roya = 48 h está atribuida de forma forzada a EPPO/DEFRA y las anclas de Gillett y Schilder son APROXIMACION.
- **Zona horaria:**
  - **IDEAM:** recalculé con código propio el ciclo diario medio de T en el JSON crudo. En las 5 estaciones del IDEAM el mínimo cae a las 10–11 h y el máximo a las 18–19 h, o sea, en UTC. En Salitre (CAR) caen a las 5 y a las 13 h, en hora local. Se confirma la corrección de −5 h.
  - **Open-Meteo:** 8.760 h por punto y 0 duplicados.
  - **Etiqueta de la humedad del IDEAM:** el sensor 0027 se llama "HUMEDAD DEL SUELO A 1 m Ó MAS", pero sus valores se comportan como HR del aire. Lo anotó el equipo de clima y lo confirma la correlación con T, de −0,79 a −0,92. Es una inferencia, no un dato del metadato.
- **Backtest y robustez:** mi reimplementación da exactamente lo mismo que `robustez_dias_alto_2025.csv` en las 36 combinaciones. Las combinaciones son 4 puntos × T−1/0/+1 × 3 enfermedades.
  - Botrytis ≥ 0,50 también coincide: 24/23/15/27.
  - Con HR 85 coincide con `dias_riesgo_anual_2025.csv`: 14/45/14, 7/31/4, 12/22/16 y 12/35/14.
  - La estacionalidad que el backtest "no dejó en CSV" también se sostiene: feb–may concentra el 65 %, 67 % y 64 % con T −1, 0 y +1 °C, con abril como pico (12, 20 y 29).
- **Reproducibilidad:** volví a correr `backtest_riesgo.py --fecha 2026-10-23` y los 17 CSV de `resultados/backtest/` salen idénticos por SHA-1. `riesgo_hoy.json` solo cambia en el titular de Sotaquirá, por mi corrección (abajo).
- **Prueba sin datos:** `risk.py actual --fecha 2026-11-05` devuelve el error de "sin datos" y no "bajo".

**Hallazgos nuevos y correcciones:**

1. **CORREGIDO: el tablero titulaba "Roya ALTO" en Sotaquirá.**
   - **Problema:** `riesgo_hoy.json` elegía la `enfermedad_principal` por índice/umbral alto. El mensaje del 23-oct decía "Roya ALTO: 31 h de mojadura a 14,0 °C (índice 0,79)", aunque Botrytis, un modelo publicado, estaba en 0,98.
   - **Por qué es un error:** contradice la regla de roya que decidió el equipo (19–25 °C), el límite de EPPO (15 °C) y la propia recomendación de la sección 7 del backtest de mostrar la roya como regla de vigilancia.
   - **Cambio:** en `resultados/backtest/backtest_riesgo.py`, a igual clase, la roya ya no encabeza el `mensaje`, ni en HR 90 ni en HR 85. Sigue en `enfermedades` con su clase y su índice.
   - **Resultado:** el mensaje ahora dice "Botrytis ALTO ... (índice 0,98)". No cambia ningún nivel, índice ni CSV.
   - Actualicé la tabla de la sección 4 de `reportes/backtest-riesgo.md`.
2. **CORREGIDO: la frase 1 del pitch subestimaba la carga de alertas del tablero.**
   - **Problema:** decía "5–10 alertas altas por finca al año", que es la cifra con HR 90. Pero el tablero muestra `nivel_alerta` = máx(HR 90, HR 85).
   - **Comprobación (`v7_carga_alertas_tablero.py`):**
     - La unión de ambos criterios es idéntica a HR 85: ningún día en alto con HR 90 deja de estarlo con HR 85.
     - Con esa unión hay **22–45 días y 11–19 episodios al año por punto**.
   - **Cambio:** la frase ahora da las dos cifras.
   - El costo de las falsas alarmas (SUPUESTO de 30 USD por alerta) es entonces ≤ 570 USD/año por punto, no ≤ 300.
3. **CORREGIDO: frase del reporte de clima sobre la hora de la mínima.**
   - **Problema:** decía "la mínima cae a las 6 h, es decir ~0,7 h antes del amanecer (≈5,9 h)". Las 6 h son después de las 5,9 h, así que mezclaba la moda con la mediana.
   - **Dato:** la moda es 6 h, la mediana (primera ocurrencia) es 5 h y la mediana de la diferencia con el amanecer es −0,7 h.
   - **Cambio:** precisé el texto en `reportes/clima-open-meteo.md`. No cambia la conclusión: la hora local es correcta.
4. **SIN CAMBIO, decisión del equipo: la regla de roya que se acordó nunca se dispara en la Sabana.**
   - En 2025, de 3.370 a 5.063 horas mojadas por punto, solo 0–35 tuvieron T ≥ 19 °C.
   - Ningún periodo de 12 h o más superó los 13,7 °C de media.
   - En el pronóstico actual, la T media de las horas mojadas es de 10,3–13,2 °C.
   - **Conclusión:** con la regla acordada (19–25 °C) la roya da **0 alertas**, y con el GIM (Tmin = 8 °C, SUPUESTO) da 16 días en alto. No hay un punto intermedio con fuente.
   - Hay que decidir si la roya se muestra en el tablero. Mi recomendación: solo como vigilancia visual del clasificador, sin índice ambiental.
5. **MATIZ, ya escrito en el backtest:** la incertidumbre combinada es mayor de lo que muestra la tabla de robustez.
   - Esa tabla mueve solo T, con HR y criterio fijos. Si se combinan el criterio (HR 90 o 85) y ±1 °C, los días en alto de antracnosis (suma de 4 puntos) van de **7 a 73**.
   - Además, desplazar T sin mover HR supone que el error de HR es independiente. El MAE de HR es de 7–12 puntos, más ancho que el salto de HR 90 a 85.
6. **MATIZ en las frases del pitch:**
   - **Frase 5:** dice "el pronóstico pone en alerta alta a Guasca y Chía". El pico de ambos es el 22-oct, un día pasado del modelo, no observado y no pronosticado. La ventana de 72 h incluye "ayer" por diseño (NCSU), pero conviene decirlo.
   - **Frase 4:** el 87 % de Chía (34 de 39) viene con 128 falsas alarmas relativas frente a la estación.

**Pedido relayado del usuario:** "pasalos a sonnet" se refiere al modelo de los subagentes. Es una configuración del orquestador y no se puede hacer desde esta tarea. No toqué ninguna configuración.

## Veredicto corto (primera pasada)

- **Se sostiene:**
  - Los coeficientes de Wilson 1990 y Bulger 1987 coinciden con las imágenes de NC State IPM y reproducen sus gráficas.
  - La corrección de −5 h al IDEAM es real.
  - El control de calidad de Open-Meteo es correcto.
  - Las cifras del backtest se reproducen exactamente.
  - Las pruebas pasan (136 de 136 tras mi cambio).
  - Ningún coeficiente está inventado.
- **No se sostiene tal como se presenta:**
  1. **Roya.** Los días de roya son un artefacto de un SUPUESTO (Tmin = 8 °C). Con la regla que decidió el equipo (19–25 °C) o con el rango de EPPO (15–25 °C), en 2025 hay **0** días de riesgo.
  2. **Antracnosis.** Sus días en alto salen **100 %** de la aproximación del equipo, no de un modelo publicado.
  3. **Botrytis.** La mitad de sus días en alto (30 de 61) son extrapolación de Bulger, con más de 32 h de mojadura.
  4. **Sensibilidad.** Con ±1 °C de error en la temperatura (dentro del MAE medido), los días en alto cambian de forma drástica. Con ERA5 en lugar de best_match se multiplican por 1,6 a 17.
  5. **"87–92 %".** Es la sensibilidad por **hora** del proxy de hoja mojada. La sensibilidad por **día de alerta** frente a una estación es del 28–48 %.
- **Corregido:**
  - `riesgo_ventana_72h` respondía "bajo" en silencio cuando la fecha caía fuera del pronóstico.
  - Tres frases inexactas en los reportes.

## Qué hice

1. **Pruebas.** Corrí `.venv/bin/python -I -m pytest riesgo -q`: 135 pasaron antes de mi cambio y 136 después. También probé `risk.py` con el Python 3.9 del sistema: funciona.
2. **Coeficientes contra la fuente.** Abrí las imágenes de NC State IPM guardadas en `raw/riesgo_ncsu_sas/` (fórmulas FLSAS, GIM y las 4 gráficas) y comprobé cada coeficiente. Reimplementé Wilson, Bulger y GIM **sin importar `risk.py`** (`v1_modelos_independientes.py`).
3. **Fuentes citadas.** Revisé las copias de Acta Hort. 810:355, Crossref (Miles 2013 y MacKenzie y Peres 2012a/b), Europe PMC (Gama 2021, Pfister 2004, Magarey 2005), EDIS PP366, UC IPM, DEFRA/EPPO y el PDF de Griffin y Anderson 2026. Abrí de nuevo en la web el código de la LWP de Open-Meteo, Sentelhas 2008, el blog del Strawberry Center y Hortidaily (lista en Fuentes).
4. **Miles 2013.** Intenté conseguir los coeficientes por dos vías:
   - Tesis de MSU: HTTP 403 (anti-bot "go-away").
   - PDF de MSU: página de desafío de Incapsula.
   - No intenté saltar ningún bloqueo. Las copias quedaron en `raw/verif_riesgo_msu_thesis/` y `raw/verif_riesgo_miles2013_pdf/` con su NOTA.
5. **Clima.** Hice un control de calidad independiente de los 4 CSV de 2025 y comprobé la zona horaria de las 27 respuestas en caché.
   - Recalculé desde `raw/ideam_datosgov_2025/` las correlaciones con desfase de 0, −4, −5 y −6 h (`v3_ideam_utc_y_proxy.py`).
   - Recalculé la sensibilidad del proxy de hoja mojada.
   - Recalculé las áreas de la EVA.
   - Corrí la prueba sin red del cliente.
6. **Riesgo 2025.** Recalculé de forma independiente los días bajo/medio/alto de 4 criterios × 4 puntos × 3 enfermedades (`v2_qc_y_recalculo_2025.py`).
7. **Backtest.** Volví a correr `backtest_riesgo.py` completo en una copia en el scratchpad, con enlaces simbólicos a los datos para no sobrescribir nada, y comparé byte a byte.
8. **Sensibilidades nuevas.**
   - Tmin de la roya, umbral de acción de Botrytis y extrapolación de Bulger (`v4_sensibilidad_roya_botrytis.py`).
   - Sesgo de ±1 °C y modelo ERA5 (`v5_sensibilidad_entrada_clima.py`).

## Resultados

### 1. Coeficientes, fórmulas y atribuciones

| Afirmación | Veredicto | Evidencia |
|---|---|---|
| Wilson 1990: f = −3,7 + 0,33·W − 0,069·W·T + 0,005·W·T² − 9,3e-5·W·T³ | **CONFIRMADO** | Coincide con la imagen NCSU `anthracnose-fruit-rot-FLSAS-formula`. Mi reimplementación da 0,151 a 7,0 h, 0,499 a 13,1 h y 0,900 a 20,9 h (26,6 °C), igual que la gráfica. Óptimo analítico: 26,52 °C (NCSU dice 26,6). |
| Bulger 1987: f = −4,268 − 0,0901·W + 0,0294·W·T − 2,35e-5·W·T³ | **CONFIRMADO** | Coincide con la imagen NCSU. Da 0,503 a 13,8 h, 0,700 a 16,5 h y 0,899 a 20,8 h (20,5 °C), y 0,041 a 5 °C. Óptimo: 20,42 °C. |
| Recorte frío de Wilson (T < 9,33 °C → g(9,33)) | **CONFIRMADO como implementación** | Sin recorte, el polinomio da 0,961 a 0 °C y 20,9 h. La gráfica de NCSU es plana, cerca de 0,06. Con el recorte da 0,061. Es una decisión propia que reproduce la gráfica, no algo publicado. |
| GIM (Magarey 2005, forma NCSU), 1 ciclo ≈ 20 % | **CONFIRMADO** | La fórmula coincide con la imagen NCSU y 1 ciclo da 0,202. Los parámetros de C. acutatum (7/27,5/35 °C, 6/36 h) y de B. cinerea (6/20,5/40 °C, 8/18 h) coinciden con el texto de NCSU. |
| `risk.py` frente a mi reimplementación | **CONFIRMADO** | Diferencia máxima de 1,6e-14 en una grilla de 100 combinaciones de W y T. |
| Umbrales 0,15/0,50 (antracnosis) y 0,50/0,70 (Botrytis) | **CONFIRMADO** | MacKenzie y Peres 2012a: captan si INF > 0,15 y piraclostrobina si > 0,5. 2012b: Bulger con INF ≥ 0,50. Resúmenes en `raw/riesgo_crossref/`. |
| El Blueberry Advisory System usa Wilson 1990; Gama 2021 lo validó en arándano | **CONFIRMADO, con MATIZ** | EDIS PP366 lo dice de forma explícita. Pero el resumen de Gama 2021 dice que la validación fue en **Florida**, con *C. gloeosporioides* y con 15–27 °C como condición favorable. No dice nada sobre mojadura a 9–12 °C, que es lo típico de la Sabana. El sistema de Michigan (Hortidaily) también se adaptó del modelo de fresa de UF, no de Miles. Esto refuerza la elección de Wilson. |
| Miles 2013 como modelo de antracnosis (lo pedía el proyecto) | **NO IMPLEMENTADO**; atribución correcta | El resumen de Crossref confirma "ecuaciones gaussianas 3D", R² de 0,86 y 0,90, óptimo de infección 25 °C (26 °C para crecimiento micelial) y aumento hasta 48 h. Los coeficientes no se obtuvieron: lo comprobé, ambas vías están bloqueadas. `risk.py` no dice usar Miles. El reporte de clima sí lo decía, ya corregido (sección 6). |
| Aproximación de arándano: anclas de Gillett y Schilder 2009 | **CONFIRMADO como cita; anclaje = SUPUESTO** | El resumen de ISHS dice "aumento considerable" tras 12–18 h a 20–25 °C, 18–24 h a 30 °C, 24 h a 15 °C y 36–48 h a 10 °C. Leer "aumento considerable" como índice 0,5 es una decisión propia; está rotulada APROXIMACION. |
| "Wilson necesita 79 h a 10 °C y 35 h a 15 °C para llegar a 0,5" | **CONFIRMADO** | Recalculado: 78,7 h y 34,9 h. |
| Roya: Topt de 21,5 °C (Pfister 2004) y 19–23 °C favorable (Griffin y Anderson 2026) | **CONFIRMADO** | Pfister trabajó en *Rhododendron* y el README lo dice. Griffin 2026, página 3: "19–23 °C, with 21.5 °C considered the optimum". |
| Roya: LWDmax = 48 h "según EPPO/DEFRA" | **MATIZ (atribución forzada)** | DEFRA dice que la plaga "requires a temperature range of 15–25 °C ... and a leaf wetness period of 48 hours". Es un **requisito**, no un tope. `risk.py` lo usa como Wmax y pone Wmin = 8 h (SUPUESTO). Además, las alertas de roya caen a 11,6–13,3 °C, fuera de los 15–25 °C de esa misma fuente (sección 5.1). |
| Broome 1995 es de uva y no se usa como fresa | **CONFIRMADO** | No aparece en `risk.py` ni en el backtest. MacKenzie 2012b lo trata como otro modelo de Botrytis. |
| Oídio: reglas de Gubler-Thomas (UC IPM) | **CONFIRMADO, con discrepancia menor** | UC IPM suma 20 puntos en cada uno de los 3 días de arranque. `risk.py` muestra 0, 0 y luego 60. No cambia nada en la Sabana: la racha máxima entre 21,1 y 29,4 °C en 2025 es de 4 h (Tausa 0 h) y la regla pide 6 h, así que el índice da 0 de forma estructural. |
| Sentelhas 2008: HR ≥ 90 % con FC de 0,87–0,92 | **CONFIRMADO** | Resumen en explore.cnr.it. Además: FAR de 0,02–0,31 y "site-specific thresholds" mejoran la precisión. |
| Fórmula de la LWP de Open-Meteo | **CONFIRMADO** | `FaoEvapotranspiration.swift`, `leafwetnessPorbability`: si lluvia > 1, min(80 + 2·lluvia, 100); si no, clip((T−5)/10) × clip(1 − (VPD−0,1)·1,25) × 100. |

**No encontré ningún coeficiente inventado.** Lo que no viene de una fuente está rotulado SUPUESTO o APROXIMACION en el código. Hay dos excepciones: el uso de "48 h" de EPPO como Wmax (atribución forzada) y la frase del reporte de clima sobre Miles (corregida).

### 2. Clima: zona horaria, control de calidad y proxy de hoja mojada

- **Control de calidad de Open-Meteo 2025:** **CONFIRMADO.** Cada punto tiene 8.760 h, con 0 duplicados, 0 NaN y paso único de 3.600 s. La hora modal de la T mínima es las 6 h y la de la máxima, las 12–14 h. Las 27 respuestas en caché dicen `America/Bogota` con −18.000 s.
  - Detalle: "nunca Td > T" solo es cierto con tolerancia de 0,2 °C. Hay 15 h con Td = T + 0,1 °C, todas con HR = 100 %. Es redondeo, ya precisado en el reporte.
- **Las fechas del IDEAM están en UTC:** **CONFIRMADO.** En la hora cruda, la T mínima cae a las 10–11 h y la máxima a las 18–19 h.
  - Correlación con Open-Meteo: 0,13–0,18 sin desfase y 0,87–0,92 con −5 h.
  - En Salitre (CAR) la T mínima cae a las 5 h y r = 0,85 sin desfase: ya viene en hora local.
  - Matiz: en Guasca el mejor desfase es −6 h (r 0,896 frente a 0,868 con −5). Solo afecta la lluvia semanal del backtest; no es relevante.
- **MAE y r de T y HR, y lluvia 1,7–4,5 veces más horas:** **CONFIRMADO.** Recalculé la razón de horas con lluvia: 1,74–4,51.
  - Dato nuevo: la correlación **horaria** de la lluvia de Open-Meteo con el pluviómetro es de 0,07 a 0,16 con cualquier desplazamiento (−1, 0 o +1 h). La hora en que llueve en el modelo es prácticamente ruido. Las horas mojadas por lluvia en el sistema no tienen valor de evidencia a escala de finca.
- **Sensibilidad del proxy (HR_OM ≥ 85 % o lluvia ≥ 0,5 mm/h frente a HR_IDEAM ≥ 90 % o lluvia > 0):** **CONFIRMADO.** U. Sabana 0,870, Cucunubá 0,887, Duitama 0,716 y Salitre 0,89 (solo HR).
  - Matiz: el resumen dice "87–92 % en 3 de 4 estaciones". Mezcla dos variantes (con y sin lluvia).
  - Es una sensibilidad **por hora** y compara un proxy con otro proxy, no con hojas mojadas.
- **"Con lluvia > 0 se marca mojado el 55–74 % del año":** **CONFIRMADO** (0,552–0,736).
- **EVA 2025:** **CONFIRMADO.** Sotaquirá 182, Tausa 121 y Guasca 57 ha suman 360 de 906,7 ha (39,7 %). Boyacá tiene 437,35 ha y Cundinamarca 419,68 ha. Chía no aparece en 2019–2025.
- **Cliente sin red:** **CONFIRMADO.** `CLIMA_OFFLINE=1 python3 -I clima/clima_client.py offline-test` da OK en los 4 puntos.
  - Matiz: el fallback devuelve el último pronóstico (216 h) aunque se pidan otros parámetros. Lo indica en `origen`.
- **ERA5-Land sin lluvia ni viento en 2025:** **CONFIRMADO** (100 % NaN).

### 3. Recálculo independiente y reproducibilidad

- **Días bajo/medio/alto 2025:** mi implementación, independiente de `risk.py`, coincide en **47 de 48** combinaciones con `riesgo/salidas/resumen_dias_por_clase_2025.csv`.
  - La única diferencia está en Tausa, roya, con "lluvia > 0", que es el escenario descartado: mi cálculo da 52/93 y el original 47/91.
  - La causa es de diseño: `risk.py` evalúa cada día con la mojadura acumulada **al cierre del día**, y yo tomo el máximo horario. En la roya, el índice puede volver a 0 dentro del día porque la T media acumulada baja de ~10 °C y entra la regla Wmax. No es un error, pero muestra que el GIM con Wmax es discontinuo.
- **Backtest:** al correrlo completo de nuevo, los 16 CSV salen **idénticos byte a byte**. `riesgo_hoy.json` también es idéntico, salvo el campo `generado`.
- **Números del backtest que comprobé:**
  - 93 días en alto (meses 2, 14, 13, 20, 15, 8, 2, 8, 0, 11, 0 y 0).
  - Multiplicadores de HR 85 frente a 90: ×2,8, ×2,2 y ×3,0.
  - Ningún día en alto de antracnosis o roya sin Botrytis en alto.
  - Los 36 de 75 días de la concordancia con estaciones.
- **Error de diseño en la fenología (hallazgo del backtest):** **CONFIRMADO** matemáticamente. Con multiplicador 0,5, Botrytis en fruto verde no llega ni a "medio" (0,5·índice < 0,5). Con 0,7 en maduración, "alto" exige un índice de 1,0. No lo corregí: los multiplicadores son SUPUESTO y por defecto no se aplica fenología (`etapa=None`).

### 4. Riesgo de hoy (23-oct-2026)

- `riesgo/salidas/riesgo_actual.json` se reproduce igual salvo `generado`.
- **MATIZ:** hay dos JSON del mismo día que no coinciden en Tausa.
  - `riesgo_actual.json` (risk.py, HR 90) dice **bajo**.
  - `resultados/backtest/riesgo_hoy.json` (`nivel_alerta` = máximo de HR 90 y HR 85) dice **alto**.
  - Decisión pendiente: el tablero debe leer uno solo. Recomiendo `riesgo_hoy.json`, que es coherente con la política de preferir falsas alarmas.
- En Guasca y Chía el pico es el 22-oct, un "día pasado" del pronóstico (modelo, no observación). El JSON lo marca.

## 5. Hallazgos que cambian cómo presentar la evidencia

### 5.1 La roya es un artefacto de Tmin = 8 °C (SUPUESTO)

Días medio/alto de roya en 2025 (HR 90), según la Tmin del GIM (`salida_v4.txt`):

| Tmin | Sotaquirá | Tausa | Guasca | Chía |
|---|---|---|---|---|
| 8 °C (actual, SUPUESTO) | 17/4 | 2/0 | 13/6 | 20/6 |
| 10 °C | 6/0 | 0/0 | 8/3 | 8/2 |
| 12 °C | 0/0 | 0/0 | 0/0 | 0/0 |
| 15 °C (límite inferior de EPPO) | 0/0 | 0/0 | 0/0 | 0/0 |

- Los 68 días medio o alto de roya de 2025 tienen una T media de mojadura < 15 °C. Los días en alto, entre 11,6 y 13,3 °C.
- Con la **regla empírica que decidió el equipo** (19–25 °C con mojadura prolongada) hay **0** periodos en los 4 puntos. Ningún periodo de ≥ 12 h supera los 13,7 °C de media.
- Pfister 2004 dice que la germinación se reduce "greatly ... below 15 °C".
- **Conclusión:**
  - Las cifras "roya 0–6 días en alto" no son evidencia: dependen por completo de un parámetro sin fuente.
  - Y al revés: si la roya existe en la Sabana (Salazar y Buriticá 2012), un modelo de "T media de la mojadura" con un rango de 15–25 °C nunca la vería. Tampoco hay una regla validada.
  - Recomiendo presentar la roya como **regla empírica de vigilancia** y no con conteos de días. No cambié el parámetro: es una decisión del equipo, no un error local.

### 5.2 Antracnosis: los días en alto salen solo de la aproximación

- Con Wilson sola hay 0 días en alto en los 4 puntos (`comparacion_modelos_antracnosis_2025.csv`).
- Los 16 días en alto salen de la aproximación propia: anclas cualitativas leídas como índice 0,5, con mediana de 9,9–12,2 °C y 35–43 h.
- Hay que decirlo así en la diapositiva: "alerta basada en una aproximación de 5 anclas de un resumen de congreso, no en un modelo validado".

### 5.3 Botrytis: la mitad de los días en alto es extrapolación

- De los 61 días en alto, **30** salen de periodos con más de 32 h de mojadura (Sotaquirá 8/18, Tausa 11/17, Guasca 4/10, Chía 7/16).
- El rango de 32 h de Bulger viene de un resumen de buscador, NO VERIFICADO; APS respondió 403 también para mí.
- `estadisticas_eventos_2025.csv` reporta solo el 0,8–2,6 % de **periodos** fuera de rango. Ese dato oculta que el problema se concentra en los días que alertan.
- **Umbral de acción:** el único umbral validado en campo para Botrytis es 0,50 (MacKenzie y Peres 2012b). El sistema llama "medio" a 0,50–0,70 y cuenta como alerta solo ≥ 0,70.
  - Con 0,50 los días serían 24, 23, 15 y 27, frente a 18, 17, 10 y 16.
  - Si la política es sensibilidad, la alerta de Botrytis debería dispararse en 0,50. Es una decisión, no un error, así que no la cambié.

### 5.4 Las cifras de días en alto dependen mucho del clima de entrada

Días en alto 2025, suma de 4 puntos (`salida_v5.txt`):

| Entrada | Antracnosis | Botrytis | Roya |
|---|---|---|---|
| best_match, T − 1 °C | 7 | 45 | 5 |
| **best_match (publicado)** | **16** | **61** | **16** |
| best_match, T + 1 °C | 27 | 70 | 38 |

- El MAE de T frente al IDEAM es de 1,2–1,6 °C, así que ±1 °C es un error realista.
- Con **ERA5** en vez de best_match, los días en alto por punto pasan, por ejemplo en Tausa, de 3/17/0 a 52/77/43. ERA5 tiene menos horas mojadas, pero 1,6–1,9 °C más de T durante la mojadura.
- best_match es el modelo que se validó con estaciones, así que es la elección correcta. Pero el resultado **no es robusto**: hay que presentar las cifras como orden de magnitud con rango, no como "3–6 días".

### 5.5 Sensibilidad por hora frente a sensibilidad por día de alerta

- El "~0,9" del proxy es por **hora**. Frente al riesgo calculado con la estación, la sensibilidad por **día-enfermedad en alto** es:
  - 28 % con el criterio central (alto, mismo día).
  - 48 % en la configuración más favorable: HR 85, alerta en medio o alto y ±1 día.
- El backtest lo explica bien en su reporte, pero el resumen que circuló ("34 de 39") es el mejor caso (U. Sabana, configuración más favorable). Cucunubá da 2 de 34.
- La meta de **sensibilidad ≥ 90 % sigue sin verificar** con la capa ambiental, incluso frente a un proxy.

## 6. Correcciones aplicadas

1. **`riesgo/risk.py`, `riesgo_ventana_72h`: error claro y local.**
   - **Antes:** si la fecha caía fuera del pronóstico en caché, por ejemplo con la caché vencida y sin red el día de la demo, devolvía `riesgo_global = "bajo"` con 0 días evaluados. Era un "sin riesgo" silencioso, justo el tipo de caso no detectado que la propuesta quiere evitar. Lo reproduje: con el pronóstico actual (21 al 29 de octubre), `--fecha 2026-10-31` y `2026-11-05` daban "bajo".
   - **Ahora:** devuelve `riesgo_global = "sin_datos"` y un campo `error` con el rango disponible; el CLI ya imprimía `error`. Si la ventana está incompleta (1 o 2 de 3 días), agrega `advertencia`.
   - Agregué la prueba `test_ventana_72h_sin_datos_no_es_bajo` en `riesgo/tests/test_risk.py`: **136 de 136 pasan**.
   - Comprobé que no cambia ninguna salida existente:
     - `risk.py actual --fecha 2026-10-23` da un JSON idéntico salvo `generado`.
     - Los 16 CSV del backtest salen idénticos.
     - Con `--fecha 2026-11-05` ahora imprime el error.
   - Lo documenté en `riesgo/README.md`.
2. **`reportes/modelos-riesgo.md`:** la frase "×4 a 7 de HR 95 a HR 85" solo valía para Chía. Agregué las cifras reales: ×15 en antracnosis, ×7 en Botrytis y ×12 en roya en el agregado; Botrytis de ×5 a ×22 por punto. También el efecto de "lluvia > 0": ×35, ×12 y ×34.
3. **`reportes/clima-open-meteo.md`:**
   - Precisé "nunca Td > T": la tolerancia es de 0,2 °C.
   - Corregí que el insumo de los modelos fuera "Miles 2013": `risk.py` usa Wilson más la aproximación, con la serie horaria.

Las correcciones van marcadas en el texto con "[... verificacion-riesgo-clima ...]".

## 7. Detalles menores (sin cambio)

- **Lluvia horaria de Open-Meteo:** es la suma de la hora **previa**, y `risk.py` la trata como si empezara en la marca horaria. Hay un desfase de 1 h en las horas mojadas por lluvia. El impacto es mínimo frente al ruido del punto 2.
- **Rangos en el resumen de modelos-riesgo:** dice "con lluvia > 0 los días en alto pasan de 140 a 222". El rango real entre puntos y enfermedades es de 88 a 222 (Botrytis 120–222).
- **Correlación sin desfase:** el resumen de clima dice "aprox. 0". Es 0,13–0,18 (−0,02 en Guasca), como dice el cuerpo del reporte.

## Archivos producidos o modificados

- **Producidos** (en `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/verificacion-riesgo-clima_scripts/`):
  - Scripts: `v1_modelos_independientes.py`, `v2_qc_y_recalculo_2025.py`, `v3_ideam_utc_y_proxy.py`, `v4_sensibilidad_roya_botrytis.py` y `v5_sensibilidad_entrada_clima.py`.
  - Salidas: `salida_v1.txt`, `salida_v2_qc.csv`, `salida_v2_recalculo.csv`, `salida_v3_ideam.csv`, `salida_v4.txt` y `salida_v5.txt`.
  - Para reproducir: `/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I -B <script>`, cada uno en menos de 10 s.
- **Descargas bloqueadas:**
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/verif_riesgo_msu_thesis/` (403).
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/verif_riesgo_miles2013_pdf/` (Incapsula).
- **Modificados:**
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/risk.py` (`riesgo_ventana_72h`).
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/tests/test_risk.py` (+1 prueba).
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/README.md`.
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/modelos-riesgo.md`.
  - `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/clima-open-meteo.md`.
- La copia del backtest que volví a correr está en el scratchpad de la sesión y no forma parte del proyecto.
- **Segunda pasada:**
  - **Producidos:**
    - `reportes/verificacion-riesgo-clima_scripts/v6_segunda_pasada.py` y `salida_v6.txt`: reimplementación independiente, estacionalidad, regla de roya, hora de la Tmin, UTC del IDEAM y puntos de NCSU.
    - `v7_carga_alertas_tablero.py` y `salida_v7.txt`: carga de alertas con la regla del tablero.
  - **Descargas de metadatos** (APIs públicas, sin login):
    - `raw/verif2_riesgo_miles2013_oa/`
    - `raw/verif2_riesgo_bulger1987/`
    - `raw/verif2_riesgo_wilson1990/`
  - **Modificados:**
    - `resultados/backtest/backtest_riesgo.py`: elección del titular.
    - `resultados/backtest/riesgo_hoy.json`: regenerado; solo cambia el mensaje de Sotaquirá.
    - `reportes/backtest-riesgo.md`: frase 1 del pitch y tabla de la sección 4.
    - `reportes/clima-open-meteo.md`: frase de la hora de la mínima.
  - URLs abiertas en esta pasada:
    - https://api.semanticscholar.org/graph/v1/paper/DOI:10.1111/ppa.12061
    - https://api.openalex.org/works/doi:10.1111/ppa.12061
    - https://api.semanticscholar.org/graph/v1/paper/DOI:10.1094/Phyto-77-1225
    - https://api.openalex.org/works/doi:10.1094/Phyto-77-1225
    - https://api.crossref.org/works/10.1094/Phyto-77-1225
    - https://api.crossref.org/works/10.1094/Phyto-80-111

## Fuentes

**URLs que abrí en esta sesión:**
- https://raw.githubusercontent.com/open-meteo/open-meteo/main/Sources/App/Helper/FaoEvapotranspiration.swift (función `leafwetnessPorbability`).
- https://raw.githubusercontent.com/open-meteo/open-meteo/main/Sources/App/Helper/Meteorology.swift (no contiene la LWP).
- https://explore.cnr.it/resource/item/58890 (resumen de Sentelhas et al. 2008, *Agric. For. Meteorol.* 148:392).
- https://strawberrycenterblog.com/2022/04/13/classic-botrytis-data-from-1987/ (óptimo ~20 °C; no da el rango ni la ecuación).
- https://hortidaily.com/article/9719902/us-blueberry-rot-risk-prediction-model-launched-for-michigan-growers (el sistema de Michigan adapta el modelo de fresa de UF: 68–86 °F y ≥ 12 h).

**Bloqueadas, sin intentar saltarlas:**
- https://www.apsnet.org/publications/phytopathology/backissues/Documents/1987Abstracts/Phyto77_1225.htm (403).
- https://d.lib.msu.edu/etd/2763/FULL_TEXT/view (403).
- https://www.canr.msu.edu/smallfruitnhoppathology/pdf/07-RA-Miles%20et%20al.%202013%20PP.pdf (Incapsula).

**Copias locales que leí como datos:**
- `raw/riesgo_ncsu_sas/`: las 8 imágenes y el texto de https://ipm.ces.ncsu.edu/development-of-anthacnose-and-botrytis-strawberry-fruit-infection-risk-models.
- `raw/riesgo_actahort_810_46/`, `raw/riesgo_crossref/`, `raw/riesgo_europepmc/`, `raw/riesgo_edis_pp366/`, `raw/riesgo_uf_ae450/`, `raw/riesgo_ucipm_gpm/`, `raw/riesgo_defra_tminima/` y `raw/ciencia_mdpi_jof12_133/` (Griffin y Anderson 2026, CC BY).
- `raw/ideam_datosgov_2025/` (IDEAM, datos.gov.co, CC BY-SA 4.0) y `raw/eva_upra_arandano/` (UPRA, CC BY-SA 4.0).

**Clima:** Open-Meteo, CC BY 4.0. Atribución: "Weather data by Open-Meteo.com".

## Límites

- **No tuve acceso al texto completo** de Miles 2013, Bulger 1987 ni Wilson 1990. Los coeficientes de Wilson y Bulger los verifiqué contra NC State, que es una fuente secundaria pero oficial, y contra la reproducción de sus gráficas. No los comparé con los artículos originales.
- **Mis recálculos usan los mismos datos de entrada** (Open-Meteo y el IDEAM crudo). No validan nada contra enfermedad: no hay incidencia de campo.
- **Las sensibilidades de la sección 5 son de un solo año (2025)** y de las cabeceras municipales.
- **Que los metadatos de datos.gov.co no mencionen el UTC** no lo comprobé. Lo que sí confirmé es el desfase.

## Pendientes recomendados

1. **Decidir cómo se presenta la roya:** como regla empírica de vigilancia sin conteo de días, o con Tmin justificada. Hoy los conteos son un artefacto (sección 5.1).
2. **Decidir si Botrytis alerta desde 0,50,** el umbral validado (sección 5.3). Marcar en la diapositiva que la mitad de los días en alto es extrapolación de más de 32 h.
3. **Elegir un solo JSON para el tablero** (`riesgo_hoy.json`) y refrescar el pronóstico el día de la demo. Con mi corrección, una caché vencida ya no se muestra como "bajo".
4. **En la diapositiva de evidencia:**
   - Presentar los días en alto como rango, por el sesgo de ±1 °C: antracnosis 7–27, Botrytis 45–70 y roya 5–38 en la suma de 4 puntos.
   - Presentar la sensibilidad por día-alerta (28–48 %) junto a la sensibilidad por hora (~0,9).
5. **Corregir los multiplicadores de fenología de Botrytis** si se va a usar `etapa`.
6. **Pedir Miles 2013** a la biblioteca de la U. de La Sabana o a los autores.

La API key de Roboflow no aplica a esta tarea: no la leí ni la usé, y no aparece en ningún archivo que produje.
