# Reporte del agente entrenamiento-evaluacion

Fecha: 2026-10-23. Máquina: Mac M4 (MPS), venv `.venv` con Python 3.11.15. El documento principal es **`resultados/ml/RESULTADOS.md`**: trae las tablas completas y la diapositiva de evidencia. Este reporte resume el trabajo y lo que queda pendiente.

## Qué hice

1. **Preparé los datos de DrBerry** (`drberry-original-data` v1, la versión sin aumentar; `raw/drberry/...-yolov8`).
   - Convertí el dataset a recortes por caja (737) y a imágenes completas con su clase dominante (410).
   - Agrupé las imágenes con phash y con las ráfagas de 10 s, lo que dejó 139 grupos.
   - Hice un split 70/15/15 agrupado y estratificado. El test quedó **congelado** y verificado después de cada evaluación.
   - El modo imagen usa **las mismas fotos de test** que el modo recortes.
2. **Líneas base CLIP** (ViT-B-32 laion2b): cero-shot y sonda lineal, en los dos modos.
   - Agregué rasgos de teselas (2x2 y 3x3) para las lesiones diminutas.
   - Agregué validación cruzada agrupada de 5 pliegues sobre train+val para elegir C y el umbral.
3. **YOLO11n-cls en MPS.**
   - Medí la primera época antes de entrenar: 4,1 s en recortes a 224, 4,1 s en imagen a 224 y 7,1 s en imagen a 448.
   - Entrené recortes a 224 e imagen a 224, 448 y 640, con un máximo de 80 épocas y paciencia 25. El total fue de unos 19 min, así que no hizo falta GPU. Dejé `GUIA_GPU.md` con comandos opcionales.
4. **Umbral.** Lo fijé en val, o en OOF, para sensibilidad de enfermedad ≥ 0,90 con el mínimo de falsas positivas. También calculé el criterio por clase. En test solo informé.
5. **Evaluación en el test congelado.** Usé bootstrap por grupos (1000 réplicas) y Clopper-Pearson para CLIP cero-shot, la sonda y YOLO.
   - Medí cuánto infla la fuga del split original de Roboflow y comparé con el 84 % publicado.
6. **Evaluación fuera de DrBerry** sobre 10.360 imágenes y 19 categorías:
   - campo OOD de iNaturalist y Commons;
   - PlantDoc (imágenes completas y recortes);
   - PlantVillage;
   - fresa (Afzaal 2021 y Mendeley).

   Las corrí con 9 combinaciones de modelo y umbral.
7. **Estrés sintético** de la cadena pantalla → cámara: 8 perturbaciones sobre el test, con 5 modelos.
8. **Galerías de errores** (HTML y PNG) para cada modelo y análisis de patrones.
9. **Entregables:**
   - `resultados/detector.yaml`;
   - `resultados/ml/modelo_final/`, con `predict.py` probado sobre 5 imágenes y la latencia en MPS y CPU;
   - la figura de evidencia;
   - `RESULTADOS.md`.

No usé la API key de Roboflow, porque este rol no descarga nada. Verifiqué con `grep -F -f .secrets/roboflow_api_key`, sin imprimirla, que no aparece en `resultados/`, `pipeline/` ni `reportes/`. No descargué archivos ni abrí URLs.

## Cambios y correcciones al pipeline (documentados en `pipeline/README.md`)

| Cambio | Tipo | Motivo |
|---|---|---|
| `split.py`: `grupos_por_split_y_clase_mayoritaria` | **Bug** | Usaba la etiqueta del primer ítem de cada grupo, no la mayoritaria. Solo afectaba al resumen; los splits y el hash del test no cambian. |
| `split.py --assign-from DIR` | Nueva opción | Hace que el modo imagen herede el split de recortes por `source_id`, con las mismas fotos de test. |
| `clip_baseline.py --tiles K` (+ `predict.py`, `predict_manifest.py`) | Nueva opción | Rasgos `[global, media, máx]` de teselas. El cabezal guarda `tiles` y la inferencia lo respeta. |
| `train_yolo_cls.py --extra CLAVE=VALOR` | Nueva opción | Pasa hiperparámetros extra a Ultralytics. |
| `export_detector_yaml.py --umbral-conjunto`, `--extra-yaml` | **Bug** + opción | Antes escribía siempre "validacion" como conjunto del umbral. Ahora se puede fusionar secciones extra sin pisar claves. |
| `cv_clip_probe.py` | Nuevo módulo | Validación cruzada agrupada para C y el umbral, y modelo final en train+val. |
| `predict_manifest.py` | Nuevo módulo | Predicción en lote sobre cualquier CSV. Comparte embeddings CLIP. Verifiqué que da probabilidades idénticas (máx. \|Δp\| = 0) a las de `train_yolo_cls.py` y `cv_clip_probe.py` en el test. |
| `ood_eval.py` | Nuevo módulo | Tasa de alarma por categoría OOD con IC, recall de la clase esperada y AUC frente a una referencia sana. |
| Pruebas | Nuevas | `tests/test_ood.py` (3) y `test_split.py::test_assign_from_reuses_source_split`. Resultado: **45 passed, 2 skipped** y, con `RUN_SLOW=1`, **47 passed**. |

## Archivos producidos (todos bajo `/Users/santiagosantafe/Downloads/SabanaHack/datos/`)

- **Documentos y figuras:**
  - `resultados/ml/RESULTADOS.md`: tablas, lectura y diapositiva de evidencia.
  - `resultados/ml/figuras/evidencia_sens_fp.png`.
  - `resultados/ml/GUIA_GPU.md`.
  - `resultados/ml/protocolo_seleccion.json`.
- **Detector:** `resultados/detector.yaml`, para la simulación (copia en `resultados/ml/modelo_final/detector.yaml`). Se regenera con:

  ```bash
  .venv/bin/python -I resultados/ml/scripts/detector_extras.py
  W=resultados/ml/drberry_image; .venv/bin/python -I pipeline/export_detector_yaml.py --metrics $W/eval_clip_cv_tiles3_test/metrics.json \
    --threshold $W/umbral_clip_cv_tiles3.json --split-summary $W/splits/split_summary.json --latency resultados/ml/modelo_final/latencia_mps.json \
    --umbral-conjunto "OOF validación cruzada agrupada 5 pliegues sobre train+val (342 imágenes, 118 grupos)" \
    --dataset-name "DrBerry drberry-original-data v1 (imagen completa, clase dominante)" --dataset-license "CC BY 4.0" \
    --extra-yaml resultados/ml/detector_extras.yaml --out resultados/detector.yaml   # (+ --model-name, --data-notes, --warning: ver RESULTADOS.md)
  ```
- **Modelos:** `resultados/ml/modelo_final/` (pesos, umbrales, README, 5 imágenes, predicciones y latencias) y dos alternativas en subcarpetas.
- **Tablas:** `resultados/ml/tabla_drberry_test.csv`, `tabla_ood.csv` y `tabla_stress.csv`.
- **Datos y corridas:**
  - `resultados/ml/drberry_crops/` y `drberry_image/`: conversión, dedup, splits congelados, CLIP, runs de YOLO, `umbral_*.json`, `eval_*`, galerías y semillas.
  - `resultados/ml/ood/`: manifiesto, spec, predicciones y evaluación.
  - `resultados/ml/stress/`: imágenes perturbadas de uso interno, predicciones y evaluación.
- **Scripts y logs:**
  - `resultados/ml/scripts/`: `train_all.sh`, `eval_model.sh`, `build_ood_manifests.py`, `stress_pantalla.py`, `eval_stress.sh`, `resumen_tablas.py`, `detector_extras.py` y `figura_evidencia.py`.
  - `resultados/ml/logs/`: un log por paso, del 01 al 07.
- **Pipeline:** `predict_manifest.py`, `ood_eval.py`, `cv_clip_probe.py` y `tests/test_ood.py` son nuevos; `split.py`, `clip_baseline.py`, `predict.py`, `train_yolo_cls.py`, `export_detector_yaml.py`, `README.md` y `tests/test_split.py` están modificados.

## Resultados clave

Detalle con IC en `RESULTADOS.md`.

- **Recortes de caja** (localización perfecta, cota superior). Sonda CLIP: exactitud 0,96, sensibilidad 87/87 [IC95 CP 0,96–1,00] y falsas positivas 0/14 [0–0,23]. YOLO11n-cls tiene la misma sensibilidad pero 6/14 falsas positivas.
- **Imagen completa, modelo final** (sonda CLIP con teselas 3x3, elegida en val y en OOF con el protocolo registrado):
  - sensibilidad 43/54 = 0,80 [0,66–0,89] y falsas positivas 5/14 = 0,36 [0,13–0,65];
  - detección por enfermedad: alternaria 4/14, heliothis 18/18, oídio 21/22;
  - con 5 semillas de CV: sensibilidad 0,80–0,81 y falsas positivas 0,36–0,50.
- **El umbral de val** (25 grupos, 10 sanas) no se sostuvo en test en 4 de 5 modelos de imagen. La validación cruzada OOF (342 imágenes) da la cifra realista: unas 33 % de falsas positivas con 90 % de sensibilidad.
- **YOLO11n-cls en imagen** (224/448/640): sensibilidad 0,85–0,91 con falsas positivas de 0,57–0,71 en test.
- **Candidato post-hoc:** la sonda de recortes aplicada a la imagen. Da sensibilidad 49/54 = 0,91 con falsas positivas 2/14 en test, y 13/60 falsas alarmas en hojas sanas de campo, frente a 44/60 del final. Lo evalué *después* de la selección y queda como hipótesis a confirmar con capturas del D1.
- **Fuga:** con el split original de Roboflow, la misma sonda da 0,91 de exactitud en imagen, frente a 0,69 con el split agrupado.
- **Comparación con el 84 % publicado:** no es comparable. El paper reporta mAP50 de detección (84,7 % en la Tabla 2) sobre datos aumentados antes de partir; nosotros medimos clasificación con split agrupado.
- **Fuera de DrBerry:**
  - Los modelos de imagen alertan en el 86–93 % del oídio de campo y en el 98–100 % de la roya, aunque la roya no está entrenada.
  - Las falsas alarmas en hojas sanas de campo van del 22 % al 90 % según el modelo; el final está en 73 %.
  - En PlantVillage, de laboratorio, el final alerta solo en el 5 %. El dominio de campo es el problema.
- **Estrés pantalla → cámara (sintético):** la sensibilidad del final baja de 0,80 a 0,65 con todas las perturbaciones combinadas.
- **Latencia p50** (Mac M4): el final tarda 59 ms en MPS y 85 ms en CPU; el candidato, 12 y 19 ms; YOLO 224, 7,6 y 5,4 ms.

## Fuentes

- Locales:
  - `resultados/ficha_drberry.md`, `resultados/drberry_imagenes.csv`, `resultados/ficha_campo_ood.md` y `resultados/ficha_secundarios.md`;
  - `raw/campo_ood/manifiesto.csv`, `resultados/secundarios/manifest_secundarios.csv` y los índices de `raw/fresa_*`;
  - `reportes/codigo-pipeline-imagenes.md` y `reportes/preparacion-entorno.md`;
  - `simulacion/parametros.yaml`, del que leí qué parámetros del clasificador espera la simulación.
- No abrí URLs web. La URL de DrBerry viene del `data.yaml` de la exportación.

## Límites

- **Datos.** Una finca en Perú y un día. El test tiene 68 imágenes en 21 grupos, con 14 sanas en unos 5 grupos y 14 Alternaria en 5 grupos, así que los IC son anchos. Clopper-Pearson ignora el agrupamiento y es optimista.
- **Cadena real.** No medí la cadena pantalla → cámara del D1, porque no tengo acceso al robot. El estrés es sintético y sus parámetros son SUPUESTOS.
- **Comparación YOLO frente a CLIP.** Es justa en val pero no en OOF, porque YOLO no tiene validación cruzada.
- **Mirada al test.** El paso a validación cruzada y el candidato post-hoc se decidieron o evaluaron después de ver test. Lo declaro en `protocolo_seleccion.json`, en `detector.yaml` y en `RESULTADOS.md`.
- **Clases.** Las clases del clasificador no cubren antracnosis, Botrytis ni roya.
- **Representatividad OOD.** Las fotos de campo son de zona templada y casi todas de Vaccinium silvestre; no hay datos andinos. 158 fotos son CC BY-NC y solo sirven para evaluación interna.

## Pendientes (por prioridad)

1. **Medir con el D1 real.**
   - Usar `pipeline/predict.py --camera ... --center-crop 0.7 --save-frames DIR --log DIR/alertas.jsonl` mientras la pantalla muestra las 68 fotos del test de imagen.
   - Etiquetar las capturas y evaluarlas con `predict_manifest.py` + `evaluate.py`.
   - Con eso se decide entre el modelo final y el candidato post-hoc con datos nuevos.
2. **Recolectar fotos locales de hojas sanas,** incluidos brotes rojizos, para recalibrar el umbral de campo. Es la mayor fuente de falsas alarmas.
3. **Probar `convert.py --mode leaf-crops`** sobre `raw/drberry_leafdet2`, que da hojas de Alternaria sin el atajo de escala. No lo hice por tiempo.
4. **(Opcional) Validación cruzada de YOLO** (5 entrenamientos por configuración) para compararlo con CLIP en OOF.

## Re-verificación (2026-10-23 18:35, nueva invocación del mismo rol)

El workflow volvió a lanzar este rol cuando el trabajo ya estaba terminado (salidas de las 18:03 a las 18:31). No volví a entrenar, para no pisar los resultados ni el test congelado. Solo verifiqué:
- `pytest pipeline/tests -q`: 45 passed, 2 skipped.
- `split.py --verify`: recortes intacto (sha256 ed56f4e7…, 101 ítems, 21 grupos) e imagen intacto (sha256 3ffbaca8…, 68 ítems, 21 grupos).
- `predict.py` con `modelo_final/clip_probe_tiles3.joblib` sobre las 5 imágenes de prueba: 4 de 5 aciertan; `5_sana.jpg` da falsa alarma (p_enfermedad 0,90 ≥ umbral 0,737). Es lo mismo que la corrida anterior.
- La API key no aparece en `resultados/`, `pipeline/` ni `reportes/` (búsqueda con grep -F -f, sin imprimirla).
