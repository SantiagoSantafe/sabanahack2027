# Reporte: ciencia-enfermedades (verificación con fuentes)

Rol: ciencia-enfermedades · Fecha: 2026-10-23 · Proyecto Sabana Hack, "Berry Good Idea"

Convenciones del reporte:
- **VERIFICADO**: lo confirma al menos una fuente primaria o de extensión que abrí y leí.
- **CORREGIDO**: la fuente dice otra cosa; pongo el valor corregido.
- **NO VERIFICADO**: no encontré fuente o no pude abrirla. No lo uso como hecho.
- "(solo buscador)": el dato lo vi en el resumen de un buscador, pero la página estaba bloqueada (403, Cloudflare o certificado). Úsalo como indicio, no como cita.
- Todo lo que no tiene fuente va marcado **SUPUESTO**.
- No hay citas textuales: todo está parafraseado. Las fuentes tienen derechos de autor o licencias propias; las copias en `raw/` son solo para uso interno, no para redistribuir.

---

## 0. Resumen ejecutivo: lo que cambia para el equipo

1. **Botrytis debería ser el modelo ambiental principal, no el secundario.** Ya existe una regla publicada para arándano y no hace falta el proxy de fresa: más de 6 h de mojadura con temperatura entre 14 y 25 °C. En Chile, esa regla dio r = 0,96 frente a la incidencia de moho gris en fruta almacenada (Rivera, Zoffoli y Latorre 2013, *Plant Disease* 97:1069). Advertencia: los autores dicen que falta validarla en campo. Además, Botrytis apareció en 8 de 9 fincas muestreadas en Cundinamarca y Boyacá (Valbuena-Gaona et al. 2025).
2. **La antracnosis como enfermedad "principal" es poco pertinente para la Sabana.** Su óptimo de infección es ~25 °C (Miles et al. 2013; MSU E-3039). Las zonas productoras colombianas tienen medias de 12 a 18 °C (Valbuena-Gaona 2025; Guasca 12,85 °C según Cortés-Rojas 2016). Ninguna fuente colombiana que encontré la reporta entre los problemas principales. Puede pesar más bajo invernadero, donde las máximas llegan a 25–35 °C (tesis de Sopó), pero eso es una **hipótesis**.
3. **La roya está confirmada en Colombia y es de las enfermedades más preocupantes.** La especie registrada es *Thekopsora minima* (= *Pucciniastrum minimum*): Rionegro, Antioquia, 2.300 m, 2011 (Salazar y Buriticá 2012). Apareció en 6 de 9 fincas del altiplano cundiboyacense y es, con la muerte regresiva, la de mayor preocupación (Valbuena-Gaona 2025). Problema de diseño: **el clasificador visual (DrBerry) no tiene clase de roya ni de Botrytis**. Hoy, los dos problemas biológicos más importantes de Colombia solo los cubriría la capa ambiental. Hay que declararlo como "casos no detectados por diseño".
4. **La muerte regresiva** (complejo *Lasiodiplodia*, *Neofusicoccum*, *Pestalotiopsis*, *Phomopsis*…) es una de las dos enfermedades más importantes en Colombia (Valbuena-Gaona 2025) y **está fuera del foco**. Hay que decirlo en la sustentación.
5. **Oídio**: está verificado que no necesita agua libre (Cornell). Que el agua libre lo inhiba está verificado solo como regla general de los oídios (WSU), no para *E. vaccinii* en particular. No encontré registro de *E. vaccinii* en Colombia: el estudio de dispersión global (Bradshaw et al. 2025) nombra a Perú, pero no a Colombia.
6. **Heliothis es un insecto** (Lepidoptera: *Chloridea virescens*, antes *Heliothis virescens*, y/o *Helicoverpa* spp.), no una enfermedad. Hay registros de daño en arándano en Perú. No encontré ningún registro en arándano colombiano. En Colombia sí se reporta daño mecánico de aves y roedores en hojas y frutos, que el clasificador podría confundir con "Heliothis" (**riesgo de falsa alarma**).
7. ***D. suzukii*: primer reporte oficial en Colombia en 2026** (EPPO RS 2026/136, con base en el reporte IPPC del 29-05-2026). Se detectó en Antioquia, Santander y Boyacá, **solo en fresa**, y está bajo control oficial. Boyacá es departamento arandanero, así que conviene mencionarla como riesgo emergente que el sistema podría incorporar más adelante.
8. **Fenología: producción continua, con picos inducidos por poda.** No hay una temporada fija de floración: en una misma finca coexisten flores, fruto verde y fruto maduro, así que **el modelo de riesgo no debe "apagarse" por época** (SUPUESTO derivado de las fuentes del punto 8). Las lluvias son bimodales: marzo–mayo y septiembre–noviembre.
9. **Representatividad de datos (rúbrica de Evidencia).** DrBerry tiene fotos de costa peruana, a pleno sol de mediodía y con celular. Colombia es trópico alto, cada vez más bajo cubierta o macrotúnel, y con problemas dominantes distintos. Del foco visual, solo **Alternaria** coincide claramente con lo que se ve en campo en Colombia.

---

## 1. Oídio (*Erysiphe vaccinii*, sin. *Microsphaera vaccinii*)

| Afirmación | Veredicto | Evidencia (parafraseada) | Fuente |
|---|---|---|---|
| Se dispersa por viento | **VERIFICADO** | Las corrientes de aire llevan los conidios a tejido nuevo; la infección ocurre en periodos de HR alta | Cornell Fast Facts (Heidenreich, Fiacchino, Koeller): https://bpb-us-e1.wpmucdn.com/blogs-dev.cornell.edu/dist/0/7265/files/2017/01/BB-mildew-fast-fact-xzsrqg.pdf |
| NO necesita agua libre | **VERIFICADO** (arándano) | Cornell dice explícitamente que no hace falta agua libre en la hoja para infectar | Cornell (misma URL) |
| El agua libre lo inhibe | **VERIFICADO solo como generalidad de oídios**; **NO VERIFICADO para *E. vaccinii*** | El agua libre puede matar esporas de oídios e inhibir su micelio; la humedad atmosférica sí favorece la germinación | WSU Extension (J. Cooper), *Powdery Mildews*: https://wpcdn.web.wsu.edu/extension/uploads/sites/53/2014/04/PowderyMildews.pdf |
| Manchas cloróticas o rojizas en el haz | **VERIFICADO** | Manchas cloróticas con borde rojizo en el haz, parecidas al virus de la mancha anular roja (red ringspot). Penn State describe moteado amarillo que pasa a manchas rojas con margen más claro | Cornell; Penn State: https://extension.psu.edu/blueberry-disease-powdery-mildew-not-symptoms-youd-expect |
| A veces sin micelio visible | **VERIFICADO** | Penn State: las placas "polvorientas" típicas muchas veces no aparecen. Cornell: el micelio blanco se ve en variedades susceptibles | Penn State; Cornell |
| Síntomas en el envés | **VERIFICADO** | Áreas acuosas en el envés, opuestas a las cloróticas del haz (esto lo separa del virus), que luego se vuelven rojizas. Puede afectarse cualquiera de las dos caras | Cornell; Penn State; Agraria.pe 2022 (Perú, publirreportaje, fiabilidad baja): https://www.agraria.pe/noticias/oidiosis-un-nuevo-reto-a-controlar-en-el-cultivo-de-arandano-27077 |
| Clima favorable | **VERIFICADO con matiz** | Cornell y WSU: más común y severo en clima cálido y seco. Penn State se contradice ("cálido y húmedo" y también "cálido y seco"). Ensayo en Ica, Perú (Biloxi): Tmáx 25,4–28,0 °C, Tmín 6,2–10,3 °C, HR máx 73–79 %, sin lluvia, con oídio presente | Iglesias-Osores y Alvarez 2026, *Mex. J. Phytopathol.* 44(2):120: https://www.scielo.org.mx/pdf/rmfi/v44n2/2007-8080-rmfi-44-02-a120-en.pdf |
| Expansión global | **VERIFICADO** | Especie emergente que se expande desde el este de EE. UU. China, Marruecos, México y EE. UU. figuran en el resumen; Perú y Portugal en la nota de prensa. Colombia no aparece | Bradshaw et al. 2025, *New Phytologist* 246:103–112, doi:10.1111/nph.20351 (resumen vía Crossref); https://www.newphytologist.org/news/blueberries-beware-powdery-mildew-spreading-across-the-globe |
| Presencia en Colombia | **NO VERIFICADO** | No encontré ningún registro. Valbuena-Gaona 2025 lo menciona solo como enfermedad de importancia global, no lo encontró en campo | — |

Implicación (SUPUESTO razonado): el riesgo de oídio sube con HR alta **sin** mojadura de hoja. La lluvia o el aspersor lo suprimirían, pero favorecen a Botrytis y a la roya. Una regla de oídio y otra de Botrytis responden a condiciones casi opuestas.

## 2. Alternaria (*Alternaria tenuissima* / *Alternaria* spp.)

| Afirmación | Veredicto | Evidencia | Fuente |
|---|---|---|---|
| Se dispersa por viento y salpicadura | **VERIFICADO** | Las esporas pasan de tejido infectado a fruto por viento o salpicadura de lluvia, desde final de floración hasta madurez. Sobrevive en bayas secas viejas y pedúnculos muertos | Ohio State PLPATH-FRU-44 (Anco y Ellis 2011): https://ohioline.osu.edu/factsheet/plpath-fru-44 |
| Óptimo ~20 °C | **VERIFICADO** | Óptimo de desarrollo de enfermedad: 68 °F (20 °C). Milholland 1973: crecimiento in vitro óptimo a 28 °C, pero enfermedad óptima a 20 °C | Ohio State; Milholland 1973, *Phytopathology* 63:1395, doi:10.1094/Phyto-63-1395 (metadatos vía Crossref; cifras del resumen **solo buscador**) |
| Clima fresco y húmedo | **VERIFICADO (débil)** | Las infecciones de hoja ocurren en primavera fresca y húmeda (MSU y UGA, **solo buscador**). La guía de BC (Canadá) ubica las manchas de marzo a mayo | BC Blueberry Field Guide: https://fieldguide.bcblueberry.com/alternaria-fruit-rot/ (abierta parcialmente) |
| Horas de mojadura | **NO VERIFICADO** | No encontré ningún umbral en horas específico de arándano | — |
| Mancha con borde rojo-café | **VERIFICADO** (literatura de EE. UU.) | Manchas necróticas pequeñas (~6 mm), redondeadas, con borde café rojizo. BC: 1–5 mm, grises (lo del "margen rojo" en BC es **solo buscador**) | Ohio State; BC |
| Descripción en Colombia | **Diferente** | En campo colombiano se describe como manchas necróticas con **halo clorótico**, que en estados avanzados pudren el fruto. Se encontró en la mayoría de fincas, con focos en Boyacá y el noreste de Cundinamarca | Valbuena-Gaona et al. 2025, *Rev. Colomb. Cienc. Hortíc.* 19(1), doi:10.19053/uptc.24223719.18515: https://revistas.uptc.edu.co/index.php/ciencias_horticolas/article/download/18515/15282/90885 |

Implicación: la variación de síntomas entre Perú, EE. UU. y Colombia (halo clorótico frente a borde rojo) es una fuente concreta de **casos no detectados** del clasificador entrenado con DrBerry.

## 3. Antracnosis / pudrición madura (*Colletotrichum fioriniae*, antes *C. acutatum*; también complejo *C. gloeosporioides*)

| Afirmación | Veredicto | Evidencia | Fuente |
|---|---|---|---|
| Infecta en floración y fruto verde | **VERIFICADO** | Puede infectar en cualquier momento entre floración y cosecha; los conidios llegan a flores y frutos jóvenes | MSU E-3039 (Miles y Schilder 2008): https://archive.lib.msu.edu/DMC/extension_publications/e3039/E3039.pdf ; PNW Handbook: https://pnwhandbooks.org/plantdisease/host-disease/blueberry-vaccinium-corymbosum-ripe-rot-anthracnose |
| Latencia hasta la maduración | **VERIFICADO** | El fruto verde infectado no muestra síntomas; aparecen al madurar | MSU E-3039; NC State: https://content.ces.ncsu.edu/anthracnose-fruit-rot-of-blueberries ; PNW |
| Salpicadura desde "frutos momificados/ramas" | **CORREGIDO** | Salpicadura de lluvia o riego por aspersión: sí. Pero el inóculo invernal está en **ramillas infectadas, espolones de fruto viejos, escamas de yemas florales y pedicelos**. Ninguna de las tres fuentes nombra los frutos momificados como fuente principal | MSU E-3039; NC State; PNW |
| 20–30 °C con >12 h de mojadura | **CORREGIDO** | Óptimo de infección **~25 °C**. Basta **≥8 h** de mojadura continua a 25 °C; con ≥24 h la infección es severa. A temperaturas más bajas hace falta más mojadura: a 11–16 °C, 10 h según un estudio y 18–24 h según otro. Las interrupciones secas inhiben la infección. Miles 2013: crecimiento óptimo a 26 °C, casi nulo a 5 y 35 °C, y la infección aumenta con la mojadura hasta 48 h | MSU E-3039; NC State; PNW; Miles, Gillett, Jarosz y Schilder 2013, *Plant Pathology* 62:1238–1247, doi:10.1111/ppa.12061 (cita y autores **VERIFICADOS** en Crossref; cifras del resumen **solo buscador**; el PDF de MSU fue bloqueado). Ojo: el autor no es "Hancock" |
| Presencia e importancia en Colombia | **NO VERIFICADO** | No encontré registro de *Colletotrichum* en arándano colombiano. No figura entre los problemas principales de Valbuena-Gaona 2025 (Cundinamarca y Boyacá, abril–junio de 2024, diagnóstico por síntomas), ni de Cortés-Rojas 2016 (Guasca) | — |

Importancia fuera de Colombia: en EE. UU. es la enfermedad de fruto más común, con pérdidas de 10–20 % antes de cosecha y de hasta 100 % en poscosecha (MSU E-3039).

Límite del juicio: como la infección es latente, un muestreo por síntomas en fruto verde puede subestimar la antracnosis. Que "no figure" en Colombia no prueba que no exista.

## 4. Botrytis / tizón de flor y moho gris (*Botrytis cinerea*)

| Afirmación | Veredicto | Evidencia | Fuente |
|---|---|---|---|
| Infecta en flor (tizón de flor) | **VERIFICADO** | Ataca la flor en floración; puede bajar del racimo al tallo y causar tizón de ramilla. Rivera 2013: plena floración y fruto **maduro** son las etapas más susceptibles | CT Agric. Exp. Station (Y. Li, ene-2023): https://portal.ct.gov/-/media/CAES/PDIO/Fact-Sheets/Botrytis-Blight-of-Blueberry.pdf ; Rivera et al. 2013 (resumen vía Crossref), doi:10.1094/PDIS-12-12-1112-RE |
| Latencia en fruto | **VERIFICADO** | Los frutos infectados pueden no mostrar síntomas hasta poscosecha | CT CAES |
| Viento y salpicadura | **VERIFICADO** | Corrientes de aire o salpicadura de agua | CT CAES; Ohio State (sobre todo viento) |
| Sobrevive en restos | **VERIFICADO** | Micelio latente en ramillas muertas y restos en el suelo, y esclerocios persistentes en suelo | CT CAES; Ohio State |
| 15–25 °C, HR > 90 %, ≥ 8 h de mojadura | **CORREGIDO** | Regla **específica de arándano**: >**6 h** de mojadura entre **14 y 25 °C** (Rivera 2013, Chile; r = 0,96 con moho gris en fruta almacenada; sin validar en campo). CT CAES: ≥6 h de mojadura continua **o** HR > 90 %, óptimo 65–75 °F (18–24 °C). Escalado en arándano silvestre (Nueva Escocia): a 16 °C, 6 h dan infección baja; para infección alta hacen falta 24 h a 12 °C, 13 h a 16 °C y 10 h a 20 °C. Las "8 h a 20 °C" vienen de U. Maine, arándano silvestre (**solo buscador**) | Rivera 2013; CT CAES; NSAC/Dalhousie: https://cdn.dal.ca/content/dam/dalhousie/images/sites/wild-blueberry/pdfs/Wild%20Blueberry%20Blight%20Management.pdf |
| Proxy de fresa (Bulger 1987) | **VERIFICADO como cita** | Bulger, Ellis y Madden 1987, *Phytopathology* 77:1225–1230, doi:10.1094/Phyto-77-1225 (metadatos en Crossref y Semantic Scholar). Óptimo ~20 °C en flor de fresa (Strawberry Center blog y resumen APS **solo buscador**). Broome 1995 (*Phytopathology* 85:97) es efectivamente de **uva** | https://strawberrycenterblog.com/2022/04/13/classic-botrytis-data-from-1987/ |
| Heladas predisponen | **VERIFICADO** | Las flores y yemas dañadas por frío son puerta de entrada | UGA Blueberry blog: https://site.caes.uga.edu/blueberry/?p=457 ; CT CAES |
| Presencia en Colombia | **VERIFICADO** | Tizón de botrytis en 8 de 9 fincas (todas menos Mosquera). En Colombia se ve como botones florales atrofiados que viran a violeta u oscuro, con moho gris. También aparece entre los problemas principales en Guasca | Valbuena-Gaona 2025; Cortés-Rojas et al. 2016, *Agron. Colomb.* 34(1), doi:10.15446/agron.colomb.v34n1.54897: https://revistas.unal.edu.co/index.php/agrocol/article/download/54897/60637?inline=1 |

## 5. Roya del arándano en Colombia

| Afirmación | Veredicto | Evidencia | Fuente |
|---|---|---|---|
| Especie *Thekopsora minima* | **VERIFICADO** | Registro en *V. corymbosum* en Antioquia, Rionegro, vereda Higuerón, 2.300 msnm, 08-11-2011 (MMUNM-1973). Solo se halló el estado uredinial (II). Primera colecta en Suramérica sobre arándano. Hoy EPPO la llama *Pucciniastrum minimum*: Colombia figura como "presente, sin detalles" (datos actualizados el 2024-12-09). El catálogo de hongos de Colombia la lista sobre *V. corymbosum* | Salazar Yepes y Buriticá Céspedes 2012, *Rev. Fac. Nac. Agron. Medellín* 65(2):6697–6702: https://revistas.unal.edu.co/index.php/refame/article/view/36502 (PDF leído). EPPO: https://gd.eppo.int/taxon/THEKMI/distribution . EPPO Alert 2016/058: https://gd.eppo.int/reporting/article-5460 . ColFungi: https://colfungi.org/taxon/urn:lsid:indexfungorum.org:names:546834/general-information |
| *Naohidemyces vaccinii* en Colombia | **NO VERIFICADO** | No encontré ningún registro. Valbuena-Gaona 2025 identifica la roya del altiplano solo como "*Pucciniastrum* sp.", por síntomas, así que **la especie en la Sabana no está confirmada** | — |
| ~19–25 °C | **VERIFICADO (aprox.)** | Germinación de urediniosporas: óptimo 21,5 °C; cae mucho a 30 °C y por debajo de 15 °C. Producción de uredinios: óptimo 19,5 °C. Ensayo hecho en **Rhododendron**, no en arándano. In vitro, 19–23 °C es favorable | Pfister, Halik y Bergdahl 2004, *Plant Dis.* 88:359–362, doi:10.1094/PDIS.2004.88.4.359 (resumen vía Crossref); Griffin y Anderson 2026, *J. Fungi* 12:133 (CC BY): https://mdpi-res.com/d_attachment/jof/jof-12-00133/article_deploy/jof-12-00133.pdf |
| Mojadura prolongada | **VERIFICADO cualitativo**; **horas NO VERIFICADO** | La mojadura larga y la HR alta en el dosel favorecen la infección (UF/IFAS). En hoja desprendida, 100 % de HR **no bastó**: hicieron falta gotas de agua sobre la hoja. Las 4–8 h citadas son de otras royas (*Uromyces*), no de *T. minima* | UF/IFAS PP385: https://ask.ifas.ufl.edu/publication/PP385 ; Griffin y Anderson 2026 |
| Ciclo de 10–14 d | **VERIFICADO** | Incubación de 10,7 d a 20 °C y 10,0 d a 25 °C (óptimo predicho 23 °C); unos 4 d más a 15 °C (≈14–15 d) y unos 3 d más a 30 °C. Uredinios a los 9–10 d en hoja de arándano desprendida. PNW: periodo latente de ~10 d a 68 °F | Pfister 2004; Griffin y Anderson 2026; PNW: https://pnwhandbooks.org/plantdisease/host-disease/blueberry-vaccinium-corymbosum-rust |
| Pústulas en el envés | **VERIFICADO** | Pústulas (uredinios) amarillo-naranja en el envés. En el haz, manchas amarillas que se necrosan, a veces con borde púrpura. Defoliación prematura. Confirmado también en Colombia | Schilder y Miles 2011, *Plant Dis.* 95:768 (resumen vía Crossref); PNW; Valbuena-Gaona 2025 |
| Hospedero alterno (*Tsuga*) | Contexto | En arándano que conserva hojas no hace falta el hospedero alterno (PNW); en Colombia solo se halló el estado II (Salazar 2012). Que *Tsuga* esté ausente en Colombia es **SUPUESTO**: no lo verifiqué | PNW; Salazar 2012 |
| Importancia en sistema perenne (evergreen) | **VERIFICADO (análogo)** | En Florida, con arándano evergreen, es especialmente costosa y los productores la ponen entre sus tres principales preocupaciones sanitarias. Colombia también es un sistema sin dormancia | UF/IFAS PP385 |

Extrapolación para la Sabana (SUPUESTO): con medias de 12–18 °C, la incubación estaría más cerca de 14 d que de 10 d. Una alerta de roya debería contar ~2 semanas desde el evento de riesgo hasta que aparece la pústula, que es lo que el robot podría ver si existiera una clase visual de roya.

## 6. Heliothis / Helicoverpa en arándano

| Afirmación | Veredicto | Evidencia | Fuente |
|---|---|---|---|
| Daño en arándano | **VERIFICADO (Perú)** | *Chloridea virescens* (antes *Heliothis virescens*): las larvas pequeñas comen hojas y al crecer migran a los frutos y los perforan; la hembra pone en los brotes terminales (Andina 2020, citando a Cultivida). En Perú, *Helicoverpa* spp. y *Chloridea* spp. dañan hojas, flores y frutos | Andina: https://andina.pe/agencia/noticia-peru-alcanza-las-12000-hectareas-cultivos-arandanos-808255.aspx ; Portal Frutícola (nov-2025): https://www.portalfruticola.com/?p=607319 |
| Es una plaga, no una enfermedad | **VERIFICADO** | DrBerry la trata como una "enfermedad" más (oidium, heliothis, alternaria), pero es un lepidóptero | Morales, Cavero y Ugarte 2023, KDIR (paper CC BY-NC-ND 4.0): https://www.scitepress.org/Papers/2023/122071/122071.pdf |
| Presencia en Colombia | *H. zea* presente (dato antiguo); **en arándano: NO VERIFICADO** | EPPO: *H. zea* presente en Colombia, sin detalles, con base en información de 1992. No encontré registros en arándano colombiano, y las fuentes colombianas sobre arándano no la mencionan (Valbuena 2025; Cortés-Rojas 2016, que sí nombra ácaros) | EPPO: https://gd.eppo.int/taxon/HELIZE/distribution/CO |
| Cómo distinguirla de enfermedades | **SUPUESTO** (criterio general, sin fuente específica de arándano) | Daño por masticación: falta tejido (orificios, bordes rasgados), puede haber excremento o larva, no hay signos de hongo. Las enfermedades del foco dejan necrosis con margen o halo (Alternaria), placas o manchas rojizas sin pérdida de tejido (oídio) o pústulas en el envés (roya) | — |
| Confusión probable en Colombia | **VERIFICADO (el confusor existe)** | Valbuena 2025 reporta daño mecánico de aves y roedores con mordidas en fruto y lesiones en hoja, presente en varias fincas → posible **falsa alarma** "Heliothis" | Valbuena-Gaona 2025 |

Nota de procedencia de DrBerry: el resumen dice "Huaral", pero el texto ubica el Fundo San Roberto en el distrito de Sayán, provincia de **Huaura** (Lima). El dataset tiene 439 imágenes con una sola clase y 105 con dos o más, todas tomadas a mediodía soleado con dos celulares y una cámara compacta. Hay que mencionarlo al hablar de representatividad.

## 7. Periodos latentes (infección → síntoma visible)

| Problema | Periodo | Veredicto | Fuente |
|---|---|---|---|
| Oídio | Infección en ~23 h; nuevas esporas formadas a los ~5 d | **VERIFICADO** (ficha de extensión; no cita el estudio de origen) | Cornell Fast Facts |
| Alternaria | — | **NO VERIFICADO** | — |
| Antracnosis, fruto maduro | ~7 d | **VERIFICADO** | MSU E-3039 |
| Antracnosis, fruto verde | Latente hasta la maduración (semanas; sin cifra) | **VERIFICADO cualitativo**; días **NO VERIFICADO** | MSU E-3039; NC State; PNW |
| Antracnosis, poscosecha | Pudrición en 2–4 d sin refrigerar | **NO VERIFICADO** (solo buscador, fuente poco clara) | — |
| Botrytis, flor | — | **NO VERIFICADO** | — |
| Botrytis, fruto | Latente hasta poscosecha | **VERIFICADO cualitativo**; días **NO VERIFICADO** | CT CAES; Rivera 2013 (fruta exportada pasa >15 d a 0 °C) |
| Roya | 10,0–10,7 d a 20–25 °C; ≈14–15 d a 15 °C; 9–10 d en hoja desprendida de arándano | **VERIFICADO** (ojo: Pfister trabajó en Rhododendron) | Pfister 2004; Griffin y Anderson 2026; PNW |
| Heliothis | No aplica (insecto) | — | — |

Fenología de Biloxi (días de floración a cosecha): **NO VERIFICADO**. Solo se sabe que florece temprano, madura 14–21 d antes que los rabbiteye más tempranos y puede necesitar protección contra heladas (Spiers et al. 2002, *Acta Hortic.* 574:153: https://agris.fao.org/search/en/records/65df8d5b0f3e94b9e5d9b3e9).

---

## 8. Fenología y sistema de cultivo del arándano en Colombia (Sabana y altiplano)

| Tema | Hallazgo | Veredicto | Fuente |
|---|---|---|---|
| Altitud de cultivo | 2.200–2.900 m (Asocolblue, 2026); 2.600–3.000 m (industria, 2025); región de estudio 2.000–3.000 m | **VERIFICADO** (gremio e industria; académico) | Portal Frutícola, 23-02-2026 (entrevista al presidente de Asocolblue): https://www.portalfruticola.com/noticias/2026/02/23/arandanos-colombianos-tecnificacion-crecimiento-exportador/ ; Blueberries Consulting, 22-09-2025: https://blueberriesconsulting.com/en/la-creciente-industria-de-los-arandanos-en-colombia-importaciones-record-y-expansion-de-cultivos-en-altura/ ; Valbuena-Gaona 2025 |
| Clima | Altiplano: 12–18 °C, HR > 70 %, lluvias bimodales (mar–may y sep–nov), secas en dic–feb y jun–ago. Sopó: 2.650 m, 6–19 °C, ~848 mm/año. Guasca: 2.700 m, media 12,85 °C, 640,8 mm/año bimodal | **VERIFICADO** | Valbuena-Gaona 2025; tesis de Sopó (Ramírez 2023, U. Cundinamarca): https://repositorio.ucundinamarca.edu.co/items/3810b0db-8887-4cdb-a4a1-6fdb554a0868/full ; Cortés-Rojas 2016 |
| ¿Producción continua o por flujos? | **Continua, con picos.** En Guasca hubo cosecha semanal continua durante 28 semanas, con picos (Sharpblue más marcados, Biloxi más estable). Asocolblue: producción de enero a diciembre. Industria: la poda se usa para inducir producción, porque el fotoperiodo casi no varía | **VERIFICADO** | Cortés-Rojas 2016; Portal Frutícola 2026; Blueberries Consulting 2025 |
| Épocas de pico | Nov–dic (el mayor), may–jun y sep. En 2018, un productor concentraba esfuerzos de fin de agosto a mediados de diciembre por la ventana de exportación | **VERIFICADO solo con fuente de industria** (fuente anónima; no académica) | Blueberries Consulting 2025; Portal Frutícola 30-07-2018: https://www.portalfruticola.com/?p=212155 |
| Floración | Sin temporada fija; en la misma finca los brotes basales llegan a floración mientras los laterales siguen vegetativos (Sopó, 12 semanas) | **VERIFICADO (estudio local)**; la extrapolación a "siempre hay flor y fruto en la finca" es **SUPUESTO** | Tesis de Sopó |
| Variedades | Domina Biloxi; luego Emerald, Legacy y Victoria (las siembras recientes son sobre todo Emerald y Legacy). En 2016 solo Biloxi y Legacy se usaban masivamente y Duke fracasó. Hay ensayos con Sharpblue (Guasca) | **VERIFICADO** (industria + académico) | Blueberries Consulting 2025; Portal Frutícola 21-10-2016: https://www.portalfruticola.com/?p=65821 ; Cortés-Rojas 2016 |
| Sistemas | Predomina campo abierto; entre los protegidos se prefiere macrotúnel a invernadero (industria). Fincas del estudio académico: casa de malla plástica, macrotúnel con malla fotoselectiva, invernadero con ventilación cenital, plástico por hilera, malla antigranizo. Sopó: 8 ha, todo bajo invernadero, en bolsas o materas con sustrato (25 % arena de río, 25 % tierra negra, 50 % cascarilla). Guasca: campo abierto, camas elevadas en suelo con acolchado plástico negro. El presidente de Asocolblue cuenta que cubrió su cultivo porque ~50 % de la fruta sin cubrir no cumplía estándar de exportación | **VERIFICADO** | Blueberries Consulting 2025; Valbuena-Gaona 2025; tesis de Sopó; Cortés-Rojas 2016; Portal Frutícola 2026 |
| Distancias de siembra | Guasca: 0,8 m entre plantas × 2,2 m entre centros de cama (5.600 pl/ha) y 1,0 × 2,2 m (4.275 pl/ha). Sopó (invernadero): 0,7 m entre plantas × 1,2 m "entre camas" (ambiguo: puede ser pasillo o centro a centro) | **VERIFICADO** | Cortés-Rojas 2016; tesis de Sopó |
| Altura del arbusto en Colombia | No encontré ningún dato colombiano. Biloxi es de porte erecto y vigoroso (USDA). La cifra de "~1,5 m (5 ft) adulto" sale de un catálogo de vivero de EE. UU. (solo buscador) | **NO VERIFICADO** | Spiers et al. 2002 (porte) |
| Heladas | En el invernadero de Sopó hubo mínimas de 0–10 °C con heladas (feb–abr 2021) y máximas de 25–35 °C | **VERIFICADO** | Tesis de Sopó |
| Área y regiones | ~1.000 ha; Cundinamarca y Boyacá suman ~90 % de la producción; luego Antioquia, cerca de Ecuador, etc. | **VERIFICADO** (gremio) | Portal Frutícola 2026 |
| Libro de referencia colombiano | Fischer et al. (eds.) 2021, *Avances en el cultivo de las berries en el trópico*, SCCH, doi:10.17584/IBerries | Cita **VERIFICADA** (Crossref); contenido **NO VERIFICADO** (la página de destino da 404) | — |

Implicaciones para el robot (SUPUESTO, verificar con el equipo de hardware):
- Con 1,2 m entre camas bajo invernadero (Sopó), el pasillo útil puede ser estrecho para un cuadrúpedo. No verifiqué las dimensiones del AgiBot D1.
- Como coexisten estados fenológicos, el riesgo de Botrytis (flor y fruto maduro) existe todo el año.
- El aspersor suma horas de mojadura. CT CAES y MSU recomiendan evitar el riego por aspersión o regar temprano. El sistema podría recomendar **posponer el aspersor** cuando el riesgo de Botrytis o roya es alto: es una acción concreta y defendible.

## 9. Importancia económica relativa en Colombia y los Andes

| Problema | Evidencia en Colombia | Evidencia en los Andes y otros sitios | Prioridad sugerida |
|---|---|---|---|
| **Roya** (*T. minima* / *Pucciniastrum* sp.) | Está en 6 de 9 fincas (falta en Mosquera, Paipa y Sutatausa); máximos en Tuta y Ubaté. Con la muerte regresiva, la de mayor preocupación (Valbuena 2025). Entre las principales en Guasca (Cortés-Rojas 2016) | Perú: primer reporte en 2020 (Huarhua et al., *Plant Dis.* 104:3077, doi:10.1094/PDIS-03-20-0585-PDN). Brasil 2019 (Pazdiora et al., *Plant Dis.* 103:1026) | **Alta** |
| **Muerte regresiva** (complejo; fuera del foco) | De las más importantes por severidad (Valbuena 2025) | — | Alta, **fuera del foco** (declararlo) |
| **Botrytis** | En 8 de 9 fincas (Valbuena 2025); "moho gris" principal en Guasca (Cortés-Rojas 2016) | Plaga mayor en Chile, con exportación de >15 d a 0 °C (Rivera 2013). Pérdidas de >20 % (Abbey et al. 2024, citado por Valbuena; no lo abrí) | **Alta** |
| **Alternaria** | Está en la mayoría de fincas, con focos en Boyacá y el noreste de Cundinamarca (Valbuena 2025) | Clase de DrBerry (Perú) | Media |
| Fumagina | Villapinzón y Duitama (Valbuena 2025) | — | Media-baja (fuera del foco) |
| Ácaros | Principales en Guasca (Cortés-Rojas 2016) | — | Fuera del foco |
| **Oídio** | Sin registro colombiano | Severo en Perú (Piura, Olmos, Ica; Agraria.pe 2022; Iglesias-Osores 2026). Emergente global (Bradshaw 2025) | **Baja para Colombia** (NO VERIFICADO) |
| **Antracnosis** | Sin registro colombiano | Enfermedad de fruto n.º 1 en EE. UU. (MSU) | **Baja-media para la Sabana** (NO VERIFICADO) |
| **Heliothis** | Sin registro en arándano colombiano | Plaga en Perú (Andina 2020) | Baja para Colombia (NO VERIFICADO) |
| Abióticos | Daño mecánico por aves, roedores y manipulación; deshidratación y antocianescencia del fruto, en todas o casi todas las fincas (Valbuena 2025) | — | Confusores del clasificador |

Límites de Valbuena 2025, según los mismos autores: muestreo en abril–junio de 2024 (lluvias), diagnóstico por síntomas con confirmación de laboratorio solo en casos dudosos, posible sesgo por el permiso de los dueños, y todas las fincas con Biloxi. No reporta incidencias regionales en cifras que yo pudiera extraer del texto: las figuras son gráficas.

## 10. Situación de *Drosophila suzukii* y de la roya en Colombia

- ***D. suzukii***: **VERIFICADO.** EPPO la califica como "presente, distribución restringida", con primer registro en 2026. La ONPF la declaró presente, no ampliamente distribuida y bajo control oficial (2026-05). Se detectó en varias zonas de **Antioquia, Santander y Boyacá**, **solo en fresa**, y hay muestreos oficiales en curso. Cundinamarca no aparece. La referencia IPPC que enlaza EPPO apunta por error a una página de Venezuela sobre Foc R4T, y no encontré el comunicado del ICA (**NO VERIFICADO** en fuente ICA). Fuentes: https://gd.eppo.int/taxon/DROSSU/distribution/CO ; https://gd.eppo.int/reporting/article-8432
- **Roya**: **VERIFICADO** que está presente y establecida en fincas comerciales del altiplano (Salazar 2012; EPPO; Valbuena 2025). **NO VERIFICADO** si el ICA la regula o la declara de control oficial.

---

## 11. Parámetros sugeridos para `riesgo/` (con estado)

| Enfermedad | Regla | Estado |
|---|---|---|
| **Botrytis (proponer como principal)** | Hora "mojada" = mojadura de hoja o HR ≥ 90 % (CT CAES). Evento de riesgo: >6 h mojadas seguidas con T media de 14–25 °C (Rivera 2013). Escala de severidad (silvestre, Nueva Escocia): 20 °C/10 h, 16 °C/13 h y 12 °C/24 h → riesgo alto | Regla de arándano **VERIFICADA** (sin validar en campo). Usar HR ≥ 90 % como sustituto de la mojadura con Open-Meteo es **SUPUESTO** |
| Antracnosis | Riesgo si mojadura ≥ 8 h con T ~25 °C; ≥ 24 h → severo; a 11–16 °C hacen falta ≥ 10 h (otro estudio dice 18–24 h). Las interrupciones secas cortan el evento | **VERIFICADO** (MSU, NCSU, PNW). Coeficientes gaussianos de Miles 2013: **NO VERIFICADO** (no los obtuve) |
| Roya | Riesgo si T en 15–25 °C (óptimo ~21–23 °C) y hay mojadura de hoja. Síntoma esperado ~10 d después a 20–25 °C y ~14 d a 15 °C. Por encima de 30 °C, riesgo bajo | Temperatura e incubación **VERIFICADAS** (Pfister 2004; Griffin 2026). Horas mínimas de mojadura: **NO VERIFICADO** (proxy de 4–8 h de otras royas = **SUPUESTO**) |
| Oídio (si se modela) | Riesgo con HR alta **sin** agua libre; la lluvia o el aspersor lo reducen | Cualitativo **VERIFICADO** (Cornell; WSU general). Umbrales numéricos: **NO VERIFICADO** |
| Alternaria | Riesgo con ~20 °C, tiempo fresco y húmedo | Temperatura **VERIFICADA**; horas de mojadura **NO VERIFICADO** |

---

## 12. Archivos producidos

- `reportes/ciencia-enfermedades.md` (este archivo)
- Copias de las fuentes, cada una en su carpeta, con su `URL.txt`. Contenido no confiable, solo para uso interno:
  - `raw/ciencia_cornell_oidio/` (Cornell Fast Facts, oídio)
  - `raw/ciencia_wsu_powdery/` (WSU, oídios en general)
  - `raw/ciencia_mjp_oidio_peru/` (Iglesias-Osores y Alvarez 2026)
  - `raw/ciencia_msu_e3039/` (MSU E-3039, antracnosis)
  - `raw/ciencia_caes_botrytis/` (CT CAES, Botrytis)
  - `raw/ciencia_dal_wildblueberry_blight/` (Nueva Escocia, tizón)
  - `raw/ciencia_mdpi_jof12_133/` (Griffin y Anderson 2026, roya; CC BY)
  - `raw/ciencia_rfnam_royas2012/` (Salazar y Buriticá 2012, roya en Colombia)
  - `raw/ciencia_uptc_valbuena2025/` (Valbuena-Gaona et al. 2025, estado fitosanitario en Colombia; licencia **NO VERIFICADA**)
  - `raw/ciencia_ucundinamarca_tesis_sopo/` (tesis de Sopó, 2023)
  - `raw/ciencia_drberry_paper/` (paper de DrBerry, CC BY-NC-ND 4.0)
- Los PDF se procesaron con `pdftotext` desde fuera de `raw/`; no se ejecutó ningún código descargado. No se usó la API key de Roboflow (este rol no la necesita).

## 13. Límites

- Varias páginas clave estaban bloqueadas (Cloudflare o Incapsula en apsnet.org y canr.msu.edu, certificado en UMaine, 403 en NSW DPI y Agriculture Victoria). Los datos de Miles 2013, Bulger 1987 y Milholland 1973 vienen del resumen en el buscador o de Crossref; sus cifras no salen del texto completo.
- No pude acceder al libro de la SCCH (Fischer et al. 2021) ni a la ficha técnica del ICA (404). Tampoco encontré documentos de AGROSAVIA específicos de arándano.
- La evidencia colombiana sobre enfermedades descansa en dos estudios: Valbuena 2025 (9 fincas, una sola temporada, diagnóstico por síntomas) y Cortés-Rojas 2016 (una finca).
- Pfister 2004 (temperaturas de la roya) se hizo en Rhododendron, no en arándano.
- Las cifras de picos de cosecha vienen de fuentes de industria con informante anónimo.

## 14. Pendientes sugeridos

1. Decidir con el equipo si se cambia la prioridad ambiental a Botrytis (principal), roya (secundaria) y antracnosis (terciaria, sobre todo bajo cubierta).
2. Pedir al agente de clima que derive "horas mojadas" a partir de HR y precipitación de Open-Meteo, documentado como SUPUESTO.
3. En la sustentación, declarar como "casos no detectados por diseño": roya y Botrytis en la parte visual, muerte regresiva, ácaros y *D. suzukii*.
4. Buscar imágenes de roya del arándano con licencia abierta. Sería la clase visual más pertinente para Colombia.
5. Si hay tiempo: confirmar en el ICA el estatus regulatorio de la roya y de *D. suzukii*, y conseguir las alturas del arbusto en fincas de la Sabana.
