# Revisión crítica del documento del equipo (agente revision-documento)

Fecha: 2026-10-23. Documento revisado: "Berry Good Idea · Plan completo del equipo (Sabana Hack)", Claude Doc del proyecto `9c0a5374-f338-45a8-9ac1-6089724600e1`, cuerpo `0bfc15a1-bacf`, **revisión 22**. Lo leí completo (519 líneas, unos 49.500 caracteres) en modo solo lectura. **No edité el documento ni dejé comentarios.**

## Resultado en una línea

De unas 70 afirmaciones revisadas, hay **9 incorrectas**, **unas 20 imprecisas** y **unas 10 no verificables**; el resto son correctas. Los errores que más se ven son cuatro. Las cifras de área sembrada están mal atribuidas: lo oficial son 907 ha en 2025. El D1 EDU sí trae cámara y tiene IP54 según AgiBot. El SDK del D1 no tiene interfaz ROS. El "84 % de DrBerry" no es una línea base comparable. Las cuentas de la matriz, del beneficio B y de los puntos de equilibrio cuadran.

---

## 1. Lista priorizada

Escala de veredictos: CORRECTO / INCORRECTO / IMPRECISO / NO VERIFICABLE.

### Prioridad 1: lo que un jurado detectaría o lo que se dice en voz alta en el pitch

**1. Área sembrada en Colombia: "500 ha (Asocolblue) o ~1.000 ha (Forbes 2026)"**
- Secciones: El cultivo en Colombia (tabla), Advertencias, Pitch 0:00–0:40 ("500–1.000 ha").
- Veredicto: **INCORRECTO** (las dos fuentes están mal atribuidas).
  - Portal Frutícola (28-ene-2025) no menciona a Asocolblue ni las 500 ha. Dice 760 ha, citando al gerente de Agroventure Capital, y la expectativa de pasar de 1.500 ha.
  - Forbes (26-may-2026) no da ninguna cifra de área.
- Corrección propuesta: usar la cifra oficial. EVA 2025 (UPRA) da **906,7 ha sembradas, 664,7 ha cosechadas y 6.031 t**. Boyacá tiene 437 ha y Cundinamarca 420 ha (94,6 % entre las dos). La serie va de 265 ha en 2019 a 907 ha en 2025. Frase para el pitch: "unas 900 ha sembradas en 2025, casi todas en Boyacá y Cundinamarca (EVA-UPRA)".
- Fuentes: https://www.datos.gov.co/resource/uejq-wxrr.json (copia en `raw/revision_documento_eva/`), https://www.portalfruticola.com/noticias/2025/01/28/arandanos-en-colombia, https://forbes.co/2026/05/26/negocios/arandano-colombiano-el-sello-que-lanzo-el-sector-para-impulsar-el-consumo-y-exportacion/

**2. "El D1 EDU no trae cámara de fábrica" y "Sensores de fábrica: Ninguno; cámara y LiDAR opcionales"**
- Secciones: Robots (tabla AgiBot, filas D1 EDU y D1 Pro), Correcciones, Preguntas pendientes.
- Veredicto: **INCORRECTO**.
  - La ficha oficial D1 Pro/Edu lista "un cámara de 1920×1080, DFOV 122°, HFOV 111°, VFOV 70°" y una IMU.
  - La guía SDK V2.0.7 dice que el video de la "wide-angle camera" se publica por RTSP: `rtsp://192.168.234.1:8554/test` por wifi y `rtsp://192.168.168.168:8554/test` por cable.
  - El manual de usuario señala la "Front camera" en la cabeza.
- Corrección propuesta: "El D1 EDU trae una cámara frontal gran angular (1080p, 122° diagonal) accesible por RTSP; el LiDAR y la cámara de profundidad son opcionales." Esto responde la pregunta pendiente "¿Qué cámara tiene el D1?". Un gran angular de 122° deja pocos píxeles por hoja frente a una pantalla, así que la prueba de las 20 fotos es todavía más urgente.
- Fuentes: https://agibot.com/products/D1_Pro, https://www.agibot.com/filepage/299.html, ficha https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787630270608055.pdf y guía SDK https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787630535400794.pdf. Los dos PDF son idénticos en tamaño a las copias de `raw/agibot_docs/`.

**3. D1 EDU "IP32 (fuentes no coinciden)" y "El D1 EDU no tiene protección certificada"**
- Secciones: Robots (tabla), Operación y mantenimiento (Corrosión).
- Veredicto: **INCORRECTO** según el fabricante. La guía SDK oficial (especificaciones compartidas "D1 Edu & Ultra") da "Ingress Protection Rating IP54". El IP32 solo aparece en un blog de revendedor (openelab).
- Corrección propuesta: "IP54 según la guía SDK de AgiBot (un revendedor dice IP32)". IP54 no implica resistencia a fungicidas cúpricos, y ese riesgo se mantiene.
- Efecto en otra sección: el documento recomienda el D1 Ultra por "IP54, SDK abierto", pero el EDU tiene el mismo IP54 y la misma SDK (la guía aplica a los dos). Ver el punto 18.
- Fuentes: guía SDK (URL arriba), https://openelab.io/blogs/learn/agibot-d1-pro-vs-d1-edu-vs-d1-ultra

**4. "SDK + ROS 2, Python" (D1 EDU) y "Open SDK + ROS 2" (D1 Ultra)**
- Sección: Robots (tabla).
- Veredicto: **INCORRECTO** en cuanto a ROS 2. La guía SDK V2.0.7, en su FAQ 6.18 "Is There a ROS Interface?", responde: "Currently, there is no ROS interface available." Lo que sí hay:
  - SDK en Python 3.10 y C++.
  - Ubuntu 22.04 en máquina física (no WSL).
  - URDF para Isaac Sim y MuJoCo.
- Corrección propuesta: "SDK propio en Python/C++ (sin ROS); modelo URDF para Isaac Sim y MuJoCo."
- Fuentes: guía SDK (URL arriba), https://agibot.com/products/D1_Pro

**5. "Línea base publicada YOLOv5 84 %" y "comparar contra el 84 %"**
- Secciones: Datasets, Validación (capa 1), Pitch 3:45–4:30.
- Veredicto: **IMPRECISO**, y la comparación tal como está planteada no es válida.
  - El resumen del paper dice "accuracy of 84% and recall of 91%". Es un detector YOLOv5s entrenado con aumentación.
  - Sin aumentación, la tabla 2 da precisión 69,0 %, recall 44,5 % y mAP50 53,4 %.
  - La mejor configuración da 88 % / 94 % / 94 %.
  - El paper usó 544 imágenes (439 con una enfermedad y 105 con dos o más). La versión pública de Roboflow tiene 410.
  - El agente adquisicion-drberry encontró fuga por ráfagas entre los splits, así que es probable que esas métricas estén infladas.
- Corrección propuesta: "DrBerry reporta 84 % de precisión y 91 % de recall con YOLOv5s y aumentación (69 % y 45 % sin aumentación), sobre un split con fuga. Nuestro número sale de un split por grupos y es más difícil." En la diapositiva de evidencia, comparar el recall por clase con la tabla 2, no con un solo 84 %.
- Fuentes: https://scitepress.org/PublishedPapers/2023/122071 (PDF en `raw/drberry_paper/`), `resultados/ficha_drberry.md`

**6. "La pantalla muestra hojas del conjunto de prueba de DrBerry, que el modelo nunca vio"**
- Secciones: Demo en vivo (Montaje) y Validación (capa 1: "dividir DrBerry en entrenamiento y prueba").
- Veredicto: **INCORRECTO** si se usa el split original. El 86 % de las imágenes de test comparte ráfaga (fotos de la misma hoja tomadas con ≤ 10 s de diferencia) con train o valid, y la mediana de la distancia temporal a train es de 2 s.
- Corrección propuesta: usar `split_grupal_sugerido` de `resultados/drberry_imagenes.csv` y decirlo en el pitch.
- Riesgo para la meta: el test original solo trae 8 imágenes con Alternaria como clase dominante, 16 de Heliothis, 13 de oídio y 6 sanas. Con 8 casos, acertar 8 de 8 solo garantiza un recall ≥ 63 % (IC 95 %). La meta de "sensibilidad ≥ 90 %" no se puede demostrar con ese test, así que hay que reportar intervalos.
- Fuentes: `resultados/conteo_clases.csv`, `resultados/ficha_drberry.md` (agente adquisicion-drberry)

**7. DrBerry "Campo, Huaral (Perú)"**
- Sección: Datasets.
- Veredicto: **IMPRECISO**. El resumen dice "Huaral", pero el cuerpo del paper (sección 3.2.1) dice "Fundo San Roberto, distrito de Sayán, provincia de Huaura". Además:
  - Las fotos son de una sola finca y un solo día (2022-09-19), con tres celulares o cámaras.
  - Muchas hojas están desprendidas o en la mano, no en la planta.
- Corrección propuesta: "Fotos en finca (Sayán, Huaura, Perú), un día y tres cámaras; muchas hojas fuera de la planta." Esto pesa en el criterio de representatividad de la rúbrica.
- Fuentes: paper (URL arriba), `resultados/ficha_drberry.md`

**8. Thorvald: "control completo del oidio en 30 ha"**
- Secciones: Advertencias y Posicionamiento.
- Veredicto: **INCORRECTO** frente a la fuente citada. FarmingUK (16-dic-2021) habla de fresas en "over 10 hectares" en dos fincas de Kent, tratadas con UV-C. Las muestras "having no traces of the fungal disease" y la etiqueta "world-first" vienen del propio equipo de Thorvald. No dice que el robot diagnostique. Los 200 kg de peso del robot no aparecen en esa fuente.
- Corrección propuesta: "más de 10 ha de fresa en Kent (dato de la empresa, 2021)".
- Fuente: https://www.farminguk.com/news/robot-delivers-world-first-season-free-of-powdery-mildew-sprays_59536.html

**9. Antracnosis: "Miles et al. 2013, validado en arándano" y "20–30 °C y más de 12 h de mojadura"**
- Secciones: Enfermedades (tabla), Propuesta paso 1, Correcciones, Límites.
- Veredicto: **IMPRECISO**.
  - La cita es correcta: Miles, Gillett, Jarosz y Schilder 2013, *Plant Pathology* 62:1238–1247, doi 10.1111/ppa.12061.
  - Pero es un estudio en condiciones controladas sobre fruto de arándano. Encuentra un óptimo de **25 °C** y una infección que crece hasta **48 h** de mojadura, con ecuaciones gaussianas 3D (R² de 0,86 a 0,90).
  - El propio resumen dice que "lay the groundwork for a disease prediction model". No reporta validación en campo.
  - El umbral "20–30 °C y >12 h" no aparece en el resumen.
- Corrección propuesta: "modelo desarrollado con fruto de arándano en condiciones controladas (Miles 2013); usamos su ecuación, o una regla derivada marcada SUPUESTO".
- Falta en la sección "Lo que el jurado atacará": **METOS (Pessl) ya ofrece un modelo comercial de "blueberry anthracnose"** en FieldClimate, no solo de Botrytis. El diferenciador debe ser la confirmación cama por cama.
- Fuentes: https://api.openalex.org/works/doi:10.1111/ppa.12061 (resumen), https://metos.global/en/blueberry-production-with-metos-systems/. La página de MSU citada en el documento cargó vacía.

**10. Jornal "~75.900 COP con prestaciones, ~19 USD (TRM supuesta de 4.000)"**
- Secciones: El cultivo en Colombia (tabla) y Finanzas (variable w).
- Veredicto: **IMPRECISO** (COP) e **INCORRECTO** (USD).
  - Los 75.900 COP salen de SMMLV 2026 / 30 × 1,30 = 75.873 COP. El SMMLV es de 1.750.905 COP y sigue vigente según Portafolio (10-oct-2026).
  - El factor del 30 % viene del **proyecto de ley 504 de 2025**, que en el artículo de Actualícese es un proyecto radicado, no una ley. Su estado actual es NO VERIFICADO.
  - La TRM del 23-oct-2026 es **3.185,01 COP/USD** (promedio de los últimos 12 meses: 3.532), no 4.000. El jornal queda en unos **23,8 USD**.
- Efecto: B base sube de 1.830 a ~1.878 USD/ha/año, un efecto menor. Pero la TRM es un dato público que el jurado puede comprobar.
- Fuentes: https://www.datos.gov.co/resource/32sa-8pi3.json, https://www.portafolio.co/economia/gobierno/salario-minimo-de-2026-sigue-en-1-750-905-millones-tras-aclaracion-sobre-fallos-del-consejo-de-estado-504236, https://actualicese.com/proyecto-de-ley-que-busca-reglamentar-el-contrato-y-jornal-agropecuario-se-radico/

**11. "Perú FOB 6,22 USD/kg (2025)" (Gestión)**
- Sección: El cultivo en Colombia (tabla).
- Veredicto: **INCORRECTO**. El artículo no da precio por kg. Da 2.457 millones de USD y 373.514 t, lo que implica **6,58 USD/kg**.
- Corrección propuesta: "~6,6 USD/kg (cociente de valor y volumen, Gestión 2025)".
- Fuente: https://gestion.pe/economia/mercados/peru-consolida-liderazgo-mundial-en-arandanos-exportaciones-suman-usd-2457-millones-en-2025-noticia/

**12. "Rendimiento ~12 t/ha hoy" (Y = 12 t/ha en Finanzas)**
- Secciones: El cultivo en Colombia y Finanzas.
- Veredicto: **IMPRECISO**. Forbes dice "algunos cultivos siguen registrando rendimientos cercanos a 12 toneladas por hectárea", lo que no es un promedio. El promedio nacional EVA 2025 es **9,07 t/ha cosechada** (Boyacá 10,3 y Cundinamarca 8,5).
- Efecto: con Y = 9,07 t/ha, B base baja a ~1.478 USD/ha/año y el ROI neto del híbrido de 3,3× a ~2,4×.
- Corrección propuesta: dejar 12 t/ha como escenario "finca tecnificada" y mostrar también 9 t/ha (promedio nacional).
- Fuentes: Forbes y EVA (URLs arriba)

**13. Precio P = 4 / 6 / 8 USD/kg frente a "en finca 8–10 USD/kg" y "no usar precio de exportación"**
- Sección: Finanzas (tabla de variables y "Lo que el jurado atacará").
- Veredicto: **IMPRECISO (incoherencia interna)**.
  - El propio documento dice que el 95 % se vende local a 8–10 USD/kg en finca (Forbes, citando a Planasa) y que no hay que usar precio de exportación.
  - Aun así, la base es 6 USD/kg, casi igual al FOB de Perú.
  - La UNAD (citando a Afanador 2020) da un FOB colombiano de 7–9 USD/kg.
- Corrección propuesta: decir explícitamente que 6 USD/kg es un supuesto conservador, o subir la base a 8 USD/kg. Con P = 8, B base = 2.310 USD/ha/año.
- Fuentes: Forbes (URL arriba), https://repository.unad.edu.co/handle/10596/41047

### Prioridad 2: afecta las finanzas o la evidencia aunque se vea menos

**14. "L y f pesan el 90 % del resultado"**
- Sección: Finanzas.
- Veredicto: **IMPRECISO**. Y·P·L·f es el 78,7 % de B en el escenario base (1.440 de 1.830), el 85,5 % en el optimista y el 100 % en el pesimista.
- Corrección propuesta: "~80 % en el escenario base".
- Fuente: cálculo propio, `reportes/revision-documento_scripts/checks.py`

**15. Sensibilidad de la matriz: "si el costo pesa 30 % queda empatado con la red fija (81 contra 80)"**
- Sección: Matriz.
- Veredicto: **CORRECTO** para los pesos que se muestran, pero **IMPRECISO** como conclusión. El documento no solo sube el costo: también baja ubicación (20→15) y robustez (15→10). El resultado depende de qué pesos se bajan:

  | Pesos (anticipa, ubica, costo, encaje, robustez, registro) | B. Red fija | F. Híbrido |
  |---|---|---|
  | Documento: 20, 15, 30, 15, 10, 10 | 80 | 81 |
  | 15, 15, 30, 15, 15, 10 | 79 | 79 |
  | 20, 20, 30, 15, 10, 5 | 79 | 81 |
  | 20, 10, 30, 15, 15, 10 | **83** | 79 |
  | 20, 10, 40, 15, 5, 10 | **85** | 79 |

- Corrección propuesta: decir "con costo al 30 % y ubicación al 10 % gana la red fija". Así la frase del pitch "lo que inclina la balanza es saber en qué cama está el problema" queda demostrada con números. Hay otro detalle discutible: F (430 USD/ha/año) tiene el mismo puntaje de costo que A (320). Con costo = 2, F baja a 79 y sigue ganando con los pesos base.

**16. Costo por ha de D1 MaxPro y Genie G1 (2.100 y 2.200 USD/ha/año; "MaxPro en 20 ha: No")**
- Sección: Finanzas (tabla de configuraciones).
- Veredicto: **NO VERIFICABLE / no reproducible** con las cifras del documento.
  - Con los mismos supuestos que reproducen al D1 Ultra (inversión/3 años + O&M de 2.300–3.250 USD/año, en 20 ha), MaxPro da (91.800 + 1.500)/3 + 3.250 = **~1.720 USD/ha/año**. Eso es menor que B base (1.830), así que "No se paga" pasaría a "ajustado".
  - Genie G1 da ~1.880 en lugar de 2.200.
  - MaxPro como servicio para 60 ha da ~570 en lugar de 700.
  - La tabla parece usar un O&M de ~10.000 USD/año para estas plataformas que no está documentado.
- Corrección propuesta: publicar la hoja de cálculo con el O&M de cada plataforma.

**17. "ROI ~4,7×" y "ROI ~3,3×"**
- Sección: Finanzas.
- Veredicto: **CORRECTO** si ROI = (B − C)/C: (1.830 − 320)/320 = 4,72 y (1.830 − 430)/430 = 3,26. Pero el documento no da la fórmula, y B/C da 5,7 y 4,3.
- Corrección propuesta: escribir "ROI neto = (B − costo)/costo".

**18. "D1 Ultra: IP54, SDK abierto: recomendado" frente al D1 EDU**
- Secciones: Resumen, Precios, Pitch.
- Veredicto: **IMPRECISO**. Según la guía SDK, EDU y Ultra comparten IP54, SDK, batería (4,6 Ah, 1–2 h), carga útil de 5 kg y escalón de 16 cm. Las diferencias publicadas son:
  - peso: 15,5 kg (EDU) frente a 16 kg (Ultra);
  - velocidad: 3,5 m/s frente a 3,7 m/s;
  - control remoto con pantalla en el Ultra;
  - según un revendedor, una carga estática de unos 8 kg en el Ultra.
- Precio en la tienda oficial: EDU 6.080 USD y Ultra 9.600 USD.
- Corrección propuesta: justificar el Ultra o pasar a producción con el EDU. El ahorro sería de ~33 USD/ha/año sobre el costo FOB puesto en Colombia.
- Fuentes: guía SDK, https://store.agibot.com/products/d1-edu.json y https://store.agibot.com/products/d1-ultra.json, https://www.generationrobots.com/en/404439-agibot-d1-ultra-quadruped-robot.html

**19. D1 Ultra "15 kg" y batería "6 km sin carga, 4 km con 5 kg"**
- Sección: Robots (tabla).
- Veredicto: **IMPRECISO**. La guía SDK y el datasheet oficial dan **16 kg** (generationrobots dice 15 kg). La columna "Batería" trae alcance en km: la autonomía oficial es de 1–2 h (6 ± 1 km a 1 m/s sin carga).
- Corrección propuesta: "15–16 kg; 1–2 h (6 km sin carga, 4 km con 5 kg según revendedor)".
- Fuentes: guía SDK, generationrobots (URLs arriba)

**20. Botrytis: "15–25 °C, HR mayor a 90 %, 8 h o más de mojadura" (Bulger et al. 1987)**
- Sección: Enfermedades (tabla).
- Veredicto: **IMPRECISO**.
  - Bulger, Ellis y Madden 1987 (*Phytopathology* 77:1225–1230, doi 10.1094/Phyto-77-1225) ensayaron de 5 a 30 °C con hasta 32 h de mojadura en flores de fresa. Encontraron un óptimo de ~20 °C, 100 % de infección con 24 h de mojadura, y una infección muy reducida por encima de 25 °C y por debajo de 15 °C.
  - El rango de 15–25 °C es correcto, pero la HR > 90 % y el umbral de 8 h no salen de Bulger.
  - Para arándano, NCSU da 20–25 °C (68–77 °F) como ideal para la germinación.
- Corrección propuesta: "15–25 °C (Bulger 1987); HR > 90 % y 8 h son regla operativa nuestra (SUPUESTO)".
- Fuentes: https://www.ebi.ac.uk/europepmc/webservices/rest/search (resumen en `raw/revision_documento_europepmc/bulger1987.json`), https://content.ces.ncsu.edu/botrytis-gray-mold-blossom-blight-and-fruit-rot-of-blueberry. La página de APS citada en el documento devolvió 403.

**21. Roya (Thekopsora minima): "19–25 °C, rocío prolongado, ciclo de 10–14 días; registrada en Colombia"**
- Secciones: Enfermedades y Pitch ("roya presente").
- Veredicto: **CORRECTO en parte**.
  - El ciclo de 10 días a 20 °C (68 °F) es correcto según el manual PNW.
  - El rango de 19–25 °C está NO VERIFICADO: lo atribuye a una guía de DPIRD (Australia Occidental) un resultado de búsqueda, pero la página dio 403, igual que la de Victoria citada en el documento.
  - El registro en Colombia es correcto. Colfungi lista la especie sobre *V. corymbosum* sin localidad. La mejor cita es Salazar Yepes y Buriticá 2012 (*Rev. Fac. Nac. Agron. Medellín* 65(2):6697–6702): primer registro en Suramérica, en Rionegro (Antioquia), a 2.300 msnm, en noviembre de 2011.
- Corrección propuesta: citar a Salazar Yepes y Buriticá 2012 y decir "registrada en Antioquia (2011); su presencia en la Sabana está sin confirmar (pregunta al mentor)".
- Fuentes: https://pnwhandbooks.org/plantdisease/host-disease/blueberry-vaccinium-corymbosum-rust, https://colfungi.org/taxon/urn:lsid:indexfungorum.org:names:546834/general-information, `raw/ciencia_rfnam_royas2012/` (URL de origen https://revistas.unal.edu.co/index.php/refame/article/download/36502/38427)

**22. Licencias y descripción de los datasets**
- Secciones: Datasets y Advertencias ("licencias sin verificar").
- PlantVillage "CC BY-SA (sin verificar)": **CORRECTO, ya verificado**. La tarjeta de Hugging Face (mohanty/PlantVillage) declara cc-by-sa-3.0. El repositorio de GitHub no tiene LICENSE. El cláusula "compartir igual" importa si se vende el producto.
- Strawberry Hybrid Augmentation (Mendeley) "Reuso académico (sin verificar)": **INCORRECTO**.
  - La licencia es **CC BY-NC 4.0**, que no permite uso comercial.
  - Incluye 1.018 imágenes **sintéticas hechas con DALL·E 3** (solo en train) sobre una base de 2.459 imágenes.
  - Las cifras de 5.610 imágenes, 8 clases y formato COCO son correctas.
- Strawberry Disease (Afzaal 2021) "Invernadero": **IMPRECISO**. Las fotos son de invernaderos de Corea del Sur, tomadas con celular, y ~20 % vienen de internet. Las cifras de 2.500 imágenes, 7 clases, máscaras y CC BY 4.0 son correctas.
- HyperspectralBlueberries: **CORRECTO** en 420 frutos (210 sanos y 210 con defecto) y 25–28 GB (Zenodo lista 27,8 GB). La licencia es **CC BY 4.0** (ya verificada). La cita "Deng et al. 2024" es NO VERIFICADA: Zenodo lista a "Lu, Yuzhen (Supervisor)".
- DrBerry "conteo por clase sin verificar": **ya verificado**. Tiene 410 imágenes y 737 cajas (Alternaria 289, Heliothis 204, oídio 162, sana 82). Por clase dominante: 68 / 161 / 121 / 60.
- Fuentes: https://huggingface.co/api/datasets/mohanty/PlantVillage, https://data.mendeley.com/datasets/k2ptxmfjhj, https://datasetninja.com/strawberry-disease-detection, https://zenodo.org/records/11200576, `resultados/conteo_clases.csv`

**23. "Los sensores de humedad se descalibran justo cerca del 100 % de humedad" (U. Wisconsin)**
- Sección: Operación y mantenimiento.
- Veredicto: **IMPRECISO** (la fuente no dice eso). U. Wisconsin solo dice que una HR baja en mañanas con rocío puede indicar falla, y recomienda calibrar con el fabricante cada 2 años.
- Corrección propuesta: citar la hoja de datos Sensirion SHT3x, que sí lo respalda: la exposición prolongada a HR > 80 % puede desplazar la lectura (+3 %RH tras 60 h), con recuperación lenta y deriva típica < 0,25 %RH por año.
- Fuentes: https://fruit.wisc.edu/2026/03/20/weather-station-maintenance-reminder/, https://sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf

**24. Baterías de litio "300–500 ciclos, es decir cambio cada 1–1,5 años con un ciclo diario"**
- Sección: Operación y mantenimiento.
- Veredicto: **IMPRECISO**. La cuenta da 300/365 = 0,8 años y 500/365 = 1,4 años, y la cifra de ciclos no tiene fuente.
- Corrección propuesta: "0,8–1,4 años (SUPUESTO; pedir a AgiBot los ciclos de la batería de 4,6 Ah)".

**25. "Por qué no humanoide: pesan de 2 a 4 veces más que el D1, ninguno declara protección… cuestan de 4 a 10 veces más"**
- Sección: Robots.
- Veredicto: **IMPRECISO** e incoherente con la tabla del propio documento.
  - Con los datos del documento, el peso va de 1,3× (Booster K1) a 4,5× (A2). El X2 es 2,1× y el X2 Ultra 2,5×.
  - El precio frente al D1 EDU va de 2,7× (Unitree G1) y 4× (X2) a 12,5× (A3 Ultra) y 15× (H1).
  - La tabla le pone al A2 "IP5X solo articulaciones", así que "ninguno declara" contradice la tabla.
- Corrección propuesta: "pesan 1,3–4,5 veces más, cuestan 3–15 veces más; ninguno declara protección del cuerpo completo".

**26. "Algunos cuadrúpedos sí tienen IP67… cuestan de 6 a 25 veces lo que cuesta el D1 EDU"**
- Sección: Correcciones.
- Veredicto: **IMPRECISO**. Con los precios del documento frente a 5.999 USD, D1 Max es 8,0×, MaxPro 11,3×, X30 14–16,5× y ANYmal 25×.
- Corrección propuesta: "de 8 a 25 veces".

**27. Unitree Go2 EDU "13.900 USD"**
- Sección: Robots (otros fabricantes).
- Veredicto: **IMPRECISO**. La página citada muestra £8.398,80, sin decir si incluye IVA. Son unos 11.000–11.500 USD con una tasa SUPUESTA de 1,30–1,37 USD/GBP. El peso (15 kg) y la batería (2–4 h) son correctos.
- Fuente: https://store.ired.co.uk/products/unitree-go2-edu-quadruped-robot

### Prioridad 3: fuentes rotas y detalles menores

**28. Resolución ICA 11768 de 2019 (reingreso)**
- Veredicto: **CORRECTO** en el fondo, con el **enlace roto**. La Resolución 11768 del 5 de agosto de 2019 fija la metodología del "periodo de reentrada" tras aplicar plaguicidas químicos de uso agrícola. El enlace del normograma INVIMA devuelve 404.
- Corrección propuesta: usar el término oficial "periodo de reentrada" y citar la Circular Externa 5 de 2020 del ICA, que confirma el número y la fecha.
- Fuente: https://www.ica.gov.co/getattachment/Areas/Agricola/Servicios/Regulacion-y-Control-de-Plaguicidas-Quimicos/CIRCULAR-EXTERNA-N-5.pdf.aspx?lang=es-CO (copia en `raw/revision_documento_ica_circular/`)

**29. Establecimiento "50–60 mil USD/ha (datos de 2020)" (UNAD 2021)**
- Veredicto: **CORRECTO** tal como está citado, pero la fuente es débil y el enlace está roto (404).
  - Es un trabajo de diplomado que cita a "Afanador, 2020".
  - El mismo texto da un FOB colombiano de 7–9 USD/kg.
- Corrección propuesta: nuevo enlace https://repository.unad.edu.co/handle/10596/41047 y marcar la cifra como "fuente secundaria".

**30. Perú "19,2 t/ha (2021)" (Agraria.pe)**
- Veredicto: **IMPRECISO**. El artículo dice 19.206 kg/ha en 2021, pero sus propios totales (261.000 t en 16.850 ha) dan 15,5 t/ha.
- Corrección propuesta: "15–19 t/ha según la base de área".
- Fuente: https://agraria.pe/index.php/noticias/fall-creek-peru-tiene-el-rendimiento-productivo-promedio-de--30244

**31. Rúbrica: "Una maqueta sin comportamiento real saca 0 a 12 de 25" frente a "robot caminando y animación, 8–12"**
- Secciones: Rúbrica, Diagnóstico, Demo.
- Veredicto: **NO VERIFICABLE**, porque no tengo el documento oficial del reto. Los pesos (15/20/25/20/10/10) coinciden con el contexto del equipo.
- Corrección propuesta: dejar un solo rango (0–12 o 8–12) en todo el documento.

**32. Pitch 0:40–1:30: "video dividido en 4 cuadrantes (cuadrúpedo, red fija, kit en aspersora, humanoide)"**
- Veredicto: **IMPRECISO (incoherencia interna)**. La matriz tiene 6 alternativas y la E (ruedas: Amiga o Genie) no aparece en el video.
- Corrección propuesta: agregar E o decir que E solo está en la matriz.

**33. D1 EDU "pendiente 40°"**
- Veredicto: **IMPRECISO**. La ficha oficial dice "30° standard, up to 40° maximum".

**34. D1 MaxPro "LiDAR de 96 líneas"**
- Veredicto: **NO VERIFICADO**. RobotShop solo dice "onboard LiDAR module". El resto de la fila es correcto: 68 kg, IP67, −20 a 55 °C, 2,5–5,5 h con cambio en caliente, 50 kg, escaleras de 30 cm, 45° y vadeo de 20 cm. RobotShop lo vende a 94.459 USD.
- Fuente: https://www.robotshop.com/products/agibot-d1-maxpro-quadruped-robot-dog

**35. "El arándano colombiano se concentra en la región cundiboyacense, a 2.600–3.000 msnm"**
- Veredicto: concentración **CORRECTA** (EVA: 94,6 % en Boyacá y Cundinamarca); altitud **NO VERIFICADA** (no tiene fuente). Portal Frutícola solo dice "sobre los 2.000 metros". La roya se registró a 2.300 msnm.

---

## 2. Coherencia interna (recalculado)

Script: `reportes/revision-documento_scripts/checks.py`.

| Cálculo | Documento | Recalculado | Veredicto |
|---|---|---|---|
| Totales de la matriz A–F (pesos 20/20/20/15/15/10) | 73 / 75 / 68 / 42 / 69 / 83 | 73 / 75 / 68 / 42 / 69 / 83 | CORRECTO |
| Sensibilidad B y F (20/15/30/15/10/10) | 80 / 81 | 80 / 81 | CORRECTO (ver punto 15) |
| B pesimista / base / optimista | 144 / 1.830 / 6.740 | 144 / 1.830 / 6.740 | CORRECTO |
| Equilibrio en kg (costo / 6 USD/kg) | 53, 18, 15, 72, 350, 117, 370, 108, 73 | 53,3, 18,3, 15, 71,7, 350, 116,7, 366,7, 108,3, 73,3 | CORRECTO |
| % de la cosecha (de 12 t) | 0,4 / 0,6 / 2,9 % | 0,44 / 0,60 / 2,92 % | CORRECTO |
| ROI D1 Ultra / híbrido | 4,7× / 3,3× | (B − C)/C = 4,72 / 3,26 | CORRECTO si se define así (punto 17) |
| Falsa alarma frente a no detectado | 30 y 105 USD frente a 2.160; ~70:1 (~20:1) | 12.000 × 3 % × 6 = 2.160; 72:1 y 20,6:1 | CORRECTO |
| Factor de importación | 1,35 | 1,08 × 1,05 × 1,19 = 1,349 | CORRECTO como cuenta |
| Precios puestos en Colombia | 4.300 … 149.200 | FOB × 1,35, todos dentro de ±100 USD | CORRECTO |
| Peso de L·f en B | 90 % | 78,7 % (base) | IMPRECISO |
| Batería con 300–500 ciclos | 1–1,5 años | 0,8–1,4 años | IMPRECISO |
| MaxPro 20 ha / Genie G1 / MaxPro 60 ha | 2.100 / 2.200 / 700 | ~1.720 / ~1.880 / ~570 con el O&M del propio documento | NO REPRODUCIBLE (punto 16) |
| D1 Ultra + mástil = 320 USD/ha/año | 320 | 11.600/3 + 2.533 de O&M, en 20 ha = 320 (O&M dentro del rango de 2.300–3.250) | CORRECTO |
| Red fija + D1 = 430 | 430 | 320 + 110 | CORRECTO |
| Demo + evidencia | 45 | 25 + 20 | CORRECTO |
| Pesimista: "solo red fija y kit se pagan" | — | 110 y 90 < 144 < 320 | CORRECTO |

Incoherencias de texto entre secciones:
- El D1 EDU "no tiene protección certificada" (Operación) y "IP32" (Robots), cuando el fabricante dice IP54 (puntos 3 y 18).
- "Ninguno declara protección" (humanoides) frente a "IP5X solo articulaciones" (A2) en la tabla (punto 25).
- "No usar precio de exportación" frente a P base = 6 ≈ FOB de Perú, cuando el precio en finca es de 8–10 (punto 13).
- Rango de Demo "0 a 12" frente a "8 a 12" (punto 31).
- Video de 4 alternativas frente a una matriz de 6 (punto 32).
- "Límites": "Los modelos de Botrytis son de fresa; solo el de antracnosis es de arándano" está bien, pero "validado" exagera (punto 9).

---

## 3. Afirmaciones verificadas como correctas

- **EPPO, D. suzukii en Colombia:** CORRECTO. Figura como "Present, restricted distribution", con primer registro en 2026 en Antioquia, Santander y Boyacá. La fuente es el EPPO Reporting Service 2026/136, y la ONPF declaró en mayo de 2026 que está bajo control oficial. https://gd.eppo.int/taxon/DROSSU/distribution/CO
- **Mercado colombiano (Forbes 2026):** el 95 % se vende en el mercado local, a 8–10 USD/kg en finca, con costo de 3,5–5 USD/kg (Planasa). CORRECTO.
- **Arancel:** 5 % en las subpartidas 8479.50.00.00 (robots industriales n.e.p.) y 8479.89.90.00 del Decreto 1881 de 2021. CORRECTO; la clasificación del D1 no está confirmada. El IVA del 19 % es la tarifa general. https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1881_2021.htm
- **Precios en la tienda AgiBot:** D1 EDU 6.080 USD ("coincide con la tienda oficial"), D1 Pro 3.200 y D1 Ultra 9.600. CORRECTO.
- **D1 Pro sin SDK:** CORRECTO.
- **D1 EDU, especificaciones básicas:** 15,5 kg, 1–2 h, 5 kg de carga y escalón de 16 cm. CORRECTO.
- **URDF e Isaac:** CORRECTO; también hay soporte para MuJoCo.
- **D1 Max:** cuerpo de 40 kg, ruedas-patas, IP67, 3,5 h con carga, 25–30 kg, obstáculos de 80 cm y 45°. CORRECTO. RobotShop lo vende a 66.599 USD.
- **D1 MaxPro:** ver el punto 34; todo correcto salvo las "96 líneas".
- **Spot:** 33,8 kg, IP54, 90 min y 0,61 m de altura caminando. CORRECTO. El precio de 74.500 USD no aparece en la página (NO VERIFICADO).
- **X2 Ultra:** ~39 kg, ~2 h, carga de 3 kg en postura específica y ≤ 1 kg en todo el espacio de trabajo, Orin NX y RGB-D + LiDAR 3D. CORRECTO. La altura es de 1,31 m, y "táctil" se refiere solo al sensor de la cabeza.
- **A2:** 69 kg, 169 cm, 2 h y LiDAR + RGB-D. CORRECTO. El "IP5X" no aparece en la página oficial (NO VERIFICADO).
- **Genie G1:** 150 kg, 130–180 cm, 4 h o más, Jetson AGX Orin de 64 GB y obstáculos de 20 mm. CORRECTO.
- **Jetson Orin Nano Super:** 249 USD (Phoronix, 17-dic-2024). CORRECTO.
- **PlantDoc:** 2.598 imágenes, 13 especies y hasta 17 enfermedades, tomadas de internet. CC BY 4.0 en GitHub, y para arándano solo trae "Blueberry leaf" (sana). CORRECTO.
- **PlantVillage:** 54.303 imágenes y 38 clases; para arándano solo trae `Blueberry___healthy` (1.502 imágenes en la copia local). CORRECTO.
- **Citas de los modelos:** Bulger, Ellis y Madden 1987 y Miles et al. 2013 tienen bien volumen y páginas. Broome 1995 es de uva (no lo verifiqué; el documento ya lo corrigió).
- **Síntomas de NCSU:** el oídio empieza como una capa blanca tenue con manchas pálidas que se vuelven rojas, y la Alternaria hace lesiones café-grises con borde rojo en tiempo fresco y húmedo. CORRECTO. El "~20 °C" de la Alternaria no tiene número en la fuente (NO VERIFICADO).
- **Estaciones METOS/Pessl con modelo de Botrytis:** CORRECTO, y además tienen uno de antracnosis de arándano (punto 9).
- **Paper de CMU arXiv 2603.23112:** existe. Es "Active Robotic Perception for Disease Detection and Mapping in Apple Trees" (Feddock, Yandun, Aćimović y Silwal), del 24-mar-2026, sobre fuego bacteriano en manzano en reposo. Es antecedente directo de "robot que mapea enfermedad", y el posicionamiento debería mencionarlo como investigación, no como producto comercial.

## 4. Datos útiles para las preguntas pendientes del equipo

Todo esto sale de la guía SDK oficial V2.0.7 y de la ficha técnica de AgiBot.
- **Odometría:** la SDK tiene `getPosition` (posición en el marco de origen), `getWorldVelocity` y `getBodyVelocity`. Responde "¿Se puede leer la odometría…?" con un sí.
- **Cámara:** frontal gran angular de 1080p, DFOV de 122°, por RTSP vía GStreamer. Las URL están en el punto 2.
- **Conexión:** por wifi (192.168.234.1) o por cable (192.168.168.168). Wifi 5, banda de 2,4 GHz.
- **Entorno de desarrollo:** Ubuntu 22.04 en máquina física (no WSL), Python 3.10 y CMake 3.8 o superior.
- **Firmware:** se necesita el firmware de control de movimiento 0.2.6 o superior.
- **ROS:** no hay interfaz ROS.

## 5. Archivos producidos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/revision-documento.md` (este reporte).
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/revision-documento_scripts/checks.py` (recálculos) y `eva2.py` (agregación EVA).
- `raw/revision_documento_eva/` (EVA por año), `raw/revision_documento_api/` (TRM, tienda AgiBot, HF, GitHub y arXiv), `raw/revision_documento_europepmc/` (Bulger y Miles), `raw/revision_documento_ica_circular/` (circular ICA) y `raw/revision_documento_unad/` (tesis UNAD). Cada carpeta tiene su `LEEME_fuente.txt`.

## 6. Fuentes abiertas de verdad

Portal Frutícola, Forbes, Agraria.pe, Gestión, datos.gov.co (EVA uejq-wxrr y TRM 32sa-8pi3), Actualícese, Portafolio, la circular del ICA, EPPO, Colfungi, Europe PMC, Crossref, OpenAlex, PNW Handbooks, NCSU (hojas y Botrytis), METOS, TFDS, la API de Hugging Face, la API de GitHub, arXiv (PlantDoc y 2603.23112), Dataset Ninja, Mendeley Data, Zenodo, agibot.com (D1_Pro, filepage/299, los dos PDF oficiales), store.agibot.com (.json), openelab, generationrobots, RobotShop (D1 Max y MaxPro), la documentación del X2, agibot.com (A2 y G1), Boston Dynamics, iRed, FarmingUK, U. Wisconsin, Sensirion, Phoronix, el normograma de la DIAN y el repositorio de la UNAD. Las URL exactas están en cada punto.

También usé copias locales que bajaron otros agentes: el paper de DrBerry, Salazar Yepes y Buriticá 2012, y `resultados/ficha_drberry.md` y `conteo_clases.csv`.

## 7. Límites

- **Páginas que no pude abrir:**
  - Respondieron 403: APS (Bulger; usé Europe PMC), Victoria (roya), NSW DPI y DPIRD (roya), METER (sensor de hoja mojada), embeddedworks (nodo LoRa) y Roboflow Universe (PlantDoc).
  - La página de MSU sobre antracnosis cargó vacía.
  - Respondieron 404: el PDF de la Resolución ICA en el normograma INVIMA y el enlace viejo de la UNAD.
  - El PDF de DEFRA sobre *T. minima* falló en la herramienta.
- **Sin texto completo de Miles 2013:** el artículo es de pago, así que solo usé el resumen.
- **Sin el documento oficial del reto:** la rúbrica y sus descriptores quedan NO VERIFICABLES.
- **No revisé:**
  - Unitree B2, Deep Robotics X30, ANYmal D, Unitree H1, Booster T1/K1, NAO 6, farm-ng Amiga y Clearpath Husky.
  - El "D2 Max".
  - Las alturas de cámara estimadas y la tabla de costos de sensores (el documento ya los marca como aproximados).
- **Fecha del promedio de la TRM:** el promedio de 12 meses (3.532) se calculó con `vigenciadesde ≥ 2025-10-23`.
- **API key de Roboflow:** no la usé, porque mi rol no la necesitaba. Se compartió en texto plano en el chat, y conviene rotarla al terminar el hackathon.

## 8. Pendientes sugeridos (para quien edite el documento)

1. Reemplazar el área sembrada por la de EVA 2025 en la tabla, en las advertencias y en el guion del pitch (punto 1).
2. Corregir la cámara, el IP54 y la falta de ROS del D1 (puntos 2–4), y revisar la recomendación del Ultra frente al EDU (punto 18).
3. Reescribir la comparación con DrBerry y usar el split por grupos en la demo y en la validación (puntos 5–7).
4. Ajustar la TRM, el precio FOB de Perú, el rendimiento y el precio base, y volver a correr la sensibilidad de B (puntos 10–14).
5. Publicar la hoja de cálculo del costo por plataforma (punto 16) y el barrido de pesos de la matriz (punto 15).
6. Agregar METOS/Pessl (antracnosis de arándano) a "Lo que el jurado atacará" (punto 9).
