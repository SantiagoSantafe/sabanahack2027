# Verificación adversaria: ciencia de enfermedades y parámetros de simulación

Rol: verificador adversario (ciencia-simulacion) · Fecha: 2026-10-23 · Sabana Hack, "Berry Good Idea"

Objeto de la revisión:
- `reportes/ciencia-enfermedades.md` (agente ciencia-enfermedades)
- `simulacion/parametros.yaml`, `reportes/parametros-simulacion.md` y `simulacion/calibracion_parametros/*` (agente parametros-simulacion)

Convenciones: **CONFIRMADO** = lo abrí y la fuente lo dice. **REFUTADO / CORREGIDO** = la fuente o el cálculo dice otra cosa. **INCOMPLETO** = es cierto, pero omite evidencia que cambia la conclusión. **SUPUESTO** / **NO VERIFICADO** se usan igual que en el resto del proyecto. No uso la API key de Roboflow (este rol no la necesita) ni la copio en ningún lado.

---

## 0. Veredicto corto

- **La base factual de los dos agentes es sólida.** Revisé 68 filas de afirmaciones contra la fuente primaria o de extensión: 31 del reporte de enfermedades y 37 del YAML y su reporte. Los números citados coinciden con la fuente en casi todos los casos. No encontré cifras inventadas ni DOIs falsos. Los cálculos se reproducen exactamente: la calibración da las mismas cifras al re-ejecutarla y una re-implementación independiente concuerda con ella con un error de ~8 % como máximo.
- **Corregí 6 errores claros y locales en `parametros.yaml`.** Ningún `valor` cambió, así que `beta_calibrado.json` sigue siendo válido (lo re-ejecuté sobre el YAML corregido y dio lo mismo). Ver sección 4.
- **Hay 5 hallazgos que sí cambian decisiones** (sección 5):
  1. **Roya en 'Biloxi' (el cultivar de casi todas las fincas colombianas):** el periodo hasta la pústula fue de **15–21 d** a 21–24 °C (Huarhua et al. 2020). Ningún agente lo usó. El "ciclo de 10–14 d" queda **incompleto**, y con un periodo latente de 18 d el `r_objetivo` de 0.12 /d **no se alcanza ni con beta = 1** (r máximo 0.106).
  2. **Ventanas de temperatura frente al clima de la Sabana.** La regla de roya del equipo (19–25 °C) casi nunca se activaría con medias de 12–18 °C, y Pfister 2004 muestra que a 15 °C se forman tantos uredinios como a 20 y 25 °C. Botrytis (14–25 °C, Rivera 2013) tiene el mismo problema en noches frías. Ambas reglas producirían **casos no detectados**.
  3. **"66 plantas por lote" no es el monitoreo real de las fincas.** Es la salida de la fórmula de Cochran (90 % de confianza, 10 % de error, p = 0,5), que da unas 68 plantas para cualquier lote grande. Toda la comparación humano-robot de la regla de Parnell descansa sobre ese número.
  4. **La epidemia simulada crece más lento que exponencial.** La `r` medida cae a la mitad entre las fases de 10–50 y 250–1.000 plantas infectadas. El criterio "el simulador debe reproducir los números de Parnell" usa una `r` constante, y por eso dará cifras humanas unas 2 veces más altas que las que mostrará el simulador.
  5. **El aspersor no está documentado en Colombia.** Las dos fincas colombianas con dato de riego usan **goteo/fertirriego** (Guasca, Sopó). Además, MSU, CT CAES y UF/IFAS desaconsejan el riego por aspersión porque favorece antracnosis, Botrytis y roya. La frecuencia del robot ("cada turno de aspersor") y el concepto "delante del aspersor" necesitan otra justificación.

---

## 1. Qué hice

1. Leí completos los dos reportes, el YAML y los dos scripts de calibración.
2. **Re-ejecuté la calibración** sobre una copia del proyecto en el scratchpad, para no sobrescribir los resultados del agente: primero con el YAML original y luego con el YAML ya corregido. Las salidas son idénticas a `beta_calibrado.json` y `calibracion_complementaria.json`.
3. **Re-implementé el simulador de forma independiente**, con convolución directa por desplazamientos en lugar de FFT y con otra semilla. Medí `r` en cuatro ventanas de tamaño de brote.
4. **Recalculé a mano** los pesos de los kernels, las fracciones de presión "en la misma cama", la regla de Parnell, las conversiones de unidades (min/acre → min/ha, s/planta) y la fórmula de Cochran.
5. **Abrí las fuentes:**
   - las copias locales en `raw/` de los otros agentes, convertidas a texto desde fuera de `raw/`;
   - 9 resúmenes nuevos en Europe PMC y 4 registros nuevos en Crossref;
   - 8 páginas web (EPPO ×3, Portal Frutícola, Blueberries Consulting, Ohio State, Penn State, UF/IFAS);
   - 1 artículo nuevo descargado (Cortés-Rojas 2016).
6. Busqué en la web registros de oídio y de antracnosis en arándano colombiano, para intentar refutar los "NO VERIFICADO" del reporte de enfermedades.

Todo el Python que leyó archivos de `raw/` corrió con `-I`, desde fuera de `raw/`, con rutas pasadas como argumento.

---

## 2. Reproducción de cálculos

| Chequeo | Resultado | Veredicto |
|---|---|---|
| `calibrar_beta.py` + `calibracion_complementaria.py` re-ejecutados (semillas del agente) | Mismos `beta_max`: 0.0196 / 0.264 / 0.0485 / 0.0184; antracnosis con r máximo 0.0528; fondo de 1.1e-4 con beta = 0.3 | **CONFIRMADO** |
| Re-implementación independiente (sin FFT, semilla 5, 8 réplicas), ventana de 10–250 plantas | r = 0.086 (Botrytis, beta = 0.020), 0.124 (roya), 0.152 (oídio), 0.052 (Alternaria); objetivos 0.08 / 0.12 / 0.15 / 0.05 | **CONFIRMADO** (error <= ~8 %) |
| Pesos y fracciones de los kernels (cálculo propio) | Razones 100:1, 3.5:1, 9.9:1, 3.5:1, 5.8:1; fracciones en la misma cama 0.973 / 0.493 / 0.620 / 0.489 / 0.636 | **CONFIRMADO** |
| Regla de Parnell: aritmética | Humano r = 0.1: 1.63 %. Robot: 0.01 %. Oídio: 2.45 % × 5.000 × e^(0.15·7) ≈ 350. Alternaria ≈ 50. Roya 1.96 % → 413 | **CONFIRMADO** (la cuenta; ver 5.4 para el concepto) |
| Factor e^(r·incubación) | Coincide con el factor e^(rλ) de la regla de Mastin et al. 2019 (ecuación 2.2 del texto completo) | **CONFIRMADO** |
| 20 min/acre → min/ha; 49 min / 66 plantas | 49.4 min/ha; 44.5 s por planta | **CONFIRMADO** |
| Ruido de calibración | Oídio con λ = 3 m: 0.0485 en un script y 0.0543 en el otro (otra semilla y otra grilla de beta) | ±12 %; no se reporta en el YAML |
| `r` según la ventana (re-implementación independiente) | Oídio 0.157 / 0.136 / 0.082; Botrytis 0.104 / 0.072 / 0.046; roya 0.113 / 0.107 / 0.079; Alternaria 0.062 / 0.044 / 0.029 (ventanas de 10–50, 50–250 y 250–1.000 infectadas) | **Hallazgo nuevo**: crecimiento subexponencial (5.4) |
| Roya con periodo latente de 18 d (escenario Biloxi) | r = 0.090 con beta = 0.264; 0.106 con beta = 0.5 y 0.106 con beta = 1 | `r_objetivo` = 0.12 **inalcanzable** (5.1) |
| Sensibilidad de la "fracción en la misma cama" (Botrytis) | f_cruce 0.2 → 0.75; 0.8 → 0.33; λ = 2.1 m → 0.56; camas a 2.2 m → 0.47. Roya con los pares (r0, b) del paper: 0.49 y 0.64 | La conclusión "49–64 %" depende sobre todo de **supuestos** |

---

## 3. Fuentes revisadas: afirmación → veredicto

### 3.1 Reporte `ciencia-enfermedades.md`

| Afirmación | Veredicto | Evidencia que abrí |
|---|---|---|
| Oídio: no necesita agua libre; infección en ~23 h; esporas a los ~5 d; manchas cloróticas con borde rojizo y áreas acuosas en el envés | CONFIRMADO | Cornell Fast Facts (`raw/ciencia_cornell_oidio`) |
| El agua libre inhibe a los oídios (como regla general) | CONFIRMADO | WSU (`raw/ciencia_wsu_powdery`) |
| Penn State: moteado amarillo que pasa a rojo; el polvo blanco muchas veces falta; el texto se contradice sobre el clima | CONFIRMADO | extension.psu.edu (abierto) |
| Bradshaw 2025: E. vaccinii en China, Marruecos, México y EE. UU.; Colombia no figura | CONFIRMADO | Europe PMC, resumen |
| Oídio en Colombia: NO VERIFICADO | Se mantiene | Mi búsqueda tampoco encontró registro |
| Alternaria: 68 °F, viento y salpicadura de fin de floración a madurez, manchas de ~6 mm con borde café rojizo | CONFIRMADO | ohioline.osu.edu PLPATH-FRU-44 (abierto) |
| Alternaria en Colombia: necrosis con halo clorótico | CONFIRMADO | Valbuena-Gaona 2025 (texto) |
| Milholland 1973 (cita) | CONFIRMADO (metadatos) | Crossref |
| Antracnosis: óptimo 25 °C, ≥ 8 h de mojadura, ≥ 24 h severa, ~7 d en fruto maduro; inverna en ramillas, espolones viejos y yemas; aspersor | CONFIRMADO | MSU E-3039 (texto) |
| PNW: 10 h frente a 18–24 h a 52–60 °F; las interrupciones secas inhiben | CONFIRMADO | `raw/paramsim_pnw_...ripe-rot` |
| Miles, Gillett, Jarosz y Schilder 2013, Plant Pathol 62:1238 | CONFIRMADO (cita) | Crossref. Las cifras del resumen siguen como "solo buscador": Wiley dio 403 |
| Antracnosis en Colombia: NO VERIFICADO | Se mantiene, **con matiz** | *C. acutatum* s.l. y *C. gloeosporioides* s.l. causan antracnosis en mora andina (*Rubus glaucus*) en 8 zonas de Colombia, con pérdidas de hasta 40 % (Afanador-Kafuri et al. 2014, Plant Dis, doi:10.1094/PDIS-07-13-0752-RE; resumen en Europe PMC). El género está en el trópico alto, aunque no hay registro en arándano |
| Botrytis: regla de arándano > 6 h de mojadura entre 14 y 25 °C, r = 0,96, sin validar en campo; plena floración y fruto maduro, las etapas más susceptibles | CONFIRMADO | Rivera et al. 2013, resumen en Europe PMC |
| CT CAES: ≥ 6 h de mojadura o HR > 90 %; 65–75 °F | CONFIRMADO | `raw/ciencia_caes_botrytis` |
| Nueva Escocia: 6 h a 16 °C (baja); 24 h a 12 °C, 13 h a 16 °C y 10 h a 20 °C (alta) | CONFIRMADO | `raw/ciencia_dal_wildblueberry_blight` |
| Bulger 1987: óptimo ~20 °C (marcado "solo buscador") | **CONFIRMADO directamente** | Resumen en Europe PMC. Agrega un dato: la infección cae mucho por debajo de 15 °C y por encima de 25 °C |
| Broome 1995 es de uva | CONFIRMADO | Europe PMC |
| Roya: *T. minima* en Rionegro, vereda Higuerón, 2.300 msnm, 8-nov-2011, MMUNM-1973, solo estado II | CONFIRMADO | `raw/ciencia_rfnam_royas2012` |
| EPPO: *T. minima* presente en Colombia, sin detalles; datos actualizados al 2024-12-09 | CONFIRMADO | gd.eppo.int/taxon/THEKMI/distribution |
| Pfister 2004: óptimos 21,5 °C y 19,5 °C; incubación de 10,7 d (20 °C) y 10,0 d (25 °C); ~4 d más a 15 °C; ensayo en rododendro | CONFIRMADO | Resumen (Europe PMC) |
| Griffin y Anderson 2026: uredinios a los 9–10 d; 100 % de HR no bastó, hicieron falta gotas; 19–23 °C; CC BY | CONFIRMADO | `raw/ciencia_mdpi_jof12_133` |
| "Ciclo de la roya de 10–14 d, como suponíamos" | **INCOMPLETO** | En Biloxi, pústulas a los 15–21 d con 21–24 °C (Huarhua et al. 2020, resumen). En Sharpblue, 10 d a 20–22 °C (Keith et al. 2008). Ver 5.1 |
| Valbuena 2025: roya en 6 de 9 fincas (falta en Mosquera, Paipa y Sutatausa); Botrytis en 8 de 9 (falta en Mosquera); 12–18 °C, HR > 70 %, lluvias bimodales; muestreo abril–junio de 2024; Biloxi; sin oídio, antracnosis ni Heliothis | CONFIRMADO | Texto completo |
| Licencia de Valbuena 2025: NO VERIFICADA | **Ahora verificada** | CC BY-NC-SA 4.0 según los metadatos de Crossref (no aparece en el texto del PDF) |
| *D. suzukii*: primer registro en Colombia en 2026; en fresa; Antioquia, Santander y Boyacá; bajo control oficial; el enlace IPPC apunta por error a Venezuela | CONFIRMADO | gd.eppo.int (distribución y RS 2026/136) |
| Asocolblue: ~1.000 ha; Cundinamarca y Boyacá ~90 %; 2.200–2.900 m; producción todo el año; ~50 % de la fruta sin cubierta no exportable | CONFIRMADO | Portal Frutícola, 23-02-2026 |
| Picos nov–dic, may–jun y sep; poda para inducir producción; domina Biloxi; predomina campo abierto y se prefiere macrotúnel a invernadero | CONFIRMADO | Blueberries Consulting 2025. Las afirmaciones no tienen informante con nombre: el reporte ya lo advierte |
| Guasca: 0,8 × 2,2 m (5.600 pl/ha) y 1,0 × 2,2 m (4.275 pl/ha); 12,85 °C; ácaros, roya y moho gris; 28 semanas de cosecha | CONFIRMADO, **con un error de la propia fuente** | Cortés-Rojas 2016 (descargado). Con esas distancias da 5.682 y 4.545 pl/ha: las densidades que reporta el artículo no cuadran con su marco de siembra |
| Sopó: 2.650 m, 6–19 °C, ~848 mm, 8 ha bajo invernadero, 0,7 × 1,2 m, heladas (0–10 °C) y máximas de 25–35 °C | CONFIRMADO | Tesis (texto) |
| DrBerry: el resumen dice Huaral, el texto Sayán, provincia de Huaura; 439 + 105 imágenes; exactitud 84 % y recall 91 % en el resumen; tablas con 44,5 % y 92,6 % | CONFIRMADO | `raw/ciencia_drberry_paper` |
| UF/IFAS PP385: en sistemas evergreen la roya está entre las 3 preocupaciones principales; el aspersor la favorece | CONFIRMADO | ask.ifas.ufl.edu (abierto) |

No revisé Pazdiora 2019 (roya en Brasil) ni Spiers 2002 (Biloxi).

### 3.2 `parametros.yaml` y `parametros-simulacion.md`

| Parámetro / afirmación | Veredicto | Nota |
|---|---|---|
| Ntahimpera 1997: 27 cm, exp(−d²) | CONFIRMADO | Lo de "radio de captura de 72 cm" estaba mal dicho: es el área de conteo. **Corregido** |
| Yang 1990: ~60 % frente a ~18 % a 60 cm con 2,3 m/s | Cifras CONFIRMADAS; "en campo" **REFUTADO** | Es un simulador de lluvia con túnel de viento. **Corregido** |
| Madden 1993: 0,19 / 0,07 / 0 / 0 (1990) | CONFIRMADO | Fresa al ras del suelo; el fruto de arándano está a 0,5–1,5 m (SUPUESTO) |
| Madden y Boudreau 1997; Boudreau y Madden 1995 | CONFIRMADO | — |
| Wilson 1990: óptimo 25–30 °C, > 80 % tras 13 h | CONFIRMADO | — |
| Verma 2007: 10 h a 11 °C bastaron | CONFIRMADO | — |
| Agostini 1993: 0,05 / 0,11 / 0,05 / 0,04 en árboles y 0,07 / 0,05 / 0,04 / 0,02 en flores | CONFIRMADO | Son gompits/d: bien advertido |
| Silva-Junior 2014: logística de 0,53 /d; patrón inicial aleatorio | CONFIRMADO | — |
| Johnson y Powelson 1983: 70 % a 0,9 m y < 25 % a > 4 m; esporas hasta ~3 m | Cifras CONFIRMADAS; "λ ≥ 3,0 m" **REFUTADO** | Es una cota superior (λ ≤ 3,0 m). La pudrición de vaina del mismo artículo da λ ≈ 2,1 m. **Corregido el comentario** |
| Wang 2023: > 50 % a 10 cm, ~80 % a 16 cm | CONFIRMADO | — |
| Neugebauer 2024: conidias a los 3–4 d (cita a Bristow 2017); aplicaciones cada 7–10 d | CONFIRMADO | `duracion_proteccion_dias` usa el intervalo de aplicación como proxy: es DERIVADO, no FUENTE A (no lo cambié) |
| Pfister 2004; Dal Bello 1998 (pústulas a los 10 d; solo 48 h a 20 °C y luego invernadero); Keith 2008 | CONFIRMADO | — |
| Periodo latente de roya = 12 d, "FUENTE/A" | **Etiqueta REFUTADA** | Es una extrapolación (rododendro + ajuste por frío) y omitía a Huarhua (15–21 d en Biloxi). **Cambiada a DERIVADO/B** |
| Mikaberidze: b = 3,04 y 2,23; r ≈ 0,18–0,25 | CONFIRMADO | Pero b y r0 se ajustaron en pares (r0 = 2,23 y 0,45 m), y el YAML combina b = 2,6 con r0 = 1,0 (SUPUESTO). El "infeccioso = 20 d" es circular, ver 4 |
| Aldrighetti 2025: 1,65 m/d, decaimiento exponencial | CONFIRMADO | — |
| Xu 1999 (4–10 d, ~22 °C); Xu y Robinson 2000 (5–16 d, < 1 d de síntoma a esporulación) | CONFIRMADO | — |
| Dodgson 2021: > 15,5 °C y < 30 °C, HR > 60 %, 144 h, aplicar entre 125 y 144 h | CONFIRMADO | — |
| Hong y Fitt 1995/1996: 4 h a 18 °C; 2,5–3,5 d; 1–11 d | CONFIRMADO | — |
| UGA (gusano del tabaco): huevo 3–4 d; larva 17–18 d a 25 °C; pupa ~13 d | CONFIRMADO | — |
| Combes 2025: 23 evaluadores, hasta 175 robles, Sp > Se en 22 de 23 | CONFIRMADO | — |
| Mastin 2019: 588/900 = 0,65; los 10 mejores de 16 inspectores; *P. ramorum* en rododendro; retraso de 14 d | CONFIRMADO | — |
| Parnell 2015: E(q*) = r/(N/Δ) | CONFIRMADO | — |
| Valbuena 2025: 66–68 plantas (Mosquera, 51) | Cifra CONFIRMADA; uso como esfuerzo humano **REFUTADO** | Es la fórmula de Cochran. **Etiqueta cambiada a DERIVADO/C** |
| Rutgers: 89 campos en una semana | CONFIRMADO | Programa de New Jersey, no colombiano |
| Green Methods: ~20 min por semana por acre (muestreo por área) | CONFIRMADO | Regla genérica de una empresa, no de arándano |
| Sensirion SHT31: ±0,2 °C; ±2 %HR (típico) | CONFIRMADO | La tabla del SHT30 sube a ±3 % con 90 % de HR. El umbral de HR ≥ 90 % de Botrytis queda dentro de la banda de error |
| Louws y Driver 2005: 15,0 / 6,3 / 8,0 / 18,8 % | Cifras CONFIRMADAS; "0 % (Elevate)" **inexacto** | Elevate quedó 25 % peor que el testigo (no significativo), y el 47 % de Captevate no es significativo (LSD 7,0). **Comentario corregido** |
| Cordova 2019: ~10 % | CONFIRMADO | El YAML decía "10 puntos" y el resumen no lo aclara. **Comentario ajustado** |
| MacKenzie y Peres 2012: 47 % menos aplicaciones; 40 % menos eficaz si se empieza tras los síntomas | CONFIRMADO | — |
| Cordova 2017: mediana de 7 aplicaciones menos (50 %) | CONFIRMADO | El DOI no está en `raw/paramsim_europepmc/doi/`, pero aparece en `fungicide_meta.json` y lo consulté aparte |
| Barry 2025: AUDPC de roya −20–25 % | Cifra CONFIRMADA; **contexto omitido** | Frente a los peores tratamientos, no frente a un testigo; ningún producto controló la roya. **Comentario corregido** |
| Huarhua 2020: primer reporte en Perú, 9 campos de Biloxi | CONFIRMADO | Omitía los 15–21 d (5.1) |
| Best Berries 2,50 × 0,80 m = 5.000; INIA camellón de 1 m × 50 cm y 0,8–1 m sobre la hilera; UGA 4 ft; Asocolblue 5.000–5.500 pl/ha | CONFIRMADO | — |
| Rango de `distancia_entre_hileras_m` [2,5; 3,05] | **REFUTADO** (excluye a Colombia) | Guasca: 2,2 m entre centros de cama. **Rango ampliado a [2,2; 3,05]** |
| "28 referencias con DOI verificadas en Europe PMC" | **Inexacto (menor)** | El YAML tiene 27 DOIs distintos. De ellos, 25 están en `doi/`, 2 se verificaron por otra vía y 3 archivos de `doi/` no se citan en el YAML. Todas las referencias existen |
| "beta_max calibrado para reproducir la r de la literatura" | **Exagerado** | 3 de 5 `r_objetivo` son SUPUESTO (Botrytis, oídio, Alternaria), como reconoce la sección de límites del propio reporte |
| "El frente de roya (~0,95 m/d) coincide con Hawái (~1,2 m/d): concordancia buena" | **Exagerado** | "En un mes" da una cota inferior (≥ 1,2 m/d), y el simulado queda por debajo. Había otra fuente posible (un vivero con roya desde mayo de 2007). **Nota añadida** |

---

## 4. Cambios que hice en `simulacion/parametros.yaml`

Todas las líneas nuevas empiezan con `VERIFICADOR:`. **No cambié ningún `valor`.** El YAML sigue cargando sin errores, todos los ids de `fuentes` resuelven (ahora son 51) y la calibración re-ejecutada sobre la versión corregida da salidas idénticas.

| # | Ubicación | Cambio | Motivo |
|---|---|---|---|
| 1 | Encabezado | Nota de revisión | Trazabilidad |
| 2 | `grilla.distancia_entre_hileras_m` | `rango` de [2.5, 3.05] a **[2.2, 3.05]**; se añade la fuente `cortesrojas2016` | El rango excluía la única medida colombiana a campo abierto |
| 3 | `antracnosis.kernel` (comentarios) | "en campo" → simulador con túnel de viento (Yang 1990); "radio de captura de 72 cm" → área de conteo (Ntahimpera 1997) | Lectura errónea de la fuente |
| 4 | `botrytis.kernel.lambda_m` (comentario) | "λ ≥ 3,0 m" → **"λ ≤ 3,0 m"** (cota superior); se añade λ ≈ 2,1 m (pudrición de vaina, mismo artículo); el extremo 4,0 del rango queda como SUPUESTO | Desigualdad invertida |
| 5 | `botrytis` | Notas sobre la regla de arándano de Rivera 2013 y su ventana de 14 °C frente a Guasca; sensibilidad de la fracción en la misma cama | Discrepancia entre agentes; conclusión que dependía de supuestos |
| 6 | `roya.latente_dias` | Etiqueta FUENTE/A → **DERIVADO/B**; se añaden Huarhua 2020 (15–21 d en Biloxi) y Keith 2008; se sugiere un escenario de 18 d | El valor 12 es una extrapolación y la etiqueta no lo decía |
| 7 | `roya.infeccioso_dias` (comentario) | Se aclara que μ = 0,05 es el supuesto del propio paper, recuperado al despejarlo | Derivación circular |
| 8 | `roya.kernel` (comentario) | Se documentan los pares (r0, b) ajustados en el paper | Combinación sin respaldo |
| 9 | `roya.condiciones_infeccion` (comentario) | Ventana sugerida de 15–25 °C; el aspersor favorece la roya | Pfister 2004; UF/IFAS PP385 |
| 10 | `oidio` (comentarios) | El micelio blanco a menudo falta; periodo latente de ~5 d en arándano (Cornell) frente a una posible acumulación lenta en frío (Dodgson) | Discrepancia entre agentes |
| 11 | `deteccion.humano.plantas_por_bloque_por_visita` | Etiqueta FUENTE/A → **DERIVADO/C**, con la explicación de Cochran | La cifra no mide el monitoreo real |
| 12 | `deteccion.robot.frecuencia_dias` (comentario) | Las fincas colombianas documentadas riegan por goteo; las guías desaconsejan la aspersión | Pertinencia |
| 13 | `tratamiento.eficacia_protectante` (comentarios) | Louws y Driver: significancia y Elevate peor que el testigo; Cordova 2019: "~10 %"; Barry 2025: frente a los peores tratamientos | Contexto omitido |
| 14 | `validacion.regla_parnell` y `roya_hawai` | `r` según la ventana (medida); la observación de Hawái es una cota | El criterio de validación no se cumpliría |
| 15 | `fuentes.valbuena2025` | Licencia: "no verificada" → **CC BY-NC-SA 4.0** (Crossref) | Verificada |
| 16 | `fuentes.cortesrojas2016` | Fuente nueva (metadatos de Crossref; CC BY-NC-SA 4.0) | Respaldo del cambio 2 |

No toqué `reportes/ciencia-enfermedades.md`, `reportes/parametros-simulacion.md` ni los JSON de calibración: sus cifras siguen siendo correctas para el YAML actual.

---

## 5. Hallazgos que no corregí (son ambiguos o los decide el equipo)

### 5.1 Roya en Biloxi: periodo latente más largo y `r_objetivo` incompatible
- Huarhua et al. 2020 asperjaron una suspensión de esporas sobre plantas de Biloxi y las mantuvieron en invernadero a 21–24 °C, mojándolas a diario. Las pústulas aparecieron a los 15–21 d. Keith et al. 2008 vieron 10 d en Sharpblue, un cultivar muy susceptible, e indican que Biloxi mostró cierta tolerancia.
- Con latente = 18 d, el simulador no llega a r = 0,12 /d ni con beta = 1 (r máximo 0,106). Corrí 6 réplicas con las semillas del script.
- **Recomendación:** escenario "Biloxi frío" con latente de 18 d y `r_objetivo` de 0,08–0,09, recalibrado. Además, la alerta de roya debería anticipar unos **2–3 semanas** entre el evento de riesgo y la pústula, no 10 d.

### 5.2 Las ventanas de temperatura no encajan con la Sabana (riesgo de casos no detectados)
- **Roya:** la regla del equipo, 19–25 °C, casi no se activaría con medias de 12–18 °C. Pfister 2004 encontró igual número de uredinios a 15, 20 y 25 °C. Sugerencia: 15–25 °C más mojadura con gotas (Griffin y Anderson 2026: la HR del 100 % sola no basta).
- **Botrytis:** Rivera 2013 empieza en 14 °C, pero en Guasca el artículo reporta una media de 12,85 °C y una mínima de 10,6 °C. Nueva Escocia reporta infección alta con 24 h a 12 °C. Sugerencia: probar con el clima real de Open-Meteo cuántos eventos marca cada regla en un año, frente a la presencia de Botrytis en 8 de 9 fincas. Esto entrega a la rúbrica una cifra explícita de casos no detectados de la regla.
- **Oídio:** la regla de fresa exige más de 15,5 °C. En la Sabana sería poco frecuente, lo que coincide con que no hay registro colombiano.

### 5.3 "66 plantas por visita" no es el monitoreo real
Lo que Valbuena 2025 reporta es la fórmula de Cochran: n0 = 1,65² · 0,25 / 0,1² = 68,06, corregida por población finita (con N = 195 da 51, el valor de Mosquera). No dice cuántas plantas revisa un monitor en la práctica. La conclusión "el humano encuentra el brote con unas 350 plantas infectadas y el robot con unas 2" depende directamente de N = 66 y de Se = 0,65. Esa sensibilidad viene de los 10 mejores inspectores profesionales de 16, con otra enfermedad. Hay que presentarla como **escenario**, con sensibilidad para N entre 30 y 300.

### 5.4 Crecimiento subexponencial: el chequeo de Parnell, tal como está escrito, fallará
En la grilla, la `r` cae a la mitad entre las ventanas de 10–50 y 250–1.000 infectadas (tabla de la sección 2). El hallazgo humano ocurre con varios cientos de plantas infectadas, cuando la `r` efectiva vale aproximadamente la mitad de `r_objetivo`. El simulador dará entonces un q* humano unas 2 veces menor que las cuentas del YAML, sin que haya un error. **Recomendación:** validar con la `r` medida en el propio simulador durante esa fase. El orden de magnitud de la comparación humano-robot se mantiene.

### 5.5 El aspersor en Colombia: sin evidencia, y contraindicado por las guías
Guasca usa cinta de goteo por cama (Cortés-Rojas 2016) y Sopó usa fertirriego. No encontré fuentes colombianas con riego por aspersión en arándano: queda **NO VERIFICADO**. MSU E-3039 y CT CAES recomiendan el goteo, y UF/IFAS dice que la aspersión favorece la roya. Para la sustentación (Pertinencia) conviene:
- justificar la frecuencia del robot por su propia agenda (por ejemplo, cada 2 días), no por el aspersor;
- presentar "no regar por aspersión con riesgo alto" como recomendación, no como premisa.

### 5.6 Otros puntos menores
- **Antracnosis.** "r no llega a 0,07 desde un foco, lo que respalda la alerta ambiental" es consecuencia del kernel supuesto (w_d2 = 0,1 y w_cama_vecina = 0,01), no una evidencia independiente. La conclusión es razonable por la biología (inóculo en cada arbusto, MSU), pero no por la simulación. Además, `radio_max_m` = 2,0 es menor que los 2,5 m de la cama vecina. No tiene efecto, porque el kernel de tipo vecindad no usa ese radio, pero es incoherente.
- **Fracción de presión en la misma cama** (49–64 %): oscila entre 33 y 75 % dentro del rango supuesto de `f_cruce_hilera`. "La alerta debe cubrir las camas vecinas" es una decisión prudente, no un resultado medido.
- **Periodos infecciosos:** todos son SUPUESTO o circulares (sección 4, cambio 7). Conviene un análisis de sensibilidad con ±50 %.
- **`duracion_proteccion_dias`:** el intervalo de aplicación de 7–10 d se usa como si fuera la duración de la protección. Es DERIVADO, no FUENTE A.
- **Ruido de calibración:** ±12 % entre los dos scripts (oídio). Conviene reportar `beta_max` con un intervalo.
- **Densidad de Guasca:** el artículo da 5.600 y 4.275 pl/ha, pero con sus propias distancias resultan 5.682 y 4.545. Hay que citarlo con esa advertencia.
- **Antracnosis en Colombia:** sin registro en arándano. Sin embargo, *C. acutatum* s.l. y *C. gloeosporioides* s.l. causan pérdidas de hasta 40 % en mora andina (Afanador-Kafuri et al. 2014). El inóculo potencial existe en el mismo piso térmico, lo que matiza el "poco pertinente". No cambia la prioridad.

---

## 6. Archivos producidos o modificados

- `reportes/verificacion-ciencia-simulacion.md` (este reporte)
- `simulacion/parametros.yaml` (comentarios, etiquetas, un rango y dos fuentes; ver sección 4)
- `raw/verifcs_europepmc/`: respuestas JSON de Europe PMC (Rivera 2013, Bulger 1987, Broome 1995, Bradshaw 2025, Schilder y Miles 2011, Cordova 2017, Afanador-Kafuri 2014; búsquedas vacías para ppa.12061 y Phyto-63-1395). Uso interno.
- `raw/verifcs_crossref/`: metadatos de Crossref (Miles 2013, Milholland 1973, Valbuena 2025, Cortés-Rojas 2016). Uso interno.
- `raw/verifcs_cortesrojas2016/`: HTML del artículo (CC BY-NC-SA 4.0) con `URL.txt`. Uso interno, no redistribuir.
- Scripts de verificación en el scratchpad de la sesión (no son entregables): `tools/check_kernel.py` (pesos), `tools/indep_sim.py` (re-implementación), `tools/frac_sens.py` (sensibilidad), `tools/roya_l18.py` (escenario Biloxi).

---

## 7. Fuentes que abrí en esta verificación

Además de las copias locales en `raw/ciencia_*` y `raw/paramsim_*` citadas en las tablas:

- API de Europe PMC: `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"<doi>"&format=json&resultType=core` para 10.1094/PDIS-12-12-1112-RE, 10.1094/Phyto-77-1225, 10.1094/Phyto-85-97, 10.1111/nph.20351, 10.1094/PDIS-12-10-0884 y 10.1094/PDIS-04-17-0477-RE; búsqueda "Colletotrichum AND Andean blackberry AND Colombia".
- API de Crossref: `https://api.crossref.org/works/` para 10.1111/ppa.12061, 10.1094/Phyto-63-1395, 10.19053/uptc.24223719.18515 y 10.15446/agron.colomb.v34n1.54897.
- https://revistas.unal.edu.co/index.php/agrocol/article/download/54897/60637?inline=1 (Cortés-Rojas et al. 2016)
- https://gd.eppo.int/taxon/DROSSU/distribution/CO
- https://gd.eppo.int/reporting/article-8432
- https://gd.eppo.int/taxon/THEKMI/distribution
- https://www.portalfruticola.com/noticias/2026/02/23/arandanos-colombianos-tecnificacion-crecimiento-exportador/
- https://blueberriesconsulting.com/en/la-creciente-industria-de-los-arandanos-en-colombia-importaciones-record-y-expansion-de-cultivos-en-altura/
- https://ohioline.osu.edu/factsheet/plpath-fru-44
- https://extension.psu.edu/blueberry-disease-powdery-mildew-not-symptoms-youd-expect
- https://ask.ifas.ufl.edu/publication/PP385
- Intentos fallidos: https://bsppjournals.onlinelibrary.wiley.com/doi/abs/10.1111/ppa.12061 (HTTP 403) y la página de pestinfo de Plant Pathology 62:1238 (conexión rechazada). Las cifras del resumen de Miles 2013 siguen como "solo buscador".

Licencias: los resúmenes de Europe PMC y los metadatos de Crossref conservan los derechos de sus editoriales. Todo está parafraseado y nada se redistribuye.

---

## 8. Límites de esta verificación

- No abrí el texto completo de Miles 2013, Bulger 1987, Rivera 2013, Pfister 2004 ni Huarhua 2020: solo sus resúmenes.
- La re-implementación usa el mismo modelo conceptual: verifica el código, no el modelo. No tengo ninguna serie de campo colombiana con la que validar `r`, kernels ni periodos latentes, y nadie en el equipo la tiene.
- No verifiqué Pazdiora 2019, Spiers 2002, Agraria.pe, Andina ni las fuentes de Heliothis en Perú. Tampoco el bloqueo de NSW DPI ni el de canr.msu.edu.
- El escenario de roya con latente de 18 d usa 6 réplicas: es un indicio robusto (r máximo < 0,12), no una calibración.
- No revisé `pipeline/`, `clima/` ni `finanzas/` (fuera de mi foco).

## 9. Pendientes sugeridos

1. **Equipo de riesgo:** ampliar la ventana de roya a 15–25 °C y contar, con el clima real de Open-Meteo de la Sabana, cuántos eventos de riesgo de roya y de Botrytis da cada regla en un año (evidencia de casos no detectados).
2. **Simulación:** agregar los escenarios "roya en Biloxi" (latente de 18 d, `r_objetivo` de 0,08–0,09, recalibrado) y "Botrytis λ = 2,1 m". En la regla de Parnell, comparar con la `r` medida y no con `r_objetivo`.
3. **Detección humana:** presentar N = 66 como escenario, con sensibilidad para N entre 30 y 300, y conseguir el protocolo real de monitoreo (Asocolblue o un agrónomo).
4. **Robot:** desligar la frecuencia del aspersor y confirmar si alguna finca de la Sabana riega por aspersión. Si ninguna lo hace, reformular "delante del aspersor".
5. **Comunicación:** cambiar "concordancia buena con Hawái" por "mismo orden de magnitud" y "calibrado a la r de la literatura" por "calibrado a r de literatura (2 de 5) o supuestas (3 de 5)".
