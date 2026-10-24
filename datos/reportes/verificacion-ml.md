# Verificación adversaria: resultados de imágenes (ml)

Agente verificacion-ml, 2026-10-23. Objetivo: intentar refutar `resultados/ml/RESULTADOS.md`, `resultados/detector.yaml` y el pipeline de imágenes. Todo se recalculó con el `.venv` del equipo (`python -I`), sin re-entrenar y sin tocar el test congelado. Los scripts de verificación están en el directorio temporal de la sesión; los números clave aparecen aquí para poder repetirlos.

## 1. Veredicto corto

| Pregunta | Resultado |
|---|---|
| (a) ¿Hay fuga entre train, val y test? | **No encontré fuga.** 0 imágenes, grupos o pares casi-duplicados cruzan splits. Queda correlación de escena (misma finca, mismo día), inherente al dataset. |
| (b) ¿El test se usó para elegir umbral o hiperparámetros? | **El umbral y C no.** Sí hubo miradas al test para decidir el método (val a validación cruzada, teselas), declaradas solo en parte. |
| (c) ¿Coinciden la matriz de confusión y el recall por clase? | **Sí, exacto**, recalculado desde las predicciones. |
| (d) ¿Son razonables los IC? | **Parcialmente.** Los IC Clopper-Pearson de los titulares ignoran el agrupamiento y son optimistas. |
| (e) ¿Está bien matizada la comparación con el 84 %? | **Casi.** Falta que el paper reporta 94,1 % y 96,1 % mAP50 en su Tabla 3, y la hipótesis de "aumentó antes de partir" es una inferencia. |
| (f) ¿Son fiables las etiquetas de la evaluación fuera de dominio? | **Las de enfermedad sí; las de "sana" son débiles y de otro encuadre.** La conclusión "especificidad de campo más representativa" no se sostiene. |
| (g) ¿Es coherente `detector.yaml`? | **Sí**, salvo una frase que corregí. |
| (h) ¿Funciona `predict.py`? | **Sí.** Reproduce las predicciones del lote y de las 5 imágenes. |

Hallazgo nuevo más importante: **el modo recortes ("cota superior") tiene un atajo de tamaño** que inflaba la parte de Alternaria (sección 4).

## 2. (a) Fuga de datos

Hechos, con lo que hice para comprobarlos:

- **Sin aumentaciones.** `drberry-original-data` v1 tiene 410 imágenes con 410 `source_id` únicos, sin copias aumentadas (la ficha y la API de Roboflow dicen "sin aumentación"; los nombres lo confirman). Los proyectos `gen-*` aumentados no se usaron.
- **Grupos.** Recalculé: 0 grupos y 0 `source_id` en más de un split, tanto en el modo imagen (410) como en el de recortes (737). El split de recortes y el de imagen asignan cada foto al mismo split.
- **phash propio.** Calculé phash, dhash y average-hash de las 410 imágenes con `imagehash`. Pares con phash ≤ 12 o dhash ≤ 10: 151, todos dentro del mismo split; **0 cruzan**.
- **Similitud CLIP.** La similitud coseno del vecino más cercano de cada imagen de test en train+val tiene mediana 0,934 (máximo 0,967), y dentro de un mismo grupo la mediana es 0,967. Miré a ojo los 10 pares más parecidos y los 7 pares de menor distancia temporal entre cámaras distintas: son hojas distintas (el parecido viene del fondo, la mano y la luz).
- **Distancia temporal.** 12 imágenes de test tienen una foto de train o val a ≤ 10 s, **pero siempre de otra cámara** (nombres `IMG_...` frente a `2022...`). La ráfaga se definió por cámara, así que dos teléfonos disparando casi a la vez no se fusionan. Revisé 9 de esos pares a ojo: hojas distintas, a veces con etiqueta distinta. Riesgo residual bajo.
- **Fuga de escala de escena.** Todo es una finca, un día, tres cámaras y fondos repetidos (paja, corteza, mano). El modelo puede aprender el fondo. Un split por grupos no lo elimina; solo un conjunto externo lo mide (sección 6).
- **Medí la inflación de la fuga por mi cuenta.** Con los mismos embeddings CLIP globales y una regresión logística, una validación cruzada aleatoria sobre las 410 imágenes da exactitud 0,906 y falsas alarmas 0,17, y una agrupada da 0,726 y 0,45 (5 semillas). Es decir, la fuga infla unos 18 puntos, en línea con los "unos 20" del reporte (que compara 0,91 con 0,69 sobre dos test distintos; mi comparación es sobre los mismos datos).

## 3. (b) Uso del test

- `threshold.py` fija el umbral solo con el CSV de validación u OOF; el test entra únicamente como informe. Confirmé que el umbral 0,7373 sale de `predicciones_cvprobe_val.csv` (342 OOF, 118 grupos, 0 grupos en más de un pliegue, 0 ítems en común con el test). Mi recálculo independiente da el mismo punto de operación (mínimo de falsas alarmas 15/46 con sensibilidad ≥ 0,90; el valor 0,7373 es el punto medio con el puntaje anterior, y cualquier umbral entre 0,7287 y 0,7459 da las mismas alertas en OOF).
- C se eligió por macro-F1 OOF, sin test. `StandardScaler` y la regresión se ajustan dentro de cada pliegue.
- **Miradas al test que influyeron en el método** (cronología de `resultados/ml/logs/`):
  1. 17:52 a 18:02: se evaluaron en test 9 configuraciones (recortes e imagen, cero-shot, sonda, teselas 2 y 3, YOLO 224 y 448).
  2. El protocolo `protocolo_seleccion.json` se registró a las **18:03:25**, es decir, después de esas evaluaciones. El texto "El test congelado se evalua UNA vez" del protocolo es falso en sentido literal. RESULTADOS.md §2 sí declara la mirada que motivó el paso a validación cruzada.
  3. La idea de las teselas apareció después de ver en test que Alternaria no se detectaba a imagen completa. No está declarada como mirada al test.
- La selección final es limpia en parámetros (umbral, C, variante por OOF), pero **la frase de la diapositiva "el umbral se fijó sin mirar el test" es optimista**. Propongo: "el umbral y los parámetros se fijaron en validación cruzada; el método se ajustó tras ver un test previo, y lo declaramos".
- Sesgo hacia el final: no se eligió el mejor en test. El modelo final no es el mejor en test (teselas 2x2 da 0,87 de sensibilidad), lo que es honesto.
- Todos los candidatos post-hoc están marcados como tales en el yaml. Correcto.

## 4. (c) Recálculo independiente y hallazgo del atajo de recortes

### 4.1 Imagen completa, modelo final (tiles3, CV5)

Con `predicciones_cvprobe_test.csv` (sha256 `5a473fae…`, igual al del yaml) y la regla "sospecha si 1 − p(sana) ≥ 0,7373, clase = enfermedad más probable":

| Verdad \ decisión | alternaria | heliothis | oídio | sana |
|---|---|---|---|---|
| alternaria (14) | 4 | 0 | 0 | 10 |
| heliothis (18) | 0 | 16 | 2 | 0 |
| oídio (22) | 0 | 5 | 16 | 1 |
| sana (14) | 4 | 0 | 1 | 9 |

- Coincide con `matriz_confusion_conteos` del yaml, celda por celda. Exactitud 0,6618, macro-F1 0,6235, TP 43, FP 5, FN 11, TN 9, sensibilidad 0,7963, tasa FP 0,3571.
- Clopper-Pearson recalculado: sensibilidad [0,665–0,894], FP [0,128–0,649]. Igual que el yaml.
- Bootstrap por grupo (5.000 réplicas, semilla mía): sensibilidad [0,57–0,98], FP [0,00–0,75]. Igual que el yaml dentro del ruido.
- Detección como sospecha por clase: alternaria 4/14, heliothis 18/18, oídio 21/22. Diagnóstico correcto: 4/14, 16/18, 16/22. Ambas versiones están en el yaml y no se contradicen.
- **Re-inferencia.** Con los pesos entregados (`modelo_final/clip_probe_tiles3.joblib`) y una caché de embeddings nueva, las 68 predicciones de test difieren de las guardadas en menos de 2e-5 y todas dan la misma decisión.
- Los 9 puntos de operación del yaml con `fuente` y `tp_de` (`puntos_operacion_test`, `comparaciones_test`, candidato y estrés) coinciden con sus `metrics.json` en TP/FN, FP/TN, exactitud y umbral.

### 4.2 Estructura de los errores

- Las 11 no detectadas vienen de **4 grupos** (un grupo de Alternaria aporta 6). Alternaria: solo 2 de los 5 grupos tienen alguna detección.
- Las 5 falsas alarmas vienen de **2 de los 5 grupos de sanas**. El n efectivo es 5 hojas físicas de sana.
- Fragilidad del punto de operación: con 0,7459 (el siguiente puntaje observado) las falsas alarmas bajan a 4/14 con la misma sensibilidad. El reporte ya documenta que el re-guardado JPEG q92 las baja a 3/14. Con 14 sanas, un punto de umbral mueve la tasa 7 puntos.

### 4.3 Hallazgo: el modo recortes tiene un atajo de tamaño

El convertidor aplica un tamaño mínimo de recorte (96 px) y una ampliación a 224. Midiendo los 737 recortes:

| Clase | Recortes | Ancho mínimo | Mediana | Máximo |
|---|---|---|---|---|
| alternaria | 289 | 96 | **96** | **96** |
| heliothis | 204 | 202 | 961 | 1024 |
| oídio | 162 | 238 | 799 | 1024 |
| sana | 82 | 158 | 856 | 1024 |

- **Los 289 recortes de Alternaria miden exactamente 96x96 px**, o sea el mínimo; son lesiones ampliadas y borrosas. Ninguna otra clase baja de 158 px.
- Solo con el tamaño del recorte, Alternaria frente a sana tiene AUC 1,00; solo con la nitidez (varianza del Laplaciano), 0,987 en todo el conjunto y 1,00 en test.
- Heliothis frente a sana y oídio frente a sana no tienen ese atajo: AUC por tamaño 0,52 y 0,55 en test.

Consecuencias:
- El "87/87 y 0/14, cota superior con localización perfecta" mezcla 35 recortes de Alternaria que el modelo pudo separar por resolución y no por la lesión con 52 de heliothis y oídio, que sí son una medida limpia (**52/52 detectadas, 0/14 falsas alarmas**).
- El candidato post-hoc (sonda de recortes aplicada a la imagen) hereda el atajo: nunca diagnostica "alternaria" a imagen completa (0/14), lo que es coherente con haber aprendido "borroso y pequeño = alternaria".
- **IC de los recortes.** Son 87 recortes de 54 imágenes y 19 grupos. El IC95 CP [0,96–1,00] trata los recortes como independientes. Con 19 de 19 grupos acertados, el límite inferior a nivel de grupo es 0,025^(1/19) ≈ 0,82. Lo mismo para las 14 sanas de 5 grupos.
- Esto no afecta el modo imagen (que no usa recortes).

Cambio hecho: nota en `RESULTADOS.md` §13. No cambié las cifras, que son correctas como cálculo.

## 5. (d) Intervalos de confianza

- Los bootstrap por grupo se calculan bien (remuestrean los 21 grupos de test). Con 5 grupos de sanas y 5 de Alternaria dan intervalos degenerados ([0,00–1,00] para el recall de Alternaria y para la tasa de FP hasta 0,74). No es un error, pero hay que citarlos así: "no sabemos más que el IC más ancho".
- Los **Clopper-Pearson** de los titulares (sensibilidad 0,66–0,89; FP 0,13–0,65) suponen 54 y 14 observaciones independientes. No lo son (19 grupos con enfermos y 5 de sanas). Los bootstrap por grupo (0,57–0,98 y 0,00–0,74) son los apropiados. RESULTADOS.md §10 lo dice, pero la diapositiva (§9) cita el CP. Recomiendo citar el rango por grupo o ambos.
- El hecho de que la sensibilidad OOF sea 0,90 (por construcción, el umbral se eligió ahí) y 0,80 en test es compatible con ese ruido: la diferencia (11 no detectados, de 4 grupos) no demuestra por sí sola un sobreajuste.
- Sin ajuste por múltiples comparaciones: se miraron unas 12 configuraciones en test; los IC de cada una por separado son aún más optimistas para "el mejor".

## 6. (e) Comparación con el 84 % publicado

Abrí `raw/drberry_paper/122071.pdf` (Morales, Cavero y Ugarte, KDIR 2023) y comparé:

- El resumen dice "accuracy of 84% and recall of 91%", sin tabla que lo respalde (coincide con el reporte).
- La **Tabla 2**, fila 3, da precisión 86,4, recall 73,6 y mAP50 **84,7** (coincide con el reporte).
- La **Tabla 3** (YOLOv5s y YOLOv5m "in Testing Images") da mAP50 **94,1 y 96,1** y recall 92,6 y 92,7. El reporte no la menciona; el 84 % es el valor intermedio y no el mejor que publican. Esto sube la vara: conviene escribir "84,7 % mAP50 (Tabla 2) y hasta 94–96 % (Tabla 3), de detección".
- "Evaluó sobre datos aumentados antes de partirlos" no aparece en el paper: el texto solo dice que se aumentó con Keras y que Roboflow dio los archivos. Es una inferencia de la ficha, y debería llevar la marca NO VERIFICADO.
- El paper habla de 544 imágenes (439 con una enfermedad y 105 con varias); la versión 1 usada tiene 410. No son el mismo conjunto exacto.
- Conclusión: la afirmación central (no comparable: detección frente a clasificación, y fuga) **se sostiene**; el matiz debe incluir lo anterior.

Nota para la simulación: `simulacion/parametros.yaml` cita "recall 92,6 %" y "44,5 %" y todavía no reemplaza `sensibilidad_clasificador` (0,80 SUPUESTO) ni `especificidad_clasificador` (0,95 SUPUESTO) por lo medido (0,80 y 0,64 en DrBerry; 0,27 en campo con la salvedad de la sección 7).

## 7. (f) Evaluación fuera de dominio

- Recalculé desde `ood/pred/predicciones_image_clip_cv_tiles3.csv` y `manifest_ood.csv`: 44/60 sanas de campo, 53/57 oídio, 60/60 roya, 51/51 orugas, 202/451 PlantDoc verde, 69/1502 PlantVillage, 9/13 cultivadas y 35/47 silvestres. **Todo coincide** con RESULTADOS.md y el yaml. Los pesos usados son los del modelo final (mismo sha256), aunque el campo `modelo` del JSON dice otra ruta (solo una etiqueta).
- **Etiquetas de enfermedad:** de calidad razonable (grado research, taxón verificado, 31+22 descartes por hospedero). Siguen sin confirmación de laboratorio, como dice la ficha.
- **Etiqueta "sana": débil y de otro encuadre.** Miré un mosaico de 24 sanas (12 con alerta y 12 sin ella): son escenas de planta entera con fruto, flor, manos y fondo, no primeros planos de hoja como DrBerry ni la vista del robot. "Sana" es "sin síntomas a la vista en miniatura" (revisión del agente, no de un fitopatólogo), y en esas escenas una mancha pequeña pasa desapercibida. El 73 % de alertas mide principalmente el cambio de encuadre.
- **Sensibilidad OOD poco informativa.** El modelo alerta también en el 100 % de la fresa asintomática (58/58), el 62 % de las hojas sanas de otras especies y el 84 % de las rojizas. Que alerte en 93 % del oídio y 100 % de la roya, con un modelo que alerta casi siempre, no es "bueno para ante la duda alerta": no discrimina. La medida con sentido es el AUC (0,83 oídio de campo frente a sanas de campo), y también puede reflejar el encuadre (síntoma de cerca frente a planta entera).
- **Frase corregida:** `recomendacion_para_simulacion.especificidad_clasificador.etiqueta` decía que la de campo "es la más representativa de una finca real". No se sostiene (arándano silvestre de zona templada, planta entera, no andino, no vista del robot). La cambié en `resultados/detector.yaml`, `resultados/ml/modelo_final/detector.yaml`, `resultados/ml/detector_extras.yaml` y `resultados/ml/scripts/detector_extras.py`. Solo cambió ese campo (comprobado comparando el YAML antes y después); el YAML sigue cargando y las pruebas siguen en 45 passed, 2 skipped. El valor numérico 0,2667 no cambió.
- Las filas de PlantVillage (1502 imágenes de 160 hojas) y PlantDoc (recortes de una web) no son independientes entre sí; sus IC son optimistas.

## 8. (g) y (h) Coherencia del yaml y `predict.py`

- `detector.yaml` es coherente con las métricas (sección 4.1), el test congelado (sha256 `3ffbaca8…`, `split.py --verify` dice "intacto" para recortes y para imagen) y el sha256 de las predicciones. Número de grupos y de ítems coinciden. Los hashes no son circulares.
- Notas menores: el yaml contiene dos bloques `fuera_de_dominio` (el del modelo final al nivel superior y el del candidato anidado), lo que puede confundir a un consumidor; la clave `estres_pantalla_camara_sintetico.original` da 3/14 falsas alarmas frente a 5/14 del test principal (re-guardado en JPEG q92, declarado).
- `pytest pipeline/tests`: 45 passed, 2 skipped. Corrí `predict.py` sobre las 5 imágenes con CPU: las probabilidades son idénticas a las de `predicciones_5_imagenes_cpu.jsonl` (4 aciertan; `5_sana.jpg` da falsa alarma con p_enfermedad 0,896 frente a 0,737). La latencia de inferencia fue 87 a 89 ms (la primera llamada incluye calentamiento) frente a p50 85 ms.
- Con `--center-crop 0.7` (la receta de demo), `3_alternaria.jpg` mantiene la alerta pero cambia el diagnóstico de alternaria (0,92) a oídio (0,58). Recortando el 70 % central de las 68 imágenes de test y usando el mismo umbral: 44/54 detectadas y 2/14 falsas alarmas (dentro del ruido), pero Alternaria da alerta en 5 de 14 y solo 2 de ellas se diagnostican como alternaria. `--save-frames` solo actúa en modo cámara.
- No se pudo probar la cámara ni la pantalla (no hay D1 aquí). La API key de Roboflow no aparece en `resultados/`, `pipeline/` ni `reportes/` (búsqueda con `grep -F -f`, sin imprimirla).

## 9. Cambios que hice

1. `resultados/ml/RESULTADOS.md`: sección §13 con las notas del verificador (atajo de recortes, IC, especificidad de campo, frase del umbral, paper, fragilidad). No se tocó ninguna cifra.
2. Frase de especificidad de campo en `resultados/detector.yaml`, `resultados/ml/modelo_final/detector.yaml`, `resultados/ml/detector_extras.yaml` y `resultados/ml/scripts/detector_extras.py`.
3. Nada más: no re-entrené, no regeneré tablas y no toqué el test congelado.

## 10. Riesgos abiertos y sugerencias

- **Reemplazar** en `simulacion/parametros.yaml` la sensibilidad y la especificidad del clasificador por lo medido, y usar como pesimistas 0,65 de sensibilidad (estrés) y 0,64 de especificidad (DrBerry).
- **Citar** los IC por grupo, no solo los Clopper-Pearson; describir la prueba de recortes como "heliothis + oídio 52/52, 0/14" y no como 87/87.
- **Declarar** en la diapositiva que el método se afinó tras ver un test previo.
- **Medir con el D1 real** (pendiente principal): es la única prueba que cubre cámara, pantalla y fondo.
- **Conjunto de sanas adecuado:** hojas de arándano sano de un cultivo comercial con el mismo encuadre que el robot, idealmente locales, para medir la especificidad real.
- **Recortes sin atajo:** repetir la cota superior con recortes de tamaño fijo (por ejemplo 224 px desde la imagen original) para todas las clases.
- **El pedido de pasar los subagentes a Sonnet** no lo puedo atender desde aquí: este agente no cambia su propio modelo ni el del workflow.

## 11. Fuentes y archivos revisados

- Locales: `resultados/ml/RESULTADOS.md`, `resultados/detector.yaml`, `resultados/ml/drberry_image/` (splits, `clip_cv_tiles3`, `eval_*`, `umbral_*`), `resultados/ml/drberry_crops/`, `resultados/ml/ood/`, `resultados/ml/modelo_final/`, `resultados/ml/logs/`, `resultados/ficha_drberry.md`, `resultados/ficha_campo_ood.md`, `pipeline/*.py`, `simulacion/parametros.yaml`.
- Externa (abierta como archivo local): Morales, Cavero y Ugarte (2023), *DrBerry: Detection of Diseases in Blueberry Bush Leaves*, KDIR 2023, `raw/drberry_paper/122071.pdf` (https://www.scitepress.org/Papers/2023/122071/122071.pdf). Texto bajo CC BY-NC-ND 4.0, consultado solo para lectura interna.
