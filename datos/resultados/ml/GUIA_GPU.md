# Guía para entrenar en la GPU del equipo (opcional)

**No hace falta una GPU para reproducir lo entregado.** En el Mac M4 (MPS) cada entrenamiento completo de YOLO11n-cls tomó minutos, no horas: 1.ª época medida de 4,1 s (recortes, 224 px), 4,1 s (imagen, 224 px) y 7,1 s (imagen, 448 px) (`logs/03a_yolo_estimacion.log`); las corridas completas (80 épocas máx., paciencia 25) pararon por paciencia en 28–55 épocas y tardaron entre ~2 y ~10 min (`logs/03b_yolo_train.log`, `drberry_*/runs/*/train_status.json`). El umbral de 2 h que pedía esta guía no se alcanzó.

La GPU sirve solo si el equipo quiere probar modelos más grandes o validación cruzada de YOLO. Estos comandos están **sin probar en GPU** (no tenemos acceso a esa máquina).

## Preparación

```bash
# En la máquina con GPU, copiar la carpeta datos/ (o al menos pipeline/, resultados/ml/drberry_image/{splits,yolo_cls}/ y raw/drberry/)
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt   # torch con CUDA: instalar la rueda de pytorch.org correspondiente
D=$PWD; PY=$D/.venv/bin/python
```

`train_yolo_cls.py` elige `cuda` sola si está disponible (`--device auto`). Los pesos `yolo11s-cls.pt` / `yolo11m-cls.pt` NO están en `pipeline/pesos/`: hay que descargarlos de los releases oficiales de Ultralytics (AGPL-3.0) y pasar `--allow-online` o la ruta local con `--model`.

## Comandos

```bash
# Imagen completa a 640 px con un modelo mayor (mismo split congelado; el test NO se usa para elegir)
$PY -I pipeline/train_yolo_cls.py --data-dir resultados/ml/drberry_image/yolo_cls \
    --splits-dir resultados/ml/drberry_image/splits --project resultados/ml/drberry_image/runs_gpu --name y11s_640 \
    --model yolo11s-cls.pt --imgsz 640 --epochs 150 --patience 40 --batch 32 --max-minutes 110 \
    --extra cos_lr=True --extra dropout=0.2 --allow-online

# Umbral en val, evaluación en test congelado y galería (mismo procedimiento que en el Mac)
bash resultados/ml/scripts/eval_model.sh image y11s_640 resultados/ml/drberry_image/runs_gpu/y11s_640 yolo
$PY -I pipeline/split.py --verify resultados/ml/drberry_image/splits   # evidencia de que el test no cambió
```

Si el presupuesto de tiempo corta el entrenamiento, continuar con `--resume resultados/ml/drberry_image/runs_gpu/y11s_640`.

## Advertencias

- La validación tiene solo 25 grupos (10 sanas): con YOLO el umbral fijado en val no se sostuvo en test (ver `RESULTADOS.md`). Para comparar con la sonda CLIP en igualdad de condiciones habría que hacer validación cruzada agrupada también con YOLO (5 entrenamientos por configuración).
- Más capacidad no arregla los dos problemas de datos que vimos: Alternaria con lesiones diminutas en fotos de hoja en la mano y el atajo de fondo (hojas sanas sobre sustrato -> "alternaria"). Eso pide más fotos y más variadas, no más GPU.
