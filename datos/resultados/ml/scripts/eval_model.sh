#!/usr/bin/env bash
# Umbral en VALIDACIÓN (sens >= 0.90), evaluación y galería en TEST congelado para un modelo.
# Uso: eval_model.sh <modo crops|image> <nombre> <carpeta_pred> <prefijo>
set -euo pipefail
D=/Users/santiagosantafe/Downloads/SabanaHack/datos
PY=$D/.venv/bin/python; P=$D/pipeline
cd "$D"
W=$D/resultados/ml/drberry_$1; N=$2; PD=$3; PRE=$4
ATTR="DrBerry (Roboflow Universe, drberry-original-data v1), CC BY 4.0"
"$PY" -I "$P/threshold.py" --val-pred "$PD/predicciones_${PRE}_val.csv" --test-pred "$PD/predicciones_${PRE}_test.csv" --out "$W/umbral_$N.json"
"$PY" -I "$P/evaluate.py" --pred "$PD/predicciones_${PRE}_val.csv" --threshold "$W/umbral_$N.json" --out "$W/eval_${N}_val" --title "$N ($1) VAL"
"$PY" -I "$P/evaluate.py" --pred "$PD/predicciones_${PRE}_test.csv" --threshold "$W/umbral_$N.json" --out "$W/eval_${N}_test" --title "$N ($1) TEST congelado"
"$PY" -I "$P/gallery.py" --pred "$PD/predicciones_${PRE}_test.csv" --threshold "$W/umbral_$N.json" --out "$W/galeria_${N}_test" --attribution "$ATTR"
"$PY" -I "$P/split.py" --verify "$W/splits"
