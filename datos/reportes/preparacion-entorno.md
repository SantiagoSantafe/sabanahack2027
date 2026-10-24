# Reporte: preparacion-entorno

Fecha: 2026-10-23. Máquina: macOS 26.6.2, Apple Silicon (arm64).

## Qué hice

1. Busqué un intérprete Python 3.10 o superior. No están `uv` ni `pyenv`. Homebrew tiene `python3.11` (3.11.15) y `python3.14` (3.14.6). Elegí **3.11.15**, porque torch, ultralytics y open_clip publican ruedas arm64 probadas para esa versión.
2. Creé el venv: `/opt/homebrew/bin/python3.11 -m venv /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv` y actualicé pip a 26.2.2.
3. Instalé con pip (log: `pipeline/pip_install.log`): torch, torchvision, ultralytics, open_clip_torch, imagehash, scikit-learn, pyyaml, pillow, pandas, numpy, matplotlib, requests, pytest, roboflow, tqdm y seaborn. `pip check` devolvió "No broken requirements found".
4. Escribí el script de verificación `pipeline/verificar_entorno.py`, lo corrí y dejé su salida en `pipeline/pesos/verificacion_entorno.json` y su log en `pipeline/pesos/verificacion_entorno.log`.
5. Hice además una prueba de entrenamiento en MPS: 5 pasos de SGD sobre yolo11n-cls, con batch 16 de 224x224.
6. Generé `requirements.txt` con `pip freeze` (79 paquetes).

No usé la API key de Roboflow. Para este rol no hacía falta, y el archivo `.secrets/roboflow_api_key` quedó sin tocar.

## Versiones exactas (verificadas con import y `__version__`)

| Paquete | Versión |
|---|---|
| Python | 3.11.15 |
| torch | 2.14.1 |
| torchvision | 0.29.1 |
| ultralytics | 8.4.184 |
| open_clip_torch | 3.3.0 |
| timm (dependencia de open_clip) | 1.0.30 |
| huggingface-hub | 2.3.0 |
| imagehash | 4.3.2 |
| scikit-learn | 1.9.1 |
| scipy | 1.17.1 |
| pyyaml | 6.0.3 |
| pillow | 13.0.0 |
| pandas | 3.1.0 |
| numpy | 2.4.6 |
| matplotlib | 3.11.2 |
| seaborn | 0.13.2 |
| requests | 2.34.2 |
| pytest | 9.1.1 |
| roboflow | 1.7.2 |
| tqdm | 4.70.1 |
| opencv-python / opencv-python-headless | 5.0.0.93 / 5.0.0.93 |

## Resultados de la verificación

- **Imports:** los 16 paquetes pedidos importan sin error (`"errores": {}`).
- **MPS:** `torch.backends.mps.is_available()` y `is_built()` devuelven True. Un matmul 512x512 en `mps` corre bien.
- **Ultralytics:** se descargó `yolo11n-cls.pt` (5,5 MB) desde `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n-cls.pt` a `pipeline/pesos/yolo11n-cls.pt`. Una predicción en MPS sobre una imagen sintética tardó 2,97 s, incluida la descarga. La clase ImageNet top-1 ("ping-pong_ball", 0,25) es irrelevante; solo comprueba que el flujo funciona.
- **Entrenamiento en MPS:** 5 pasos forward/backward/step con batch 16 tardaron 4,3 s. Salida de forma (16, 1000).
- **open_clip:** ViT-B-32 con `pretrained="laion2b_s34b_b79k"` (repo HF `laion/CLIP-ViT-B-32-laion2B-s34B-b79K`) quedó en caché en `pipeline/pesos/open_clip/` (584 MB, `open_clip_model.safetensors`). Embedding de 512 dimensiones. Zero-shot en MPS sobre la imagen sintética: 46,5 s, casi todo descarga; las cargas siguientes salen de la caché local. Las probabilidades zero-shot de esa imagen sintética no tienen ningún valor agronómico.

## Archivos producidos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/` (1,4 GB)
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/requirements.txt` (pip freeze)
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/verificar_entorno.py` (se puede volver a correr)
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pip_install.log`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pesos/yolo11n-cls.pt`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pesos/open_clip/` (caché HF de ViT-B-32 laion2b)
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pesos/verificacion_entorno.json` y `.log`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pesos/_prueba_sintetica.png` (imagen de prueba generada, no es un dato real)

## Cómo usarlo (resto del equipo)

```bash
PY=/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python
$PY -I /Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/verificar_entorno.py   # re-verificar
# open_clip con la caché local (sin volver a descargar):
#   open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k",
#       cache_dir="/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pesos/open_clip")
# YOLO: YOLO("/Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/pesos/yolo11n-cls.pt"), device="mps"
# Roboflow: ROBOFLOW_API_KEY="$(cat /Users/santiagosantafe/Downloads/SabanaHack/datos/.secrets/roboflow_api_key)" $PY -I script.py
```

## Licencias (registradas, no redistribuir pesos)

- ultralytics 8.4.184 y pesos YOLO11: **AGPL-3.0** según `pip show`. Para la demo del hackathon basta. Un uso comercial cerrado necesitaría licencia Enterprise. Esto último está NO VERIFICADO en esta sesión, porque no abrí la página de licencias de Ultralytics.
- open_clip_torch 3.3.0: MIT (`pip show`). Pesos `laion/CLIP-ViT-B-32-laion2B-s34B-b79K`: etiqueta `license:mit` en los metadatos de Hugging Face, consultada con `huggingface_hub.model_info`.
- torch 2.14.1: Apache-2.0, BSD y otras (`pip show`).
- roboflow 1.7.2: `pip show` no declara licencia (NO VERIFICADO).

## Límites y advertencias

- Están instalados `opencv-python` y `opencv-python-headless` (5.0.0.93 los dos), porque ultralytics pide uno y roboflow el otro. `import cv2` funciona y `pip check` está limpio. Si aparece un conflicto de GUI de cv2 (por ejemplo con `cv2.imshow`), desinstalar el headless.
- Las versiones son las más recientes que resolvió pip el 2026-10-23. `requirements.txt` las fija para reproducir el entorno.
- Ultralytics creó su archivo de configuración en `~/Library/Application Support/Ultralytics/settings.json` con `datasets_dir=/Users/santiagosantafe/Downloads/SabanaHack/datos/datasets`, porque tomó el directorio desde el que se corrió. Usen rutas absolutas en los YAML de datos.
- Ese mismo archivo trae `"sync": true` por defecto (analítica anónima de Ultralytics). Lo dejé sin cambiar porque es configuración persistente de usuario. Si el equipo prefiere desactivarlo: `.venv/bin/yolo settings sync=False`.
- La descarga de Hugging Face fue sin autenticación (aviso de rate limit). No se inició sesión.
- No medí rendimiento real con hojas de arándano. Eso le toca al agente de pipeline con DrBerry.

## Pendientes

- Nada bloqueante para este rol.
- Opcional: si se va a correr `yolo` desde otra carpeta, revisar `datasets_dir`/`runs_dir` con `.venv/bin/yolo settings`.
