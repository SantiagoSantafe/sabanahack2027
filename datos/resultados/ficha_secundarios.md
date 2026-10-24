# Ficha de datasets secundarios: PlantDoc y PlantVillage (evaluación fuera del dominio)

Sabana Hack, reto "Berry Good Idea". Autor: agente `adquisicion-plantdoc-plantvillage`. Fecha: 2026-10-23.
Manifiesto por imagen: `resultados/secundarios/manifest_secundarios.csv` (10.611 filas). Resumen en JSON: `resultados/secundarios/resumen_secundarios.json`. Script reproducible: `resultados/secundarios/inventario_secundarios.py`.

## En una frase

Ninguno de los dos sirve para medir el rendimiento principal: no tienen oídio, alternaria ni Heliothis **en arándano**. Sí sirven como **pruebas de estrés externas** para cuatro preguntas: (1) cuántas falsas alarmas da el modelo con hojas de arándano de otro dominio, (2) si el oídio y la alternaria se reconocen cuando cambia la especie, (3) si una enfermedad desconocida pasa como "sana" (casos no detectados) y (4) qué hace el robot con hojas que no son de arándano.

## 1. Qué se descargó

| Fuente | Ruta local | Versión | Licencia (verificada en la fuente) | Dominio |
|---|---|---|---|---|
| PlantDoc, repo de clasificación con imágenes completas | `raw/plantdoc/PlantDoc-Dataset/` (+ `PlantDoc-Dataset_colisiones/`) | GitHub pratikkayal/PlantDoc-Dataset, commit `5467f60` (2021-05-02) | **CC BY 4.0**: LICENSE.txt, README ("License: Creative Commons Attribution 4.0 International") y campo `license` de la API de GitHub | **Web**: fotos de Google Images y Ecosia. Mezcla campo, jardín, stock con fondo blanco, herbario y clipart. No es laboratorio ni un cultivo comercial controlado |
| PlantDoc, repo de detección (solo cajas) | `raw/plantdoc/PlantDoc-Object-Detection-Dataset/` (train/test_labels.csv) | commit `4730a23` (2022-02-21) | CC BY 4.0 (LICENSE.txt, API de GitHub) | igual |
| PlantDoc, recortes por hoja (derivados) | `raw/plantdoc/crops_od/` | generados aquí desde las cajas | hereda CC BY 4.0 | web, una hoja por imagen |
| PlantDoc en Roboflow (solo metadatos, no descargado) | — | proyecto `joseph-nelson/plantdoc`, versiones 1 a 4 | API de Roboflow: **"CC BY 4.0"**, 2.569 imágenes, Blueberry leaf 838 cajas | igual que GitHub |
| PlantVillage (5 clases) | `raw/plantvillage/PlantVillage-Dataset/raw/color/` | GitHub spMohanty/PlantVillage-Dataset, commit `7f7ecc7` (2026-02-05) | **CC BY-SA 3.0** según la tarjeta de Hugging Face `mohanty/PlantVillage`, publicada por el mismo autor. El repo de GitHub **no tiene LICENSE** (la API devuelve `None`) y el catálogo TFDS no declara licencia | **Laboratorio**: una hoja sola, de frente, sobre fondo gris uniforme, 256x256 px (comprobado en las 6.389 imágenes) |
| Particiones oficiales de PlantVillage | `raw/plantvillage/hf_splits/color_{train,test}.txt` | HF `mohanty/PlantVillage` | igual | — |

No hizo falta usar la API key de Roboflow para descargar. Solo se usó una vez para leer los metadatos y confirmar la licencia (por variable de entorno; nunca se imprimió ni se guardó).

## 2. Conteos útiles para la evaluación

"Grupos independientes" es la unidad que hay que usar para los intervalos de confianza. En PlantVillage, varias fotos son de la **misma hoja física** (`leaf_id` de `leaf_grouping/leaf-map.json`). Los recortes de PlantDoc se agrupan por la imagen de la que salen.

| Categoría de evaluación | Fuente / clase original | Imágenes | Grupos independientes | Notas |
|---|---|---|---|---|
| **sana_arandano** (laboratorio) | PlantVillage `Blueberry___healthy` | 1.502 (HF: 1.178 train / 324 test) | **160 hojas** (entre 3 y 29 fotos por hoja, mediana 8) | Especie de Vaccinium no indicada |
| **sana_arandano** (web, imagen completa) | PlantDoc `Blueberry leaf` | 117 (106 train / 11 test) | 117 (con 1 duplicado exacto entre train y test) | **No es "sana" pura**. Ver la revisión visual más abajo |
| **sana_arandano** (web, recorte de hoja) | PlantDoc OD `Blueberry leaf` | 849 recortes; 787 con lado ≥64 px | 117 imágenes de origen | Lado menor del recorte: p10=71, p50=179, p90=405 px |
| ↳ subconjunto verde sin síntomas y lado ≥64 px | revisión visual | **451** (434 train / 17 test) | 65 imágenes | Es el mejor conjunto externo de "sana" para medir falsas alarmas |
| **oidio_otra_especie** (laboratorio) | PV `Cherry_(including_sour)___Powdery_mildew` | 1.052 | **65 hojas** (entre 1 y 24 fotos por hoja, mediana 19) | Patógeno en cerezo: *Podosphaera* sp. (NO VERIFICADO en esta sesión) |
| **oidio_otra_especie** (laboratorio) | PV `Squash___Powdery_mildew` | 1.835 | **sin leaf_id** (no figura en leaf-map) | El tamaño efectivo es desconocido y menor que 1.835 |
| **oidio_otra_especie** (web) | PlantDoc `Squash Powdery mildew leaf` | 130 imágenes / 254 recortes (todos ≥64 px) | 130 | 3 cajas no tienen imagen en el repo de clasificación |
| **alternaria_otra_especie** (laboratorio) | PV `Potato___Early_blight` + `Tomato___Early_blight` | 1.000 + 1.000 | 250 + 250 hojas (unas 4 fotos por hoja) | *Alternaria solani/linariae* (NO VERIFICADO en esta sesión). Es un proxy débil: el síntoma (anillos concéntricos en solanáceas) no es el de la mancha por Alternaria del arándano |
| **alternaria_otra_especie** (web) | PlantDoc `Tomato Early blight leaf` + `Potato leaf early blight` | 88 + 117 imágenes / 541 recortes (482 ≥64 px) | 205 | Hay errores de etiqueta: imágenes con nombre "Phytophthora" (tizón tardío) dentro de la clase de tizón temprano |
| **otra_enfermedad_otra_especie** | 17 clases de enfermedad de PlantDoc (sarna, royas, manchas, tizones, virus, moho) | 1.391 | ≈1.391 (53 marcadas como duplicado) | Solo vale para "alarma sí/no"; no sirve para exactitud por clase |
| **sana_otra_especie** | PlantDoc: hojas sanas de manzano, pimentón, cerezo, durazno, frambuesa, soya, fresa, tomate y vid | 733 | ≈733 (8 duplicadas) | Simula maleza u otra planta frente a la cámara |
| excluir | PlantDoc `Tomato two spotted spider mites leaf` | 2 | — | Ácaros: fuera de foco |

Total PlantDoc: **2.578 imágenes** (2.342 train / 236 test, 28 carpetas de clase). El artículo reporta 2.598 imágenes y 27 clases (Singh et al. 2020). La diferencia no está explicada en la fuente.

### Revisión visual de PlantDoc `Blueberry leaf` (117 imágenes)

La hice yo, Claude, mirando hojas de contacto. **No es una revisión agronómica: NO VERIFICADO por un agrónomo.** Está en `resultados/secundarios/triage_visual_plantdoc_blueberry.csv`, y los recortes heredan la etiqueta en la columna `revision_visual` del manifiesto.

| Etiqueta visual | Imágenes (train/test) | Recortes (todos) |
|---|---|---|
| verde_sin_sintomas_visibles | 65 (58/7) | 496 |
| coloracion_rojiza_otono_o_brotes | 27 (26/1) | 209 |
| sintomas_o_desorden_visible (manchas, clorosis, necrosis, "Damage", "Disease", deficiencia de Fe) | 19 (16/3) | 89 |
| dudosa (insecto visible, hojas amarillentas, texto superpuesto) | 3 | 9 |
| no_apta (hojas secas, clipart) | 3 | 46 |

Según los nombres de archivo, las especies incluyen *V. corymbosum*, *V. angustifolium*, *V. myrtilloides*, *V. ovalifolium*, *V. alaskaense* y *V. myrtillus*. No todas son arándano alto cultivado.

## 3. Hallazgos de calidad que afectan la evaluación

1. **PlantVillage infla el N.** Las 1.502 fotos de arándano son 160 hojas físicas. Un intervalo calculado sobre 1.502 sería falsamente estrecho. Hay que agregar por `leaf_id`, por ejemplo con la probabilidad media de enfermedad por hoja.
2. **Cambio de dominio documentado.** Mohanty et al. (2016) reportan 99,35% de exactitud en el test de PlantVillage, pero solo 31,40% y 31,69% con imágenes de otras fuentes. Singh et al. (2020, PlantDoc, Tablas 1 y 2) reportan que entrenar en PlantVillage y probar en PlantDoc da 15,08% (VGG16, imagen completa) y entre 19,73% y 39,87% en recortes, según la arquitectura. Es la razón para probar el modelo de DrBerry fuera de su dominio y no fiarse solo de su test interno.
3. **Ruido y fugas en PlantDoc**, medidos con pHash sobre las 2.578 imágenes:
   - 55 grupos de imágenes idénticas (112 imágenes). De ellos, 27 aparecen con **clases distintas** (por ejemplo, la misma foto como "Corn Gray leaf spot" y como "Corn leaf blight", o como tizón temprano y tardío de la papa) y 14 cruzan train/test.
   - 78 pares casi duplicados (distancia de Hamming ≤6): 16 cruzan train/test y 35 están en clases distintas.
   - Las imágenes repetidas están marcadas en `duplicado_phash=si`. Deben excluirse.
4. **Los README se contradicen.** El README del repo de clasificación dice tener los recortes ("Cropped-PlantDoc"), pero contiene imágenes completas (2.578). El artículo describe 9.216 recortes. Los recortes se regeneraron aquí desde las cajas del repo de detección (8.469 + 452 cajas en total; se usaron 1.644 de 4 clases).
5. **Colisiones de nombre en macOS.** 6 pares de archivos de PlantDoc solo difieren en mayúsculas (2 de esos pares, es decir 4 archivos, están en Blueberry leaf). Al clonar en macOS, un archivo pisa al otro. Las 12 versiones se restauraron en `PlantDoc-Dataset_colisiones/`. En el árbol principal, esos 6 nombres **no deben usarse**: tienen el contenido del otro archivo del par. El manifiesto ya apunta a las versiones correctas.
6. **Copyright de terceros.** Muchas imágenes de PlantDoc son de stock con marca de agua (shutterstock, alamy, dreamstime). La licencia CC BY 4.0 del dataset no anula el copyright de esas fotos. Úsenlas solo para evaluación interna y **no las muestren en el pitch ni en la pantalla de la demo**.

## 4. Cómo usarlos en la evaluación (fuera del dataset)

Reglas:
- **No entrenar** con estos conjuntos. Si alguien usa alguno para entrenar o calibrar, deja de ser externo y debe anotarse.
- Reportar siempre **aparte** de la métrica principal de DrBerry.
- Usar solo **alarma sí/no** (cualquier clase de enfermedad = alarma). No calcular exactitud por clase en PlantDoc, por el ruido de etiquetas.
- Excluir `duplicado_phash=si` y `apto_lado_min_64=no`.
- Calcular el intervalo (Wilson o bootstrap) **por grupo**: `grupo` del manifiesto (`leaf:<id>` en PlantVillage, imagen de origen en los recortes de PlantDoc).

| Prueba | Conjunto (filtro del manifiesto) | Métrica | Lectura |
|---|---|---|---|
| **E1. Falsas alarmas en arándano sano, laboratorio** | PV `sana_arandano`, agregado por las 160 hojas | % de hojas con alarma | Con 160 hojas, si p≈10%, el IC95% es de ±4,6 pp (aproximación normal, cálculo propio). Con 0 alarmas, la cota superior es ≈3/160 = 1,9% (regla de tres) |
| **E2. Falsas alarmas en arándano sano, web** | recortes PlantDoc `sana_arandano` + `revision_visual=verde_sin_sintomas_visibles` + apto (451 recortes, 65 imágenes) | % de alarma, IC por imagen de origen | Es el más parecido a una hoja real frente a la cámara |
| **E3. Hojas rojizas y con síntomas** | recortes PlantDoc `sana_arandano` con `coloracion_rojiza...` (≈192 aptos) y `sintomas_o_desorden...` (89) | % de alarma | Las rojizas son una fuente esperable de falsas alarmas. Que aparezcan en la Sabana de Bogotá (sin otoño) está NO VERIFICADO. Con síntomas, la alarma es deseable aunque no sea una enfermedad entrenada |
| **E4. Oídio en otra especie** | PV cerezo (65 hojas), PV calabaza, recortes PlantDoc de calabaza (254) | % de alarma y % de predicción "oidio" | Solo mide si el modelo generaliza el patrón de micelio blanco. No prueba nada sobre el arándano |
| **E5. Alternaria (proxy débil)** | PV papa y tomato early blight (500 hojas), recortes PlantDoc (482) | % de alarma y % de predicción "alternaria" | Si es bajo, no implica que el modelo falle en el arándano: el síntoma es distinto |
| **E6. Enfermedad desconocida** | PlantDoc `otra_enfermedad_otra_especie` sin duplicados | % que el modelo llama "sana" | Es una estimación pesimista de los **casos no detectados** ante una enfermedad nueva |
| **E7. No es arándano** | PlantDoc `sana_otra_especie` | % de alarma y % que pasa una puerta "¿es arándano?" (por ejemplo, CLIP o un umbral de confianza) | Define qué hace el robot ante una maleza u otra planta |

Carga mínima, ejecutada desde `datos/`, no desde `raw/`:

```python
import pandas as pd
m = pd.read_csv("resultados/secundarios/manifest_secundarios.csv")
e2 = m[(m.fuente=="PlantDoc-OD-recorte") & (m.categoria_eval=="sana_arandano")
       & (m.revision_visual=="verde_sin_sintomas_visibles") & (m.apto_lado_min_64=="si")]
e1 = m[(m.fuente=="PlantVillage") & (m.categoria_eval=="sana_arandano")]   # agrupar por m.grupo (leaf:<id>)
# rutas relativas a /Users/santiagosantafe/Downloads/SabanaHack/datos
```

Preprocesamiento: PlantVillage es de 256x256 y PlantDoc tiene tamaño variable (mediana de Blueberry: 1200x957). Usen el mismo redimensionado que en el entrenamiento con DrBerry. El fondo gris uniforme de PlantVillage es un atajo conocido: si el modelo acierta mucho en E1 pero falla en E2, el problema es el fondo.

## 5. Licencias y cómo citar

- **PlantDoc**: CC BY 4.0. Citar: Singh D., Jain N., Jain P., Kayal P., Kumawat S., Batra N. (2020). *PlantDoc: A Dataset for Visual Plant Disease Detection*. CoDS-COMAD 2020, pp. 249–253. doi:10.1145/3371158.3371196. Las imágenes de stock conservan el copyright de terceros (ver hallazgo 6).
- **PlantVillage**: CC BY-SA 3.0, según la tarjeta de HF `mohanty/PlantVillage`. El repo de GitHub no declara licencia. Si se redistribuye un derivado, ShareAlike obliga a usar la misma licencia. Citar: Hughes D.P. y Salathé M. (2015), arXiv:1511.08060, y Mohanty S.P., Hughes D.P. y Salathé M. (2016), *Front. Plant Sci.* 7:1419, doi:10.3389/fpls.2016.01419.
- No redistribuir ninguno de los dos. Para la demo, usar las imágenes de DrBerry.

## 6. Límites

- No hay **Heliothis** ni daño en fruto en ninguno de los dos datasets: son solo hojas. Tampoco hay **oídio ni alternaria en arándano**.
- La revisión visual de PlantDoc Blueberry la hizo una IA, no un agrónomo.
- La correspondencia entre "Squash Powdery mildew" y el oídio del arándano (*Erysiphe vaccinii*, nombre NO VERIFICADO en esta sesión), o entre "Early blight" y la Alternaria del arándano, es de tipo de síntoma, no de patógeno. NO VERIFICADO que el aspecto visual sea comparable.
- PlantVillage Squash PM no tiene `leaf_id`, así que su tamaño efectivo es desconocido.
- La procedencia de las fotos de PlantDoc no está documentada (fecha, lugar, cámara), así que no se sabe qué tan representativas son.

## 7. Fuentes que abrí

- https://github.com/pratikkayal/PlantDoc-Dataset (clon, README.md, LICENSE.txt y API `api.github.com/repos/pratikkayal/PlantDoc-Dataset`)
- https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset (clon parcial: README, LICENSE, CSV)
- https://arxiv.org/abs/1911.10317 y PDF (`raw/plantdoc/paper/1911.10317.pdf`): Tablas 1–3 y sección 3.1
- https://api.roboflow.com/joseph-nelson/plantdoc (metadatos; la página universe.roboflow.com devolvió 403)
- https://github.com/spMohanty/PlantVillage-Dataset (README.md, README_HF.md, CITATION.cff, clon parcial)
- https://huggingface.co/api/datasets/mohanty/PlantVillage (licencia `cc-by-sa-3.0`) y `.../resolve/main/splits/color_{train,test}.txt`
- https://www.tensorflow.org/datasets/catalog/plant_village (no declara licencia del dataset; 54.303 ejemplos; v1.0.2)
- https://arxiv.org/abs/1511.08060 (el resumen no declara licencia para las imágenes; el artículo está bajo CC BY-NC-SA 4.0 en arXiv)
- https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2016.01419/full (99,35% vs 31,40%/31,69%; "controlled conditions"; artículo CC BY)
