# Resultados del clasificador de hojas (DrBerry, arándano)

Sabana Hack, reto "Berry Good Idea". Agente entrenamiento-evaluación, 2026-10-23. Todas las cifras salen de archivos de `resultados/ml/`, que se citan en cada sección. Los IC95 son Clopper-Pearson (CP) o bootstrap que remuestrea grupos de ráfaga (boot). Las tablas completas están en `tabla_drberry_test.csv`, `tabla_ood.csv` y `tabla_stress.csv`.

> **Modelo EN USO: `modelo_camara` (Mc_tr), medido con la cámara del D1: sensibilidad 42/54 = 0,78 (IC por grupo 0,61–0,92), falsas alarmas 4/14 = 0,29 (IC 0,00–0,71), alternaria 3/14** (`../../reportes/reentreno-camara.md`). Todo lo que sigue en este archivo es del modelo anterior (`modelo_final`) con imágenes limpias, sin cámara. Cifras vigentes: `CIFRAS_CLAVE.md`.

## 1. En una frase

- **Si la lesión ya está recortada** (cota superior; el "87/87 y 0/14" está inflado por el tamaño de los recortes de alternaria, ver §13): la parte limpia es oídio + Heliothis, **52/52 y 0/14**.
- **Con la hoja completa** (modelo anterior, imagen limpia, sin cámara), el modelo elegido con protocolo detecta **43 de 54 enfermas (80 %)** y da **5 de 14 falsas alarmas (36 %)**.
  - Alternaria es el punto débil.
- **Fuera de DrBerry** casi todo lo enfermo dispara alerta (oídio 93 %, roya 100 %), pero también disparan **44 de 60 hojas sanas de campo**.

## 2. Datos y protocolo

| Paso | Resultado | Fuente |
|---|---|---|
| Conversión (DrBerry drberry-original-data v1, CC BY 4.0) | Recortes: 737 (alternaria 289, heliothis 204, oídio 162, sana 82). Imagen completa: 410 (68 / 161 / 121 / 60) | `drberry_*/convert/convert_summary.json` |
| Deduplicación | phash ≤ 6 (71 pares) más ráfagas de 10 s de `resultados/drberry_imagenes.csv` dan **139 grupos** | `drberry_crops/dedup/` |
| Split 70/15/15 agrupado y estratificado (semilla 20261023) | Recortes: 523 / 113 / 101 (grupos 93 / 25 / 21). Imagen: 278 / 64 / 68, **las mismas fotos de test** (`split.py --assign-from`). **Fuga 0** | `drberry_*/splits/split_summary.json` |
| Test congelado | Recortes: sha256 `ed56f4e7…`, contenido `7e721c4b…`. Es el mismo hash de contenido que obtuvo el agente de código en su prueba de humo, así que el split es reproducible. Imagen: sha256 `3ffbaca8…`, contenido `818562c3…`. `split.py --verify` dio "intacto" después de cada evaluación | `drberry_*/splits/test_frozen.json`, `logs/04*.log` |
| Test de imagen por clase | alternaria 14, heliothis 18, oídio 22, sana 14. Las 14 sanas vienen de unos 5 grupos (3 grupos con sana como clase mayoritaria) | `split_summary.json` |

**Protocolo de selección.** Lo registré en `protocolo_seleccion.json` antes de evaluar los modelos de validación cruzada en test.

- **Unidad principal:** imagen completa, porque es lo que el D1 verá en la pantalla. Los recortes quedan como cota superior.
- **Familia de modelo:** se elige en validación con el umbral que da sensibilidad ≥ 0,90 y el mínimo de falsas positivas.
- **Variante y umbral:** se eligen con validación cruzada agrupada en 5 pliegues sobre train+val, con predicciones fuera de pliegue (OOF). Son 342 imágenes y 118 grupos, frente a 64 imágenes y 25 grupos de val.
- **Declaración:** el paso a validación cruzada lo decidí *después* de ver que el umbral fijado en val (10 sanas) no sostuvo la sensibilidad en test en 4 de los 5 modelos de imagen. Fue una mirada al test y la dejo dicha.

## 3. Resultados en el test congelado de DrBerry

"Sens" es la fracción de enfermas que reciben alerta (sospecha = 1 − p(sana) ≥ umbral). "FP" es la fracción de sanas que reciben alerta.

### 3.1 Recortes de caja (lesión u hoja ya localizada: cota superior)

| Modelo | Umbral (val) | Exactitud | Sens [IC95 CP] | FP [IC95 CP] | Recall oídio |
|---|---|---|---|---|---|
| CLIP cero-shot | 0,639 | 0,59 | 86/87 = 0,99 [0,94–1,00] | 3/14 = 0,21 [0,05–0,51] | 0,12 |
| **Sonda lineal CLIP** | 0,801 | **0,96** [boot 0,89–1,00] | **87/87 = 1,00 [0,96–1,00]** | **0/14 = 0,00 [0,00–0,23]** | 0,84 |
| YOLO11n-cls 224 | 0,648 | 0,91 | 87/87 = 1,00 [0,96–1,00] | 6/14 = 0,43 [0,18–0,71] | 0,88 |

### 3.2 Imagen completa (lo que ve el robot)

| Modelo | Umbral fijado en | Sens. en val/OOF | FP en val/OOF | Exactitud test | Sens test [IC95 CP] | FP test [IC95 CP] | Alternaria detectada | AUC enfermo-sano |
|---|---|---|---|---|---|---|---|---|
| CLIP cero-shot | val | 0,94 | 7/10 | 0,43 | 49/54 = 0,91 [0,80–0,97] | 9/14 = 0,64 [0,35–0,87] | 9/14 | 0,88 |
| Sonda CLIP (global) | val | 0,91 | 1/10 | 0,69 | 44/54 = 0,81 [0,69–0,91] | 6/14 = 0,43 | 6/14 | 0,85 |
| Sonda CLIP teselas 2x2 | val | 0,93 | 0/10 | 0,71 | 45/54 = 0,83 | 2/14 = 0,14 | 5/14 | 0,90 |
| Sonda CLIP teselas 3x3 | val | 0,91 | 0/10 | 0,69 | 43/54 = 0,80 | 0/14 = 0,00 | 4/14 | 0,94 |
| YOLO11n-cls 224 | val | 0,91 | 6/10 | 0,72 | 49/54 = 0,91 [0,80–0,97] | 8/14 = 0,57 [0,29–0,82] | 10/14 | 0,84 |
| YOLO11n-cls 448 | val | 0,96 | 2/10 | 0,56 | 46/54 = 0,85 | 10/14 = 0,71 | 8/14 | 0,78 |
| YOLO11n-cls 640 | val | 0,96 | 2/10 | 0,69 | 46/54 = 0,85 | 10/14 = 0,71 | 6/14 | 0,77 |
| Sonda CV5 global | OOF | 0,91 | 17/46 | 0,74 | 44/54 = 0,81 | 4/14 = 0,29 | 6/14 | 0,86 |
| Sonda CV5 teselas 2x2 | OOF | 0,92 | 15/46 | 0,69 | 47/54 = 0,87 | 5/14 = 0,36 | 7/14 | 0,86 |
| **Sonda CV5 teselas 3x3 [FINAL]** | OOF | 0,90 | 15/46 | **0,66** | **43/54 = 0,80 [0,66–0,89]** | **5/14 = 0,36 [0,13–0,65]** | **4/14** | 0,87 |
| Idem, umbral por clase (alta sensibilidad) | OOF | 0,95 | 24/46 | 0,65 | 48/54 = 0,89 [0,77–0,96] | 7/14 = 0,50 [0,23–0,77] | 8/14 | 0,87 |
| *Candidato post-hoc:* sonda de **recortes** aplicada a la imagen | val | 0,91 | 1/10 | 0,71 | 49/54 = 0,91 [0,80–0,97] | 2/14 = 0,14 [0,02–0,43] | 9/14 (con diagnóstico alternaria 0/14) | 0,92 |

Fuentes: `drberry_image/eval_*_test/metrics.json`, `umbral_*.json` y `tabla_drberry_test.csv`. El IC bootstrap por grupos de la sensibilidad final es [0,57–0,98].

Cómo leer la tabla:

1. **La validación de 25 grupos engaña.**
   - Las sondas con teselas tuvieron 0/10 falsas positivas en val, y YOLO 448/640 tuvo sensibilidad 0,96 en val. En test, la sensibilidad de las teselas cayó a 0,80–0,83 y la tasa de falsas positivas de YOLO subió a 0,71.
   - La validación cruzada OOF da una cifra más realista: alrededor de 33 % de falsas positivas con 90 % de sensibilidad. Es coherente con lo que se vio en test.
2. **Alternaria es el problema a imagen completa.**
   - Solo se detectan 4 a 10 de 14. Heliothis (16–18/18) y oídio (21–22/22) se detectan casi siempre.
   - Las lesiones de Alternaria miden unos 25 px en 1024 px y desaparecen al reducir la imagen.
   - Las teselas suben el AUC de test (0,90–0,94 frente a 0,85 sin teselas, con umbral fijado en val), pero no mejoran la detección de Alternaria.
3. **El modelo final se eligió con protocolo y no es el mejor en test.** Lo reporto así a propósito: cambiar de modelo ahora sería ajustar al test.
4. **El candidato post-hoc se ve mejor, pero hay que tratarlo como hipótesis.**
   - Es la sonda entrenada con recortes y aplicada a la imagen. Logra la misma sensibilidad que YOLO 224 con un tercio de las falsas alarmas, y es el que mejor generaliza al campo (§5).
   - Lo evalué *después* de elegir el final, así que es una hipótesis a confirmar con capturas del D1.
   - Nunca diagnostica "alternaria" a imagen completa (0/14): detecta la alerta, pero la llama oídio o heliothis.
5. **Variabilidad por semilla del final.** La CV5 con teselas 3x3 y semillas 0 a 4 dio en test sensibilidad 0,80–0,81 y falsas positivas 0,36–0,50 (`drberry_image/semillas_cv_tiles3/`, `logs/04k_semillas_cv.log`).
6. **Fragilidad del punto de operación.** Volver a guardar las fotos de test como JPEG de calidad 92 cambió las falsas positivas del final de 5/14 a 3/14 (`tabla_stress.csv`, condición "original"). Con 14 sanas, cada hoja mueve la tasa 7 puntos.

### 3.3 Entrenamiento de YOLO11n-cls en MPS (Mac M4)

| Run | 1.ª época (estimación) | Épocas (paciencia 25) | Mejor época (top-1 en val) | Minutos |
|---|---|---|---|---|
| Recortes 224 | 4,1 s | 28 | 3 (0,920) | 1,8 |
| Imagen 224 | 4,1 s | 55 | 30 (0,766) | 2,6 |
| Imagen 448 | 7,1 s | 40 | 15 (0,828) | 4,5 |
| Imagen 640 | n/d (17,6 s con la GPU compartida) | 43 | 18 (0,844) | 9,9 |

Fuentes: `logs/03a_yolo_estimacion.log`, `logs/03b_yolo_train.log` y `drberry_*/runs/*/train_status.json`.

- Todas las corridas pararon por paciencia muy por debajo del presupuesto de 90 min, así que no hizo falta la GPU (`GUIA_GPU.md`).
- La exactitud top-1 en val oscila ±5 puntos entre épocas, y eso hace poco fiable el "best.pt".
- CLIP (embeddings más las dos cabezas) tarda unos 10–12 s por modo (`logs/02_clip.log`).

## 4. Comparación con el "84 %" publicado (DrBerry, KDIR 2023)

**No es comparable de forma directa.**

- **Métrica y tarea.** El paper reporta **detección** con YOLOv5s: mAP50 84,7 % en su Tabla 2 (fila 3), y "accuracy 84 %, recall 91 %" en el resumen sin tabla de respaldo. Nosotros medimos **clasificación** de un recorte dado o de la imagen completa (`resultados/ficha_drberry.md` §5).
- **Partición.** Según la ficha, el paper evaluó sobre datos aumentados antes de partirlos (proyectos `gen-*`). Nosotros partimos por ráfagas, sin fuga.
- **Medimos el efecto de la fuga.** La misma sonda CLIP entrenada y evaluada con el split original de Roboflow, que tiene fuga por ráfagas, da en imagen completa **exactitud 0,91 con umbral (0,95 con argmax)**. Con nuestro split agrupado da 0,69–0,74. Es decir, la fuga infla la exactitud unos **20 puntos** (`drberry_image/eval_clip_probe_split_original_test/`). En recortes: 0,97 con fuga frente a 0,96 sin fuga.
- **Lo más parecido a "detectar bien".** Nuestro modo de recortes es una cota superior que supone localización perfecta: 0,96 de exactitud y 87/87 enfermas (inflado por el atajo de tamaño de alternaria; limpio: 52/52 con oídio + Heliothis). Para llegar ahí en el robot falta un detector de lesiones, que no entrenamos.

## 5. Fuera de DrBerry (¿cuánto cae?)

Cada celda es la tasa de alerta (k/n). En las filas **sanas**, la alerta es una **falsa alarma**. En las filas **enfermas**, la alerta es lo deseado: es la sensibilidad de sospecha, sin importar el diagnóstico. Cada modelo usa el umbral fijado en DrBerry.

| Conjunto (n) | Final (imagen, teselas 3x3) | Candidato post-hoc | YOLO 448 imagen | Cero-shot imagen | Sonda de recortes (umbral de recortes) |
|---|---|---|---|---|---|
| **Hojas sanas de campo, iNaturalist/Commons (60)** | **44/60 (73 %)** | **13/60 (22 %)** | 54/60 (90 %) | 18/60 (30 %) | 7/60 (12 %) |
| Arándano verde sin síntomas, recortes PlantDoc web (451) | 202 (45 %) | 217 (48 %) | 138 (31 %) | 291 (65 %) | 145 (32 %) |
| Arándano rojizo u otoñal, PlantDoc (192) | 162 (84 %) | 157 (82 %) | 164 (85 %) | 185 (96 %) | 110 (57 %) |
| Arándano sano de laboratorio, PlantVillage (1502; 160 hojas) | 69 (5 %) | 278 (19 %) | 743 (49 %) | 1343 (89 %) | 84 (6 %) |
| Hoja sana de otra especie, PlantDoc (725) | 451 (62 %) | 341 (47 %) | 545 (75 %) | 206 (28 %) | 236 (33 %) |
| Fresa asintomática (58) | 58 (100 %) | 55 (95 %) | 40 (69 %) | 58 (100 %) | 45 (78 %) |
| **Oídio en Vaccinium, campo (57)** | 53 (93 %) | 49 (86 %) | 51 (89 %) | 53 (93 %) | 43 (75 %) |
| **Roya en Vaccinium, campo (60), no entrenada** | 60 (100 %) | 60 (100 %) | 59 (98 %) | 60 (100 %) | 55 (92 %) |
| Orugas sobre Vaccinium, proxy de Heliothis (51) | 51 (100 %) | 50 (98 %) | 42 (82 %) | 51 (100 %) | 48 (94 %) |
| Arándano con síntomas o desorden, PlantDoc (89) | 47 (53 %) | 51 (57 %) | 34 (38 %) | 67 (75 %) | 38 (43 %) |
| Oídio en cerezo, calabaza y fresa (1052 / 1835 / 151) | 77 / 100 / 100 % | 96 / 99 / 92 % | 71 / 83 / 33 % | 100 / 100 / 84 % | 83 / 97 / 85 % |
| Tizón temprano (Alternaria) en papa, PV (1000) y PlantDoc (482) | 100 / 95 % | 100 / 95 % | 100 / 71 % | 100 / 100 % | 100 / 90 % |

Fuentes: `ood/eval/<modelo>/ood_metrics.json` y `tabla_ood.csv`. El manifiesto y el spec están en `ood/manifest_ood.csv` y `ood/spec_ood.json`, y salen de `raw/campo_ood/manifiesto.csv`, `resultados/secundarios/manifest_secundarios.csv` y los índices de fresa.

Lectura:

- **Sensibilidad.** Los modelos de imagen detectan como sospecha casi todo lo enfermo de campo: oídio 86–93 % y roya 98–100 %, aunque la roya no está entrenada. Eso es bueno para la regla "ante la duda, alerta".
- **Diagnóstico.** El diagnóstico fuera de dominio es pobre. El recall de la clase "oidio" en el oídio de campo es 0,42 en el final y 0,58 en el candidato, y en el oídio de fresa es 0,00 en ambos.
- **El punto crítico son las falsas alarmas en hojas sanas reales.**
  - El modelo final alerta en el 73 % de las hojas sanas de campo: 9 de 13 cultivadas y 35 de 47 silvestres.
  - En PlantVillage, de laboratorio con fondo uniforme, alerta solo en el 5 %. El fondo y la iluminación de campo son los que disparan la alarma.
  - El candidato post-hoc baja las falsas alarmas de campo al 22 %, con 2 de 13 cultivadas.
  - Separabilidad independiente del umbral, AUC de oídio de campo frente a sanas de campo: 0,83 en el final, 0,89 en el candidato y 0,24 en YOLO 448.
- **Hojas rojizas u otoñales.** Disparan alerta en el 57–96 % de los casos con cualquier modelo. Si la Sabana tiene brotes rojizos, serán una fuente fija de falsas alarmas (NO VERIFICADO en campo colombiano).
- **Representatividad.** Todas las fotos de campo son de zona templada del hemisferio norte y de Vaccinium mayormente silvestre (`resultados/ficha_campo_ood.md`). No hay nada andino. Alternaria de campo tiene 3 fotos y no es evaluable.

## 6. Estrés sintético de la cadena pantalla → cámara

Le apliqué al test congelado de imagen perturbaciones que imitan lo que pasa al fotografiar una pantalla. Los parámetros son SUPUESTOS: baja resolución de 256 px, desenfoque, reflejo, balance de blancos frío, ruido, giro de 7° con borde oscuro, JPEG de calidad 30 y la combinación de todas. Script en `scripts/stress_pantalla.py`.

| Modelo | Sens original → combinada | FP original → combinada | Peor condición individual |
|---|---|---|---|
| Final (teselas 3x3) | 0,80 → **0,65** | 0,21 → 0,64 | ruido: sens 0,69 |
| Candidato post-hoc | 0,91 → 0,74 | 0,14 → 0,21 | reflejo: FP 0,50 |
| YOLO11n-cls 224 | 0,91 → 0,72 | 0,57 → 0,21 | perspectiva: sens 0,76 |
| YOLO11n-cls 448 | 0,85 → 0,35 | 0,71 → 0,71 | combinada |

Fuentes: `tabla_stress.csv` y `stress/eval/<modelo>/<condicion>/metrics.json`.

- La combinación de perturbaciones le quita entre 15 y 50 puntos de sensibilidad a cualquier modelo. **Antes de la demo hay que medir con la cámara real del D1** (ver §10).

## 7. Galería de errores y patrones

Las galerías están en `drberry_*/galeria_<modelo>_test/galeria.html` (con PNG y `errores.csv`). Todas llevan la atribución DrBerry CC BY 4.0.

- **No detectados (modelo final): 11.** Son 10 de Alternaria y 1 de oídio, de solo **4 grupos**.
  - Son hojas verdes **sostenidas en la mano**, con cielo o plástico al fondo y puntos de Alternaria diminutos, invisibles a 224 px.
  - En una muestra visual de 10 fotos de train, varias Alternaria muestran decoloración rojiza o parda. Las de test que fallan son verdes. Es una observación de muestra, NO VERIFICADA.
- **Falsas alarmas (modelo final): 5, de solo 2 grupos.** Son hojas sanas **desprendidas sobre sustrato** (corteza de pino o paja), clasificadas como "alternaria" en 4 casos y "oídio" en 1.
  - Hipótesis: un atajo de contexto (hoja desprendida sobre sustrato → enfermedad). NO VERIFICADO: no hay etiqueta de fondo, y en una muestra de 10 fotos por clase no se ve una diferencia clara.
- **Confusiones entre enfermedades.** Las manchas pardo-rojizas de oídio se confunden con Heliothis (5 en el final; 4 de 4 en la sonda de recortes).
- **YOLO en recortes.** 6 falsas alarmas: hojas sanas amarillentas sobre paja → "oídio", y sanas en la mano → "heliothis".
- **Concentración de errores.** Los errores se concentran en pocas hojas físicas, así que el n efectivo es de grupos, no de fotos. Por eso los IC bootstrap por grupo son tan anchos.

## 8. Entregables

- **`resultados/detector.yaml`** (copia en `modelo_final/detector.yaml`) contiene:
  - el modelo final con su matriz de confusión normalizada, el recall por clase con IC, el binario enfermo-sano, el umbral, los hashes del test congelado y la latencia;
  - la detección por enfermedad;
  - los dos puntos de operación;
  - las comparaciones (cota de recortes, YOLO 224 y split con fuga);
  - el candidato post-hoc;
  - los bloques fuera de dominio y de estrés;
  - una sección `recomendacion_para_simulacion`: sensibilidad 0,80 [0,66–0,89], escenario pesimista 0,65, detección por clase oídio 0,95 / alternaria 0,29 / heliothis 1,00, y especificidad 0,64 en DrBerry frente a **0,27 en campo**.
- **`modelo_final/`**: pesos, umbrales, `README.md` de uso, las 5 imágenes de prueba con sus predicciones y la latencia en MPS y CPU.

  | Modelo | Latencia p50 MPS | Latencia p50 CPU |
  |---|---|---|
  | Final | 59 ms | 85 ms |
  | Candidato | 12 ms | 19 ms |
  | YOLO 224 | 7,6 ms | 5,4 ms |

  En las 5 imágenes, el final acierta 4 y da 1 falsa alarma (5_sana). MPS y CPU dan resultados idénticos.
- **Figura:** `figuras/evidencia_sens_fp.png` muestra sensibilidad y falsas alarmas con IC95 para las 8 condiciones clave.

## 9. Diapositiva de evidencia (propuesta)

1. **Prueba sin trampa.** 410 fotos DrBerry agrupadas en 139 ráfagas, sin fuga entre train y test. El test está congelado (68 imágenes y 21 grupos, sha256 `3ffbaca8…`) y verificado después de cada evaluación. El umbral se fijó sin mirar el test.
2. **Con la cámara del robot** (`modelo_camara`, 68 hojas de laboratorio mostradas al D1, solo 14 sanas), detecta **42 de 54 enfermas (78 %, IC por grupo 61–92 %)** con **4 de 14 falsas alarmas (29 %, IC 0–71 %)**. Alternaria es el punto débil: 3 de 14. *Versión anterior (modelo_final, imagen limpia, sin cámara): 43 de 54 = 80 % y 5 de 14 = 36 %.* NO mostrar "87/87 con 0/14": las lesiones de alternaria miden ~96 px y el tamaño solo las separa; la cifra limpia es 52/52 (oídio + Heliothis) con 0/14, cota superior con localización perfecta.
3. **La fuga infla unos 20 puntos.** El mismo modelo con el split original de Roboflow da 91 % de exactitud, frente a 69 % con el split agrupado. El 84 % publicado es mAP de detección con datos aumentados antes de partir, así que no es comparable.
4. **Fuera de DrBerry** (231 fotos de campo de iNaturalist y Commons), el robot alerta en el 93 % del oídio y en el 100 % de la roya, que no estaba entrenada. Pero también alerta en **44 de 60 hojas sanas**. Una sonda entrenada con recortes baja esa cifra a 13 de 60 (hallazgo post-hoc, a confirmar).
5. **Preferimos falsas alarmas.** Una falsa alarma cuesta unos 30 USD y un caso no detectado unos 2.160 USD/ha/semana (SUPUESTOS del equipo). Por eso el umbral apunta a 90 % de sensibilidad y el operario confirma cada alerta. La prueba sintética pantalla→cámara bajó la sensibilidad del modelo anterior a 65 %; la medición real con el D1 ya se hizo (punto 2). Limitación obligatoria: probado con 68 hojas de laboratorio, solo 14 sanas; el riesgo ambiental no está validado contra enfermedad real; el robot sugiere y el supervisor manda a un operario a confirmar.

## 10. Límites y pendientes

- **Datos.** Una finca en Perú, un día y 3 cámaras. La mayoría son hojas en la mano o desprendidas. Test de imagen con solo 14 sanas (unos 5 grupos) y 14 Alternaria (5 grupos), así que los IC son anchos. Clopper-Pearson ignora el agrupamiento y es optimista.
- **Clases.** El clasificador no ve antracnosis, Botrytis ni roya, que son las enfermedades del modelo ambiental. Heliothis es daño de insecto, no una enfermedad.
- **Pendiente principal: la medición real con el D1.**
  - Capturar con `pipeline/predict.py --camera <idx|url> --center-crop 0.7 --save-frames DIR --log DIR/alertas.jsonl` mientras la pantalla muestra las 68 fotos del test.
  - Etiquetar las capturas con la verdad del test.
  - Evaluar con `pipeline/predict_manifest.py` + `pipeline/evaluate.py`.
  - En esa misma corrida, confirmar o descartar el candidato post-hoc.
- **Para bajar las falsas alarmas de campo:**
  - recolectar fotos locales de hojas sanas (incluidos brotes rojizos) y recalibrar el umbral por dominio;
  - entrenar con hojas enteras recortadas (`convert.py --mode leaf-crops` sobre `raw/drberry_leafdet2`), que no se probó por tiempo.
- **YOLO** se evaluó con umbral de val, no con CV (5 entrenamientos por configuración). La comparación con CLIP es justa en val, no en OOF.
- **Supuestos.** Las perturbaciones de estrés, los umbrales phash y de ráfaga, el margen de recorte (10 %, mínimo 96 px), las descripciones del cero-shot y los costos de 30 USD y 2.160 USD son SUPUESTOS.

## 11. Reproducir (desde `datos/`, con `.venv/bin/python -I`)

```bash
bash resultados/ml/scripts/train_all.sh                                   # YOLO (secuencial, ~20 min en M4)
bash resultados/ml/scripts/eval_model.sh image clip_probe resultados/ml/drberry_image/clip probe   # umbral, eval y galería
.venv/bin/python -I pipeline/cv_clip_probe.py --splits-dir resultados/ml/drberry_image/splits --out resultados/ml/drberry_image/clip_cv_tiles3 \
    --tiles 3 --cache resultados/ml/drberry_image/clip_tiles3/embeddings_cache.npz
.venv/bin/python -I resultados/ml/scripts/build_ood_manifests.py && .venv/bin/python -I pipeline/predict_manifest.py ...   # ver logs/05*.log
.venv/bin/python -I resultados/ml/scripts/stress_pantalla.py && bash resultados/ml/scripts/eval_stress.sh
.venv/bin/python -I resultados/ml/scripts/detector_extras.py   # y luego pipeline/export_detector_yaml.py (comando en reportes/entrenamiento-evaluacion.md)
.venv/bin/python -I resultados/ml/scripts/resumen_tablas.py && .venv/bin/python -I resultados/ml/scripts/figura_evidencia.py
```

Los comandos exactos de cada paso están en `logs/` (un log por paso, numerados del 01 al 07).

## 12. Licencias y citas

- **DrBerry:** CC BY 4.0 (Roboflow Universe, workspace `drberry`, `drberry-original-data` v1; URL según el `data.yaml`, que no abrí). No se redistribuye. Las imágenes de `modelo_final/imagenes_prueba` y `stress/imgs` son de uso interno.
- **iNaturalist y Commons:** licencias por foto en `raw/campo_ood/manifiesto.csv`; 158 son CC BY-NC, aptas solo para evaluación interna.
- **PlantDoc:** CC BY 4.0, con fotos de stock de terceros.
- **PlantVillage:** CC BY-SA 3.0.
- **Fresa:** Afzaal 2021 es CC BY 4.0 y Mendeley k2ptxmfjhj es CC BY-NC 4.0.
- **Software y pesos:** Ultralytics y YOLO11 son AGPL-3.0. open_clip es MIT y los pesos laion ViT-B-32 son MIT (según `reportes/preparacion-entorno.md`).

## 13. Notas del verificador adversario (agente verificacion-ml)

Detalle y evidencia en `reportes/verificacion-ml.md`. Las cifras de las secciones 3 a 6 se recalcularon desde las predicciones guardadas y coinciden. Lo que cambia es cómo leerlas.

- **Recortes (cota superior).** Los 289 recortes de Alternaria miden exactamente 96x96 px (el mínimo del convertidor, ampliados a 224), mientras que las otras clases miden entre 158 y 1024 px. Solo con la nitidez o el tamaño del recorte se separa Alternaria de sana con AUC 0,99 en todo el conjunto y 1,00 en test. Por eso el "35/35 de Alternaria" y parte del "87/87" de la §3.1 no prueban que el modelo vea la lesión. La parte limpia es Heliothis + oídio: 52/52 detectadas y 0/14 falsas alarmas (el tamaño no separa esas clases de sana: AUC 0,52 y 0,55).
- **IC de los recortes.** Son 87 recortes de 54 imágenes y 19 grupos. Con 19 de 19 grupos acertados, el límite inferior a nivel de grupo es unos 0,82, no 0,96.
- **Especificidad "de campo".** Las 60 hojas sanas de iNaturalist son sobre todo fotos de planta entera con fruto, flor y manos, de Vaccinium silvestre templado. Su 73 % de alertas mide cambio de dominio de encuadre, no la especificidad esperada en una finca. Se corrigió la etiqueta correspondiente en `detector.yaml`.
- **"El umbral se fijó sin mirar el test" (§9, punto 1).** El umbral sí salió de las predicciones OOF, pero el paso de val a validación cruzada y la idea de las teselas vinieron después de ver resultados de test (hubo al menos 9 evaluaciones en test, entre recortes e imagen, antes del modelo final). Esta mirada ya está declarada en la §2; conviene repetirla en la diapositiva.
- **Comparación con el 84 %.** El paper también reporta mAP50 de 94,1 % (YOLOv5s) y 96,1 % (YOLOv5m) en su Tabla 3. Que el paper aumentó antes de partir es una inferencia: el texto no describe el orden.
- **Fragilidad.** Con el umbral 0,7459 (el siguiente puntaje observado) el modelo final da 4/14 falsas alarmas en lugar de 5/14, con la misma sensibilidad 43/54. Las 5 falsas alarmas vienen de 2 de los 5 grupos de sanas.
