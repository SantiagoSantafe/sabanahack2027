# Modelo final del clasificador de hojas (demo AgiBot D1)

Clasificador de hoja completa con 4 clases: `sana`, `oidio`, `alternaria`, `heliothis`. Regla de alerta: **sospecha si `1 − p(sana) ≥ umbral`**. Cuando hay sospecha, la clase es la enfermedad más probable.

| Archivo | Qué es |
|---|---|
| `clip_probe_tiles3.joblib` | **Modelo final elegido con el protocolo registrado.** Es una sonda lineal sobre CLIP ViT-B-32 (laion2b_s34b_b79k) con teselas 3x3, entrenada en train+val de DrBerry y con C elegido por validación cruzada agrupada en 5 pliegues. Es un pickle: cárguenlo solo desde este pipeline. |
| `umbral.json` | Umbral 0,737, fijado sobre las predicciones OOF de esa validación cruzada para sensibilidad ≥ 0,90. |
| `umbral_alta_sensibilidad_por_clase.json` | Umbral 0,415: cada enfermedad ≥ 0,90 en OOF. Da más alertas. |
| `detector.yaml` | Copia de `resultados/detector.yaml` con las métricas del test congelado, los IC y las secciones de comparación, fuera de dominio y estrés. |
| `imagenes_prueba/` | 5 fotos del test congelado de DrBerry (CC BY 4.0, uso interno), de grupos distintos. |
| `predicciones_5_imagenes_{mps,cpu}.jsonl`, `latencia_{mps,cpu}.json` | Prueba de `predict.py` y latencia. |
| `alternativa_sonda_recortes_en_imagen/` | **Candidato post-hoc:** la sonda CLIP entrenada con recortes y aplicada a la imagen, con umbral 0,292 fijado en val de imagen. Se evaluó después de elegir el final, así que hay que confirmarlo con datos nuevos. |
| `alternativa_yolo11n_cls_224/` | YOLO11n-cls a 224 px en imagen completa, con umbral 0,834 de val. Fue el más estable en el estrés sintético. Licencia AGPL-3.0. |

## Uso (desde `datos/`, nunca desde `raw/`)

```bash
PY=.venv/bin/python; M=resultados/ml/modelo_final
$PY -I pipeline/predict.py --weights $M/clip_probe_tiles3.joblib --threshold $M/umbral.json --image hoja.jpg
# Cámara o flujo del robot mirando la pantalla, con recorte central y registro de alertas:
$PY -I pipeline/predict.py --weights $M/clip_probe_tiles3.joblib --threshold $M/umbral.json --camera 0 --frames 0 \
    --interval 1.0 --center-crop 0.7 --save-frames resultados/ml/capturas_d1 --log resultados/ml/capturas_d1/alertas.jsonl
```

Necesita los pesos CLIP en caché en `pipeline/pesos/open_clip`; no descarga nada.

## Prueba sobre 5 imágenes

Los resultados en MPS y en CPU son idénticos.

| Imagen | Final (tiles3) | Candidato post-hoc | YOLO 224 |
|---|---|---|---|
| 1_sana | sana (p_enf 0,22) | sana (0,15) | **alternaria (0,93): falsa alarma** |
| 2_oidio | oídio (1,00) | oídio (1,00) | heliothis (1,00): alerta, pero diagnóstico errado |
| 3_alternaria | alternaria (1,00) | oídio (1,00): alerta, pero diagnóstico errado | alternaria (1,00) |
| 4_heliothis | heliothis (1,00) | heliothis (1,00) | heliothis (1,00) |
| 5_sana | **alternaria (0,90): falsa alarma** | sana (0,04) | **alternaria (0,95): falsa alarma** |

## Latencia

Inferencia más preproceso, sin contar la carga. Son 30 repeticiones sobre `3_alternaria.jpg` en un Mac M4.

| Modelo | MPS p50 / p95 | CPU p50 / p95 | Carga |
|---|---|---|---|
| Final (CLIP, 10 recortes por imagen) | 59,2 / 62,4 ms | 84,9 / 85,9 ms | 2,5–2,8 s |
| Candidato post-hoc (CLIP global) | 12,3 / 12,5 ms | 18,6 / 19,5 ms | 2,5–2,7 s |
| YOLO11n-cls 224 | 7,6 / 9,1 ms | 5,4 / 5,9 ms | 0,9 s |

Los tres modelos caben de sobra en un ciclo de 1 frame por segundo.

## Cifras clave y advertencias

Están en `../RESULTADOS.md`:

- *Modelo anterior (imagen limpia, sin cámara); el modelo en uso es `modelo_camara`: 42/54 = 0,78 y 4/14 = 0,29 con la cámara del D1.* En el test congelado (68 imágenes, 21 grupos), el modelo final detecta **43 de 54 enfermas (0,80)** y da **5 de 14 falsas alarmas**.
- Con Alternaria a imagen completa solo detecta 4 de 14.
- En hojas sanas de campo (iNaturalist) da **44 de 60 falsas alarmas**.
- No se ha medido la cadena real pantalla → cámara del D1.
