# Reporte: adquisicion-plantdoc-plantvillage

Fecha: 2026-10-23. Ficha completa para el equipo: `resultados/ficha_secundarios.md`.

## Qué hice

1. **PlantDoc (GitHub, sin login):**
   - Hice `git clone --depth 1` de `pratikkayal/PlantDoc-Dataset` en `raw/plantdoc/PlantDoc-Dataset/`. Pesa 1,9 GB con `.git`; el archivo más grande, el pack, es de ~0,95 GB, por debajo del límite de 2 GB.
   - En macOS chocaron 6 pares de archivos que solo difieren en mayúsculas. Restauré las 12 versiones con `git cat-file` en `raw/plantdoc/PlantDoc-Dataset_colisiones/`.
   - Del repo de detección `PlantDoc-Object-Detection-Dataset` bajé solo los CSV de cajas, el README y el LICENSE, con un clon parcial sparse.
2. **PlantDoc en Roboflow:** usé la key del equipo una sola vez, por variable de entorno y sin imprimirla, para leer los metadatos del proyecto público `joseph-nelson/plantdoc`. Devolvió licencia CC BY 4.0, 2.569 imágenes y Blueberry leaf con 838 cajas. No descargué nada de allí porque GitHub tiene los mismos datos sin key.
3. **PlantVillage (GitHub, sin login):** hice un clon parcial (`--filter=blob:none`, sparse-checkout) de `spMohanty/PlantVillage-Dataset`. Solo bajé `raw/color/` de 5 clases:
   - `Blueberry___healthy`
   - `Cherry_(including_sour)___Powdery_mildew` y `Squash___Powdery_mildew` (las opcionales pedidas)
   - `Potato___Early_blight` y `Tomato___Early_blight`: los añadí yo como proxy de *Alternaria* en otra especie, con 2.000 imágenes y 20 MB. Si sobran, se pueden ignorar.

   También bajé `leaf_grouping/leaf-map.json` (qué fotos son de la misma hoja) y las particiones oficiales de HF (`color_train/test.txt`).
4. **Licencias:** las verifiqué en cada fuente (sección 5 de la ficha).
5. **Inventario reproducible:** escribí `resultados/secundarios/inventario_secundarios.py`. Corre con el venv, `-I` y cwd=`datos/`, y hace lo siguiente:
   - cuenta imágenes y tamaños;
   - agrupa por `leaf_id`;
   - calcula pHash para encontrar duplicados exactos y casi duplicados;
   - genera 1.644 recortes de hoja desde las cajas de PlantDoc (4 clases);
   - escribe el manifiesto por imagen, con la categoría de evaluación, el grupo para los intervalos de confianza y la licencia.
6. **Revisión visual de las 117 imágenes de PlantDoc "Blueberry leaf"**, hecha por mí con hojas de contacto. No es una revisión agronómica.

## Archivos producidos

- `resultados/ficha_secundarios.md`: conteos, licencias, laboratorio o campo, protocolo de evaluación E1–E7 y fuentes.
- `resultados/secundarios/manifest_secundarios.csv`: 10.611 filas (2.578 imágenes de PlantDoc + 1.644 recortes + 6.389 de PlantVillage).
- `resultados/secundarios/resumen_secundarios.json`
- `resultados/secundarios/triage_visual_plantdoc_blueberry.csv`
- `resultados/secundarios/inventario_secundarios.py`
- `raw/plantdoc/{PlantDoc-Dataset, PlantDoc-Dataset_colisiones, PlantDoc-Object-Detection-Dataset, crops_od, paper/1911.10317.pdf, LEEME_procedencia.md}`
- `raw/plantvillage/{PlantVillage-Dataset, hf_splits, LEEME_procedencia.md}`

## Resultados clave

- **PlantDoc:**
  - 2.578 imágenes completas (2.342 train / 236 test), web.
  - Blueberry leaf: 117 imágenes y 849 recortes (787 con lado ≥64 px).
  - Revisión visual de las 117: 65 verdes sin síntomas, 27 rojizas u otoñales, 19 con síntomas o desorden (clorosis, manchas, "Damage", deficiencia de Fe), 3 dudosas y 3 no aptas. **La clase "Blueberry leaf" no es "sana" pura.**
  - Conjunto externo de "sana" recomendado: 451 recortes verdes aptos de 65 imágenes.
- **PlantVillage:**
  - Blueberry___healthy: 1.502 imágenes, que son solo **160 hojas físicas** (mediana de 8 fotos por hoja).
  - Cherry PM: 1.052 imágenes de 65 hojas.
  - Squash PM: 1.835 imágenes sin `leaf_id`.
  - Early blight: 1.000 + 1.000 imágenes de 250 + 250 hojas.
  - Todas son de laboratorio: 256x256, fondo uniforme.
- **Ruido en PlantDoc:**
  - 55 grupos de imágenes idénticas, 27 de ellos con clases distintas y 14 entre train y test.
  - 78 pares casi duplicados.
  - En la clase de tizón temprano hay imágenes con nombre "Phytophthora", que es tizón tardío.
- **Licencias:**
  - PlantDoc: CC BY 4.0 (GitHub y Roboflow), pero muchas fotos son de stock con marca de agua y conservan copyright de terceros.
  - PlantVillage: CC BY-SA 3.0 según la tarjeta de HF del autor. El repo de GitHub no tiene LICENSE.
- **Evidencia publicada de caída fuera de dominio:**
  - Mohanty 2016: 99,35% en el test de PlantVillage frente a ~31% con imágenes de otras fuentes.
  - PlantDoc 2020: entrenar en PlantVillage y probar en PlantDoc da 15,08% en imagen completa y entre 19,73% y 39,87% en recortes.

## Fuentes

Están en la sección 7 de la ficha. Todas las abrí en esta sesión.

## Límites

- Ninguno de los dos datasets tiene oídio, alternaria ni Heliothis **en arándano**, ni imágenes de fruto. Solo sirven para pruebas de estrés: falsas alarmas fuera de dominio, generalización entre especies y enfermedades desconocidas.
- La revisión visual la hizo una IA, sin validación agronómica.
- La analogía entre patógenos de otras especies y los del arándano está NO VERIFICADA.
- Para PlantVillage Squash PM no hay agrupación por hoja.
- Corrí `git` con cwd dentro de `raw/`, solo para clonar y hacer checkout; los repos clonados no traen hooks. Todo el Python corrió con `-I` y cwd=`datos/`.
- La página de Roboflow Universe devolvió 403, así que la licencia de Roboflow sale solo de su API.

## Pendientes (para otros roles)

- Correr E1–E7 (ficha, sección 4) con el modelo entrenado en DrBerry, usando el umbral orientado a sensibilidad, y reportar intervalos de confianza por grupo.
- Que un agrónomo o un miembro del equipo valide la revisión visual de los 65 recortes verdes antes de citarlos como "sana".
- Decidir si se añade una puerta "¿es arándano?" (CLIP o un umbral de confianza) a partir del resultado de E7.
- Si se necesita espacio, `raw/plantdoc/PlantDoc-Dataset/.git` (945 MB) se puede borrar sin perder imágenes, salvo las colisiones, que ya están restauradas aparte. No lo borré.
