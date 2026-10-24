# Pipeline de imágenes: Sabana Hack, reto "Berry Good Idea"

Este pipeline convierte un dataset de detección (DrBerry) en un clasificador de hojas de arándano con cuatro clases: `sana`, `oidio`, `alternaria` y `heliothis`. Con eso:

- arma las líneas base,
- fija el umbral de "sospecha" en validación,
- evalúa con intervalos en el test congelado,
- exporta `resultados/detector.yaml` para la simulación,
- y da la inferencia para la demo con el AgiBot D1.

Todo funciona por línea de comandos (`argparse`, `--help` en cada script) y con el venv del equipo:

```bash
D=/Users/santiagosantafe/Downloads/SabanaHack/datos
PY=$D/.venv/bin/python
cd $D            # NUNCA dentro de raw/ (contenido no confiable)
$PY -I pipeline/<script>.py --help
```

Ejecutamos siempre con `-I` (modo aislado). Cada script agrega su propia carpeta a `sys.path` para importar `common.py` y `metrics.py`.

## Flujo

```
raw/drberry/...-yolov8 (images/ + labels/ + data.yaml)
   │ convert.py        → manifest.csv (un ítem por recorte/imagen, con source_id de la imagen de ORIGEN)
   │ dedup.py          → groups.csv (casi-duplicados phash + ráfagas externas → mismo grupo)
   │ split.py          → train/val/test.csv 70/15/15 agrupado y estratificado; test CONGELADO (sha256)
   │                     (+ --materialize: carpeta train/val/test/<clase>/ para Ultralytics)
   ├─ clip_baseline.py → predicciones_{zeroshot,probe}_{train,val,test}.csv + clip_*.joblib
   └─ train_yolo_cls.py→ run Ultralytics + predicciones_yolo_{val,test}.csv
   │ threshold.py      → umbral elegido en VALIDACIÓN (sensibilidad ≥ 0.90) + curva
   │ evaluate.py       → metrics.json (+ IC bootstrap 1000), confusion_matrix.png, pr_curve.png  [TEST]
   │ gallery.py        → galeria.html + PNG de falsas alarmas / no detectados / confusiones
   │ export_detector_yaml.py → resultados/detector.yaml (para simulacion/)
   └ predict.py        → inferencia imagen/carpeta/cámara o flujo RTSP, con latencia (demo)
```

Para correr todo de una vez, con salida por defecto en `pipeline/work/drberry_<modo>/`:

```bash
bash pipeline/run_drberry.sh                       # recortes por caja
bash pipeline/run_drberry.sh image                 # imagen completa (clase dominante)
TRAIN_YOLO=1 MAX_MIN=25 bash pipeline/run_drberry.sh
EXPORT_DETECTOR=1 MODEL_FOR_EXPORT=probe bash pipeline/run_drberry.sh   # escribe resultados/detector.yaml
```

## Módulos

| Script | Qué hace | Salidas principales |
|---|---|---|
| `convert.py` | Pasa de YOLO a clasificación. Tiene cuatro modos: `crops` (un recorte por caja, con `--margin`, `--min-crop-px`, `--min-box-px`, `--square` y `--max-side`), `image` (clase dominante de la imagen; `--skip-multiclass`), `leaf-crops` (recorta las cajas de hoja y las etiqueta con la lesión que tienen dentro) y `folders` (dataset ya separado por carpetas de clase). Reconoce la estructura de Roboflow (`split/images`), la de Ultralytics (`images/split`) y la plana; lee polígonos y aplica EXIF. Las clases se normalizan a minúsculas sin tildes; `--class-map` sirve para renombrarlas. | `manifest.csv`, `crops/<clase>/*.jpg`, `convert_summary.json` |
| `dedup.py` | Calcula el phash de cada imagen de ORIGEN y une los pares con Hamming ≤ `--threshold` usando union-find. Opcionalmente fusiona grupos externos (`--extra-groups-csv`), por ejemplo las ráfagas de `resultados/drberry_imagenes.csv`. | `groups.csv`, `duplicates_report.{json,md}`, `duplicate_pairs.png` |
| `split.py` | Reparte 70/15/15 por GRUPO. Estratifica por la clase mayoritaria del grupo, usa semilla fija y se queda con el más estratificado de `--trials` órdenes. Comprueba que ningún grupo ni ninguna fuente caiga en dos splits. Deja `test.csv` en solo lectura con `test_frozen.json` (sha256 del archivo y del contenido) y se niega a sobrescribir un test distinto si no se pasa `--force`. `--verify DIR` revisa que el test siga intacto. | `train/val/test.csv`, `split_summary.json`, `test_frozen.json` |
| `clip_baseline.py` | Línea base con open_clip ViT-B-32 (laion2b_s34b_b79k, caché local `pesos/open_clip`). Tiene dos modos: cero-shot (7 plantillas × 2–3 descripciones por clase) y sonda lineal (estandarización + regresión logística `class_weight=balanced`, con C elegido por macro-F1 en val). Los embeddings quedan en caché. | `predicciones_*.csv`, `clip_{zeroshot,probe}.joblib`, `clip_resumen.json` |
| `train_yolo_cls.py` | Entrena yolo11n-cls (o `--model yolov8n-cls.pt`) en MPS. Al terminar la 1.ª época estima el tiempo total. `--max-minutes` corta limpiamente y el run se reanuda con `--resume RUN_DIR`, que usa `weights/resume.pt`; `--estimate-only` hace una sola época. Con `--splits-dir` escribe las predicciones de val y test usando `best.pt`. | run de Ultralytics, `train_status.json`, `predicciones_yolo_*.csv` |
| `evaluate.py` | Calcula la matriz de confusión (conteos y normalizada), P/R/F1 por clase, exactitud, macro-F1, exactitud balanceada y el binario enfermo-vs-sano (sensibilidad, especificidad, tasa FP, FDR, VPP, VPN). Da IC bootstrap de 1000 réplicas de todas las métricas, remuestreando GRUPOS si existe la columna `group`, y además Clopper-Pearson. Incluye curva PR, AP y AUC. Evalúa con argmax y, si se le pasa umbral, también con la regla de umbral. | `metrics.json`, `per_class.csv`, `confusion_matrix.png`, `pr_curve.png` |
| `threshold.py` | Fija el umbral en VALIDACIÓN: busca la sensibilidad ≥ objetivo (0.90) con el mínimo de falsas alarmas y, si hay empate, se queda con el más bajo para ganar sensibilidad. Usa el punto medio con el puntaje siguiente. `--criterio por_clase` exige que cada enfermedad cumpla el objetivo por separado. `--test-pred` solo informa el resultado en test. | `threshold.json`, `*_curva.csv`, `*_curva.png` |
| `gallery.py` | Arma la galería de falsas alarmas, no detectados y confusiones entre enfermedades, ordenada por la confianza del error. El HTML es autocontenido y se adapta al modo oscuro. | `galeria.html`, `<tipo>.png`, `errores.csv` |
| `export_detector_yaml.py` | Escribe `resultados/detector.yaml` con la matriz normalizada, el recall por clase con IC, la sensibilidad y la tasa FP binarias con IC, el umbral, el origen de los datos (dataset, licencia, hash del test congelado, semilla), la fecha y la latencia (si se le pasa). | `resultados/detector.yaml` |
| `predict.py` | Inferencia sobre `--image`, `--dir` o `--camera` (índice o URL rtsp/http, que se guarda sin credenciales en el log). Devuelve clase, confianza, `p_enfermedad`, `sospecha` y latencia (preproceso, inferencia y total). Opciones: `--roi`/`--center-crop` para recortar la pantalla que mira el robot, `--log` JSONL para el registro de alertas, `--save-frames` y `--bench N` (p50/p95). | JSON por línea; `--bench-out` |
| `cv_clip_probe.py` | Sonda CLIP con validación cruzada AGRUPADA (`StratifiedGroupKFold`, 5 pliegues) sobre train+val: elige C por macro-F1 fuera de pliegue (OOF), escribe las predicciones OOF como `predicciones_cvprobe_val.csv` (para que `threshold.py` fije el umbral con ~4x más datos que val) y entrena el modelo final en train+val. Acepta `--tiles`. | `predicciones_cvprobe_{val,test}.csv`, `clip_probe.joblib`, `cv_resumen.json` |
| `predict_manifest.py` | Predicciones en lote sobre cualquier CSV (`path`, etiqueta, `group`), con uno o varios modelos `.pt`/`.joblib`; los cabezales CLIP comparten embeddings (caché `.npz`). Lee las imágenes con PIL + EXIF como `predict.py`. Omite y lista las ilegibles. | `predicciones_<nombre>.csv`, `omitidas.csv` |
| `ood_eval.py` | Evaluación fuera de dominio: tasa de alarma por categoría con IC (Clopper-Pearson y bootstrap por grupo), recall de la clase esperada y AUC frente a una referencia sana del mismo dominio, según un `--spec` JSON (`esperado: sana|enfermedad`). | `ood_metrics.json`, `ood_tabla.csv` |

Módulos de apoyo: `common.py` (convenciones, E/S, regla de decisión) y `metrics.py` (métricas puras y selección de umbral).

### Cambios del agente entrenamiento-evaluacion (2026-10-23)

- `split.py --assign-from DIR`: reutiliza la asignación `source_id -> split` de otro split (así el modo imagen usa exactamente las mismas fotos de test que el modo recortes). Corrección: `grupos_por_split_y_clase_mayoritaria` contaba la etiqueta del primer ítem del grupo, no la mayoritaria.
- `clip_baseline.py --tiles K`: rasgos `[global, media, máx]` de una rejilla KxK (para lesiones diminutas); el cabezal guarda `tiles` y `predict.py`/`predict_manifest.py` lo respetan. El cero-shot usa solo la parte global.
- `train_yolo_cls.py --extra CLAVE=VALOR`: pasa argumentos extra a `model.train` (p. ej. `cos_lr=True`).
- `export_detector_yaml.py --umbral-conjunto` (antes decía siempre "validacion") y `--extra-yaml` (fusiona secciones adicionales sin pisar claves existentes).
- Nuevos `cv_clip_probe.py`, `predict_manifest.py`, `ood_eval.py` y pruebas `tests/test_ood.py`, `test_split.py::test_assign_from_reuses_source_split`.
- Corridas reales y resultados: `resultados/ml/RESULTADOS.md`.

## Formatos (contratos entre módulos)

- **Manifiesto** (`convert.py`): `item_id, path, label, source_id, source_path, source_split, dataset, mode, box_index, orig_class, box_*, crop_*, img_w, img_h, n_boxes_image, multiclass_image`.
- **Splits** (`split.py`): el manifiesto más `group` y `split`.
- **Predicciones** (todos los modelos): `path, y_true, y_pred, p_<clase>…`, más `item_id, source_id, group, split, model`. `evaluate`, `threshold` y `gallery` solo dependen de este formato. Para agregar otro modelo basta con escribir este CSV.
- **Regla de decisión**: el puntaje de enfermedad es `1 − p(sana)`. Hay sospecha si puntaje ≥ umbral, y en ese caso la clase decidida es la enfermedad más probable. Sin umbral se decide por argmax. `predict.py` aplica la misma regla (está probada).

## Decisiones y supuestos (cámbienlos por CLI)

- La semilla del split es `20261023`. Las proporciones son 70/15/15 y se prueban 200 órdenes.
- El umbral de casi-duplicado phash es **6/64 bits (SUPUESTO heurístico)**. Revisen `duplicate_pairs.png`. En DrBerry se fusionan además las ráfagas (`grupo_rafaga`, umbral de 10 s; SUPUESTO del agente de adquisición).
- Los recortes usan margen del 10 %, lado mínimo de 96 px y forma cuadrada (SUPUESTO). Las cajas de Alternaria son lesiones de unos 25 px en 1024 px, así que sin `--min-crop-px` el recorte casi no tendría contexto.
- Las descripciones del cero-shot están en inglés y son un **SUPUESTO de redacción**. Se pueden cambiar con `--prompts-json`.
- El objetivo de sensibilidad es 0.90, por la preferencia del equipo de falsas alarmas (~30 USD) frente a no detectados (~2.160 USD/ha/semana); los dos costos son **SUPUESTOS del equipo**.

## Advertencias metodológicas (para "Evidencia y validación")

1. **Atajo de escala en `crops`.** Las cajas de Alternaria encierran lesiones diminutas y las de las demás clases encierran la hoja completa (ver `resultados/ficha_drberry.md`). Un clasificador de recortes puede aprender "recorte pequeño = Alternaria". Además, los recortes suponen que una persona ya localizó la lesión, es decir, una localización perfecta.
   - Para estimar lo que vería el robot conviene reportar también el modo `image`, o usar `leaf-crops` sobre `raw/drberry_leafdet2`.
   - En la prueba de humo de este agente (scratchpad, no oficial), la sonda CLIP con la regla de umbral dio exactitud 0.96 con recortes y 0.72 con imagen completa sobre el test agrupado.
2. **Muestra pequeña.** El test de recortes tiene 21 grupos y solo 4 son de Alternaria por clase mayoritaria. Hay que reportar siempre los IC.
   - Si la métrica es 0 o 1, el bootstrap colapsa (IC [1, 1]). En ese caso usen el Clopper-Pearson, que `metrics.json` y `detector.yaml` también incluyen.
   - Clopper-Pearson supone independencia entre ítems, así que con ráfagas es optimista.
3. **El test congelado no se toca** para elegir modelos, hiperparámetros ni umbrales. El umbral se fija en val y en test solo se informa. `split.py --verify` sirve de evidencia de que el test no cambió.
4. **Validación sana pequeña.** En val hay de 9 a 12 hojas sanas, así que la tasa de falsas alarmas estimada es muy imprecisa (`threshold.py` lo avisa).
5. **Cadena pantalla → cámara del D1.** No se mide con este dataset. Hay que capturar frames con `predict.py --camera ... --save-frames DIR --log ...`, etiquetarlos y evaluarlos con el mismo `evaluate.py`; para eso basta un CSV de predicciones con `y_true`.
6. **Representatividad.** Los datos son de una finca en Perú, tomados en un solo día, con hojas casi siempre desprendidas o en la mano. Los resultados no se pueden extrapolar a campo colombiano sin validación local.

## Pruebas

```bash
/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I -m pytest /Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/tests -q
# Integración real (carga CLIP, entrena YOLO 2 épocas en CPU con imágenes sintéticas):
RUN_SLOW=1 /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I -m pytest /Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/tests -q
```

Las pruebas usan solo imágenes sintéticas generadas al vuelo (45 rápidas + 2 lentas; con `RUN_SLOW=1` pasan las 47). Cubren:

- la conversión: geometría de recortes, polígonos, líneas inválidas, modos y estructuras de carpetas;
- la deduplicación: casi-duplicados y grupos externos;
- el split: sin fuga, reproducible con la semilla, proporciones, estratificación, protección y verificación del test congelado, materialización;
- las métricas en casos conocidos: P/R/F1, binario, Clopper-Pearson, bootstrap y umbral;
- la cadena threshold → evaluate → gallery → export;
- `predict.py` con un clasificador falso;
- el presupuesto de tiempo de YOLO con un entrenador falso.

## Licencias y seguridad

- **DrBerry:** CC BY 4.0. Hay que citarlo (Roboflow Universe, workspace `drberry`) y no redistribuirlo. Las galerías llevan la atribución.
- **Software y pesos:** Ultralytics y los pesos YOLO11 son AGPL-3.0; open_clip es MIT; los pesos laion CLIP-ViT-B-32 son MIT según los metadatos de HF (ver `reportes/preparacion-entorno.md`).
- **Archivos `.joblib`:** son pickles. Carguen solo los que genera este pipeline.
- **API key de Roboflow:** este pipeline no la usa. Las descargas son tarea de los agentes de adquisición.
- **Red:** los scripts fijan `YOLO_OFFLINE=1` (y `HF_HUB_OFFLINE=1` si los pesos CLIP ya están en caché) solo dentro de su proceso, para no descargar nada ni enviar analítica. `--allow-online` lo desactiva.
