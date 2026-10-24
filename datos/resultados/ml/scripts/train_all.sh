#!/usr/bin/env bash
# Entrena YOLO11n-cls en MPS para cada configuración (secuencial). Lanzar con nohup en segundo plano.
set -uo pipefail
D=/Users/santiagosantafe/Downloads/SabanaHack/datos
PY=$D/.venv/bin/python; P=$D/pipeline
cd "$D"
run () { # modo imgsz nombre
  W=$D/resultados/ml/drberry_$1
  echo "== $(date +%T) entrenando $1 imgsz=$2 -> $W/runs/$3"
  "$PY" -I "$P/train_yolo_cls.py" --data-dir "$W/yolo_cls" --splits-dir "$W/splits" --project "$W/runs" --name "$3" \
     --epochs 80 --patience 25 --imgsz "$2" --max-minutes 30 --seed 0
  echo "== $(date +%T) fin $3 (código $?)"
}
run crops 224 y11n_224
run image 224 y11n_224
run image 448 y11n_448
run image 640 y11n_640
echo "== $(date +%T) TODO TERMINADO"
