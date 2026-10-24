# Reporte del agente `adquisicion-campo-ood`

Fecha: 2026-10-23. Encargo: armar un conjunto pequeño de prueba con fotos reales de campo, ajenas a DrBerry, y conseguir un dataset de fresa como proxy. La ficha técnica completa está en `resultados/ficha_campo_ood.md`.

## Qué hice

1. **iNaturalist (API pública, sin login).**
   - Busqué los IDs de taxón y bajé los metadatos de las observaciones con foto con licencia abierta: CC0, BY, BY-SA, BY-NC y BY-NC-SA. Excluí las ND.
   - Los taxones fueron *Erysiphe vaccinii*, *Naohidemyces vacciniorum*, *Pucciniastrum minimum* (= *Thekopsora minima*), *V. corymbosum* con hoja verde, Lepidoptera con hospedero Vaccinium declarado, Heliothinae y *Alternaria*.
   - Resolví el hospedero declarado (campo "Host Plant ID") para filtrar lo que no es Vaccinium.
2. **Muestreo.** Una foto por observación, repartiendo por turnos entre autores y con semilla fija. Bajé entre 90 y 168 candidatas por clase, en tamaño "large" de iNat (≤1.024-1.280 px).
3. **Wikimedia Commons (API pública).** Agregué 13 candidatas: 2 de roya en southern highbush cultivado en Maui (Starr), 1 de roya en *V. oxycoccos*, 2 de orugas y 8 de hoja sana. Me topé con el rate-limit de la API; bajé el ritmo y no reintenté en bucle.
4. **Revisión manual de las 476 candidatas.** Hice hojas de contacto numeradas, las miré con la herramienta Read y abrí a tamaño completo las dudosas. Descarté 245 y registré el motivo de cada una. Eso dejó 231 imágenes en `raw/campo_ood/<clase>/`.
5. **Fresa.**
   - Encontré el mirror público de Afzaal et al. 2021 en Dataset Ninja: un enlace directo sin login de 409 MB (`DOWNLOAD.md` del repo de GitHub). Lo bajé y lo extraje después de comprobar que el tar no traía rutas peligrosas ni symlinks.
   - Del dataset de Mendeley k2ptxmfjhj (579 MB, 10.207 archivos, aumentado y con imágenes sintéticas en train) bajé solo el split test: 464 archivos, 27 MB, con verificación SHA-256.
   - Construí un índice por imagen para cada dataset y revisé a ojo una muestra de 20.
6. Intenté buscar Alternaria en arándano en Bugwood/IPM Images. Los resultados no se pudieron filtrar por texto, así que no saqué nada (queda como pendiente).

## Archivos producidos

- `raw/campo_ood/manifiesto.csv`: 231 imágenes aceptadas, con clase, fuente, nivel de etiqueta, taxón, hospedero, grado, cultivada o no, lugar, lat/lon, fecha, autor, licencia, atribución, URL de la observación y de la foto, y md5.
- `raw/campo_ood/{sana,oidio,roya,heliothis_oruga,alternaria}/`: las imágenes.
- `raw/campo_ood/_descartadas/` y `descartes.csv`: 245 imágenes, con su motivo.
- `raw/campo_ood/_revision_hojas_contacto/`: 33 archivos (hojas de contacto e índices), como evidencia de la revisión.
- `raw/campo_ood/_api/`: respuestas crudas de la API y `_query_log.json`, con cada URL consultada y su total.
- `raw/fresa_afzaal2021_datasetninja/`: el tar, `extraido/` y `indice_imagenes.csv`.
- `raw/fresa_mendeley_k2ptxmfjhj_test/`: 463 jpg, `_annotations.coco.json`, `_mendeley_metadata.json` e `indice_imagenes.csv`.
- `resultados/ficha_campo_ood.md`: conteos, licencias, representatividad, sesgos y cómo evaluar.
- `reportes/adquisicion-campo-ood_scripts/`: todos los scripts, que se ejecutan con `python3 -I`.

## Resultados

| Clase | Aceptadas | Nivel de etiqueta |
|---|---|---|
| sana | 60 | *V. corymbosum* verificado + revisión visual. 13 son plantas cultivadas |
| oidio | 57 | Estricta (*E. vaccinii*, research) |
| roya | 60 | Estricta (55 *N. vacciniorum*, 3 *T. minima*, 2 Commons) |
| heliothis_oruga | 51 | **Proxy**: orugas no Heliothinae sobre Vaccinium |
| alternaria | 3 (2 obs.) | No verificada: **no evaluable** |

**Etiquetas claramente erróneas o fuera del arándano descartadas: 81.**
- 31 en oídio por taxonomía: formas de *E. vaccinii* sobre *Catalpa*, *Epigaea*, etc.
- 7 más en oídio a ojo: hojas de *Catalpa* o de otra planta.
- 22 en roya: aecios en acículas de *Tsuga*.
- 4 en orugas: ilustración, adulto, minador y foto sin larva ni daño.
- 12 en alternaria: ID dudosa, el observador reporta picnidios.
- 5 en sana: hojas con daño o manchas.

Las otras 164 se descartaron porque no sirven para un clasificador de hoja: plano general, flor o fruto, larva fuera de la planta, síntoma invisible, etc.

**Fresa:**
- Afzaal tiene 2.500 imágenes. Su test trae gray_mold 145, antracnosis 36, oídio de hoja 151 y oídio de fruto 43; no tiene clase sana.
- El test de Mendeley tiene 463 imágenes, unas 58 por clase, incluidas 58 "Asymptomatic".
- 248 nombres del test de Mendeley coinciden con imágenes de Afzaal, 135 de ellas del train de Afzaal: **hay riesgo de fuga si se combinan**.

**Lo que permite concluir el tamaño de muestra (Clopper-Pearson al 95 %):**
- Con 60 imágenes, una sensibilidad ≥ 90 % solo se puede afirmar si falla como mucho 1. Con 60 de 60, el límite inferior es 94,0 %; con 59 de 60, 91,1 %.
- Con 0 falsas alarmas en 60 sanas, la tasa de falsas alarmas queda por debajo de 6,0 %.

## Hallazgos que importan para el pitch

- **No existe ni una foto abierta de Heliothis/Helicoverpa sobre arándano** en iNaturalist ni en Commons. Tampoco hay casi nada de Alternaria en arándano. Esas dos clases de DrBerry no se pueden validar fuera de DrBerry con datos públicos. Es un hallazgo honesto para la sección de "Evidencia y validación".
- **Cambio de dominio de síntoma:**
  - El oídio OOD es micelio blanco; el de DrBerry se ve sobre todo como manchas rojizas, según `ficha_drberry.md`.
  - La clase de orugas OOD muestra larvas; la de DrBerry, agujeros.
  - Hay que esperar una caída y explicarla así.
- **La roya OOD sirve como "enfermedad no entrenada".** El % que el modelo llama "sana" es una medida directa de casos no detectados ante una enfermedad nueva.
- **Representatividad:** todo es de zona templada (EE. UU., Canadá y norte de Europa). No hay nada andino ni tropical, y la mayoría de los hospederos de oídio y roya son Vaccinium silvestres.

## Fuentes consultadas (URLs abiertas)

- iNaturalist API: `https://api.inaturalist.org/v1/taxa?q=...`, `https://api.inaturalist.org/v1/observations?...` (todas las URLs con su total en `raw/campo_ood/_api/_query_log.json`) y `https://api.inaturalist.org/v1/observations/species_counts?taxon_id=48353`. Fotos: `https://inaturalist-open-data.s3.amazonaws.com/photos/<id>/large.*`.
- Wikimedia Commons API: `https://commons.wikimedia.org/w/api.php` (list=search y prop=imageinfo|extmetadata). La URL de cada archivo está en el manifiesto.
- Dataset Ninja: `https://datasetninja.com/strawberry-disease-detection` (solo comprobé que responde con HTTP 200), `https://api.github.com/repos/dataset-ninja/strawberry-disease-detection` y `https://raw.githubusercontent.com/dataset-ninja/strawberry-disease-detection/main/{DOWNLOAD,LICENSE,CITATION,SUMMARY}.md`. Descarga desde `assets.supervisely.com/remote/...`, el enlace de `DOWNLOAD.md`.
- Mendeley: `https://data.mendeley.com/public-api/datasets/k2ptxmfjhj`, `https://data.mendeley.com/public-api/datasets/k2ptxmfjhj/folders/1`, `https://data.mendeley.com/datasets/k2ptxmfjhj` y las URLs de descarga `https://data.mendeley.com/public-files/datasets/k2ptxmfjhj/files/<id>/file_downloaded`.
- Bugwood (sin resultado útil): `https://www.ipmimages.org/search/action.cfm?q=alternaria%20blueberry` y `https://api.bugwood.org/rest/api/image/.json`.
- Kaggle (versión original de Afzaal): **omitido** porque exige login.

## Límites

- La revisión visual la hice yo sobre miniaturas: NO VERIFICADO por un fitopatólogo. "Sana" es la etiqueta más débil.
- Grado research no equivale a confirmación de laboratorio.
- Hay sesgo hacia casos vistosos y faltan las infecciones tempranas, así que la sensibilidad medida puede salir optimista (SUPUESTO).
- 158 de 231 imágenes tienen licencia NC: sirven para evaluación interna, no para un producto ni para redistribuirlas.
- El país del manifiesto (`pais_aprox`) se sacó del texto del lugar y es aproximado. Para lo exacto, usen lat/lon.
- No usé la API key de Roboflow (no hacía falta) y no la escribí en ningún archivo.

## Pendientes

1. Correr el clasificador entrenado con DrBerry sobre `raw/campo_ood/` y reportar FPR (sana), sensibilidad (oidio, heliothis_oruga) y % "sana" en roya, con IC exacto. Le corresponde al agente de evaluación.
2. Buscar a mano en Bugwood/IPM Images fotos CC de Alternaria y de *Helicoverpa* en arándano. Si el equipo tiene contacto con un agrónomo colombiano, pedirle 20 a 30 fotos propias de la Sabana.
3. Si se usa la fresa para entrenar, deduplicar Afzaal contra el test de Mendeley con hash perceptual antes de hacerlo.
