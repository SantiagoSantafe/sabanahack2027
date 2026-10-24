# Ficha del dataset DrBerry (arándano: sana, alternaria, oídio, Heliothis)

Preparada por el agente `adquisicion-drberry` el 2026-10-23. Todas las cifras de esta ficha salen de los archivos descargados o de la API de Roboflow, salvo las que llevan la marca SUPUESTO o NO VERIFICADO.

## 1. Identificación

| Campo | Valor |
|---|---|
| Versión elegida | **Roboflow `drberry/drberry-original-data`, versión 1 ("data_original")**, creada el 2023-05-26 |
| URL | https://universe.roboflow.com/drberry/drberry-original-data/dataset/1 |
| Licencia | **CC BY 4.0**, según la API de Roboflow y `data.yaml`. Hay que atribuir y no se debe redistribuir sin la cita |
| Cita | Morales, C., Cavero, E., Ugarte, W. (2023). *DrBerry: Detection of Diseases in Blueberry Bush Leaves*. KDIR 2023 (IC3K), vol. 1, pp. 355-364. SciTePress. DOI 10.5220/0012207100003598. El texto del paper está bajo CC BY-NC-ND 4.0 |
| Origen de las fotos | Fundo San Roberto, distrito de Sayán, provincia de Huaura, Lima, Perú (sección 3.2.1 del paper; el resumen dice "Huaral"). Las fotos se tomaron a mediodía y con sol. Cámaras: Huawei Y7 2019, Samsung A30 y Sony CyberShot DSC-W630 (paper) |
| Fecha de captura | Según los nombres de archivo, **todas las fotos son del 2022-09-19, entre las 12:35 y las 14:44**, o sea una sola sesión de unas 2 h. El dato sale de 374 nombres con marca de tiempo; las 36 fotos `DSC*` no traen fecha |
| Tipo de anotación | Detección con cajas (YOLO y COCO). No hay polígonos |
| Clases (`data.yaml`) | `0 Alternaria`, `1 Heliothis`, `2 Oidio`, `3 Sana`. En COCO los ids van del 1 al 4 y el id 0 es una supercategoría vacía, `Leaf-Diseases-in-Blueberries` |
| Preprocesamiento de Roboflow | Auto-orient y **resize "Stretch to" 1024x1024**. El estiramiento deforma la relación de aspecto original; no consta el tamaño original y Roboflow eliminó el EXIF |
| Aumentaciones | **Ninguna.** Lo dicen la API (`augmentation: {}`) y el README de la exportación ("No image augmentation techniques were applied") |
| Formatos descargados | YOLOv8 y COCO, que coinciden caja por caja |

Rutas locales:
- `raw/drberry/drberry-original-data-v1-yolov8/{train,valid,test}/{images,labels}` y su `data.yaml`
- `raw/drberry/drberry-original-data-v1-coco/{train,valid,test}/_annotations.coco.json`
- `raw/drberry/_roboflow_metadata/`: JSON de todos los proyectos y versiones del workspace y listado de imágenes (sin la key)

Ejemplos de rutas, relativas a `raw/drberry/drberry-original-data-v1-yolov8/`:
- Sana: `train/images/20220919_123511_jpg.rf.231cd41fe1e0926971df876c24e815c3.jpg`
- Oidio: `train/images/20220919_123534_jpg.rf.d1b6863efc061f84bc348bef75537c86.jpg`
- Alternaria: `train/images/20220919_124258_jpg.rf.a677b12c0e1294589eb0aa710b564418.jpg`
- Heliothis: `train/images/20220919_131530_jpg.rf.554e7fb13d2fea1e2bfb689be548e6fa.jpg`
- Para cada imagen, la etiqueta está en `.../labels/<mismo nombre>.txt`

## 2. Versiones disponibles en el workspace `drberry`

Todos los proyectos son públicos, de detección y con licencia CC BY 4.0.

| Proyecto / versión | Creada | Imágenes en la versión (train/valid/test) | Preprocesamiento | Aumentación de Roboflow | Nombres de archivo | Veredicto |
|---|---|---|---|---|---|---|
| **drberry-original-data / v1 "data_original"** | 2023-05-26 | **410 (327/40/43)** | auto-orient, stretch 1024 | **ninguna** | originales (`20220919_HHMMSS`, `IMG_…`, `DSC…`) | **ELEGIDA** |
| drberry-gen-1 / v1 "v1.0" | 2023-02-03 | 1683 (1343/166/174) | ninguno | ninguna en Roboflow | `alternaria_0_284 (N).png`, etc. | Aumentada **fuera** de Roboflow (Keras): no usar |
| drberry-gen-2 / v1 | 2023-04-08 | 2753 (2198/272/283) | ninguno | ninguna en Roboflow | `aug_*` | Aumentada fuera de Roboflow: no usar |
| drberry-gen-3 / v1 | 2023-04-09 | 2671 (2134/263/274) | ninguno | ninguna en Roboflow | `aug_*` | Aumentada fuera de Roboflow. El workspace dice "2 versiones" pero la API solo devuelve la v1 |
| drberry-gen-3-20 / v1 | 2023-04-26 | 585 (408/116/61) | ninguno | ninguna en Roboflow | `aug_*` | Descargada solo para verificar las copias aumentadas (ver §6) |
| drberry-leaf-detection / v1 "v1_Adicional_Augm" | 2022-11-06 | 1626 (1500/63/63) | auto-orient, fit 256 | x3, flip h/v, rotación 90°, blur 1 px | originales | Otro esquema de etiquetas, muy aumentada |
| drberry-leaf-detection-2 / v1 "V1_1024" | 2023-01-21 | 978 (822/93/63) | stretch 1024 | x3, flip horizontal | originales | Otro esquema |
| drberry-leaf-detection-2 / v2 "V2_1024" | 2023-01-31 | 1000 (844/93/63) | stretch 1024 y remapeo de etiquetas | x3, flip horizontal | originales | Descargada como auxiliar (§7) |

Cómo reconocer las copias aumentadas en los proyectos `gen-*`: Roboflow las reporta "sin aumentación" porque se subieron ya aumentadas. El paper dice que se aumentaron con Keras ImageDataGenerator (rotación, flips, brillo, channel shift y relleno "reflect"). Los nombres empiezan por `aug_` o por `<clase>_0_<n> (k)`, por lo que **no se puede volver al original por el nombre**. Hay que emparejar por hash perceptual probando flips y rotaciones. El relleno "reflect" fabrica hojas duplicadas en espejo en los bordes; se ve en `resultados/drberry_figuras/gen3-20_aumentada_vs_original.jpg`.

## 3. Conteos de la versión elegida

El archivo completo es `resultados/conteo_clases.csv`.

**Imágenes por split:** train 327, valid 40, test 43, en total **410**, todas de 1024x1024 en RGB. Ninguna imagen está sin etiqueta y no hay etiquetas malformadas ni fuera de [0,1].

El proyecto tiene 439 imágenes, pero 29 quedaron sin split (`none`) y no forman parte de la versión. Son, por ejemplo, `20220919_124619.jpg` y `DSC00434.JPG`. No se sabe por qué quedaron fuera (NO VERIFICADO).

**Cajas por clase y split:**

| Clase | train | valid | test | Total | % de cajas |
|---|---|---|---|---|---|
| Alternaria | 219 | 38 | 32 | **289** | 39.2 % |
| Heliothis | 163 | 22 | 19 | **204** | 27.7 % |
| Oidio | 131 | 15 | 16 | **162** | 22.0 % |
| Sana | 69 | 7 | 6 | **82** | 11.1 % |
| Total | 582 | 82 | 73 | **737** | |

**Imágenes por clase dominante** (la clase con más cajas en la imagen; es lo que sirve para un clasificador de imagen):

| Clase | train | valid | test | Total | Imágenes que contienen la clase |
|---|---|---|---|---|---|
| Alternaria | 54 | 6 | 8 | **68** (16.6 %) | 78 |
| Heliothis | 129 | 16 | 16 | **161** (39.3 %) | 162 |
| Oidio | 96 | 12 | 13 | **121** (29.5 %) | 123 |
| Sana | 48 | 6 | 6 | **60** (14.6 %) | 62 |

- Hay 1.78 cajas por imagen de media en train (2.05 en valid y 1.70 en test), con mediana 1 y máximo 19. 145 imágenes tienen 2 o más cajas.
- Solo **15 imágenes son multiclase** (12 en train, 1 en valid y 2 en test).

## 4. Problemas detectados (importan para la rúbrica de "Evidencia y validación")

1. **Fuga por ráfagas entre train, valid y test (crítico).** Los autores tomaron varias fotos seguidas de la misma hoja, y el split aleatorio de Roboflow las repartió entre los tres conjuntos.
   - La mediana de la distancia temporal entre una imagen de valid o test y la imagen de train más cercana es **2 s**.
   - El **94.7 % de valid** (36 de 38 con fecha) y el **89.2 % de test** (33 de 37) tienen una foto en train tomada a 10 s o menos.
   - Agrupando como "ráfaga" las fotos de la misma cámara separadas por 10 s o menos (las DSC con número consecutivo): salen **139 grupos para 410 imágenes** (mediana de 2 imágenes por grupo, máximo 10). **57 grupos aparecen en más de un split**, y el **90 % de valid y el 86 % de test** comparten grupo con otro split.
   - Hay además 45 pares casi idénticos (dHash ≤ 4/64), 16 de ellos entre splits distintos.
   - Consecuencia: **las métricas calculadas con el split original salen infladas.** Por eso `resultados/drberry_imagenes.csv` trae la columna `grupo_rafaga` y una propuesta de `split_grupal_sugerido`: ~70/15/15 por grupos, estratificado y con semilla 20261023, que deja train 273, valid 66 y test 71 imágenes, con 95, 22 y 22 grupos.
   - El umbral de 10 s es una heurística (SUPUESTO). Se revisó a ojo con `drberry_figuras/pares_fotos_consecutivas_10a90s.jpg`: los pares separados por más de 10 s suelen ser hojas distintas.
2. **Tamaño de muestra efectivo pequeño.** Por clase dominante hay **Alternaria 21 grupos**, Sana 27, Oidio 40 y Heliothis 64.
   - Con el split original, el test tiene 8 imágenes de Alternaria y 6 de Sana. Acertar 8 de 8 deja un límite inferior del IC 95 % (Clopper-Pearson, 0.025^(1/8)) de **63 %**.
   - **Con estos datos no se puede demostrar una sensibilidad ≥ 90 %.** Hay que presentarla como estimación con su intervalo.
3. **Granularidad de las cajas inconsistente.**
   - Las cajas de Sana, Oidio y Heliothis encierran la **hoja completa**: el área mediana es 33 %, 25 % y 40 % de la imagen.
   - Las de Alternaria encierran **lesiones diminutas**: el área mediana es el **0.06 %** de la imagen, y 249 de las 289 cajas ocupan menos del 0.1 %.
   - Consecuencias: (a) un detector tiene que encontrar puntos de unos 25x25 px en 1024 px; (b) para un clasificador de recortes de hoja **no existe la caja de hoja de Alternaria**, así que hay que clasificar la imagen completa o sacar la caja de hoja de otra fuente (ver §7, `Hoja de arandano`); (c) el desbalance cambia según se cuente: por cajas domina Alternaria (39 %) y por imágenes domina Heliothis (39 %).
4. **Representatividad baja.** Es una sola finca, un solo día, unas 2 h, a mediodía y con sol. Muchas hojas están **desprendidas y apoyadas sobre el sustrato de fibra de coco, sobre la rodilla (jean) o en la mano**, a pocos centímetros. Casi nunca se ven hojas en la planta desde la altura de un robot. Ver `drberry_figuras/muestra_fondos_y_camaras.jpg`.
   - Hay una brecha de dominio con el D1 y con la demo "cámara mirando una pantalla" (reflejos, moiré, color de la pantalla). Conviene medir esa cadena aparte.
5. **Confusión entre cámara y clase.**
   - Las fotos `IMG_*` (cámara inferida por convención de nombres: Huawei, NO VERIFICADO) son en un 64 % Heliothis (63 de 98).
   - El 93 % de las imágenes de Alternaria (63 de 68) tienen nombre estilo Samsung, `YYYYMMDD_HHMMSS` (cámara inferida, NO VERIFICADO).
   - Un modelo podría aprender la cámara en lugar de la enfermedad.
6. **Duplicados con sufijo "(0)".** Cuatro fotos tienen una gemela con el mismo segundo de captura, por ejemplo `20220919_134049` y `20220919_134049-0-`. Dos pares caen en splits distintos: 144213 está en train y valid, y 144423 en train y test.
7. **Semántica de clases.**
   - "Heliothis" es **daño de insecto** (agujeros de larva), no una enfermedad.
   - En el dataset, "Oidio" aparece sobre todo como manchas rojizas o púrpuras en la hoja, no como micelio blanco (observación visual de las muestras, NO VERIFICADO agronómicamente).
   - Ninguna de las cuatro clases es antracnosis, Botrytis ni roya, que son las enfermedades del modelo ambiental.

## 5. Línea base publicada (paper KDIR 2023, leído de su PDF)

| Configuración | Precisión (todas las clases) | Recall | mAP50 |
|---|---|---|---|
| YOLOv5s sin aumentación (Tabla 2, fila 1) | 69.0 % | 44.5 % | 53.4 % |
| YOLOv5s con 4 aumentaciones (Tabla 2, fila 3) | 86.4 % | 73.6 % | 84.7 % |
| YOLOv5s con aumentación y "Hyp Low" (Tabla 3) | 88.4 % | 92.6 % | 94.1 % |
| YOLOv5m con aumentación y "Hyp Low" (Tabla 3) | 93.0 % | 92.7 % | 96.1 % |

- El resumen del paper dice "accuracy of 84% and recall of 91%", y esas dos cifras no aparecen tal cual en las tablas. El "84 %" que usa el equipo coincide más con el mAP50 de 84.7 % de la Tabla 2.
- En la Tabla 3, el recall de YOLOv5s por clase es: Alternaria 90.4 %, Heliothis 88.4 %, Oidium 98.7 % y Healthy 92.8 %.
- **Advertencia:** el paper evaluó sobre datos aumentados antes de partirlos (los proyectos `gen-*`). Verificamos que gen-3-20 contiene copias aumentadas de fotos de este mismo dataset y 10 pares casi idénticos entre sus splits (§6). Por eso **es probable que esas métricas estén infladas** (inferencia; no se pudo verificar qué proyecto exacto usó la Tabla 3).

## 6. Evidencia de copias aumentadas en `gen-*`

Se descargó `drberry-gen-3-20` v1 a `raw/drberry_gen3_20/`.
- Sus 585 imágenes se llaman `aug_*`.
- Comparando por dHash contra las 410 originales y sus flips y rotaciones de 90°: **83 de 585 coinciden con una foto original a distancia ≤ 8/64 bits, y 144 de 585 a ≤ 12.** Como control, dos originales al azar quedan en p1 = 20 y p50 = 32.
- Ejemplo: `test/aug_14_2376…` es el espejo de la original `train/20220919_125213…`.
- Dentro de gen-3-20 hay 10 pares casi idénticos repartidos entre splits.
- **No hay que mezclar `gen-*` con el test de `drberry-original-data`.**

## 7. Datos auxiliares descargados (no sustituyen a la versión elegida)

El conteo está en `resultados/conteo_clases_auxiliares.csv`.

- **`raw/drberry_leafdet2/`**: drberry-leaf-detection-2 v2, en YOLOv8 y 1024x1024.
  - Clases: `Dano por Alternaria` (1796 cajas), `Dano por Heliothis` (900), `Dano por Oidio` (708) y **`Hoja de arandano` (949 cajas de hoja)**.
  - Son 633 fotos de la misma sesión. **433 coinciden por nombre** con la versión elegida y **200 son fotos extra.**
  - Train tiene aumentación x3 con flip horizontal: hay que agrupar por el prefijo antes de `.rf.` (477 nombres únicos en 844 archivos).
  - Puede servir para sacar recortes de hoja de Alternaria. Ojo: la v2 no tiene auto-orient, así que la orientación podría no coincidir con la versión elegida (NO VERIFICADO).
- **`raw/drberry_gen3_20/`**: solo como evidencia de la §6.
- **`raw/roboflow_blueberry_plantdiag/`**: Plant Diagnosis AI 13 (Blueberry), de `dynamite-duelers-2`, declarado CC BY 4.0.
  - 118 imágenes fuente y 249 en la versión, a 416x416, con aumentación x3 en train.
  - Clases: `anthracnose` (435 cajas), `Exobasidium leaf spot` (549) y `septoria leaf spot` (469).
  - **Procedencia dudosa:** parecen imágenes de internet, con marcas de agua de terceros y paneles de figuras, y alguna hoja quizá no es de arándano.
  - Úsese solo como prueba cualitativa fuera de dominio, por ejemplo para ver qué hace el clasificador ante antracnosis. No vale como evidencia ni para mostrar en público.

## 8. Recomendaciones para el pipeline (no se entrenó nada)

1. Usar solo `drberry-original-data` v1 y **re-partir por `grupo_rafaga`** (o con GroupKFold), y reportar las métricas con intervalo de confianza.
2. Para el clasificador hay dos opciones: (a) imagen completa con la etiqueta `clase_dominante`, descartando o marcando las 15 imágenes multiclase; (b) recortes de hoja, sacando las cajas de hoja de Alternaria de `drberry_leafdet2` cuando el nombre coincide.
3. Fijar el umbral orientado a sensibilidad sobre el valid agrupado, no sobre el split original.
4. Presentar como limitaciones la representatividad (§4.4) y la confusión cámara-clase (§4.5).
