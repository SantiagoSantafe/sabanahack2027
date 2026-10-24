# Reporte: modelos-riesgo

Fecha: 2026-10-23. Rol: implementar los modelos de riesgo ambiental (antracnosis, Botrytis, roya y oídio) con pruebas. El detalle técnico, con las fórmulas en texto, está en `riesgo/README.md`.

## Resumen

- **Antracnosis**
  - La ecuación operativa para arándano es **Wilson et al. 1990** (fresa). El Blueberry Advisory System de UF/IFAS la usa y Gama et al. 2021 la validaron en campo en arándano.
  - Los coeficientes de Miles 2013 **no se obtuvieron**: el artículo es cerrado y la copia de MSU está bloqueada.
  - La implementé con un recorte frío que reproduce la curva publicada por NCSU. Le añadí una **APROXIMACION calibrada en arándano** con Gillett y Schilder 2009, del mismo grupo que Miles. El índice final es el máximo de las dos.
- **Botrytis**: **Bulger et al. 1987**, con los coeficientes exactos que publica NC State IPM. Sus umbrales (0,50 y 0,70) están validados en campo por MacKenzie y Peres 2012, aunque en fresa.
- **Roya**: no existe ecuación publicada. Es una APROXIMACION con el modelo genérico de Magarey 2005 y temperaturas de Pfister 2004.
- **Oídio**: índice de Gubler-Thomas de la vid, marcado como **NO VALIDADO** en arándano.
- **Pruebas**: 135 en pytest, todas pasan. Reproduzco los puntos publicados de las gráficas de NCSU con error de 0,003 o menos.
- **Con el clima real de 2025** (criterio central de mojadura):
  - Días en "alto" por punto: antracnosis 3-6, Botrytis 10-18, roya 0-6, oídio 0.
  - Periodos de mojadura que llegan a "alto": 0-11 por año, por punto y enfermedad.

## Qué hice

1. **Investigué las ecuaciones** y abrí las fuentes que no estaban bloqueadas (lista en la sección de fuentes):
   - **NC State IPM**: publica como imágenes las ecuaciones FLSAS de Wilson 1990 y Bulger 1987, el GIM con sus parámetros, los umbrales, la regla "4 h secas cierran el periodo" y que la T media se calcula solo con las horas mojadas. Bajé las imágenes y las leí. Los coeficientes se comprueban porque reproducen las gráficas publicadas.
   - **UF/IFAS EDIS PP366** (Gama et al. 2022): confirma que el Blueberry Advisory System usa la ecuación de Wilson 1990. El resumen de Gama et al. 2021 (*Plant Dis.* 105:1806) informa su validación en campo en arándano en Florida.
   - **Miles et al. 2013**: solo obtuve el resumen, vía Crossref. Usan "ecuaciones gaussianas tridimensionales" con R² de 0,86 y 0,90, óptimo de 25 °C y aumento hasta 48 h. El PDF de MSU (Incapsula), la tesis (403) y Wiley (Unpaywall: closed) no fueron accesibles, así que **los coeficientes no se implementaron**.
   - **Gillett y Schilder 2009** (*Acta Hortic.* 810:355, resumen ISHS): umbrales de mojadura en arándano a 10, 15, 20-25 y 30 °C. Son las anclas de la aproximación.
   - **MacKenzie y Peres 2012a y 2012b** (resúmenes Crossref): los umbrales 0,15 y 0,5 (antracnosis) y 0,50 (Botrytis) se validaron en campo en fresa en Florida.
   - **Roya**:
     - Pfister 2004: óptimo de 21,5 °C e incubación de 10-10,7 d a 20-25 °C.
     - Griffin y Anderson 2026: 19-23 °C favorable, y la hoja necesita gotas de agua.
     - EPPO, vía DEFRA: 15-25 °C y 48 h de mojadura.
     - PNW: latencia de ~10 d a 20 °C.
     - Salazar y Buriticá 2012: registro en Colombia.
     - Agriculture Victoria, UTAS y NSW DPI estaban bloqueados.
   - **Oídio**: tomé las reglas de Gubler-Thomas de la página de UC IPM (vid). Cornell indica que el oídio del arándano no necesita agua libre.
2. **Implementé** `riesgo/risk.py`, sin dependencias externas y compatible con Python 3.9 y 3.11:
   - Detección de periodos de mojadura: proxy HR/lluvia/LWP/riego, con interrupciones configurables y horas faltantes contadas como secas.
   - Índices por evento para las cuatro enfermedades.
   - Clasificación bajo/medio/alto y multiplicador de fenología (SUPUESTO).
   - Resumen diario con la LWD acumulada por día, presión de roya a 14 días y ventana de 72 h al estilo NCSU.
   - Motivo en texto para el agrónomo y CLI para la demo.
   - Por defecto uso la lluvia ≥ 0,5 mm/h que recomienda el equipo de clima. Con "lluvia > 0" el sistema pasaría casi medio año en alerta.
3. **Escribí 135 pruebas** (`riesgo/tests/test_risk.py`): casos de libro, monotonicidad en LWD, unimodalidad en T, límites (sin mojadura → 0), detección de periodos, las reglas de Gubler-Thomas, clasificación, fenología, lectura de CSV y DataFrame, e integración con los datos reales.
4. **Corrí los modelos sobre el clima horario de 2025** de los 4 puntos (`riesgo/correr_2025.py`). Usé 5 criterios de mojadura y comparé los modelos de antracnosis.
5. **Generé 2 figuras** con la paleta validada por el script del skill de visualización.
6. **Corrí el riesgo actual de 72 h** sobre los pronósticos en caché del 23-oct-2026 para la demo.

## Archivos producidos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/risk.py`: librería y CLI.
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/tests/test_risk.py` y `conftest.py`: 135 pruebas.
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/README.md`: fórmulas, fuentes, evidencia y límites.
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/correr_2025.py` y `graficas.py`.
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/salidas/`:
  - `riesgo_2025_<punto>_eventos.csv` y `riesgo_2025_<punto>_diario.csv` (4 puntos).
  - `resumen_dias_por_clase_2025.csv`, `alertas_por_periodo_2025.csv`, `riesgo_mensual_2025.csv`.
  - `comparacion_modelos_antracnosis_2025.csv`, `estadisticas_eventos_2025.csv`.
  - `riesgo_actual.json`: riesgo de 72 h para la demo.
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo/graficas/curvas_antracnosis_arandano.png` y `riesgo_diario_2025.png`.
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/riesgo_*/`: copias de las fuentes. Las páginas bloqueadas se guardaron como `BLOQUEADO_pagina_de_desafio.html` y cada carpeta tiene su `NOTA.txt`.

## Resultados

### Casos de libro reproducidos

| Caso | Publicado | Obtenido |
|---|---|---|
| Wilson 1990 a 26,6 °C | 0,15 a 7,0 h y 0,50 a 13,1 h (gráfica NCSU) | 0,151 y 0,499 |
| Bulger 1987 a 20,5 °C | 0,50 a 13,8 h y 0,70 a 16,5 h (gráfica NCSU) | 0,503 y 0,700 |
| Óptimos analíticos | 26,6 y 20,5 °C (NCSU) | 26,5 y 20,4 °C |
| GIM | 1 ciclo ≈ 20 % (NCSU) | 0,202 |
| Wilson con recorte frío, a 0 °C y 20,9 h | ~0,06 (gráfica NCSU) | 0,061 |

### Hallazgo 1: en frío, la ecuación de fresa subestima al arándano

Para llegar al índice 0,5 Wilson necesita:

| Temperatura | Wilson | Arándano (Gillett y Schilder 2009) |
|---|---|---|
| 10 °C | 79 h | 36-48 h |
| 15 °C | 35 h | 24 h |
| 20-25 °C | 13-18 h | 12-18 h (coinciden) |

Durante los periodos de mojadura de 2025 la temperatura mediana fue de 8,6 a 10,6 °C. Con Wilson sola **ningún punto tuvo un día en "alto"**; con la envolvente hubo 3-6. Por eso el sistema usa la envolvente.

### Hallazgo 2: el umbral de lluvia define el sistema

| Criterio de mojadura | Periodo más largo | Días en "alto", Chía (antracnosis / Botrytis / roya) |
|---|---|---|
| HR ≥ 90 % o lluvia > 0 | 210-396 h | 140 / 167 / 154 |
| HR ≥ 90 % o lluvia ≥ 0,5 mm/h | 40-54 h | 6 / 16 / 6 |
| HR ≥ 85 % o lluvia ≥ 0,5 mm/h (alerta) | — | 12 / 35 / 14 |

Con "lluvia > 0" la llovizna espuria de Open-Meteo encadena periodos de mojadura. Con 0,5 mm/h los periodos se acortan y las alertas bajan a un nivel manejable.

### Hallazgo 3: Botrytis domina el riesgo ambiental en la Sabana

| Punto | Antracnosis | Botrytis | Roya | Oídio |
|---|---|---|---|---|
| Chía | 36 / 6 | 11 / 16 | 20 / 6 | 0 / 0 |
| Guasca | 17 / 4 | 5 / 10 | 13 / 6 | 0 / 0 |
| Sotaquirá | 38 / 3 | 6 / 18 | 17 / 4 | 0 / 0 |
| Tausa | 20 / 3 | 6 / 17 | 2 / 0 | 0 / 0 |

Días medio / alto en 2025 con el criterio central. Esto coincide con la recomendación de `reportes/ciencia-enfermedades.md` de priorizar Botrytis y roya.

### Hallazgo 4: Gubler-Thomas no sirve en la Sabana

Dio 0 días con riesgo en los 4 puntos. A 2.500 m casi nunca hay 6 h seguidas entre 21 y 29 °C. El oídio queda a cargo del clasificador visual.

### Otros resultados

- **Estacionalidad**: el riesgo se concentra en feb-may (máximo en abril) y repunta en agosto y octubre.
- **Demo**: el riesgo de 72 h con el pronóstico del 23-oct-2026 sale **alto** en Chía, Guasca y Sotaquirá (Botrytis 0,93-0,98) y **bajo** en Tausa. Está en `salidas/riesgo_actual.json`.

## Fuentes

URLs abiertas; las copias están en `raw/riesgo_*`:

- https://ipm.ces.ncsu.edu/development-of-anthacnose-and-botrytis-strawberry-fruit-infection-risk-models (y sus imágenes en eit-wagpress-prod.s3.amazonaws.com).
- https://edis.ifas.ufl.edu/publication/PP366/pdf
- https://ask.ifas.ufl.edu/publication/AE450
- https://www.actahort.org/books/810/810_46.htm
- https://api.crossref.org/works/10.1111/ppa.12061 (Miles 2013, resumen).
- Crossref, búsquedas bibliográficas: MacKenzie y Peres 2012a y 2012b; Bulger 1987 y Wilson 1990 solo con metadatos.
- Europe PMC REST: Gama 2021 (PMID 32954983), Pfister 2004 (PMID 30812614), Magarey 2005 (PMID 18943841), Griffin y Anderson 2026 (PMID 41745275).
- https://hortidaily.com/article/9719902/us-blueberry-rot-risk-prediction-model-launched-for-michigan-growers
- https://ipm.ucanr.edu/DISEASE/DATABASE/grapepowderymildew.html
- https://hopper.science.oregonstate.edu/risk/grape_powdery_app
- https://planthealthportal.defra.gov.uk/assets/uploads/T.minima-summary-for-consultationMay21.pdf
- https://strawberrycenterblog.com/2022/04/13/classic-botrytis-data-from-1987/
- PDFs que otros agentes ya habían descargado y que leí: Griffin y Anderson 2026 (*J. Fungi*, CC BY), Salazar y Buriticá 2012, Cornell Fast Facts sobre oídio, CT CAES sobre Botrytis, MSU E-3039 y el PNW Handbook sobre la roya.

## Límites

- **Sin validación con incidencia de campo.** Los resultados de 2025 son frecuencias de alerta, no aciertos. **No se puede afirmar una sensibilidad ≥ 90 %** para la capa ambiental.
- **La mojadura es un proxy de HR y lluvia de modelo**, sin sensor de hoja. Los días en alto se multiplican por 4 a 7 al pasar de HR ≥ 95 % a HR ≥ 85 %, y por más de 20 si se acepta cualquier lluvia. *[Corregido por verificacion-riesgo-clima, 23-oct-2026: "×4 a 7" solo vale para Chía. Sumando los 4 puntos (`salidas/resumen_dias_por_clase_2025.csv`), de HR ≥ 95 % a HR ≥ 85 % los días en alto pasan de 3 a 45 (antracnosis, ×15), de 19 a 133 (Botrytis, ×7) y de 4 a 48 (roya, ×12); por punto, Botrytis va de ×5 a ×22 y varias combinaciones pasan de 0 a 4-14 días. Con "lluvia > 0" frente a lluvia ≥ 0,5 mm/h (HR 90) el aumento es ×35 en antracnosis, ×12 en Botrytis y ×34 en roya.]*
- **Modelos prestados**:
  - Antracnosis y Botrytis vienen de fresa.
  - La aproximación de arándano se basa en un resumen con anclas cualitativas.
  - La roya es GIM con parámetros SUPUESTOS: Tmin, Tmax, LWDmin y los umbrales de clase.
  - El oídio es un modelo de vid.
  - La fenología es un SUPUESTO.
- **Riego**: no hay datos de riego por aspersión. Si no llega la columna `riego`, el riesgo de las camas con aspersor está subestimado.
- **Rango de Bulger**: el de 5-30 °C y 32 h viene de un resumen de buscador, porque APS estaba bloqueado.

## Pendientes

1. Conseguir los coeficientes de Miles 2013, por ejemplo en una biblioteca universitaria o pidiéndolos a los autores, y compararlos con la aproximación.
2. Instalar al menos un sensor de mojadura de hoja en la red fija para calibrar el umbral de HR in situ (Sentelhas et al. 2008 recomiendan calibrar por sitio).
3. Conseguir registros de incidencia por cama en una finca de la Sabana (Asocolblue o la U. de La Sabana) para medir sensibilidad y falsas alarmas reales.
4. Conectar `riesgo_ventana_72h` al sistema de alertas: ordenar las camas que el D1 inspecciona primero y recomendar posponer el aspersor cuando Botrytis o roya estén en alto.
5. Buscar un índice de oídio específico de arándano que use HR alta sin mojadura. Hoy no hay ninguno con fuente.
