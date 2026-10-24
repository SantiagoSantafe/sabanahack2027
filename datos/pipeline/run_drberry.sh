#!/usr/bin/env bash
# Pipeline completo sobre DrBerry (drberry-original-data v1) hasta las métricas y, opcionalmente, detector.yaml.
#
# Uso:
#   bash pipeline/run_drberry.sh                 # recortes por caja (modo crops)
#   bash pipeline/run_drberry.sh image           # imagen completa con clase dominante
#   WORK=/ruta/salida TRAIN_YOLO=1 MAX_MIN=25 bash pipeline/run_drberry.sh
#   EXPORT_DETECTOR=1 bash pipeline/run_drberry.sh   # escribe resultados/detector.yaml (sobrescribe)
#
# Variables: WORK (carpeta de trabajo; por defecto pipeline/work/drberry_<modo>), SEED (20261023),
# TRAIN_YOLO (0/1), EPOCHS (40), MAX_MIN (25), MODEL_FOR_EXPORT (probe|zeroshot|yolo; por defecto probe).
# OJO: split.py congela el test en $WORK/splits. Volver a correr con otra semilla falla a propósito
# (usar otra carpeta WORK o --force a mano si de verdad se quiere re-congelar).
set -euo pipefail

D=/Users/santiagosantafe/Downloads/SabanaHack/datos
PY="$D/.venv/bin/python"
P="$D/pipeline"
MODE="${1:-crops}"
WORK="${WORK:-$P/work/drberry_$MODE}"
SEED="${SEED:-20261023}"
SRC="$D/raw/drberry/drberry-original-data-v1-yolov8"
ATTR="DrBerry (Roboflow Universe, drberry-original-data v1), CC BY 4.0"
cd "$D"   # nunca ejecutar con el directorio de trabajo dentro de raw/

echo "== 1) convert ($MODE)"
"$PY" -I "$P/convert.py" --input "$SRC" --out "$WORK/convert" --mode "$MODE" --margin 0.10 --min-crop-px 96 --square \
  --dataset-name drberry-original-v1

echo "== 2) dedup (phash + ráfagas de resultados/drberry_imagenes.csv)"
"$PY" -I "$P/dedup.py" --manifest "$WORK/convert/manifest.csv" --out "$WORK/dedup" --threshold 6 --pairs-png \
  --extra-groups-csv "$D/resultados/drberry_imagenes.csv" --extra-key nombre_original --extra-group grupo_rafaga

echo "== 3) split 70/15/15 agrupado y estratificado"
"$PY" -I "$P/split.py" --manifest "$WORK/convert/manifest.csv" --groups "$WORK/dedup/groups.csv" --out "$WORK/splits" \
  --seed "$SEED" --materialize "$WORK/yolo_cls"

echo "== 4) CLIP cero-shot y sonda lineal"
"$PY" -I "$P/clip_baseline.py" --splits-dir "$WORK/splits" --out "$WORK/clip" --mode both

run_eval () {  # $1 = nombre, $2 = carpeta con predicciones_<prefijo>_{val,test}.csv, $3 = prefijo
  "$PY" -I "$P/threshold.py" --val-pred "$2/predicciones_$3_val.csv" --test-pred "$2/predicciones_$3_test.csv" \
    --out "$WORK/umbral_$1.json"
  "$PY" -I "$P/evaluate.py" --pred "$2/predicciones_$3_test.csv" --threshold "$WORK/umbral_$1.json" --out "$WORK/eval_$1_test"
  "$PY" -I "$P/gallery.py" --pred "$2/predicciones_$3_test.csv" --threshold "$WORK/umbral_$1.json" --out "$WORK/galeria_$1_test" \
    --attribution "$ATTR"
}
echo "== 5) umbral (en val), evaluación y galería (en test congelado)"
run_eval zeroshot "$WORK/clip" zeroshot
run_eval probe "$WORK/clip" probe

if [ "${TRAIN_YOLO:-0}" = "1" ]; then
  echo "== 6) YOLO clasificación (MPS)"
  "$PY" -I "$P/train_yolo_cls.py" --data-dir "$WORK/yolo_cls" --splits-dir "$WORK/splits" --project "$WORK/runs" --name y11n \
    --epochs "${EPOCHS:-40}" --max-minutes "${MAX_MIN:-25}"
  RUN="$(ls -td "$WORK"/runs/y11n* | head -1)"
  if [ -f "$RUN/predicciones_yolo_test.csv" ]; then run_eval yolo "$RUN" yolo; fi
fi

"$PY" -I "$P/split.py" --verify "$WORK/splits"

if [ "${EXPORT_DETECTOR:-0}" = "1" ]; then
  M="${MODEL_FOR_EXPORT:-probe}"
  echo "== 7) detector.yaml desde el modelo '$M'"
  "$PY" -I "$P/export_detector_yaml.py" --metrics "$WORK/eval_${M}_test/metrics.json" --threshold "$WORK/umbral_$M.json" \
    --split-summary "$WORK/splits/split_summary.json" --dataset-name "DrBerry drberry-original-data v1 ($MODE)" \
    --dataset-license "CC BY 4.0" --dataset-url "https://universe.roboflow.com/drberry/drberry-original-data/dataset/1" \
    --data-notes "Una finca (Fundo San Roberto, Perú), un día (2022-09-19); ver resultados/ficha_drberry.md" \
    --out "$D/resultados/detector.yaml"
fi
echo "Listo: $WORK"
