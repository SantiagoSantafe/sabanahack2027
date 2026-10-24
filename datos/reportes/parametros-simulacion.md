# Reporte del agente parametros-simulacion

Fecha: 2026-10-23. Armé la tabla de parámetros con fuente para la simulación del brote (grilla bloque × camas × plantas, contagio diario a vecinas modulado por riesgo climático, periodo latente, detección por robot, humano y red fija). No usé la API key de Roboflow, porque este rol no la necesita.

## Qué hice

1. **Busqué literatura** con la API REST de Europe PMC (resúmenes y textos completos de acceso abierto), el buscador web y descargas directas de PDFs de extensión. Cada fuente que cito la abrí yo. Las 28 referencias con DOI las verifiqué una por una con `query=DOI:"…"` en Europe PMC (`raw/paramsim_europepmc/doi/`).
2. **Extraje valores** (valor, rango, unidad, órgano, hospedante) leyendo el texto descargado con un extractor propio. No usé resúmenes automáticos.
3. **Escribí `simulacion/parametros.yaml`.** Cada parámetro lleva `valor`, `rango`, `etiqueta` (FUENTE / DERIVADO / SUPUESTO / NO_VERIFICADO), `calidad` (A = arándano, B = análogo, C = extensión o industria, D = supuesto), ids de `fuentes` y un comentario `#` con la cita y la cuenta.
4. **Calibré `beta_max` por enfermedad** con una simulación de referencia en la grilla por defecto, para que la tasa temprana `r` iguale la `r` objetivo de la literatura. Además medí la velocidad del frente para validarla contra los dos datos de campo que tengo (oídio en fresa y roya en Hawái).
5. **Calculé los órdenes de magnitud esperados al primer hallazgo** (regla de Parnell et al. 2015), humano frente a robot, como chequeo de validación para el simulador.

## Archivos producidos

| Archivo | Contenido |
|---|---|
| `simulacion/parametros.yaml` | Tabla de parámetros con etiquetas, calidad y 50 fuentes |
| `simulacion/calibracion_parametros/calibrar_beta.py` | Calibración de `beta_max` (lee el YAML) |
| `simulacion/calibracion_parametros/calibracion_complementaria.py` | Inóculo de fondo en antracnosis y sensibilidad de lambda en oídio |
| `simulacion/calibracion_parametros/beta_calibrado.json`, `curvas_r_beta.csv`, `calibracion_complementaria.json`, `*.log` | Resultados (semillas fijas, reproducibles) |
| `raw/paramsim_*/` (25 carpetas) | Copias locales de las fuentes (`source.pdf/html`, `text.txt`, `URL.txt`). Uso interno, no redistribuir |

Para reproducir, desde `datos/`: `.venv/bin/python -I simulacion/calibracion_parametros/calibrar_beta.py` y luego `.venv/bin/python -I simulacion/calibracion_parametros/calibracion_complementaria.py`. Las dos tardan unos 2 min en total.

## Resultados: tabla resumen

### Geometría (default: 1 bloque = 1 ha = 40 camas × 125 plantas = 5.000 plantas)

| Parámetro | Valor | Rango | Fuente (calidad) |
|---|---|---|---|
| Distancia entre plantas | 0.8 m | 0.6–1.22 | Perú 2.50 × 0.80 m (Best Berries, gob.pe); INIA Chile 0.8–1 m; UGA 4 ft (C) |
| Distancia entre hileras | 2.5 m | 2.5–3.05 | Best Berries 2.50 m; UGA 10 ft (C) |
| Densidad | 5.000 pl/ha | 4.760–5.700 | Colombia 5.000–5.500 (Asocolblue vía Agronegocios); Perú 4.760, 5.000, 5.236, 5.700 (C) |
| Ancho de camellón | 1.0 m | 0.8–1.2 | INIA Chile: 1 m de ancho y 50 cm de alto (C) |
| Pasillo libre | 1.5 m | 1.0–2.05 | DERIVADO (2.5 − 1.0). La copa adulta puede reducirlo (SUPUESTO) |
| Clima del Altiplano | 12–18 °C, HR > 70 %, 2.000–3.000 m | | Valbuena-Gaona et al. 2025, 9 fincas en Cundinamarca y Boyacá (A) |

### Enfermedades

| | Antracnosis | Botrytis | Roya | Oídio | Alternaria | Heliothis |
|---|---|---|---|---|---|---|
| ¿La ve el robot? | No (fruto, no es clase) | No | No (no es clase; pústulas en el envés) | Sí | Sí (lesiones chicas) | Sí |
| Dispersión | Salpicadura de lluvia o **aspersor** | Viento y salpicadura | Viento, cola gruesa | Viento | Aérea y salpicadura (S) | Oviposición de polillas |
| Kernel | Vecindad: d1 = 1, d2 = 0.1 (S), cama vecina = 0.01 (S) | exp, λ = 3 m (D: frijol) | potencia, b = 2.6 (2.23–3.04, roya del trigo) | exp, λ = 3 m (S; 1–8) | exp, λ = 2 m (S) | sin kernel |
| Vecina inmediata, misma cama : cama vecina de enfrente (D) | 100 : 1 | 3.5 : 1 | 9.9 : 1 | 3.5 : 1 | 5.8 : 1 | n/a |
| Presión de infección que queda en la misma cama (D) | 97 % | 49 % | 62 % | 49 % | 64 % | n/a |
| Latente (d) | 7 (5–10) fruto maduro (A); fruto verde hasta maduración | 4 (3–7) en flor (A) | 12 (10–21); 10.0–10.7 a 20–25 °C (B), más en frío | 7 (4–16) (B) | 5 (S); incubación 4 (2–11) (B) | huevo 3.5 d + 1–3 d hasta daño visible |
| Infeccioso (d) | 10 (S) | 7 (S) | 20 (D: µ⁻¹ de roya del trigo) | 14 (S) | 14 (S) | larva 17–18 d a 25 °C (B) |
| r objetivo (/d) | 0.07 (0.02–0.11) (B: cítricos) | 0.08 (S) | 0.12 (0.05–0.25) (B + S) | 0.15 (S) | 0.05 (S) | — |
| beta_max calibrado | 0.3 + fondo 1.1e-4 | 0.020 | 0.264 | 0.0485 | 0.0184 | tasa de oviposición 5e-4 (S) |

(S) = SUPUESTO, (D) = DERIVADO. Las fuentes por celda están en el YAML.

### Detección y tratamiento

| Parámetro | Valor | Fuente (calidad) |
|---|---|---|
| Frecuencia del monitoreo humano | 7 d | Programa IPM semanal de Rutgers, 89 campos de arándano en una semana (C) |
| Plantas por lote por visita | 66 (51–68) | Valbuena-Gaona 2025: tamaño de muestra óptimo con 90 % de confianza y 10 % de error en el Altiplano (A) |
| Tiempo | 49 min/ha/semana → ~45 s por planta | Green Methods, página comercial (C) + DERIVADO |
| Sensibilidad humana, síntoma claro | 0.65 | Mastin et al. 2019: 588/900, inspectores profesionales, *P. ramorum* (B) |
| Sensibilidad humana, síntoma inicial | 0.35 (0.2–0.5) | SUPUESTO; Combes et al. 2025: la sensibilidad crece con el número de síntomas (B) |
| Especificidad humana | 0.97 | SUPUESTO; Combes 2025: Sp > Se en 22 de 23 evaluadores (B) |
| Robot: frecuencia, cobertura, visibilidad | 2 d, 100 %, 0.5 | SUPUESTO |
| Sensibilidad del clasificador | 0.80 (0.445–0.926) | Línea base DrBerry vía `reportes/adquisicion-drberry.md`. **Reemplazar por la del pipeline** |
| Error de la red fija | ±0.2 °C, ±2 %HR | Datasheet Sensirion SHT31 (A para el sensor) |
| Eficacia protectante | 0.6 (0–0.95) | Fresa NC 2004: 58 % el mejor programa, 0 % algunos (B); Botrytis FL ~10 puntos (B); roya en arándano con orgánicos −20–25 % AUDPC (A) |
| Duración de la protección | 7 d (7–10) | Neugebauer et al. 2024 (A/C) |
| Penalización por tratar después de los síntomas | −40 % de eficacia | MacKenzie y Peres 2012, fresa (B) |
| Ahorro de aplicaciones con pronóstico | 47–50 % | MacKenzie y Peres 2012; Cordova et al. 2017 (B) |

## Hallazgos para el equipo (y para el pitch)

1. **Misma cama frente a cama vecina.** En antracnosis, el simulador de lluvia dejó casi todas las colonias en un radio de 27 cm (Ntahimpera et al. 1997). Cruzar un pasillo de ~1.5 m es raro, así que la relación de pesos queda en ~100:1 y el 97 % de la presión de infección se queda en la misma cama. En las enfermedades de viento la vecina de enfrente pesa entre 3.5 y 10 veces menos que la de la misma cama, pero, como hay muchas plantas en las otras camas, solo el 49–64 % de la presión total se queda en la cama de origen. Para Botrytis y oídio la alerta debe cubrir también las camas vecinas.
2. **Una antracnosis que parte de un solo foco crece despacio.** Con salpicadura local, `r` no pasa de 0.053/d ni con beta = 1, y el frente avanza ~0.13 m/d. Para llegar a r = 0.07/d hace falta inóculo disperso: p_fondo ≈ 1.1e-4 por planta y día con beta = 0.3. Encaja con la biología, porque el hongo inverna en ramillas y escamas de yemas de cada arbusto (MSU E-3039; PNW). Esto apoya la decisión del equipo de tratar la antracnosis como alerta **ambiental**: de nada sirve "buscar el foco".
3. **El aspersor dispersa la antracnosis.** La salpicadura del riego por aspersión dispersa conidias (MSU; PNW). Que el D1 vaya *delante* del aspersor es bueno para ver hojas secas, pero el riego mismo es un evento de dispersión. Sugerencia operativa: si hay alerta en una cama, no regarla por aspersión.
4. **En oídio la cámara no gana tiempo al patógeno.** Entre síntoma visible y esporulación pasa menos de 1 día (Xu y Robinson 2000). El robot no adelanta el periodo infeccioso: su valor está en la frecuencia (2 d frente a 7 d) y en la cobertura (100 % de las plantas frente a 66 por lote).
5. **Regla de Parnell como prueba verificable.** E[q*] = r·Δ/(N·Se). Para oídio (r = 0.15): el monitoreo humano encuentra el brote con ~2.45 % del bloque sintomático (~350 plantas infectadas) y el robot con ~0.015 % (~2 infectadas). Para Alternaria: ~50 frente a <1. Si el simulador no reproduce estos órdenes de magnitud, algo está mal.
6. **Hueco importante: la roya.** En Colombia la roya es de las enfermedades más importantes (6 de 9 fincas; Valbuena-Gaona 2025), pero el clasificador no tiene esa clase y las pústulas están en el envés. Hoy solo la cubre la regla ambiental. Hay que decirlo como límite (rúbrica "casos no detectados").
7. **Tratar temprano paga.** Las aplicaciones iniciadas después de los síntomas fueron 40 % menos efectivas (MacKenzie y Peres 2012). Este es el número para justificar la detección temprana.
8. **Contexto colombiano.** Varias fincas del Altiplano están bajo macrotúnel, invernadero o malla, y el clima va de 12 a 18 °C. Open-Meteo no ve ese microclima, y el frío alarga los periodos latentes (en la roya, unos 4 d más a 15 °C).

## Validación de la calibración

- **Roya.** El frente simulado, ~0.95 m/d, es del mismo orden que la observación de Hawái: 1 arbusto en la esquina de una parcela de 36.6 × 9.1 m y toda la parcela en ~1 mes, o ~1.2 m/d (Keith et al. 2008). La concordancia es buena.
- **Oídio.** El frente simulado da 0.69, 0.78 y 1.01 m/d con λ = 3, 5 y 8 m, frente a 1.65 m/d medido en fresa bajo macrotúnel (Aldrighetti et al. 2025), un hospedante mucho más denso. Dejé λ = 3 m como base y λ = 8 m como escenario de sensibilidad.
- **Antracnosis.** El YAML trae el dato de campo para comprobar el kernel: tras una lluvia, la incidencia fue 7–19 % a ≤ 61 cm de la fuente (Madden et al. 1993).

## Fuentes (URLs que abrí)

- Europe PMC: API de búsqueda `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%22<doi>%22&format=json&resultType=core` (resúmenes de las 28 referencias con DOI listadas en el YAML) y textos completos `…/rest/PMC11333449/fullTextXML` (Neugebauer 2024), `…/PMC12671890/fullTextXML` (Combes 2025) y `…/PMC6558562/fullTextXML` (Mastin 2019).
- https://archive.lib.msu.edu/DMC/extension_publications/e3039/E3039.pdf
- https://pnwhandbooks.org/plantdisease/host-disease/blueberry-vaccinium-corymbosum-rust , …-ripe-rot-anthracnose , …-botrytis-blight , …-alternaria-fruit-rot
- https://revistas.uptc.edu.co/index.php/ciencias_horticolas/article/download/18515/15282/90885 (Valbuena-Gaona et al. 2025)
- https://arxiv.org/pdf/1410.0587 (Mikaberidze et al.)
- https://www.biorxiv.org/content/biorxiv/early/2021/08/04/2021.08.04.455115.full.pdf (Dodgson et al. 2021, CC BY 4.0)
- https://plantmanagementnetwork.org/pub/trial/fntests/reports/2005/SMF040.pdf
- https://site.caes.uga.edu/blueberry/?p=930
- https://extension.uga.edu/content/dam/extension/programs-and-services/integrated-pest-management/documents/insect-pdfs/tbw.pdf
- https://extension.rutgers.edu/sites/default/files/2026-04/bb-v42n05.pdf
- https://greenmethods.com/pages/scouting-info
- https://sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf
- https://cdn.www.gob.pe/uploads/document/file/1916215/Adriano%20Marcuzzo-Best%20Berries-Arandano_0.pdf
- https://www.portalfruticola.com/?p=173671
- https://fieldreport.caes.uga.edu/wp-content/uploads/2025/08/C-946_4.pdf
- https://www.agronegocios.co/agricultura/las-exportaciones-de-arandanos-superaron-us-1-millon-durante-el-primer-semestre-3446716 y https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623
- https://agraria.pe/noticias/al-peru-han-ingresado-mas-de-30-variedades-9724
- https://repositorio.lamolina.edu.pe/server/api/core/items/3af55fc9-63af-4b05-99d6-dcfc573ceaec y …/f7529d2e-59e3-4434-a126-1c2571014703

**Licencias.** Los resúmenes de Europe PMC conservan el copyright de su editorial: los usé para extraer cifras con cita. Son CC BY: Dodgson 2021 (bioRxiv), Combes 2025 y Wang 2023 (PLoS) y Neugebauer 2024 (Frontiers). La licencia del artículo de la UPTC no la verifiqué (es una revista de acceso abierto). Ninguna fuente se redistribuye: las copias de `raw/` son de uso interno.

## Límites

- **Mucha evidencia es análoga (B), no de arándano.** Los gradientes vienen de fresa y frijol; las tasas de antracnosis, de cítricos; los latentes de oídio, de rosa y espino; el kernel de roya, del trigo. Las `r` de Botrytis, oídio y Alternaria son SUPUESTO: no encontré tasas de campo publicadas en arándano.
- **Agostini 1993 da tasas Gompertz**, no logísticas: solo valen como orden de magnitud.
- **La calibración es de referencia:** un foco, riesgo = 1 constante, sin tratamiento y una sola grilla de 1 ha. Las `r` de campo son promedios de temporada, así que `beta_max` puede quedar subestimado (sensibilizar con beta/0.6). La velocidad del frente es una medida ruidosa: la distancia máxima en la cama del foco, sin fondo.
- **La sensibilidad humana de 0.65 es de inspectores profesionales**, con otra enfermedad (*P. ramorum*) y otro hospedante. La de síntoma inicial es SUPUESTO.
- **Todos los parámetros del robot son SUPUESTO** (frecuencia, cobertura, visibilidad desde el pasillo y Sp) hasta que el pipeline mida la sensibilidad por clase y la cadena pantalla → cámara.
- **Sin datos colombianos de tasas ni de gradientes.** De Colombia solo tengo presencia e incidencia relativa por finca, el tamaño de muestra y la densidad gremial.

## Bloqueos (no los salté)

- **apsnet.org (resúmenes APS):** HTTP 403. Usé los mismos resúmenes vía Europe PMC.
- **canr.msu.edu:** anti-bot Incapsula. No pude abrir el ensayo MSU 2022 de fungicidas en arándano ("83–100 % de control"), que queda NO_VERIFICADO.
- **dpi.nsw.gov.au:** desafío de Cloudflare. La guía de roya ("latente 10–21 d") queda NO_VERIFICADO.
- **INIA Perú** (`pgc-snia.inia.gob.pe:8443`, `repositorio.inia.gob.pe`): sin conexión. El ciclo de Heliothis en arándano de Huaral (77.8 ± 9.1 d) y la capacidad de daño por estadio quedan NO_VERIFICADO.
- **Otras fuentes caídas:** UNITRU (marco de Chao, 2.5 × 0.84 m) no resolvió DNS; dos PDFs de UF/IFAS (CREC y GCREC) dieron 404; bluedynamo.msu.edu no resolvió DNS.
- **WebFetch:** el resumidor rechazó algunas páginas de patógenos por su filtro. Las leí con curl y un extractor propio.
- **Tamaño:** ninguna descarga pasó de 6 MB.

## Pendientes

1. **Pipeline:** llenar `deteccion.robot.sensibilidad_clasificador.por_clase` y `especificidad_clasificador` con los valores medidos (split por ráfaga y pantalla → D1).
2. **Riesgo:** entregar `riesgo_d(t)` en [0,1] por enfermedad. El YAML trae los umbrales de apoyo: 8 h de mojadura a 25 °C en antracnosis, 4 h a 18 °C en Alternaria, 15.5–30 °C y HR ≥ 60 % en oídio.
3. **Simulación:** usar `contagio_lejano_por_planta_dia` específico de antracnosis (1.1e-4), no el general. Correr los escenarios λ = 8 m para oídio y beta/0.6 para todas. Comprobar la regla de Parnell.
4. **Robot:** medir el ancho del D1 frente al pasillo libre (1.0–1.5 m) y decidir si recorre los dos lados de cada cama, porque eso cambia `p_lesion_visible_desde_pasillo`.
5. **Si hay contacto con un agrónomo local o Asocolblue:** pedir el protocolo real de monitoreo (frecuencia y plantas por lote) y el calendario de riego por aspersión.
6. **Comunicación:** declarar la roya y la antracnosis/Botrytis en fruto como "no detectables por cámara" en la sección de casos no detectados.
