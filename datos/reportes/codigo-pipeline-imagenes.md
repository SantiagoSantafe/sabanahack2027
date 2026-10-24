# Reporte del agente codigo-pipeline-imagenes

Fecha: 2026-10-23. Máquina: Mac con Apple M4 y venv `.venv` (Python 3.11.15, torch 2.14.1, ultralytics 8.4.184, open_clip 3.3.0).

## Qué hice

1. Escribí el pipeline de imágenes en `pipeline/`. Son 10 módulos CLI (argparse y type hints), dos módulos de apoyo (`common.py` y `metrics.py`), el script `run_drberry.sh` que corre todo y un `README.md` con el flujo, los formatos, los supuestos y las advertencias. Todo se ejecuta con `python -I`.
2. Escribí 43 pruebas pytest en `pipeline/tests/`. Usan **solo imágenes sintéticas generadas al vuelo**. Las 41 rápidas pasan en unos 3 s. Las 2 lentas (`RUN_SLOW=1`) cargan CLIP real y entrenan, reanudan y predicen con YOLO en CPU; también pasan, en unos 9 s.
3. Validé el código contra los datos reales de DrBerry. Corrí en el **scratchpad**, no en las carpetas del proyecto, para no congelar un test por el equipo. Hice dos corridas completas con `run_drberry.sh`, en modo recortes y en modo imagen completa, más una corrida manual previa.
4. Probé YOLO en **MPS** con el presupuesto de tiempo y la reanudación, y medí la latencia de `predict.py` con pesos YOLO y con la sonda CLIP.

No usé la API key de Roboflow, porque este rol no descarga nada. Verifiqué con `grep` que no aparece en `pipeline/` ni en `reportes/`.

## Archivos producidos

- Ruta base: `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/`.
- Módulos pedidos: `convert.py`, `dedup.py`, `split.py`, `clip_baseline.py`, `train_yolo_cls.py`, `evaluate.py`, `threshold.py`, `gallery.py`, `export_detector_yaml.py` y `predict.py`.
- Apoyo: `common.py` (convenciones, E/S, regla de decisión, modo sin red) y `metrics.py` (métricas, bootstrap, Clopper-Pearson, selección de umbral).
- `run_drberry.sh`: corre todo, de la conversión a `detector.yaml`. YOLO se activa con `TRAIN_YOLO=1` y la exportación con `EXPORT_DETECTOR=1`.
- `README.md` y `pytest.ini`.
- `tests/`: `conftest.py`, `test_convert.py`, `test_dedup.py`, `test_split.py`, `test_metrics.py`, `test_eval_pipeline.py` y `test_models.py`.
- Este reporte.

No escribí nada en `resultados/` ni en `raw/`. `resultados/detector.yaml` **no existe todavía**: lo debe generar quien entrene el modelo, con `EXPORT_DETECTOR=1`.

## Funciones clave (resumen)

- **convert.py**
  - Modos: `crops` (margen, lado mínimo, filtro de cajas diminutas, cuadrado, `--max-side`), `image` (clase dominante, `--skip-multiclass`), `leaf-crops` (hoja etiquetada por la lesión que contiene, pensado para `raw/drberry_leafdet2`) y `folders`.
  - Estructuras aceptadas: Roboflow, Ultralytics y plana.
  - Lee polígonos y aplica EXIF.
  - `source_id` = nombre sin `.rf.<hash>`, así las copias aumentadas de la misma foto quedan juntas.
- **dedup.py**: phash 64 bits con union-find. Fusiona además grupos externos (ráfagas de `resultados/drberry_imagenes.csv`) y genera un mosaico de pares (los más parecidos y los más cercanos al umbral).
- **split.py**: reparte 70/15/15 por grupo, estratificado y con semilla, quedándose con el mejor de 200 órdenes. Verifica que no haya fuga.
  - Deja `test.csv` en solo lectura, con `test_frozen.json` que guarda el sha256 del archivo y el del contenido.
  - Se niega a re-congelar sin `--force`; `--verify` revisa el test.
  - `--materialize` crea la estructura que pide Ultralytics.
- **clip_baseline.py**: cero-shot (7 plantillas por 2–3 descripciones por clase) y sonda lineal (estandarización + regresión logística balanceada, con C elegido en val). Guarda los embeddings en caché y escribe cabezales `.joblib` que reutiliza `predict.py`.
- **train_yolo_cls.py**: estima el tiempo total tras la 1.ª época. `--max-minutes` corta limpio y el run se reanuda desde `weights/resume.pt`, que es necesario porque Ultralytics quita el optimizador de `last.pt` al terminar. Lo verifiqué leyendo `ultralytics/engine/trainer.py`. También tiene `--estimate-only` y escribe predicciones de val y test.
- **evaluate.py**: matriz de confusión, P/R/F1, sensibilidad, especificidad, tasa FP y FDR. Da IC bootstrap de 1000 réplicas **por grupo** y Clopper-Pearson, curva PR, AP y AUC, con las reglas argmax y umbral.
- **threshold.py**: elige en **validación** el umbral que cumple sensibilidad ≥ 0.90 con el **mínimo de falsas alarmas**. Si hay empate, toma el umbral más bajo para ganar sensibilidad, y usa el punto medio con el puntaje siguiente. Tiene `--criterio por_clase`; con `--test-pred` el test solo se informa.
- **gallery.py**: falsas alarmas, no detectados y confusiones entre enfermedades, en HTML autocontenido y PNG, con atribución.
- **export_detector_yaml.py**: genera el YAML para la simulación: matriz normalizada, recall con IC, tasa FP, umbral, origen de los datos, hash del test congelado, fecha y latencia.
- **predict.py**: trabaja con una imagen, una carpeta o una cámara (índice o URL rtsp/http, guardada sin credenciales en el log). Admite ROI o recorte central, registro JSONL y `--bench`.

## Resultados

### Pruebas

`/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I -m pytest /Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/tests -q` → **41 passed, 2 skipped**. Con `RUN_SLOW=1` → **43 passed**.

### Validación con DrBerry real (scratchpad; prueba de humo, NO es la cifra oficial)

**Conversión.** Da 737 recortes (alternaria 289, heliothis 204, oídio 162, sana 82) de 410 imágenes. En modo imagen da 410 ítems (68 / 161 / 121 / 60). Las dos cifras **coinciden** con `resultados/ficha_drberry.md` y `conteo_clases.csv`. Hubo 0 líneas de etiqueta inválidas.

**Deduplicación.** Solo con phash (umbral 6) hay 71 pares y 349 grupos. Al sumar las ráfagas quedan **139 grupos**, la misma cifra de ráfagas de la ficha. 0 pares tienen etiquetas distintas. En el mosaico, los 6 pares que revisé en el límite (distancia 6) son la misma hoja con un leve desplazamiento, así que el umbral 6 es conservador.

**Split** (semilla 20261023):

| Split | Recortes | Grupos |
|---|---|---|
| Train | 523 | 93 |
| Val | 113 | 25 |
| Test | 101 | 21 |

- **Fuga: 0** grupos y 0 fuentes entre splits.
- Dos corridas independientes dieron el **mismo hash de contenido** del test (`7e721c4b…`).
- Por clase mayoritaria, el test tiene solo 4 grupos de Alternaria, 6 de Heliothis, 7 de oídio y 4 de sanas.

**Tiempos en M4/MPS:**
- CLIP (embeddings de 737 recortes y las dos cabezas): unos 11 s.
- YOLO11n-cls a 224 px: la 1.ª época tarda 7.8 s y las siguientes unos 3.7 s, así que 40 épocas llevan unos 3–5 min.
- La reanudación con `--max-minutes 0.4` paró tras 6 épocas y quedó reanudable.

**Latencia de `predict.py`** (30 repeticiones, sin contar la carga del modelo):

| Modelo | p50 | p95 | Carga del modelo |
|---|---|---|---|
| YOLO11n-cls (1 época) | 8.3 ms | 9.3 ms | 0.9 s |
| Sonda CLIP | 15.8 ms | 22.9 ms | 3.8 s |

**Métricas en el test del humo.** El umbral se fijó en val con objetivo 0.90. Entre corchetes va el IC95: bootstrap por grupo para la exactitud y Clopper-Pearson para sensibilidad y FPR.

| Datos / modelo | Umbral | Exactitud | Sensibilidad enfermo | FPR (sanas) | Recall oídio |
|---|---|---|---|---|---|
| Recortes / sonda CLIP | 0.801 | 0.96 [0.89–1.00] | 1.00 (87/87) [0.96–1.00] | 0.00 (0/14) [0–0.23] | 0.84 |
| Recortes / CLIP cero-shot | 0.639 | 0.59 [0.45–0.72] | 0.99 (86/87) [0.94–1.00] | 0.21 (3/14) [0.05–0.51] | 0.12 |
| Imagen completa / sonda CLIP | 0.697 | 0.72 [0.53–0.87] | 0.89 (51/57) [0.79–0.96] | 0.125 (1/8) [0.003–0.53] | 0.30 |
| Imagen completa / cero-shot | 0.367 | 0.40 [0.22–0.59] | 1.00 (57/57) [0.94–1.00] | 0.50 (4/8) [0.16–0.84] | 0.05 |

Lectura del humo:

- **La sonda lineal CLIP es una línea base fuerte. El cero-shot no sirve para diagnosticar**, aunque separa bien enfermo de sano (AP de 0.99 o más).
- **Recortes contra imagen completa.** La exactitud de 0.96 con recortes supone que una persona ya localizó la lesión, y además puede aprovechar un atajo de escala: las cajas de Alternaria son lesiones diminutas, las demás son hojas completas. En imagen completa baja a 0.72. Hay que mostrar las dos cifras al jurado.
- **El umbral fijado en val no garantiza 0.90 en test.** Con imagen completa, val dio 0.926 y test 0.895. Es lo esperable con n pequeño. Opciones: `--target-sensitivity 0.95` o `--criterio por_clase`.
- **Oídio es la clase más débil.** Se confunde sobre todo con Heliothis (4 de 25 recortes del test).
- En el modo recortes el bootstrap colapsa a [1, 1] cuando la métrica vale 1. Por eso el YAML y el JSON incluyen también Clopper-Pearson.

## Fuentes

- Locales:
  - `resultados/ficha_drberry.md`, `resultados/drberry_imagenes.csv` (ráfagas), `resultados/conteo_clases.csv` y `reportes/adquisicion-drberry.md`.
  - `reportes/preparacion-entorno.md` (versiones y licencias).
  - `raw/drberry/drberry-original-data-v1-yolov8/` (`data.yaml`: CC BY 4.0, https://universe.roboflow.com/drberry/drberry-original-data/dataset/1, URL tomada del `data.yaml` y no abierta por mí).
  - `raw/drberry_leafdet2/.../data.yaml` (clases de hoja y lesión).
- Código fuente de Ultralytics 8.4.184 instalado en el venv (`engine/trainer.py`, `utils/__init__.py`), leído para el ciclo de guardado y reanudación y para `YOLO_OFFLINE`.
- No abrí URLs web en este rol.

## Límites

- Las cifras del humo vienen de **un** split (semilla 20261023) y de un test de 21 grupos (26 en imagen completa). Los IC son anchos y Clopper-Pearson ignora el agrupamiento, así que es optimista. No son resultados oficiales.
- **SUPUESTOS** (todos configurables por CLI):
  - umbral phash de 6;
  - margen del 10 % y recorte mínimo de 96 px;
  - descripciones del cero-shot;
  - rejilla de C;
  - desempate del umbral hacia más sensibilidad;
  - costos de 30 USD y 2.160 USD/ha/semana, que vienen del equipo.
- El modo `leaf-crops` está probado solo con datos sintéticos; no lo corrí sobre `drberry_leafdet2`. Esa versión no tiene auto-orient (NO VERIFICADO según la ficha).
- `predict.py --camera` no se probó con una cámara real ni con el flujo del D1 (sin acceso). No abre ventana de visualización: devuelve JSON y JSONL.
- Ultralytics es AGPL-3.0. Los `.joblib` son pickles, así que solo hay que cargar los que genera este pipeline.

## Pendientes y sugerencias

1. **Agente de entrenamiento:** correr `TRAIN_YOLO=1 bash pipeline/run_drberry.sh` (y `image`) en la carpeta acordada. Elegir el modelo con **val**, nunca con test. Luego correr `EXPORT_DETECTOR=1 MODEL_FOR_EXPORT=<modelo>` para escribir `resultados/detector.yaml`, que lee la simulación.
2. Decidir la unidad que usará la demo: recortes de lesión u hoja, o imagen completa. Probar `leaf-crops` con `raw/drberry_leafdet2` para tener hojas de Alternaria sin el atajo de escala.
3. Medir la cadena pantalla → cámara del D1:
   - capturar frames con `predict.py --camera <idx|url> --save-frames DIR --log ...`;
   - etiquetarlos a mano;
   - evaluarlos con `evaluate.py`.

   Es evidencia directa para el criterio "Demo + Evidencia".
4. Si se quiere más margen ante casos no detectados, usar `--target-sensitivity 0.95` o `--criterio por_clase` en `threshold.py` y reportar el costo en falsas alarmas.
5. Opcional: subir el umbral phash a 8–10 y revisar `duplicate_pairs.png`. Con DrBerry no cambia nada, porque las ráfagas ya cubren esos pares.
