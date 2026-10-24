# Paquete para la demo del robot

Descomprimir en la raíz del proyecto (la carpeta que contiene `datos/`) **con la terminal**, para conservar los enlaces de la caché de CLIP:

```bash
unzip BerryGoodIdea_demo_robot.zip -d /ruta/al/proyecto
```

- `datos/raw/drberry/drberry-original-data-v1-yolov8/{train,valid,test}/`: **solo** las 68 imágenes del test congelado y sus etiquetas (el test agrupado toma fotos de las tres carpetas originales de Roboflow). DrBerry, licencia CC BY 4.0: hay que citar la fuente (https://universe.roboflow.com/drberry/drberry-original-data).
- `datos/resultados/ml/drberry_image/splits/test_relativo.csv`: el mismo test.csv, con rutas **relativas a `datos/`**. Úsalo en lugar de test.csv, que trae rutas absolutas del otro Mac.
- `datos/pipeline/pesos/open_clip/` y `yolo11n-cls.pt`: los pesos que necesita `predict.py`.
- `datos/raw/agibot_docs/`: la guía del SDK del D1 (AGIQUAD_D1_Edu_Ultra_SDK_Guide_V2.0.7.pdf), el manual de usuario y las fichas técnicas. Solo para uso interno del equipo.

No incluye la API key de Roboflow. Si hace falta, se pone a mano en `datos/.secrets/roboflow_api_key`.
