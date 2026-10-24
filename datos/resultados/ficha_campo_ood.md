# Ficha del conjunto de prueba fuera de DrBerry (`campo_ood`)

Preparada por el agente `adquisicion-campo-ood` el 2026-10-23. Las cifras salen de los archivos descargados, del manifiesto o de las APIs consultadas. Lo que no está verificado lleva la marca SUPUESTO o NO VERIFICADO.

## 1. Para qué sirve

Es un conjunto pequeño de fotos reales de campo, todas ajenas a DrBerry. Sirve para medir cuánto cae el clasificador entrenado con DrBerry fuera de su finca, su día y sus cámaras.

DrBerry es una sola finca de Sayán (Lima, Perú), fotografiada en una sola sesión de unas 2 h y con fuga por ráfagas entre splits (ver `resultados/ficha_drberry.md`). Este conjunto, en cambio, usa **una foto por observación**, de **observaciones y autores distintos**, de varios países, años y estaciones. Por eso sirve como prueba de generalización independiente.

## 2. Ubicación y estructura

```
raw/campo_ood/
  manifiesto.csv              <- una fila por imagen ACEPTADA (231). Columnas: ruta, clase, fuente, nivel_etiqueta,
                                 taxon_identificado, hospedero_declarado, obs_id, photo_id, quality_grade,
                                 cultivado_captive, lugar, lat, lon, fecha, autor, licencia, atribucion, URLs, md5
  sana/  oidio/  roya/  heliothis_oruga/  alternaria/      <- imágenes aceptadas (jpg, lado mayor <= 1280 px)
  _descartadas/<clase>/ + _descartadas/descartes.csv       <- 245 descartadas, con el motivo de cada una
  _revision_hojas_contacto/   <- hojas de contacto numeradas que se usaron en la revisión manual + índice
  _api/                       <- respuestas crudas de la API de iNaturalist y registro de consultas (_query_log.json)
raw/fresa_afzaal2021_datasetninja/   <- dataset de fresa de Afzaal et al. 2021 (proxy), con indice_imagenes.csv
raw/fresa_mendeley_k2ptxmfjhj_test/  <- split test del dataset de Mendeley (proxy), con indice_imagenes.csv
```

Los scripts para reproducir todo están en `reportes/adquisicion-campo-ood_scripts/`.

## 3. Conteos finales

| Clase | Aceptadas | Observaciones independientes | Autores distintos | Nivel de etiqueta | Fuente |
|---|---|---|---|---|---|
| sana | **60** | 60 | 60 | Especie *V. corymbosum* verificada + revisión visual sin síntomas | iNat 58 (46 research, 12 cultivadas), Commons 2 |
| oidio | **57** | 57 | 55 | **Estricta**: *Erysiphe vaccinii*, grado research | iNat 57 |
| roya | **60** | 60 | 54 | **Estricta**: *Naohidemyces vacciniorum* 55, *Pucciniastrum minimum* (= *Thekopsora minima*) 3, Commons 2 | iNat 58, Commons 2 |
| heliothis_oruga | **51** | 51 | 36 | **Proxy**: orugas de Lepidoptera (no Heliothinae) sobre Vaccinium, o su daño | iNat 50 (25 research, 25 needs_id), Commons 1 |
| alternaria | **3** | **2** | 2 | **No verificada** (needs_id) | iNat 3 |
| **Total** | **231** | | | | |

- **Alternaria no es evaluable.** Solo hay 3 fotos de 2 observaciones, ambas sin confirmar por la comunidad. En una de ellas también hay galerías de minador en la hoja. Se puede usar solo como ejemplo cualitativo.
- **No hay ni una observación con licencia abierta de Heliothinae (*Helicoverpa*, *Heliothis*, *Chloridea*) sobre Vaccinium.** Se buscó en 396 observaciones de Heliothinae con planta hospedera declarada (ninguna en Vaccinium) y por texto ("blueberry", "Vaccinium", "arándano", "mirtilo"). Solo salieron 3, y eran adultos en lugares llamados "Blueberry". Por eso la clase es un proxy de "oruga o daño de oruga en arándano".
- Tamaño de las imágenes: lado menor con mediana de 768 px (mínimo 357 px), y lado mayor de 1.024 a 1.280 px. Son las versiones "large" de iNaturalist y miniaturas de 1.024 px de Commons.

## 4. Cómo se construyó

1. **Fuentes:** la API pública de iNaturalist (`https://api.inaturalist.org/v1/observations`, sin login) y la API de Wikimedia Commons (`https://commons.wikimedia.org/w/api.php`). Solo se usaron fotos con licencia `cc0`, `cc-by`, `cc-by-sa`, `cc-by-nc` o `cc-by-nc-sa`. Se excluyeron las ND y "todos los derechos reservados". Las fotos se bajaron de `inaturalist-open-data.s3.amazonaws.com`. Todas las consultas, con su URL y su total, están en `raw/campo_ood/_api/_query_log.json`.
2. **Consultas por clase:**
   - oidio: taxón 765061 (*Erysiphe vaccinii*), grado research. Hubo **31 candidatas descartadas por taxonomía antes de mirarlas**. iNaturalist agrupa en *E. vaccinii* formas que viven en otros hospederos: f. *elevata* en *Catalpa* (24), f. *epigaeae* en *Epigaea* (6) y f. *convertibilis* (1). Solo se aceptan la especie y la f. *vaccinii*, y se excluyen las observaciones cuyo campo "Host Plant ID" no es Vaccinium.
   - roya: taxones 628810 (*Naohidemyces vacciniorum*) y 1706161 (*Pucciniastrum minimum*; iNat lo devuelve al buscar *Thekopsora minima*), grado research. Se excluye el hospedero declarado *Tsuga*.
   - sana: taxón 52740 (*V. corymbosum*) con la anotación "hojas verdes" (term 36 = 38). Se toman las de grado research y las cultivadas (captive). El grado casual de las cultivadas se debe solo a que la planta es cultivada.
   - heliothis_oruga: Lepidoptera (47157) con el campo "Host Plant ID" igual a alguna de las 23 especies de Vaccinium o al género. Se excluyen los minadores (Gracillariidae, Nepticulidae, Heliozelidae, Coleophora, etc.) y los registros anotados como adulto, pupa o huevo.
   - alternaria: *Alternaria* (327996) con "blueberry", "Vaccinium" o "arándano" en el texto, o con hospedero Vaccinium.
   - Commons: búsqueda por texto. Se tomaron 2 fotos de Forest y Kim Starr de arándano southern highbush cv. Misty con roya (Maui, CC BY 3.0 US), *N. vacciniorum* sobre *V. oxycoccos* (CC BY 2.0), una larva de *Acrobasis vaccinii* en frutos (UGA Plant Pathology Archive, CC BY 3.0 US) y 8 candidatas de hoja sana.
3. **Muestreo:** una foto por observación (la primera, sin elegir por contenido) y reparto por turnos entre autores, con un máximo de 2 a 6 por autor según la clase. La semilla es fija. Se bajaron 90 candidatas por clase (160 para sana) y se aplicó un **tope de 60 por clase**. Al recortar se sacó primero del autor más repetido. En sana se priorizaron las plantas cultivadas.

## 5. Revisión manual (punto 3 del encargo)

Revisé **todas** las candidatas, no solo una muestra, mirando hojas de contacto numeradas con la herramienta de lectura de imágenes. Son 476 candidatas en total. Algunas fotos dudosas se miraron a tamaño completo. **No es una revisión agronómica: NO VERIFICADO por un fitopatólogo.** Se descartaron 245 imágenes; los motivos están en `_descartadas/descartes.csv`.

| Clase | Candidatas | Descartadas | Etiqueta claramente errónea o fuera del arándano | Motivos principales |
|---|---|---|---|---|
| oidio | 121 | 64 | **38**: 31 por taxonomía (formas de *E. vaccinii* en *Catalpa*, *Epigaea*, etc.), 4 hojas de *Catalpa* que se colaron con ID a nivel de especie y 3 que no parecen Vaccinium | síntoma no visible (12), plano general (11), herbario (1), duplicado (1), mancha necrótica que no es micelio (1) |
| roya | 93 | 33 | **22**: aecios en acículas de *Tsuga*, el hospedero alterno. Es el mismo hongo, pero no es hoja de arándano | síntoma no visible o ambiguo (8), plano general (1), foto con lupa (1), tope de 60 (1) |
| heliothis_oruga | 77 | 26 | **4**: ilustración (1), adulto (1), minador (1) y foto sin larva ni daño (1) | larva fuera de la planta, en mano, papel o mesa (12); hoja desprendida sobre fondo de laboratorio (5); sin larva o daño claro (5) |
| alternaria | 17 | 14 | **12**: una observación de tallos y microscopía en la que el observador reporta **picnidios**, que no son estructuras de *Alternaria*. Se considera ID dudosa | plano general con agujeros (1) y foto repetida de la misma observación (1) |
| sana | 168 | 108 | **5** con daño o manchas visibles (no son "sanas"), 1 de herbario y 5 con follaje rojizo u otoñal | flor, fruto, planta lejana o maceta (84); tope de 60 (8); otras de calidad (desenfocada, oscura, sin hojas, plano general, posibles manchas: 5) |

**Resumen:** 81 descartes (38 + 22 + 4 + 12 + 5) por etiqueta errónea o por hospedero o estadio que no corresponde. El resto se descartó porque la foto no sirve para un clasificador de hoja: síntoma invisible, plano general, flor o fruto como protagonista, larva fuera de la planta, etc.

**Calidad del muestreo de fresa:** revisé visualmente 16 imágenes del split test de Afzaal (4 por clase: moho gris, antracnosis, oídio de hoja y oídio de fruto) y 4 "Asymptomatic" de Mendeley. No vi etiquetas claramente erróneas. En 2 de las 4 de oídio de hoja el síntoma casi no se ve en miniatura, y 2 de las 4 de antracnosis están sobre fondo de estudio azul, no en campo. La hoja está en `_revision_hojas_contacto/fresa_00.jpg`.

## 6. Representatividad y sesgos (importante para la rúbrica)

1. **Geografía y clima.** Todo viene de zonas templadas del hemisferio norte, salvo 3 fotos de roya de Nueva Zelanda. Las latitudes van de 28° a 69°.
   - oidio: EE. UU. 48 y Canadá 9.
   - sana: EE. UU. 46, Canadá 4 y unas pocas de Europa y Asia.
   - roya: Europa del norte (Suecia, Finlandia, Rusia, Alemania, Reino Unido, etc.) ≈40 y EE. UU. 12.
   - **No hay ni una foto tropical, andina ni de la Sabana de Bogotá**, y tampoco de Perú. El dominio de la demo (Colombia, unos 2.600 m s. n. m.) queda fuera de los dos conjuntos.
2. **Arándano silvestre frente a cultivado.** En oídio, roya y orugas los hospederos son sobre todo **Vaccinium silvestres** (*V. parvifolium*, *V. pallidum*, *V. myrtillus*, *V. angustifolium*, *V. arboreum*, *V. membranaceum*, etc.), no highbush comercial. Solo 13 de las 60 sanas son plantas cultivadas (12 captive de iNat + 1 cultivar de Commons), y 2 fotos de roya son de highbush cultivado (Maui). La forma de la hoja, el brillo y el tamaño cambian con la especie.
3. **Patógeno de roya.** 55 de las 60 fotos son de *Naohidemyces vacciniorum*, una roya boreal de Vaccinium silvestre. La roya registrada en cultivos de Colombia es *Thekopsora minima*, de la que aquí solo hay 3 fotos (*P. minimum* en iNat). Que las fotos Starr de Maui sean *T. minima* está NO VERIFICADO. Los síntomas son parecidos: pústulas anaranjadas en el envés y manchas rojizas en el haz. Es un parecido visual, no una equivalencia.
4. **El síntoma no coincide con DrBerry.**
   - Según la ficha de DrBerry, su "Oidio" se ve sobre todo como manchas rojizas o púrpuras (NO VERIFICADO agronómicamente). Aquí el oídio es sobre todo **micelio blanco y polvoriento**, con unas 10 fotos (conteo visual aproximado) de hojas rojizas o púrpuras con parches blancos.
   - "Heliothis" en DrBerry es **daño con agujeros**. Aquí la clase muestra sobre todo **la larva visible** (Datana, Hyphantria, Acronicta, geométridos, slug caterpillars, etc.) y algunas hojas enrolladas o esqueletizadas.
   - Hay que esperar una caída fuerte por estas dos diferencias, y explicarla como **cambio de dominio de síntoma**, no solo de cámara.
5. **Encuadre.** Hay hojas en la planta, hojas en la mano y algunos primeros planos con macro. Se descartaron los planos generales, la microscopía y el fondo de laboratorio. No es la vista de un robot a la altura de la cama: es la de una persona que se agacha a fotografiar el síntoma.
6. **Sesgo de selección de iNaturalist.** La gente fotografía lo llamativo. Los casos graves y vistosos están sobrerrepresentados y faltan los casos tempranos y sutiles, que son los que importan para "detectar a tiempo". La sensibilidad medida aquí probablemente es **optimista** frente a infecciones tempranas (SUPUESTO).
7. **Calidad de la etiqueta.**
   - Grado research significa que al menos 2/3 de los identificadores coinciden a partir de fotos. **No hay confirmación de laboratorio** (NO VERIFICADO).
   - La mitad de las orugas son needs_id (el taxón de la larva no está confirmado). Lo que sí declara el observador es el hospedero Vaccinium, y la larva o el daño se ven en la foto.
   - "sana" es una etiqueta débil: la especie está verificada, pero la "ausencia de síntomas" es solo mi revisión visual en miniatura.
8. **Estación.** Las fotos son de julio a octubre del hemisferio norte (verano y otoño). Las sanas son de mayo a agosto. Se descartaron las hojas otoñales rojas en "sana", pero siguen apareciendo en oídio y roya (hojas rojizas con síntoma). Hay riesgo de que el modelo aprenda "rojo = enfermo".
9. **Años:** sobre todo 2024 a 2026. Hay 16 fotos anteriores a 2018.
10. **Licencias no comerciales.** 158 de 231 imágenes son CC BY-NC o BY-NC-SA. Se pueden usar para evaluación interna en el hackathon, pero **no deben entrar en un producto comercial** sin revisarlo.

## 7. Cómo usarlo en la evaluación (propuesta)

Una foto por observación hace que cada imagen sea una unidad independiente. Esto no pasa en DrBerry, donde hay ráfagas.

| Clase OOD | Pregunta que responde | Métrica |
|---|---|---|
| sana (60) | ¿Cuántas falsas alarmas da fuera de la finca? | % predicho como cualquier enfermedad (FPR), con IC 95 % |
| oidio (57) | ¿Detecta el oídio fuera de dominio? | Sensibilidad "alarma" (cualquier clase ≠ sana) y sensibilidad "oidio" exacta |
| roya (60) | **Enfermedad no entrenada**: ¿pasa como sana? | % predicho "sana" = casos no detectados ante una enfermedad nueva |
| heliothis_oruga (51) | ¿Alerta ante orugas o su daño? | % de alarma y % "Heliothis" (proxy; leer junto con §6.4) |
| alternaria (3) | — | Solo cualitativo; no reportar porcentaje |

Lo que permite concluir este tamaño de muestra (IC exacto de Clopper-Pearson al 95 %, cálculo propio):
- Con n = 60, si se detectan 60 de 60, el límite inferior de la sensibilidad es 94,0 %; con 59 de 60 es 91,1 % y con 58 de 60 es 88,5 %. **Para afirmar una sensibilidad ≥ 90 % hace falta que se escape como mucho 1 de 60.**
- Con n = 57 (oidio): con 57 de 57 el límite inferior es 93,7 % y con 56 de 57 es 90,6 %.
- Con n = 51 (orugas): con 51 de 51 es 93,0 % y con 50 de 51 es 89,6 %.
- Falsas alarmas en 60 sanas: con 0 alarmas, el límite superior del IC es 6,0 %; con 1, 8,9 %; con 3, 13,9 %.

Preprocesamiento: hay que usar el mismo redimensionado que con DrBerry (DrBerry está estirada a 1024x1024). Conviene probar también el recorte centrado, porque las fotos de iNat no son cuadradas.

Complemento: la ficha `resultados/ficha_secundarios.md` (de otro agente) cubre PlantDoc y PlantVillage. Su hoja sana web de PlantDoc y este conjunto se pueden reportar lado a lado. No se comprobó si hay solapamiento de imágenes entre PlantDoc y iNaturalist (NO VERIFICADO; es poco probable).

## 8. Fresa como proxy (Botrytis, antracnosis, oídio)

| Dataset | Ruta | Licencia | Contenido | Uso sugerido |
|---|---|---|---|---|
| Afzaal et al. 2021, *Sensors* 21(19):6565, DOI 10.3390/s21196565, mirror de Dataset Ninja | `raw/fresa_afzaal2021_datasetninja/extraido/{train,val,test}/{img,ann}` + `indice_imagenes.csv` | **CC BY 4.0**, según `LICENSE.md` del repo `github.com/dataset-ninja/strawberry-disease-detection`, que cita el artículo. No se pudo ver la licencia en Kaggle porque exige login | 2.500 imágenes (train 1.450, val 307, test 743), 7 clases con polígonos. **Test:** gray_mold 145, anthracnose_fruit_rot 36, powdery_mildew_leaf 151, powdery_mildew_fruit 43, leaf_spot 162, angular_leafspot 147, blossom_blight 62. Solo 9 imágenes son multiclase | Proxy visual de Botrytis (gray_mold), antracnosis y oídio. **No trae clase sana** |
| Galarza-Falfán et al., Mendeley Data k2ptxmfjhj v1 (2025), DOI 10.17632/k2ptxmfjhj.1 | `raw/fresa_mendeley_k2ptxmfjhj_test/` (solo el split **test** de "traditional augmentation") + `indice_imagenes.csv` + `_mendeley_metadata.json` | **CC BY-NC 4.0** (API de Mendeley) | 463 imágenes de 640x640 en COCO, unas 58 por clase, incluida **"Asymptomatic Strawberry" (58)** | Aporta la clase "sana" que le falta a Afzaal |

Avisos:
- El dataset de Mendeley es una **extensión aumentada** de Afzaal y de Pérez-Borrero et al. 2020. Su split train tiene imágenes sintéticas generadas con DALL·E 3. Por eso **solo se bajó el test**: 27 MB de 579 MB y 10.207 archivos.
- 248 de sus 463 imágenes de test llevan el nombre original de una imagen de Afzaal, y 135 de ellas son del **train** de Afzaal. **No mezclar los dos conjuntos** en entrenamiento y prueba sin deduplicar.
- Pueden ser copias recortadas o aumentadas (rotaciones, brillo) y no solo copias exactas (NO VERIFICADO).
- La licencia del componente Pérez-Borrero (StrawDI) no se verificó.
- **La fresa no es arándano.** Sirve para probar un detector de pudrición o moho de fruto como prueba de concepto, o como prueba de estrés. **No sirve para medir la sensibilidad del clasificador de arándano.**
- Parte de las imágenes de Afzaal están sobre fondo de estudio, según lo visto en la muestra revisada.

## 9. Licencias y atribución

- Cada imagen aceptada tiene en `manifiesto.csv` la licencia, el autor y la URL de la observación y de la foto.

| Licencia | Imágenes |
|---|---|
| CC BY-NC | 147 |
| CC BY | 55 |
| CC BY-NC-SA | 11 |
| CC BY-SA | 11 |
| CC0 | 7 |

- **No redistribuir** el conjunto ni publicarlo en el repo del equipo. Si se muestran fotos en el pitch, hay que poner la atribución (columna `atribucion`). Las BY-SA obligan a compartir igual las obras derivadas, y las NC excluyen el uso comercial.
- Citas: iNaturalist (observaciones individuales, ver el manifiesto), Wikimedia Commons (autores en el manifiesto), Afzaal et al. 2021 (CC BY 4.0) y Galarza-Falfán et al. 2025 (Mendeley, CC BY-NC 4.0).

## 10. Límites y pendientes

- **Alternaria en arándano sigue sin datos OOD.** Pendiente buscar a mano en Bugwood/IPM Images (`ipmimages.org`, muchas fotos con CC BY-NC 3.0). La búsqueda automática no funcionó: la página es dinámica y la API no filtra por texto.
- **Heliothis/Helicoverpa en arándano:** no hay fotos abiertas. Si el equipo consigue fotos propias o de un agrónomo colombiano, hay que agregarlas como clase estricta.
- **Tropical o andino:** no hay. La mejor prueba de representatividad sería capturar 20 a 30 hojas reales de un cultivo de la Sabana. Fuera del alcance (SUPUESTO: no hay acceso a plantas en el hackathon).
- La revisión visual no reemplaza a un fitopatólogo. Las etiquetas "sana" son las más débiles.
- No se usó la API key de Roboflow: no hizo falta.
