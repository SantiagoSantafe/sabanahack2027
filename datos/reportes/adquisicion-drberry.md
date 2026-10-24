# Reporte del agente adquisicion-drberry

Fecha: 2026-10-23. No se entrenó ningún modelo.

## Qué hice

1. **Consulté la API REST de Roboflow** con la key del equipo. La key se leyó de `.secrets/roboflow_api_key` y se pasó solo por la variable `ROBOFLOW_API_KEY`; nunca se imprimió y se redacta de todos los JSON guardados. Comprobé con `grep` que la key no aparece en ningún archivo de `raw/drberry*`, `raw/roboflow_*`, `resultados/` ni del scratchpad.
2. **Listé el workspace `drberry`:** tiene 7 proyectos, con sus versiones, preprocesamientos y aumentaciones, y el listado de nombres de imagen de cada proyecto (endpoint `search`).
3. **Elegí `drberry-original-data` v1 "data_original".** Es la única versión sin ninguna aumentación (410 imágenes; auto-orient y stretch a 1024x1024). La descargué en **YOLOv8** y en **COCO** a `raw/drberry/` y comprobé que los dos formatos coinciden caja por caja.
4. **Analicé la versión elegida:** conteos por clase y split, tamaños, cajas raras, duplicados exactos (md5) y casi exactos (dHash), fechas y cámaras a partir del nombre, y ráfagas temporales que causan fuga entre splits.
5. **Verifiqué que los proyectos `gen-*` son copias aumentadas fuera de Roboflow.** Descargué gen-3-20 y emparejé sus imágenes con las originales por dHash.
6. **Leí el paper** (PDF de SciTePress) para sacar el protocolo de captura y la línea base por clase.
7. **Busqué fuentes alternativas** en GitHub, Zenodo, HuggingFace, Mendeley, Kaggle y Roboflow Universe, y descargué dos datasets auxiliares pequeños.

## Archivos producidos

- `resultados/ficha_drberry.md`: ficha completa (fuente, versiones, licencia, conteos, problemas, línea base y recomendaciones).
- `resultados/conteo_clases.csv`: cajas, imágenes con la clase e imágenes por clase dominante, por split y en total. Corresponde a la versión elegida.
- `resultados/conteo_clases_auxiliares.csv`: los mismos conteos para gen-3-20, leaf-detection-2 v2 y plant-diagnosis blueberry.
- `resultados/drberry_imagenes.csv`: una fila por imagen con split, ruta, nombre original, cámara inferida, marca de tiempo, cajas por clase, clase dominante, multiclase, `grupo_rafaga` (umbral de 10 s), si el grupo cae en varios splits y `split_grupal_sugerido`.
- `resultados/drberry_resumen_original.json`: estadísticas crudas (áreas de caja, casi-duplicados, brechas temporales).
- `resultados/drberry_figuras/`: cuatro mosaicos de muestra con su `LEEME.txt` de atribución.
- `raw/drberry/`: exportaciones YOLOv8 y COCO (zip y extraídas), `_roboflow_metadata/` y `LEEME_fuente.txt`.
- `raw/drberry_gen3_20/`, `raw/drberry_leafdet2/`, `raw/roboflow_blueberry_plantdiag/` y `raw/drberry_paper/`, cada uno con su `LEEME_fuente.txt` (licencia y cita).
- `reportes/adquisicion-drberry_scripts/`: scripts usados, para poder reproducir el trabajo (`rf_info.py`, `rf_download.py`, `rf_search.py`, `analiza_yolo.py`, `tabla_imagenes.py`, `split_grupal.py`, `draw.py`).
- `raw/_tmp_rf_venv/`: venv temporal con requests, Pillow, PyYAML y pypdf. Se puede borrar cuando exista `.venv`.

## Resultados clave

- **Versión elegida:** 410 imágenes (327 train, 40 valid, 43 test), todas de 1024x1024, y 737 cajas: Alternaria 289, Heliothis 204, Oidio 162 y Sana 82.
- **Por clase dominante de la imagen:** Heliothis 161, Oidio 121, Alternaria 68 y Sana 60. Solo 15 imágenes son multiclase. Licencia CC BY 4.0.
- **Fuga crítica en el split original:** la mediana de la distancia temporal de valid o test a train es de 2 s. El 90 % de valid y el 86 % de test comparten ráfaga (≤ 10 s) con otro split. Hay 139 ráfagas para 410 imágenes y solo 21 son de Alternaria.
- **Granularidad de las cajas:** las de Alternaria son lesiones (área mediana 0.06 % de la imagen) y las demás clases tienen cajas de hoja completa (25-40 %).
- **Representatividad:** una finca (Fundo San Roberto, Perú), un solo día (2022-09-19, 12:35-14:44), hojas casi siempre desprendidas o en la mano, tres cámaras y confusión entre cámara y clase.
- **gen-1, gen-2, gen-3 y gen-3-20 son aumentaciones Keras de las mismas fotos**, aunque Roboflow las presente "sin aumentación". En gen-3-20, 83 de 585 imágenes se emparejan con una original a dHash ≤ 8 y hay 10 pares casi idénticos entre sus splits. Es probable que las métricas del paper (mAP50 94-96 %) estén infladas.
- **Línea base del paper:** sin aumentación, YOLOv5s da precisión 69.0 %, recall 44.5 % y mAP50 53.4 %. En la mejor configuración, YOLOv5s da 88.4 %, 92.6 % y 94.1 %. El resumen dice "accuracy 84 %, recall 91 %".

## Fuentes consultadas (URLs abiertas de verdad)

- API de Roboflow: `https://api.roboflow.com/drberry`, `/drberry/<proyecto>`, `/drberry/<proyecto>/<ver>/<formato>` y `/drberry/<proyecto>/search`. También `/dynamite-duelers-2` y `/dynamite-duelers-2/plant-diagnosis-ai-13--blueberry`.
- Páginas de Universe citadas en los README de exportación: https://universe.roboflow.com/drberry/drberry-original-data/dataset/1 y https://universe.roboflow.com/drberry/drberry-gen-3-20/dataset/1
- Paper: https://scitepress.org/PublishedPapers/2023/122071 y https://www.scitepress.org/Papers/2023/122071/122071.pdf (copia local en `raw/drberry_paper/122071.pdf`, CC BY-NC-ND 4.0, solo para uso interno).
- Zenodo: `https://zenodo.org/api/records?q=drberry` dio 0 resultados. Las búsquedas `blueberry leaf` y `blueberry disease images` solo devolvieron datasets de fruto o arbusto (BlueberryDCM, CC BY-NC 4.0; FlexiGroBots, CC BY 4.0). Ninguno es de enfermedad de hoja.
- HuggingFace: `https://huggingface.co/api/datasets?search=blueberry` devolvió 24 datasets y ninguno es de enfermedad de hoja. Por ejemplo, `cnavarrete/blueberry_dataset` tiene las clases Unripe, Pint y Ripe (lo verifiqué en su `data.yaml`), y `sankarip/blue_berry_data*` es de segmentación y no tiene licencia.
- GitHub: la búsqueda `drberry blueberry` dio 0 repos y `blueberry leaf disease` dio 5.
  - `chrisHuaman/blueberry-leaf-disease` es una app que consume los modelos DrBerry; no trae datos ni licencia.
  - `share2code99/blueberry_leaf_disease_classification` se deriva de Plant Diagnosis AI 13 y no aporta datos nuevos.
- Búsqueda web en Mendeley: no apareció ningún dataset de enfermedad de hoja de arándano. PlantVillage (Mendeley `tywbtsjrjv`) solo tiene `Blueberry_healthy` en laboratorio; no lo descargué porque es grande y no aporta enfermedades.

## Límites y bloqueos

- **Kaggle:** pide login, así que lo omití.
- **Buscador de Roboflow Universe** (`universe.roboflow.com/search`): devolvió HTTP 403 a WebFetch. Encontré el proyecto auxiliar por búsqueda web y lo consulté por la API.
- **Origen de los 29 "none":** no se sabe por qué el proyecto original tiene 29 imágenes sin split que no entran en la versión.
- **Tamaño original de las fotos:** no se conserva, por el stretch a 1024 y porque Roboflow elimina el EXIF.
- **Cámara por imagen:** es una inferencia a partir de la convención de nombres (NO VERIFICADO).
- **Umbral de ráfaga de 10 s:** es una heurística (SUPUESTO) revisada con unos pocos pares visuales.
- **Ninguna descarga superó 2 GB.** La mayor fue de 139 MB (leaf-detection-2).

## Pendientes y sugerencias para otros agentes

- **Pipeline:** usar `resultados/drberry_imagenes.csv` (columnas `grupo_rafaga` y `split_grupal_sugerido`) para partir sin fuga. Decidir entre clasificar la imagen completa o recortes de hoja. Para recortar Alternaria, las cajas de hoja `Hoja de arandano` están en `raw/drberry_leafdet2`, con 433 nombres en común con la versión elegida.
- **Evaluación:** con 8 imágenes de Alternaria en el test original, acertar 8 de 8 solo garantiza un límite inferior del 63 % (IC 95 %). Hay que reportar las sensibilidades con intervalo y medir aparte la cadena "pantalla → cámara del D1".
- **Comunicación:** citar a DrBerry (CC BY 4.0) en la presentación y no redistribuir el dataset. No mostrar imágenes de `roboflow_blueberry_plantdiag`, cuya procedencia es dudosa.
