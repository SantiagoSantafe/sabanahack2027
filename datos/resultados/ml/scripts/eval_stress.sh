#!/usr/bin/env bash
# Evalúa cada condición de estrés (sintético) con el umbral de cada modelo (fijado en val/OOF de DrBerry).
set -euo pipefail
D=/Users/santiagosantafe/Downloads/SabanaHack/datos; PY=$D/.venv/bin/python; R=$D/resultados/ml
cd "$D"
for pair in "image_clip_cv_tiles3:umbral_clip_cv_tiles3" "image_clip_cv_tiles0:umbral_clip_cv_tiles0" "image_yolo224:umbral_yolo224" "image_yolo448:umbral_yolo448"; do
  M=${pair%%:*}; U=$R/drberry_image/${pair##*:}.json
  "$PY" -I -c "
import pandas as pd, os
df = pd.read_csv('$R/stress/pred/predicciones_$M.csv', keep_default_na=False)
os.makedirs('$R/stress/pred_por_condicion/$M', exist_ok=True)
for c, g in df.groupby('dataset'):
    g.to_csv(f'$R/stress/pred_por_condicion/$M/{c}.csv', index=False)
"
  for f in "$R"/stress/pred_por_condicion/$M/*.csv; do
    c=$(basename "$f" .csv)
    "$PY" -I "$D/pipeline/evaluate.py" --pred "$f" --threshold "$U" --out "$R/stress/eval/$M/$c" --n-boot 300 --title "estres $c ($M)" | grep -o "acc=.*FPR=[0-9.]*" | sed "s/^/$M $c: /"
  done
done
